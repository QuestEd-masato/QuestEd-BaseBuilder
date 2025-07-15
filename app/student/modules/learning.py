# app/student/modules/learning.py
"""学生自由進度学習機能 - レッスンシステムのみ"""

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
from sqlalchemy import desc, func

from app.models import CurriculumUnit, StudentUnitSelection, User, Curriculum, db

# レッスンシステムのモデルは遅延インポート
CurriculumLesson = None
LessonTask = None
StudentLessonProgress = None
StudentTaskCheck = None
LessonType = None
TaskCheckStatus = None

def _import_lesson_models():
    """レッスンシステムモデルの遅延インポート"""
    global CurriculumLesson, LessonTask, StudentLessonProgress, StudentTaskCheck, LessonType, TaskCheckStatus
    
    try:
        from app.modules.lesson_system.models.lesson_models import (
            CurriculumLesson as _CurriculumLesson,
            LessonTask as _LessonTask,
            StudentLessonProgress as _StudentLessonProgress,
            StudentTaskCheck as _StudentTaskCheck,
            LessonType as _LessonType,
            TaskCheckStatus as _TaskCheckStatus
        )
        CurriculumLesson = _CurriculumLesson
        LessonTask = _LessonTask
        StudentLessonProgress = _StudentLessonProgress
        StudentTaskCheck = _StudentTaskCheck
        LessonType = _LessonType
        TaskCheckStatus = _TaskCheckStatus
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to import lesson models: {e}")
        return False

def get_lesson_models():
    """レッスンシステムモデルの取得"""
    if CurriculumLesson is None:
        _import_lesson_models()
    return CurriculumLesson is not None
    
# BaseBuilderタスク統合サービス
from app.services.basebuilder_task_service import (
    BaseBuilderTaskService, get_task_basebuilder_achievement
)

from ..utils import student_required

learning_bp = Blueprint("student_learning", __name__)


@learning_bp.route("/learning")
@login_required
@student_required
def learning_portal():
    """統合学習ポータル - レッスンシステムのみ"""
    try:
        # レッスンモデルの遅延インポート
        LESSON_SYSTEM_AVAILABLE = get_lesson_models()
        # 学生が所属するクラスの取得
        from app.models import ClassEnrollment
        enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
        class_ids = [e.class_id for e in enrollments]
        
        if not class_ids:
            flash("所属クラスが見つかりません。管理者にお問い合わせください。", "warning")
            return render_template("student/learning_portal.html", 
                                 available_curricula=[], my_progress=[])
        
        # 利用可能なカリキュラムを取得（クラス単位）
        from app.models import Class
        available_curricula = []
        for class_id in class_ids:
            class_obj = Class.query.get(class_id)
            if class_obj:
                class_curricula = Curriculum.query.filter_by(class_id=class_id).all()
                for curriculum in class_curricula:
                    # レッスンシステムのみを使用
                    if LESSON_SYSTEM_AVAILABLE and CurriculumLesson is not None:
                        try:
                            total_lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum.id).count()
                        except Exception as e:
                            current_app.logger.error(f"CurriculumLesson count error for curriculum {curriculum.id}: {e}")
                            total_lessons = 0
                    else:
                        total_lessons = 0
                    
                    # レッスンがあるカリキュラムのみ表示
                    if total_lessons > 0:
                        available_curricula.append({
                            'curriculum': curriculum,
                            'class_name': class_obj.name,
                            'total_lessons': total_lessons,
                            'system_type': 'lessons'
                        })

        # 学生の進捗状況を取得（レッスンシステムのみ）
        my_progress = []
        for curriculum_data in available_curricula:
            curriculum = curriculum_data['curriculum']
            
            # レッスンシステムの進捗処理のみ
            if LESSON_SYSTEM_AVAILABLE and CurriculumLesson is not None:
                # レッスンシステムの進捗処理
                try:
                    lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum.id).all()
                except Exception as lesson_error:
                    current_app.logger.error(f"Lesson progress query error: {str(lesson_error)}")
                    continue
                total_lessons = len(lessons)
                completed_lessons = 0
                in_progress_lessons = 0
                
                # 各レッスンの完了タスク数を計算
                total_lesson_tasks = 0
                completed_lesson_tasks = 0
                
                for lesson in lessons:
                    try:
                        # レッスンの進捗を取得
                        lesson_progress = StudentLessonProgress.query.filter_by(
                            student_id=current_user.id, lesson_id=lesson.id
                        ).first()
                        
                        if lesson_progress:
                            if lesson_progress.is_completed:
                                completed_lessons += 1
                            elif lesson_progress.completion_percentage > 0:
                                in_progress_lessons += 1
                        
                        # レッスンのタスク数をカウント
                        lesson_tasks = LessonTask.query.filter_by(lesson_id=lesson.id).all()
                        total_lesson_tasks += len(lesson_tasks)
                        
                        # 完了済みタスク数をカウント
                        for task in lesson_tasks:
                            try:
                                task_check = StudentTaskCheck.query.filter_by(
                                    student_id=current_user.id,
                                    task_id=task.id,
                                    status=TaskCheckStatus.COMPLETED
                                ).first()
                                if task_check:
                                    completed_lesson_tasks += 1
                            except Exception as task_check_error:
                                current_app.logger.error(f"Task check error: {str(task_check_error)}")
                                continue
                    except Exception as lesson_loop_error:
                        current_app.logger.error(f"Lesson loop error: {str(lesson_loop_error)}")
                        continue
                
                progress_percentage = round((completed_lesson_tasks / total_lesson_tasks * 100) if total_lesson_tasks > 0 else 0, 1)
                
                my_progress.append({
                    'curriculum_id': curriculum.id,
                    'curriculum_title': curriculum.title,
                    'class_name': curriculum_data['class_name'],
                    'total_tasks': total_lesson_tasks,
                    'completed_tasks': completed_lesson_tasks,
                    'in_progress_tasks': total_lesson_tasks - completed_lesson_tasks,
                    'submitted_tasks': 0,  # レッスンシステムでは提出概念なし
                    'progress_percentage': progress_percentage,
                    'can_start': total_lessons > 0,
                    'system_type': 'lessons',
                    'total_lessons': total_lessons,
                    'completed_lessons': completed_lessons,
                    'in_progress_lessons': in_progress_lessons
                })

        # 全体統計の計算
        total_available = len(available_curricula)
        total_my_progress = len(my_progress)
        completed_curricula = len([p for p in my_progress if p['progress_percentage'] >= 100])
        in_progress_curricula = len([p for p in my_progress if 0 < p['progress_percentage'] < 100])
        
        learning_stats = {
            "total_available": total_available,
            "selected_count": total_my_progress,
            "completed_count": completed_curricula,
            "in_progress_count": in_progress_curricula,
        }

        return render_template(
            "student/learning_portal.html",
            available_curricula=available_curricula,
            my_progress=my_progress,
            learning_stats=learning_stats
        )

    except Exception as e:
        import traceback
        current_app.logger.error(f"Learning portal error: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        flash("学習ポータルの読み込み中にエラーが発生しました。", "error")
        return redirect(url_for("student_dashboard.dashboard"))


@learning_bp.route("/unit/<int:unit_id>")
@login_required
@student_required  
def unit_detail(unit_id):
    """単元詳細と学習 - レッスンシステムにリダイレクト"""
    try:
        unit = CurriculumUnit.query.get(unit_id)
        
        # 単元が存在しない場合の処理
        if not unit:
            current_app.logger.warning(f"Unit {unit_id} not found, checking if it's a curriculum ID")
            
            # unit_idがcurriculum_idとして使われている可能性をチェック
            curriculum = Curriculum.query.get(unit_id)
            if curriculum:
                # クラス配信チェック
                from app.models import ClassEnrollment
                enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
                class_ids = [e.class_id for e in enrollments]
                
                if curriculum.class_id not in class_ids:
                    flash("このカリキュラムはあなたのクラスに配信されていません。", "error")
                    return redirect(url_for("student_learning.learning_portal"))
                
                # レッスンシステムが利用可能かチェック
                lesson_count = CurriculumLesson.query.filter_by(curriculum_id=unit_id).count()
                current_app.logger.info(f"Direct curriculum {unit_id} has {lesson_count} lessons")
                
                if lesson_count > 0:
                    flash(f"「{curriculum.title}」のレッスン一覧に移動します。", "info")
                    return redirect(url_for("student_learning.curriculum_lessons", curriculum_id=unit_id))
                
                # レッスンシステムのみをサポート
            
            # どちらも存在しない場合
            flash("指定された学習単元が見つかりません。", "error")
            return redirect(url_for("student_learning.learning_portal"))

        # 選択状況を確認
        selection = StudentUnitSelection.query.filter_by(
            student_id=current_user.id, unit_id=unit_id
        ).first()

        if not selection:
            flash("この単元を学習するには、まず選択してください。", "warning")
            return redirect(url_for("student_learning.learning_portal"))

        # カリキュラムベースシステムに移行済みかチェック
        if unit.legacy_curriculum_id:
            curriculum_id = unit.legacy_curriculum_id
            current_app.logger.info(f"Unit {unit_id} checking systems for curriculum {curriculum_id}")
            
            # クラス配信チェック
            curriculum = Curriculum.query.get(curriculum_id)
            if curriculum:
                from app.models import ClassEnrollment
                enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
                class_ids = [e.class_id for e in enrollments]
                
                if curriculum.class_id not in class_ids:
                    flash("このカリキュラムはあなたのクラスに配信されていません。", "error")
                    return redirect(url_for("student_learning.learning_portal"))
            
            # レッスンシステムが利用可能かチェック
            lesson_count = CurriculumLesson.query.filter_by(curriculum_id=curriculum_id).count()
            current_app.logger.info(f"Curriculum {curriculum_id} has {lesson_count} lessons")
            
            if lesson_count > 0:
                # レッスンが存在する場合はレッスン一覧にリダイレクト
                flash(f"「{unit.title}」はレッスン形式学習に移行しました。", "info")
                return redirect(url_for("student_learning.curriculum_lessons", curriculum_id=curriculum_id))
            
            # レッスンシステムのみをサポート - タスクシステムは削除済み

        # 従来の問題ベース学習をサポート (後方互換性)
        current_app.logger.warning(f"Unit {unit_id} has no modern learning system, falling back to legacy mode")
        flash("この単元は新しい学習システムへの移行をご検討ください。", "info")
        
        # カリキュラムベースシステムへの移行案内を表示
        return render_template(
            "student/unit_detail.html", 
            unit=unit, 
            selection=selection,
            problems=[],  # 空の問題リスト
            progress_records={},  # 空の進捗記録
            stats={
                'total_problems': 0,
                'completed_problems': 0,
                'in_progress_problems': 0,
                'progress_percentage': 0
            },
            migration_mode=True  # 移行案内モード
        )

    except Exception as e:
        current_app.logger.error(f"Unit detail error for unit_id {unit_id}: {str(e)}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        flash("単元詳細の読み込み中にエラーが発生しました。", "error")
        return redirect(url_for("student_learning.learning_portal"))


@learning_bp.route("/curriculum/<int:curriculum_id>/direct")
@login_required
@student_required
def curriculum_direct_access(curriculum_id):
    """カリキュラムへの直接アクセス - ダッシュボードからのリンク用"""
    try:
        curriculum = Curriculum.query.get_or_404(curriculum_id)
        
        # クラス配信チェック
        from app.models import ClassEnrollment
        enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
        class_ids = [e.class_id for e in enrollments]
        
        if curriculum.class_id not in class_ids:
            flash("このカリキュラムはあなたのクラスに配信されていません。", "error")
            return redirect(url_for("student_learning.learning_portal"))
        
        # レッスンシステムが利用可能かチェック
        lesson_count = CurriculumLesson.query.filter_by(curriculum_id=curriculum_id).count()
        current_app.logger.info(f"Direct access to curriculum {curriculum_id}: {lesson_count} lessons")
        
        if lesson_count > 0:
            flash(f"「{curriculum.title}」のレッスン一覧に移動します。", "info")
            return redirect(url_for("student_learning.curriculum_lessons", curriculum_id=curriculum_id))
        
        # レッスンシステムのみをサポート - タスクシステムは削除済み
        
        # レッスンが存在しない場合
        flash(f"「{curriculum.title}」にはまだ学習コンテンツが設定されていません。", "warning")
        return redirect(url_for("student_learning.learning_portal"))
        
    except Exception as e:
        current_app.logger.error(f"Direct curriculum access error: {str(e)}")
        flash("カリキュラムへのアクセス中にエラーが発生しました。", "error")
        return redirect(url_for("student_learning.learning_portal"))


# ============================================
# レッスンシステム機能
# ============================================

@learning_bp.route("/curriculum/<int:curriculum_id>/lessons")
@login_required
@student_required
def curriculum_lessons(curriculum_id):
    """カリキュラムのレッスン一覧表示"""
    try:
        # レッスンモデルの遅延インポート
        LESSON_SYSTEM_AVAILABLE = get_lesson_models()
        
        current_app.logger.info(f"curriculum_lessons called for curriculum_id: {curriculum_id}")
        current_app.logger.info(f"LESSON_SYSTEM_AVAILABLE: {LESSON_SYSTEM_AVAILABLE}")
        current_app.logger.info(f"CurriculumLesson is None: {CurriculumLesson is None}")
        
        # レッスンシステムが利用可能かチェック
        if not LESSON_SYSTEM_AVAILABLE or CurriculumLesson is None:
            current_app.logger.error("Lesson system models not available")
            flash("レッスンシステムが利用できません。", "error")
            return redirect(url_for("student_learning.learning_portal"))
            
        curriculum = Curriculum.query.get_or_404(curriculum_id)
        current_app.logger.info(f"Found curriculum: {curriculum.title}")
        
        # レッスン一覧を取得（順序付き）
        try:
            lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum_id)\
                .order_by(CurriculumLesson.lesson_number).all()
            current_app.logger.info(f"Found {len(lessons)} lessons for curriculum {curriculum_id}")
        except Exception as lesson_error:
            current_app.logger.error(f"Failed to fetch lessons: {str(lesson_error)}")
            flash("レッスン一覧の取得に失敗しました。", "error")
            return redirect(url_for("student_learning.learning_portal"))
            
        # 学生の進捗データを取得
        lesson_progresses = {}
        if lessons:
            try:
                progresses = StudentLessonProgress.query.filter_by(
                    student_id=current_user.id
                ).filter(
                    StudentLessonProgress.lesson_id.in_([l.id for l in lessons])
                ).all()
                lesson_progresses = {p.lesson_id: p for p in progresses}
            except Exception as progress_error:
                current_app.logger.error(f"Failed to fetch lesson progress: {str(progress_error)}")
                # 進捗データが取得できなくても続行
        
        # レッスンごとの進捗情報を付与
        lesson_data = []
        for lesson in lessons:
            progress = lesson_progresses.get(lesson.id)
            lesson_data.append({
                'lesson': lesson,
                'progress': progress,
                'is_completed': progress.is_completed if progress else False,
                'completion_percentage': progress.completion_percentage if progress else 0,
                'can_start': True,  # 制限なしで開始可能
            })
        
        current_app.logger.info(f"Rendering template with {len(lesson_data)} lesson items")
        return render_template(
            "student/curriculum_lessons.html",
            curriculum=curriculum,
            lesson_data=lesson_data
        )
        
    except Exception as e:
        current_app.logger.error(f"Curriculum lessons error: {str(e)}")
        flash("レッスン一覧の読み込み中にエラーが発生しました。", "error")
        return redirect(url_for("student_learning.learning_portal"))


@learning_bp.route("/lesson/<int:lesson_id>")
@login_required
@student_required
def lesson_detail(lesson_id):
    """レッスン詳細表示と学習"""
    try:
        # レッスンモデルの遅延インポート
        LESSON_SYSTEM_AVAILABLE = get_lesson_models()
        
        # レッスンシステムが利用可能かチェック
        if not LESSON_SYSTEM_AVAILABLE or CurriculumLesson is None:
            current_app.logger.error("Lesson system models not available")
            flash("レッスンシステムが利用できません。", "error")
            return redirect(url_for("student_learning.learning_portal"))
            
        lesson = CurriculumLesson.query.get_or_404(lesson_id)
        
        # 学生の進捗データ取得または作成
        progress = StudentLessonProgress.query.filter_by(
            student_id=current_user.id, lesson_id=lesson_id
        ).first()
        
        if not progress:
            # 進捗レコードが存在しない場合は作成
            progress = StudentLessonProgress(
                student_id=current_user.id,
                lesson_id=lesson_id,
                completion_percentage=0,
                is_completed=False
            )
            db.session.add(progress)
            db.session.commit()
        
        # レッスンのタスク一覧を取得
        lesson_tasks = LessonTask.query.filter_by(lesson_id=lesson_id)\
            .order_by(LessonTask.task_number).all()
        
        # タスクの完了状況を取得
        task_checks = {}
        if lesson_tasks:
            checks = StudentTaskCheck.query.filter_by(
                student_id=current_user.id
            ).filter(
                StudentTaskCheck.task_id.in_([t.id for t in lesson_tasks])
            ).all()
            task_checks = {c.task_id: c for c in checks}
        
        # タスクデータを構築
        task_data = []
        for task in lesson_tasks:
            check = task_checks.get(task.id)
            task_data.append({
                'task': task,
                'check': check,
                'is_completed': check and check.status == TaskCheckStatus.COMPLETED,
                'status': check.status if check else None
            })
        
        return render_template(
            "student/lesson_detail.html",
            lesson=lesson,
            progress=progress,
            task_data=task_data
        )
        
    except Exception as e:
        current_app.logger.error(f"Lesson detail error: {str(e)}")
        flash("レッスン詳細の読み込み中にエラーが発生しました。", "error")
        return redirect(url_for("student_learning.curriculum_lessons", curriculum_id=lesson.curriculum_id))