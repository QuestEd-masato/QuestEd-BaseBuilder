"""
レッスンシステムモジュール

このモジュールは以下の機能を提供します：
- カリキュラムレッスン管理
- レッスンタスク管理
- 学生のレッスン進捗追跡
- タスクチェック機能
- 3状態管理（未完了・進行中・完了）
"""

from .services.lesson_service import LessonService
from .services.progress_service import LessonProgressService
from .models.lesson_models import CurriculumLesson, LessonTask, StudentLessonProgress, StudentTaskCheck
from .routes.lesson_routes import lesson_bp

__all__ = [
    'LessonService',
    'LessonProgressService', 
    'CurriculumLesson',
    'LessonTask',
    'StudentLessonProgress',
    'StudentTaskCheck',
    'lesson_bp'
]

__version__ = '1.0.0'