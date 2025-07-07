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
        # URLパラメータからクラスIDを取得
        class_id = request.args.get('class_id', type=int)
        selected_class = None
        
        # 学生が履修しているクラスを取得
        enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
        classes = [enrollment.class_obj for enrollment in enrollments]
        
        # ClassEnrollmentが空の場合、User.class_idから取得を試行
        if not classes and current_user.class_id:
            direct_class = Class.query.get(current_user.class_id)
            if direct_class:
                classes = [direct_class]
        
        # クラスIDが指定されている場合、該当するクラスを選択
        if class_id:
            selected_class = next((cls for cls in classes if cls.id == class_id), None)
            if not selected_class:
                # 指定されたクラスにアクセス権がない場合
                flash(f'クラスID {class_id} にアクセスする権限がありません。', 'error')
                class_id = None
        
        # クラスが指定されていない場合、最初のクラスを選択
        if not selected_class and classes:
            selected_class = classes[0]
            class_id = selected_class.id
        
        # 最近のチャット履歴を取得（クラス指定がある場合はそのクラスのみ）
        chat_query = ChatHistory.query.filter_by(user_id=current_user.id)
        if class_id:
            chat_query = chat_query.filter_by(class_id=class_id)
        
        recent_chats = chat_query.order_by(ChatHistory.created_at.desc()).limit(10).all()
        
        current_app.logger.info(f"[CHAT] Student {current_user.id} accessing chat for class {class_id}")
        
        return render_template('chat.html', 
                             classes=classes,
                             selected_class=selected_class,
                             class_id=class_id,
                             recent_chats=recent_chats)
        
    except Exception as e:
        current_app.logger.error(f"Chat page error: {str(e)}")
        flash('チャットページの読み込み中にエラーが発生しました。', 'error')
        return redirect(url_for('student_dashboard.dashboard'))