"""
Student Tools API
=================
Phase 4.3: API分割実装 - 学生ツールAPI

責任:
- 探究テーマ選択
- TODO管理
- 目標進捗更新

移行元ルート: /theme/*/select, /todo/*/toggle, /goal/*/progress

注意: この API は app/student/modules の実装済み機能への
     プロキシとして機能します（重複コード削減のため）
"""

import logging
from datetime import datetime

from flask import Blueprint, jsonify, request, redirect, url_for
from flask_login import current_user, login_required

from app.models import Goal, InquiryTheme, Todo, db
from app.utils.rate_limiting import api_limit

# 実装済み機能をインポート
try:
    from app.student.modules.goals_todos import toggle_todo_completion
    from app.student.modules.themes import select_theme as select_theme_impl
    DELEGATION_AVAILABLE = True
except ImportError as e:
    # フォールバック用のログ記録
    logging.warning(f"Student module functions not available for delegation: {e}")
    DELEGATION_AVAILABLE = False

student_tools_bp = Blueprint("student_tools", __name__)


@student_tools_bp.route("/theme/<int:theme_id>/select", methods=["POST"])
@login_required
@api_limit()
def select_theme(theme_id):
    """探究テーマ選択API - student.themes.select_theme への委譲"""
    try:
        if DELEGATION_AVAILABLE:
            # 実装済みの関数に委譲
            return select_theme_impl(theme_id)
        else:
            logging.error("Theme selection delegation not available")
            return jsonify({"status": "error", "message": "機能が利用できません"}), 503
    except Exception as e:
        logging.error(f"Select theme error: {str(e)}")
        return jsonify({"status": "error", "message": "エラーが発生しました"}), 500


@student_tools_bp.route("/todo/<int:todo_id>/toggle", methods=["POST"])
@login_required
@api_limit()
def toggle_todo(todo_id):
    """TODO切り替えAPI - student.goals_todos.toggle_todo_completion への委譲"""
    try:
        if DELEGATION_AVAILABLE:
            # 実装済みの関数に委譲
            return toggle_todo_completion(todo_id)
        else:
            logging.error("Todo toggle delegation not available")
            return jsonify({"status": "error", "message": "機能が利用できません"}), 503
    except Exception as e:
        logging.error(f"Toggle todo error: {str(e)}")
        return jsonify({"status": "error", "message": "エラーが発生しました"}), 500


@student_tools_bp.route("/goal/<int:goal_id>/progress", methods=["POST"])
@login_required
@api_limit()
def update_goal_progress(goal_id):
    """目標進捗更新API"""
    try:
        # 目標の存在確認とアクセス権チェック
        goal = Goal.query.filter_by(id=goal_id, student_id=current_user.id).first()
        if not goal:
            return jsonify({"status": "error", "message": "目標が見つからないか、アクセス権限がありません"}), 404

        # リクエストデータの取得
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "無効なリクエストデータです"}), 400

        # 進捗値の取得とバリデーション
        progress = data.get('progress')
        if progress is None:
            return jsonify({"status": "error", "message": "進捗値が指定されていません"}), 400
        
        try:
            progress = int(progress)
            if progress < 0 or progress > 100:
                return jsonify({"status": "error", "message": "進捗値は0-100の範囲で指定してください"}), 400
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "進捗値は数値で指定してください"}), 400

        # 進捗の更新
        goal.progress = progress
        goal.updated_at = datetime.now()
        
        # 完了状態の自動設定
        if progress == 100:
            goal.is_completed = True
        elif progress < 100 and goal.is_completed:
            goal.is_completed = False

        db.session.commit()

        logging.info(f"Goal progress updated: goal_id={goal_id}, progress={progress}, user_id={current_user.id}")
        return jsonify({
            "status": "success", 
            "message": "目標進捗を更新しました",
            "progress": progress,
            "is_completed": goal.is_completed
        })

    except Exception as e:
        db.session.rollback()
        logging.error(f"Update goal progress error: {str(e)}")
        return jsonify({"status": "error", "message": "エラーが発生しました"}), 500
