# サービス層の基底クラスとユーティリティ

from .ai_recommender import AIRecommendationEngine, RecommendationAnalytics
from .base_service import BaseService, CRUDService
from .pattern_analyzer import (
    DifficultyPreferenceAnalyzer,
    LearningStyleAnalyzer,
    PatternAnalyzerService,
    SubjectStrengthAnalyzer,
    TimePreferenceAnalyzer,
)
from .spaced_repetition import (
    AdaptiveDifficultyAdjuster,
    SpacedRepetitionEngine,
    SuperMemoAlgorithm,
)
from .user_service import UserService
from .weakness_analyzer import WeaknessAnalyzer, WeaknessRecommendationEngine

__all__ = [
    "BaseService",
    "CRUDService",
    "UserService",
    "PatternAnalyzerService",
    "TimePreferenceAnalyzer",
    "DifficultyPreferenceAnalyzer",
    "SubjectStrengthAnalyzer",
    "LearningStyleAnalyzer",
    "AIRecommendationEngine",
    "RecommendationAnalytics",
    "WeaknessAnalyzer",
    "WeaknessRecommendationEngine",
    "SpacedRepetitionEngine",
    "SuperMemoAlgorithm",
    "AdaptiveDifficultyAdjuster",
]
