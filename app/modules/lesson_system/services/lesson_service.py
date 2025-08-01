"""
レッスンサービス

レッスンの管理とビジネスロジックを担当
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.models import db
from ..models.lesson_models import CurriculumLesson, LessonTask, LessonType


class LessonService:
    """レッスン管理サービス"""
    
    @staticmethod
    def get_all_lessons() -> List[CurriculumLesson]:
        """全てのレッスンを取得"""
        try:
            return CurriculumLesson.query.order_by(
                CurriculumLesson.curriculum_id,
                CurriculumLesson.lesson_number
            ).all()
        except SQLAlchemyError as e:
            current_app.logger.error(f"Failed to fetch all lessons: {e}")
            return []
    
    @staticmethod
    def get_lessons_by_curriculum(curriculum_id: int) -> List[CurriculumLesson]:
        """カリキュラムIDでレッスン一覧を取得"""
        try:
            return CurriculumLesson.query.filter_by(
                curriculum_id=curriculum_id
            ).order_by(CurriculumLesson.lesson_number).all()
        except SQLAlchemyError as e:
            current_app.logger.error(f"Failed to fetch lessons for curriculum {curriculum_id}: {e}")
            return []
    
    @staticmethod
    def get_lesson_by_id(lesson_id: int) -> Optional[CurriculumLesson]:
        """レッスンIDでレッスンを取得"""
        try:
            return CurriculumLesson.query.get(lesson_id)
        except SQLAlchemyError as e:
            current_app.logger.error(f"Failed to fetch lesson {lesson_id}: {e}")
            return None
    
    @staticmethod
    def get_lesson_tasks(lesson_id: int) -> List[LessonTask]:
        """レッスンのタスク一覧を取得"""
        try:
            return LessonTask.query.filter_by(
                lesson_id=lesson_id
            ).order_by(LessonTask.task_number).all()
        except SQLAlchemyError as e:
            current_app.logger.error(f"Failed to fetch tasks for lesson {lesson_id}: {e}")
            return []
    
    @staticmethod
    def create_lesson(curriculum_id: int, lesson_data: Dict[str, Any]) -> Optional[CurriculumLesson]:
        """新しいレッスンを作成"""
        try:
            lesson = CurriculumLesson(
                curriculum_id=curriculum_id,
                lesson_number=lesson_data.get('lesson_number'),
                title=lesson_data.get('title'),
                description=lesson_data.get('description'),
                lesson_type=lesson_data.get('lesson_type', LessonType.LECTURE),
                duration_minutes=lesson_data.get('duration_minutes'),
                learning_objectives=lesson_data.get('learning_objectives', []),
                key_points=lesson_data.get('key_points', []),
                created_by=lesson_data.get('created_by')
            )
            
            db.session.add(lesson)
            db.session.commit()
            
            current_app.logger.info(f"Created lesson {lesson.id} for curriculum {curriculum_id}")
            return lesson
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to create lesson: {e}")
            return None
    
    @staticmethod
    def update_lesson(lesson_id: int, lesson_data: Dict[str, Any]) -> bool:
        """レッスン情報を更新"""
        try:
            lesson = CurriculumLesson.query.get(lesson_id)
            if not lesson:
                return False
            
            # 更新可能なフィールドのみ更新
            updatable_fields = [
                'title', 'description', 'lesson_type', 'duration_minutes',
                'learning_objectives', 'key_points', 'evaluation_criteria',
                'resources', 'teacher_notes'
            ]
            
            for field in updatable_fields:
                if field in lesson_data:
                    setattr(lesson, field, lesson_data[field])
            
            lesson.updated_at = datetime.utcnow()
            db.session.commit()
            
            current_app.logger.info(f"Updated lesson {lesson_id}")
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to update lesson {lesson_id}: {e}")
            return False
    
    @staticmethod
    def delete_lesson(lesson_id: int) -> bool:
        """レッスンを削除"""
        try:
            lesson = CurriculumLesson.query.get(lesson_id)
            if not lesson:
                return False
            
            # 関連するタスクも削除
            LessonTask.query.filter_by(lesson_id=lesson_id).delete()
            
            db.session.delete(lesson)
            db.session.commit()
            
            current_app.logger.info(f"Deleted lesson {lesson_id}")
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to delete lesson {lesson_id}: {e}")
            return False
    
    @staticmethod
    def get_lesson_statistics(curriculum_id: int) -> Dict[str, Any]:
        """カリキュラムのレッスン統計を取得"""
        try:
            lessons = LessonService.get_lessons_by_curriculum(curriculum_id)
            
            total_lessons = len(lessons)
            total_duration = sum(lesson.duration_minutes or 0 for lesson in lessons)
            
            lesson_types = {}
            for lesson in lessons:
                lesson_type = lesson.lesson_type.value if lesson.lesson_type else 'unknown'
                lesson_types[lesson_type] = lesson_types.get(lesson_type, 0) + 1
            
            return {
                'total_lessons': total_lessons,
                'total_duration_minutes': total_duration,
                'average_duration': total_duration / total_lessons if total_lessons > 0 else 0,
                'lesson_types': lesson_types
            }
            
        except Exception as e:
            current_app.logger.error(f"Failed to calculate lesson statistics: {e}")
            return {
                'total_lessons': 0,
                'total_duration_minutes': 0,
                'average_duration': 0,
                'lesson_types': {}
            }