# app/student/modules/themes.py
"""学生探究テーマ機能"""

from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app.models import Class, ClassEnrollment, InquiryTheme, MainTheme, db

from ..utils import student_required

themes_bp = Blueprint("student_themes", __name__)


@themes_bp.route("/themes")
@login_required
@student_required
def themes():
    """探究テーマ一覧とクラス選択"""
    try:
        # 学生が履修しているクラスを取得
        enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
        classes = [enrollment.class_obj for enrollment in enrollments]

        if not classes:
            flash("履修しているクラスがありません。")
            return redirect(url_for("student_dashboard.dashboard"))

        # URLパラメータからクラスIDを取得
        selected_class_id = request.args.get("class_id", type=int)
        selected_class = None

        if selected_class_id:
            # 指定されたクラスが履修クラスに含まれているかチェック
            selected_class = next(
                (c for c in classes if c.id == selected_class_id), None
            )
            if not selected_class:
                flash("指定されたクラスにアクセス権限がありません。")
                return redirect(url_for("student_themes.themes"))

        # 選択中のテーマを取得
        selected_theme = InquiryTheme.query.filter_by(
            student_id=current_user.id, is_selected=True
        ).first()

        # クラスが選択されている場合、そのクラスのメインテーマを取得
        main_themes = []
        if selected_class:
            main_themes = (
                MainTheme.query.filter_by(class_id=selected_class.id)
                .order_by(MainTheme.created_at.desc())
                .all()
            )

        # 学生の個人テーマを取得
        personal_themes = (
            InquiryTheme.query.filter_by(student_id=current_user.id)
            .order_by(InquiryTheme.created_at.desc())
            .all()
        )

        # テンプレートが期待する形式でテーマデータを構築
        themes_with_main = []
        for theme in personal_themes:
            # メインテーマ情報を取得
            main_theme = None
            if theme.main_theme_id:
                main_theme = MainTheme.query.get(theme.main_theme_id)

            themes_with_main.append({"theme": theme, "main_theme": main_theme})

        # 利用可能なメインテーマ（選択されたクラスのもの）
        available_main_themes = main_themes if selected_class else []

        # 選択されたクラスの情報
        class_obj = selected_class
        main_theme = main_themes[0] if main_themes else None

        return render_template(
            "view_themes.html",
            classes=classes,
            selected_class=selected_class,
            class_obj=class_obj,
            main_theme=main_theme,
            main_themes=main_themes,
            available_main_themes=available_main_themes,
            personal_themes=personal_themes,
            themes_with_main=themes_with_main,
            selected_theme=selected_theme,
            class_id=selected_class_id if selected_class else None,
        )

    except Exception as e:
        current_app.logger.error(f"Themes list error: {str(e)}")
        flash("テーマ一覧の読み込み中にエラーが発生しました。")
        return redirect(url_for("student_dashboard.dashboard"))


@themes_bp.route("/select_theme/<int:theme_id>")
@login_required
@student_required
def select_theme(theme_id):
    """探究テーマ選択"""
    try:
        theme = InquiryTheme.query.get_or_404(theme_id)

        # 権限チェック
        if theme.student_id != current_user.id:
            flash("このテーマを選択する権限がありません。")
            return redirect(url_for("student_themes.themes"))

        # 現在選択されているテーマの選択を解除
        current_selected = InquiryTheme.query.filter_by(
            student_id=current_user.id, is_selected=True
        ).first()

        if current_selected:
            current_selected.is_selected = False

        # 新しいテーマを選択
        theme.is_selected = True

        try:
            db.session.commit()
            flash(f"テーマ「{theme.title}」を選択しました。", "success")

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Theme selection error: {str(e)}")
            flash("テーマの選択に失敗しました。", "error")

        return redirect(url_for("student_themes.themes"))

    except Exception as e:
        current_app.logger.error(f"Select theme error: {str(e)}")
        flash("テーマ選択中にエラーが発生しました。")
        return redirect(url_for("student_themes.themes"))


@themes_bp.route("/create_personal_theme", methods=["GET", "POST"])
@login_required
@student_required
def create_personal_theme():
    """個人探究テーマ作成"""
    try:
        # 学生が履修しているクラスを取得
        enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
        classes = [enrollment.class_obj for enrollment in enrollments]

        if not classes:
            flash("履修しているクラスがありません。")
            return redirect(url_for("student_dashboard.dashboard"))

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            class_id = request.form.get("class_id", type=int)

            # 入力値検証
            if not title:
                flash("テーマタイトルを入力してください。", "error")
                return render_template("create_personal_theme.html", classes=classes)

            if not class_id or class_id not in [c.id for c in classes]:
                flash("有効なクラスを選択してください。", "error")
                return render_template("create_personal_theme.html", classes=classes)

            # 新しい個人テーマを作成
            new_theme = InquiryTheme(
                title=title,
                description=description,
                student_id=current_user.id,
                class_id=class_id,
                is_selected=False,
                created_at=datetime.utcnow(),
            )

            try:
                db.session.add(new_theme)
                db.session.commit()
                flash(f"個人テーマ「{title}」を作成しました。", "success")
                return redirect(url_for("student_themes.themes", class_id=class_id))

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Personal theme creation error: {str(e)}")
                flash("個人テーマの作成に失敗しました。", "error")

        return render_template("create_personal_theme.html", classes=classes)

    except Exception as e:
        current_app.logger.error(f"Create personal theme error: {str(e)}")
        flash("個人テーマ作成画面の読み込み中にエラーが発生しました。")
        return redirect(url_for("student_themes.themes"))


@themes_bp.route("/main_theme/<int:main_theme_id>/create_personal")
@login_required
@student_required
def create_from_main_theme(main_theme_id):
    """メインテーマから個人テーマを作成"""
    try:
        main_theme = MainTheme.query.get_or_404(main_theme_id)

        # クラス履修チェック
        enrollment = ClassEnrollment.query.filter_by(
            student_id=current_user.id, class_id=main_theme.class_id
        ).first()

        if not enrollment:
            flash("このクラスのテーマにアクセス権限がありません。")
            return redirect(url_for("student_themes.themes"))

        # メインテーマから個人テーマを作成
        personal_theme = InquiryTheme(
            title=main_theme.title,
            description=main_theme.description,
            student_id=current_user.id,
            class_id=main_theme.class_id,
            main_theme_id=main_theme.id,
            is_selected=False,
            created_at=datetime.utcnow(),
        )

        try:
            db.session.add(personal_theme)
            db.session.commit()
            flash(f"メインテーマ「{main_theme.title}」から個人テーマを作成しました。", "success")
            return redirect(
                url_for("student_themes.themes", class_id=main_theme.class_id)
            )

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Create from main theme error: {str(e)}")
            flash("個人テーマの作成に失敗しました。", "error")

        return redirect(url_for("student_themes.themes"))

    except Exception as e:
        current_app.logger.error(f"Create from main theme error: {str(e)}")
        flash("個人テーマ作成中にエラーが発生しました。")
        return redirect(url_for("student_themes.themes"))


@themes_bp.route("/theme/<int:theme_id>/edit", methods=["GET", "POST"])
@login_required
@student_required
def edit_theme(theme_id):
    """個人テーマ編集"""
    try:
        theme = InquiryTheme.query.get_or_404(theme_id)

        # 権限チェック
        if theme.student_id != current_user.id:
            flash("このテーマを編集する権限がありません。")
            return redirect(url_for("student_themes.themes"))

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()

            # 入力値検証
            if not title:
                flash("テーマタイトルを入力してください。", "error")
                return render_template("edit_theme.html", theme=theme)

            # テーマ情報を更新
            theme.title = title
            theme.description = description
            theme.updated_at = datetime.utcnow()

            try:
                db.session.commit()
                flash(f"テーマ「{title}」を更新しました。", "success")
                return redirect(
                    url_for("student_themes.themes", class_id=theme.class_id)
                )

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Theme update error: {str(e)}")
                flash("テーマの更新に失敗しました。", "error")

        return render_template("edit_theme.html", theme=theme)

    except Exception as e:
        current_app.logger.error(f"Edit theme error: {str(e)}")
        flash("テーマ編集画面の読み込み中にエラーが発生しました。")
        return redirect(url_for("student_themes.themes"))


@themes_bp.route("/theme/<int:theme_id>/delete")
@login_required
@student_required
def delete_theme(theme_id):
    """個人テーマ削除"""
    try:
        theme = InquiryTheme.query.get_or_404(theme_id)

        # 権限チェック
        if theme.student_id != current_user.id:
            flash("このテーマを削除する権限がありません。")
            return redirect(url_for("student_themes.themes"))

        class_id = theme.class_id
        theme_title = theme.title

        try:
            db.session.delete(theme)
            db.session.commit()
            flash(f"テーマ「{theme_title}」を削除しました。", "success")

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Theme deletion error: {str(e)}")
            flash("テーマの削除に失敗しました。", "error")

        return redirect(url_for("student_themes.themes", class_id=class_id))

    except Exception as e:
        current_app.logger.error(f"Delete theme error: {str(e)}")
        flash("テーマ削除中にエラーが発生しました。")
        return redirect(url_for("student_themes.themes"))


@themes_bp.route("/class/<int:class_id>/themes")
@login_required
@student_required
def class_themes(class_id):
    """特定クラスの探究テーマ表示"""
    try:
        # 権限チェック：学生が該当クラスに履修しているかを確認
        enrollment = ClassEnrollment.query.filter_by(
            student_id=current_user.id, class_id=class_id
        ).first()

        if not enrollment:
            flash("このクラスにアクセス権限がありません。")
            return redirect(url_for("student_dashboard.dashboard"))

        class_obj = Class.query.get_or_404(class_id)

        # そのクラスのメインテーマを取得
        main_themes = (
            MainTheme.query.filter_by(class_id=class_id)
            .order_by(MainTheme.created_at.desc())
            .all()
        )

        # 学生の選択中テーマを取得
        selected_theme = InquiryTheme.query.filter_by(
            student_id=current_user.id, is_selected=True
        ).first()

        # 学生の個人テーマ（このクラス関連）を取得
        personal_themes = (
            InquiryTheme.query.filter_by(student_id=current_user.id, class_id=class_id)
            .order_by(InquiryTheme.created_at.desc())
            .all()
        )

        return render_template(
            "student/class_themes.html",
            class_obj=class_obj,
            main_themes=main_themes,
            personal_themes=personal_themes,
            selected_theme=selected_theme,
        )

    except Exception as e:
        current_app.logger.error(f"Class themes error: {str(e)}")
        flash("クラステーマの読み込み中にエラーが発生しました。")
        return redirect(url_for("student_dashboard.dashboard"))
