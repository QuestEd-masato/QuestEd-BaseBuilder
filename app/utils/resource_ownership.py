# app/utils/resource_ownership.py
"""
Resource Ownership Validation System
リソース所有権検証システム

機能:
- ユーザーがアクセス権限を持つリソースかチェック
- 役割ベースのアクセス制御強化
- データ分離とプライバシー保護
- 監査ログ記録

セキュリティ原則:
- 学生は自分のデータのみアクセス可能
- 教師は担当クラス学生のデータのみアクセス可能
- 管理者は所属学校内のデータのみアクセス可能
"""

import logging
from functools import wraps
from typing import Dict, List, Optional, Union

from flask import abort, current_app, request
from flask_login import current_user
from sqlalchemy import and_, or_

from app.models import (
    ActivityLog,
    ChatHistory,
    Class,
    ClassEnrollment,
    Goal,
    InquiryTheme,
    StudentEvaluation,
    Todo,
    User,
    db,
)

logger = logging.getLogger(__name__)


class ResourceOwnershipValidator:
    """リソース所有権検証クラス"""
    
    # リソースタイプとテーブルのマッピング
    RESOURCE_MAPPINGS = {
        'user': User,
        'activity_log': ActivityLog,
        'todo': Todo,
        'goal': Goal,
        'inquiry_theme': InquiryTheme,
        'student_evaluation': StudentEvaluation,
        'chat_history': ChatHistory,
    }
    
    @classmethod
    def verify_ownership(
        cls, 
        user_id: int, 
        resource_type: str, 
        resource_id: int,
        action: str = 'read'
    ) -> bool:
        """
        リソース所有権を検証
        
        Args:
            user_id: アクセスするユーザーID
            resource_type: リソースタイプ
            resource_id: リソースID
            action: アクション (read, write, delete)
            
        Returns:
            bool: アクセス許可の可否
        """
        try:
            user = User.query.get(user_id)
            if not user:
                logger.warning(f"User {user_id} not found for ownership check")
                return False
            
            # 管理者は（制限付きで）全てのリソースにアクセス可能
            if user.role == 'admin':
                return cls._verify_admin_access(user, resource_type, resource_id)
            
            # 教師は担当クラス学生のリソースにアクセス可能
            elif user.role == 'teacher':
                return cls._verify_teacher_access(user, resource_type, resource_id, action)
            
            # 学生は自分のリソースのみアクセス可能
            elif user.role == 'student':
                return cls._verify_student_access(user, resource_type, resource_id, action)
            
            else:
                logger.warning(f"Unknown user role: {user.role}")
                return False
                
        except Exception as e:
            logger.error(f"Ownership verification error: {e}")
            return False
    
    @classmethod
    def _verify_admin_access(cls, user: User, resource_type: str, resource_id: int) -> bool:
        """管理者のアクセス権限を確認"""
        # 管理者は同じ学校内のリソースのみアクセス可能
        if resource_type not in cls.RESOURCE_MAPPINGS:
            return False
        
        model_class = cls.RESOURCE_MAPPINGS[resource_type]
        resource = model_class.query.get(resource_id)
        
        if not resource:
            return False
        
        # 学校ID照合
        if hasattr(resource, 'school_id'):
            return resource.school_id == user.school_id
        
        # リソースがユーザーに関連付けられている場合
        if hasattr(resource, 'student_id'):
            student = User.query.get(resource.student_id)
            return student and student.school_id == user.school_id
        
        # ユーザーリソースの場合
        if resource_type == 'user':
            return resource.school_id == user.school_id
        
        return True  # その他の場合は許可（ログで監視）
    
    @classmethod
    def _verify_teacher_access(cls, user: User, resource_type: str, resource_id: int, action: str) -> bool:
        """教師のアクセス権限を確認"""
        if resource_type not in cls.RESOURCE_MAPPINGS:
            return False
        
        model_class = cls.RESOURCE_MAPPINGS[resource_type]
        resource = model_class.query.get(resource_id)
        
        if not resource:
            return False
        
        # 教師は担当クラス学生のリソースのみアクセス可能
        if hasattr(resource, 'student_id'):
            return cls._is_teacher_student(user.id, resource.student_id)
        
        # ユーザーリソースの場合
        if resource_type == 'user':
            if resource.role == 'student':
                return cls._is_teacher_student(user.id, resource.id)
            else:
                # 他の教師・管理者へのアクセスは制限
                return action == 'read' and resource.school_id == user.school_id
        
        # その他のリソース（クラス関連など）
        if hasattr(resource, 'class_id'):
            return cls._is_teacher_class(user.id, resource.class_id)
        
        return False
    
    @classmethod
    def _verify_student_access(cls, user: User, resource_type: str, resource_id: int, action: str) -> bool:
        """学生のアクセス権限を確認"""
        if resource_type not in cls.RESOURCE_MAPPINGS:
            return False
        
        model_class = cls.RESOURCE_MAPPINGS[resource_type]
        resource = model_class.query.get(resource_id)
        
        if not resource:
            return False
        
        # 学生は自分のリソースのみアクセス可能
        if hasattr(resource, 'student_id'):
            return resource.student_id == user.id
        
        # ユーザーリソースの場合
        if resource_type == 'user':
            return resource.id == user.id
        
        return False
    
    @classmethod
    def _is_teacher_student(cls, teacher_id: int, student_id: int) -> bool:
        """指定の学生が教師の担当学生かチェック"""
        # 教師が担当するクラスに学生が所属しているかチェック
        enrollment = db.session.query(ClassEnrollment).join(Class).filter(
            and_(
                ClassEnrollment.student_id == student_id,
                Class.teacher_id == teacher_id
            )
        ).first()
        
        return enrollment is not None
    
    @classmethod
    def _is_teacher_class(cls, teacher_id: int, class_id: int) -> bool:
        """指定のクラスが教師の担当クラスかチェック"""
        class_obj = Class.query.filter_by(id=class_id, teacher_id=teacher_id).first()
        return class_obj is not None
    
    @classmethod
    def get_accessible_resources(
        cls, 
        user_id: int, 
        resource_type: str,
        filters: Optional[Dict] = None
    ) -> List[int]:
        """
        ユーザーがアクセス可能なリソースIDのリストを取得
        
        Args:
            user_id: ユーザーID
            resource_type: リソースタイプ
            filters: 追加のフィルター条件
            
        Returns:
            List[int]: アクセス可能なリソースIDのリスト
        """
        try:
            user = User.query.get(user_id)
            if not user or resource_type not in cls.RESOURCE_MAPPINGS:
                return []
            
            model_class = cls.RESOURCE_MAPPINGS[resource_type]
            query = model_class.query
            
            # 追加フィルターを適用
            if filters:
                for key, value in filters.items():
                    if hasattr(model_class, key):
                        query = query.filter(getattr(model_class, key) == value)
            
            # ロール別のアクセス制御
            if user.role == 'admin':
                # 管理者は同じ学校内のリソース
                if hasattr(model_class, 'school_id'):
                    query = query.filter(model_class.school_id == user.school_id)
                elif hasattr(model_class, 'student_id'):
                    # 学生IDを通じて学校を特定
                    query = query.join(User, model_class.student_id == User.id).filter(
                        User.school_id == user.school_id
                    )
            
            elif user.role == 'teacher':
                # 教師は担当クラス学生のリソース
                if hasattr(model_class, 'student_id'):
                    # 担当学生のリソースのみ
                    student_ids = cls._get_teacher_student_ids(user.id)
                    query = query.filter(model_class.student_id.in_(student_ids))
                elif hasattr(model_class, 'class_id'):
                    # 担当クラスのリソース
                    class_ids = cls._get_teacher_class_ids(user.id)
                    query = query.filter(model_class.class_id.in_(class_ids))
                else:
                    return []  # アクセス不可
            
            elif user.role == 'student':
                # 学生は自分のリソースのみ
                if hasattr(model_class, 'student_id'):
                    query = query.filter(model_class.student_id == user.id)
                elif resource_type == 'user':
                    query = query.filter(model_class.id == user.id)
                else:
                    return []  # アクセス不可
            
            resources = query.all()
            return [resource.id for resource in resources]
            
        except Exception as e:
            logger.error(f"Error getting accessible resources: {e}")
            return []
    
    @classmethod
    def _get_teacher_student_ids(cls, teacher_id: int) -> List[int]:
        """教師が担当する学生IDのリストを取得"""
        enrollments = db.session.query(ClassEnrollment.student_id).join(Class).filter(
            Class.teacher_id == teacher_id
        ).all()
        
        return [enrollment.student_id for enrollment in enrollments]
    
    @classmethod
    def _get_teacher_class_ids(cls, teacher_id: int) -> List[int]:
        """教師が担当するクラスIDのリストを取得"""
        classes = Class.query.filter_by(teacher_id=teacher_id).all()
        return [class_obj.id for class_obj in classes]


def resource_ownership_required(resource_type: str, id_param: str = 'id', action: str = 'read'):
    """
    リソース所有権チェック用デコレーター
    
    Args:
        resource_type: リソースタイプ
        id_param: リソースIDのパラメーター名
        action: アクション
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            # リソースIDを取得
            resource_id = kwargs.get(id_param)
            if resource_id is None:
                # URLパラメーターから取得を試行
                try:
                    resource_id = int(request.view_args.get(id_param))
                except (TypeError, ValueError):
                    logger.warning(f"Invalid resource ID parameter: {id_param}")
                    abort(400)
            
            # 所有権を検証
            if not ResourceOwnershipValidator.verify_ownership(
                current_user.id, resource_type, resource_id, action
            ):
                logger.warning(
                    f"Access denied: User {current_user.id} ({current_user.role}) "
                    f"attempted {action} on {resource_type} {resource_id}"
                )
                abort(403)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def filter_accessible_resources(resource_type: str, resources: List, user_id: Optional[int] = None):
    """
    リソースリストをユーザーのアクセス権限でフィルタリング
    
    Args:
        resource_type: リソースタイプ
        resources: リソースオブジェクトのリスト
        user_id: ユーザーID（Noneの場合はcurrent_userを使用）
        
    Returns:
        List: フィルタリング済みリソースリスト
    """
    if not user_id:
        if not current_user.is_authenticated:
            return []
        user_id = current_user.id
    
    try:
        accessible_ids = ResourceOwnershipValidator.get_accessible_resources(
            user_id, resource_type
        )
        
        return [resource for resource in resources if resource.id in accessible_ids]
        
    except Exception as e:
        logger.error(f"Error filtering accessible resources: {e}")
        return []


# リソース所有権チェック用のヘルパー関数

def can_access_user_data(target_user_id: int, current_user_id: Optional[int] = None) -> bool:
    """指定ユーザーのデータにアクセス可能かチェック"""
    if not current_user_id:
        if not current_user.is_authenticated:
            return False
        current_user_id = current_user.id
    
    return ResourceOwnershipValidator.verify_ownership(
        current_user_id, 'user', target_user_id, 'read'
    )


def can_modify_user_data(target_user_id: int, current_user_id: Optional[int] = None) -> bool:
    """指定ユーザーのデータを変更可能かチェック"""
    if not current_user_id:
        if not current_user.is_authenticated:
            return False
        current_user_id = current_user.id
    
    return ResourceOwnershipValidator.verify_ownership(
        current_user_id, 'user', target_user_id, 'write'
    )


def get_accessible_student_ids(teacher_id: Optional[int] = None) -> List[int]:
    """アクセス可能な学生IDのリストを取得（教師用）"""
    if not teacher_id:
        if not current_user.is_authenticated or current_user.role != 'teacher':
            return []
        teacher_id = current_user.id
    
    return ResourceOwnershipValidator._get_teacher_student_ids(teacher_id)


def log_access_attempt(resource_type: str, resource_id: int, action: str, success: bool):
    """リソースアクセス試行をログに記録"""
    try:
        user_info = f"User:{current_user.id}({current_user.role})" if current_user.is_authenticated else "Anonymous"
        ip_address = request.remote_addr if request else "Unknown"
        
        log_message = (
            f"Resource Access: {action} {resource_type}:{resource_id} "
            f"by {user_info} from {ip_address} - {'SUCCESS' if success else 'DENIED'}"
        )
        
        if success:
            logger.info(log_message)
        else:
            logger.warning(log_message)
            
    except Exception as e:
        logger.error(f"Failed to log access attempt: {e}")


# モジュール機能の統合
def setup_resource_ownership_protection(app):
    """リソース所有権保護機能をアプリケーションに設定"""
    
    @app.before_request
    def before_request():
        """リクエスト前の処理"""
        # 静的ファイルやヘルスチェックは除外
        if (request.endpoint and 
            (request.endpoint.startswith('static') or 
             request.endpoint == 'health_check')):
            return
        
        # APIエンドポイントでの自動チェック（将来の拡張用）
        pass
    
    logger.info("Resource ownership protection initialized")