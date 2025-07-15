"""
Admin and Teacher API
====================
Phase 4.3: API分割実装 - 管理者・教師API

責任:
- 教師情報取得
- データエクスポート機能

移行元ルート: /teacher/first_class, /export/evaluations
"""

import logging
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.models import Class, ClassEnrollment, StudentEvaluation, db
from app.utils.rate_limiting import api_limit

admin_teacher_bp = Blueprint("admin_teacher", __name__)


@admin_teacher_bp.route("/teacher/first_class", methods=["GET"])
@login_required
@api_limit()
def get_first_class():
    """教師の最初のクラス取得API"""
    try:
        if current_user.role != "teacher":
            return jsonify({"status": "error", "message": "この機能は教師のみ利用できます"}), 403

        first_class = Class.query.filter_by(teacher_id=current_user.id).first()

        if not first_class:
            return jsonify({"status": "error", "message": "クラスが見つかりません"}), 404

        return jsonify(
            {
                "status": "success",
                "class": {"id": first_class.id, "name": first_class.name},
            }
        )

    except Exception as e:
        logging.error(f"Get first class error: {str(e)}")
        return jsonify({"status": "error", "message": "エラーが発生しました"}), 500


@admin_teacher_bp.route("/export/evaluations", methods=["POST"])
@login_required
@api_limit()
def export_evaluations():
    """評価データエクスポートAPI"""
    try:
        if current_user.role not in ["teacher", "admin"]:
            return jsonify({"status": "error", "message": "この機能は教師・管理者のみ利用できます"}), 403

        # TODO: エクスポート実装
        return jsonify({"status": "success", "message": "エクスポートを開始しました"})

    except Exception as e:
        logging.error(f"Export evaluations error: {str(e)}")
        return jsonify({"status": "error", "message": "エラーが発生しました"}), 500
