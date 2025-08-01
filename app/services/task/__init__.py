"""
タスクサービスモジュール

task_management.pyを3つの専門サービスに分割:
- TaskCRUDService: 課題のCRUD操作専門
- TaskProgressService: 学生進捗管理専門
- TaskValidationService: 入力検証専門
"""

from .task_crud_service import TaskCRUDService
from .task_progress_service import TaskProgressService
from .task_validation_service import TaskValidationService

__all__ = [
    "TaskCRUDService",
    "TaskProgressService",
    "TaskValidationService"
]