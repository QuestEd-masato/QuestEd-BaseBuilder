# app/teacher/modules/curriculum_management.py
"""カリキュラム管理機能"""

import csv
import io
import json
import logging
from datetime import datetime

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app.ai import generate_curriculum_with_ai
from app.models import (
    Class,
    Curriculum,
    CurriculumUnit,
    MainTheme,
    ProblemCategory,
    Subject,
    User,
    db,
)
from app.services.curriculum_bridge_service import CurriculumBridgeService

from ..common import teacher_required

# レッスンシステムモデル（エラー保護）
try:
    from app.modules.lesson_system.models.lesson_models import (
        CurriculumLesson, LessonTask, StudentLessonProgress, StudentTaskCheck,
        LessonType, TaskCheckStatus
    )
except ImportError:
    CurriculumLesson = None
    LessonTask = None
    StudentLessonProgress = None
    StudentTaskCheck = None
    LessonType = None
    TaskCheckStatus = None

curriculum_management_bp = Blueprint("teacher_curriculum_management", __name__)


@curriculum_management_bp.route("/class/<int:class_id>/curriculums")
@login_required
@teacher_required
def view_curriculums(class_id):
    """カリキュラム一覧"""
    class_obj = Class.query.get_or_404(class_id)

    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash("このクラスのカリキュラムを表示する権限がありません。")
        return redirect(url_for("teacher_class_management.classes"))

    curriculums = Curriculum.query.filter_by(
        class_id=class_id, teacher_id=current_user.id
    ).all()

    # 各カリキュラムの変換状況を取得
    curriculum_stats = []
    for curriculum in curriculums:
        conversion_status = CurriculumBridgeService.get_conversion_status(curriculum.id)
        curriculum_stats.append(
            {
                "curriculum": curriculum,
                "is_converted": conversion_status.get("is_converted", False),
                "converted_units": conversion_status.get("converted_units", 0),
                "conversion_date": conversion_status.get("conversion_date"),
            }
        )

    return render_template(
        "curriculums.html",
        class_obj=class_obj,
        curriculums=curriculums,
        curriculum_stats=curriculum_stats,
    )


@curriculum_management_bp.route("/class/<int:class_id>/curriculum/create")
@login_required
@teacher_required
def create_curriculum_form(class_id):
    """カリキュラム作成フォーム"""
    class_obj = Class.query.get_or_404(class_id)

    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash("このクラスのカリキュラムを作成する権限がありません。")
        return redirect(url_for("teacher_class_management.classes"))

    # メインテーマを取得
    main_themes = MainTheme.query.filter_by(class_id=class_id).all()

    # 教科情報を取得
    subjects = Subject.query.filter_by(is_active=True).all()

    return render_template(
        "create_curriculum.html",
        class_obj=class_obj,
        main_themes=main_themes,
        subjects=subjects,
    )


@curriculum_management_bp.route(
    "/class/<int:class_id>/curriculum/generate", methods=["POST"]
)
@login_required
@teacher_required
def generate_curriculum(class_id):
    """AIによるカリキュラム生成"""
    try:
        class_obj = Class.query.get_or_404(class_id)
        # 権限チェック
        if class_obj.teacher_id != current_user.id:
            return jsonify({"error": "権限がありません"}), 403

        # フォームデータとJSONデータの両方に対応
        if request.is_json:
            data = request.get_json()
        else:
            # 通常のフォームデータの場合
            data = {
                "title": request.form.get("title", ""),
                "description": request.form.get("description", ""),
                "main_theme_id": request.form.get("main_theme_id", ""),
                "total_classes": int(request.form.get("total_classes", 35)),
                "total_hours": float(request.form.get("total_hours", 29.2)),
                "difficulty_level": int(request.form.get("difficulty_level", 2)),
                "mastery_threshold": int(request.form.get("mastery_threshold", 80)),
                "self_paced_mode": request.form.get("self_paced_mode", "flexible"),
                "prerequisite_skills": request.form.get("prerequisite_skills", ""),
                "has_fieldwork": request.form.get("has_fieldwork") == "on",
                "fieldwork_count": int(request.form.get("fieldwork_count", 0))
                if request.form.get("has_fieldwork")
                else 0,
                "has_presentation": request.form.get("has_presentation") == "on",
                "presentation_format": request.form.get(
                    "presentation_format", "プレゼンテーション"
                ),
                "group_work_level": request.form.get("group_work_level", "ハイブリッド"),
                "external_collaboration": request.form.get("external_collaboration")
                == "on",
                # 新タスクシステムのフォームデータ追加（既存システムに影響なし）
                "include_detailed_tasks": request.form.get("include_detailed_tasks") == "on",
                "default_task_types": request.form.getlist("default_task_types") if request.form.get("include_detailed_tasks") else [],
                "submission_formats": request.form.getlist("submission_formats") if request.form.get("include_detailed_tasks") else [],
                "tasks_per_week": int(request.form.get("tasks_per_week", 3)) if request.form.get("include_detailed_tasks") else 3,
                "task_difficulty_distribution": request.form.get("task_difficulty_distribution", "mixed") if request.form.get("include_detailed_tasks") else "mixed",
                "auto_generate_rubrics": request.form.get("auto_generate_rubrics") == "on",
                "enable_auto_approval": request.form.get("enable_auto_approval") == "on",
                "ai_generate_tasks": request.form.get("ai_generate_tasks") == "on",
                "task_generation_prompt": request.form.get("task_generation_prompt", "") if request.form.get("include_detailed_tasks") else "",
            }

        if not data or not data.get("title"):
            return jsonify({"error": "タイトルは必須です"}), 400

        # AIでカリキュラムを生成（課題設定に応じて関数選択）
        try:
            # 新タスクシステムが有効かつ詳細課題設計が要求された場合
            if (current_app.config.get('TASK_SYSTEM_ENABLED', False) and 
                data.get('include_detailed_tasks', False)):
                
                # 新しい課題統合カリキュラム生成を使用
                from app.ai.task_curriculum_helpers import generate_curriculum_with_tasks
                
                # クラス詳細情報の準備
                class_details = {
                    'name': class_obj.name,
                    'main_theme': '',
                    'main_theme_description': ''
                }
                
                # メインテーマ情報の取得
                if data.get('main_theme_id'):
                    main_theme = MainTheme.query.get(data['main_theme_id'])
                    if main_theme:
                        class_details['main_theme'] = main_theme.title
                        class_details['main_theme_description'] = main_theme.description or ''
                
                # カリキュラム設定の準備
                curriculum_settings = {
                    'total_hours': data.get('total_hours', 29.2),
                    'has_fieldwork': data.get('has_fieldwork', False),
                    'fieldwork_count': data.get('fieldwork_count', 0),
                    'has_presentation': data.get('has_presentation', True),
                    'presentation_format': data.get('presentation_format', 'プレゼンテーション'),
                    'group_work_level': data.get('group_work_level', 'ハイブリッド'),
                    'external_collaboration': data.get('external_collaboration', False)
                }
                
                # 課題設定の準備
                task_settings = {
                    'include_detailed_tasks': True,
                    'default_task_types': data.get('default_task_types', ['worksheet', 'report']),
                    'submission_formats': data.get('submission_formats', ['document']),
                    'tasks_per_week': data.get('tasks_per_week', 3),
                    'task_difficulty_distribution': data.get('task_difficulty_distribution', 'mixed'),
                    'auto_generate_rubrics': data.get('auto_generate_rubrics', False),
                    'enable_auto_approval': data.get('enable_auto_approval', False),
                    'ai_generate_tasks': data.get('ai_generate_tasks', True),
                    'task_generation_prompt': data.get('task_generation_prompt', '')
                }
                
                # 課題統合カリキュラムを生成
                raw_curriculum_data = generate_curriculum_with_tasks(
                    class_details, curriculum_settings, task_settings
                )
                
                # 既存形式に変換
                curriculum_content = {
                    "title": data.get("title"),
                    "description": data.get("description", f"{class_obj.name}のカリキュラム"),
                    "content": json.dumps(raw_curriculum_data, ensure_ascii=False),
                    "format": "json"
                }
                
            else:
                # 既存のカリキュラム生成を使用（従来通り）
                curriculum_content = generate_curriculum_with_ai(data)
                
        except Exception as ai_error:
            current_app.logger.error(f"AI generation error: {str(ai_error)}")
            # フォールバック
            curriculum_content = {
                "title": data.get("title"),
                "description": f"{class_obj.name}のカリキュラム",
                "content": "1. 基礎学習\n2. 応用学習\n3. 発展学習",
                "format": "json",
            }

        # カリキュラムを保存
        new_curriculum = Curriculum(
            class_id=class_id,
            title=curriculum_content.get("title", data.get("title")),
            description=curriculum_content.get(
                "description", data.get("description", "")
            ),
            content=curriculum_content.get("content", ""),
            format=curriculum_content.get("format", "text"),
            teacher_id=current_user.id,
            subject_id=class_obj.subject_id,
            total_hours=data.get("total_hours", 29.2),
            has_fieldwork=data.get("has_fieldwork", False),
            fieldwork_count=data.get("fieldwork_count", 0),
            has_presentation=data.get("has_presentation", True),
            presentation_format=data.get("presentation_format", "プレゼンテーション"),
            group_work_level=data.get("group_work_level", "ハイブリッド"),
            external_collaboration=data.get("external_collaboration", False),
        )
        # 新しいフィールドを追加データとして保存（課題設定含む）
        curriculum_metadata = {
            "total_classes": data.get("total_classes", 35),
            "difficulty_level": data.get("difficulty_level", 2),
            "mastery_threshold": data.get("mastery_threshold", 80),
            "self_paced_mode": data.get("self_paced_mode", "flexible"),
            "prerequisite_skills": data.get("prerequisite_skills", ""),
            "main_theme_id": data.get("main_theme_id", ""),
            # 新タスクシステム設定の保存（既存システムに影響なし）
            "task_system_settings": {
                "include_detailed_tasks": data.get("include_detailed_tasks", False),
                "default_task_types": data.get("default_task_types", []),
                "submission_formats": data.get("submission_formats", []),
                "tasks_per_week": data.get("tasks_per_week", 3),
                "task_difficulty_distribution": data.get("task_difficulty_distribution", "mixed"),
                "auto_generate_rubrics": data.get("auto_generate_rubrics", False),
                "enable_auto_approval": data.get("enable_auto_approval", False),
                "ai_generate_tasks": data.get("ai_generate_tasks", True),
                "task_generation_prompt": data.get("task_generation_prompt", "")
            } if data.get("include_detailed_tasks", False) else {}
        }

        # メタデータをcurriculum_dataフィールドに保存
        existing_data = {}
        if curriculum_content.get("content"):
            try:
                existing_data = (
                    json.loads(curriculum_content["content"])
                    if isinstance(curriculum_content["content"], str)
                    else curriculum_content["content"]
                )
            except (json.JSONDecodeError, TypeError):
                existing_data = {}

        # メタデータを結合
        existing_data.update(curriculum_metadata)
        new_curriculum.curriculum_data = json.dumps(existing_data, ensure_ascii=False)

        db.session.add(new_curriculum)
        db.session.commit()

        # フォームからのリクエストの場合はリダイレクト
        if not request.is_json:
            flash("カリキュラムが作成されました。", "success")
            return redirect(
                url_for(
                    "teacher_curriculum_management.view_curriculums", class_id=class_id
                )
            )

        # JSONリクエストの場合
        # 結果返却
        lesson_count = 0
        try:
            if curriculum_content.get("format") == "lesson_based":
                content_json = json.loads(curriculum_content.get("content", "{}"))
                lesson_count = len(content_json.get('lessons', []))
        except:
            pass
            
        return jsonify(
            {
                "success": True,
                "curriculum_id": new_curriculum.id,
                "lesson_count": lesson_count,
                "message": f"レッスン形式カリキュラムが作成されました。({lesson_count}レッスン)",
                "redirect": url_for(
                    "teacher_curriculum_management.edit_curriculum_lessons",  # 2025-07-11: 直接レッスン編集にリダイレクト
                    curriculum_id=new_curriculum.id,
                ) if curriculum_content.get("format") == "lesson_based" else url_for(
                    "teacher_curriculum_management.view_curriculums", class_id=class_id
                ),
            }
        )

    except Exception as e:
        current_app.logger.error(f"Curriculum generation error: {str(e)}")
        db.session.rollback()

        if not request.is_json:
            flash("カリキュラムの生成に失敗しました。", "error")
            return redirect(
                url_for(
                    "teacher_curriculum_management.create_curriculum_form",
                    class_id=class_id,
                )
            )

        return jsonify({"error": "カリキュラムの生成に失敗しました", "details": str(e)}), 500


@curriculum_management_bp.route("/curriculum/<int:curriculum_id>")
@login_required
@teacher_required
def view_curriculum(curriculum_id):
    """カリキュラム詳細表示"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)

    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        flash("このカリキュラムを表示する権限がありません。")
        return redirect(url_for("teacher_class_management.classes"))

    # レッスンが存在する場合は、レッスン編集画面にリダイレクト
    if CurriculumLesson is not None:
        lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum_id).all()
    else:
        lessons = []
    if lessons:
        return redirect(url_for("teacher_curriculum_management.edit_curriculum_lessons", curriculum_id=curriculum_id))

    # 変換状況を取得
    conversion_status = CurriculumBridgeService.get_conversion_status(curriculum_id)

    # 関連する単元を取得
    converted_units = []
    if conversion_status.get("is_converted", False):
        converted_units = CurriculumUnit.query.filter_by(
            legacy_curriculum_id=curriculum_id, is_active=True
        ).all()

    # クラス情報を取得
    class_obj = Class.query.get_or_404(curriculum.class_id)

    # カリキュラムデータを解析
    curriculum_data = {}
    error_occurred = False
    if curriculum.content:
        try:
            # フォーマットをチェックしてパース方法を決定
            if curriculum.format == "json":
                curriculum_data = json.loads(curriculum.content)
            elif curriculum.format == "table":
                # テーブル形式（タブ区切り）の場合はそのまま保持
                curriculum_data = {"raw_content": curriculum.content, "format": "table"}
            else:
                # テキスト形式または未定義の場合
                # JSONとしてパースを試行
                try:
                    curriculum_data = json.loads(curriculum.content)
                except json.JSONDecodeError:
                    # JSONパースに失敗した場合はテキストとして扱う
                    curriculum_data = {"raw_content": curriculum.content, "format": "text"}
        except json.JSONDecodeError:
            current_app.logger.warning(f"Invalid JSON in curriculum {curriculum_id}")
            curriculum_data = {"raw_content": curriculum.content, "format": "text"}
            error_occurred = True

    return render_template(
        "curriculum_unified.html",
        curriculum=curriculum,
        class_obj=class_obj,
        curriculum_data=curriculum_data,
        error_occurred=error_occurred,
        conversion_status=conversion_status,
        converted_units=converted_units,
        problem_categories=[],
        text_sets=[],
        completion_percentage=0,
    )


@curriculum_management_bp.route(
    "/curriculum/<int:curriculum_id>/edit", methods=["GET", "POST"]
)
@login_required
@teacher_required
def edit_curriculum(curriculum_id):
    """カリキュラム編集"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)

    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        flash("このカリキュラムを編集する権限がありません。")
        return redirect(url_for("teacher_class_management.classes"))

    if request.method == "POST":
        try:
            curriculum.title = request.form.get("title", curriculum.title)
            curriculum.description = request.form.get(
                "description", curriculum.description
            )
            curriculum.content = request.form.get("content", curriculum.content)

            # フォーマットの処理
            format_type = request.form.get("format", "table")

            if format_type == "json":
                try:
                    # JSON形式の検証
                    json.loads(curriculum.content)
                    curriculum.format = "json"
                except json.JSONDecodeError:
                    flash("無効なJSON形式です。", "error")
                    class_obj = Class.query.get_or_404(curriculum.class_id)
                    return render_template(
                        "curriculum_unified.html",
                        curriculum=curriculum,
                        class_obj=class_obj,
                        curriculum_data={},
                        error_occurred=False,
                        problem_categories=[],
                        text_sets=[],
                        completion_percentage=0,
                    )
            elif format_type == "table":
                # テーブル形式として保存
                curriculum.format = "table"
            else:
                curriculum.format = "text"

            curriculum.updated_at = datetime.utcnow()
            db.session.commit()

            flash("カリキュラムが更新されました。", "success")
            return redirect(
                url_for(
                    "teacher_curriculum_management.view_curriculum",
                    curriculum_id=curriculum_id,
                )
            )

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Curriculum update error: {str(e)}")
            flash("カリキュラムの更新に失敗しました。", "error")

    # クラス情報を取得
    class_obj = Class.query.get_or_404(curriculum.class_id)

    # カリキュラムデータを解析
    curriculum_data = {}
    if curriculum.content:
        try:
            # フォーマットをチェックしてパース方法を決定
            if curriculum.format == "json":
                curriculum_data = json.loads(curriculum.content)
            elif curriculum.format == "table":
                # テーブル形式（タブ区切り）の場合はそのまま保持
                curriculum_data = {"raw_content": curriculum.content, "format": "table"}
            else:
                # テキスト形式または未定義の場合
                try:
                    curriculum_data = json.loads(curriculum.content)
                except json.JSONDecodeError:
                    curriculum_data = {"raw_content": curriculum.content, "format": "text"}
        except json.JSONDecodeError:
            current_app.logger.warning(f"Invalid JSON in curriculum {curriculum_id}")
            curriculum_data = {"raw_content": curriculum.content, "format": "text"}

    return render_template(
        "curriculum_unified.html",
        curriculum=curriculum,
        class_obj=class_obj,
        curriculum_data=curriculum_data,
        error_occurred=False,
        problem_categories=[],
        text_sets=[],
        completion_percentage=0,
    )


@curriculum_management_bp.route("/curriculum/<int:curriculum_id>/delete")
@login_required
@teacher_required
def delete_curriculum(curriculum_id):
    """カリキュラム削除"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)

    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        flash("このカリキュラムを削除する権限がありません。")
        return redirect(url_for("teacher_class_management.classes"))

    class_id = curriculum.class_id

    try:
        # 関連する変換済み単元も削除
        converted_units = CurriculumUnit.query.filter_by(
            legacy_curriculum_id=curriculum_id
        ).all()
        for unit in converted_units:
            db.session.delete(unit)

        db.session.delete(curriculum)
        db.session.commit()

        flash("カリキュラムが削除されました。", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Curriculum deletion error: {str(e)}")
        flash("カリキュラムの削除に失敗しました。", "error")

    return redirect(
        url_for("teacher_curriculum_management.view_curriculums", class_id=class_id)
    )


@curriculum_management_bp.route("/curriculum/<int:curriculum_id>/export")
@login_required
@teacher_required
def export_curriculum(curriculum_id):
    """カリキュラムエクスポート"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)

    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        flash("このカリキュラムをエクスポートする権限がありません。")
        return redirect(url_for("teacher_class_management.classes"))

    try:
        # エクスポートデータを準備
        export_data = {
            "title": curriculum.title,
            "description": curriculum.description,
            "content": curriculum.content,
            "format": curriculum.format,
            "created_at": curriculum.created_at.isoformat()
            if curriculum.created_at
            else None,
            "updated_at": curriculum.updated_at.isoformat()
            if curriculum.updated_at
            else None,
        }

        # JSONファイルとしてダウンロード
        response = Response(
            json.dumps(export_data, ensure_ascii=False, indent=2),
            mimetype="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=curriculum_{curriculum_id}.json"
            },
        )

        return response

    except Exception as e:
        current_app.logger.error(f"Curriculum export error: {str(e)}")
        flash("カリキュラムのエクスポートに失敗しました。", "error")
        return redirect(
            url_for(
                "teacher_curriculum_management.view_curriculum",
                curriculum_id=curriculum_id,
            )
        )


@curriculum_management_bp.route(
    "/class/<int:class_id>/curriculum/import", methods=["GET", "POST"]
)
@login_required
@teacher_required
def import_curriculum(class_id):
    """カリキュラムインポート"""
    class_obj = Class.query.get_or_404(class_id)

    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash("このクラスにカリキュラムをインポートする権限がありません。")
        return redirect(url_for("teacher_class_management.classes"))

    if request.method == "POST":
        if "file" not in request.files:
            flash("ファイルが選択されていません。")
            return render_template("import_curriculum.html", class_obj=class_obj)

        file = request.files["file"]
        if file.filename == "":
            flash("ファイルが選択されていません。")
            return render_template("import_curriculum.html", class_obj=class_obj)

        try:
            # JSONファイルを読み込み
            file_content = file.read().decode("utf-8")
            curriculum_data = json.loads(file_content)

            # 必須フィールドの確認
            required_fields = ["title", "content"]
            for field in required_fields:
                if field not in curriculum_data:
                    flash(f'必須フィールド "{field}" がありません。', "error")
                    return render_template(
                        "import_curriculum.html", class_obj=class_obj
                    )

            # カリキュラムを作成
            new_curriculum = Curriculum(
                class_id=class_id,
                title=curriculum_data["title"],
                description=curriculum_data.get("description", ""),
                content=curriculum_data["content"],
                format=curriculum_data.get("format", "text"),
                teacher_id=current_user.id,
                subject_id=class_obj.subject_id,
            )

            db.session.add(new_curriculum)
            db.session.commit()

            flash("カリキュラムがインポートされました。", "success")
            return redirect(
                url_for(
                    "teacher_curriculum_management.view_curriculums", class_id=class_id
                )
            )

        except json.JSONDecodeError:
            flash("無効なJSONファイルです。", "error")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Curriculum import error: {str(e)}")
            flash("カリキュラムのインポートに失敗しました。", "error")

    return render_template("import_curriculum.html", class_obj=class_obj)


@curriculum_management_bp.route("/download_curriculum_template")
@login_required
@teacher_required
def download_curriculum_template():
    """カリキュラムテンプレートダウンロード"""
    template_data = {
        "title": "サンプルカリキュラム",
        "description": "カリキュラムの説明",
        "content": "1. 導入\n2. 展開\n3. まとめ",
        "format": "text",
    }

    response = Response(
        json.dumps(template_data, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={
            "Content-Disposition": "attachment; filename=curriculum_template.json"
        },
    )

    return response


@curriculum_management_bp.route("/curriculum/<int:curriculum_id>/convert")
@login_required
@teacher_required
def convert_curriculum_to_units(curriculum_id):
    """カリキュラムを単元に変換"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)

    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        flash("このカリキュラムを変換する権限がありません。")
        return redirect(url_for("teacher_class_management.classes"))

    try:
        # CurriculumBridgeServiceを使用して変換
        result = CurriculumBridgeService.convert_curriculum_to_units(
            curriculum_id=curriculum_id, created_by=current_user.id
        )

        if result["success"]:
            flash(f'カリキュラムが{result["units_created"]}個の単元に変換されました。', "success")
        else:
            flash(f'変換に失敗しました: {result["error"]}', "error")

    except Exception as e:
        current_app.logger.error(f"Curriculum conversion error: {str(e)}")
        flash("カリキュラムの変換中にエラーが発生しました。", "error")

    return redirect(
        url_for(
            "teacher_curriculum_management.view_curriculum", curriculum_id=curriculum_id
        )
    )


@curriculum_management_bp.route("/curriculum/<int:curriculum_id>/units")
@login_required
@teacher_required
def view_converted_units(curriculum_id):
    """変換済み単元一覧"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)

    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        flash("この情報を表示する権限がありません。")
        return redirect(url_for("teacher_class_management.classes"))

    # 変換済み単元を取得
    converted_units = (
        CurriculumUnit.query.filter_by(
            legacy_curriculum_id=curriculum_id, is_active=True
        )
        .order_by(CurriculumUnit.order_index)
        .all()
    )

    return render_template(
        "converted_units.html", curriculum=curriculum, converted_units=converted_units
    )


@curriculum_management_bp.route("/unit/<int:unit_id>/edit", methods=["GET", "POST"])
@login_required
@teacher_required
def edit_unit(unit_id):
    """単元編集"""
    unit = CurriculumUnit.query.get_or_404(unit_id)

    # 権限チェック
    if unit.created_by != current_user.id:
        flash("この単元を編集する権限がありません。")
        return redirect(url_for("teacher_class_management.classes"))

    if request.method == "POST":
        try:
            unit.title = request.form.get("title", unit.title)
            unit.description = request.form.get("description", unit.description)
            unit.learning_objectives = request.form.get(
                "learning_objectives", unit.learning_objectives
            )
            unit.difficulty_level = int(
                request.form.get("difficulty_level", unit.difficulty_level)
            )
            unit.estimated_minutes = int(
                request.form.get("estimated_minutes", unit.estimated_minutes or 0)
            )

            # タグの処理（JSON形式）
            tags_input = request.form.get("tags", "")
            if tags_input:
                tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
                unit.tags = json.dumps(tags)
            else:
                unit.tags = None

            unit.updated_at = datetime.utcnow()
            db.session.commit()

            flash("単元が更新されました。", "success")
            return redirect(
                url_for(
                    "teacher_curriculum_management.view_converted_units",
                    curriculum_id=unit.legacy_curriculum_id,
                )
            )

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Unit update error: {str(e)}")
            flash("単元の更新に失敗しました。", "error")

    return render_template("edit_unit.html", unit=unit)


@curriculum_management_bp.route("/unit/<int:unit_id>/delete")
@login_required
@teacher_required
def delete_unit(unit_id):
    """単元削除"""
    unit = CurriculumUnit.query.get_or_404(unit_id)

    # 権限チェック
    if unit.created_by != current_user.id:
        flash("この単元を削除する権限がありません。")
        return redirect(url_for("teacher_class_management.classes"))

    curriculum_id = unit.legacy_curriculum_id

    try:
        # 単元を非アクティブに設定（完全削除ではなく）
        unit.is_active = False
        unit.updated_at = datetime.utcnow()
        db.session.commit()

        flash("単元が削除されました。", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unit deletion error: {str(e)}")
        flash("単元の削除に失敗しました。", "error")

    return redirect(
        url_for(
            "teacher_curriculum_management.view_converted_units",
            curriculum_id=curriculum_id,
        )
    )


# Main Theme Management Routes
@curriculum_management_bp.route("/class/<int:class_id>/main_themes")
@login_required
@teacher_required
def view_main_themes(class_id):
    """大テーマ一覧表示"""
    class_obj = Class.query.get_or_404(class_id)

    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash("このクラスの大テーマを表示する権限がありません。")
        return redirect(url_for("teacher_class_management.classes"))

    main_themes = MainTheme.query.filter_by(class_id=class_id).all()

    return render_template(
        "view_main_themes.html", class_obj=class_obj, main_themes=main_themes
    )


@curriculum_management_bp.route(
    "/class/<int:class_id>/main_theme/create", methods=["GET", "POST"]
)
@login_required
@teacher_required
def create_main_theme(class_id):
    """大テーマ作成"""
    class_obj = Class.query.get_or_404(class_id)

    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash("このクラスの大テーマを作成する権限がありません。")
        return redirect(url_for("teacher_class_management.classes"))

    if request.method == "POST":
        try:
            title = request.form.get("title")
            description = request.form.get("description")

            if not title:
                flash("タイトルは必須です。", "error")
                return render_template("create_main_theme.html", class_obj=class_obj)

            main_theme = MainTheme(
                title=title,
                description=description,
                class_id=class_id,
                teacher_id=current_user.id,
                created_at=datetime.utcnow(),
            )

            db.session.add(main_theme)
            db.session.commit()

            flash("大テーマが作成されました。", "success")
            return redirect(
                url_for(
                    "teacher_curriculum_management.view_main_themes", class_id=class_id
                )
            )

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Main theme creation error: {str(e)}")
            flash("大テーマの作成に失敗しました。", "error")

    return render_template("create_main_theme.html", class_obj=class_obj)


@curriculum_management_bp.route(
    "/main_theme/<int:theme_id>/edit", methods=["GET", "POST"]
)
@login_required
@teacher_required
def edit_main_theme(theme_id):
    """大テーマ編集"""
    main_theme = MainTheme.query.get_or_404(theme_id)

    # 権限チェック
    if main_theme.teacher_id != current_user.id:
        flash("この大テーマを編集する権限がありません。")
        return redirect(url_for("teacher_class_management.classes"))

    if request.method == "POST":
        try:
            title = request.form.get("title")
            description = request.form.get("description")

            if not title:
                flash("タイトルは必須です。", "error")
                return render_template("edit_main_theme.html", main_theme=main_theme)

            main_theme.title = title
            main_theme.description = description
            main_theme.updated_at = datetime.utcnow()

            db.session.commit()

            flash("大テーマが更新されました。", "success")
            return redirect(
                url_for(
                    "teacher_curriculum_management.view_main_themes",
                    class_id=main_theme.class_id,
                )
            )

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Main theme update error: {str(e)}")
            flash("大テーマの更新に失敗しました。", "error")

    return render_template("edit_main_theme.html", main_theme=main_theme)


@curriculum_management_bp.route("/main_theme/<int:theme_id>/delete")
@login_required
@teacher_required
def delete_main_theme(theme_id):
    """大テーマ削除"""
    main_theme = MainTheme.query.get_or_404(theme_id)

    # 権限チェック
    if main_theme.teacher_id != current_user.id:
        flash("この大テーマを削除する権限がありません。")
        return redirect(url_for("teacher_class_management.classes"))

    class_id = main_theme.class_id

    try:
        db.session.delete(main_theme)
        db.session.commit()

        flash("大テーマが削除されました。", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Main theme deletion error: {str(e)}")
        flash("大テーマの削除に失敗しました。", "error")

    return redirect(
        url_for("teacher_curriculum_management.view_main_themes", class_id=class_id)
    )


# ============================================
# レッスン形式カリキュラム編集機能
# ============================================

@curriculum_management_bp.route("/curriculum/<int:curriculum_id>/lessons")
@login_required
@teacher_required
def edit_curriculum_lessons(curriculum_id):
    """カリキュラムのレッスン形式編集画面"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        flash("このカリキュラムを編集する権限がありません。", "error")
        return redirect(url_for("teacher_class_management.classes"))
    
    # クラス情報取得
    class_obj = Class.query.get_or_404(curriculum.class_id)
    
    # 既存レッスン取得
    lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum_id)\
        .order_by(CurriculumLesson.lesson_number).all()
    
    # 各レッスンのタスクも取得し、タスク数を事前に計算
    for lesson in lessons:
        lesson_tasks = LessonTask.query.filter_by(lesson_id=lesson.id)\
            .order_by(LessonTask.task_number).all()
        lesson.tasks_list = lesson_tasks  # リストとして明示的に保存
        lesson.tasks_count = len(lesson_tasks)  # タスク数を事前計算
    
    return render_template(
        "teacher/curriculum_lesson_editor.html",
        curriculum=curriculum,
        class_obj=class_obj,
        lessons=lessons
    )


@curriculum_management_bp.route("/curriculum/<int:curriculum_id>/lessons/save", methods=["POST"])
@login_required
@teacher_required
def save_curriculum_lessons(curriculum_id):
    """カリキュラムレッスン保存"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        return jsonify({"success": False, "message": "権限がありません"}), 403
    
    try:
        # 既存のレッスンとタスクを削除
        existing_lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum_id).all()
        for lesson in existing_lessons:
            # タスクも一緒に削除される（cascade設定済み）
            db.session.delete(lesson)
        
        # 新しいレッスンデータを処理
        lessons_data = []
        form_data = request.form.to_dict(flat=False)
        
        # フォームデータを解析してレッスンデータを構築
        lesson_indices = set()
        for key in form_data.keys():
            if key.startswith('lessons[') and '][title]' in key:
                # lessons[0][title] から 0 を抽出
                import re
                match = re.search(r'lessons\[(\d+)\]', key)
                if match:
                    lesson_indices.add(int(match.group(1)))
        
        for lesson_index in sorted(lesson_indices):
            lesson_data = {
                'lesson_number': lesson_index + 1,
                'title': form_data.get(f'lessons[{lesson_index}][title]', [''])[0],
                'type': form_data.get(f'lessons[{lesson_index}][type]', ['lecture'])[0],
                'duration': int(form_data.get(f'lessons[{lesson_index}][duration]', ['50'])[0]),
                'description': form_data.get(f'lessons[{lesson_index}][description]', [''])[0],
                'tasks': []
            }
            
            # タスクデータを収集
            task_indices = set()
            for key in form_data.keys():
                if key.startswith(f'lessons[{lesson_index}][tasks][') and '][title]' in key:
                    match = re.search(f'lessons\\[{lesson_index}\\]\\[tasks\\]\\[(\\d+)\\]', key)
                    if match:
                        task_indices.add(int(match.group(1)))
            
            for task_index in sorted(task_indices):
                task_title = form_data.get(f'lessons[{lesson_index}][tasks][{task_index}][title]', [''])[0]
                task_description = form_data.get(f'lessons[{lesson_index}][tasks][{task_index}][description]', [''])[0]
                
                if task_title.strip():  # 空でないタスクのみ追加
                    lesson_data['tasks'].append({
                        'task_number': task_index + 1,
                        'title': task_title,
                        'description': task_description
                    })
            
            lessons_data.append(lesson_data)
        
        # データベースに保存
        for lesson_data in lessons_data:
            # レッスン作成
            lesson = CurriculumLesson(
                curriculum_id=curriculum_id,
                lesson_number=lesson_data['lesson_number'],
                title=lesson_data['title'],
                description=lesson_data['description'],
                lesson_type=LessonType(lesson_data['type']),
                duration_minutes=lesson_data['duration'],
                created_by=current_user.id
            )
            db.session.add(lesson)
            db.session.flush()  # IDを取得するため
            
            # タスク作成
            for task_data in lesson_data['tasks']:
                task = LessonTask(
                    lesson_id=lesson.id,
                    task_number=task_data['task_number'],
                    title=task_data['title'],
                    description=task_data['description']
                )
                db.session.add(task)
        
        db.session.commit()
        flash("カリキュラムレッスンが保存されました。", "success")
        
        return redirect(url_for(
            "teacher_curriculum_management.edit_curriculum_lessons",
            curriculum_id=curriculum_id
        ))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Curriculum lessons save error: {str(e)}")
        flash("カリキュラムレッスンの保存に失敗しました。", "error")
        
        return redirect(url_for(
            "teacher_curriculum_management.edit_curriculum_lessons",
            curriculum_id=curriculum_id
        ))


@curriculum_management_bp.route("/curriculum/<int:curriculum_id>/update-info", methods=["POST"])
@login_required
@teacher_required
def update_curriculum_info(curriculum_id):
    """カリキュラム基本情報更新"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        return jsonify({"success": False, "message": "権限がありません"}), 403
    
    try:
        data = request.get_json()
        
        # タイトルと説明を更新
        curriculum.title = data.get('title', curriculum.title)
        curriculum.description = data.get('description', curriculum.description)
        curriculum.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": "カリキュラム情報が更新されました",
            "curriculum": {
                "id": curriculum.id,
                "title": curriculum.title,
                "description": curriculum.description
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Curriculum info update error: {str(e)}")
        return jsonify({"success": False, "message": "更新に失敗しました"}), 500


@curriculum_management_bp.route("/curriculum/<int:curriculum_id>/lessons/api", methods=["GET"])
@login_required
@teacher_required
def get_curriculum_lessons_api(curriculum_id):
    """カリキュラムレッスンAPI取得"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        return jsonify({"success": False, "message": "権限がありません"}), 403
    
    # レッスン取得
    lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum_id)\
        .order_by(CurriculumLesson.lesson_number).all()
    
    lessons_data = []
    for lesson in lessons:
        # タスク取得
        tasks = LessonTask.query.filter_by(lesson_id=lesson.id)\
            .order_by(LessonTask.task_number).all()
        
        lesson_dict = lesson.to_dict()
        lesson_dict['tasks'] = [task.to_dict() for task in tasks]
        lessons_data.append(lesson_dict)
    
    return jsonify({
        "success": True,
        "curriculum": {
            "id": curriculum.id,
            "title": curriculum.title,
            "description": curriculum.description
        },
        "lessons": lessons_data
    })
