# app/student/modules/dashboard.py
"""学生ダッシュボード機能 - Phase8E対応ファサード"""

import logging
import traceback
from datetime import datetime, timedelta

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
from sqlalchemy import func, text

from app.models import (
    ActivityLog,
    ChatHistory,
    Class,
    ClassEnrollment,
    CurriculumUnit,
    Goal,
    InquiryTheme,
    InterestSurvey,
    MainTheme,
    PersonalitySurvey,
    Todo,
    User,
    db,
)

# Phase6-B: 既存Dashboard Service Layer Import
from app.services import DashboardService, DashboardRendererService, StudentInfoService

# Phase8E: 学生ダッシュボード専門サービス統合
from app.services.student_dashboard.dashboard_presentation_service import DashboardPresentationService
from app.services.student_dashboard.learning_progress_service import LearningProgressService
from app.services.student_dashboard.basebuilder_analytics_service import BaseBuilderAnalyticsService
from app.services.student_dashboard.curriculum_analytics_service import CurriculumAnalyticsService
from app.services.student_dashboard.student_ranking_service import StudentRankingService

from app.utils.model_helpers import mysql_nulls_last
from basebuilder.models import WordProficiency

from ..utils import (
    get_current_student_classes,
    get_student_survey_status,
    get_student_theme_status,
    student_required,
)

dashboard_bp = Blueprint("student_dashboard", __name__)

# Phase8E: 専門サービス初期化
presentation_service = DashboardPresentationService()
progress_service = LearningProgressService()
basebuilder_service = BaseBuilderAnalyticsService()
curriculum_service = CurriculumAnalyticsService()
ranking_service = StudentRankingService()

# Phase6-B: 既存サービス（後方互換性）
legacy_dashboard_service = DashboardService()
legacy_renderer_service = DashboardRendererService()
legacy_student_info_service = StudentInfoService()


def _get_student_classes():
    """学生の履修クラスを取得（既存互換性）"""
    enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
    classes = [enrollment.class_obj for enrollment in enrollments]

    # ClassEnrollmentが空の場合、User.class_idから取得を試行
    if not classes and current_user.class_id:
        direct_class = Class.query.get(current_user.class_id)
        if direct_class:
            classes = [direct_class]
            current_app.logger.info(
                f"[DASHBOARD] Student {current_user.id}: Using direct class_id {current_user.class_id}"
            )

    # デバッグ情報をログに記録
    current_app.logger.info(
        f"[DASHBOARD] Student {current_user.id} ({current_user.username}): "
        f"Found {len(enrollments)} enrollments, {len(classes)} classes, class_id={current_user.class_id}"
    )

    return classes


@dashboard_bp.route("/dashboard")
@login_required
@student_required
def dashboard():
    """
    学生ダッシュボード（Phase8E統合ファサード）
    Phase6-B互換性を維持しつつ、Phase8E専門サービスを活用
    """
    try:
        # Phase8E: 専門サービス統合
        current_app.logger.info(f"[DASHBOARD] Phase8E: Loading dashboard for student {current_user.id}")
        
        # 基本的なクラス情報を取得
        classes = _get_student_classes()
        if not classes:
            flash("履修しているクラスがありません。先生に連絡して、クラスに登録してもらってください。")
            return render_template(
                "student/dashboard_minimal.html",
                student_info={"class_count": 0},
                classes=[],
            )
        
        # Phase8E: 並列データ取得（パフォーマンス最適化）
        dashboard_data = {}
        
        # 学習進捗データ
        dashboard_data["learning_progress"] = progress_service.get_lesson_progress_summary(current_user.id)
        dashboard_data["progress_statistics"] = progress_service.get_progress_statistics(current_user.id)
        dashboard_data["completion_requirements"] = progress_service.calculate_completion_requirements(current_user.id)
        
        # BaseBuilder統計
        dashboard_data["basebuilder_stats"] = basebuilder_service.generate_vocabulary_stats(current_user.id)
        dashboard_data["proficiency_breakdown"] = basebuilder_service.calculate_proficiency_breakdown(current_user.id)
        dashboard_data["weekly_basebuilder_metrics"] = basebuilder_service.get_weekly_learning_metrics(current_user.id)
        
        # カリキュラム統計
        dashboard_data["curriculum_stats"] = curriculum_service.generate_unit_statistics(current_user.id)
        dashboard_data["class_curriculum_progress"] = curriculum_service.get_class_curriculum_progress(current_user.id)
        dashboard_data["study_time_estimates"] = curriculum_service.calculate_study_time_estimates(current_user.id)
        
        # ランキングデータ
        class_ids = [c.id for c in classes]
        dashboard_data["ranking_data"] = {
            "class_top_learners": ranking_service.get_class_top_learners(class_ids),
            "weekly_top_learners": ranking_service.get_weekly_top_learners(class_ids),
            "my_ranking_metrics": ranking_service.calculate_ranking_metrics(current_user.id)
        }
        
        # Phase6-B互換性データ（既存サービス使用）
        legacy_dashboard_data = legacy_dashboard_service.build_dashboard_data(current_user.id)
        rendered_sections = legacy_renderer_service.render_complete_dashboard(legacy_dashboard_data)
        
        # Phase8E: 統合データにクラス情報追加
        dashboard_data["classes"] = classes
        dashboard_data["student_info"] = legacy_student_info_service.build_student_basic_info(current_user.id)
        
        # テンプレート表示（Phase8E Presentation Service使用）
        return presentation_service.render_main_dashboard(current_user.id, dashboard_data)
        
    except Exception as e:
        current_app.logger.error(f"[DASHBOARD] Error for student {current_user.id}: {str(e)}")
        current_app.logger.error(f"[DASHBOARD] Traceback: {traceback.format_exc()}")
        flash("ダッシュボードの読み込み中にエラーが発生しました。", "error")
        return presentation_service.render_minimal_dashboard(current_user.id)


@dashboard_bp.route("/dashboard_minimal")
@login_required
@student_required
def dashboard_minimal():
    """最小限のダッシュボード（エラー時のフォールバック）"""
    try:
        # Phase8E: Presentation Service使用
        return presentation_service.render_minimal_dashboard(current_user.id)
    except Exception as e:
        current_app.logger.error(f"Minimal dashboard error: {str(e)}")
        return render_template(
            "student/dashboard_minimal.html",
            student_info={"class_count": 0},
            classes=[],
        )


@dashboard_bp.route("/debug/role")
@login_required
def debug_role():
    """デバッグ用: ユーザーのロール情報を表示"""
    info = {
        "user_id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "is_authenticated": current_user.is_authenticated,
        "is_active": current_user.is_active,
        "class_id": current_user.class_id,
    }
    return jsonify(info)


@dashboard_bp.route("/debug/routes")
@login_required
def debug_routes():
    """デバッグ用: 登録されているルート一覧を表示"""
    routes = []
    for rule in current_app.url_map.iter_rules():
        routes.append({
            "endpoint": rule.endpoint,
            "methods": list(rule.methods),
            "rule": str(rule),
        })
    return jsonify(routes)


@dashboard_bp.route("/api/dashboard/quick-stats")
@login_required
@student_required
def api_quick_stats():
    """ダッシュボード用のクイック統計API（Phase8E対応）"""
    try:
        # 基本統計
        stats = {
            "activities_count": ActivityLog.query.filter_by(
                student_id=current_user.id
            ).count(),
            "todos_pending": Todo.query.filter_by(
                student_id=current_user.id, is_completed=False
            ).count(),
            "goals_active": Goal.query.filter_by(
                student_id=current_user.id, is_completed=False
            ).count(),
            "classes_enrolled": ClassEnrollment.query.filter_by(
                student_id=current_user.id
            ).count(),
        }

        # Phase8E: 学習進捗統計（専門サービス使用）
        try:
            learning_progress = progress_service.get_lesson_progress_summary(current_user.id)
            learning_stats = {
                "curricula_available": learning_progress["stats"]["total_selected"],
                "curricula_completed": learning_progress["stats"]["completed"],
                "curricula_in_progress": learning_progress["stats"]["in_progress"],
                "completion_rate": learning_progress["stats"]["completion_rate"],
            }
            stats.update(learning_stats)
        except Exception as stats_e:
            current_app.logger.error(f"Learning stats error: {str(stats_e)}")
            # フォールバック値
            stats.update({
                "curricula_available": 0,
                "curricula_completed": 0,
                "curricula_in_progress": 0,
                "completion_rate": 0,
            })

        return jsonify({"success": True, "stats": stats})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Phase8E: レガシー関数を内部ヘルパーに変換（外部アクセス不可）
def _get_learning_progress_summary():
    """レガシー関数 - Phase8E Service経由で実装"""
    return progress_service.get_lesson_progress_summary(current_user.id)


def _build_student_basic_info_legacy(classes):
    """
    学生の基本情報を構築（レガシー版）
    Phase8E: 後方互換性のため復帰、StudentInfoService経由で実装
    """
    try:
        # Phase8E: レガシーサービス経由で基本情報を取得
        basic_info = legacy_student_info_service.get_student_info(current_user.id)
        
        # レガシー形式に変換
        student_info = {
            "has_completed_surveys": basic_info.get("survey_completed", False),
            "selected_theme": basic_info.get("selected_theme"),
            "recent_activities": basic_info.get("recent_activities", [])[:5],
            "pending_todos": basic_info.get("pending_todos", [])[:5],
            "active_goals": basic_info.get("active_goals", [])[:5],
            "class_count": len(classes),
        }
        
        return student_info
    except Exception as e:
        current_app.logger.error(f"[DASHBOARD] Legacy student info error: {str(e)}")
        return {
            "has_completed_surveys": False,
            "selected_theme": None,
            "recent_activities": [],
            "pending_todos": [],
            "active_goals": [],
            "class_count": len(classes),
        }


def _build_legacy_class_details(classes):
    """後方互換性のため、従来のclass_details形式を構築"""
    class_details = []
    for class_obj in classes:
        try:
            # メインテーマを取得
            main_themes = MainTheme.query.filter_by(class_id=class_obj.id).all()
            
            # マイルストーンを取得
            try:
                from app.models import Milestone
                next_milestone = (
                    Milestone.query.filter_by(class_id=class_obj.id)
                    .filter(Milestone.due_date >= datetime.now().date())
                    .order_by(*mysql_nulls_last(Milestone.due_date, "asc"))
                    .first()
                )
            except Exception:
                next_milestone = None
            
            # チャット履歴を取得
            try:
                latest_chat = (
                    ChatHistory.query.filter_by(
                        user_id=current_user.id, class_id=class_obj.id
                    )
                    .order_by(ChatHistory.created_at.desc())
                    .first()
                )
            except Exception:
                latest_chat = None
            
            class_detail = {
                "class": class_obj,
                "main_themes": main_themes,
                "next_milestone": next_milestone,
                "latest_chat": latest_chat,
            }
            class_details.append(class_detail)
            
        except Exception:
            # エラー時は基本情報のみ
            class_details.append({
                "class": class_obj,
                "main_themes": [],
                "next_milestone": None,
                "latest_chat": None,
            })
    
    return class_details


def _build_legacy_class_themes(classes):
    """後方互換性のため、従来のall_class_themes形式を構築"""
    all_class_themes = []
    for class_obj in classes:
        try:
            main_themes = MainTheme.query.filter_by(class_id=class_obj.id).all()
            theme_title = main_themes[0].title if main_themes else None
            
            class_theme = {
                "class_id": class_obj.id,
                "class_name": class_obj.name,
                "theme_title": theme_title,
            }
            all_class_themes.append(class_theme)
        except Exception:
            # エラー時は基本情報のみ
            all_class_themes.append({
                "class_id": class_obj.id,
                "class_name": class_obj.name,
                "theme_title": None,
            })
    
    return all_class_themes


def _generate_weekly_activity_stats():
    """レガシー関数 - Phase8E統合により簡略化"""
    try:
        # Phase8E: ActivityAnalyticsServiceに相当する機能
        # ここでは簡易実装
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        daily_activities = (
            db.session.query(
                func.date(ActivityLog.created_at).label("date"),
                func.count(ActivityLog.id).label("count"),
            )
            .filter(
                ActivityLog.student_id == current_user.id,
                ActivityLog.created_at >= start_date,
                ActivityLog.created_at <= end_date,
            )
            .group_by(func.date(ActivityLog.created_at))
            .all()
        )
        
        # 7日分のデータを準備
        stats = []
        for i in range(7):
            date = (start_date + timedelta(days=i)).date()
            count = 0
            
            for activity in daily_activities:
                if activity.date == date:
                    count = activity.count
                    break
            
            stats.append({"date": date.strftime("%m/%d"), "count": count})
        
        return stats
        
    except Exception as e:
        current_app.logger.error(f"Weekly activity stats error: {str(e)}")
        return []


def _generate_progress_stats():
    """レガシー関数 - Phase8E Service経由で実装"""
    return progress_service.get_progress_statistics(current_user.id)


def _get_weekly_top_learners(classes):
    """レガシー関数 - Phase8E Service経由で実装"""
    class_ids = [c.id for c in classes]
    return ranking_service.get_weekly_top_learners(class_ids)


def get_class_top_learners(classes):
    """レガシー関数 - Phase8E Service経由で実装（外部互換性維持）"""
    class_ids = [c.id for c in classes]
    return ranking_service.get_class_top_learners(class_ids)


def _generate_basebuilder_stats():
    """レガシー関数 - Phase8E Service経由で実装"""
    return basebuilder_service.generate_vocabulary_stats(current_user.id)


def _generate_unit_stats():
    """レガシー関数 - Phase8E Service経由で実装"""
    return curriculum_service.generate_unit_statistics(current_user.id)


def _get_difficulty_label(level):
    """難易度ラベル取得（ユーティリティ関数）"""
    difficulty_map = {
        1: "初級",
        2: "中級",
        3: "上級",
        4: "発展",
        5: "探究",
    }
    return difficulty_map.get(level, "不明")


# Phase8E: サービス状態確認（デバッグ用）
@dashboard_bp.route("/api/dashboard/service-status")
@login_required
@student_required
def api_service_status():
    """Phase8E サービス状態確認API"""
    try:
        service_status = {
            "presentation": presentation_service.get_service_status(),
            "progress": progress_service.get_service_status(),
            "basebuilder": basebuilder_service.get_service_status(),
            "curriculum": curriculum_service.get_service_status(),
            "ranking": ranking_service.get_service_status(),
            "phase8e_enabled": True,
            "checked_at": datetime.now().isoformat()
        }
        return jsonify({"success": True, "services": service_status})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500