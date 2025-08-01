# app/teacher/modules/task_management.py
"""教師タスク管理機能 - Phase7-2リファクタリング版"""

from datetime import datetime, timedelta
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import and_, desc, func

from app.models import (
    Class, ClassEnrollment, Curriculum, User, db, StudentUnitSelection, CurriculumUnit
)
from flask import jsonify
# 新カリキュラムタスクシステムは削除済み
CurriculumTask = None
StudentTaskProgress = None
TaskStatus = None
from ..common import teacher_required
# Phase7-2: 新しいサービス層のインポート
from app.services import (
    TeacherTaskStatisticsService,
    TeacherProgressService,
    TeacherApprovalService
)

task_management_bp = Blueprint("teacher_task_management", __name__)


@task_management_bp.route("/pending-task-approvals")
@login_required
@teacher_required
def pending_task_approvals():
    """課題承認画面"""
    try:
        return render_template("teacher/pending_task_approvals.html")
    except Exception as e:
        current_app.logger.error(f"Pending task approvals error: {str(e)}")
        flash("課題承認画面の読み込み中にエラーが発生しました。", "error")
        return redirect(url_for("teacher_dashboard.dashboard"))


@task_management_bp.route("/task-management")
@login_required
@teacher_required
def task_management():
    """課題管理ダッシュボード"""
    try:
        # フィルター条件取得
        class_filter = request.args.get('class_id', type=int)
        curriculum_filter = request.args.get('curriculum_id', type=int)
        status_filter = request.args.get('status')
        week_filter = request.args.get('week', type=int)

        # 教師が担当するクラス取得
        teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
        
        # 教師が作成したカリキュラム取得
        teacher_curricula = Curriculum.query.filter_by(created_by=current_user.id).all()

        # Phase7-2: サービス層を使用した統計データの計算
        statistics_service = TeacherTaskStatisticsService()
        stats = statistics_service.calculate_teacher_statistics(
            teacher_classes, class_filter, curriculum_filter, status_filter
        )
        
        # Phase7-2: サービス層を使用したクラス別進捗データの取得
        progress_service = TeacherProgressService()
        classes_progress = progress_service.get_classes_progress(
            teacher_classes, class_filter, curriculum_filter, week_filter
        )
        
        # Phase7-2: サービス層を使用した承認待ち課題詳細の取得
        approval_service = TeacherApprovalService()
        pending_submissions = approval_service.get_pending_submissions(
            teacher_classes, class_filter, curriculum_filter, status_filter
        )

        return render_template(
            "teacher/task_management.html",
            teacher_classes=teacher_classes,
            teacher_curricula=teacher_curricula,
            pending_submissions_count=stats['pending_submissions'],
            completion_rate=stats['completion_rate'],
            active_students_count=stats['active_students'],
            overdue_tasks_count=stats['overdue_tasks'],
            classes_progress=classes_progress,
            pending_submissions_detail=pending_submissions
        )

    except Exception as e:
        current_app.logger.error(f"Task management error: {str(e)}")
        flash("課題管理ダッシュボードの読み込み中にエラーが発生しました。", "error")
        return redirect(url_for("teacher_dashboard.dashboard"))


@task_management_bp.route("/submission/<int:submission_id>/detail")
@login_required
@teacher_required
def submission_detail(submission_id):
    """個別課題提出詳細"""
    try:
        # Phase7-2: サービス層を使用した提出詳細取得
        approval_service = TeacherApprovalService()
        submission_detail_data = approval_service.get_submission_detail(str(submission_id))
        
        if not submission_detail_data:
            flash("提出詳細が見つかりません。", "error")
            return redirect(url_for("teacher_task_management.task_management"))

        return render_template(
            "teacher/task_submission_detail.html",
            **submission_detail_data
        )

    except Exception as e:
        current_app.logger.error(f"Submission detail error: {str(e)}")
        flash("提出詳細の読み込み中にエラーが発生しました。", "error")
        return redirect(url_for("teacher_task_management.task_management"))


@task_management_bp.route("/class/<int:class_id>/progress")
@login_required
@teacher_required
def class_progress(class_id):
    """クラス別進捗詳細"""
    try:
        # Phase7-2: サービス層を使用したクラス進捗詳細取得
        progress_service = TeacherProgressService()
        class_progress_data = progress_service.get_class_progress_detail(class_id)
        
        if 'error' in class_progress_data:
            flash("アクセス権限がありません。", "error")
            return redirect(url_for("teacher_task_management.task_management"))

        return render_template(
            "teacher/class_progress.html",
            class_obj={
                'id': class_progress_data['class_id'],
                'name': class_progress_data['class_name']
            },
            students_progress=class_progress_data['students_progress']
        )

    except Exception as e:
        current_app.logger.error(f"Class progress error: {str(e)}")
        flash("クラス進捗の読み込み中にエラーが発生しました。", "error")
        return redirect(url_for("teacher_task_management.task_management"))


@task_management_bp.route("/api/submission/<submission_id>/approve", methods=['POST'])
@login_required
@teacher_required
def approve_unit_submission(submission_id):
    """レッスン単元完了申請の承認"""
    try:
        # Phase7-2: サービス層を使用した承認処理
        approval_service = TeacherApprovalService()
        approval_data = request.get_json() or {}
        
        result = approval_service.approve_submission(submission_id, approval_data)
        
        if result['success']:
            return jsonify({
                'status': 'success',
                'message': result['message']
            })
        else:
            status_code = 404 if '見つかりません' in result['error'] else 403 if '権限' in result['error'] else 400
            return jsonify({
                'status': 'error',
                'message': result['error']
            }), status_code
            
    except Exception as e:
        current_app.logger.error(f"[APPROVAL] Error approving submission {submission_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': 'システムエラーが発生しました'}), 500


@task_management_bp.route("/api/submission/<submission_id>/reject", methods=['POST'])
@login_required
@teacher_required
def reject_unit_submission(submission_id):
    """レッスン単元完了申請の却下"""
    try:
        # Phase7-2: サービス層を使用した却下処理
        approval_service = TeacherApprovalService()
        rejection_data = request.get_json() or {}
        
        result = approval_service.reject_submission(submission_id, rejection_data)
        
        if result['success']:
            return jsonify({
                'status': 'success', 
                'message': result['message']
            })
        else:
            status_code = 404 if '見つかりません' in result['error'] else 403 if '権限' in result['error'] else 400
            return jsonify({
                'status': 'error',
                'message': result['error']
            }), status_code
            
    except Exception as e:
        current_app.logger.error(f"[REJECTION] Error rejecting submission {submission_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': 'システムエラーが発生しました'}), 500


# Phase7-2追加: 統計APIエンドポイント（オプション）
@task_management_bp.route("/api/statistics")
@login_required
@teacher_required
def get_statistics_api():
    """統計データAPI"""
    try:
        class_filter = request.args.get('class_id', type=int)
        curriculum_filter = request.args.get('curriculum_id', type=int)
        
        teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
        statistics_service = TeacherTaskStatisticsService()
        
        stats = statistics_service.calculate_teacher_statistics(
            teacher_classes, class_filter, curriculum_filter
        )
        
        return jsonify({
            'status': 'success',
            'data': stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Statistics API error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'システムエラーが発生しました'
        }), 500


# Phase7-2追加: 承認履歴APIエンドポイント（オプション）
@task_management_bp.route("/api/approval-history")
@login_required
@teacher_required
def get_approval_history_api():
    """承認履歴API"""
    try:
        days_back = request.args.get('days', default=30, type=int)
        class_filter = request.args.get('class_id', type=int)
        
        approval_service = TeacherApprovalService()
        history = approval_service.get_approval_history(days_back, class_filter)
        
        return jsonify({
            'status': 'success',
            'data': history
        })
        
    except Exception as e:
        current_app.logger.error(f"Approval history API error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'システムエラーが発生しました'
        }), 500