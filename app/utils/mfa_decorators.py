# app/utils/mfa_decorators.py
"""
Multi-Factor Authentication Decorators
MFA認証用デコレーター

機能:
- MFA必須ページの保護
- MFA設定済みユーザーのチェック
- 信頼済みデバイスの管理
- セキュリティ監査ログ
"""

import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional

from flask import abort, flash, redirect, request, session, url_for
from flask_login import current_user

from app.auth.mfa import MFAService, is_mfa_enabled, is_mfa_required
from app.models.mfa_models import MFADeviceTrust
from app.models import db

logger = logging.getLogger(__name__)


def mfa_required(allow_trusted_device: bool = True, trust_duration_days: int = 30):
    """
    MFA認証を必須とするデコレーター
    
    Args:
        allow_trusted_device: 信頼済みデバイスでのスキップを許可するか
        trust_duration_days: デバイス信頼期間（日数）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # ログインチェック
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            # MFAが必須でない場合はスキップ
            if not is_mfa_required(current_user):
                return func(*args, **kwargs)
            
            # MFAが有効でない場合は設定画面へ
            if not is_mfa_enabled(current_user):
                flash('多要素認証の設定が必要です。', 'warning')
                return redirect(url_for('mfa.setup'))
            
            # 信頼済みデバイスチェック
            if allow_trusted_device and _is_trusted_device(current_user.id):
                # 信頼期間を延長
                _extend_device_trust(current_user.id)
                return func(*args, **kwargs)
            
            # MFA検証チェック
            if not _is_mfa_verified_in_session():
                # セッションにリダイレクト先を保存
                session['mfa_redirect_url'] = request.url
                flash('多要素認証が必要です。', 'info')
                return redirect(url_for('mfa.verify'))
            
            # MFA検証の有効期限チェック（30分）
            if not _is_mfa_verification_valid():
                session.pop('mfa_verified_at', None)
                session['mfa_redirect_url'] = request.url
                flash('多要素認証の有効期限が切れました。再度認証してください。', 'info')
                return redirect(url_for('mfa.verify'))
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def mfa_setup_required(func):
    """
    MFA設定が必須の場合に設定画面へリダイレクトするデコレーター
    管理者など、MFA必須ユーザー用
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        # MFAが必須かつ未設定の場合
        if is_mfa_required(current_user) and not is_mfa_enabled(current_user):
            flash('管理者アカウントには多要素認証の設定が必須です。', 'error')
            return redirect(url_for('mfa.setup'))
        
        return func(*args, **kwargs)
    
    return wrapper


def admin_mfa_required(func):
    """
    管理者専用：MFA必須デコレーター
    管理者の重要な操作に使用
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        if current_user.role != 'admin':
            abort(403)
        
        # 管理者は常にMFA必須
        if not is_mfa_enabled(current_user):
            flash('管理者機能を使用するには多要素認証の設定が必要です。', 'error')
            return redirect(url_for('mfa.setup'))
        
        # 信頼済みデバイス機能は無効（管理者は毎回認証）
        if not _is_mfa_verified_in_session() or not _is_mfa_verification_valid(strict=True):
            session.pop('mfa_verified_at', None)
            session['mfa_redirect_url'] = request.url
            flash('管理者機能には多要素認証が必要です。', 'warning')
            return redirect(url_for('mfa.verify'))
        
        return func(*args, **kwargs)
    
    return wrapper


def sensitive_operation_mfa(func):
    """
    機密操作用MFAデコレーター
    パスワード変更、設定変更など重要な操作用
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        # MFAが有効な場合のみチェック
        if is_mfa_enabled(current_user):
            # 機密操作は15分以内の認証が必要
            if not _is_mfa_verification_valid(max_age_minutes=15):
                session.pop('mfa_verified_at', None)
                session['mfa_redirect_url'] = request.url
                flash('この操作には最近の多要素認証が必要です。', 'warning')
                return redirect(url_for('mfa.verify'))
        
        return func(*args, **kwargs)
    
    return wrapper


def _is_mfa_verified_in_session() -> bool:
    """セッションでMFA認証済みかチェック"""
    return (
        'mfa_verified' in session and 
        session['mfa_verified'] and
        'mfa_verified_at' in session and
        'mfa_user_id' in session and
        session['mfa_user_id'] == current_user.id
    )


def _is_mfa_verification_valid(max_age_minutes: int = 30, strict: bool = False) -> bool:
    """
    MFA認証の有効性チェック
    
    Args:
        max_age_minutes: 有効期限（分）
        strict: 厳格モード（管理者用、デバイス信頼無効）
    """
    if not _is_mfa_verified_in_session():
        return False
    
    try:
        verified_at = datetime.fromisoformat(session['mfa_verified_at'])
        age = datetime.utcnow() - verified_at
        
        # 厳格モードの場合は短い有効期限
        if strict:
            max_age_minutes = min(max_age_minutes, 15)
        
        return age < timedelta(minutes=max_age_minutes)
    
    except (ValueError, KeyError):
        return False


def _is_trusted_device(user_id: int) -> bool:
    """信頼済みデバイスかチェック"""
    try:
        device_fingerprint = _generate_device_fingerprint()
        
        trusted_device = MFADeviceTrust.query.filter_by(
            user_id=user_id,
            device_fingerprint=device_fingerprint,
            is_trusted=True
        ).first()
        
        return trusted_device and trusted_device.is_valid()
    
    except Exception as e:
        logger.error(f"Device trust check failed: {e}")
        return False


def _extend_device_trust(user_id: int, days: int = 30):
    """デバイス信頼期間を延長"""
    try:
        device_fingerprint = _generate_device_fingerprint()
        
        trusted_device = MFADeviceTrust.query.filter_by(
            user_id=user_id,
            device_fingerprint=device_fingerprint
        ).first()
        
        if trusted_device:
            trusted_device.extend_trust(days)
    
    except Exception as e:
        logger.error(f"Device trust extension failed: {e}")


def _generate_device_fingerprint() -> str:
    """デバイスフィンガープリント生成"""
    import hashlib
    
    # ブラウザ情報を組み合わせてハッシュ化
    components = [
        request.headers.get('User-Agent', ''),
        request.headers.get('Accept-Language', ''),
        request.headers.get('Accept-Encoding', ''),
        request.remote_addr,  # IPアドレスも含める
    ]
    
    fingerprint_data = '|'.join(components)
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()


def mark_mfa_verified(user_id: int, trust_device: bool = False):
    """
    MFA認証完了をセッションにマーク
    
    Args:
        user_id: ユーザーID
        trust_device: デバイスを信頼済みとしてマークするか
    """
    session['mfa_verified'] = True
    session['mfa_verified_at'] = datetime.utcnow().isoformat()
    session['mfa_user_id'] = user_id
    
    # デバイス信頼設定
    if trust_device:
        try:
            device_fingerprint = _generate_device_fingerprint()
            
            # 既存の信頼済みデバイスをチェック
            existing_trust = MFADeviceTrust.query.filter_by(
                user_id=user_id,
                device_fingerprint=device_fingerprint
            ).first()
            
            if existing_trust:
                existing_trust.extend_trust()
            else:
                # 新規信頼済みデバイス登録
                new_trust = MFADeviceTrust(
                    user_id=user_id,
                    device_fingerprint=device_fingerprint,
                    trust_expires_at=datetime.utcnow() + timedelta(days=30),
                    last_ip=request.remote_addr
                )
                db.session.add(new_trust)
                db.session.commit()
                
        except Exception as e:
            logger.error(f"Device trust setup failed: {e}")


def clear_mfa_verification():
    """MFA認証状態をクリア"""
    session.pop('mfa_verified', None)
    session.pop('mfa_verified_at', None)
    session.pop('mfa_user_id', None)
    session.pop('mfa_redirect_url', None)


# セッション管理用ヘルパー関数
def get_mfa_redirect_url() -> Optional[str]:
    """MFA認証後のリダイレクト先URL取得"""
    return session.pop('mfa_redirect_url', None)