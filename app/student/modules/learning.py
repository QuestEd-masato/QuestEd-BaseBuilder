# app/student/modules/learning.py
"""学生学習ポータル機能 - レッスンシステムとの統合インターフェース"""

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

from app.models import CurriculumUnit, StudentUnitSelection, User, Curriculum, db, ClassEnrollment, Class

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

# ===== 責任境界の明確化 (Phase A-2) =====
# 
# student_learning.py の責任:
# 1. 学習ポータル (learning_portal) - メイン機能
# 2. 単元詳細 (unit_detail) - レガシーサポート
# 3. レッスンシステムとの連携インターフェース (curriculum_lessons等のリダイレクト)
# 
# lesson_system.py の責任:  
# 1. レッスン管理 (curriculum_lessons, lesson_detail)
# 2. タスク管理 (task_*, lesson_learning)
# 3. レッスン進捗管理
# 
# リダイレクト層は Phase B で段階的削除予定
# ================================================


@learning_bp.route("/learning")
@login_required
@student_required
def learning_portal():
    """統合学習ポータル - レッスンシステムのみ"""
    # ✅ Phase 1: 緊急診断ログ実装
    current_app.logger.info(f"[DEBUG] learning_portal:start user_id={current_user.id}")

    try:
        # 🔍 Phase 1: レッスンモデルインポート診断
        try:
            LESSON_SYSTEM_AVAILABLE = get_lesson_models()
            current_app.logger.info(f"[DEBUG] lesson_models_import: success={LESSON_SYSTEM_AVAILABLE}")

            if not LESSON_SYSTEM_AVAILABLE:
                current_app.logger.error("[CRITICAL] lesson_models_import failed - cannot proceed")
                flash("システムの初期化中にエラーが発生しました。管理者にお問い合わせください。", "error")
                return redirect(url_for("student_dashboard.dashboard"))

        except Exception as import_error:
            current_app.logger.error(f"[CRITICAL] lesson_models_import exception: {str(import_error)}")
            import traceback
            current_app.logger.error(f"[CRITICAL] lesson_models_import traceback: {traceback.format_exc()}")
            raise import_error
        # 🔍 Phase 1: クラス所属診断
        try:
            enrollments = ClassEnrollment.query.filter_by(
                student_id=current_user.id,
                is_active=True  # ✅ 修正: is_activeフィルタ追加
            ).all()
            class_ids = [e.class_id for e in enrollments]
            current_app.logger.info(f"[DEBUG] enrollment_check: user_id={current_user.id} classes={len(class_ids)}")

        except Exception as enrollment_error:
            current_app.logger.error(f"[CRITICAL] enrollment_query failed: user_id={current_user.id} error={str(enrollment_error)}")
            import traceback
            current_app.logger.error(f"[CRITICAL] enrollment_query traceback: {traceback.format_exc()}")
            raise enrollment_error
        
        if not class_ids:
            current_app.logger.warning(f"[WARN] no_enrollment: user_id={current_user.id}")
            flash("所属クラスが見つかりません。管理者にお問い合わせください。", "warning")
            return render_template("student/learning_portal.html",
                                 available_curricula=[], my_progress=[])
        
        # 利用可能なカリキュラムを取得（クラス単位）
        available_curricula = []
        for class_id in class_ids:
            class_obj = Class.query.get(class_id)
            if class_obj:
                class_curricula = Curriculum.query.filter_by(class_id=class_id).all()
                for curriculum in class_curricula:
                    # Phase修正: curriculum_dataからレッスン数を取得
                    total_lessons = 0
                    
                    # 1. curriculum_lessonsテーブルをチェック
                    if LESSON_SYSTEM_AVAILABLE and CurriculumLesson is not None:
                        try:
                            total_lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum.id).count()
                        except Exception as e:
                            current_app.logger.error(f"CurriculumLesson count error for curriculum {curriculum.id}: {e}")
                    
                    # 2. curriculum_lessonsが0件の場合、移行アダプター経由で取得
                    if total_lessons == 0:
                        try:
                            # Phase 5-3: 移行アダプター経由で統一的に取得
                            from app.services.curriculum.migration_adapter import CurriculumMigrationAdapter
                            content = CurriculumMigrationAdapter.read_curriculum_content(curriculum.id)
                            if content:
                                table_content = content.get('table_content', [])
                                total_lessons = len(table_content)
                                current_app.logger.info(f"Using migration adapter for {curriculum.id}: {total_lessons} lessons")
                        except Exception as e:
                            current_app.logger.error(f"Error reading curriculum content for {curriculum.id}: {e}")
                    
                    # Fix: 新規カリキュラム対応 - レッスンが0でもカリキュラムを表示
                    # レッスン数に関わらず、すべてのカリキュラムを表示対象にする
                    available_curricula.append({
                        'curriculum': curriculum,
                        'class_name': class_obj.name,
                        'total_lessons': total_lessons,
                        'system_type': 'lessons' if total_lessons > 0 else 'empty',
                        'is_empty': total_lessons == 0
                    })

        # 学生の進捗状況を取得（レッスンシステムのみ）
        my_progress = []
        for curriculum_data in available_curricula:
            curriculum = curriculum_data['curriculum']
            
            # Phase修正: curriculum_lessonsとcurriculum_dataの統合進捗処理
            total_lessons = curriculum_data['total_lessons']
            completed_lessons = 0
            in_progress_lessons = 0
            total_lesson_tasks = 0
            completed_lesson_tasks = 0
            
            # 1. curriculum_lessonsテーブルベースの進捗（優先）
            lessons = []
            if LESSON_SYSTEM_AVAILABLE and CurriculumLesson is not None:
                try:
                    lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum.id).all()
                except Exception as lesson_error:
                    current_app.logger.error(f"Lesson progress query error: {str(lesson_error)}")
                    lessons = []
            
            if lessons:
                # curriculum_lessonsベースの詳細進捗計算
                total_lesson_tasks = 0
                completed_lesson_tasks = 0
                
                for lesson in lessons:
                    try:
                        # レッスンの進捗を取得
                        lesson_progress = StudentLessonProgress.query.filter_by(
                            student_id=current_user.id, lesson_id=lesson.id
                        ).first()
                        
                        if lesson_progress:
                            # Phase5: 承認済みレッスンのみを完了とする
                            if hasattr(lesson_progress, 'approval_status') and lesson_progress.approval_status == 'approved':
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
            else:
                # 2. curriculum_dataベースの簡易進捗計算
                total_lesson_tasks = total_lessons  # 1レッスン=1タスクとして簡略化
                completed_lesson_tasks = 0  # 実際の進捗は未実装のため0
                progress_percentage = 0.0
                current_app.logger.info(f"Using simple progress for curriculum_data based curriculum {curriculum.id}")
            
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
                'system_type': curriculum_data.get('system_type', 'lessons'),
                'is_empty': curriculum_data.get('is_empty', False),
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

        # ✅ Phase 1: 成功ログ
        current_app.logger.info(f"[DEBUG] learning_portal:success user_id={current_user.id} "
                               f"curricula={total_available} progress_items={total_my_progress}")

        return render_template(
            "student/learning_portal.html",
            available_curricula=available_curricula,
            my_progress=my_progress,
            learning_stats=learning_stats
        )

    except Exception as e:
        import traceback
        # ✅ Phase 1: 詳細エラーログ改善
        current_app.logger.error(f"[CRITICAL] learning_portal_error: user_id={current_user.id} error={str(e)}")
        current_app.logger.error(f"[CRITICAL] learning_portal_traceback: {traceback.format_exc()}")
        flash("学習ポータルの読み込み中にエラーが発生しました。", "error")
        return redirect(url_for("student_dashboard.dashboard"))


@learning_bp.route("/lesson/<int:lesson_id>")
@login_required
@student_required
def lesson_detail(lesson_id):
    """レッスン詳細表示 - lesson_systemへのリダイレクト"""
    try:
        # lesson_systemのlesson_detailにリダイレクト
        return redirect(url_for('lesson_system.lesson_detail', lesson_id=lesson_id))
    except Exception as e:
        current_app.logger.error(f"Error in lesson_detail redirect: {e}")
        flash("レッスン詳細の読み込み中にエラーが発生しました。", "error")
        return redirect(url_for('student_learning.learning_portal'))


# ===== Phase B-3: lesson_learning統合完了 =====
# lesson_learning機能は削除済み
# テンプレートで直接 lesson_system.lesson_detail を参照するよう変更


# ===== Phase B-2: タスクルート削除 =====
# タスク機能は lesson_system.py で管理
# テンプレートで404エラーの場合、lesson_systemへの移行を促すメッセージ表示


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
# カリキュラム詳細表示機能（学生用）
# ============================================

@learning_bp.route("/curriculum/<int:curriculum_id>")
@login_required
@student_required
def curriculum_detail(curriculum_id):
    """学生用カリキュラム詳細表示"""
    try:
        
        # カリキュラムの存在確認
        curriculum = Curriculum.query.get_or_404(curriculum_id)
        
        # アクセス権限チェック：学生が所属するクラスのカリキュラムのみ表示
        enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
        class_ids = [e.class_id for e in enrollments]
        
        if curriculum.class_id not in class_ids:
            flash("このカリキュラムにはアクセスできません。", "error")
            return redirect(url_for("student_learning.learning_portal"))
        
        # レッスン取得
        lessons = []
        if get_lesson_models() and CurriculumLesson:
            try:
                lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum_id).all()
            except Exception as e:
                current_app.logger.error(f"Failed to get lessons for curriculum {curriculum_id}: {e}")
        
        # クラス情報取得
        class_obj = Class.query.get(curriculum.class_id)
        
        return render_template(
            "student/curriculum_detail.html",
            curriculum=curriculum,
            lessons=lessons,
            class_name=class_obj.name if class_obj else "不明",
        )
        
    except Exception as e:
        current_app.logger.error(f"Student curriculum detail error for {curriculum_id}: {str(e)}")
        flash("カリキュラム詳細の取得中にエラーが発生しました。", "error")
        return redirect(url_for("student_learning.learning_portal"))


# ============================================
# レッスンシステム機能は新しいモジュール式システムに移行済み
# 旧機能は削除済み - lesson_system ブループリントを使用
# ============================================