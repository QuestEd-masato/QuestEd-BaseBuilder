# app/student/modules/chat.py
"""学生AIチャット機能"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import func, desc

from app.models import db, ChatHistory, Class, ClassEnrollment
from ..utils import student_required

chat_bp = Blueprint('student_chat', __name__)

@chat_bp.route('/chat')
@login_required
@student_required
def chat():
    """学生用AIチャットページ"""
    try:
        # 学生が履修しているクラスを取得
        enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
        classes = [enrollment.class_obj for enrollment in enrollments]
        
        # ClassEnrollmentが空の場合、User.class_idから取得を試行
        if not classes and current_user.class_id:
            direct_class = Class.query.get(current_user.class_id)
            if direct_class:
                classes = [direct_class]
        
        # 最近のチャット履歴を取得
        recent_chats = ChatHistory.query.filter_by(
            user_id=current_user.id
        ).order_by(ChatHistory.created_at.desc()).limit(10).all()
        
        return render_template('chat.html', 
                             classes=classes,
                             recent_chats=recent_chats)
        
    except Exception as e:
        current_app.logger.error(f"Chat page error: {str(e)}")
        flash('チャットページの読み込み中にエラーが発生しました。', 'error')
        return redirect(url_for('student_dashboard.dashboard'))