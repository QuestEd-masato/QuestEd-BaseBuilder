"""
モデル属性の安全なアクセスヘルパー

Author: QuestEd Development Team
Created: 2025-01-15
Version: 1.0.0
"""

from typing import Optional, List
from sqlalchemy import case


def safe_get_class_id(user) -> Optional[int]:
    """
    ユーザーのクラスIDを安全に取得
    
    Args:
        user: Userモデルインスタンス
        
    Returns:
        Optional[int]: クラスID、見つからない場合はNone
    """
    if user.role == 'teacher':
        # 教師の場合は担当クラスから
        from app.models import Class
        teacher_class = Class.query.filter_by(teacher_id=user.id).first()
        return teacher_class.id if teacher_class else None
    else:
        # 生徒の場合
        if hasattr(user, 'class_id'):
            return user.class_id
        
        # enrolled_classesから取得
        if hasattr(user, 'enrolled_classes') and user.enrolled_classes:
            return user.enrolled_classes[0].id
        
        # ClassEnrollmentから取得
        from app.models import ClassEnrollment
        enrollment = ClassEnrollment.query.filter_by(student_id=user.id).first()
        return enrollment.class_id if enrollment else None


def safe_get_user_classes(user) -> List[int]:
    """
    ユーザーが関連するクラスIDのリストを安全に取得
    
    Args:
        user: Userモデルインスタンス
        
    Returns:
        List[int]: クラスIDのリスト
    """
    class_ids = []
    
    if user.role == 'teacher':
        # 教師の場合は担当クラス全て
        from app.models import Class
        teacher_classes = Class.query.filter_by(teacher_id=user.id).all()
        class_ids = [c.id for c in teacher_classes]
    else:
        # 生徒の場合は所属クラス全て
        from app.models import ClassEnrollment
        enrollments = ClassEnrollment.query.filter_by(
            student_id=user.id, 
            is_active=True
        ).all()
        class_ids = [e.class_id for e in enrollments]
    
    return class_ids


def mysql_nulls_last(column, direction='asc'):
    """
    MySQL用のNULLS LAST実装
    SQLAlchemy 2.0対応版
    
    Args:
        column: SQLAlchemyカラムオブジェクト
        direction: ソート方向 ('asc' または 'desc')
        
    Returns:
        List: MySQLでNULLS LASTを実現するためのorder_by句
    """
    if direction == 'asc':
        return [
            case((column.is_(None), 1), else_=0),  # SQLAlchemy 2.0: タプル形式
            column.asc()
        ]
    else:
        return [
            case((column.is_(None), 0), else_=1),  # SQLAlchemy 2.0: タプル形式
            column.desc()
        ]


def mysql_nulls_first(column, direction='asc'):
    """
    MySQL用のNULLS FIRST実装
    SQLAlchemy 2.0対応版
    
    Args:
        column: SQLAlchemyカラムオブジェクト
        direction: ソート方向 ('asc' または 'desc')
        
    Returns:
        List: MySQLでNULLS FIRSTを実現するためのorder_by句
    """
    if direction == 'asc':
        return [
            case((column.is_(None), 0), else_=1),  # SQLAlchemy 2.0: タプル形式
            column.asc()
        ]
    else:
        return [
            case((column.is_(None), 1), else_=0),  # SQLAlchemy 2.0: タプル形式
            column.desc()
        ]


def safe_get_model_field(model_instance, field_name: str, default=None):
    """
    モデルインスタンスのフィールドを安全に取得
    
    Args:
        model_instance: モデルインスタンス
        field_name: フィールド名
        default: デフォルト値
        
    Returns:
        フィールド値、存在しない場合はdefault
    """
    return getattr(model_instance, field_name, default)


def safe_get_relationship(model_instance, relationship_name: str, default=None):
    """
    モデルインスタンスのリレーションシップを安全に取得
    
    Args:
        model_instance: モデルインスタンス
        relationship_name: リレーションシップ名
        default: デフォルト値
        
    Returns:
        リレーションシップオブジェクト、存在しない場合はdefault
    """
    try:
        return getattr(model_instance, relationship_name, default)
    except Exception:
        return default


def safe_query_filter(query, **filters):
    """
    存在しないフィールドでのフィルタリングを安全に実行
    
    Args:
        query: SQLAlchemyクエリオブジェクト
        **filters: フィルタ条件
        
    Returns:
        フィルタ済みクエリオブジェクト
    """
    try:
        return query.filter_by(**filters)
    except Exception as e:
        # ログ出力（オプション）
        import logging
        logging.warning(f"Query filter failed: {e}")
        return query


def get_study_duration_safe(activity_log):
    """
    ActivityLogから学習時間を安全に取得
    study_durationフィールドが存在しない場合の代替案
    
    Args:
        activity_log: ActivityLogインスタンス
        
    Returns:
        int: 学習時間（分）、推定値または0
    """
    # study_durationフィールドが存在する場合
    if hasattr(activity_log, 'study_duration') and activity_log.study_duration:
        return activity_log.study_duration
    
    # 代替案1: contentの長さから推定（簡易版）
    if hasattr(activity_log, 'content') and activity_log.content:
        # 100文字につき1分と仮定（調整可能）
        estimated_minutes = max(1, len(activity_log.content) // 100)
        return min(estimated_minutes, 60)  # 最大60分
    
    # 代替案2: reflectionの長さから推定
    if hasattr(activity_log, 'reflection') and activity_log.reflection:
        estimated_minutes = max(1, len(activity_log.reflection) // 50)
        return min(estimated_minutes, 30)  # 最大30分
    
    # デフォルト: 5分
    return 5


def validate_model_fields(model_class, required_fields: List[str]) -> List[str]:
    """
    モデルクラスに必要なフィールドが存在するかチェック
    
    Args:
        model_class: SQLAlchemyモデルクラス
        required_fields: 必要なフィールド名のリスト
        
    Returns:
        List[str]: 存在しないフィールド名のリスト
    """
    missing_fields = []
    
    for field_name in required_fields:
        if not hasattr(model_class, field_name):
            missing_fields.append(field_name)
    
    return missing_fields


def get_model_fields(model_class) -> List[str]:
    """
    モデルクラスの全フィールド名を取得
    
    Args:
        model_class: SQLAlchemyモデルクラス
        
    Returns:
        List[str]: フィールド名のリスト
    """
    try:
        return [column.name for column in model_class.__table__.columns]
    except Exception:
        return []


def safe_update_model(model_instance, update_data: dict, allowed_fields: List[str] = None):
    """
    モデルインスタンスを安全に更新
    
    Args:
        model_instance: 更新対象のモデルインスタンス
        update_data: 更新データの辞書
        allowed_fields: 更新を許可するフィールドのリスト（Noneの場合は全フィールド）
        
    Returns:
        bool: 更新成功の可否
    """
    try:
        for field_name, value in update_data.items():
            # フィールド制限チェック
            if allowed_fields and field_name not in allowed_fields:
                continue
                
            # フィールド存在チェック
            if hasattr(model_instance, field_name):
                setattr(model_instance, field_name, value)
        
        return True
    except Exception as e:
        import logging
        logging.error(f"Model update failed: {e}")
        return False


def safe_order_by_with_nulls(query, column, direction='asc', nulls='last'):
    """
    安全なNULL処理付きORDER BY
    SQLAlchemy 2.0完全対応版
    
    Args:
        query: SQLAlchemyクエリオブジェクト
        column: ソート対象カラム
        direction: ソート方向 ('asc' または 'desc')
        nulls: NULL値の位置 ('last' または 'first')
        
    Returns:
        修正されたクエリオブジェクト
    """
    try:
        if nulls == 'last':
            return query.order_by(*mysql_nulls_last(column, direction))
        elif nulls == 'first':
            return query.order_by(*mysql_nulls_first(column, direction))
        else:
            # デフォルトソート
            if direction == 'asc':
                return query.order_by(column.asc())
            else:
                return query.order_by(column.desc())
    except Exception as e:
        import logging
        logging.warning(f"Order by failed, using default sort: {e}")
        return query.order_by(column.asc())


def validate_sqlalchemy_compatibility():
    """
    SQLAlchemy 2.0互換性の検証
    
    Returns:
        Dict[str, Any]: 検証結果
    """
    try:
        from sqlalchemy import __version__ as sqlalchemy_version
        from sqlalchemy import case, func
        
        # case()構文のテスト
        test_case = case((True, 1), else_=0)
        
        return {
            'sqlalchemy_version': sqlalchemy_version,
            'case_syntax_compatible': True,
            'mysql_nulls_helper_available': True,
            'status': 'compatible'
        }
    except Exception as e:
        return {
            'sqlalchemy_version': 'unknown',
            'case_syntax_compatible': False,
            'mysql_nulls_helper_available': False,
            'status': 'incompatible',
            'error': str(e)
        }