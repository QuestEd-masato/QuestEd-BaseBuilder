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