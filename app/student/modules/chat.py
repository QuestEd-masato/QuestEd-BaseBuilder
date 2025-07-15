# app/student/modules/chat.py
"""学生AIチャット機能"""

from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import desc, func

from app.models import ChatHistory, Class, ClassEnrollment, db

from ..utils import student_required

chat_bp = Blueprint("student_chat", __name__)


@chat_bp.route("/chat/select")
@login_required
@student_required
def select_class():
    """AIチャット用のクラス選択画面"""
    try:
        # 学生が履修しているクラスを取得
        enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
        classes = [enrollment.class_obj for enrollment in enrollments]

        # ClassEnrollmentが空の場合、User.class_idから取得を試行
        if not classes and current_user.class_id:
            direct_class = Class.query.get(current_user.class_id)
            if direct_class:
                classes = [direct_class]

        current_app.logger.info(
            f"[CHAT] Student {current_user.id} selecting class for chat, found {len(classes)} classes"
        )

        return render_template("select_class_for_chat.html", classes=classes)

    except Exception as e:
        current_app.logger.error(f"Chat class selection error: {str(e)}")
        flash("クラス選択画面の読み込み中にエラーが発生しました。", "error")
        return redirect(url_for("student_dashboard.dashboard"))


@chat_bp.route("/chat")
@login_required
@student_required
def chat():
    """学生用AIチャットページ"""
    try:
        # URLパラメータからクラスIDを取得
        class_id = request.args.get("class_id", type=int)
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
                flash(f"クラスID {class_id} にアクセスする権限がありません。", "error")
                class_id = None

        # クラスが指定されていない場合、クラス選択画面にリダイレクト
        if not selected_class and classes:
            if len(classes) > 1:
                # 複数クラスがある場合はクラス選択画面に遷移
                return redirect(url_for("student_chat.select_class"))
            else:
                # 1つのクラスしかない場合はそのクラスを選択
                selected_class = classes[0]
                class_id = selected_class.id

        # 最近のチャット履歴を取得（クラス指定がある場合はそのクラスのみ）
        chat_query = ChatHistory.query.filter_by(user_id=current_user.id)
        if class_id:
            chat_query = chat_query.filter_by(class_id=class_id)

        recent_chats = (
            chat_query.order_by(ChatHistory.created_at.desc()).limit(10).all()
        )

        current_app.logger.info(
            f"[CHAT] Student {current_user.id} accessing chat for class {class_id}"
        )

        return render_template(
            "chat.html",
            classes=classes,
            selected_class=selected_class,
            class_id=class_id,
            recent_chats=recent_chats,
        )

    except Exception as e:
        current_app.logger.error(f"Chat page error: {str(e)}")
        flash("チャットページの読み込み中にエラーが発生しました。", "error")
        return redirect(url_for("student_dashboard.dashboard"))
