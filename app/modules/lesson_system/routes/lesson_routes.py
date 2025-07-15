"""
レッスンシステム ルーティング

学生・教師向けレッスン機能のルート定義
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user

from app.utils.decorators import student_required, teacher_required
from ..services.lesson_service import LessonService
from ..services.progress_service import LessonProgressService
from ..models.lesson_models import TaskCheckStatus

lesson_bp = Blueprint('lesson_system', __name__, url_prefix='/lesson-system')


# === 学生向けルート ===

@lesson_bp.route('/curriculum/<int:curriculum_id>/lessons')
@login_required
@student_required
def curriculum_lessons(curriculum_id):
    """カリキュラムのレッスン一覧表示"""
    try:
        lessons = LessonService.get_lessons_by_curriculum(curriculum_id)
        
        # 学生の進捗データを取得
        lesson_data = []
        for lesson in lessons:
            progress = LessonProgressService.get_student_progress(current_user.id, lesson.id)
            lesson_data.append({
                'lesson': lesson,
                'progress': progress,
                'is_completed': progress.is_completed if progress else False,
                'completion_percentage': progress.completion_percentage if progress else 0
            })
        
        progress_summary = LessonProgressService.get_curriculum_progress_summary(
            current_user.id, curriculum_id
        )
        
        return render_template(
            'student/curriculum_lessons.html',
            curriculum_id=curriculum_id,
            lesson_data=lesson_data,
            progress_summary=progress_summary
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in curriculum_lessons: {e}")
        flash("レッスン一覧の読み込み中にエラーが発生しました。", "error")
        return redirect(url_for('student_learning.learning_portal'))


@lesson_bp.route('/lesson/<int:lesson_id>')
@login_required
@student_required
def lesson_detail(lesson_id):
    """レッスン詳細表示"""
    try:
        lesson = LessonService.get_lesson_by_id(lesson_id)
        if not lesson:
            flash("レッスンが見つかりません。", "error")
            return redirect(url_for('student_learning.learning_portal'))
        
        # 学生の進捗データ取得または作成
        progress = LessonProgressService.get_student_progress(current_user.id, lesson_id)
        if not progress:
            progress = LessonProgressService.create_or_update_progress(
                current_user.id, lesson_id, {}
            )
        
        # レッスンのタスク一覧を取得
        lesson_tasks = LessonService.get_lesson_tasks(lesson_id)
        
        # タスクの完了状況を取得
        task_checks = LessonProgressService.get_student_task_checks(current_user.id, lesson_id)
        task_check_dict = {tc.task_id: tc for tc in task_checks}
        
        # タスクデータを構築
        task_data = []
        for task in lesson_tasks:
            check = task_check_dict.get(task.id)
            task_data.append({
                'task': task,
                'check': check,
                'is_completed': check and check.status == TaskCheckStatus.COMPLETED,
                'status': check.status if check else None
            })
        
        return render_template(
            'student/lesson_detail.html',
            lesson=lesson,
            progress=progress,
            task_data=task_data
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in lesson_detail: {e}")
        flash("レッスン詳細の読み込み中にエラーが発生しました。", "error")
        return redirect(url_for('student_learning.learning_portal'))


# === API ルート ===

@lesson_bp.route('/api/task/<int:task_id>/check', methods=['POST'])
@login_required
@student_required
def update_task_check(task_id):
    """タスクチェック状況を更新"""
    try:
        data = request.get_json()
        status_str = data.get('status', 'not_started')
        notes = data.get('notes', '')
        
        # ステータス文字列をenumに変換
        status_mapping = {
            'not_started': TaskCheckStatus.NOT_STARTED,
            'in_progress': TaskCheckStatus.IN_PROGRESS,
            'completed': TaskCheckStatus.COMPLETED
        }
        
        status = status_mapping.get(status_str, TaskCheckStatus.NOT_STARTED)
        
        success = LessonProgressService.update_task_check(
            current_user.id, task_id, status, notes
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'タスクの状況を更新しました。'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'タスクの更新に失敗しました。'
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error updating task check: {e}")
        return jsonify({
            'success': False,
            'message': 'エラーが発生しました。'
        }), 500


@lesson_bp.route('/api/lesson/<int:lesson_id>/progress', methods=['POST'])
@login_required
@student_required
def update_lesson_progress(lesson_id):
    """レッスン進捗を更新"""
    try:
        data = request.get_json()
        
        progress = LessonProgressService.create_or_update_progress(
            current_user.id, lesson_id, data
        )
        
        if progress:
            return jsonify({
                'success': True,
                'message': 'レッスンの進捗を更新しました。',
                'completion_percentage': progress.completion_percentage
            })
        else:
            return jsonify({
                'success': False,
                'message': '進捗の更新に失敗しました。'
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error updating lesson progress: {e}")
        return jsonify({
            'success': False,
            'message': 'エラーが発生しました。'
        }), 500


# === 教師向けルート ===

@lesson_bp.route('/teacher/curriculum/<int:curriculum_id>/lessons')
@login_required
@teacher_required
def teacher_curriculum_lessons(curriculum_id):
    """教師用：カリキュラムレッスン管理"""
    try:
        lessons = LessonService.get_lessons_by_curriculum(curriculum_id)
        statistics = LessonService.get_lesson_statistics(curriculum_id)
        
        return render_template(
            'lesson_system/teacher_lessons.html',
            curriculum_id=curriculum_id,
            lessons=lessons,
            statistics=statistics
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in teacher_curriculum_lessons: {e}")
        flash("レッスン管理画面の読み込み中にエラーが発生しました。", "error")
        return redirect(url_for('teacher_dashboard.dashboard'))


@lesson_bp.route('/teacher/lesson/<int:lesson_id>/analytics')
@login_required
@teacher_required
def lesson_analytics(lesson_id):
    """教師用：レッスン分析"""
    try:
        lesson = LessonService.get_lesson_by_id(lesson_id)
        if not lesson:
            flash("レッスンが見つかりません。", "error")
            return redirect(url_for('teacher_dashboard.dashboard'))
        
        # TODO: 学生の進捗分析データを取得
        analytics_data = {
            'lesson': lesson,
            'student_progress': [],  # 実装予定
            'completion_rates': {},  # 実装予定
        }
        
        return render_template(
            'lesson_system/lesson_analytics.html',
            **analytics_data
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in lesson_analytics: {e}")
        flash("レッスン分析画面の読み込み中にエラーが発生しました。", "error")
        return redirect(url_for('teacher_dashboard.dashboard'))