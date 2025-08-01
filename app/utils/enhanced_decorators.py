# app/utils/enhanced_decorators.py
"""
Enhanced Security Decorators
セキュリティ強化デコレーター

既存のデコレーターにセキュリティ機能を追加:
- MFA認証チェック
- リソース所有権チェック
- 監査ログ記録
- レート制限
"""

import logging
from functools import wraps
from typing import Optional

from flask import request
from flask_login import current_user

from app.utils.decorators import admin_required, login_required, teacher_required
from app.utils.mfa_decorators import mfa_required, admin_mfa_required
from app.utils.resource_ownership import (
    resource_ownership_required,
    log_access_attempt,
)

logger = logging.getLogger(__name__)


def secure_admin_required(func):
    """
    管理者権限 + MFA認証が必要なデコレーター
    重要な管理機能用
    """
    @wraps(func)
    @login_required
    @admin_required
    @admin_mfa_required
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    return wrapper


def secure_teacher_required(mfa_required_flag: bool = False):
    """
    教師権限 + オプションMFA認証デコレーター
    
    Args:
        mfa_required_flag: MFA認証を必須とするか
    """
    def decorator(func):
        @wraps(func)
        @login_required
        @teacher_required
        def wrapper(*args, **kwargs):
            # MFA必須の場合
            if mfa_required_flag:
                from app.utils.mfa_decorators import mfa_required as mfa_check
                if not mfa_check(allow_trusted_device=True)(lambda: True)():
                    from flask import redirect, url_for
                    return redirect(url_for('mfa.verify'))
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def secure_student_access(resource_type: str, id_param: str = 'id'):
    """
    学生用セキュアアクセスデコレーター
    自分のリソースのみアクセス可能
    
    Args:
        resource_type: リソースタイプ
        id_param: リソースIDパラメーター名
    """
    def decorator(func):
        @wraps(func)
        @login_required
        @resource_ownership_required(resource_type, id_param, 'read')
        def wrapper(*args, **kwargs):
            # アクセスログを記録
            resource_id = kwargs.get(id_param) or request.view_args.get(id_param)
            log_access_attempt(resource_type, resource_id, 'read', True)
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def secure_data_modification(resource_type: str, id_param: str = 'id', mfa_required_flag: bool = False):
    """
    データ変更用セキュアデコレーター
    所有権チェック + オプションMFA認証
    
    Args:
        resource_type: リソースタイプ
        id_param: リソースIDパラメーター名
        mfa_required_flag: MFA認証を必須とするか
    """
    def decorator(func):
        @wraps(func)
        @login_required
        @resource_ownership_required(resource_type, id_param, 'write')
        def wrapper(*args, **kwargs):
            # MFA必須の場合（重要な操作）
            if mfa_required_flag:
                from app.utils.mfa_decorators import sensitive_operation_mfa
                return sensitive_operation_mfa(func)(*args, **kwargs)
            
            # アクセスログを記録
            resource_id = kwargs.get(id_param) or request.view_args.get(id_param)
            log_access_attempt(resource_type, resource_id, 'write', True)
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def audit_log_access(resource_type: str, action: str = 'access'):
    """
    監査ログ記録デコレーター
    重要なアクセスを記録
    
    Args:
        resource_type: リソースタイプ
        action: アクション
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # アクセス前ログ
                user_info = f"{current_user.id}({current_user.role})" if current_user.is_authenticated else "Anonymous"
                logger.info(f"AUDIT: {action} {resource_type} by {user_info} from {request.remote_addr}")
                
                # 関数実行
                result = func(*args, **kwargs)
                
                # 成功ログ
                logger.info(f"AUDIT: {action} {resource_type} completed successfully")
                
                return result
                
            except Exception as e:
                # エラーログ
                logger.error(f"AUDIT: {action} {resource_type} failed: {str(e)}")
                raise
        
        return wrapper
    
    return decorator


def rate_limited_access(limit: str = "10 per minute"):
    """
    レート制限付きアクセスデコレーター
    
    Args:
        limit: レート制限（例: "10 per minute"）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from app.utils.rate_limiting import user_based_limit
            return user_based_limit(limit)(func)(*args, **kwargs)
        
        return wrapper
    
    return decorator


# 統合セキュリティデコレーター

def maximum_security(resource_type: str, id_param: str = 'id'):
    """
    最大セキュリティデコレーター
    - ログイン必須
    - リソース所有権チェック
    - MFA認証必須
    - 監査ログ記録
    - レート制限
    """
    def decorator(func):
        @wraps(func)
        @login_required
        @mfa_required(allow_trusted_device=False)  # 信頼済みデバイス無効
        @resource_ownership_required(resource_type, id_param, 'write')
        @audit_log_access(resource_type, 'critical_access')
        @rate_limited_access("5 per minute")
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def standard_security(resource_type: str, id_param: str = 'id', action: str = 'read'):
    """
    標準セキュリティデコレーター
    - ログイン必須
    - リソース所有権チェック
    - アクセスログ記録
    """
    def decorator(func):
        @wraps(func)
        @login_required
        @resource_ownership_required(resource_type, id_param, action)
        def wrapper(*args, **kwargs):
            # アクセスログを記録
            resource_id = kwargs.get(id_param) or request.view_args.get(id_param)
            log_access_attempt(resource_type, resource_id, action, True)
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# 使用例をコメントで記載

"""
使用例:

# 管理者の重要な操作（MFA必須）
@app.route('/admin/users/<int:id>/delete', methods=['POST'])
@secure_admin_required
def delete_user(id):
    pass

# 教師のクラス管理（MFA推奨）
@app.route('/teacher/class/<int:class_id>/students')
@secure_teacher_required(mfa_required_flag=True)
def view_class_students(class_id):
    pass

# 学生の個人データアクセス
@app.route('/student/profile/<int:id>')
@secure_student_access('user', 'id')
def view_student_profile(id):
    pass

# データ変更操作（MFA必須）
@app.route('/student/goal/<int:id>/edit', methods=['POST'])
@secure_data_modification('goal', 'id', mfa_required_flag=True)
def edit_goal(id):
    pass

# 最大セキュリティが必要な操作
@app.route('/admin/system/config', methods=['POST'])
@maximum_security('system_config')
def update_system_config():
    pass

# 標準的な読み取り操作
@app.route('/student/activity/<int:id>')
@standard_security('activity_log', 'id', 'read')
def view_activity(id):
    pass
"""