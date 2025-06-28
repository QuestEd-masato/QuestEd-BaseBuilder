"""
Weakness Recommendation Generator
=================================
推奨事項生成専門モジュール

責任:
- 弱点に基づく学習推奨事項の生成
- 具体的なアクションプランの作成
- 学習リソースの推奨
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from flask import current_app

from .severity_evaluator import Weakness


@dataclass
class Recommendation:
    """推奨事項データクラス"""
    id: str
    weakness_id: str
    title: str
    description: str
    action_type: str  # 'practice', 'review', 'method_change', 'resource'
    priority: str  # 'high', 'medium', 'low'
    estimated_time_minutes: int
    resources: List[Dict[str, str]]  # リソースのリスト
    prerequisites: List[str]  # 前提条件
    expected_outcome: str


class WeaknessRecommendationGenerator:
    """推奨事項生成クラス"""
    
    def __init__(self):
        self.recommendation_templates = self._load_recommendation_templates()
    
    def generate_recommendations(
        self, 
        weaknesses: List[Weakness],
        learning_data: Dict[str, Any]
    ) -> List[Recommendation]:
        """
        弱点に基づいて推奨事項を生成
        
        Args:
            weaknesses: 評価された弱点のリスト
            learning_data: 学習データ（コンテキスト用）
            
        Returns:
            list: 生成された推奨事項
        """
        try:
            recommendations = []
            
            for weakness in weaknesses:
                # 弱点タイプ別の推奨事項を生成
                if weakness.category == 'error_pattern':
                    recommendations.extend(
                        self._generate_error_pattern_recommendations(weakness)
                    )
                elif weakness.category == 'concept_understanding':
                    recommendations.extend(
                        self._generate_concept_recommendations(weakness)
                    )
                elif weakness.category == 'subject_category':
                    recommendations.extend(
                        self._generate_category_recommendations(weakness, learning_data)
                    )
                elif weakness.category == 'difficulty_progression':
                    recommendations.extend(
                        self._generate_difficulty_recommendations(weakness)
                    )
                elif weakness.category == 'learning_effectiveness':
                    recommendations.extend(
                        self._generate_effectiveness_recommendations(weakness)
                    )
            
            # 重複除去と優先順位付け
            recommendations = self._deduplicate_and_prioritize_recommendations(
                recommendations, weaknesses
            )
            
            current_app.logger.info(
                f"Generated {len(recommendations)} recommendations for {len(weaknesses)} weaknesses"
            )
            
            return recommendations
            
        except Exception as e:
            current_app.logger.error(f"Error generating recommendations: {str(e)}")
            return []
    
    def _generate_error_pattern_recommendations(self, weakness: Weakness) -> List[Recommendation]:
        """エラーパターンに対する推奨事項"""
        recommendations = []
        
        if weakness.subcategory == 'consecutive_error':
            recommendations.append(Recommendation(
                id=f"rec_{weakness.subcategory}_1",
                weakness_id=f"{weakness.category}:{weakness.subcategory}",
                title="エラー後の振り返り習慣の導入",
                description="間違えた後は必ず30秒の振り返りタイムを設けましょう。なぜ間違えたかを言語化することで、同じミスを防げます。",
                action_type="method_change",
                priority="high",
                estimated_time_minutes=5,
                resources=[
                    {"type": "guide", "title": "効果的な振り返り方法", "url": "#reflection-guide"}
                ],
                prerequisites=[],
                expected_outcome="連続エラーの50%削減"
            ))
            
            recommendations.append(Recommendation(
                id=f"rec_{weakness.subcategory}_2",
                weakness_id=f"{weakness.category}:{weakness.subcategory}",
                title="リカバリー問題セットの活用",
                description="エラー後に簡単な問題を1-2問解いて、自信を回復させてから次に進みましょう。",
                action_type="practice",
                priority="medium",
                estimated_time_minutes=10,
                resources=[
                    {"type": "problems", "title": "基礎復習問題セット", "url": "#basic-problems"}
                ],
                prerequisites=[],
                expected_outcome="学習継続率の向上"
            ))
        
        elif weakness.subcategory == 'rushed_answer':
            recommendations.append(Recommendation(
                id=f"rec_{weakness.subcategory}_1",
                weakness_id=f"{weakness.category}:{weakness.subcategory}",
                title="3秒ルールの導入",
                description="問題を読み終わったら、必ず3秒待ってから回答を始めましょう。この習慣が慌てミスを防ぎます。",
                action_type="method_change",
                priority="high",
                estimated_time_minutes=0,
                resources=[],
                prerequisites=[],
                expected_outcome="慌てミスの70%削減"
            ))
        
        elif weakness.subcategory == 'overthinking':
            recommendations.append(Recommendation(
                id=f"rec_{weakness.subcategory}_1",
                weakness_id=f"{weakness.category}:{weakness.subcategory}",
                title="制限時間付き練習の実施",
                description="1問あたり2-3分の制限時間を設けて練習しましょう。考えすぎを防ぎ、直感的な理解を促進します。",
                action_type="practice",
                priority="high",
                estimated_time_minutes=30,
                resources=[
                    {"type": "timer", "title": "学習タイマーツール", "url": "#timer-tool"}
                ],
                prerequisites=[],
                expected_outcome="回答時間の適正化"
            ))
        
        return recommendations
    
    def _generate_concept_recommendations(self, weakness: Weakness) -> List[Recommendation]:
        """概念理解の弱点に対する推奨事項"""
        recommendations = []
        
        concept = weakness.subcategory
        
        # 基礎からの復習
        recommendations.append(Recommendation(
            id=f"rec_concept_{concept}_1",
            weakness_id=f"{weakness.category}:{weakness.subcategory}",
            title=f"{concept}の基礎概念復習",
            description=f"{concept}の基本的な定義と原理から復習しましょう。土台をしっかり固めることが重要です。",
            action_type="review",
            priority="high",
            estimated_time_minutes=45,
            resources=[
                {"type": "textbook", "title": f"{concept}基礎テキスト", "url": f"#text-{concept}"},
                {"type": "video", "title": f"{concept}解説動画", "url": f"#video-{concept}"}
            ],
            prerequisites=[],
            expected_outcome=f"{concept}の基礎理解度80%達成"
        ))
        
        # 段階的練習
        recommendations.append(Recommendation(
            id=f"rec_concept_{concept}_2",
            weakness_id=f"{weakness.category}:{weakness.subcategory}",
            title=f"{concept}の段階的練習プログラム",
            description="易しい問題から始めて、徐々に難易度を上げていく練習プログラムです。",
            action_type="practice",
            priority="high",
            estimated_time_minutes=60,
            resources=[
                {"type": "problems", "title": f"{concept}練習問題集", "url": f"#problems-{concept}"}
            ],
            prerequisites=[f"rec_concept_{concept}_1"],
            expected_outcome="応用問題への対応力向上"
        ))
        
        return recommendations
    
    def _generate_category_recommendations(
        self, 
        weakness: Weakness,
        learning_data: Dict[str, Any]
    ) -> List[Recommendation]:
        """カテゴリ別弱点に対する推奨事項"""
        recommendations = []
        
        category_id = weakness.subcategory.replace('category_', '')
        
        # カテゴリ特化の学習パス
        recommendations.append(Recommendation(
            id=f"rec_category_{category_id}_1",
            weakness_id=f"{weakness.category}:{weakness.subcategory}",
            title=f"カテゴリ{category_id}集中学習パス",
            description="このカテゴリに特化した2週間の集中学習プログラムです。基礎から応用まで体系的に学習します。",
            action_type="practice",
            priority="high",
            estimated_time_minutes=30 * 14,  # 1日30分×14日
            resources=[
                {"type": "learning_path", "title": f"カテゴリ{category_id}マスタープラン", "url": f"#path-{category_id}"}
            ],
            prerequisites=[],
            expected_outcome="カテゴリ正答率70%以上達成"
        ))
        
        # 関連リソース
        recommendations.append(Recommendation(
            id=f"rec_category_{category_id}_2",
            weakness_id=f"{weakness.category}:{weakness.subcategory}",
            title="補助教材の活用",
            description="視覚的な理解を促進する補助教材を活用しましょう。",
            action_type="resource",
            priority="medium",
            estimated_time_minutes=20,
            resources=[
                {"type": "infographic", "title": "概念マップ", "url": f"#map-{category_id}"},
                {"type": "flashcards", "title": "暗記カード", "url": f"#cards-{category_id}"}
            ],
            prerequisites=[],
            expected_outcome="概念の定着率向上"
        ))
        
        return recommendations
    
    def _generate_difficulty_recommendations(self, weakness: Weakness) -> List[Recommendation]:
        """難易度進行の問題に対する推奨事項"""
        recommendations = []
        
        if weakness.subcategory == 'abnormal_gradient':
            recommendations.append(Recommendation(
                id="rec_diff_gradient_1",
                weakness_id=f"{weakness.category}:{weakness.subcategory}",
                title="難易度調整プログラム",
                description="現在のレベルに合わせて難易度を再調整します。無理のない進行で着実にステップアップしましょう。",
                action_type="method_change",
                priority="high",
                estimated_time_minutes=0,
                resources=[],
                prerequisites=[],
                expected_outcome="適切な難易度での学習継続"
            ))
        
        elif weakness.subcategory.startswith('level_'):
            level = weakness.subcategory.replace('level_', '')
            
            recommendations.append(Recommendation(
                id=f"rec_diff_level_{level}_1",
                weakness_id=f"{weakness.category}:{weakness.subcategory}",
                title=f"レベル{level}ブリッジプログラム",
                description=f"レベル{level}の問題に必要なスキルを段階的に習得するプログラムです。",
                action_type="practice",
                priority="high",
                estimated_time_minutes=120,
                resources=[
                    {"type": "problems", "title": f"レベル{level}準備問題集", "url": f"#prep-{level}"}
                ],
                prerequisites=[],
                expected_outcome=f"レベル{level}正答率60%以上"
            ))
        
        return recommendations
    
    def _generate_effectiveness_recommendations(self, weakness: Weakness) -> List[Recommendation]:
        """学習効果の問題に対する推奨事項"""
        recommendations = []
        
        if weakness.subcategory == 'declining_performance':
            recommendations.append(Recommendation(
                id="rec_eff_decline_1",
                weakness_id=f"{weakness.category}:{weakness.subcategory}",
                title="学習方法の見直し",
                description="現在の学習方法が合っていない可能性があります。新しいアプローチを試してみましょう。",
                action_type="method_change",
                priority="high",
                estimated_time_minutes=30,
                resources=[
                    {"type": "guide", "title": "効果的な学習方法ガイド", "url": "#study-guide"}
                ],
                prerequisites=[],
                expected_outcome="学習効果の改善"
            ))
            
            recommendations.append(Recommendation(
                id="rec_eff_decline_2",
                weakness_id=f"{weakness.category}:{weakness.subcategory}",
                title="モチベーション回復プログラム",
                description="小さな成功体験を積み重ねて、学習へのモチベーションを回復させます。",
                action_type="practice",
                priority="high",
                estimated_time_minutes=15,
                resources=[
                    {"type": "problems", "title": "達成感重視問題セット", "url": "#motivational-set"}
                ],
                prerequisites=[],
                expected_outcome="学習意欲の向上"
            ))
        
        elif weakness.subcategory == 'learning_plateau':
            recommendations.append(Recommendation(
                id="rec_eff_plateau_1",
                weakness_id=f"{weakness.category}:{weakness.subcategory}",
                title="チャレンジレベルの調整",
                description="現在の問題が簡単すぎる可能性があります。少し難しい問題にチャレンジしてみましょう。",
                action_type="practice",
                priority="high",
                estimated_time_minutes=45,
                resources=[
                    {"type": "problems", "title": "チャレンジ問題集", "url": "#challenge-set"}
                ],
                prerequisites=[],
                expected_outcome="学習曲線の再上昇"
            ))
            
            recommendations.append(Recommendation(
                id="rec_eff_plateau_2",
                weakness_id=f"{weakness.category}:{weakness.subcategory}",
                title="学習方法の多様化",
                description="異なる角度からアプローチすることで、停滞を打破できます。",
                action_type="method_change",
                priority="medium",
                estimated_time_minutes=30,
                resources=[
                    {"type": "guide", "title": "多様な学習アプローチ", "url": "#diverse-methods"}
                ],
                prerequisites=[],
                expected_outcome="新たな理解の獲得"
            ))
        
        return recommendations
    
    def _deduplicate_and_prioritize_recommendations(
        self,
        recommendations: List[Recommendation],
        weaknesses: List[Weakness]
    ) -> List[Recommendation]:
        """推奨事項の重複除去と優先順位付け"""
        # 重複除去
        unique_recommendations = {}
        for rec in recommendations:
            if rec.id not in unique_recommendations:
                unique_recommendations[rec.id] = rec
        
        # 弱点の重要度に基づいて優先順位を調整
        weakness_severity_map = {
            f"{w.category}:{w.subcategory}": w.severity * w.confidence 
            for w in weaknesses
        }
        
        # 優先順位でソート
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        sorted_recommendations = sorted(
            unique_recommendations.values(),
            key=lambda r: (
                priority_order.get(r.priority, 0),
                weakness_severity_map.get(r.weakness_id, 0)
            ),
            reverse=True
        )
        
        return sorted_recommendations[:10]  # 上位10件まで
    
    def _load_recommendation_templates(self) -> Dict:
        """推奨事項テンプレートをロード"""
        # 実際の実装では外部ファイルやDBから読み込む
        return {
            'error_patterns': {
                'consecutive_error': ['reflection', 'recovery'],
                'rushed_answer': ['pause_technique', 'mindfulness'],
                'overthinking': ['time_limit', 'intuition_training']
            },
            'concepts': {
                'default': ['review_basics', 'gradual_practice', 'visual_aids']
            }
        }