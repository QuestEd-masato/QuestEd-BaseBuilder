# サービス層の基底クラスとユーティリティ

from .ai_recommender import AIRecommendationEngine, RecommendationAnalytics
from app.core.base_service import BaseService
from .base_service import CRUDService
# Phase6-B: Dashboard関連サービス
from .dashboard_service import DashboardService
from .dashboard_renderer import DashboardRendererService
from .student_info_service import StudentInfoService
# Phase6-C: Unit Management関連サービス（Phase8Aで統合済み、削除予定）
# Phase7-2: Teacher Task Management関連サービス
from .teacher_task_statistics_service import TeacherTaskStatisticsService
from .teacher_progress_service import TeacherProgressService
from .teacher_approval_service import TeacherApprovalService
from .pattern_analyzer import (
    DifficultyPreferenceAnalyzer,
    LearningStyleAnalyzer,
    PatternAnalyzerService,
    SubjectStrengthAnalyzer,
    TimePreferenceAnalyzer,
)
# from .spaced_repetition import (
#     AdaptiveDifficultyAdjuster,
#     SpacedRepetitionEngine,
#     SuperMemoAlgorithm,
# )  # Phase9-3: BaseBuilder統合により削除
from .user_service import UserService
# Phase6-A: 新しい分割済みWeaknessAnalyzer使用
from .weakness import WeaknessAnalyzer, WeaknessRecommendationEngine
# Phase8C: Curriculum Management関連サービス
from .curriculum import (
    CurriculumDataService,
    CurriculumValidationService,
    CurriculumAIService,
    CurriculumImportExportService,
    # LessonManagementService,  # 削除: 新システム使用
    ThemeManagementService,
    TeacherCurriculumUnitService
)

__all__ = [
    "BaseService",
    "CRUDService",
    "UserService",
    # Phase6-B: Dashboard関連サービス
    "DashboardService",
    "DashboardRendererService", 
    "StudentInfoService",
    # Phase6-C: Unit Management関連サービス（Phase8Aで統合済み、削除済み）
    # Phase7-2: Teacher Task Management関連サービス
    "TeacherTaskStatisticsService",
    "TeacherProgressService", 
    "TeacherApprovalService",
    "PatternAnalyzerService",
    "TimePreferenceAnalyzer",
    "DifficultyPreferenceAnalyzer",
    "SubjectStrengthAnalyzer",
    "LearningStyleAnalyzer",
    "AIRecommendationEngine",
    "RecommendationAnalytics",
    "WeaknessAnalyzer",
    "WeaknessRecommendationEngine",
    # "SpacedRepetitionEngine",
    # "SuperMemoAlgorithm", 
    # "AdaptiveDifficultyAdjuster",  # Phase9-3: BaseBuilder統合により削除
    # Phase8C: Curriculum Management関連サービス
    "CurriculumDataService",
    "CurriculumValidationService",
    "CurriculumAIService",
    "CurriculumImportExportService",
    # "LessonManagementService",  # 削除: 新システム使用
    "ThemeManagementService",
    "TeacherCurriculumUnitService",
]
