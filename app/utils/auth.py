"""
認証・権限関連のユーティリティ関数

ユーザーの所属確認、権限チェックに関する共通機能を提供します。
"""

import logging
from typing import Optional, Dict, Any
from flask import current_app
from flask_login import current_user

from app.models import ClassEnrollment, Class, User


logger = logging.getLogger(__name__)


def check_student_class_access(student_id: int, class_id: int) -> bool:
    """
    生徒のクラスアクセス権限を確認
    
    Args:
        student_id: 生徒ID
        class_id: クラスID
        
    Returns:
        bool: アクセス権限があるかどうか
    """
    try:
        enrollment = ClassEnrollment.query.filter_by(
            student_id=student_id,
            class_id=class_id,
            is_active=True
        ).first()
        
        if enrollment:
            logger.debug(f"クラスアクセス権限確認OK: student_id={student_id}, class_id={class_id}")
            return True
        else:
            logger.warning(f"クラスアクセス権限なし: student_id={student_id}, class_id={class_id}")
            return False
            
    except Exception as e:
        logger.error(f"クラスアクセス権限チェックエラー: {str(e)} (student_id={student_id}, class_id={class_id})")
        return False


def check_teacher_class_access(teacher_id: int, class_id: int) -> bool:
    """
    教師のクラスアクセス権限を確認
    
    Args:
        teacher_id: 教師ID
        class_id: クラスID
        
    Returns:
        bool: アクセス権限があるかどうか
    """
    try:
        class_obj = Class.query.filter_by(
            id=class_id,
            teacher_id=teacher_id
        ).first()
        
        if class_obj:
            logger.debug(f"教師クラスアクセス権限確認OK: teacher_id={teacher_id}, class_id={class_id}")
            return True
        else:
            logger.warning(f"教師クラスアクセス権限なし: teacher_id={teacher_id}, class_id={class_id}")
            return False
            
    except Exception as e:
        logger.error(f"教師クラスアクセス権限チェックエラー: {str(e)} (teacher_id={teacher_id}, class_id={class_id})")
        return False


def get_user_classes(user_id: int, role: str) -> list:
    """
    ユーザーの所属クラス一覧を取得
    
    Args:
        user_id: ユーザーID
        role: ユーザーロール（'student' or 'teacher'）
        
    Returns:
        list: クラスのリスト
    """
    try:
        if role == 'student':
            # 生徒の場合：enrollment経由
            enrollments = ClassEnrollment.query.filter_by(
                student_id=user_id,
                is_active=True
            ).all()
            return [enrollment.class_obj for enrollment in enrollments if enrollment.class_obj]
            
        elif role == 'teacher':
            # 教師の場合：直接所有
            classes = Class.query.filter_by(teacher_id=user_id).all()
            return classes
            
        else:
            logger.warning(f"未対応のロール: {role} (user_id={user_id})")
            return []
            
    except Exception as e:
        logger.error(f"ユーザークラス取得エラー: {str(e)} (user_id={user_id}, role={role})")
        return []


def log_access_attempt(function_name: str, success: bool, **kwargs) -> None:
    """
    アクセス試行をログに記録
    
    Args:
        function_name: 関数名
        success: 成功/失敗
        **kwargs: 追加情報
    """
    user_id = current_user.id if current_user.is_authenticated else 'anonymous'
    status = 'SUCCESS' if success else 'FAILED'
    
    log_message = f"[{function_name}] アクセス{status}: user_id={user_id}"
    
    for key, value in kwargs.items():
        log_message += f", {key}={value}"
    
    if success:
        logger.info(log_message)
    else:
        logger.warning(log_message)


def require_role(required_role: str) -> bool:
    """
    現在のユーザーが指定されたロールを持つかチェック
    
    Args:
        required_role: 必要なロール
        
    Returns:
        bool: ロールを持つかどうか
    """
    if not current_user.is_authenticated:
        return False
    
    return current_user.role == required_role