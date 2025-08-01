# app/models/mfa_models.py
"""
Multi-Factor Authentication (MFA) Models
多要素認証システム用データベースモデル

セキュリティ要件:
- Secret keyの暗号化保存
- Backup codesの安全な管理
- ブルートフォース攻撃対策
- 使用履歴の記録
"""

import json
import secrets
from datetime import datetime, timedelta
from typing import List, Optional

from extensions import db
from sqlalchemy import Index


class UserMFASecret(db.Model):
    """
    ユーザーMFA秘密鍵管理テーブル
    
    セキュリティ特性:
    - secret_key: Fernet暗号化で保存
    - backup_codes: JSON暗号化で保存
    - 使用回数制限とロック機能
    """
    
    __tablename__ = "user_mfa_secrets"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    
    # 暗号化された秘密鍵 (TOTP用)
    secret_key_encrypted = db.Column(db.Text, nullable=False)
    
    # 暗号化されたバックアップコード (JSON)
    backup_codes_encrypted = db.Column(db.Text, nullable=False)
    
    # MFA有効/無効フラグ
    is_enabled = db.Column(db.Boolean, default=False, nullable=False)
    
    # セキュリティ関連
    failed_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    last_used_at = db.Column(db.DateTime, nullable=True)
    
    # タイムスタンプ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーションシップ
    user = db.relationship("User", backref=db.backref("mfa_secret", uselist=False))
    
    # インデックス
    __table_args__ = (
        Index('idx_user_mfa_user_id', 'user_id'),
        Index('idx_user_mfa_enabled', 'is_enabled'),
    )
    
    def is_locked(self) -> bool:
        """MFAがロックされているかチェック"""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until
    
    def lock_account(self, duration_minutes: int = 30):
        """アカウントを一定時間ロック"""
        self.locked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
        db.session.commit()
    
    def unlock_account(self):
        """アカウントロックを解除"""
        self.locked_until = None
        self.failed_attempts = 0
        db.session.commit()
    
    def record_success(self):
        """認証成功を記録"""
        self.failed_attempts = 0
        self.last_used_at = datetime.utcnow()
        db.session.commit()
    
    def record_failure(self):
        """認証失敗を記録"""
        self.failed_attempts += 1
        
        # 5回失敗でロック
        if self.failed_attempts >= 5:
            self.lock_account(30)  # 30分ロック
        
        db.session.commit()


class MFABackupCode(db.Model):
    """
    MFAバックアップコード管理テーブル
    
    バックアップコードの個別管理により:
    - 使用済みコードの追跡
    - 残りコード数の管理
    - セキュリティ監査対応
    """
    
    __tablename__ = "mfa_backup_codes"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    
    # 暗号化されたコード
    code_hash = db.Column(db.String(255), nullable=False)
    
    # 使用状態
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    used_ip = db.Column(db.String(45), nullable=True)
    
    # タイムスタンプ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # リレーションシップ
    user = db.relationship("User", backref="mfa_backup_codes")
    
    # インデックス
    __table_args__ = (
        Index('idx_mfa_backup_user_id', 'user_id'),
        Index('idx_mfa_backup_used', 'is_used'),
    )
    
    @classmethod
    def get_unused_count(cls, user_id: int) -> int:
        """未使用バックアップコード数を取得"""
        return cls.query.filter_by(user_id=user_id, is_used=False).count()
    
    def mark_as_used(self, ip_address: str):
        """バックアップコードを使用済みとしてマーク"""
        self.is_used = True
        self.used_at = datetime.utcnow()
        self.used_ip = ip_address
        db.session.commit()


class MFALoginAttempt(db.Model):
    """
    MFA認証試行ログテーブル
    
    セキュリティ監査とブルートフォース攻撃検知用:
    - 全ての認証試行を記録
    - 成功/失敗パターンの分析
    - 不審なアクセスの検知
    """
    
    __tablename__ = "mfa_login_attempts"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    
    # 認証試行の詳細
    attempt_type = db.Column(db.Enum('TOTP', 'BACKUP_CODE', name='mfa_type'), nullable=False)
    success = db.Column(db.Boolean, nullable=False)
    
    # セキュリティ情報
    ip_address = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.Text, nullable=True)
    
    # 失敗理由 (成功時はNone)
    failure_reason = db.Column(db.Enum(
        'INVALID_CODE', 'EXPIRED_CODE', 'ACCOUNT_LOCKED', 
        'CODE_ALREADY_USED', 'RATE_LIMITED', 'SYSTEM_ERROR',
        name='mfa_failure_reason'
    ), nullable=True)
    
    # タイムスタンプ
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # リレーションシップ
    user = db.relationship("User", backref="mfa_login_attempts")
    
    # インデックス
    __table_args__ = (
        Index('idx_mfa_attempts_user_time', 'user_id', 'attempted_at'),
        Index('idx_mfa_attempts_ip_time', 'ip_address', 'attempted_at'),
        Index('idx_mfa_attempts_success', 'success'),
    )
    
    @classmethod
    def recent_failures_by_ip(cls, ip_address: str, minutes: int = 30) -> int:
        """指定IP からの最近の失敗試行数を取得"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        return cls.query.filter(
            cls.ip_address == ip_address,
            cls.success == False,
            cls.attempted_at >= cutoff_time
        ).count()
    
    @classmethod
    def recent_failures_by_user(cls, user_id: int, minutes: int = 30) -> int:
        """指定ユーザーの最近の失敗試行数を取得"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        return cls.query.filter(
            cls.user_id == user_id,
            cls.success == False,
            cls.attempted_at >= cutoff_time
        ).count()


class MFADeviceTrust(db.Model):
    """
    信頼済みデバイス管理テーブル
    
    ユーザビリティ向上のため:
    - 定期的にMFAをスキップ可能
    - デバイス固有の識別子管理
    - 信頼期間の管理
    """
    
    __tablename__ = "mfa_device_trust"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    
    # デバイス識別情報
    device_fingerprint = db.Column(db.String(255), nullable=False)  # ブラウザ情報のハッシュ
    device_name = db.Column(db.String(100), nullable=True)  # ユーザー指定のデバイス名
    
    # 信頼状態
    is_trusted = db.Column(db.Boolean, default=True, nullable=False)
    trust_expires_at = db.Column(db.DateTime, nullable=False)
    
    # セキュリティ情報
    last_ip = db.Column(db.String(45), nullable=False)
    last_used_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # タイムスタンプ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # リレーションシップ
    user = db.relationship("User", backref="trusted_devices")
    
    # インデックス
    __table_args__ = (
        Index('idx_device_trust_user_fingerprint', 'user_id', 'device_fingerprint'),
        Index('idx_device_trust_expires', 'trust_expires_at'),
    )
    
    def is_valid(self) -> bool:
        """信頼が有効かチェック"""
        return self.is_trusted and datetime.utcnow() < self.trust_expires_at
    
    def extend_trust(self, days: int = 30):
        """信頼期間を延長"""
        self.trust_expires_at = datetime.utcnow() + timedelta(days=days)
        self.last_used_at = datetime.utcnow()
        db.session.commit()
    
    def revoke_trust(self):
        """信頼を取り消し"""
        self.is_trusted = False
        db.session.commit()


# Users テーブルへのMFA関連カラム追加用のマイグレーション
"""
既存のusersテーブルに以下のカラムを追加:

ALTER TABLE users ADD COLUMN mfa_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN mfa_enforced BOOLEAN DEFAULT FALSE;  -- 管理者による強制
ALTER TABLE users ADD COLUMN last_mfa_verification TIMESTAMP NULL;
ALTER TABLE users ADD COLUMN mfa_setup_completed_at TIMESTAMP NULL;

-- 管理者は MFA 必須のポリシー
-- UPDATE users SET mfa_enforced = TRUE WHERE role = 'admin';
"""