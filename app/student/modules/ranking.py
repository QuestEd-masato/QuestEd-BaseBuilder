# app/student/modules/ranking.py
"""学生ランキング詳細機能"""

import logging
from datetime import datetime, timedelta

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
from sqlalchemy import desc, func

from app.models import Class, ClassEnrollment, User, db
from basebuilder.models import AnswerRecord, WordProficiency

from ..utils import student_required

ranking_bp = Blueprint("student_ranking", __name__)


@ranking_bp.route("/ranking")
@login_required
@student_required
def ranking():
    """基礎学力マスターランキング詳細ページ"""
    try:
        # 学生が履修しているクラスを取得
        enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
        classes = [enrollment.class_obj for enrollment in enrollments]

        # ClassEnrollmentが空の場合、User.class_idから取得を試行
        if not classes and current_user.class_id:
            direct_class = Class.query.get(current_user.class_id)
            if direct_class:
                classes = [direct_class]

        if not classes:
            flash("所属クラスが見つかりません。先生に連絡して、クラスに登録してもらってください。")
            return redirect(url_for("student_dashboard.dashboard"))

        class_ids = [cls.id for cls in classes]

        # RankingServiceを使用してランキングを取得
        ranking_type = request.args.get("type", "total_points")
        scope = request.args.get("scope", "school")  # デフォルトを学校全体に変更

        # RankingServiceから正しいポイントベースのランキングを取得
        from app.services.ranking_service import RankingService

        try:
            ranking_data = RankingService.get_ranking(
                ranking_type=ranking_type,
                scope=scope,
                scope_id=class_ids[0] if scope == "class" and class_ids else None,
                limit=20,
            )

            # 自分の順位を検索
            my_rank = None
            if ranking_data.get("rankings"):
                for idx, student in enumerate(ranking_data["rankings"]):
                    if student["student_id"] == current_user.id:
                        total_participants = ranking_data.get(
                            "total_participants", len(ranking_data["rankings"])
                        )
                        percentile = round(
                            (total_participants - student["rank"] + 1)
                            / total_participants
                            * 100
                        )
                        my_rank = {
                            "rank": student["rank"],
                            "score": student["score"],
                            "total_participants": total_participants,
                            "percentile": percentile,
                        }
                        break

        except Exception as e:
            current_app.logger.error(f"RankingService error: {str(e)}")
            # フォールバック: 空のランキングデータ
            ranking_data = {
                "rankings": [],
                "total_participants": 0,
                "last_updated": datetime.utcnow().isoformat(),
            }
            my_rank = None

        return render_template(
            "student/ranking.html",
            ranking_data=ranking_data,
            ranking_type=ranking_type,
            scope=scope,
            my_rank=my_rank,
            student_classes=classes,
        )

    except Exception as e:
        current_app.logger.error(f"Ranking page error: {str(e)}")
        flash("ランキング情報の取得中にエラーが発生しました。", "error")
        return redirect(url_for("student_dashboard.dashboard"))


# RankingService に置き換えられた古い関数
# _get_overall_ranking, _get_monthly_ranking, _get_weekly_ranking は削除

# 削除済み: _get_monthly_ranking, _get_weekly_ranking


@ranking_bp.route("/ranking_analysis")
@login_required
@student_required
def ranking_analysis():
    """ランキング分析ページ（学生用）- rankingページにリダイレクト"""
    flash("学生用のランキング詳細ページにアクセスしています。", "info")
    return redirect(url_for("student_ranking.ranking"))


# 削除済み: _get_my_position (RankingServiceに統合)
