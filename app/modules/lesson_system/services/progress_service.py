"""
レッスン進捗サービス

学生のレッスン進捗管理と3状態管理を担当
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.models import db
from ..models.lesson_models import StudentLessonProgress, StudentTaskCheck, CurriculumLesson, LessonTask, TaskCheckStatus


class LessonProgressService:
    """レッスン進捗管理サービス"""
    
    @staticmethod
    def get_student_progress(student_id: int, lesson_id: int) -> Optional[StudentLessonProgress]:
        """学生のレッスン進捗を取得"""
        try:
            return StudentLessonProgress.query.filter_by(
                student_id=student_id,
                lesson_id=lesson_id
            ).first()
        except SQLAlchemyError as e:
            current_app.logger.error(f"Failed to fetch progress for student {student_id}, lesson {lesson_id}: {e}")
            return None
    
    @staticmethod
    def create_or_update_progress(student_id: int, lesson_id: int, progress_data: Dict[str, Any]) -> Optional[StudentLessonProgress]:
        """レッスン進捗を作成または更新"""
        try:
            progress = LessonProgressService.get_student_progress(student_id, lesson_id)
            
            if not progress:
                # 新規作成
                progress = StudentLessonProgress(
                    student_id=student_id,
                    lesson_id=lesson_id,
                    started_at=datetime.utcnow()
                )
                db.session.add(progress)
            
            # 更新可能なフィールド
            updatable_fields = [
                'time_spent_minutes', 'understanding_level', 'difficulty_level',
                'reflection', 'completion_percentage'
            ]
            
            for field in updatable_fields:
                if field in progress_data:
                    setattr(progress, field, progress_data[field])
            
            # 完了判定
            completion_percentage = progress_data.get('completion_percentage', progress.completion_percentage or 0)
            if completion_percentage >= 100 and not progress.is_completed:
                progress.is_completed = True
                progress.completed_at = datetime.utcnow()
            
            progress.updated_at = datetime.utcnow()
            db.session.commit()
            
            return progress
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to update progress: {e}")
            return None
    
    @staticmethod
    def get_student_task_checks(student_id: int, lesson_id: int) -> List[StudentTaskCheck]:
        """学生のタスクチェック状況を取得"""
        try:
            progress = LessonProgressService.get_student_progress(student_id, lesson_id)
            if not progress:
                return []
            
            return StudentTaskCheck.query.filter_by(
                student_id=student_id,
                lesson_progress_id=progress.id
            ).all()
            
        except SQLAlchemyError as e:
            current_app.logger.error(f"Failed to fetch task checks: {e}")
            return []
    
    @staticmethod
    def update_task_check(student_id: int, task_id: int, status: TaskCheckStatus, notes: str = None) -> bool:
        """タスクチェック状況を更新"""
        try:
            # タスクから対応するレッスンを取得
            task = LessonTask.query.get(task_id)
            if not task:
                return False
            
            # 進捗レコードを取得または作成
            progress = LessonProgressService.get_student_progress(student_id, task.lesson_id)
            if not progress:
                progress = LessonProgressService.create_or_update_progress(
                    student_id, task.lesson_id, {}
                )
            
            # タスクチェック状況を取得または作成
            task_check = StudentTaskCheck.query.filter_by(
                student_id=student_id,
                lesson_progress_id=progress.id,
                task_id=task_id
            ).first()
            
            if not task_check:
                task_check = StudentTaskCheck(
                    student_id=student_id,
                    lesson_progress_id=progress.id,
                    task_id=task_id,
                    status=status,
                    checked_at=datetime.utcnow()
                )
                db.session.add(task_check)
            else:
                task_check.status = status
                task_check.checked_at = datetime.utcnow()
            
            if status == TaskCheckStatus.COMPLETED:
                task_check.completed_at = datetime.utcnow()
            
            if notes:
                task_check.notes = notes
            
            db.session.commit()
            
            # レッスンの完了率を再計算
            LessonProgressService._recalculate_lesson_progress(student_id, task.lesson_id)
            
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to update task check: {e}")
            return False
    
    @staticmethod
    def _recalculate_lesson_progress(student_id: int, lesson_id: int):
        """レッスンの進捗率を再計算"""
        try:
            # レッスンの全タスクを取得
            lesson_tasks = LessonTask.query.filter_by(lesson_id=lesson_id).all()
            if not lesson_tasks:
                return
            
            total_tasks = len(lesson_tasks)
            
            # 完了済みタスクを計算
            progress = LessonProgressService.get_student_progress(student_id, lesson_id)
            if not progress:
                return
            
            completed_tasks = StudentTaskCheck.query.filter_by(
                student_id=student_id,
                lesson_progress_id=progress.id,
                status=TaskCheckStatus.COMPLETED
            ).count()
            
            # 完了率を計算
            completion_percentage = int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0
            
            # 進捗を更新
            progress.completion_percentage = completion_percentage
            if completion_percentage >= 100 and not progress.is_completed:
                progress.is_completed = True
                progress.completed_at = datetime.utcnow()
            
            db.session.commit()
            
        except Exception as e:
            current_app.logger.error(f"Failed to recalculate lesson progress: {e}")
    
    @staticmethod
    def get_curriculum_progress_summary(student_id: int, curriculum_id: int) -> Dict[str, Any]:
        """カリキュラム全体の進捗サマリーを取得"""
        try:
            lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum_id).all()
            
            total_lessons = len(lessons)
            completed_lessons = 0
            in_progress_lessons = 0
            total_completion_percentage = 0
            
            for lesson in lessons:
                progress = LessonProgressService.get_student_progress(student_id, lesson.id)
                if progress:
                    completion_percentage = progress.completion_percentage or 0
                    total_completion_percentage += completion_percentage
                    
                    if progress.is_completed:
                        completed_lessons += 1
                    elif completion_percentage > 0:
                        in_progress_lessons += 1
            
            overall_progress = int(total_completion_percentage / total_lessons) if total_lessons > 0 else 0
            
            return {
                'total_lessons': total_lessons,
                'completed_lessons': completed_lessons,
                'in_progress_lessons': in_progress_lessons,
                'not_started_lessons': total_lessons - completed_lessons - in_progress_lessons,
                'overall_completion_percentage': overall_progress
            }
            
        except Exception as e:
            current_app.logger.error(f"Failed to calculate curriculum progress summary: {e}")
            return {
                'total_lessons': 0,
                'completed_lessons': 0,
                'in_progress_lessons': 0,
                'not_started_lessons': 0,
                'overall_completion_percentage': 0
            }