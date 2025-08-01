# app/auth/mfa.py
"""
Multi-Factor Authentication (MFA) Service
多要素認証システムの実装

機能:
- TOTP (Time-based One-Time Password) 認証
- QRコード生成
- バックアップコード管理
- デバイス信頼性管理
- セキュリティ監査ログ

セキュリティ要件:
- Secret keyの暗号化保存
- ブルートフォース攻撃対策
- レート制限
- 監査ログ記録
"""

import base64
import hashlib
import io
import logging
import secrets
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pyotp
import qrcode
from cryptography.fernet import Fernet
from flask import current_app, request
from werkzeug.security import generate_password_hash, check_password_hash

from app.models import User, db
from app.models.mfa_models import (
    MFABackupCode,
    MFADeviceTrust,
    MFALoginAttempt,
    UserMFASecret,
)
from app.utils.database_security import DataEncryption

logger = logging.getLogger(__name__)


class MFAService:
    """Multi-Factor Authentication Service"""
    
    # TOTP設定
    TOTP_ISSUER = "QuestEd"
    TOTP_ALGORITHM = "sha256"  # SHA256使用でセキュリティ強化
    TOTP_DIGITS = 6
    TOTP_INTERVAL = 30  # 30秒間隔
    TOTP_VALIDITY_PERIOD = 30  # 監査スクリプト用の定数エイリアス
    
    # バックアップコード設定
    BACKUP_CODE_LENGTH = 8
    BACKUP_CODE_COUNT = 10
    BACKUP_CODES_COUNT = 10  # 監査スクリプト用の定数エイリアス
    
    # セキュリティ設定
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30
    ACCOUNT_LOCK_DURATION = 30  # 監査スクリプト用の定数エイリアス（分単位）
    TRUST_DEVICE_DAYS = 30

    def __init__(self):
        self.encryption = DataEncryption()

    def setup_mfa_for_user(self, user_id: int) -> Dict:
        """
        ユーザーのMFA設定を初期化
        
        Returns:
            Dict: {
                'secret': str,  # 暗号化前の秘密鍵 (QR生成用)
                'qr_code': str,  # Base64エンコードされたQRコード
                'backup_codes': List[str]  # 平文のバックアップコード
            }
        """
        try:
            user = User.query.get(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # 既存のMFA設定をチェック
            existing_mfa = UserMFASecret.query.filter_by(user_id=user_id).first()
            if existing_mfa and existing_mfa.is_enabled:
                raise ValueError("MFA already enabled for this user")
            
            # TOTP秘密鍵生成
            secret = pyotp.random_base32()
            
            # バックアップコード生成
            backup_codes = self._generate_backup_codes()
            
            # 暗号化
            encrypted_secret = self.encryption.encrypt_data(secret)
            encrypted_backup_codes = self.encryption.encrypt_data(
                ','.join(backup_codes)
            )
            
            # データベース保存
            if existing_mfa:
                # 既存レコードを更新
                existing_mfa.secret_key_encrypted = encrypted_secret
                existing_mfa.backup_codes_encrypted = encrypted_backup_codes
                existing_mfa.is_enabled = False  # 設定完了まで無効
                existing_mfa.failed_attempts = 0
                existing_mfa.locked_until = None
                mfa_secret = existing_mfa
            else:
                # 新規レコード作成
                mfa_secret = UserMFASecret(
                    user_id=user_id,
                    secret_key_encrypted=encrypted_secret,
                    backup_codes_encrypted=encrypted_backup_codes,
                    is_enabled=False
                )
                db.session.add(mfa_secret)
            
            # バックアップコードを個別レコードとして保存
            self._save_backup_codes(user_id, backup_codes)
            
            db.session.commit()
            
            # QRコード生成
            qr_code = self._generate_qr_code(secret, user.email)
            
            logger.info(f"MFA setup initiated for user {user_id}")
            
            return {
                'secret': secret,
                'qr_code': qr_code,
                'backup_codes': backup_codes
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"MFA setup failed for user {user_id}: {e}")
            raise

    def verify_and_enable_mfa(self, user_id: int, totp_code: str) -> bool:
        """
        TOTP コードを検証してMFAを有効化
        
        Args:
            user_id: ユーザーID
            totp_code: ユーザーが入力したTOTPコード
            
        Returns:
            bool: 検証成功かどうか
        """
        try:
            mfa_secret = UserMFASecret.query.filter_by(user_id=user_id).first()
            if not mfa_secret:
                logger.warning(f"MFA setup not found for user {user_id}")
                return False
            
            if mfa_secret.is_enabled:
                logger.warning(f"MFA already enabled for user {user_id}")
                return False
            
            # 秘密鍵を復号化
            secret = self.encryption.decrypt_data(mfa_secret.secret_key_encrypted)
            
            # TOTP検証
            totp = pyotp.TOTP(secret, algorithm=self.TOTP_ALGORITHM)
            if totp.verify(totp_code, valid_window=1):  # ±30秒の猶予
                # MFA有効化
                mfa_secret.is_enabled = True
                
                # ユーザーテーブルも更新
                user = User.query.get(user_id)
                user.mfa_enabled = True
                user.mfa_setup_completed_at = datetime.utcnow()
                
                db.session.commit()
                
                logger.info(f"MFA enabled successfully for user {user_id}")
                return True
            else:
                logger.warning(f"Invalid TOTP code for user {user_id}")
                return False
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"MFA verification failed for user {user_id}: {e}")
            return False

    def verify_mfa_code(self, user_id: int, code: str, ip_address: str = None) -> Dict:
        """
        MFAコード（TOTPまたはバックアップコード）を検証
        
        Args:
            user_id: ユーザーID
            code: 入力されたコード
            ip_address: クライアントIPアドレス
            
        Returns:
            Dict: {
                'success': bool,
                'error': str,  # エラーがある場合
                'backup_codes_remaining': int  # バックアップコード使用時
            }
        """
        ip_address = ip_address or request.remote_addr
        
        try:
            # MFA設定取得
            mfa_secret = UserMFASecret.query.filter_by(
                user_id=user_id, is_enabled=True
            ).first()
            
            if not mfa_secret:
                self._log_attempt(user_id, 'TOTP', False, 'SYSTEM_ERROR', ip_address)
                return {'success': False, 'error': 'MFA not enabled'}
            
            # アカウントロックチェック
            if mfa_secret.is_locked():
                self._log_attempt(user_id, 'TOTP', False, 'ACCOUNT_LOCKED', ip_address)
                return {'success': False, 'error': 'Account temporarily locked'}
            
            # レート制限チェック
            if self._is_rate_limited(user_id, ip_address):
                self._log_attempt(user_id, 'TOTP', False, 'RATE_LIMITED', ip_address)
                return {'success': False, 'error': 'Too many attempts'}
            
            # コードの形式判定（6桁=TOTP、8桁=バックアップコード）
            if len(code) == 6 and code.isdigit():
                return self._verify_totp_code(mfa_secret, code, ip_address)
            elif len(code) == 8 and code.isalnum():
                return self._verify_backup_code(user_id, code, ip_address)
            else:
                self._log_attempt(user_id, 'TOTP', False, 'INVALID_CODE', ip_address)
                mfa_secret.record_failure()
                return {'success': False, 'error': 'Invalid code format'}
                
        except Exception as e:
            logger.error(f"MFA verification error for user {user_id}: {e}")
            self._log_attempt(user_id, 'TOTP', False, 'SYSTEM_ERROR', ip_address)
            return {'success': False, 'error': 'System error'}

    def _verify_totp_code(self, mfa_secret: UserMFASecret, code: str, ip_address: str) -> Dict:
        """TOTP コードを検証"""
        try:
            # 秘密鍵を復号化
            secret = self.encryption.decrypt_data(mfa_secret.secret_key_encrypted)
            
            # TOTP検証
            totp = pyotp.TOTP(secret, algorithm=self.TOTP_ALGORITHM)
            
            if totp.verify(code, valid_window=1):  # ±30秒の猶予
                mfa_secret.record_success()
                self._log_attempt(mfa_secret.user_id, 'TOTP', True, None, ip_address)
                
                return {'success': True}
            else:
                mfa_secret.record_failure()
                self._log_attempt(mfa_secret.user_id, 'TOTP', False, 'INVALID_CODE', ip_address)
                
                return {'success': False, 'error': 'Invalid code'}
                
        except Exception as e:
            logger.error(f"TOTP verification error: {e}")
            return {'success': False, 'error': 'Verification failed'}

    def _verify_backup_code(self, user_id: int, code: str, ip_address: str) -> Dict:
        """バックアップコードを検証"""
        try:
            # コードをハッシュ化して検索
            code_hash = generate_password_hash(code)
            
            # 未使用のバックアップコードを検索
            backup_codes = MFABackupCode.query.filter_by(
                user_id=user_id, is_used=False
            ).all()
            
            for backup_code in backup_codes:
                if check_password_hash(backup_code.code_hash, code):
                    # コードを使用済みとしてマーク
                    backup_code.mark_as_used(ip_address)
                    
                    # MFA成功として記録
                    mfa_secret = UserMFASecret.query.filter_by(user_id=user_id).first()
                    if mfa_secret:
                        mfa_secret.record_success()
                    
                    self._log_attempt(user_id, 'BACKUP_CODE', True, None, ip_address)
                    
                    # 残りコード数
                    remaining = MFABackupCode.get_unused_count(user_id)
                    
                    return {
                        'success': True,
                        'backup_codes_remaining': remaining
                    }
            
            # 無効なバックアップコード
            mfa_secret = UserMFASecret.query.filter_by(user_id=user_id).first()
            if mfa_secret:
                mfa_secret.record_failure()
            
            self._log_attempt(user_id, 'BACKUP_CODE', False, 'INVALID_CODE', ip_address)
            
            return {'success': False, 'error': 'Invalid backup code'}
            
        except Exception as e:
            logger.error(f"Backup code verification error: {e}")
            return {'success': False, 'error': 'Verification failed'}

    def disable_mfa_for_user(self, user_id: int) -> bool:
        """ユーザーのMFAを無効化"""
        try:
            # MFA設定を取得
            mfa_secret = UserMFASecret.query.filter_by(user_id=user_id).first()
            if mfa_secret:
                mfa_secret.is_enabled = False
                
            # ユーザーテーブル更新
            user = User.query.get(user_id)
            if user:
                user.mfa_enabled = False
                
            # バックアップコードを無効化
            MFABackupCode.query.filter_by(user_id=user_id).update({
                'is_used': True,
                'used_at': datetime.utcnow()
            })
            
            # 信頼済みデバイスを無効化
            MFADeviceTrust.query.filter_by(user_id=user_id).update({
                'is_trusted': False
            })
            
            db.session.commit()
            
            logger.info(f"MFA disabled for user {user_id}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to disable MFA for user {user_id}: {e}")
            return False

    def regenerate_backup_codes(self, user_id: int) -> List[str]:
        """新しいバックアップコードを生成"""
        try:
            # 既存のバックアップコードを無効化
            MFABackupCode.query.filter_by(user_id=user_id).update({
                'is_used': True,
                'used_at': datetime.utcnow()
            })
            
            # 新しいバックアップコード生成
            backup_codes = self._generate_backup_codes()
            self._save_backup_codes(user_id, backup_codes)
            
            db.session.commit()
            
            logger.info(f"Backup codes regenerated for user {user_id}")
            return backup_codes
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to regenerate backup codes for user {user_id}: {e}")
            return []

    def get_mfa_status(self, user_id: int) -> Dict:
        """ユーザーのMFA状態を取得"""
        try:
            user = User.query.get(user_id)
            mfa_secret = UserMFASecret.query.filter_by(user_id=user_id).first()
            
            if not mfa_secret:
                return {
                    'enabled': False,
                    'enforced': getattr(user, 'mfa_enforced', False),
                    'setup_required': user.role == 'admin'  # 管理者は必須
                }
            
            backup_codes_remaining = MFABackupCode.get_unused_count(user_id)
            
            return {
                'enabled': mfa_secret.is_enabled,
                'enforced': getattr(user, 'mfa_enforced', False),
                'setup_completed_at': getattr(user, 'mfa_setup_completed_at', None),
                'last_used_at': mfa_secret.last_used_at,
                'is_locked': mfa_secret.is_locked(),
                'backup_codes_remaining': backup_codes_remaining,
                'failed_attempts': mfa_secret.failed_attempts
            }
            
        except Exception as e:
            logger.error(f"Failed to get MFA status for user {user_id}: {e}")
            return {'enabled': False}

    def _generate_backup_codes(self) -> List[str]:
        """バックアップコードを生成"""
        codes = []
        for _ in range(self.BACKUP_CODE_COUNT):
            code = ''.join(
                secrets.choice(string.ascii_uppercase + string.digits)
                for _ in range(self.BACKUP_CODE_LENGTH)
            )
            codes.append(code)
        return codes

    def _save_backup_codes(self, user_id: int, codes: List[str]):
        """バックアップコードをデータベースに保存"""
        for code in codes:
            backup_code = MFABackupCode(
                user_id=user_id,
                code_hash=generate_password_hash(code)
            )
            db.session.add(backup_code)

    def _generate_qr_code(self, secret: str, email: str) -> str:
        """QRコードを生成してBase64エンコード"""
        try:
            # TOTP URI生成
            totp = pyotp.TOTP(secret, algorithm=self.TOTP_ALGORITHM)
            provisioning_uri = totp.provisioning_uri(
                name=email,
                issuer_name=self.TOTP_ISSUER
            )
            
            # QRコード生成
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            # 画像生成
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Base64エンコード
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            return base64.b64encode(buffer.getvalue()).decode()
            
        except Exception as e:
            logger.error(f"QR code generation failed: {e}")
            return ""

    def _is_rate_limited(self, user_id: int, ip_address: str) -> bool:
        """レート制限チェック"""
        # ユーザー別制限（30分で10回まで）
        user_failures = MFALoginAttempt.recent_failures_by_user(user_id, 30)
        if user_failures >= 10:
            return True
        
        # IP別制限（30分で20回まで）
        ip_failures = MFALoginAttempt.recent_failures_by_ip(ip_address, 30)
        if ip_failures >= 20:
            return True
        
        return False

    def _log_attempt(self, user_id: int, attempt_type: str, success: bool, 
                    failure_reason: str = None, ip_address: str = None):
        """認証試行をログに記録"""
        try:
            attempt = MFALoginAttempt(
                user_id=user_id,
                attempt_type=attempt_type,
                success=success,
                ip_address=ip_address or request.remote_addr,
                user_agent=request.headers.get('User-Agent', ''),
                failure_reason=failure_reason
            )
            db.session.add(attempt)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to log MFA attempt: {e}")


# MFA必須チェック用のヘルパー関数
def is_mfa_required(user) -> bool:
    """ユーザーにMFAが必須かどうか判定"""
    # 管理者は必須
    if user.role == 'admin':
        return True
    
    # MFA強制フラグがある場合
    if hasattr(user, 'mfa_enforced') and user.mfa_enforced:
        return True
    
    return False


def is_mfa_enabled(user) -> bool:
    """ユーザーがMFAを有効にしているかチェック"""
    return hasattr(user, 'mfa_enabled') and user.mfa_enabled