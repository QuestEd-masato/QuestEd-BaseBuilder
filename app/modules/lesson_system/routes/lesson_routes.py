"""
レッスンシステム ルーティング

学生・教師向けレッスン機能のルート定義
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user

from app.utils.decorators import student_required, teacher_required
from ..services.lesson_service import LessonService
from ..services.progress_service import LessonProgressService
from ..services.lesson_import_service import LessonImportService
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
            progress_summary=progress_summary,
            is_modular_system=True  # 新しいモジュール式システムであることを示すフラグ
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
            task_data=task_data,
            is_modular_system=True  # 新しいモジュール式システムであることを示すフラグ
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

@lesson_bp.route('/teacher/lesson-management')
@login_required
@teacher_required
def lesson_management():
    """教師用：レッスン管理メイン画面"""
    try:
        # 全てのレッスンを取得
        lessons = LessonService.get_all_lessons()
        
        # カリキュラム一覧を取得（フィルタ用）
        from app.models import Curriculum
        curriculums = Curriculum.query.filter_by(is_active=True).all()
        
        # レッスン統計情報
        lesson_stats = {
            'total_lessons': len(lessons),
            'active_lessons': sum(1 for lesson in lessons if lesson.status == 'active'),
            'total_students': 0,  # TODO: 実装
            'avg_progress': 0  # TODO: 実装
        }
        
        # ページネーション処理
        page = request.args.get('page', 1, type=int)
        per_page = 20
        total_lessons = len(lessons)
        start = (page - 1) * per_page
        end = start + per_page
        
        paginated_lessons = lessons[start:end]
        
        # 簡易的なページネーションオブジェクト
        from types import SimpleNamespace
        pagination = SimpleNamespace(
            page=page,
            per_page=per_page,
            total=total_lessons,
            pages=(total_lessons + per_page - 1) // per_page,
            has_prev=page > 1,
            has_next=end < total_lessons,
            prev_num=page - 1 if page > 1 else None,
            next_num=page + 1 if end < total_lessons else None,
            iter_pages=lambda: range(1, ((total_lessons + per_page - 1) // per_page) + 1)
        )
        
        return render_template(
            'lesson_system/teacher/lesson_management.html',
            lessons=paginated_lessons,
            curriculums=curriculums,
            lesson_stats=lesson_stats,
            pagination=pagination
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in lesson_management: {e}")
        flash("レッスン管理画面の読み込み中にエラーが発生しました。", "error")
        return redirect(url_for('teacher_dashboard.dashboard'))


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


@lesson_bp.route('/teacher/analytics')
@login_required
@teacher_required
def lesson_analytics():
    """教師用：レッスン分析メイン画面"""
    try:
        # 全体的な分析データを取得
        analytics_data = {
            'total_lessons': 0,
            'active_lessons': 0,
            'student_progress': [],
            'completion_rates': {},
            'recent_activities': []
        }
        
        # レッスン一覧を取得
        lessons = LessonService.get_all_lessons()
        analytics_data['total_lessons'] = len(lessons)
        analytics_data['active_lessons'] = sum(1 for lesson in lessons if lesson.status == 'active')
        
        return render_template(
            'lesson_system/teacher/lesson_analytics.html',
            lessons=lessons,
            **analytics_data
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in lesson_analytics: {e}")
        flash("レッスン分析画面の読み込み中にエラーが発生しました。", "error")
        return redirect(url_for('teacher_dashboard.dashboard'))


@lesson_bp.route('/teacher/lesson/<int:lesson_id>/analytics')
@login_required
@teacher_required
def lesson_detail_analytics(lesson_id):
    """教師用：個別レッスン分析"""
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
            'lesson_system/teacher/lesson_detail_analytics.html',
            **analytics_data
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in lesson_detail_analytics: {e}")
        flash("レッスン分析画面の読み込み中にエラーが発生しました。", "error")
        return redirect(url_for('teacher_dashboard.dashboard'))


@lesson_bp.route('/teacher/lesson/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_lesson():
    """教師用：新規レッスン作成"""
    if request.method == 'POST':
        try:
            import_type = request.form.get('import_type', 'manual')
            
            if import_type == 'csv':
                # CSV インポート処理
                curriculum_id = int(request.form.get('curriculum_id', 0))
                if not curriculum_id:
                    flash("カリキュラムを選択してください。", "error")
                    return redirect(request.url)
                
                csv_file = request.files.get('csv_file')
                if not csv_file or csv_file.filename == '':
                    flash("CSVファイルを選択してください。", "error")
                    return redirect(request.url)
                
                # CSV インポート実行
                result = LessonImportService.import_lessons_from_csv(
                    csv_file, curriculum_id, current_user.id
                )
                
                if result['success']:
                    flash(result['message'], "success")
                    if result.get('errors'):
                        for error in result['errors']:
                            flash(error, "warning")
                    return redirect(url_for('lesson_system.lesson_management'))
                else:
                    flash(result['message'], "error")
                    return redirect(request.url)
            
            else:
                # 手動作成処理
                data = request.form.to_dict()
                data['created_by'] = current_user.id
                
                # カリキュラムIDの確認
                curriculum_id = int(data.get('curriculum_id', 0))
                if not curriculum_id:
                    flash("カリキュラムを選択してください。", "error")
                    return redirect(url_for('lesson_system.lesson_management'))
                
                # 学習目標と重要ポイントを配列に変換
                learning_objectives = [
                    obj.strip() for obj in data.get('learning_objectives', '').split('\n') 
                    if obj.strip()
                ]
                key_points = [
                    point.strip() for point in data.get('key_points', '').split('\n') 
                    if point.strip()
                ]
                
                data['learning_objectives'] = learning_objectives
                data['key_points'] = key_points
                
                lesson = LessonService.create_lesson(curriculum_id, data)
                if lesson:
                    flash("レッスンを作成しました。", "success")
                    return redirect(url_for('lesson_system.edit_lesson', lesson_id=lesson.id))
                else:
                    flash("レッスンの作成に失敗しました。", "error")
                
        except Exception as e:
            current_app.logger.error(f"Error creating lesson: {e}")
            flash("レッスン作成中にエラーが発生しました。", "error")
    
    # GET: フォーム表示
    from app.models import Curriculum
    curriculums = Curriculum.query.filter_by(is_active=True).all()
    
    return render_template(
        'lesson_system/teacher/create_lesson.html',
        curriculums=curriculums
    )


@lesson_bp.route('/teacher/lesson/<int:lesson_id>/edit', methods=['GET', 'POST'])
@login_required  
@teacher_required
def edit_lesson(lesson_id):
    """教師用：レッスン編集"""
    lesson = LessonService.get_lesson_by_id(lesson_id)
    if not lesson:
        flash("レッスンが見つかりません。", "error")
        return redirect(url_for('lesson_system.lesson_management'))
    
    if request.method == 'POST':
        try:
            data = request.form.to_dict()
            success = LessonService.update_lesson(lesson_id, data)
            
            if success:
                flash("レッスンを更新しました。", "success")
                return redirect(url_for('lesson_system.lesson_detail', lesson_id=lesson_id))
            else:
                flash("レッスンの更新に失敗しました。", "error")
                
        except Exception as e:
            current_app.logger.error(f"Error updating lesson: {e}")
            flash("レッスン更新中にエラーが発生しました。", "error")
    
    # GET: 編集フォーム表示
    from app.models import Curriculum
    curriculums = Curriculum.query.filter_by(is_active=True).all()
    tasks = LessonService.get_lesson_tasks(lesson_id)
    
    return render_template(
        'lesson_system/teacher/edit_lesson.html',
        lesson=lesson,
        curriculums=curriculums,
        tasks=tasks
    )


@lesson_bp.route('/lesson/<int:lesson_id>', methods=['DELETE'])
@login_required
@teacher_required  
def delete_lesson(lesson_id):
    """教師用：レッスン削除（API）"""
    try:
        success = LessonService.delete_lesson(lesson_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'レッスンを削除しました。'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'レッスンが見つかりません。'
            }), 404
            
    except Exception as e:
        current_app.logger.error(f"Error deleting lesson: {e}")
        return jsonify({
            'success': False,
            'message': 'レッスンの削除中にエラーが発生しました。'
        }), 500


@lesson_bp.route('/teacher/csv-template/download')
@login_required
@teacher_required
def download_csv_template():
    """CSVテンプレートファイルのダウンロード"""
    try:
        from flask import Response
        
        # CSVテンプレートを生成
        csv_content = LessonImportService.generate_csv_template()
        
        # レスポンスを作成
        response = Response(
            csv_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=lesson_import_template.csv'
            }
        )
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error generating CSV template: {e}")
        flash("CSVテンプレートの生成中にエラーが発生しました。", "error")
        return redirect(url_for('lesson_system.create_lesson'))