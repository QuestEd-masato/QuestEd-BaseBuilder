"""
Progress Service Module
======================
Phase 4.2: UnifiedProgressService (1,260行) の分解実装

元の巨大サービスを以下のモジュールに分割:
- self_paced_service.py: 自主学習進捗管理
- basebuilder_service.py: BaseBuilder進捗管理  
- inquiry_service.py: 探究学習進捗管理
- activity_tracker.py: 活動追跡とエンゲージメント
- analytics_service.py: 学習分析とパターン認識
- aggregator.py: 全体統合とファサード
- metrics_calculator.py: 指標計算専門

各モジュールは単一責任の原則に従い、テスト可能な設計を実現。
"""

from .activity_tracker import ActivityTrackingService
from .aggregator import ProgressAggregator
from .analytics_service import LearningAnalyticsService
from .basebuilder_service import BaseBuilderProgressService
from .inquiry_service import InquiryProgressService
from .metrics_calculator import StudyMetricsCalculator
from .self_paced_service import SelfPacedProgressService


# 統合ファサードクラス（後方互換性）
class UnifiedProgressService:
    """
    統合進捗サービスのファサード

    各専門サービスを統合し、元のインターフェースとの互換性を維持
    """

    def __init__(self):
        self.aggregator = ProgressAggregator()

    def get_comprehensive_progress(self, student_id: int) -> dict:
        """
        包括的な進捗情報を取得

        Args:
            student_id: 学生ID

        Returns:
            dict: 統合された進捗情報
        """
        return self.aggregator.get_comprehensive_progress(student_id)


__all__ = [
    "SelfPacedProgressService",
    "BaseBuilderProgressService",
    "InquiryProgressService",
    "ActivityTrackingService",
    "LearningAnalyticsService",
    "StudyMetricsCalculator",
    "ProgressAggregator",
    "UnifiedProgressService",  # 後方互換性
]
