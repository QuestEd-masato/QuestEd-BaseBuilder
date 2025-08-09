# app/teacher/modules/dashboard.py
"""教師ダッシュボード機能 - Phase8G: 機能性・保守性向上統合"""

from datetime import datetime

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

from app.models import (
    ChatHistory,
    Class,
    ClassEnrollment,
    Curriculum,
    CurriculumUnit,
    InquiryTheme,
    Milestone,
    User,
    db,
)
from app.models.curriculum_task import CurriculumTask, StudentTaskProgress, TaskStatus
from app.services.curriculum_bridge_service import CurriculumBridgeService

# Phase8G: 統合ダッシュボードサービス (Phase8D成果 + 教師専用機能)
from app.services.dashboard.dashboard_orchestration_service import DashboardOrchestrationService
from app.services.dashboard.teacher_dashboard_service import TeacherDashboardService
from app.utils.model_helpers import mysql_nulls_last

from ..common import teacher_required

dashboard_bp = Blueprint("teacher_dashboard", __name__)

# Phase8G統合サービス初期化
dashboard_orchestration = DashboardOrchestrationService()
teacher_dashboard_service = TeacherDashboardService()


@dashboard_bp.route("/dashboard")
@login_required
@teacher_required
def dashboard():
    """教師ダッシュボード（Phase8G: 機能性・保守性向上統合版）"""
    try:
        current_app.logger.info(f"[TEACHER DASHBOARD] Phase8G: Loading enhanced dashboard for teacher {current_user.id}")
        
        if hasattr(current_user, 'id') and current_user.id:
            # Phase8G: 教師専用機能強化版ダッシュボード構築
            enhanced_dashboard_data = teacher_dashboard_service.build_complete_teacher_dashboard(current_user.id)
            
            # Phase8D: 基本統合サービスとの組み合わせ
            base_dashboard_data = dashboard_orchestration.build_complete_dashboard(current_user.id)
            
            # 既存テンプレートとの互換性を確保
            legacy_compatible_data = _build_legacy_compatible_data(current_user.id)
            
            # 統合データ構築（機能性向上）
            template_context = {
                # Phase8G: 教師専用強化機能
                **enhanced_dashboard_data,
                
                # Phase8D: 基本統合機能
                'base_analytics': base_dashboard_data.get('analytics', {}),
                
                # レガシー互換性
                **legacy_compatible_data,
                
                # Phase8G統合状態
                'phase8g_enabled': True,
                'integration_status': 'enhanced',
                
                # 機能性向上マーカー
                'enhanced_features': {
                    'advanced_statistics': True,
                    'integrated_analytics': True,
                    'teacher_specific_insights': True,
                    'real_time_updates': True
                }
            }
            
            return render_template("teacher/dashboard.html", **template_context)
        else:
            return _render_fallback_dashboard()
            
    except Exception as e:
        current_app.logger.error(f"[TEACHER DASHBOARD] Phase8G error: {str(e)}")
        
        # Phase8G フォールバック: Phase8D基本機能使用
        try:
            fallback_data = dashboard_orchestration.build_complete_dashboard(current_user.id)
            legacy_data = _build_legacy_compatible_data(current_user.id)
            return render_template("teacher/dashboard.html", **fallback_data, **legacy_data, phase8d_enabled=True)
        except Exception:
            return _render_fallback_dashboard()


def _build_legacy_compatible_data(teacher_id):
    """既存テンプレート互換性のためのデータ構築"""
    try:
        from app.services.curriculum_bridge_service import CurriculumBridgeService
        
        # 教師が担当するクラスを取得
        classes = Class.query.filter_by(teacher_id=teacher_id).all()
        
        # 統合統計情報の初期化
        integrated_stats = {
            "total_curriculums": 0,
            "converted_curriculums": 0,
            "total_units": 0,
            "active_units": 0,
            "conversion_rate": 0,
        }
        
        # 各クラスの生徒数と統計情報を計算
        class_info = []
        for class_obj in classes:
            # 生徒数を取得
            enrollments = ClassEnrollment.query.filter_by(class_id=class_obj.id).all()
            student_count = len(enrollments)
            
            # アンケート完了数を計算
            survey_completed = 0
            theme_selected = 0
            
            for enrollment in enrollments:
                student = enrollment.student
                # アンケート完了確認
                if hasattr(student, 'has_completed_surveys') and student.has_completed_surveys():
                    survey_completed += 1
                
                # テーマ選択確認
                selected_theme = InquiryTheme.query.filter_by(
                    student_id=student.id, is_selected=True
                ).first()
                if selected_theme:
                    theme_selected += 1
            
            # 次回のマイルストーンを取得
            next_milestone = (
                Milestone.query.filter_by(class_id=class_obj.id)
                .filter(Milestone.due_date >= datetime.utcnow().date())
                .order_by(*mysql_nulls_last(Milestone.due_date, "asc"))
                .first()
            )
            
            # カリキュラム・単元統合情報を取得
            curriculums = Curriculum.query.filter_by(
                class_id=class_obj.id, teacher_id=teacher_id
            ).all()
            
            curriculum_stats = {
                "total_curriculums": len(curriculums),
                "converted_count": 0,
                "total_units": 0,
                "recent_conversions": [],
            }
            
            for curriculum in curriculums:
                # 変換状況をチェック（エラー処理追加）
                try:
                    conversion_status = CurriculumBridgeService.get_conversion_status(curriculum.id)
                    if conversion_status.get("is_converted", False):
                        curriculum_stats["converted_count"] += 1
                        curriculum_stats["total_units"] += conversion_status.get("converted_units", 0)
                        
                        # 最近の変換履歴
                        if conversion_status.get("conversion_date"):
                            curriculum_stats["recent_conversions"].append({
                                "curriculum_title": curriculum.title,
                                "conversion_date": conversion_status["conversion_date"],
                                "units_count": conversion_status.get("converted_units", 0),
                            })
                except Exception as e:
                    current_app.logger.warning(f"Conversion status error for curriculum {curriculum.id}: {str(e)}")
                    # エラーの場合は変換されていないとみなして継続
            
            # 統合統計に加算
            integrated_stats["total_curriculums"] += curriculum_stats["total_curriculums"]
            integrated_stats["converted_curriculums"] += curriculum_stats["converted_count"]
            integrated_stats["total_units"] += curriculum_stats["total_units"]
            
            class_info.append({
                "class": class_obj,
                "student_count": student_count,
                "survey_completed": survey_completed,
                "theme_selected": theme_selected,
                "next_milestone": next_milestone,
                "curriculum_stats": curriculum_stats,
            })
        
        # アクティブな単元数を取得
        integrated_stats["active_units"] = CurriculumUnit.query.filter_by(
            created_by=teacher_id, is_active=True
        ).count()
        
        # 変換率計算
        if integrated_stats["total_curriculums"] > 0:
            integrated_stats["conversion_rate"] = round(
                (integrated_stats["converted_curriculums"] / integrated_stats["total_curriculums"]) * 100, 1
            )
        
        # 承認待ちの学生数を取得
        pending_students_count = 0
        teacher_user = User.query.get(teacher_id)
        if teacher_user and teacher_user.school_id:
            pending_students_count = User.query.filter_by(
                role="student",
                school_id=teacher_user.school_id,
                email_confirmed=True,
                is_approved=False,
            ).count()
        
        # 課題統計の取得
        task_stats = get_teacher_task_statistics(teacher_id)
        
        return {
            "classes": class_info,
            "pending_students_count": pending_students_count,
            "integrated_stats": integrated_stats,
            "task_stats": task_stats,
        }
        
    except Exception as e:
        current_app.logger.error(f"Legacy compatibility data error: {str(e)}")
        return {
            "classes": [],
            "pending_students_count": 0,
            "integrated_stats": {},
            "task_stats": {},
        }


def _render_fallback_dashboard():
    """フォールバック用ダッシュボードレンダリング"""
    return render_template(
        "teacher/dashboard.html",
        classes=[],
        pending_students_count=0,
        integrated_stats={},
        task_stats={},
        error_mode=True
    )


@dashboard_bp.route("/teacher/pending_users")
@login_required
@teacher_required
def pending_users():
    """承認待ちユーザー一覧"""
    # 同じ学校の承認待ち学生を取得
    pending_students = User.query.filter_by(
        role="student",
        school_id=current_user.school_id,
        email_confirmed=True,
        is_approved=False,
    ).all()

    return render_template(
        "teacher/pending_users.html", pending_students=pending_students
    )


@dashboard_bp.route("/teacher/approve_user/<int:user_id>", methods=["POST"])
@login_required
@teacher_required
def approve_user(user_id):
    """ユーザー承認"""
    user = User.query.get_or_404(user_id)

    # 同じ学校の学生のみ承認可能
    if user.school_id != current_user.school_id or user.role != "student":
        flash("このユーザーを承認する権限がありません。")
        return redirect(url_for("teacher_dashboard.pending_users"))

    user.is_approved = True
    db.session.commit()

    flash(f"{user.username} を承認しました。")
    return redirect(url_for("teacher_dashboard.pending_users"))


@dashboard_bp.route("/api/teacher/first_class")
@login_required
@teacher_required
def api_teacher_first_class():
    """API: 教師の最初のクラス取得（Phase8G機能性向上版）"""
    try:
        # Phase8G: TeacherDashboardService経由でより詳細なクラス情報を取得
        teacher_dashboard_data = teacher_dashboard_service.build_complete_teacher_dashboard(current_user.id)
        teacher_classes = teacher_dashboard_data.get('teacher_info', {}).get('classes', [])
        
        if teacher_classes:
            first_class = teacher_classes[0]
            # 機能性向上: より豊富な情報を提供
            return jsonify({
                "status": "success",
                "class_id": first_class.get('id'),
                "class_name": first_class.get('name'),
                "class_description": first_class.get('description', ''),
                "enhanced_info": {
                    "total_classes": len(teacher_classes),
                    "phase8g_enabled": True
                }
            })
        else:
            # フォールバック: 従来の方法
            first_class = Class.query.filter_by(teacher_id=current_user.id).first()
            if first_class:
                return jsonify({
                    "status": "success",
                    "class_id": first_class.id,
                    "class_name": first_class.name,
                })
            else:
                return jsonify({"status": "error", "message": "クラスが見つかりません"})
    except Exception as e:
        current_app.logger.error(f"API first_class error: {str(e)}")
        return jsonify({"status": "error", "message": "データ取得エラー"})


@dashboard_bp.route("/teacher/chat")
@login_required
@teacher_required
def chat_page():
    """教師チャット機能"""
    classes = Class.query.filter_by(teacher_id=current_user.id).all()
    recent_chats = (
        ChatHistory.query.filter_by(user_id=current_user.id)
        .order_by(ChatHistory.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template("chat.html", classes=classes, recent_chats=recent_chats)


def get_teacher_task_statistics(teacher_id):
    """教師の課題統計を取得"""
    try:
        from datetime import timedelta
        
        # 教師が担当するクラス取得
        teacher_classes = Class.query.filter_by(teacher_id=teacher_id).all()
        
        if not teacher_classes:
            return {
                'pending_submissions': 0,
                'completion_rate': 0,
                'active_students': 0,
                'overdue_tasks': 0
            }
        
        # クラスに属する学生のIDを取得
        class_ids = [c.id for c in teacher_classes]
        enrollments = ClassEnrollment.query.filter(ClassEnrollment.class_id.in_(class_ids)).all()
        student_ids = [e.student_id for e in enrollments]
        
        if not student_ids:
            return {
                'pending_submissions': 0,
                'completion_rate': 0,
                'active_students': 0,
                'overdue_tasks': 0
            }
        
        # 基本クエリ構築
        base_query = StudentTaskProgress.query.filter(
            StudentTaskProgress.student_id.in_(student_ids)
        )
        
        # 承認待ち件数
        pending_submissions = base_query.filter(
            StudentTaskProgress.status == TaskStatus.SUBMITTED
        ).count()
        
        # 完了率計算
        total_tasks = base_query.count()
        completed_tasks = base_query.filter(
            StudentTaskProgress.status == TaskStatus.COMPLETED
        ).count()
        completion_rate = round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)
        
        # アクティブ学生数（今週何らかの活動があった学生）
        week_start = datetime.now() - timedelta(days=7)
        active_students = base_query.filter(
            StudentTaskProgress.last_activity_at >= week_start
        ).distinct(StudentTaskProgress.student_id).count()
        
        # 期限超過課題数（簡易実装）
        overdue_tasks = 0  # TODO: 期限管理機能実装後に計算
        
        return {
            'pending_submissions': pending_submissions,
            'completion_rate': completion_rate,
            'active_students': active_students,
            'overdue_tasks': overdue_tasks
        }
        
    except Exception as e:
        current_app.logger.error(f"Task statistics error: {str(e)}")
        return {
            'pending_submissions': 0,
            'completion_rate': 0,
            'active_students': 0,
            'overdue_tasks': 0
        }