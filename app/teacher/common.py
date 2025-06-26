# app/teacher/common.py
"""Teacher Blueprint共通機能"""

from flask import redirect, url_for, flash
from flask_login import current_user
from functools import wraps

def teacher_required(f):
    """教師権限を要求するデコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'teacher':
            flash('この機能は教師のみ利用可能です。')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function