# app/ai/curriculum_helpers.py
"""
AIカリキュラムヘルパー - Phase 7-3 リファクタリング版
既存システムとの互換性を維持しながらサービス層を使用
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Phase 7-3: サービス層のインポート
try:
    from app.services.ai import CurriculumGeneratorService
    # グローバルサービスインスタンス（パフォーマンス向上のため）
    _generator_service = CurriculumGeneratorService()
    _service_available = True
    logger.info("Phase 7-3: AI curriculum services initialized successfully")
except Exception as e:
    logger.error(f"Phase 7-3: Failed to initialize AI services: {str(e)}")
    _generator_service = None
    _service_available = False


def generate_curriculum_with_lessons(class_details: Dict[str, Any], curriculum_settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    AIを使用してレッスン形式カリキュラムを生成する
    Phase 7-3: サービス層を使用してリファクタリング
    
    Args:
        class_details: クラスに関する情報（名前、大テーマなど）
        curriculum_settings: カリキュラム設定（時間数、フィールドワーク有無など）

    Returns:
        dict: レッスン形式カリキュラム内容
    """
    try:
        if not _service_available:
            logger.error("AI services not available, returning fallback response")
            return _get_fallback_lesson_template()
        
        return _generator_service.generate_with_lessons(class_details, curriculum_settings)
        
    except Exception as e:
        logger.error(f"Error in generate_curriculum_with_lessons: {str(e)}")
        return _get_fallback_lesson_template()


def generate_curriculum_with_ai(class_details: Dict[str, Any], curriculum_settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    伝統的なカリキュラム生成関数（既存システムとの互換性のため保持）
    Phase 7-3: レッスン形式へリダイレクト
    
    Args:
        class_details: クラスに関する情報（名前、大テーマなど）
        curriculum_settings: カリキュラム設定（時間数、フィールドワーク有無など）

    Returns:
        dict: カリキュラム内容
    """
    try:
        if not _service_available:
            logger.error("AI services not available, returning fallback response")
            return _get_fallback_traditional_template()
        
        # Phase 7-3: 新しいレッスン形式関数を呼び出し（互換性維持）
        return _generator_service.generate_with_lessons(class_details, curriculum_settings)
        
    except Exception as e:
        logger.error(f"Error in generate_curriculum_with_ai: {str(e)}")
        return _get_fallback_traditional_template()


def generate_curriculum_csv(curriculum_data: Dict[str, Any]) -> str:
    """
    カリキュラムデータをCSV形式に変換する
    Phase 7-3: サービス層を使用してリファクタリング
    
    Args:
        curriculum_data: JSON形式のカリキュラムデータ

    Returns:
        str: CSV形式のカリキュラムデータ
    """
    try:
        if not _service_available:
            logger.error("AI services not available, returning empty CSV")
            return ""
        
        return _generator_service.generate_csv(curriculum_data)
        
    except Exception as e:
        logger.error(f"Error in generate_curriculum_csv: {str(e)}")
        return ""


def _get_fallback_lesson_template() -> Dict[str, Any]:
    """フォールバック用のレッスンテンプレート"""
    return {
        "lessons": [
            {
                "lesson_number": 1,
                "title": "オリエンテーション",
                "lesson_type": "lecture",
                "duration_minutes": 50,
                "description": "探究学習の概要説明、大テーマの理解",
                "learning_objectives": ["探究学習の意義を理解する"],
                "tasks": [
                    {
                        "task_number": 1,
                        "title": "探究テーマの理解",
                        "description": "大テーマについて調べ、自分の興味を明確にする"
                    }
                ]
            }
        ],
        "rubric_suggestion": [
            {
                "category": "問いの設定",
                "description": "探究の問いを設定する力",
                "levels": [
                    {"level": "S", "description": "独創的で深い問いを設定できる"},
                    {"level": "A", "description": "適切な問いを設定できる"},
                    {"level": "B", "description": "基本的な問いを設定できる"},
                    {"level": "C", "description": "問いの設定が不十分"},
                ],
            }
        ],
    }


def _get_fallback_traditional_template() -> Dict[str, Any]:
    """フォールバック用の従来テンプレート"""
    return {
        "phases": [
            {
                "phase": "準備期",
                "weeks": [
                    {
                        "week": "第1週",
                        "hours": 2,
                        "theme": "オリエンテーション",
                        "activities": "探究学習の概要説明、大テーマの理解",
                        "teacher_support": "探究学習の意義と進め方を説明",
                        "evaluation": "活動記録の確認",
                    }
                ],
            }
        ],
        "rubric_suggestion": [
            {
                "category": "問いの設定",
                "description": "探究の問いを設定する力",
                "levels": [
                    {"level": "S", "description": "独創的で深い問いを設定できる"},
                    {"level": "A", "description": "適切な問いを設定できる"},
                    {"level": "B", "description": "基本的な問いを設定できる"},
                    {"level": "C", "description": "問いの設定が不十分"},
                ],
            }
        ],
    }


# Phase 7-3: 追加のユーティリティ関数
def validate_api_availability() -> bool:
    """API利用可能性の確認"""
    if not _service_available:
        return False
    return _generator_service.validate_api_key()


def get_service_status() -> Dict[str, Any]:
    """サービス状態の取得"""
    return {
        "service_available": _service_available,
        "api_key_configured": validate_api_availability() if _service_available else False,
        "version": "Phase 7-3 Refactored"
    }