"""
Weakness Severity Evaluator
==========================
重要度評価専門モジュール

責任:
- 弱点の重要度評価
- 信頼度スコアの計算
- 優先順位付け
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from flask import current_app


@dataclass
class Weakness:
    """弱点データクラス"""
    category: str
    subcategory: str
    description: str
    severity: float  # 0.0-1.0
    confidence: float  # 0.0-1.0
    evidence_count: int
    affected_areas: List[str]
    trend: str  # 'improving', 'stable', 'declining'
    last_occurrence: datetime


class WeaknessSeverityEvaluator:
    """重要度評価クラス"""
    
    def __init__(self):
        self.severity_weights = {
            'accuracy_impact': 0.3,
            'frequency': 0.25,
            'recency': 0.2,
            'scope': 0.15,
            'trend': 0.1
        }
    
    def evaluate_weaknesses(
        self, 
        patterns: Dict[str, Any], 
        statistics: Dict[str, Any]
    ) -> List[Weakness]:
        """
        パターンと統計から弱点を評価
        
        Args:
            patterns: 識別されたパターン
            statistics: 計算された統計
            
        Returns:
            list: 評価された弱点のリスト
        """
        try:
            weaknesses = []
            
            # エラーパターンから弱点を抽出
            weaknesses.extend(
                self._evaluate_error_pattern_weaknesses(
                    patterns.get('error_patterns', {})
                )
            )
            
            # 概念パターンから弱点を抽出
            weaknesses.extend(
                self._evaluate_concept_weaknesses(
                    patterns.get('concept_patterns', {})
                )
            )
            
            # カテゴリ統計から弱点を抽出
            weaknesses.extend(
                self._evaluate_category_weaknesses(
                    statistics.get('category_statistics', {})
                )
            )
            
            # 難易度パターンから弱点を抽出
            weaknesses.extend(
                self._evaluate_difficulty_weaknesses(
                    patterns.get('difficulty_patterns', {}),
                    statistics.get('difficulty_statistics', {})
                )
            )
            
            # 学習曲線から弱点を抽出
            weaknesses.extend(
                self._evaluate_learning_curve_weaknesses(
                    patterns.get('learning_curve_patterns', {})
                )
            )
            
            # 重複を除去し、優先順位付け
            weaknesses = self._deduplicate_and_prioritize(weaknesses)
            
            current_app.logger.info(f"Evaluated {len(weaknesses)} weaknesses")
            
            return weaknesses
            
        except Exception as e:
            current_app.logger.error(f"Error evaluating weaknesses: {str(e)}")
            return []
    
    def _evaluate_error_pattern_weaknesses(self, error_patterns: Dict) -> List[Weakness]:
        """エラーパターンから弱点を評価"""
        weaknesses = []
        
        for pattern in error_patterns.get('common_patterns', []):
            if pattern['frequency'] >= 5:  # 5回以上発生
                severity = self._calculate_error_severity(pattern)
                confidence = min(pattern['frequency'] / 10, 1.0)  # 頻度に基づく信頼度
                
                weakness = Weakness(
                    category='error_pattern',
                    subcategory=pattern['type'],
                    description=self._get_error_pattern_description(pattern['type']),
                    severity=severity,
                    confidence=confidence,
                    evidence_count=pattern['frequency'],
                    affected_areas=self._identify_affected_areas(pattern),
                    trend='stable',  # TODO: トレンド分析の実装
                    last_occurrence=datetime.now()
                )
                
                weaknesses.append(weakness)
        
        # 連続エラーパターン
        if error_patterns.get('avg_error_streak', 0) > 3:
            weaknesses.append(Weakness(
                category='persistence',
                subcategory='consecutive_errors',
                description='連続してエラーが発生する傾向があります',
                severity=min(error_patterns['avg_error_streak'] / 5, 1.0),
                confidence=0.8,
                evidence_count=error_patterns.get('max_consecutive_errors', 0),
                affected_areas=['concentration', 'recovery'],
                trend='stable',
                last_occurrence=datetime.now()
            ))
        
        return weaknesses
    
    def _evaluate_concept_weaknesses(self, concept_patterns: Dict) -> List[Weakness]:
        """概念理解の弱点を評価"""
        weaknesses = []
        
        for weak_concept in concept_patterns.get('weak_concepts', []):
            severity = weak_concept['error_rate']
            confidence = min(weak_concept['occurrences'] / 10, 1.0)
            
            weakness = Weakness(
                category='concept_understanding',
                subcategory=weak_concept['concept'],
                description=f"{weak_concept['concept']}の理解に課題があります",
                severity=severity,
                confidence=confidence,
                evidence_count=weak_concept['occurrences'],
                affected_areas=self._get_concept_affected_areas(weak_concept['concept']),
                trend='stable',
                last_occurrence=datetime.now()
            )
            
            weaknesses.append(weakness)
        
        return weaknesses
    
    def _evaluate_category_weaknesses(self, category_statistics: Dict) -> List[Weakness]:
        """カテゴリ別の弱点を評価"""
        weaknesses = []
        
        for cat_id, stats in category_statistics.items():
            if stats['performance_level'] in ['poor', 'below_average']:
                severity = 1.0 - stats['accuracy_rate']
                confidence = min(stats['total_attempts'] / 20, 1.0)
                
                weakness = Weakness(
                    category='subject_category',
                    subcategory=f'category_{cat_id}',
                    description=f"カテゴリ{cat_id}の問題に苦手意識があります",
                    severity=severity,
                    confidence=confidence,
                    evidence_count=stats['total_attempts'],
                    affected_areas=['category_mastery'],
                    trend=self._determine_trend(cat_id, stats),
                    last_occurrence=datetime.now()
                )
                
                weaknesses.append(weakness)
        
        return weaknesses
    
    def _evaluate_difficulty_weaknesses(
        self, 
        difficulty_patterns: Dict,
        difficulty_statistics: Dict
    ) -> List[Weakness]:
        """難易度関連の弱点を評価"""
        weaknesses = []
        
        # 難易度進行の異常
        if not difficulty_patterns.get('shows_normal_progression', True):
            deviation = difficulty_patterns.get('gradient_deviation', 0)
            
            weakness = Weakness(
                category='difficulty_progression',
                subcategory='abnormal_gradient',
                description='難易度の進行に不自然なパターンが見られます',
                severity=min(deviation, 1.0),
                confidence=0.7,
                evidence_count=len(difficulty_statistics),
                affected_areas=['skill_development', 'confidence'],
                trend='stable',
                last_occurrence=datetime.now()
            )
            
            weaknesses.append(weakness)
        
        # 特定難易度での苦戦
        for level, stats in difficulty_statistics.items():
            if stats['mastery_status'] == 'needs_practice' and stats['total_attempts'] >= 10:
                severity = 1.0 - stats['accuracy_rate']
                
                weakness = Weakness(
                    category='difficulty_level',
                    subcategory=f'level_{level}',
                    description=f"難易度{level}の問題で苦戦しています",
                    severity=severity,
                    confidence=0.8,
                    evidence_count=stats['total_attempts'],
                    affected_areas=['problem_solving', 'advanced_skills'],
                    trend='stable',
                    last_occurrence=datetime.now()
                )
                
                weaknesses.append(weakness)
        
        return weaknesses
    
    def _evaluate_learning_curve_weaknesses(self, learning_curve_patterns: Dict) -> List[Weakness]:
        """学習曲線から弱点を評価"""
        weaknesses = []
        
        curve_type = learning_curve_patterns.get('curve_type', '')
        
        if curve_type == 'declining':
            weakness = Weakness(
                category='learning_effectiveness',
                subcategory='declining_performance',
                description='学習効果が低下傾向にあります',
                severity=0.8,
                confidence=0.7,
                evidence_count=len(learning_curve_patterns.get('weekly_accuracies', [])),
                affected_areas=['motivation', 'retention'],
                trend='declining',
                last_occurrence=datetime.now()
            )
            weaknesses.append(weakness)
        
        elif curve_type == 'plateau' and learning_curve_patterns.get('plateau_detected', False):
            weakness = Weakness(
                category='learning_effectiveness',
                subcategory='learning_plateau',
                description='学習が停滞期に入っています',
                severity=0.6,
                confidence=0.8,
                evidence_count=3,  # プラトー検出には最低3週間必要
                affected_areas=['progress', 'challenge_level'],
                trend='stable',
                last_occurrence=datetime.now()
            )
            weaknesses.append(weakness)
        
        return weaknesses
    
    def _calculate_error_severity(self, pattern: Dict) -> float:
        """エラーパターンの重要度を計算"""
        base_severity = 0.5
        
        # エラータイプによる調整
        error_type = pattern['type']
        if error_type == 'consecutive_error':
            base_severity += 0.2
        elif error_type == 'rushed_answer':
            base_severity += 0.1
        elif error_type == 'overthinking':
            base_severity += 0.15
        
        # 頻度による調整
        frequency_factor = min(pattern['frequency'] / 20, 0.3)
        
        return min(base_severity + frequency_factor, 1.0)
    
    def _get_error_pattern_description(self, error_type: str) -> str:
        """エラーパターンの説明を取得"""
        descriptions = {
            'consecutive_error': '連続してミスをする傾向があります',
            'rushed_answer': '急いで回答してミスをする傾向があります',
            'overthinking': '考えすぎて間違える傾向があります',
            'high_difficulty_error': '高難度問題でミスが多発しています',
            'general_error': '一般的なミスが頻発しています'
        }
        
        return descriptions.get(error_type, 'エラーパターンが検出されました')
    
    def _identify_affected_areas(self, pattern: Dict) -> List[str]:
        """影響を受ける領域を特定"""
        error_type = pattern['type']
        
        area_mapping = {
            'consecutive_error': ['concentration', 'resilience'],
            'rushed_answer': ['time_management', 'careful_thinking'],
            'overthinking': ['confidence', 'decision_making'],
            'high_difficulty_error': ['advanced_skills', 'problem_solving'],
            'general_error': ['basic_understanding', 'attention']
        }
        
        return area_mapping.get(error_type, ['general_performance'])
    
    def _get_concept_affected_areas(self, concept: str) -> List[str]:
        """概念に関連する影響領域を取得"""
        concept_area_mapping = {
            '計算': ['mathematical_thinking', 'accuracy'],
            '文法': ['language_structure', 'expression'],
            '単語': ['vocabulary', 'comprehension'],
            '理解': ['reading_comprehension', 'analysis'],
            '応用': ['problem_solving', 'creativity'],
            '分析': ['critical_thinking', 'logic']
        }
        
        return concept_area_mapping.get(concept, ['general_knowledge'])
    
    def _determine_trend(self, category_id: Any, stats: Dict) -> str:
        """トレンドを判定（簡易版）"""
        # TODO: 実際には時系列データから判定する必要がある
        accuracy = stats['accuracy_rate']
        
        if accuracy < 0.5:
            return 'declining'
        elif accuracy > 0.8:
            return 'improving'
        else:
            return 'stable'
    
    def _deduplicate_and_prioritize(self, weaknesses: List[Weakness]) -> List[Weakness]:
        """重複を除去し優先順位付け"""
        # 重複除去（カテゴリとサブカテゴリの組み合わせでユニーク化）
        unique_weaknesses = {}
        
        for weakness in weaknesses:
            key = f"{weakness.category}:{weakness.subcategory}"
            if key not in unique_weaknesses or weakness.severity > unique_weaknesses[key].severity:
                unique_weaknesses[key] = weakness
        
        # 優先順位付け（重要度 × 信頼度でソート）
        prioritized = sorted(
            unique_weaknesses.values(),
            key=lambda w: w.severity * w.confidence,
            reverse=True
        )
        
        return prioritized[:20]  # 上位20件まで