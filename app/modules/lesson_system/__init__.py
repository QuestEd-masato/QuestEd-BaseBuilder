"""
レッスンシステムモジュール

このモジュールは以下の機能を提供します：
- カリキュラムレッスン管理
- レッスンタスク管理
- 学生のレッスン進捗追跡
- タスクチェック機能
- 3状態管理（未完了・進行中・完了）
- レッスン完了申請・承認機能（Phase5追加）
"""

from .services.lesson_service import LessonService
from .services.progress_service import LessonProgressService
from .services.approval_service import LessonApprovalService
from .models.lesson_models import CurriculumLesson, LessonTask, StudentLessonProgress, StudentTaskCheck
from .routes.lesson_routes import lesson_bp
from .routes.approval_routes import approval_bp as lesson_approval_bp

__all__ = [
    'LessonService',
    'LessonProgressService',
    'LessonApprovalService',
    'CurriculumLesson',
    'LessonTask',
    'StudentLessonProgress',
    'StudentTaskCheck',
    'lesson_bp',
    'lesson_approval_bp'
]

__version__ = '1.0.0'