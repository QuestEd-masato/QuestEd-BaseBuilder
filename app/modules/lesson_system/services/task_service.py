# app/modules/lesson_system/services/task_service.py
"""
Task Service for Lesson System
==============================
レッスンタスクの管理・進捗処理サービス
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, desc

from app.models import db
from ..models.lesson_models import (
    LessonTask, StudentTaskCheck, TaskCheckStatus, 
    StudentLessonProgress, CurriculumLesson
)


class TaskService:
    """レッスンタスク管理サービス"""
    
    @staticmethod
    def get_student_tasks(student_id: int, lesson_id: Optional[int] = None) -> List[Dict]:
        """学生のタスク一覧取得"""
        try:
            query = db.session.query(LessonTask)
            
            if lesson_id:
                query = query.filter(LessonTask.lesson_id == lesson_id)
            else:
                # 学生が進行中のレッスンのタスクを取得
                active_lessons = db.session.query(StudentLessonProgress.lesson_id).filter(
                    StudentLessonProgress.student_id == student_id
                ).subquery()
                
                query = query.filter(LessonTask.lesson_id.in_(active_lessons))
            
            tasks = query.order_by(LessonTask.order_in_lesson).all()
            
            task_list = []
            for task in tasks:
                # タスクの進捗状況を取得
                progress = StudentTaskCheck.query.filter_by(
                    student_id=student_id,
                    task_id=task.id
                ).first()
                
                task_info = {
                    'id': task.id,
                    'title': task.title,
                    'description': task.description,
                    'type': task.task_type.value if task.task_type else 'general',
                    'order': task.order_in_lesson,
                    'lesson_id': task.lesson_id,
                    'lesson_title': task.lesson.title if task.lesson else '',
                    'estimated_minutes': task.estimated_minutes or 0,
                    'difficulty_level': task.difficulty_level or 1,
                    'status': progress.status.value if progress else 'not_checked',
                    'completed_at': progress.completed_at if progress else None,
                    'time_spent': progress.time_spent_minutes if progress else 0,
                    'notes': progress.notes if progress else ''
                }
                task_list.append(task_info)
            
            return task_list
            
        except Exception as e:
            print(f"[ERROR] Get student tasks failed: {e}")
            return []
    
    @staticmethod
    def update_task_progress(student_id: int, task_id: int, status: str, 
                           time_spent: int = 0, notes: str = '') -> bool:
        """タスク進捗更新"""
        try:
            # レッスン進捗を取得または作成
            task = LessonTask.query.get(task_id)
            if not task:
                return False
            
            lesson_progress = StudentLessonProgress.query.filter_by(
                student_id=student_id,
                lesson_id=task.lesson_id
            ).first()
            
            if not lesson_progress:
                lesson_progress = StudentLessonProgress(
                    student_id=student_id,
                    lesson_id=task.lesson_id,
                    started_at=datetime.utcnow()
                )
                db.session.add(lesson_progress)
                db.session.flush()
            
            # タスクチェック記録を取得または作成
            task_check = StudentTaskCheck.query.filter_by(
                student_id=student_id,
                lesson_progress_id=lesson_progress.id,
                task_id=task_id
            ).first()
            
            if not task_check:
                task_check = StudentTaskCheck(
                    student_id=student_id,
                    lesson_progress_id=lesson_progress.id,
                    task_id=task_id,
                    status=TaskCheckStatus.NOT_CHECKED
                )
                db.session.add(task_check)
            
            # ステータス更新
            try:
                task_check.status = TaskCheckStatus(status)
            except ValueError:
                task_check.status = TaskCheckStatus.NOT_CHECKED
            
            task_check.time_spent_minutes = time_spent
            task_check.notes = notes
            task_check.checked_at = datetime.utcnow()
            
            if status == 'completed':
                task_check.completed_at = datetime.utcnow()
            
            # 進捗の最終活動時刻更新
            lesson_progress.updated_at = datetime.utcnow()
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Update task progress failed: {e}")
            return False
    
    @staticmethod
    def get_lesson_completion_rate(student_id: int, lesson_id: int) -> float:
        """レッスン完了率計算"""
        try:
            # レッスンの全タスク数
            total_tasks = LessonTask.query.filter_by(lesson_id=lesson_id).count()
            
            if total_tasks == 0:
                return 0.0
            
            # 完了済みタスク数
            lesson_progress = StudentLessonProgress.query.filter_by(
                student_id=student_id,
                lesson_id=lesson_id
            ).first()
            
            if not lesson_progress:
                return 0.0
            
            completed_tasks = StudentTaskCheck.query.filter_by(
                student_id=student_id,
                lesson_progress_id=lesson_progress.id,
                status=TaskCheckStatus.COMPLETED
            ).count()
            
            return (completed_tasks / total_tasks) * 100
            
        except Exception as e:
            print(f"[ERROR] Lesson completion rate calculation failed: {e}")
            return 0.0
    
    @staticmethod
    def get_student_task_statistics(student_id: int, period_days: int = 30) -> Dict:
        """学生のタスク統計取得"""
        try:
            start_date = datetime.utcnow() - timedelta(days=period_days)
            
            # 期間内の完了タスク数
            completed_count = StudentTaskCheck.query.filter(
                StudentTaskCheck.student_id == student_id,
                StudentTaskCheck.status == TaskCheckStatus.COMPLETED,
                StudentTaskCheck.completed_at >= start_date
            ).count()
            
            # 総学習時間
            total_time = db.session.query(
                func.sum(StudentTaskCheck.time_spent_minutes)
            ).filter(
                StudentTaskCheck.student_id == student_id,
                StudentTaskCheck.completed_at >= start_date
            ).scalar() or 0
            
            # 進行中のタスク数
            in_progress_count = StudentTaskCheck.query.filter(
                StudentTaskCheck.student_id == student_id,
                StudentTaskCheck.status == TaskCheckStatus.IN_PROGRESS
            ).count()
            
            # アクティブなレッスン数
            active_lessons_count = StudentLessonProgress.query.filter(
                StudentLessonProgress.student_id == student_id,
                StudentLessonProgress.completed_at.is_(None)
            ).count()
            
            return {
                'completed_tasks': completed_count,
                'total_time_minutes': total_time,
                'in_progress_tasks': in_progress_count,
                'active_lessons': active_lessons_count,
                'average_time_per_task': total_time / completed_count if completed_count > 0 else 0,
                'period_days': period_days
            }
            
        except Exception as e:
            print(f"[ERROR] Student task statistics failed: {e}")
            return {
                'completed_tasks': 0,
                'total_time_minutes': 0,
                'in_progress_tasks': 0,
                'active_lessons': 0,
                'average_time_per_task': 0,
                'period_days': period_days
            }
    
    @staticmethod
    def mark_task_completed(student_id: int, task_id: int, time_spent: int = 0, 
                          notes: str = '') -> bool:
        """タスクを完了としてマーク"""
        return TaskService.update_task_progress(
            student_id, task_id, 'completed', time_spent, notes
        )
    
    @staticmethod
    def start_task(student_id: int, task_id: int) -> bool:
        """タスク開始"""
        return TaskService.update_task_progress(
            student_id, task_id, 'in_progress'
        )
    
    @staticmethod
    def get_task_details(task_id: int) -> Optional[Dict]:
        """タスク詳細情報取得"""
        try:
            task = LessonTask.query.get(task_id)
            if not task:
                return None
            
            return {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'type': task.task_type.value if task.task_type else 'general',
                'estimated_minutes': task.estimated_minutes or 0,
                'difficulty_level': task.difficulty_level or 1,
                'order_in_lesson': task.order_in_lesson,
                'lesson_id': task.lesson_id,
                'lesson_title': task.lesson.title if task.lesson else '',
                'lesson_number': task.lesson.lesson_number if task.lesson else 0,
                'curriculum_title': task.lesson.curriculum.title if task.lesson and task.lesson.curriculum else '',
                'created_at': task.created_at,
                'updated_at': task.updated_at
            }
            
        except Exception as e:
            print(f"[ERROR] Get task details failed: {e}")
            return None
    
    @staticmethod
    def get_next_task(student_id: int, current_task_id: int) -> Optional[Dict]:
        """次のタスクを取得"""
        try:
            current_task = LessonTask.query.get(current_task_id)
            if not current_task:
                return None
            
            # 同じレッスン内の次のタスクを探す
            next_task = LessonTask.query.filter(
                LessonTask.lesson_id == current_task.lesson_id,
                LessonTask.order_in_lesson > current_task.order_in_lesson
            ).order_by(LessonTask.order_in_lesson).first()
            
            if next_task:
                return TaskService.get_task_details(next_task.id)
            
            # 同じレッスン内に次のタスクがない場合、次のレッスンの最初のタスクを探す
            current_lesson = current_task.lesson
            if not current_lesson:
                return None
            
            next_lesson = CurriculumLesson.query.filter(
                CurriculumLesson.curriculum_id == current_lesson.curriculum_id,
                CurriculumLesson.lesson_number > current_lesson.lesson_number
            ).order_by(CurriculumLesson.lesson_number).first()
            
            if next_lesson:
                first_task = LessonTask.query.filter_by(
                    lesson_id=next_lesson.id
                ).order_by(LessonTask.order_in_lesson).first()
                
                if first_task:
                    return TaskService.get_task_details(first_task.id)
            
            return None
            
        except Exception as e:
            print(f"[ERROR] Get next task failed: {e}")
            return None