"""
BaseBuilder Common Utilities
既存機能を壊さずに共通処理を抽出
"""

from functools import wraps
from flask import flash, redirect, url_for, current_app
from flask_login import current_user


def require_roles(*roles):
    """権限チェックデコレータ"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.role not in roles:
                flash('この機能へのアクセス権限がありません。')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def handle_db_error(operation_name="操作"):
    """データベースエラーハンドリングデコレータ"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                from extensions import db
                db.session.rollback()
                current_app.logger.error(f"{operation_name} error: {str(e)}")
                flash(f'{operation_name}中にエラーが発生しました。')
                return redirect(url_for('categories.categories'))
        return decorated_function
    return decorator


def get_user_statistics(user_id):
    """ユーザー統計の共通取得処理"""
    from basebuilder.models import AnswerRecord, ProficiencyRecord
    
    answer_count = AnswerRecord.query.filter_by(student_id=user_id).count()
    correct_count = AnswerRecord.query.filter_by(
        student_id=user_id, is_correct=True
    ).count()
    
    accuracy = (correct_count / answer_count * 100) if answer_count > 0 else 0
    
    proficiency_count = ProficiencyRecord.query.filter_by(
        student_id=user_id
    ).count()
    
    return {
        'answer_count': answer_count,
        'correct_count': correct_count,
        'accuracy': round(accuracy, 1),
        'proficiency_count': proficiency_count
    }


def get_category_statistics(category_id=None):
    """カテゴリ統計の共通取得処理"""
    from basebuilder.models import BasicKnowledgeItem, TextSet
    
    query_filter = {'category_id': category_id} if category_id else {}
    
    problem_count = BasicKnowledgeItem.query.filter_by(**query_filter).count()
    text_count = TextSet.query.filter_by(**query_filter).count()
    
    return {
        'problem_count': problem_count,
        'text_count': text_count
    }


def paginate_query(query, page=1, per_page=20):
    """クエリのページネーション処理"""
    try:
        page = int(page)
        if page < 1:
            page = 1
    except (ValueError, TypeError):
        page = 1
    
    return query.paginate(page=page, per_page=per_page, error_out=False)


def format_datetime(dt):
    """日時のフォーマット処理"""
    if not dt:
        return ''
    return dt.strftime('%Y年%m月%d日 %H:%M')


def validate_form_data(data, required_fields):
    """フォームデータの検証"""
    errors = []
    
    for field in required_fields:
        if field not in data or not data[field].strip():
            errors.append(f'{field}は必須項目です。')
    
    return errors


def safe_int_conversion(value, default=0):
    """安全な整数変換"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def get_user_school_filter(user):
    """ユーザーの学校に基づくフィルタ条件を取得"""
    if user.role == 'admin':
        return {}  # 管理者は全て見れる
    elif hasattr(user, 'school_id') and user.school_id:
        return {'school_id': user.school_id}
    else:
        return {'school_id': -1}  # 存在しないIDで何も表示しない


def log_activity(activity_type, details, user_id=None):
    """アクティビティログ記録"""
    try:
        user_id = user_id or current_user.id
        current_app.logger.info(
            f"Activity: {activity_type} | User: {user_id} | Details: {details}"
        )
    except Exception as e:
        current_app.logger.error(f"Failed to log activity: {str(e)}")