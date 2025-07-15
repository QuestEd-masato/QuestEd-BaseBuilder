"""
Learning Feature Module
=======================
学習機能の統合モジュール

機能:
- 単元学習進捗管理
- 個別学習計画
- 適応学習システム
- 学習リソース管理
"""

from .adaptive_system import AdaptiveLearningSystem
from .progress_manager import LearningProgressManager
from .resource_manager import LearningResourceManager

__all__ = [
    "LearningProgressManager",
    "AdaptiveLearningSystem",
    "LearningResourceManager",
]
