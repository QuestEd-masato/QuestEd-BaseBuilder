"""
弱点に基づく推薦エンジン
Phase6-A: 旧weakness_analyzer.pyから移行
"""

import logging
from typing import Any, Dict, List

from app.models import CurriculumUnit, ProblemCategory

logger = logging.getLogger(__name__)


class WeaknessRecommendationEngine:
    """弱点に基づく推薦エンジン"""

    def __init__(self, weakness_analyzer=None):
        # Phase6-A: weakness_analyzerは循環インポート回避のため遅延初期化
        self.weakness_analyzer = weakness_analyzer

    def generate_targeted_recommendations(
        self, student_id: int, max_recommendations: int = 5
    ) -> List[Dict[str, Any]]:
        """弱点に基づく対象推薦を生成"""
        try:
            # StudentWeaknessテーブルが存在しないため、空リストを使用
            weaknesses = []

            recommendations = []

            for weakness in weaknesses:
                # 弱点に対応する学習コンテンツを推薦
                content_recommendations = self._find_content_for_weakness(weakness)
                recommendations.extend(content_recommendations)

            return recommendations[:max_recommendations]

        except Exception as e:
            logger.error(f"対象推薦生成エラー: {str(e)}")
            return []

    def _find_content_for_weakness(
        self, weakness: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """弱点データ（辞書）に対応するコンテンツを検索"""
        recommendations = []

        try:
            if weakness.get("weakness_type") == "concept":
                # 概念理解のための基礎的な単元を推薦
                basic_units = (
                    CurriculumUnit.query.filter_by(
                        difficulty=1  # difficulty_level -> difficulty
                    )
                    .filter(CurriculumUnit.title.contains(weakness.get("category", "")))
                    .limit(2)
                    .all()
                )

                for unit in basic_units:
                    recommendations.append(
                        {
                            "type": "unit",
                            "item_id": unit.id,
                            "title": f"基礎復習: {unit.title}",
                            "description": f"{weakness.get('category', '不明')}の概念理解を深めるための基礎学習",
                            "weakness_id": weakness.get("id", 0),
                            "priority": weakness.get("severity_level", 1),
                        }
                    )

            elif weakness.get("weakness_type") == "knowledge":
                # 知識定着のための問題を推薦
                if weakness.get("subject_id"):
                    categories = (
                        ProblemCategory.query.filter_by(
                            subject_id=weakness.get("subject_id")
                        )
                        .limit(2)
                        .all()
                    )

                    for category in categories:
                        recommendations.append(
                            {
                                "type": "problem_set",
                                "item_id": category.id,
                                "title": f"知識定着: {category.name}",
                                "description": f"{weakness.get('category', '不明')}の知識を定着させるための問題演習",
                                "weakness_id": weakness.get("id", 0),
                                "priority": weakness.get("severity_level", 1),
                            }
                        )

                # BaseBuilder語彙学習の推薦
                if "語彙" in weakness.get("category", ""):
                    # 弱点カテゴリに対応するBaseBuilder問題を推薦
                    analysis_data = weakness.get("analysis_data", {})
                    category_name = analysis_data.get("category_name")

                    if category_name:
                        category = ProblemCategory.query.filter_by(
                            name=category_name
                        ).first()
                        if category:
                            recommendations.append(
                                {
                                    "type": "basebuilder_category",
                                    "item_id": category.id,
                                    "title": f"語彙強化: {category_name}",
                                    "description": f"{category_name}カテゴリの語彙を集中的に学習",
                                    "weakness_id": weakness.get("id", 0),
                                    "priority": weakness.get("severity_level", 1),
                                    "learning_mode": "vocabulary_focus",
                                }
                            )

        except Exception as e:
            logger.error(f"弱点対応コンテンツ検索エラー: {str(e)}")

        return recommendations

    def get_personalized_study_plan(
        self, student_id: int, target_weeks: int = 4
    ) -> Dict[str, Any]:
        """個人に最適化された学習計画を生成"""
        try:
            # Phase6-A: 簡略化された実装
            # 実際の弱点分析は新システムを使用
            recommendations = self.generate_targeted_recommendations(student_id)
            
            return {
                "student_id": student_id,
                "target_weeks": target_weeks,
                "total_recommendations": len(recommendations),
                "weekly_goals": recommendations[:target_weeks] if recommendations else [],
                "status": "generated"
            }

        except Exception as e:
            logger.error(f"個人学習計画生成エラー: {str(e)}")
            return {
                "student_id": student_id,
                "target_weeks": target_weeks,
                "total_recommendations": 0,
                "weekly_goals": [],
                "status": "error",
                "error_message": str(e)
            }