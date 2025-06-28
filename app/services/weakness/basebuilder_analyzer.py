"""
BaseBuilder Weakness Analyzer
=============================
BaseBuilder専用の弱点分析モジュール

責任:
- 語彙学習の弱点分析
- テキスト習熟度の評価
- BaseBuilder特有のパターン認識
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import statistics
from flask import current_app

from .severity_evaluator import Weakness


class BaseBuilderWeaknessAnalyzer:
    """BaseBuilder専用分析クラス"""
    
    def analyze(self, basebuilder_data: Dict[str, Any]) -> List[Weakness]:
        """
        BaseBuilderデータから弱点を分析
        
        Args:
            basebuilder_data: BaseBuilder関連データ
            
        Returns:
            list: 識別された弱点
        """
        try:
            weaknesses = []
            
            # 単語習熟度の分析
            word_weaknesses = self._analyze_word_proficiency(
                basebuilder_data.get('word_proficiencies', [])
            )
            weaknesses.extend(word_weaknesses)
            
            # カテゴリパフォーマンスの分析
            category_weaknesses = self._analyze_category_performance(
                basebuilder_data.get('category_performance', [])
            )
            weaknesses.extend(category_weaknesses)
            
            # 語彙学習パターンの分析
            pattern_weaknesses = self._analyze_vocabulary_patterns(
                basebuilder_data.get('word_proficiencies', [])
            )
            weaknesses.extend(pattern_weaknesses)
            
            # テキスト習熟度の分析（もしデータがあれば）
            if 'text_proficiencies' in basebuilder_data:
                text_weaknesses = self._analyze_text_proficiency(
                    basebuilder_data['text_proficiencies']
                )
                weaknesses.extend(text_weaknesses)
            
            current_app.logger.info(
                f"Analyzed BaseBuilder data: found {len(weaknesses)} weaknesses"
            )
            
            return weaknesses
            
        except Exception as e:
            current_app.logger.error(f"Error analyzing BaseBuilder data: {str(e)}")
            return []
    
    def _analyze_word_proficiency(self, word_proficiencies: List[Dict]) -> List[Weakness]:
        """単語習熟度から弱点を分析"""
        weaknesses = []
        
        if not word_proficiencies:
            return weaknesses
        
        # 習熟度レベル別に分類
        mastery_groups = defaultdict(list)
        for wp in word_proficiencies:
            mastery_groups[wp['mastery_level']].append(wp)
        
        # 低習熟度の単語が多い場合
        low_mastery_words = mastery_groups[1] + mastery_groups[2]
        total_words = len(word_proficiencies)
        
        if total_words > 0:
            low_mastery_ratio = len(low_mastery_words) / total_words
            
            if low_mastery_ratio > 0.4:  # 40%以上が低習熟度
                severity = min(low_mastery_ratio, 1.0)
                
                weakness = Weakness(
                    category='vocabulary',
                    subcategory='low_mastery_words',
                    description=f"{len(low_mastery_words)}個の単語が低習熟度です。基礎語彙の定着が必要です。",
                    severity=severity,
                    confidence=0.9,
                    evidence_count=len(low_mastery_words),
                    affected_areas=['vocabulary_foundation', 'reading_comprehension'],
                    trend='stable',
                    last_occurrence=datetime.now()
                )
                weaknesses.append(weakness)
        
        # 長期間見ていない単語の検出
        stale_words = self._find_stale_words(word_proficiencies)
        if len(stale_words) > 10:
            weakness = Weakness(
                category='vocabulary',
                subcategory='stale_words',
                description=f"{len(stale_words)}個の単語を長期間復習していません。",
                severity=0.6,
                confidence=0.8,
                evidence_count=len(stale_words),
                affected_areas=['retention', 'long_term_memory'],
                trend='declining',
                last_occurrence=datetime.now()
            )
            weaknesses.append(weakness)
        
        # 正答率が低い単語群の検出
        low_accuracy_words = self._find_low_accuracy_words(word_proficiencies)
        if low_accuracy_words:
            weakness = Weakness(
                category='vocabulary',
                subcategory='persistent_errors',
                description=f"{len(low_accuracy_words)}個の単語で繰り返しミスをしています。",
                severity=0.8,
                confidence=0.9,
                evidence_count=sum(w['view_count'] for w in low_accuracy_words),
                affected_areas=['accuracy', 'word_recognition'],
                trend='stable',
                last_occurrence=datetime.now()
            )
            weaknesses.append(weakness)
        
        return weaknesses
    
    def _analyze_category_performance(self, category_performance: List[Dict]) -> List[Weakness]:
        """カテゴリ別パフォーマンスから弱点を分析"""
        weaknesses = []
        
        for category in category_performance:
            if category['total_answers'] >= 10:  # 十分なデータがある場合
                accuracy = category['accuracy']
                
                if accuracy < 0.6:  # 60%未満の正答率
                    severity = 1.0 - accuracy
                    
                    weakness = Weakness(
                        category='basebuilder_category',
                        subcategory=f"category_{category['category_id']}",
                        description=f"{category['category_name']}の正答率が{accuracy:.1%}と低くなっています。",
                        severity=severity,
                        confidence=min(category['total_answers'] / 30, 1.0),
                        evidence_count=category['total_answers'],
                        affected_areas=['category_mastery', 'systematic_knowledge'],
                        trend=self._determine_category_trend(category),
                        last_occurrence=datetime.now()
                    )
                    weaknesses.append(weakness)
        
        return weaknesses
    
    def _analyze_vocabulary_patterns(self, word_proficiencies: List[Dict]) -> List[Weakness]:
        """語彙学習パターンから弱点を分析"""
        weaknesses = []
        
        if not word_proficiencies:
            return weaknesses
        
        # 学習効率の分析
        efficiency_issues = self._analyze_learning_efficiency(word_proficiencies)
        if efficiency_issues:
            weakness = Weakness(
                category='vocabulary_learning',
                subcategory='inefficient_learning',
                description=efficiency_issues['description'],
                severity=efficiency_issues['severity'],
                confidence=0.7,
                evidence_count=len(word_proficiencies),
                affected_areas=['learning_efficiency', 'time_management'],
                trend='stable',
                last_occurrence=datetime.now()
            )
            weaknesses.append(weakness)
        
        # 定着パターンの分析
        retention_issues = self._analyze_retention_patterns(word_proficiencies)
        if retention_issues:
            weakness = Weakness(
                category='vocabulary_learning',
                subcategory='retention_problem',
                description=retention_issues['description'],
                severity=retention_issues['severity'],
                confidence=0.8,
                evidence_count=retention_issues['evidence_count'],
                affected_areas=['memory', 'long_term_retention'],
                trend='declining',
                last_occurrence=datetime.now()
            )
            weaknesses.append(weakness)
        
        return weaknesses
    
    def _analyze_text_proficiency(self, text_proficiencies: List[Dict]) -> List[Weakness]:
        """テキスト習熟度から弱点を分析"""
        weaknesses = []
        
        # 未完了テキストの分析
        incomplete_texts = [t for t in text_proficiencies if t.get('completion_rate', 0) < 1.0]
        
        if len(incomplete_texts) > 5:
            avg_completion = statistics.mean([t.get('completion_rate', 0) for t in incomplete_texts])
            
            weakness = Weakness(
                category='text_learning',
                subcategory='incomplete_texts',
                description=f"{len(incomplete_texts)}個のテキストが未完了です（平均進捗: {avg_completion:.1%}）。",
                severity=0.7,
                confidence=0.9,
                evidence_count=len(incomplete_texts),
                affected_areas=['completion_rate', 'systematic_learning'],
                trend='stable',
                last_occurrence=datetime.now()
            )
            weaknesses.append(weakness)
        
        return weaknesses
    
    # ヘルパーメソッド
    
    def _find_stale_words(self, word_proficiencies: List[Dict]) -> List[Dict]:
        """長期間見ていない単語を検出"""
        stale_threshold = datetime.now() - timedelta(days=14)
        stale_words = []
        
        for wp in word_proficiencies:
            if wp.get('last_seen'):
                last_seen = wp['last_seen']
                if isinstance(last_seen, str):
                    last_seen = datetime.fromisoformat(last_seen)
                
                if last_seen < stale_threshold and wp['mastery_level'] < 4:
                    stale_words.append(wp)
        
        return stale_words
    
    def _find_low_accuracy_words(self, word_proficiencies: List[Dict]) -> List[Dict]:
        """正答率が低い単語を検出"""
        low_accuracy_words = []
        
        for wp in word_proficiencies:
            if wp['view_count'] >= 3:  # 3回以上見た単語
                accuracy = wp['correct_count'] / wp['view_count']
                if accuracy < 0.5:  # 50%未満の正答率
                    low_accuracy_words.append(wp)
        
        return low_accuracy_words
    
    def _determine_category_trend(self, category: Dict) -> str:
        """カテゴリのトレンドを判定"""
        # 実際の実装では時系列データが必要
        accuracy = category['accuracy']
        
        if accuracy < 0.4:
            return 'declining'
        elif accuracy > 0.7:
            return 'improving'
        else:
            return 'stable'
    
    def _analyze_learning_efficiency(self, word_proficiencies: List[Dict]) -> Optional[Dict]:
        """学習効率を分析"""
        if not word_proficiencies:
            return None
        
        # 見た回数に対する習熟度の効率を計算
        inefficient_words = []
        
        for wp in word_proficiencies:
            if wp['view_count'] > 5 and wp['mastery_level'] < 3:
                inefficient_words.append(wp)
        
        if len(inefficient_words) > len(word_proficiencies) * 0.2:  # 20%以上
            return {
                'description': f"{len(inefficient_words)}個の単語で学習効率が低下しています。学習方法の見直しが必要です。",
                'severity': 0.7
            }
        
        return None
    
    def _analyze_retention_patterns(self, word_proficiencies: List[Dict]) -> Optional[Dict]:
        """定着パターンを分析"""
        if not word_proficiencies:
            return None
        
        # 一度習得したが後退した単語を検出
        regressed_words = []
        
        for wp in word_proficiencies:
            # 見た回数が多いのに習熟度が低い = 定着していない
            if wp['view_count'] > 10 and wp['mastery_level'] < 3:
                if wp['correct_count'] / wp['view_count'] < 0.6:
                    regressed_words.append(wp)
        
        if regressed_words:
            return {
                'description': f"{len(regressed_words)}個の単語で定着に問題があります。間隔反復学習が必要です。",
                'severity': 0.8,
                'evidence_count': len(regressed_words)
            }
        
        return None