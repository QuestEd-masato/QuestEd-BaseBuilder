# app/teacher/modules/task_management.py
"""教師タスク管理機能"""

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

        # 統計データの計算
        stats = calculate_statistics(teacher_classes, class_filter, curriculum_filter, status_filter)
        
        # クラス別進捗データの取得
        classes_progress = get_classes_progress(teacher_classes, class_filter, curriculum_filter, week_filter)
        
        # 承認待ち課題詳細の取得
        pending_submissions = get_pending_submissions(teacher_classes, class_filter, curriculum_filter, status_filter)

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
        # 提出進捗取得
        progress = StudentTaskProgress.query.get_or_404(submission_id)
        
        # 権限チェック：教師が担当するクラスの学生かどうか
        student = User.query.get(progress.student_id)
        task = CurriculumTask.query.get(progress.task_id)
        curriculum = Curriculum.query.get(task.curriculum_id)
        
        # 教師の担当クラス確認
        teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
        teacher_class_ids = [c.id for c in teacher_classes]
        
        student_classes = ClassEnrollment.query.filter_by(student_id=student.id).all()
        student_class_ids = [sc.class_id for sc in student_classes]
        
        if not any(class_id in teacher_class_ids for class_id in student_class_ids):
            flash("アクセス権限がありません。", "error")
            return redirect(url_for("teacher_task_management.task_management"))

        # 学生統計データ取得
        student_stats = get_student_statistics(student.id)
        
        # 提出履歴取得
        submission_history = get_submission_history(submission_id)

        return render_template(
            "teacher/task_submission_detail.html",
            progress=progress,
            task=task,
            student=student,
            student_stats=student_stats,
            submission_history=submission_history
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
        # クラス取得と権限チェック
        class_obj = Class.query.get_or_404(class_id)
        if class_obj.teacher_id != current_user.id:
            flash("アクセス権限がありません。", "error")
            return redirect(url_for("teacher_task_management.task_management"))

        # クラスの学生取得
        enrollments = ClassEnrollment.query.filter_by(class_id=class_id).all()
        students = [User.query.get(e.student_id) for e in enrollments]

        # 学生別課題進捗データ取得
        students_progress = []
        for student in students:
            if student:
                progress_data = get_student_progress_detail(student.id, class_id)
                students_progress.append(progress_data)

        return render_template(
            "teacher/class_progress.html",
            class_obj=class_obj,
            students_progress=students_progress
        )

    except Exception as e:
        current_app.logger.error(f"Class progress error: {str(e)}")
        flash("クラス進捗の読み込み中にエラーが発生しました。", "error")
        return redirect(url_for("teacher_task_management.task_management"))


def calculate_statistics(teacher_classes, class_filter=None, curriculum_filter=None, status_filter=None):
    """統計データの計算"""
    try:
        # 教師のクラスに属する学生取得
        class_ids = [c.id for c in teacher_classes]
        if class_filter:
            class_ids = [class_filter]
            
        enrollments = ClassEnrollment.query.filter(ClassEnrollment.class_id.in_(class_ids)).all()
        student_ids = [e.student_id for e in enrollments]

        # 承認待ち件数の計算
        pending_submissions = 0
        total_tasks = 0
        completed_tasks = 0
        active_students = 0

        # 新カリキュラムタスクシステムは削除済み - 統計に影響なし

        # 2. レッスンシステムの統計（完了申請）
        unit_pending = StudentUnitSelection.query.filter(
            StudentUnitSelection.student_id.in_(student_ids),
            StudentUnitSelection.approval_status == 'none',
            StudentUnitSelection.completion_request_date.isnot(None)
        ).count()
        pending_submissions += unit_pending

        # レッスンシステムの完了数追加
        unit_completed = StudentUnitSelection.query.filter(
            StudentUnitSelection.student_id.in_(student_ids),
            StudentUnitSelection.approval_status == 'approved'
        ).count()
        completed_tasks += unit_completed

        # レッスンシステムの総数追加
        unit_total = StudentUnitSelection.query.filter(
            StudentUnitSelection.student_id.in_(student_ids)
        ).count()
        total_tasks += unit_total

        # 完了率計算
        completion_rate = round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)

        # 期限超過課題数（実装は簡易版）
        overdue_tasks = 0  # TODO: 期限管理機能実装後に計算

        return {
            'pending_submissions': pending_submissions,
            'completion_rate': completion_rate,
            'active_students': active_students,
            'overdue_tasks': overdue_tasks
        }

    except Exception as e:
        current_app.logger.error(f"Statistics calculation error: {str(e)}")
        return {
            'pending_submissions': 0,
            'completion_rate': 0,
            'active_students': 0,
            'overdue_tasks': 0
        }


def get_classes_progress(teacher_classes, class_filter=None, curriculum_filter=None, week_filter=None):
    """クラス別進捗データの取得"""
    try:
        classes_progress = []
        
        target_classes = teacher_classes
        if class_filter:
            target_classes = [c for c in teacher_classes if c.id == class_filter]

        for class_obj in target_classes:
            # クラスの学生取得
            enrollments = ClassEnrollment.query.filter_by(class_id=class_obj.id).all()
            students = []
            
            for enrollment in enrollments:
                student = User.query.get(enrollment.student_id)
                if student:
                    student_progress = get_student_weekly_progress(
                        student.id, curriculum_filter, week_filter
                    )
                    student_data = {
                        'id': student.id,
                        'name': student.name or student.username,
                        'weeks_progress': student_progress['weeks'],
                        'pending_tasks': student_progress['pending_count']
                    }
                    students.append(student_data)

            # 週情報の取得（サンプル：第1-5週）
            weeks = []
            for week_num in range(1, 6):
                if week_filter is None or week_filter == week_num:
                    task_count = CurriculumTask.query.filter_by(week_number=week_num).count()
                    weeks.append({
                        'number': week_num,
                        'task_count': task_count
                    })

            # クラス統計計算
            total_students = len(students)
            if total_students > 0:
                avg_progress = sum(
                    sum(wp['percentage'] for wp in s['weeks_progress']) / len(s['weeks_progress'])
                    for s in students if s['weeks_progress']
                ) / total_students
                pending_count = sum(s['pending_tasks'] for s in students)
            else:
                avg_progress = 0
                pending_count = 0

            classes_progress.append({
                'class_id': class_obj.id,
                'class_name': class_obj.name,
                'students': students,
                'weeks': weeks,
                'average_progress': avg_progress,
                'pending_count': pending_count
            })

        return classes_progress

    except Exception as e:
        current_app.logger.error(f"Classes progress error: {str(e)}")
        return []


def get_student_weekly_progress(student_id, curriculum_filter=None, week_filter=None):
    """学生の週別進捗取得"""
    try:
        weeks_progress = []
        pending_count = 0

        for week_num in range(1, 6):  # 第1-5週
            if week_filter is None or week_filter == week_num:
                # 週の課題取得
                tasks_query = CurriculumTask.query.filter_by(week_number=week_num)
                if curriculum_filter:
                    tasks_query = tasks_query.filter_by(curriculum_id=curriculum_filter)
                
                week_tasks = tasks_query.all()
                total_tasks = len(week_tasks)
                completed_tasks = 0
                pending_tasks = 0

                for task in week_tasks:
                    progress = StudentTaskProgress.query.filter_by(
                        student_id=student_id, task_id=task.id
                    ).first()
                    
                    if progress:
                        if progress.status == TaskStatus.COMPLETED:
                            completed_tasks += 1
                        elif progress.status == TaskStatus.SUBMITTED:
                            pending_tasks += 1

                percentage = round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)
                
                weeks_progress.append({
                    'week': week_num,
                    'total': total_tasks,
                    'completed': completed_tasks,
                    'pending_count': pending_tasks,
                    'percentage': percentage
                })
                
                pending_count += pending_tasks

        return {
            'weeks': weeks_progress,
            'pending_count': pending_count
        }

    except Exception as e:
        current_app.logger.error(f"Student weekly progress error: {str(e)}")
        return {'weeks': [], 'pending_count': 0}


def get_pending_submissions(teacher_classes, class_filter=None, curriculum_filter=None, status_filter=None):
    """承認待ち課題詳細の取得"""
    try:
        # 教師のクラスに属する学生の課題取得
        class_ids = [c.id for c in teacher_classes]
        if class_filter:
            class_ids = [class_filter]

        enrollments = ClassEnrollment.query.filter(ClassEnrollment.class_id.in_(class_ids)).all()
        student_ids = [e.student_id for e in enrollments]

        current_app.logger.info(f"[PENDING_SUBMISSIONS] Class filter: {class_filter}, Class IDs: {class_ids}, Student IDs count: {len(student_ids)}")

        pending_submissions = []

        # 2. レッスンシステムの完了申請取得（最優先で処理）
        current_app.logger.info("[PENDING_SUBMISSIONS] Starting lesson system completion requests check...")
        
        try:
            from app.models import StudentUnitSelection, CurriculumUnit
            
            unit_requests = StudentUnitSelection.query.filter(
                StudentUnitSelection.student_id.in_(student_ids),
                StudentUnitSelection.approval_status == 'none',
                StudentUnitSelection.completion_request_date.isnot(None)
            ).all()

            current_app.logger.info(f"[PENDING_SUBMISSIONS] Found {len(unit_requests)} unit completion requests")

            for request in unit_requests:
                try:
                    student = User.query.get(request.student_id)
                    unit = CurriculumUnit.query.get(request.unit_id)
                    
                    current_app.logger.info(f"[PENDING_SUBMISSIONS] Processing unit request: ID={request.id}, Student={student.username if student else 'None'}, Unit={unit.title if unit else 'None'}")
                    
                    submission_data = {
                        'id': f"unit_{request.id}",
                        'type': 'unit_completion',
                        'task_title': f"{unit.title} 完了申請" if unit else "完了申請",
                        'student_name': student.full_name or student.username if student else "Unknown",
                        'submitted_at': request.completion_request_date,
                        'submission_type': 'unit_completion',
                        'content': f"進捗率: {request.progress_percentage}%",
                        'self_evaluation': None,
                        'is_overdue': False,
                        'priority': 'high',
                        'unit_id': request.unit_id,
                        'selection_id': request.id
                    }
                    pending_submissions.append(submission_data)
                    current_app.logger.info(f"[PENDING_SUBMISSIONS] Successfully added unit completion: {submission_data['task_title']}")
                except Exception as e:
                    current_app.logger.error(f"[PENDING_SUBMISSIONS] Error processing unit request {request.id}: {str(e)}")
                    import traceback
                    current_app.logger.error(traceback.format_exc())

        except Exception as e:
            current_app.logger.error(f"[PENDING_SUBMISSIONS] Error in lesson system processing: {str(e)}")
            import traceback
            current_app.logger.error(traceback.format_exc())

        # 新カリキュラムタスクシステムは削除済み - スキップ

        # 提出日時でソート
        try:
            from datetime import datetime
            pending_submissions.sort(key=lambda x: x['submitted_at'] or datetime.min, reverse=True)
        except Exception as e:
            current_app.logger.error(f"[PENDING_SUBMISSIONS] Error sorting submissions: {str(e)}")
        
        current_app.logger.info(f"[PENDING_SUBMISSIONS] Returning {len(pending_submissions)} total submissions")
        for i, submission in enumerate(pending_submissions):
            current_app.logger.info(f"[PENDING_SUBMISSIONS] {i+1}. {submission['task_title']} by {submission['student_name']} (type: {submission['type']})")
        
        return pending_submissions

    except Exception as e:
        current_app.logger.error(f"[PENDING_SUBMISSIONS] Critical error in get_pending_submissions: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return []


def get_student_statistics(student_id):
    """学生統計データ取得"""
    try:
        # 完了課題数
        completed_tasks = StudentTaskProgress.query.filter_by(
            student_id=student_id,
            status=TaskStatus.COMPLETED
        ).count()

        # 平均評価（簡易実装）
        avg_score = 4.2  # TODO: 実際の評価データから計算

        # 提出率
        total_assigned = StudentTaskProgress.query.filter_by(student_id=student_id).count()
        submitted_count = StudentTaskProgress.query.filter_by(student_id=student_id).filter(
            StudentTaskProgress.status.in_([TaskStatus.SUBMITTED, TaskStatus.COMPLETED])
        ).count()
        submission_rate = round((submitted_count / total_assigned * 100) if total_assigned > 0 else 0, 1)

        # 期限内提出率（簡易実装）
        on_time_rate = 85.0  # TODO: 実際の期限データから計算

        # クラス名取得
        enrollments = ClassEnrollment.query.filter_by(student_id=student_id).first()
        class_name = None
        if enrollments:
            class_obj = Class.query.get(enrollments.class_id)
            class_name = class_obj.name if class_obj else None

        return {
            'completed_tasks': completed_tasks,
            'average_score': avg_score,
            'submission_rate': submission_rate,
            'on_time_rate': on_time_rate,
            'class_name': class_name
        }

    except Exception as e:
        current_app.logger.error(f"Student statistics error: {str(e)}")
        return {
            'completed_tasks': 0,
            'average_score': 0,
            'submission_rate': 0,
            'on_time_rate': 0,
            'class_name': None
        }


def get_submission_history(submission_id):
    """提出履歴取得"""
    try:
        # 簡易実装：実際にはhistoryテーブルから取得
        progress = StudentTaskProgress.query.get(submission_id)
        history = []
        
        if progress.started_at:
            history.append({
                'created_at': progress.started_at,
                'action': '課題開始',
                'note': None
            })
        
        if progress.submitted_at:
            history.append({
                'created_at': progress.submitted_at,
                'action': '課題提出',
                'note': '学生による提出'
            })

        return history

    except Exception as e:
        current_app.logger.error(f"Submission history error: {str(e)}")
        return []


def get_student_progress_detail(student_id, class_id):
    """学生詳細進捗データ取得"""
    try:
        student = User.query.get(student_id)
        if not student:
            return None

        # 学生の課題進捗取得
        progresses = StudentTaskProgress.query.filter_by(student_id=student_id).all()
        
        # 週別グループ化
        weekly_progress = {}
        for progress in progresses:
            task = CurriculumTask.query.get(progress.task_id)
            if task:
                week = task.week_number
                if week not in weekly_progress:
                    weekly_progress[week] = {
                        'total': 0,
                        'completed': 0,
                        'in_progress': 0,
                        'submitted': 0
                    }
                
                weekly_progress[week]['total'] += 1
                if progress.status == TaskStatus.COMPLETED:
                    weekly_progress[week]['completed'] += 1
                elif progress.status == TaskStatus.IN_PROGRESS:
                    weekly_progress[week]['in_progress'] += 1
                elif progress.status == TaskStatus.SUBMITTED:
                    weekly_progress[week]['submitted'] += 1

        return {
            'id': student.id,
            'name': student.name or student.username,
            'weekly_progress': weekly_progress,
            'total_completed': sum(wp['completed'] for wp in weekly_progress.values()),
            'pending_tasks': sum(wp['submitted'] for wp in weekly_progress.values())
        }

    except Exception as e:
        current_app.logger.error(f"Student progress detail error: {str(e)}")
        return None


@task_management_bp.route("/api/submission/<submission_id>/approve", methods=['POST'])
@login_required
@teacher_required
def approve_unit_submission(submission_id):
    """レッスン単元完了申請の承認"""
    try:
        # submission_idがunit_で始まる場合は単元完了申請
        if str(submission_id).startswith('unit_'):
            unit_selection_id = str(submission_id).replace('unit_', '')
            
            # 承認処理
            unit_selection = StudentUnitSelection.query.get(unit_selection_id)
            if not unit_selection:
                return jsonify({'status': 'error', 'message': '申請が見つかりません'}), 404
            
            # 権限チェック: 教師が担当するクラスの学生かどうか
            teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
            teacher_class_ids = [c.id for c in teacher_classes]
            
            student_classes = ClassEnrollment.query.filter_by(student_id=unit_selection.student_id).all()
            student_class_ids = [sc.class_id for sc in student_classes]
            
            if not any(class_id in teacher_class_ids for class_id in student_class_ids):
                return jsonify({'status': 'error', 'message': 'アクセス権限がありません'}), 403
            
            # 承認処理
            unit_selection.approval_status = 'approved'
            unit_selection.approved_by = current_user.id
            unit_selection.approval_date = datetime.utcnow()
            
            db.session.commit()
            
            current_app.logger.info(f"[APPROVAL] Unit completion approved: ID={unit_selection_id}, Student={unit_selection.student_id}, Teacher={current_user.id}")
            
            return jsonify({
                'status': 'success',
                'message': '単元完了申請を承認しました'
            })
        else:
            return jsonify({'status': 'error', 'message': '無効な申請IDです'}), 400
            
    except Exception as e:
        current_app.logger.error(f"[APPROVAL] Error approving submission {submission_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'システムエラーが発生しました'}), 500


@task_management_bp.route("/api/submission/<submission_id>/reject", methods=['POST'])
@login_required
@teacher_required
def reject_unit_submission(submission_id):
    """レッスン単元完了申請の却下"""
    try:
        if str(submission_id).startswith('unit_'):
            unit_selection_id = str(submission_id).replace('unit_', '')
            
            unit_selection = StudentUnitSelection.query.get(unit_selection_id)
            if not unit_selection:
                return jsonify({'status': 'error', 'message': '申請が見つかりません'}), 404
            
            # 権限チェック
            teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
            teacher_class_ids = [c.id for c in teacher_classes]
            
            student_classes = ClassEnrollment.query.filter_by(student_id=unit_selection.student_id).all()
            student_class_ids = [sc.class_id for sc in student_classes]
            
            if not any(class_id in teacher_class_ids for class_id in student_class_ids):
                return jsonify({'status': 'error', 'message': 'アクセス権限がありません'}), 403
            
            # 却下処理 - 再申請可能状態に設定
            unit_selection.approval_status = 'rejected'
            unit_selection.approved_by = current_user.id
            unit_selection.approval_date = datetime.utcnow()
            unit_selection.completion_request_date = None  # 再申請を可能にする
            
            # 却下理由とログ情報の保存
            data = request.get_json() or {}
            rejection_reason = data.get('reason', '')
            if rejection_reason:
                unit_selection.rejection_reason = rejection_reason
                unit_selection.rejection_date = datetime.utcnow()
                current_app.logger.info(f"[REJECTION] Reason: {rejection_reason}")
            
            db.session.commit()
            
            current_app.logger.info(f"[REJECTION] Unit completion rejected: ID={unit_selection_id}, Student={unit_selection.student_id}, Teacher={current_user.id}")
            
            return jsonify({
                'status': 'success',
                'message': '単元完了申請を却下しました'
            })
        else:
            return jsonify({'status': 'error', 'message': '無効な申請IDです'}), 400
            
    except Exception as e:
        current_app.logger.error(f"[REJECTION] Error rejecting submission {submission_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'システムエラーが発生しました'}), 500