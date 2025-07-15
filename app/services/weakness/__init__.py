"""
Weakness Analysis Services
=========================
Phase 4.2: God Class分解実装

元のWeaknessAnalyzer (1,194行) を以下のモジュールに分割:
- data_collector.py: データ収集専門
- statistics_calculator.py: 統計計算専門
- pattern_analyzer.py: パターン認識専門
- severity_evaluator.py: 重要度評価専門
- recommendation_generator.py: 推奨事項生成専門
- persistence_service.py: データ永続化専門
- basebuilder_analyzer.py: BaseBuilder専用分析

各モジュールは単一責任の原則に従い、テスト可能な設計を実現。
"""

from .basebuilder_analyzer import BaseBuilderWeaknessAnalyzer
from .data_collector import WeaknessDataCollector
from .pattern_analyzer import WeaknessPatternAnalyzer
from .persistence_service import WeaknessPersistenceService
from .recommendation_generator import WeaknessRecommendationGenerator
from .severity_evaluator import WeaknessSeverityEvaluator
from .statistics_calculator import WeaknessStatisticsCalculator


# 統合ファサードクラス
class WeaknessAnalysisService:
    """
    弱点分析サービスのファサード

    各専門サービスを統合し、シンプルなインターフェースを提供
    """

    def __init__(self):
        self.data_collector = WeaknessDataCollector()
        self.statistics_calculator = WeaknessStatisticsCalculator()
        self.pattern_analyzer = WeaknessPatternAnalyzer()
        self.severity_evaluator = WeaknessSeverityEvaluator()
        self.recommendation_generator = WeaknessRecommendationGenerator()
        self.persistence_service = WeaknessPersistenceService()
        self.basebuilder_analyzer = BaseBuilderWeaknessAnalyzer()

    def analyze_student_weaknesses(self, student_id: int, force_refresh: bool = False):
        """
        学生の弱点を分析

        Args:
            student_id: 学生ID
            force_refresh: キャッシュを無視して再分析

        Returns:
            dict: 弱点分析結果
        """
        # キャッシュチェック
        if not force_refresh:
            cached_result = self.persistence_service.get_recent_analysis(student_id)
            if cached_result:
                return cached_result

        # データ収集
        learning_data = self.data_collector.collect_comprehensive_learning_data(
            student_id
        )

        # 統計分析
        statistics = self.statistics_calculator.calculate_statistics(learning_data)

        # パターン認識
        patterns = self.pattern_analyzer.analyze_patterns(learning_data, statistics)

        # 重要度評価
        weaknesses = self.severity_evaluator.evaluate_weaknesses(patterns, statistics)

        # 推奨事項生成
        recommendations = self.recommendation_generator.generate_recommendations(
            weaknesses, learning_data
        )

        # BaseBuilder特有の分析
        if learning_data.get("basebuilder_data"):
            basebuilder_weaknesses = self.basebuilder_analyzer.analyze(
                learning_data["basebuilder_data"]
            )
            weaknesses.extend(basebuilder_weaknesses)

        # 結果を保存
        result = {
            "student_id": student_id,
            "weaknesses": weaknesses,
            "recommendations": recommendations,
            "analysis_date": datetime.now(),
        }

        self.persistence_service.save_analysis(result)

        return result


# 後方互換性のためのエイリアス
WeaknessAnalyzer = WeaknessAnalysisService

__all__ = [
    "WeaknessDataCollector",
    "WeaknessStatisticsCalculator",
    "WeaknessPatternAnalyzer",
    "WeaknessSeverityEvaluator",
    "WeaknessRecommendationGenerator",
    "WeaknessPersistenceService",
    "BaseBuilderWeaknessAnalyzer",
    "WeaknessAnalysisService",
    "WeaknessAnalyzer",  # 後方互換性
]
