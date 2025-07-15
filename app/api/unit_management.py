"""
Unit Management API
==================
Phase 4.3: API分割実装 - 単元学習管理API

責任:
- 単元選択・進捗管理
- 完了申請・承認ワークフロー
- 学習進捗の一括処理
- 教師による承認管理

移行元: app/api/__init__.py の以下12ルート:
- /units/select (POST)
- /units (GET)
- /units/<int:unit_id>/progress (POST)
- /units/mappings/create (POST)
- /units/<int:unit_id>/request-completion (POST)
- /units/my-selections (GET)
- /units/completion-history (GET)
- /progress/batch-update (POST)
- /approvals/pending (GET)
- /approvals/<int:selection_id>/approve (POST)
- /approvals/<int:selection_id>/reject (POST)
- /approvals/batch-approve (POST)
- /approvals/statistics (GET)
"""

import logging
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.models import (
    Class,
    ClassEnrollment,
    ClassLearningSettings,
    CurriculumUnit,
    StudentUnitSelection,
    UnitItemMapping,
    db,
)
from app.services.unit_completion_service import UnitCompletionService
from app.utils.rate_limiting import api_limit

unit_management_bp = Blueprint("unit_management", __name__)


@unit_management_bp.route("/units/<int:unit_id>/remove", methods=["DELETE"])
@login_required
@api_limit()
def remove_unit_selection(unit_id):
    """単元選択削除API - 生徒が選択した単元を削除"""
    try:
        # 生徒のみアクセス可能
        if current_user.role != "student":
            return jsonify({"status": "error", "message": "この機能は生徒のみ利用可能です"}), 403

        # 単元選択の存在確認
        selection = StudentUnitSelection.query.filter_by(
            student_id=current_user.id, unit_id=unit_id
        ).first()

        if not selection:
            return jsonify({"status": "error", "message": "選択されていない単元です"}), 404

        # 完了済みの単元は削除不可
        if selection.approval_status == "approved":
            return jsonify({"status": "error", "message": "完了済みの単元は削除できません"}), 400

        # 強制削除フラグのチェック
        force = request.args.get("force", "false").lower() == "true"
        
        # 学習中の単元は削除前に確認（強制削除でない場合）
        if not force and selection.status == "in_progress" and selection.progress_percentage > 0:
            return jsonify({
                "status": "warning", 
                "message": "学習中の単元です。削除すると進捗が失われます。続行しますか？",
                "progress_percentage": selection.progress_percentage
            }), 200

        # 単元選択を削除
        db.session.delete(selection)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "単元選択を削除しました",
            "unit_id": unit_id
        })

    except Exception as e:
        logging.error(f"Remove unit selection error: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": "削除中にエラーが発生しました"}), 500


@unit_management_bp.route("/units/select", methods=["POST"])
@login_required
@api_limit()
def select_unit():
    """単元選択API - 生徒が学習単元を選択"""
    try:
        # リクエストデータを取得
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "JSONデータが必要です"}), 400

        unit_id = data.get("unit_id")
        selection_reason = data.get("selection_reason", "self_selected")

        if not unit_id:
            return jsonify({"status": "error", "message": "単元IDが必要です"}), 400

        # 単元の存在確認
        unit = CurriculumUnit.query.get(unit_id)
        if not unit or not unit.is_active:
            return jsonify({"status": "error", "message": "指定された単元が見つかりません"}), 404

        # 生徒の所属クラス確認（学校フィルタリング）
        if unit.school_id:
            if current_user.school_id != unit.school_id:
                return (
                    jsonify({"status": "error", "message": "この単元にアクセスする権限がありません"}),
                    403,
                )

        # 既存の選択履歴確認
        existing_selection = StudentUnitSelection.query.filter_by(
            student_id=current_user.id, unit_id=unit_id
        ).first()

        if existing_selection:
            # 既に選択済みの場合は状況に応じて処理
            if existing_selection.status == "completed":
                return jsonify({"status": "info", "message": "この単元は既に完了しています"})
            elif existing_selection.status in ["in_progress", "paused"]:
                # 学習再開
                existing_selection.status = "in_progress"
                existing_selection.last_activity_at = datetime.utcnow()
                db.session.commit()

                return jsonify(
                    {
                        "status": "success",
                        "message": "単元学習を再開しました",
                        "learning_url": f"/student/learning/unit/{unit_id}",
                    }
                )
        else:
            # 新規選択の作成
            new_selection = StudentUnitSelection(
                student_id=current_user.id,
                unit_id=unit_id,
                status="not_started",
                started_at=datetime.utcnow(),
                last_activity_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            db.session.add(new_selection)

        db.session.commit()

        logging.info(
            f"Unit selected: student_id={current_user.id}, unit_id={unit_id}, reason={selection_reason}"
        )

        return jsonify(
            {
                "status": "success",
                "message": f"単元「{unit.title}」を選択しました",
                "unit_title": unit.title,
                "learning_url": f"/student/learning/unit/{unit_id}",
            }
        )

    except Exception as e:
        logging.error(f"Unit selection error: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": "単元選択中にエラーが発生しました"}), 500


@unit_management_bp.route("/units", methods=["GET"])
@login_required
@api_limit()
def get_units():
    """単元一覧取得API - 進捗情報付き（新旧システム統合）"""
    try:
        logging.info(f"get_units called by user {current_user.id} ({current_user.role})")
        
        # クエリパラメータ
        subject_id = request.args.get("subject_id", type=int)
        school_id = request.args.get("school_id", type=int)
        include_progress = (
            request.args.get("include_progress", "true").lower() == "true"
        )
        
        logging.info(f"Parameters: subject_id={subject_id}, school_id={school_id}, include_progress={include_progress}")

        unit_data = []

        # 学生の場合、所属クラスのカリキュラムを取得
        if current_user.role == "student":
            from app.models import ClassEnrollment, Curriculum
            try:
                from app.modules.lesson_system.models.lesson_models import CurriculumLesson, StudentLessonProgress, LessonTask, StudentTaskCheck, TaskCheckStatus
            except ImportError:
                # レッスンシステムが利用できない場合は従来システムのみ
                CurriculumLesson = None
                StudentLessonProgress = None
                LessonTask = None
                StudentTaskCheck = None
                TaskCheckStatus = None
            
            # 学生の所属クラスを取得
            enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
            class_ids = [e.class_id for e in enrollments]
            
            if class_ids and CurriculumLesson:
                # 新しいカリキュラムシステム（レッスン）
                curricula = Curriculum.query.filter(Curriculum.class_id.in_(class_ids)).all()
                
                for curriculum in curricula:
                    # レッスン数を確認
                    lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum.id).all()
                    if len(lessons) > 0:  # レッスンがある場合のみ追加
                        curriculum_info = {
                            "id": curriculum.id,
                            "title": curriculum.title,
                            "description": curriculum.description,
                            "subject_id": curriculum.subject_id,
                            "estimated_hours": curriculum.total_hours or 1,
                            "estimated_minutes": int((curriculum.total_hours or 1) * 60),
                            "difficulty_level": curriculum.difficulty_level or 2,
                            "order_index": curriculum.id,  # カリキュラムIDを順序として使用
                            "system_type": "lessons",
                            "total_lessons": len(lessons)
                        }

                        if include_progress and StudentLessonProgress and LessonTask and StudentTaskCheck:
                            # レッスンシステムの進捗を計算
                            completed_lessons = 0
                            total_lesson_tasks = 0
                            completed_lesson_tasks = 0
                            
                            for lesson in lessons:
                                # レッスンの進捗を確認
                                lesson_progress = StudentLessonProgress.query.filter_by(
                                    student_id=current_user.id, lesson_id=lesson.id
                                ).first()
                                
                                if lesson_progress and lesson_progress.is_completed:
                                    completed_lessons += 1
                                
                                # レッスンのタスクをカウント
                                lesson_tasks = LessonTask.query.filter_by(lesson_id=lesson.id).all()
                                total_lesson_tasks += len(lesson_tasks)
                                
                                # 完了済みタスクをカウント
                                for task in lesson_tasks:
                                    task_check = StudentTaskCheck.query.filter_by(
                                        student_id=current_user.id,
                                        task_id=task.id,
                                        status=TaskCheckStatus.COMPLETED
                                    ).first()
                                    if task_check:
                                        completed_lesson_tasks += 1
                            
                            progress_percentage = round((completed_lesson_tasks / total_lesson_tasks * 100) if total_lesson_tasks > 0 else 0, 1)
                            
                            # 進捗状態を決定
                            if progress_percentage >= 100:
                                status = "completed"
                            elif progress_percentage > 0:
                                status = "in_progress"
                            else:
                                status = "not_started"
                            
                            curriculum_info["progress"] = {
                                "status": status,
                                "progress_percentage": progress_percentage,
                                "completed_tasks": completed_lesson_tasks,
                                "total_tasks": total_lesson_tasks,
                                "completed_lessons": completed_lessons,
                                "total_lessons": len(lessons),
                                "started_at": None,
                                "completed_at": None,
                                "last_activity_at": None,
                            }
                        elif include_progress:
                            # レッスンシステムが利用できない場合のデフォルト進捗
                            curriculum_info["progress"] = {
                                "status": "not_started",
                                "progress_percentage": 0,
                                "completed_tasks": 0,
                                "total_tasks": 0,
                                "completed_lessons": 0,
                                "total_lessons": len(lessons),
                                "started_at": None,
                                "completed_at": None,
                                "last_activity_at": None,
                            }
                        else:
                            curriculum_info["progress"] = None

                        unit_data.append(curriculum_info)

        # 従来の単元システム
        query = CurriculumUnit.query.filter_by(is_active=True)

        # フィルタリング
        if subject_id:
            query = query.filter_by(subject_id=subject_id)

        # 学校フィルタリング（学生の場合は自分の学校のみ）
        if current_user.role == "student":
            query = query.filter_by(school_id=current_user.school_id)
        elif school_id:
            query = query.filter_by(school_id=school_id)

        units = query.order_by(CurriculumUnit.order_index).all()

        # 従来の単元データを追加
        for unit in units:
            unit_info = {
                "id": unit.id,
                "title": unit.title,
                "description": unit.description,
                "subject_id": unit.subject_id,
                "estimated_hours": unit.get_estimated_hours(),
                "estimated_minutes": unit.estimated_minutes if hasattr(unit, "estimated_minutes") else int((unit.get_estimated_hours() or 1) * 60),
                "difficulty_level": unit.difficulty_level,
                "order_index": unit.order_index,
                "system_type": "tasks"
            }

            if include_progress and current_user.role == "student":
                # 学生の進捗情報を取得
                selection = StudentUnitSelection.query.filter_by(
                    student_id=current_user.id, unit_id=unit.id
                ).first()

                if selection:
                    unit_info["progress"] = {
                        "status": selection.status,
                        "progress_percentage": selection.progress_percentage,
                        "started_at": selection.started_at.isoformat()
                        if selection.started_at
                        else None,
                        "completed_at": selection.completed_at.isoformat()
                        if selection.completed_at
                        else None,
                        "last_activity_at": selection.last_activity_at.isoformat()
                        if selection.last_activity_at
                        else None,
                    }
                else:
                    unit_info["progress"] = None

            unit_data.append(unit_info)

        return jsonify(
            {
                "status": "success", 
                "data": {
                    "units": unit_data
                },
                "total_count": len(unit_data)
            }
        )

    except Exception as e:
        logging.error(f"Get units error: {str(e)}")
        logging.error(f"Error traceback: ", exc_info=True)
        return jsonify({"status": "error", "message": "単元一覧取得中にエラーが発生しました", "debug": str(e)}), 500


@unit_management_bp.route("/units/<int:unit_id>/progress", methods=["POST"])
@login_required
@api_limit()
def update_unit_progress(unit_id):
    """単元進捗更新API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "JSONデータが必要です"}), 400

        progress_percentage = data.get("progress_percentage")
        completed_item_ids = data.get("completed_item_ids", [])

        if progress_percentage is None:
            return jsonify({"status": "error", "message": "進捗率が必要です"}), 400

        # 単元選択の確認
        selection = StudentUnitSelection.query.filter_by(
            student_id=current_user.id, unit_id=unit_id
        ).first()

        if not selection:
            return jsonify({"status": "error", "message": "単元が選択されていません"}), 400

        # 進捗更新
        selection.progress_percentage = min(100, max(0, progress_percentage))
        selection.last_activity_at = datetime.utcnow()

        # ステータス更新
        if selection.progress_percentage == 0:
            selection.status = "not_started"
        elif selection.progress_percentage >= 100:
            selection.status = "completed"
            selection.completed_at = datetime.utcnow()
        else:
            selection.status = "in_progress"
            if not selection.started_at:
                selection.started_at = datetime.utcnow()

        # 完了アイテムの記録（UnitItemMappingサービスを使用）
        if completed_item_ids:
            try:
                completion_service = UnitCompletionService()
                completion_service.update_item_completion(
                    current_user.id, unit_id, completed_item_ids
                )
            except Exception as e:
                logging.warning(f"Item completion update failed: {str(e)}")

        db.session.commit()

        logging.info(
            f"Unit progress updated: student_id={current_user.id}, unit_id={unit_id}, progress={progress_percentage}%"
        )

        return jsonify(
            {
                "status": "success",
                "message": "進捗を更新しました",
                "current_progress": selection.progress_percentage,
                "current_status": selection.status,
            }
        )

    except Exception as e:
        logging.error(f"Update unit progress error: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": "進捗更新中にエラーが発生しました"}), 500


@unit_management_bp.route("/units/mappings/create", methods=["POST"])
@login_required
@api_limit()
def create_unit_mappings():
    """単元-アイテムマッピング作成API"""
    try:
        # 教師・管理者のみ実行可能
        if current_user.role not in ["teacher", "admin"]:
            return jsonify({"status": "error", "message": "この操作には教師権限が必要です"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "JSONデータが必要です"}), 400

        unit_id = data.get("unit_id")
        item_ids = data.get("item_ids", [])

        if not unit_id or not item_ids:
            return jsonify({"status": "error", "message": "単元IDとアイテムIDが必要です"}), 400

        # 単元の存在確認
        unit = CurriculumUnit.query.get(unit_id)
        if not unit:
            return jsonify({"status": "error", "message": "指定された単元が見つかりません"}), 404

        # 権限確認（教師は自分のクラスの単元のみ）
        if current_user.role == "teacher":
            if unit.created_by != current_user.id:
                return jsonify({"status": "error", "message": "この単元を編集する権限がありません"}), 403

        # 既存マッピングを削除
        UnitItemMapping.query.filter_by(unit_id=unit_id).delete()

        # 新しいマッピングを作成
        created_count = 0
        for order_index, item_id in enumerate(item_ids):
            mapping = UnitItemMapping(
                unit_id=unit_id,
                item_id=item_id,
                order_index=order_index,
                created_at=datetime.utcnow(),
            )
            db.session.add(mapping)
            created_count += 1

        db.session.commit()

        logging.info(
            f"Unit mappings created: unit_id={unit_id}, count={created_count}, teacher_id={current_user.id}"
        )

        return jsonify(
            {
                "status": "success",
                "message": f"{created_count}個のマッピングを作成しました",
                "created_count": created_count,
            }
        )

    except Exception as e:
        logging.error(f"Create unit mappings error: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": "マッピング作成中にエラーが発生しました"}), 500


@unit_management_bp.route("/units/<int:unit_id>/request-completion", methods=["POST"])
@login_required
@api_limit()
def request_unit_completion(unit_id):
    """単元完了申請API"""
    try:
        data = request.get_json()
        completion_comment = data.get("completion_comment", "") if data else ""

        # 単元選択の確認
        selection = StudentUnitSelection.query.filter_by(
            student_id=current_user.id, unit_id=unit_id
        ).first()

        if not selection:
            return jsonify({"status": "error", "message": "単元が選択されていません"}), 400

        if selection.status == "completed":
            return jsonify({"status": "info", "message": "この単元は既に完了しています"})

        # 進捗率チェック
        if selection.progress_percentage < 80:
            return jsonify({"status": "error", "message": "完了申請には80%以上の進捗が必要です"}), 400

        # クラス設定確認
        class_setting = None
        for enrollment in current_user.enrollments:
            if enrollment.class_obj.school_id == current_user.school_id:
                class_setting = ClassLearningSettings.query.filter_by(
                    class_id=enrollment.class_id
                ).first()
                break

        # 教師承認が必要かチェック
        if class_setting and class_setting.require_teacher_approval:
            # 承認待ちステータスに設定
            selection.approval_status = "pending"
            selection.completion_request_date = datetime.utcnow()
            selection.student_comments = completion_comment

            db.session.commit()

            return jsonify(
                {
                    "status": "success",
                    "message": "完了申請を送信しました。教師の承認をお待ちください。",
                    "approval_required": True,
                }
            )
        else:
            # 自動承認
            completion_service = UnitCompletionService()
            result = completion_service.complete_unit(current_user.id, unit_id)

            if result["success"]:
                return jsonify(
                    {
                        "status": "success",
                        "message": "単元を完了しました！",
                        "approval_required": False,
                    }
                )
            else:
                return jsonify({"status": "error", "message": result["message"]}), 400

    except Exception as e:
        logging.error(f"Request unit completion error: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": "完了申請中にエラーが発生しました"}), 500


@unit_management_bp.route("/units/my-selections", methods=["GET"])
@login_required
@api_limit()
def get_my_unit_selections():
    """学生の単元選択一覧取得API"""
    try:
        # 学生のみアクセス可能
        if current_user.role != "student":
            return jsonify({"status": "error", "message": "この機能は学生のみ利用できます"}), 403

        # フィルタリングパラメータ
        status = request.args.get("status")  # 'completed', 'in_progress', 'not_started'
        include_unit_details = (
            request.args.get("include_details", "true").lower() == "true"
        )

        # 基本クエリ
        query = StudentUnitSelection.query.filter_by(student_id=current_user.id)

        if status:
            query = query.filter_by(status=status)

        selections = query.order_by(StudentUnitSelection.last_activity_at.desc()).all()

        # レスポンスデータ構築
        selection_data = []
        for selection in selections:
            selection_info = {
                "id": selection.id,
                "unit_id": selection.unit_id,
                "status": selection.status,
                "progress_percentage": selection.progress_percentage,
                "approval_status": selection.approval_status,
                "started_at": selection.started_at.isoformat()
                if selection.started_at
                else None,
                "completed_at": selection.completed_at.isoformat()
                if selection.completed_at
                else None,
                "completion_request_date": selection.completion_request_date.isoformat()
                if selection.completion_request_date
                else None,
                "last_activity_at": selection.last_activity_at.isoformat()
                if selection.last_activity_at
                else None,
            }

            if include_unit_details and selection.unit:
                selection_info["unit"] = {
                    "title": selection.unit.title,
                    "description": selection.unit.description,
                    "estimated_hours": selection.unit.get_estimated_hours(),
                    "difficulty_level": selection.unit.difficulty_level,
                }

            selection_data.append(selection_info)

        return jsonify(
            {
                "status": "success",
                "selections": selection_data,
                "total_count": len(selection_data),
            }
        )

    except Exception as e:
        logging.error(f"Get my unit selections error: {str(e)}")
        return jsonify({"status": "error", "message": "選択履歴取得中にエラーが発生しました"}), 500


@unit_management_bp.route("/units/completion-history", methods=["GET"])
@login_required
@api_limit()
def get_completion_history():
    """完了履歴取得API"""
    try:
        # 学生のみアクセス可能
        if current_user.role != "student":
            return jsonify({"status": "error", "message": "この機能は学生のみ利用できます"}), 403

        # 完了済み単元を取得
        completed_selections = (
            StudentUnitSelection.query.filter_by(
                student_id=current_user.id, status="completed"
            )
            .order_by(StudentUnitSelection.completed_at.desc())
            .all()
        )

        history_data = []
        for selection in completed_selections:
            if selection.unit:
                history_item = {
                    "unit_id": selection.unit_id,
                    "unit_title": selection.unit.title,
                    "completed_at": selection.completed_at.isoformat(),
                    "progress_percentage": selection.progress_percentage,
                    "study_duration_days": (
                        selection.completed_at - selection.started_at
                    ).days
                    if selection.started_at
                    else 0,
                    "approval_status": selection.approval_status,
                    "approved_by": selection.approved_by,
                    "approved_at": selection.approved_at.isoformat()
                    if selection.approved_at
                    else None,
                }
                history_data.append(history_item)

        return jsonify(
            {
                "status": "success",
                "completion_history": history_data,
                "total_completed": len(history_data),
            }
        )

    except Exception as e:
        logging.error(f"Get completion history error: {str(e)}")
        return jsonify({"status": "error", "message": "完了履歴取得中にエラーが発生しました"}), 500


@unit_management_bp.route("/progress/batch-update", methods=["POST"])
@login_required
@api_limit()
def batch_update_progress():
    """進捗一括更新API"""
    try:
        data = request.get_json()
        if not data or "updates" not in data:
            return jsonify({"status": "error", "message": "更新データが必要です"}), 400

        updates = data["updates"]
        if not isinstance(updates, list):
            return jsonify({"status": "error", "message": "更新データは配列形式である必要があります"}), 400

        success_count = 0
        error_count = 0

        for update in updates:
            try:
                unit_id = update.get("unit_id")
                progress_percentage = update.get("progress_percentage")

                if unit_id is None or progress_percentage is None:
                    error_count += 1
                    continue

                # 単元選択の確認
                selection = StudentUnitSelection.query.filter_by(
                    student_id=current_user.id, unit_id=unit_id
                ).first()

                if not selection:
                    error_count += 1
                    continue

                # 進捗更新
                selection.progress_percentage = min(100, max(0, progress_percentage))
                selection.last_activity_at = datetime.utcnow()

                # ステータス更新
                if selection.progress_percentage >= 100:
                    selection.status = "completed"
                    if not selection.completed_at:
                        selection.completed_at = datetime.utcnow()
                elif selection.progress_percentage > 0:
                    selection.status = "in_progress"
                    if not selection.started_at:
                        selection.started_at = datetime.utcnow()

                success_count += 1

            except Exception as e:
                logging.warning(f"Batch update item error: {str(e)}")
                error_count += 1

        db.session.commit()

        return jsonify(
            {
                "status": "success" if error_count == 0 else "partial_success",
                "message": f"{success_count}件の進捗を更新しました",
                "success_count": success_count,
                "error_count": error_count,
            }
        )

    except Exception as e:
        logging.error(f"Batch update progress error: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": "一括更新中にエラーが発生しました"}), 500


# 教師向け承認管理API


@unit_management_bp.route("/approvals/pending", methods=["GET"])
@login_required
@api_limit()
def get_pending_approvals():
    """承認待ち一覧取得API"""
    try:
        # 教師のみアクセス可能
        if current_user.role != "teacher":
            return jsonify({"status": "error", "message": "この機能は教師のみ利用できます"}), 403

        # 教師のクラスの学生の承認待ち申請を取得
        pending_approvals = (
            db.session.query(StudentUnitSelection)
            .join(
                ClassEnrollment,
                StudentUnitSelection.student_id == ClassEnrollment.student_id,
            )
            .join(Class, ClassEnrollment.class_id == Class.id)
            .filter(
                Class.teacher_id == current_user.id,
                StudentUnitSelection.approval_status == "pending",
            )
            .order_by(StudentUnitSelection.completion_request_date.desc())
            .all()
        )

        approval_data = []
        for selection in pending_approvals:
            approval_item = {
                "selection_id": selection.id,
                "student_id": selection.student_id,
                "student_name": selection.student.name
                if selection.student
                else "Unknown",
                "unit_id": selection.unit_id,
                "unit_title": selection.unit.title if selection.unit else "Unknown",
                "progress_percentage": selection.progress_percentage,
                "completion_request_date": selection.completion_request_date.isoformat(),
                "student_comments": selection.student_comments,
                "study_duration_days": (
                    selection.completion_request_date - selection.started_at
                ).days
                if selection.started_at
                else 0,
            }
            approval_data.append(approval_item)

        return jsonify(
            {
                "status": "success",
                "pending_approvals": approval_data,
                "total_count": len(approval_data),
            }
        )

    except Exception as e:
        logging.error(f"Get pending approvals error: {str(e)}")
        return jsonify({"status": "error", "message": "承認待ち一覧取得中にエラーが発生しました"}), 500


@unit_management_bp.route("/approvals/<int:selection_id>/approve", methods=["POST"])
@login_required
@api_limit()
def approve_completion(selection_id):
    """単元完了承認API"""
    try:
        # 教師のみアクセス可能
        if current_user.role != "teacher":
            return jsonify({"status": "error", "message": "この機能は教師のみ利用できます"}), 403

        data = request.get_json()
        teacher_comments = data.get("teacher_comments", "") if data else ""

        # 承認対象の選択を取得
        selection = StudentUnitSelection.query.get(selection_id)
        if not selection:
            return jsonify({"status": "error", "message": "指定された申請が見つかりません"}), 404

        if selection.approval_status != "pending":
            return jsonify({"status": "error", "message": "この申請は既に処理済みです"}), 400

        # 教師の権限確認
        student_in_class = (
            db.session.query(ClassEnrollment)
            .join(Class, ClassEnrollment.class_id == Class.id)
            .filter(
                Class.teacher_id == current_user.id,
                ClassEnrollment.student_id == selection.student_id,
            )
            .first()
        )

        if not student_in_class:
            return jsonify({"status": "error", "message": "この学生の申請を承認する権限がありません"}), 403

        # 承認処理
        completion_service = UnitCompletionService()
        result = completion_service.approve_completion(
            selection_id, current_user.id, teacher_comments
        )

        if result["success"]:
            return jsonify({"status": "success", "message": "単元完了を承認しました"})
        else:
            return jsonify({"status": "error", "message": result["message"]}), 400

    except Exception as e:
        logging.error(f"Approve completion error: {str(e)}")
        return jsonify({"status": "error", "message": "承認処理中にエラーが発生しました"}), 500


@unit_management_bp.route("/approvals/<int:selection_id>/reject", methods=["POST"])
@login_required
@api_limit()
def reject_completion(selection_id):
    """単元完了拒否API"""
    try:
        # 教師のみアクセス可能
        if current_user.role != "teacher":
            return jsonify({"status": "error", "message": "この機能は教師のみ利用できます"}), 403

        data = request.get_json()
        if not data or not data.get("rejection_reason"):
            return jsonify({"status": "error", "message": "拒否理由が必要です"}), 400

        rejection_reason = data["rejection_reason"]

        # 承認対象の選択を取得
        selection = StudentUnitSelection.query.get(selection_id)
        if not selection:
            return jsonify({"status": "error", "message": "指定された申請が見つかりません"}), 404

        if selection.approval_status != "pending":
            return jsonify({"status": "error", "message": "この申請は既に処理済みです"}), 400

        # 教師の権限確認
        student_in_class = (
            db.session.query(ClassEnrollment)
            .join(Class, ClassEnrollment.class_id == Class.id)
            .filter(
                Class.teacher_id == current_user.id,
                ClassEnrollment.student_id == selection.student_id,
            )
            .first()
        )

        if not student_in_class:
            return jsonify({"status": "error", "message": "この学生の申請を処理する権限がありません"}), 403

        # 拒否処理
        selection.approval_status = "rejected"
        selection.rejection_reason = rejection_reason
        selection.approved_by = current_user.id
        selection.approved_at = datetime.utcnow()

        db.session.commit()

        logging.info(
            f"Unit completion rejected: selection_id={selection_id}, teacher_id={current_user.id}"
        )

        return jsonify({"status": "success", "message": "申請を拒否しました"})

    except Exception as e:
        logging.error(f"Reject completion error: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": "拒否処理中にエラーが発生しました"}), 500


@unit_management_bp.route("/approvals/batch-approve", methods=["POST"])
@login_required
@api_limit()
def batch_approve_completions():
    """一括承認API"""
    try:
        # 教師のみアクセス可能
        if current_user.role != "teacher":
            return jsonify({"status": "error", "message": "この機能は教師のみ利用できます"}), 403

        data = request.get_json()
        if not data or "selection_ids" not in data:
            return jsonify({"status": "error", "message": "承認対象IDが必要です"}), 400

        selection_ids = data["selection_ids"]
        teacher_comments = data.get("teacher_comments", "")

        if not isinstance(selection_ids, list):
            return (
                jsonify({"status": "error", "message": "selection_idsは配列形式である必要があります"}),
                400,
            )

        success_count = 0
        error_count = 0

        completion_service = UnitCompletionService()

        for selection_id in selection_ids:
            try:
                # 権限確認
                selection = StudentUnitSelection.query.get(selection_id)
                if not selection or selection.approval_status != "pending":
                    error_count += 1
                    continue

                student_in_class = (
                    db.session.query(ClassEnrollment)
                    .join(Class, ClassEnrollment.class_id == Class.id)
                    .filter(
                        Class.teacher_id == current_user.id,
                        ClassEnrollment.student_id == selection.student_id,
                    )
                    .first()
                )

                if not student_in_class:
                    error_count += 1
                    continue

                # 承認処理
                result = completion_service.approve_completion(
                    selection_id, current_user.id, teacher_comments
                )

                if result["success"]:
                    success_count += 1
                else:
                    error_count += 1

            except Exception as e:
                logging.warning(f"Batch approval item error: {str(e)}")
                error_count += 1

        return jsonify(
            {
                "status": "success" if error_count == 0 else "partial_success",
                "message": f"{success_count}件の申請を承認しました",
                "success_count": success_count,
                "error_count": error_count,
            }
        )

    except Exception as e:
        logging.error(f"Batch approve completions error: {str(e)}")
        return jsonify({"status": "error", "message": "一括承認処理中にエラーが発生しました"}), 500


@unit_management_bp.route("/approvals/statistics", methods=["GET"])
@login_required
@api_limit()
def get_approval_statistics():
    """承認統計取得API"""
    try:
        # 教師のみアクセス可能
        if current_user.role != "teacher":
            return jsonify({"status": "error", "message": "この機能は教師のみ利用できます"}), 403

        # 教師のクラスの学生の申請統計を取得
        base_query = (
            db.session.query(StudentUnitSelection)
            .join(
                ClassEnrollment,
                StudentUnitSelection.student_id == ClassEnrollment.student_id,
            )
            .join(Class, ClassEnrollment.class_id == Class.id)
            .filter(Class.teacher_id == current_user.id)
        )

        # 各ステータスの件数を集計
        pending_count = base_query.filter(
            StudentUnitSelection.approval_status == "pending"
        ).count()

        approved_count = base_query.filter(
            StudentUnitSelection.approval_status == "approved"
        ).count()

        rejected_count = base_query.filter(
            StudentUnitSelection.approval_status == "rejected"
        ).count()

        completed_count = base_query.filter(
            StudentUnitSelection.status == "completed"
        ).count()

        # 最近の承認活動
        recent_approvals = base_query.filter(
            StudentUnitSelection.approval_status.in_(["approved", "rejected"]),
            StudentUnitSelection.approved_at >= datetime.utcnow() - timedelta(days=7),
        ).count()

        return jsonify(
            {
                "status": "success",
                "statistics": {
                    "pending_approvals": pending_count,
                    "approved_count": approved_count,
                    "rejected_count": rejected_count,
                    "total_completed": completed_count,
                    "recent_approvals_week": recent_approvals,
                },
            }
        )

    except Exception as e:
        logging.error(f"Get approval statistics error: {str(e)}")
        return jsonify({"status": "error", "message": "統計取得中にエラーが発生しました"}), 500


@unit_management_bp.route("/curriculum/<int:curriculum_id>/request-completion", methods=["POST"])
@login_required
@api_limit()
def request_curriculum_completion(curriculum_id):
    """新レッスンシステム用カリキュラム完了申請API"""
    try:
        from app.models import ClassEnrollment, Curriculum
        from app.modules.lesson_system.models.lesson_models import CurriculumLesson, StudentLessonProgress, LessonTask, StudentTaskCheck, TaskCheckStatus
        from app.services.basebuilder_task_service import BaseBuilderTaskService
        
        # 学生のみアクセス可能
        if current_user.role != "student":
            return jsonify({"status": "error", "message": "この機能は学生のみ利用可能です"}), 403

        data = request.get_json()
        completion_comment = data.get("completion_comment", "") if data else ""
        check_basebuilder = data.get("check_basebuilder", True) if data else True

        # カリキュラムの存在確認
        curriculum = Curriculum.query.get(curriculum_id)
        if not curriculum:
            return jsonify({"status": "error", "message": "指定されたカリキュラムが見つかりません"}), 404

        # 学生がこのカリキュラムのクラスに所属しているかチェック
        enrollment = ClassEnrollment.query.filter_by(
            student_id=current_user.id, class_id=curriculum.class_id
        ).first()
        
        if not enrollment:
            return jsonify({"status": "error", "message": "このカリキュラムにアクセスする権限がありません"}), 403

        # カリキュラムのレッスンを取得
        lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum_id).all()
        
        if not lessons:
            return jsonify({"status": "error", "message": "このカリキュラムにはレッスンがありません"}), 400

        # レッスン完了状況をチェック
        total_lessons = len(lessons)
        completed_lessons = 0
        total_tasks = 0
        completed_tasks = 0
        basebuilder_text_count = 0
        basebuilder_texts_90_plus = 0
        
        for lesson in lessons:
            # レッスンの進捗を確認
            lesson_progress = StudentLessonProgress.query.filter_by(
                student_id=current_user.id, lesson_id=lesson.id
            ).first()
            
            if lesson_progress and lesson_progress.is_completed:
                completed_lessons += 1
            
            # レッスンのタスクを取得
            lesson_tasks = LessonTask.query.filter_by(lesson_id=lesson.id).all()
            total_tasks += len(lesson_tasks)
            
            # タスクの完了状況とBaseBuilder達成率をチェック
            for task in lesson_tasks:
                # タスクの完了状況
                task_check = StudentTaskCheck.query.filter_by(
                    student_id=current_user.id,
                    task_id=task.id,
                    status=TaskCheckStatus.COMPLETED
                ).first()
                
                if task_check:
                    completed_tasks += 1
                
                # BaseBuilder情報をチェック
                if check_basebuilder:
                    bb_info = BaseBuilderTaskService.get_task_basebuilder_info(task)
                    if bb_info and bb_info['type'] == 'text':
                        basebuilder_text_count += 1
                        achievement_rate = BaseBuilderTaskService.calculate_text_achievement_rate(
                            current_user.id, bb_info['text_id']
                        )
                        if achievement_rate >= 90.0:
                            basebuilder_texts_90_plus += 1

        # 完了申請条件をチェック
        lesson_requirement_met = completed_lessons >= total_lessons * 0.8  # 80%以上のレッスン完了
        
        if basebuilder_text_count > 0:
            # BaseBuilderテキストがある場合: 90%達成率 + レッスン完了
            basebuilder_requirement_met = basebuilder_texts_90_plus >= basebuilder_text_count
            can_request = lesson_requirement_met and basebuilder_requirement_met
            
            if not can_request:
                return jsonify({
                    "status": "error", 
                    "message": f"完了申請の条件が満たされていません。\nレッスン完了: {completed_lessons}/{total_lessons} (要{int(total_lessons * 0.8)}以上)\nBaseBuilder 90%達成: {basebuilder_texts_90_plus}/{basebuilder_text_count}"
                }), 400
        else:
            # BaseBuilderテキストがない場合: レッスン達成のみ
            if not lesson_requirement_met:
                return jsonify({
                    "status": "error", 
                    "message": f"完了申請の条件が満たされていません。\nレッスン完了: {completed_lessons}/{total_lessons} (要{int(total_lessons * 0.8)}以上)"
                }), 400

        # 完了申請を記録（この実装は簡略化版。実際は承認ワークフローが必要）
        logging.info(
            f"Curriculum completion requested: student_id={current_user.id}, curriculum_id={curriculum_id}, "
            f"lessons_completed={completed_lessons}/{total_lessons}, "
            f"basebuilder_90plus={basebuilder_texts_90_plus}/{basebuilder_text_count}"
        )

        return jsonify({
            "status": "success",
            "message": f"カリキュラム「{curriculum.title}」の完了申請を送信しました。教師の承認をお待ちください。",
            "completion_details": {
                "lessons_completed": f"{completed_lessons}/{total_lessons}",
                "tasks_completed": f"{completed_tasks}/{total_tasks}",
                "basebuilder_achievement": f"{basebuilder_texts_90_plus}/{basebuilder_text_count} (90%+)" if basebuilder_text_count > 0 else "なし"
            }
        })

    except Exception as e:
        logging.error(f"Request curriculum completion error: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": "完了申請中にエラーが発生しました"}), 500


@unit_management_bp.route("/unit/<int:unit_id>/resubmit-completion", methods=['POST'])
@login_required
@api_limit()
def resubmit_unit_completion(unit_id):
    """単元完了の再申請"""
    try:
        # 学生のみアクセス可能
        if current_user.role != "student":
            return jsonify({'status': 'error', 'message': 'この機能は学生のみ利用可能です'}), 403
        
        # 却下された申請を検索
        unit_selection = StudentUnitSelection.query.filter_by(
            student_id=current_user.id,
            unit_id=unit_id,
            approval_status='rejected'
        ).first()
        
        if not unit_selection:
            return jsonify({'status': 'error', 'message': '再申請可能な申請が見つかりません'}), 404
        
        # 進捗率が80%以上かチェック
        if unit_selection.progress_percentage < 80:
            return jsonify({
                'status': 'error', 
                'message': f'進捗率が不足しています（現在: {unit_selection.progress_percentage}%、必要: 80%以上）'
            }), 400
        
        # 再申請処理
        unit_selection.completion_request_date = datetime.utcnow()
        unit_selection.approval_status = 'pending'  # 承認待ち状態に戻す
        
        # 再申請回数を増加
        if unit_selection.resubmission_count is None:
            unit_selection.resubmission_count = 0
        unit_selection.resubmission_count += 1
        
        # ステータスも更新
        unit_selection.status = 'completed'  # 完了状態に設定
        
        db.session.commit()
        
        logging.info(f"Unit completion resubmitted: student_id={current_user.id}, unit_id={unit_id}, resubmission_count={unit_selection.resubmission_count}")
        
        return jsonify({
            'status': 'success',
            'message': '再申請を送信しました。教師の承認をお待ちください。',
            'resubmission_count': unit_selection.resubmission_count
        })
        
    except Exception as e:
        logging.error(f"Resubmit unit completion error: {str(e)}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': '再申請中にエラーが発生しました'}), 500
