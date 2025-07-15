# app/teacher/modules/approval_workflow.py
"""承認ワークフロー機能"""

from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import (
    Class,
    ClassEnrollment,
    ClassLearningSettings,
    CurriculumUnit,
    StudentUnitSelection,
    User,
    db,
)
from app.services.unit_completion_service import UnitCompletionService

from ..common import teacher_required

approval_workflow_bp = Blueprint("teacher_approval_workflow", __name__)


@approval_workflow_bp.route("/teacher/pending-unit-approvals")
@login_required
@teacher_required
def pending_unit_approvals():
    """承認待ち単元一覧"""
    try:
        # 教師が担当するクラスの承認待ち申請を取得
        pending_approvals = UnitCompletionService.get_pending_approvals(
            teacher_id=current_user.id
        )

        # クラス別に整理
        approvals_by_class = {}
        for approval in pending_approvals:
            class_id = approval["class_id"]
            class_name = approval["class_name"]

            if class_id not in approvals_by_class:
                approvals_by_class[class_id] = {
                    "class_name": class_name,
                    "approvals": [],
                }

            approvals_by_class[class_id]["approvals"].append(approval)

        # 統計情報
        total_pending = len(pending_approvals)
        classes_with_pending = len(approvals_by_class)

        stats = {
            "total_pending": total_pending,
            "classes_with_pending": classes_with_pending,
            "avg_per_class": round(total_pending / classes_with_pending, 1)
            if classes_with_pending > 0
            else 0,
        }

        return render_template(
            "teacher/pending_unit_approvals.html",
            approvals_by_class=approvals_by_class,
            stats=stats,
        )

    except Exception as e:
        flash(f"承認待ちリストの取得に失敗しました: {str(e)}", "error")
        return redirect(url_for("teacher_dashboard.dashboard"))


@approval_workflow_bp.route(
    "/api/approval/<int:selection_id>/approve", methods=["POST"]
)
@login_required
@teacher_required
def approve_completion(selection_id):
    """単元完了承認"""
    try:
        data = request.get_json() or {}
        comments = data.get("comments", "")

        result = UnitCompletionService.approve_completion(
            selection_id=selection_id, teacher_id=current_user.id, comments=comments
        )

        if result["success"]:
            return jsonify(
                {"success": True, "message": "承認しました", "data": result["data"]}
            )
        else:
            return jsonify({"success": False, "error": result["error"]}), 400

    except Exception as e:
        return jsonify({"success": False, "error": f"承認処理に失敗しました: {str(e)}"}), 500


@approval_workflow_bp.route("/api/approval/<int:selection_id>/reject", methods=["POST"])
@login_required
@teacher_required
def reject_completion(selection_id):
    """単元完了却下"""
    try:
        data = request.get_json() or {}
        reason = data.get("reason", "")

        if not reason:
            return jsonify({"success": False, "error": "却下理由は必須です"}), 400

        result = UnitCompletionService.reject_completion(
            selection_id=selection_id, teacher_id=current_user.id, reason=reason
        )

        if result["success"]:
            return jsonify(
                {"success": True, "message": "却下しました", "data": result["data"]}
            )
        else:
            return jsonify({"success": False, "error": result["error"]}), 400

    except Exception as e:
        return jsonify({"success": False, "error": f"却下処理に失敗しました: {str(e)}"}), 500


@approval_workflow_bp.route("/api/approval/<int:selection_id>/details")
@login_required
@teacher_required
def approval_details(selection_id):
    """承認詳細情報取得"""
    try:
        details = UnitCompletionService.get_approval_details(
            selection_id=selection_id, teacher_id=current_user.id
        )

        if details:
            return jsonify({"success": True, "data": details})
        else:
            return jsonify({"success": False, "error": "承認詳細が見つかりません"}), 404

    except Exception as e:
        return jsonify({"success": False, "error": f"詳細情報の取得に失敗しました: {str(e)}"}), 500


@approval_workflow_bp.route("/api/teacher/pending-count")
@login_required
@teacher_required
def pending_count():
    """承認待ち件数取得"""
    try:
        pending_approvals = UnitCompletionService.get_pending_approvals(
            teacher_id=current_user.id
        )

        return jsonify({"success": True, "count": len(pending_approvals)})

    except Exception as e:
        return jsonify({"success": False, "error": f"件数取得に失敗しました: {str(e)}"}), 500


@approval_workflow_bp.route(
    "/class/<int:class_id>/approval-settings", methods=["GET", "POST"]
)
@login_required
@teacher_required
def approval_settings(class_id):
    """クラス承認設定管理"""
    class_obj = Class.query.get_or_404(class_id)

    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash("この設定を変更する権限がありません。")
        return redirect(url_for("teacher_class_management.classes"))

    # 現在の設定を取得
    settings = ClassLearningSettings.query.filter_by(class_id=class_id).first()

    if not settings:
        # デフォルト設定で新規作成
        settings = ClassLearningSettings(
            class_id=class_id,
            require_teacher_approval=True,
            auto_approve_threshold=90.00,
            approval_comment_required=True,
            allow_resubmission=True,
        )
        db.session.add(settings)
        db.session.commit()

    if request.method == "POST":
        try:
            # 設定更新
            settings.require_teacher_approval = (
                request.form.get("require_teacher_approval") == "on"
            )
            settings.auto_approve_threshold = float(
                request.form.get("auto_approve_threshold", 90.0)
            )
            settings.approval_comment_required = (
                request.form.get("approval_comment_required") == "on"
            )
            settings.allow_resubmission = request.form.get("allow_resubmission") == "on"

            # バリデーション
            if (
                settings.auto_approve_threshold < 0
                or settings.auto_approve_threshold > 100
            ):
                flash("自動承認閾値は0-100の範囲で入力してください。", "error")
                return render_template(
                    "approval_settings.html", class_obj=class_obj, settings=settings
                )

            db.session.commit()
            flash("承認設定が更新されました。", "success")

            return redirect(
                url_for("teacher_class_management.class_details", class_id=class_id)
            )

        except ValueError:
            flash("数値の入力が不正です。", "error")
        except Exception as e:
            db.session.rollback()
            flash(f"設定の更新に失敗しました: {str(e)}", "error")

    return render_template(
        "approval_settings.html", class_obj=class_obj, settings=settings
    )


@approval_workflow_bp.route("/api/class/<int:class_id>/approval-settings")
@login_required
@teacher_required
def get_approval_settings(class_id):
    """承認設定取得API"""
    class_obj = Class.query.get_or_404(class_id)

    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        return jsonify({"error": "権限がありません"}), 403

    try:
        settings = ClassLearningSettings.query.filter_by(class_id=class_id).first()

        if not settings:
            # デフォルト設定を返す
            settings_data = {
                "require_teacher_approval": True,
                "auto_approve_threshold": 90.0,
                "approval_comment_required": True,
                "allow_resubmission": True,
            }
        else:
            settings_data = {
                "require_teacher_approval": settings.require_teacher_approval,
                "auto_approve_threshold": float(settings.auto_approve_threshold),
                "approval_comment_required": settings.approval_comment_required,
                "allow_resubmission": settings.allow_resubmission,
            }

        return jsonify({"success": True, "settings": settings_data})

    except Exception as e:
        return jsonify({"success": False, "error": f"設定取得に失敗しました: {str(e)}"}), 500


@approval_workflow_bp.route(
    "/api/class/<int:class_id>/approval-settings/update", methods=["POST"]
)
@login_required
@teacher_required
def update_approval_settings(class_id):
    """承認設定更新API"""
    class_obj = Class.query.get_or_404(class_id)

    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        return jsonify({"error": "権限がありません"}), 403

    try:
        data = request.get_json() or {}

        # 設定を取得または作成
        settings = ClassLearningSettings.query.filter_by(class_id=class_id).first()

        if not settings:
            settings = ClassLearningSettings(class_id=class_id)
            db.session.add(settings)

        # 設定更新
        if "require_teacher_approval" in data:
            settings.require_teacher_approval = bool(data["require_teacher_approval"])

        if "auto_approve_threshold" in data:
            threshold = float(data["auto_approve_threshold"])
            if 0 <= threshold <= 100:
                settings.auto_approve_threshold = threshold
            else:
                return (
                    jsonify({"success": False, "error": "自動承認閾値は0-100の範囲で入力してください"}),
                    400,
                )

        if "approval_comment_required" in data:
            settings.approval_comment_required = bool(data["approval_comment_required"])

        if "allow_resubmission" in data:
            settings.allow_resubmission = bool(data["allow_resubmission"])

        db.session.commit()

        return jsonify({"success": True, "message": "設定が更新されました"})

    except ValueError:
        return jsonify({"success": False, "error": "数値の入力が不正です"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"設定更新に失敗しました: {str(e)}"}), 500


@approval_workflow_bp.route("/api/approvals/batch-approve", methods=["POST"])
@login_required
@teacher_required
def batch_approve(self):
    """一括承認"""
    try:
        data = request.get_json() or {}
        selection_ids = data.get("selection_ids", [])
        comments = data.get("comments", "")

        if not selection_ids:
            return jsonify({"success": False, "error": "承認する申請を選択してください"}), 400

        results = []
        success_count = 0

        for selection_id in selection_ids:
            try:
                result = UnitCompletionService.approve_completion(
                    selection_id=selection_id,
                    teacher_id=current_user.id,
                    comments=comments,
                )

                if result["success"]:
                    success_count += 1
                    results.append({"selection_id": selection_id, "success": True})
                else:
                    results.append(
                        {
                            "selection_id": selection_id,
                            "success": False,
                            "error": result["error"],
                        }
                    )

            except Exception as e:
                results.append(
                    {"selection_id": selection_id, "success": False, "error": str(e)}
                )

        return jsonify(
            {
                "success": True,
                "message": f"{success_count}件の申請を承認しました",
                "results": results,
                "success_count": success_count,
                "total_count": len(selection_ids),
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": f"一括承認に失敗しました: {str(e)}"}), 500
