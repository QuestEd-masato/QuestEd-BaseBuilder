# app/student/utils.py
"""Student Blueprint共通機能とユーティリティ"""

import imghdr
import os
from functools import wraps

from flask import current_app, flash, redirect, url_for
from flask_login import current_user

# 定数定義
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def student_required(f):
    """学生権限を要求するデコレータ"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "student":
            flash("この機能は学生のみ利用可能です。")
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


def allowed_file(filename):
    """許可されたファイル拡張子かチェック"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_image(stream):
    """画像ファイルの妥当性をチェック"""
    header = stream.read(512)
    stream.seek(0)
    format = imghdr.what(None, header)
    if not format:
        return None
    return "." + format if format in ALLOWED_EXTENSIONS else None


def secure_filename_with_uuid(filename):
    """UUIDを使用したセキュアなファイル名生成"""
    import uuid

    from werkzeug.utils import secure_filename

    if filename and allowed_file(filename):
        ext = filename.rsplit(".", 1)[1].lower()
        return f"{uuid.uuid4().hex}.{ext}"
    return None


def get_upload_path():
    """アップロードパスを取得"""
    upload_folder = current_app.config.get("UPLOAD_FOLDER", "static/uploads")
    return os.path.join(current_app.root_path, upload_folder)


def validate_file_size(file):
    """ファイルサイズをチェック"""
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    return size <= MAX_FILE_SIZE


def get_current_student_classes():
    """現在の学生が所属するクラス一覧を取得"""
    from app.models import ClassEnrollment

    enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
    return [enrollment.class_obj for enrollment in enrollments]


def check_class_access(class_id):
    """学生がクラスにアクセス権限があるかチェック"""
    from app.models import ClassEnrollment

    enrollment = ClassEnrollment.query.filter_by(
        class_id=class_id, student_id=current_user.id
    ).first()
    return enrollment is not None


def format_activity_content(content, max_length=100):
    """活動内容を表示用にフォーマット"""
    if not content:
        return ""

    if len(content) <= max_length:
        return content

    return content[:max_length] + "..."


def calculate_completion_rate(completed, total):
    """完了率を計算"""
    if total == 0:
        return 0
    return round((completed / total) * 100, 1)


def get_student_theme_status():
    """学生のテーマ選択状況を取得"""
    from app.models import InquiryTheme

    selected_theme = InquiryTheme.query.filter_by(
        student_id=current_user.id, is_selected=True
    ).first()

    return {
        "has_selected_theme": selected_theme is not None,
        "selected_theme": selected_theme,
    }


def get_student_survey_status():
    """学生のアンケート完了状況を取得"""
    from app.models import InterestSurvey, PersonalitySurvey

    interest_survey = InterestSurvey.query.filter_by(student_id=current_user.id).first()
    personality_survey = PersonalitySurvey.query.filter_by(
        student_id=current_user.id
    ).first()

    return {
        "interest_completed": interest_survey is not None,
        "personality_completed": personality_survey is not None,
        "all_completed": interest_survey is not None and personality_survey is not None,
    }
