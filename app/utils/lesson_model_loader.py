# -*- coding: utf-8 -*-
"""
レッスンモデル共通ローダー

循環インポートを回避しながら、レッスンシステムモデルを
安全にロードするためのユーティリティ
"""
import logging
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)


def get_lesson_models() -> Tuple[Optional[Any], Optional[Any], Optional[Any], Optional[Any], Optional[Any], bool]:
    """
    レッスンシステムモデルを安全にロード（キャッシュなし・シンプル版）
    
    Returns:
        tuple: (CurriculumLesson, LessonTask, StudentLessonProgress, StudentTaskCheck, TaskCheckStatus, availability)
    """
    try:
        from app.modules.lesson_system.models.lesson_models import (
            CurriculumLesson, LessonTask, StudentLessonProgress, 
            StudentTaskCheck, TaskCheckStatus
        )
        
        logger.debug("Lesson system models loaded successfully")
        return CurriculumLesson, LessonTask, StudentLessonProgress, StudentTaskCheck, TaskCheckStatus, True
        
    except ImportError:
        logger.debug("Lesson system models not available during import")
        return None, None, None, None, None, False


def get_basic_lesson_models() -> Tuple[Optional[Any], Optional[Any], bool]:
    """
    基本的なレッスンモデルのみロード（軽量版）
    
    Returns:
        tuple: (CurriculumLesson, StudentLessonProgress, availability)
    """
    try:
        from app.modules.lesson_system.models.lesson_models import (
            CurriculumLesson, StudentLessonProgress
        )
        
        logger.debug("Basic lesson system models loaded successfully")
        return CurriculumLesson, StudentLessonProgress, True
        
    except ImportError:
        logger.debug("Basic lesson system models not available during import")
        return None, None, False


def is_lesson_system_available() -> bool:
    """
    レッスンシステムの利用可能性をチェック
    
    Returns:
        bool: レッスンシステムが利用可能かどうか
    """
    _, _, _, _, _, available = get_lesson_models()
    return available