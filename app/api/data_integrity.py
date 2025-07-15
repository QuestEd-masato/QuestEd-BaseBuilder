"""
データ整合性管理API
==================================================
Phase 3のデータ整合性確保機能をAPIとして提供。
管理者向けのデータ修正・検証機能を実装。

注意: ルートの重複や関数の重複定義を避けるため、慎重に実装
"""

import json
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from app.models import CurriculumUnit, StudentUnitSelection, db
from app.services.unit_item_mapping_service import UnitItemMappingService
from app.utils.decorators import admin_required
from app.utils.logger import create_logger

logger = create_logger(__name__)

# Blueprintの作成（名前の重複を避ける）
data_integrity_bp = Blueprint("data_integrity", __name__)


@data_integrity_bp.route("/verify", methods=["GET"])
@login_required
@admin_required
def verify_data_integrity():
    """
    データ整合性の検証

    Returns:
        検証結果のJSON
    """
    try:
        verification_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "checks": [],
        }

        # 1. curriculum_units の整合性チェック
        units_check = db.session.execute(
            """
            SELECT 
                COUNT(*) as total_units,
                SUM(CASE WHEN created_by IS NULL THEN 1 ELSE 0 END) as null_created_by,
                SUM(CASE WHEN school_id IS NULL THEN 1 ELSE 0 END) as null_school_id,
                SUM(CASE WHEN subject_id IS NULL THEN 1 ELSE 0 END) as null_subject_id
            FROM curriculum_units
            WHERE is_active = 1
        """
        ).fetchone()

        verification_results["checks"].append(
            {
                "name": "curriculum_units整合性",
                "total": units_check.total_units,
                "issues": {
                    "null_created_by": units_check.null_created_by,
                    "null_school_id": units_check.null_school_id,
                    "null_subject_id": units_check.null_subject_id,
                },
                "status": "OK"
                if (
                    units_check.null_created_by
                    + units_check.null_school_id
                    + units_check.null_subject_id
                )
                == 0
                else "NEEDS_FIX",
            }
        )

        # 2. student_unit_selections の整合性チェック
        selections_check = db.session.execute(
            """
            SELECT 
                COUNT(*) as total_selections,
                SUM(CASE WHEN progress_percentage >= 80 AND approval_status = 'none' THEN 1 ELSE 0 END) as pending_approvals,
                SUM(CASE WHEN study_time_minutes IS NULL THEN 1 ELSE 0 END) as null_study_time,
                SUM(CASE WHEN status IS NULL OR status = '' THEN 1 ELSE 0 END) as invalid_status
            FROM student_unit_selections
        """
        ).fetchone()

        verification_results["checks"].append(
            {
                "name": "student_unit_selections整合性",
                "total": selections_check.total_selections,
                "issues": {
                    "pending_approvals": selections_check.pending_approvals,
                    "null_study_time": selections_check.null_study_time,
                    "invalid_status": selections_check.invalid_status,
                },
                "status": "OK"
                if (selections_check.null_study_time + selections_check.invalid_status)
                == 0
                else "NEEDS_FIX",
            }
        )

        # 3. マッピング状況チェック
        mapping_check = db.session.execute(
            """
            SELECT 
                COUNT(DISTINCT cu.id) as total_units,
                COUNT(DISTINCT uim.unit_id) as mapped_units
            FROM curriculum_units cu
            LEFT JOIN unit_item_mappings uim ON cu.id = uim.unit_id
            WHERE cu.is_active = 1
        """
        ).fetchone()

        unmapped_count = mapping_check.total_units - mapping_check.mapped_units

        verification_results["checks"].append(
            {
                "name": "unit_item_mappings状況",
                "total": mapping_check.total_units,
                "mapped": mapping_check.mapped_units,
                "unmapped": unmapped_count,
                "status": "OK" if unmapped_count == 0 else "NEEDS_MAPPING",
            }
        )

        # 全体のステータス判定
        overall_status = "OK"
        for check in verification_results["checks"]:
            if check["status"] != "OK":
                overall_status = "NEEDS_ATTENTION"
                break

        verification_results["overall_status"] = overall_status

        return jsonify({"success": True, "data": verification_results})

    except Exception as e:
        logger.error(f"Data integrity verification error: {str(e)}")
        return jsonify({"success": False, "error": "データ整合性の検証中にエラーが発生しました"}), 500


@data_integrity_bp.route("/fix/curriculum-units", methods=["POST"])
@login_required
@admin_required
def fix_curriculum_units():
    """
    curriculum_unitsテーブルのデータ修正

    Returns:
        修正結果のJSON
    """
    try:
        # ドライラン機能
        dry_run = request.json.get("dry_run", True)

        fixes_applied = {
            "created_by_fixed": 0,
            "school_id_fixed": 0,
            "subject_id_fixed": 0,
            "dry_run": dry_run,
        }

        # 1. created_by の修正
        result = db.session.execute(
            """
            SELECT cu.id, c.teacher_id
            FROM curriculum_units cu
            JOIN curriculums c ON cu.legacy_curriculum_id = c.id
            WHERE cu.created_by IS NULL OR cu.created_by != c.teacher_id
        """
        )

        for row in result:
            if not dry_run:
                unit = CurriculumUnit.query.get(row.id)
                unit.created_by = row.teacher_id
            fixes_applied["created_by_fixed"] += 1

        # 2. school_id の修正
        result = db.session.execute(
            """
            SELECT cu.id, cl.school_id
            FROM curriculum_units cu
            JOIN curriculums c ON cu.legacy_curriculum_id = c.id
            JOIN classes cl ON c.class_id = cl.id
            WHERE cu.school_id IS NULL
        """
        )

        for row in result:
            if not dry_run:
                unit = CurriculumUnit.query.get(row.id)
                unit.school_id = row.school_id
            fixes_applied["school_id_fixed"] += 1

        # 3. subject_id の修正
        result = db.session.execute(
            """
            SELECT cu.id, c.subject_id
            FROM curriculum_units cu
            JOIN curriculums c ON cu.legacy_curriculum_id = c.id
            WHERE cu.subject_id IS NULL AND c.subject_id IS NOT NULL
        """
        )

        for row in result:
            if not dry_run:
                unit = CurriculumUnit.query.get(row.id)
                unit.subject_id = row.subject_id
            fixes_applied["subject_id_fixed"] += 1

        if not dry_run:
            db.session.commit()
            logger.info(f"Applied curriculum_units fixes: {fixes_applied}")

        return jsonify(
            {
                "success": True,
                "data": fixes_applied,
                "message": "ドライラン完了" if dry_run else "データ修正が完了しました",
            }
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Curriculum units fix error: {str(e)}")
        return jsonify({"success": False, "error": "データ修正中にエラーが発生しました"}), 500


@data_integrity_bp.route("/fix/student-selections", methods=["POST"])
@login_required
@admin_required
def fix_student_selections():
    """
    student_unit_selectionsテーブルのデータ修正

    Returns:
        修正結果のJSON
    """
    try:
        dry_run = request.json.get("dry_run", True)

        fixes_applied = {
            "approvals_migrated": 0,
            "study_time_fixed": 0,
            "status_fixed": 0,
            "dry_run": dry_run,
        }

        # 1. 完了済み単元の承認ステータス移行
        result = db.session.execute(
            """
            SELECT id FROM student_unit_selections
            WHERE progress_percentage >= 80.0 
                AND approval_status = 'none'
                AND status = 'completed'
        """
        )

        for row in result:
            if not dry_run:
                selection = StudentUnitSelection.query.get(row.id)
                selection.approval_status = "approved"
                selection.approved_at = datetime.utcnow()
                selection.teacher_comments = "既存学習データからの自動承認"
            fixes_applied["approvals_migrated"] += 1

        # 2. 学習時間の修正
        result = db.session.execute(
            """
            SELECT id FROM student_unit_selections
            WHERE study_time_minutes IS NULL
        """
        )

        for row in result:
            if not dry_run:
                selection = StudentUnitSelection.query.get(row.id)
                selection.study_time_minutes = 0
            fixes_applied["study_time_fixed"] += 1

        # 3. ステータスの修正
        result = db.session.execute(
            """
            SELECT id, progress_percentage FROM student_unit_selections
            WHERE status IS NULL OR status = ''
        """
        )

        for row in result:
            if not dry_run:
                selection = StudentUnitSelection.query.get(row.id)
                if row.progress_percentage == 0:
                    selection.status = "not_started"
                elif row.progress_percentage >= 100:
                    selection.status = "completed"
                else:
                    selection.status = "in_progress"
            fixes_applied["status_fixed"] += 1

        if not dry_run:
            db.session.commit()
            logger.info(f"Applied student_selections fixes: {fixes_applied}")

        return jsonify(
            {
                "success": True,
                "data": fixes_applied,
                "message": "ドライラン完了" if dry_run else "データ修正が完了しました",
            }
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Student selections fix error: {str(e)}")
        return jsonify({"success": False, "error": "データ修正中にエラーが発生しました"}), 500


@data_integrity_bp.route("/mappings/create", methods=["POST"])
@login_required
@admin_required
def create_unit_mappings():
    """
    単元と問題のマッピングを作成

    Returns:
        作成結果のJSON
    """
    try:
        unit_id = request.json.get("unit_id")

        if unit_id:
            # 特定の単元のマッピング作成
            mapping_count = UnitItemMappingService.create_automatic_mappings(unit_id)

            return jsonify(
                {
                    "success": True,
                    "data": {"unit_id": unit_id, "mappings_created": mapping_count},
                }
            )
        else:
            # 全未マッピング単元の一括処理
            stats = UnitItemMappingService.batch_create_mappings()

            return jsonify({"success": True, "data": stats})

    except Exception as e:
        logger.error(f"Mapping creation error: {str(e)}")
        return jsonify({"success": False, "error": "マッピング作成中にエラーが発生しました"}), 500


@data_integrity_bp.route("/mappings/status", methods=["GET"])
@login_required
@admin_required
def get_mapping_status():
    """
    マッピング状況の取得

    Returns:
        マッピング状況のJSON
    """
    try:
        # 未マッピング単元を取得
        unmapped_units = UnitItemMappingService.get_unmapped_units()

        # 全体の統計情報
        stats = db.session.execute(
            """
            SELECT 
                COUNT(DISTINCT cu.id) as total_units,
                COUNT(DISTINCT uim.unit_id) as mapped_units,
                COUNT(uim.id) as total_mappings,
                AVG(uim.weight) as avg_weight
            FROM curriculum_units cu
            LEFT JOIN unit_item_mappings uim ON cu.id = uim.unit_id
            WHERE cu.is_active = 1
        """
        ).fetchone()

        return jsonify(
            {
                "success": True,
                "data": {
                    "stats": {
                        "total_units": stats.total_units,
                        "mapped_units": stats.mapped_units,
                        "unmapped_units": stats.total_units - stats.mapped_units,
                        "total_mappings": stats.total_mappings or 0,
                        "avg_weight": float(stats.avg_weight or 0),
                    },
                    "unmapped_units": unmapped_units[:20],  # 最大20件まで
                },
            }
        )

    except Exception as e:
        logger.error(f"Mapping status error: {str(e)}")
        return jsonify({"success": False, "error": "マッピング状況の取得中にエラーが発生しました"}), 500


@data_integrity_bp.route("/progress/recalculate", methods=["POST"])
@login_required
@admin_required
def recalculate_progress():
    """
    進捗の再計算

    Returns:
        再計算結果のJSON
    """
    try:
        student_id = request.json.get("student_id")
        unit_id = request.json.get("unit_id")

        if student_id and unit_id:
            # 特定の学生・単元の進捗再計算
            success = UnitItemMappingService.update_unit_selection_progress(
                student_id, unit_id
            )

            return jsonify(
                {
                    "success": success,
                    "data": {
                        "student_id": student_id,
                        "unit_id": unit_id,
                        "updated": success,
                    },
                }
            )
        else:
            # バッチ処理（最大100件）
            updated_count = 0
            error_count = 0

            selections = (
                StudentUnitSelection.query.filter(
                    StudentUnitSelection.status.in_(["in_progress", "not_started"])
                )
                .limit(100)
                .all()
            )

            for selection in selections:
                try:
                    if UnitItemMappingService.update_unit_selection_progress(
                        selection.student_id, selection.unit_id
                    ):
                        updated_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    logger.error(
                        f"Progress update error for selection {selection.id}: {str(e)}"
                    )
                    error_count += 1

            return jsonify(
                {
                    "success": True,
                    "data": {
                        "total_processed": len(selections),
                        "updated": updated_count,
                        "errors": error_count,
                    },
                }
            )

    except Exception as e:
        logger.error(f"Progress recalculation error: {str(e)}")
        return jsonify({"success": False, "error": "進捗再計算中にエラーが発生しました"}), 500
