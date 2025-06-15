"""
QuestEd 学習弱点分析システム

このモジュールは、学生の学習データを多角的に分析し、弱点を特定して
改善策を提案する包括的な分析システムを提供します。

主な分析項目:
1. 概念理解の弱点（理論的知識の理解度）
2. スキル習得の弱点（実技・応用能力）
3. 知識定着の弱点（記憶・定着度）
4. 応用力の弱点（複合問題解決能力）
5. 学習パターンの弱点（学習方法・習慣）
6. BaseBuilder特有の弱点（語彙、記憶法、依存性など）

分析データソース:
- 自由進度学習の単元進捗
- BaseBuilder語彙学習データ
- 熟練度記録と正答率
- 学習時間パターン
- エラー頻度と種類

新規開発者向けガイド:
1. 分析には最低3回以上の学習試行が必要
2. BaseBuilderとの統合により詳細な語彙分析が可能
3. 弱点は重要度（1-5）で優先順位付けされる
4. 推薦アクションは実行可能な具体的内容
5. 分析結果は24時間キャッシュされる

Author: QuestEd Development Team
Created: 2025
Last Modified: 2025-01-15
Version: 2.0.0
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from collections import defaultdict, Counter
from sqlalchemy import and_, or_, desc, func, text
from flask import current_app

from app.models import (
    User, StudentWeakness, Subject, ProficiencyRecord, BasicKnowledgeItem,
    ProblemCategory, StudentUnitSelection, CurriculumUnit, ReviewSet, ReviewSetItem,
    WordProficiency, AnswerRecord, TextSet, LearningPath, PathAssignment
)
from app.utils.exceptions import WeaknessAnalysisError, InsufficientDataError
from extensions import db

logger = logging.getLogger(__name__)


class WeaknessAnalyzer:
    """
    学習弱点分析システム - 学生の学習データを分析して弱点を特定
    
    このクラスは、複数のデータソースから学習状況を総合的に分析し、
    学生の具体的な弱点を特定して改善策を提案します。
    
    分析アルゴリズム:
    1. データ収集: 90日間の学習履歴を収集
    2. 統計分析: 正答率、学習時間、進捗率を計算
    3. パターン認識: 学習傾向と問題パターンを識別
    4. 弱点特定: 閾値を下回る項目を弱点として識別
    5. 優先度付け: 重要度と改善可能性で順位付け
    6. 推薦生成: 具体的で実行可能な改善策を提案
    
    閾値設定の根拠:
    - 最小試行回数(3回): 統計的有意性の確保
    - 弱点正答率(70%): 教育学的に「習得」の基準
    - 信頼度(60%): データの信頼性確保
    """
    
    def __init__(self):
        """
        弱点分析システムの初期化
        
        分析パラメータの設定:
        - 最小試行回数: 統計的に意味のある分析に必要な最小データ数
        - 弱点正答率閾値: この値を下回ると弱点と判定
        - 信頼度閾値: 分析結果の信頼性を確保する最小値
        """
        # 分析パラメータ（教育学的根拠に基づく設定）
        self.min_attempts_threshold = 3  # 最小試行回数：統計的有意性
        self.weak_accuracy_threshold = 0.7  # 弱点正答率：教育学的習得基準
        self.confidence_threshold = 0.6  # 信頼度：データ品質確保
    
    def analyze_student_weaknesses(
        self, 
        student_id: int, 
        force_update: bool = False
    ) -> List[Dict[str, Any]]:
        """
        学生の弱点を総合的に分析
        
        Args:
            student_id: 学生ID
            force_update: 強制更新フラグ
            
        Returns:
            弱点分析結果のリスト
        """
        try:
            student = User.query.get(student_id)
            if not student or student.role != 'student':
                raise WeaknessAnalysisError("有効な学生が見つかりません")
            
            # 既存の分析結果をチェック
            if not force_update:
                recent_analysis = self._get_recent_analysis(student_id)
                if recent_analysis:
                    logger.info(f"学生 {student_id} の最近の弱点分析を返却")
                    return recent_analysis
            
            # 学習データを収集
            learning_data = self._collect_comprehensive_learning_data(student_id)
            
            if not learning_data:
                raise InsufficientDataError("分析に十分なデータがありません")
            
            # 各種弱点分析を実行
            weaknesses = []
            
            # 1. 概念理解の弱点分析
            concept_weaknesses = self._analyze_concept_weaknesses(student_id, learning_data)
            weaknesses.extend(concept_weaknesses)
            
            # 2. スキル習得の弱点分析
            skill_weaknesses = self._analyze_skill_weaknesses(student_id, learning_data)
            weaknesses.extend(skill_weaknesses)
            
            # 3. 知識定着の弱点分析
            knowledge_weaknesses = self._analyze_knowledge_weaknesses(student_id, learning_data)
            weaknesses.extend(knowledge_weaknesses)
            
            # 4. 応用力の弱点分析
            application_weaknesses = self._analyze_application_weaknesses(student_id, learning_data)
            weaknesses.extend(application_weaknesses)
            
            # 5. 学習パターンの弱点分析
            pattern_weaknesses = self._analyze_learning_pattern_weaknesses(student_id, learning_data)
            weaknesses.extend(pattern_weaknesses)
            
            # 6. BaseBuilder特有の弱点分析
            basebuilder_weaknesses = self._analyze_basebuilder_specific_weaknesses(student_id, learning_data)
            weaknesses.extend(basebuilder_weaknesses)
            
            # 重複排除と優先度付け
            unique_weaknesses = self._deduplicate_and_prioritize(weaknesses)
            
            # データベースに保存
            self._save_weakness_analysis(student_id, unique_weaknesses)
            
            return unique_weaknesses
            
        except Exception as e:
            logger.error(f"弱点分析エラー (学生ID: {student_id}): {str(e)}")
            raise WeaknessAnalysisError(f"弱点分析中にエラーが発生しました: {str(e)}")
    
    def _get_recent_analysis(self, student_id: int, hours: int = 24) -> Optional[List[Dict[str, Any]]]:
        """最近の弱点分析結果を取得"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent_weaknesses = StudentWeakness.query.filter(
            and_(
                StudentWeakness.student_id == student_id,
                StudentWeakness.updated_at >= cutoff_time,
                StudentWeakness.is_active == True
            )
        ).order_by(desc(StudentWeakness.severity_level)).all()
        
        if recent_weaknesses:
            return [self._weakness_to_dict(weakness) for weakness in recent_weaknesses]
        return None
    
    def _collect_comprehensive_learning_data(self, student_id: int) -> Dict[str, Any]:
        """包括的な学習データを収集（BaseBuilderデータを含む）"""
        data = {
            'proficiency_records': [],
            'unit_selections': [],
            'problem_attempts': [],
            'word_proficiency': [],
            'answer_records': [],
            'learning_paths': [],
            'categories_performance': {},
            'subjects_performance': {},
            'difficulty_trends': {},
            'time_patterns': {},
            'error_patterns': [],
            'basebuilder_stats': {}
        }
        
        try:
            # 熟練度記録の収集（過去90日）
            recent_cutoff = datetime.utcnow() - timedelta(days=90)
            
            proficiency_records = ProficiencyRecord.query.filter(
                and_(
                    ProficiencyRecord.student_id == student_id,
                    ProficiencyRecord.last_updated >= recent_cutoff
                )
            ).order_by(desc(ProficiencyRecord.last_updated)).all()
            
            for record in proficiency_records:
                try:
                    data['proficiency_records'].append({
                        'category_id': record.category_id,
                        'category_name': record.category.name if record.category else 'Unknown',
                        'subject_name': record.category.subject.name if (record.category and hasattr(record.category, 'subject') and record.category.subject) else 'Unknown',
                        'mastery_level': getattr(record, 'mastery_level', 0),
                        'total_attempted': getattr(record, 'total_attempted', 0),
                        'total_correct': getattr(record, 'total_correct', 0),
                        'accuracy_rate': getattr(record, 'accuracy_rate', 0.0),
                        'streak_count': getattr(record, 'streak_count', 0),
                        'last_updated': record.last_updated
                    })
                except Exception as e:
                    logger.warning(f"熟練度記録処理エラー (ID: {record.id}): {str(e)}")
            
            # BaseBuilder単語レベル熟練度の収集
            word_proficiencies = WordProficiency.query.filter(
                and_(
                    WordProficiency.student_id == student_id,
                    WordProficiency.last_updated >= recent_cutoff
                )
            ).order_by(desc(WordProficiency.last_updated)).all()
            
            for wp in word_proficiencies:
                try:
                    data['word_proficiency'].append({
                        'problem_id': wp.problem_id,
                        'word_title': wp.problem.title if wp.problem else 'Unknown',
                        'category_id': wp.problem.category_id if wp.problem else None,
                        'category_name': wp.problem.category.name if (wp.problem and wp.problem.category) else 'Unknown',
                        'level': getattr(wp, 'level', 0),
                        'difficulty': wp.problem.difficulty if wp.problem else 2,
                        'last_updated': wp.last_updated,
                        'review_date': wp.review_date,
                        'repetition_number': getattr(wp, 'repetition_number', 0)
                    })
                except Exception as e:
                    logger.warning(f"単語熟練度記録処理エラー (ID: {wp.id}): {str(e)}")
            
            # BaseBuilder解答記録の収集（より詳細な分析用）
            answer_records = AnswerRecord.query.filter(
                and_(
                    AnswerRecord.student_id == student_id,
                    AnswerRecord.answered_at >= recent_cutoff
                )
            ).order_by(desc(AnswerRecord.answered_at)).limit(200).all()
            
            for answer in answer_records:
                try:
                    data['answer_records'].append({
                        'problem_id': answer.problem_id,
                        'category_id': answer.problem.category_id if answer.problem else None,
                        'category_name': answer.problem.category.name if (answer.problem and answer.problem.category) else 'Unknown',
                        'is_correct': getattr(answer, 'is_correct', False),
                        'answer_time_seconds': getattr(answer, 'answer_time_seconds', 0),
                        'hint_used': getattr(answer, 'hint_used', False),
                        'difficulty': answer.problem.difficulty if answer.problem else 2,
                        'answered_at': answer.answered_at
                    })
                except Exception as e:
                    logger.warning(f"解答記録処理エラー (ID: {answer.id}): {str(e)}")
            
            # BaseBuilder学習パス進捗
            path_assignments = PathAssignment.query.filter_by(
                student_id=student_id
            ).order_by(desc(PathAssignment.assigned_at)).all()
            
            for assignment in path_assignments:
                data['learning_paths'].append({
                    'path_id': assignment.path_id,
                    'path_title': assignment.path.title if assignment.path else 'Unknown',
                    'progress': assignment.progress,
                    'completed': assignment.completed,
                    'due_date': assignment.due_date,
                    'assigned_at': assignment.assigned_at
                })
            
            # BaseBuilder統計データの集計
            data['basebuilder_stats'] = self._analyze_basebuilder_performance(
                data['word_proficiency'], data['answer_records']
            )
            
            # 単元選択履歴の収集
            unit_selections = StudentUnitSelection.query.filter_by(
                student_id=student_id
            ).order_by(desc(StudentUnitSelection.last_activity_at)).all()
            
            for selection in unit_selections:
                if selection.unit:
                    data['unit_selections'].append({
                        'unit_id': selection.unit_id,
                        'unit_title': selection.unit.title,
                        'difficulty_level': selection.unit.difficulty_level,
                        'status': selection.status,
                        'progress_percentage': float(selection.progress_percentage) if selection.progress_percentage else 0,
                        'total_items': selection.total_items,
                        'completed_items': selection.completed_items,
                        'correct_items': selection.correct_items,
                        'study_time_minutes': selection.study_time_minutes,
                        'last_activity_at': selection.last_activity_at
                    })
            
            # カテゴリ別パフォーマンス分析
            data['categories_performance'] = self._analyze_category_performance(proficiency_records)
            
            # 科目別パフォーマンス分析
            data['subjects_performance'] = self._analyze_subject_performance(proficiency_records)
            
            # 難易度別傾向分析
            data['difficulty_trends'] = self._analyze_difficulty_trends(unit_selections)
            
            # 時間パターン分析
            data['time_patterns'] = self._analyze_time_patterns(unit_selections)
            
            # エラーパターン分析
            data['error_patterns'] = self._analyze_error_patterns(proficiency_records)
            
        except Exception as e:
            logger.warning(f"学習データ収集エラー (学生ID: {student_id}): {str(e)}")
        
        return data
    
    def _analyze_category_performance(self, proficiency_records: List) -> Dict[str, Any]:
        """カテゴリ別パフォーマンスを分析"""
        category_stats = defaultdict(lambda: {
            'total_attempts': 0,
            'total_correct': 0,
            'accuracy_rates': [],
            'mastery_levels': [],
            'category_name': ''
        })
        
        for record in proficiency_records:
            cat_id = record['category_id']
            stats = category_stats[cat_id]
            
            stats['category_name'] = record['category_name']
            stats['total_attempts'] += record['total_attempted']
            stats['total_correct'] += record['total_correct']
            stats['accuracy_rates'].append(record['accuracy_rate'])
            stats['mastery_levels'].append(record['mastery_level'])
        
        # 統計計算
        for cat_id, stats in category_stats.items():
            if stats['accuracy_rates']:
                stats['avg_accuracy'] = statistics.mean(stats['accuracy_rates'])
                stats['accuracy_variance'] = statistics.variance(stats['accuracy_rates']) if len(stats['accuracy_rates']) > 1 else 0
                stats['avg_mastery'] = statistics.mean(stats['mastery_levels'])
                stats['overall_accuracy'] = stats['total_correct'] / stats['total_attempts'] if stats['total_attempts'] > 0 else 0
        
        return dict(category_stats)
    
    def _analyze_subject_performance(self, proficiency_records: List) -> Dict[str, Any]:
        """科目別パフォーマンスを分析"""
        subject_stats = defaultdict(lambda: {
            'total_attempts': 0,
            'total_correct': 0,
            'accuracy_rates': [],
            'categories_count': 0,
            'subject_name': ''
        })
        
        for record in proficiency_records:
            subject_name = record['subject_name']
            stats = subject_stats[subject_name]
            
            stats['subject_name'] = subject_name
            stats['total_attempts'] += record['total_attempted']
            stats['total_correct'] += record['total_correct']
            stats['accuracy_rates'].append(record['accuracy_rate'])
            stats['categories_count'] += 1
        
        # 統計計算
        for subject_name, stats in subject_stats.items():
            if stats['accuracy_rates']:
                stats['avg_accuracy'] = statistics.mean(stats['accuracy_rates'])
                stats['overall_accuracy'] = stats['total_correct'] / stats['total_attempts'] if stats['total_attempts'] > 0 else 0
        
        return dict(subject_stats)
    
    def _analyze_difficulty_trends(self, unit_selections: List) -> Dict[str, Any]:
        """難易度別学習傾向を分析"""
        difficulty_stats = defaultdict(lambda: {
            'total_units': 0,
            'completed_units': 0,
            'avg_progress': 0,
            'avg_accuracy': 0,
            'total_study_time': 0
        })
        
        for selection in unit_selections:
            difficulty = selection['difficulty_level']
            stats = difficulty_stats[difficulty]
            
            stats['total_units'] += 1
            if selection['status'] == 'completed':
                stats['completed_units'] += 1
            
            stats['avg_progress'] += selection['progress_percentage']
            
            if selection['total_items'] > 0:
                accuracy = selection['correct_items'] / selection['total_items']
                stats['avg_accuracy'] += accuracy
            
            stats['total_study_time'] += selection['study_time_minutes'] or 0
        
        # 平均値計算
        for difficulty, stats in difficulty_stats.items():
            if stats['total_units'] > 0:
                stats['avg_progress'] /= stats['total_units']
                stats['avg_accuracy'] /= stats['total_units']
                stats['completion_rate'] = stats['completed_units'] / stats['total_units']
        
        return dict(difficulty_stats)
    
    def _analyze_time_patterns(self, unit_selections: List) -> Dict[str, Any]:
        """時間パターンを分析"""
        time_patterns = {
            'study_sessions': [],
            'daily_study_time': defaultdict(int),
            'weekly_patterns': defaultdict(int),
            'session_lengths': []
        }
        
        for selection in unit_selections:
            if selection['last_activity_at'] and selection['study_time_minutes']:
                activity_date = selection['last_activity_at']
                study_time = selection['study_time_minutes']
                
                # 日別学習時間
                date_key = activity_date.strftime('%Y-%m-%d')
                time_patterns['daily_study_time'][date_key] += study_time
                
                # 週別パターン
                weekday = activity_date.weekday()
                time_patterns['weekly_patterns'][weekday] += study_time
                
                # セッション長
                time_patterns['session_lengths'].append(study_time)
        
        # 統計計算
        if time_patterns['session_lengths']:
            time_patterns['avg_session_length'] = statistics.mean(time_patterns['session_lengths'])
            time_patterns['session_variance'] = statistics.variance(time_patterns['session_lengths']) if len(time_patterns['session_lengths']) > 1 else 0
        
        return time_patterns
    
    def _analyze_error_patterns(self, proficiency_records: List) -> List[Dict[str, Any]]:
        """エラーパターンを分析"""
        error_patterns = []
        
        for record in proficiency_records:
            if record['accuracy_rate'] < self.weak_accuracy_threshold and record['total_attempted'] >= self.min_attempts_threshold:
                error_patterns.append({
                    'category_id': record['category_id'],
                    'category_name': record['category_name'],
                    'error_rate': 1 - record['accuracy_rate'],
                    'total_attempts': record['total_attempted'],
                    'pattern_type': self._classify_error_pattern(record)
                })
        
        return error_patterns
    
    def _analyze_basebuilder_performance(
        self, 
        word_proficiencies: List[Dict[str, Any]], 
        answer_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """BaseBuilder学習データの詳細分析"""
        stats = {
            'vocabulary_mastery': {},
            'category_weaknesses': {},
            'difficulty_patterns': {},
            'time_efficiency': {},
            'hint_dependency': {},
            'spaced_repetition_effectiveness': {}
        }
        
        try:
            # 語彙習得レベル分析
            level_distribution = defaultdict(int)
            categories_by_level = defaultdict(list)
            
            for wp in word_proficiencies:
                level_distribution[wp['level']] += 1
                categories_by_level[wp['category_name']].append(wp['level'])
            
            stats['vocabulary_mastery'] = {
                'level_distribution': dict(level_distribution),
                'total_words': len(word_proficiencies),
                'mastered_words': level_distribution[5] + level_distribution[4],  # レベル4-5を習得済み
                'struggling_words': level_distribution[0] + level_distribution[1]  # レベル0-1は苦手
            }
            
            # カテゴリ別弱点分析
            for category, levels in categories_by_level.items():
                if levels:
                    avg_level = statistics.mean(levels)
                    variance = statistics.variance(levels) if len(levels) > 1 else 0
                    stats['category_weaknesses'][category] = {
                        'average_level': avg_level,
                        'level_variance': variance,
                        'word_count': len(levels),
                        'is_weak': avg_level < 2.5 and len(levels) >= 3
                    }
            
            # 解答記録から詳細分析
            if answer_records:
                # 難易度別パフォーマンス
                difficulty_performance = defaultdict(lambda: {'correct': 0, 'total': 0, 'avg_time': 0})
                hint_usage = defaultdict(lambda: {'used': 0, 'total': 0})
                
                for record in answer_records:
                    diff = record['difficulty']
                    difficulty_performance[diff]['total'] += 1
                    if record['is_correct']:
                        difficulty_performance[diff]['correct'] += 1
                    
                    if record['answer_time_seconds']:
                        difficulty_performance[diff]['avg_time'] += record['answer_time_seconds']
                    
                    hint_usage[diff]['total'] += 1
                    if record['hint_used']:
                        hint_usage[diff]['used'] += 1
                
                # 統計計算
                for diff in difficulty_performance:
                    perf = difficulty_performance[diff]
                    if perf['total'] > 0:
                        perf['accuracy'] = perf['correct'] / perf['total']
                        perf['avg_time'] = perf['avg_time'] / perf['total']
                
                for diff in hint_usage:
                    usage = hint_usage[diff]
                    if usage['total'] > 0:
                        usage['dependency_rate'] = usage['used'] / usage['total']
                
                stats['difficulty_patterns'] = dict(difficulty_performance)
                stats['hint_dependency'] = dict(hint_usage)
            
            # 間隔反復効果性の分析
            repetition_effectiveness = defaultdict(list)
            for wp in word_proficiencies:
                if wp['repetition_number'] and wp['level']:
                    repetition_effectiveness[wp['repetition_number']].append(wp['level'])
            
            for rep_num, levels in repetition_effectiveness.items():
                if levels:
                    stats['spaced_repetition_effectiveness'][rep_num] = {
                        'average_level': statistics.mean(levels),
                        'sample_size': len(levels)
                    }
            
        except Exception as e:
            logger.warning(f"BaseBuilder分析エラー: {str(e)}")
        
        return stats
    
    def _classify_error_pattern(self, record: Dict[str, Any]) -> str:
        """エラーパターンを分類"""
        accuracy = record['accuracy_rate']
        attempts = record['total_attempted']
        
        if accuracy < 0.3:
            return 'severe_difficulty'  # 重大な困難
        elif accuracy < 0.5:
            return 'major_difficulty'   # 大きな困難
        elif accuracy < 0.7:
            return 'minor_difficulty'   # 軽微な困難
        else:
            return 'inconsistent'       # 不安定
    
    def _analyze_concept_weaknesses(self, student_id: int, learning_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """概念理解の弱点を分析"""
        weaknesses = []
        
        categories_performance = learning_data.get('categories_performance', {})
        
        for cat_id, stats in categories_performance.items():
            if (stats['avg_accuracy'] < self.weak_accuracy_threshold and 
                stats['total_attempts'] >= self.min_attempts_threshold):
                
                severity = self._calculate_severity(stats['avg_accuracy'], stats['total_attempts'])
                confidence = self._calculate_confidence(stats['total_attempts'], stats.get('accuracy_variance', 0))
                
                weakness = {
                    'student_id': student_id,
                    'category': stats['category_name'],
                    'subcategory': f"概念理解_{cat_id}",
                    'weakness_type': 'concept',
                    'severity_level': severity,
                    'confidence_score': confidence,
                    'total_attempts': stats['total_attempts'],
                    'correct_attempts': stats['total_correct'],
                    'accuracy_rate': stats['avg_accuracy'],
                    'improvement_trend': self._determine_trend(stats),
                    'recommended_actions': self._generate_concept_recommendations(stats),
                    'analysis_data': {
                        'category_id': cat_id,
                        'accuracy_variance': stats.get('accuracy_variance', 0),
                        'mastery_level': stats.get('avg_mastery', 0)
                    }
                }
                weaknesses.append(weakness)
        
        return weaknesses
    
    def _analyze_skill_weaknesses(self, student_id: int, learning_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """スキル習得の弱点を分析"""
        weaknesses = []
        
        difficulty_trends = learning_data.get('difficulty_trends', {})
        
        for difficulty, stats in difficulty_trends.items():
            if (stats['avg_accuracy'] < self.weak_accuracy_threshold and 
                stats['total_units'] >= 2):
                
                severity = self._calculate_severity(stats['avg_accuracy'], stats['total_units'])
                confidence = self._calculate_confidence(stats['total_units'], 0)
                
                weakness = {
                    'student_id': student_id,
                    'category': f"難易度{difficulty}レベル",
                    'subcategory': f"スキル習得_難易度{difficulty}",
                    'weakness_type': 'skill',
                    'severity_level': severity,
                    'confidence_score': confidence,
                    'total_attempts': stats['total_units'],
                    'correct_attempts': stats['completed_units'],
                    'accuracy_rate': stats['avg_accuracy'],
                    'improvement_trend': 'stable',
                    'recommended_actions': self._generate_skill_recommendations(difficulty, stats),
                    'analysis_data': {
                        'difficulty_level': difficulty,
                        'completion_rate': stats['completion_rate'],
                        'avg_progress': stats['avg_progress']
                    }
                }
                weaknesses.append(weakness)
        
        return weaknesses
    
    def _analyze_knowledge_weaknesses(self, student_id: int, learning_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """知識定着の弱点を分析"""
        weaknesses = []
        
        subjects_performance = learning_data.get('subjects_performance', {})
        
        for subject_name, stats in subjects_performance.items():
            if (stats['avg_accuracy'] < self.weak_accuracy_threshold and 
                stats['total_attempts'] >= self.min_attempts_threshold):
                
                severity = self._calculate_severity(stats['avg_accuracy'], stats['total_attempts'])
                confidence = self._calculate_confidence(stats['total_attempts'], 0)
                
                weakness = {
                    'student_id': student_id,
                    'category': subject_name,
                    'subcategory': f"知識定着_{subject_name}",
                    'weakness_type': 'knowledge',
                    'severity_level': severity,
                    'confidence_score': confidence,
                    'total_attempts': stats['total_attempts'],
                    'correct_attempts': stats['total_correct'],
                    'accuracy_rate': stats['avg_accuracy'],
                    'improvement_trend': 'stable',
                    'recommended_actions': self._generate_knowledge_recommendations(subject_name, stats),
                    'analysis_data': {
                        'subject_name': subject_name,
                        'categories_covered': stats['categories_count']
                    }
                }
                weaknesses.append(weakness)
        
        return weaknesses
    
    def _analyze_application_weaknesses(self, student_id: int, learning_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """応用力の弱点を分析"""
        weaknesses = []
        
        difficulty_trends = learning_data.get('difficulty_trends', {})
        
        # 応用レベル（難易度3）の分析
        if 3 in difficulty_trends:
            stats = difficulty_trends[3]
            if stats['total_units'] >= 1 and stats['avg_accuracy'] < 0.6:  # 応用問題は基準を下げる
                
                severity = self._calculate_severity(stats['avg_accuracy'], stats['total_units'])
                confidence = self._calculate_confidence(stats['total_units'], 0)
                
                weakness = {
                    'student_id': student_id,
                    'category': "応用問題",
                    'subcategory': "応用力_難易度3",
                    'weakness_type': 'application',
                    'severity_level': severity,
                    'confidence_score': confidence,
                    'total_attempts': stats['total_units'],
                    'correct_attempts': stats['completed_units'],
                    'accuracy_rate': stats['avg_accuracy'],
                    'improvement_trend': 'stable',
                    'recommended_actions': self._generate_application_recommendations(stats),
                    'analysis_data': {
                        'difficulty_level': 3,
                        'completion_rate': stats['completion_rate']
                    }
                }
                weaknesses.append(weakness)
        
        return weaknesses
    
    def _analyze_learning_pattern_weaknesses(self, student_id: int, learning_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """学習パターンの弱点を分析"""
        weaknesses = []
        
        time_patterns = learning_data.get('time_patterns', {})
        
        # 学習時間の不安定性をチェック
        if 'session_variance' in time_patterns and time_patterns['session_variance'] > 1000:  # 高い分散
            weakness = {
                'student_id': student_id,
                'category': "学習パターン",
                'subcategory': "学習時間の不安定性",
                'weakness_type': 'skill',
                'severity_level': 2,
                'confidence_score': 0.7,
                'total_attempts': len(time_patterns.get('session_lengths', [])),
                'correct_attempts': 0,
                'accuracy_rate': 0.0,
                'improvement_trend': 'stable',
                'recommended_actions': ["定期的な学習スケジュールの確立", "短時間集中学習の実践"],
                'analysis_data': {
                    'session_variance': time_patterns['session_variance'],
                    'avg_session_length': time_patterns.get('avg_session_length', 0)
                }
            }
            weaknesses.append(weakness)
        
        return weaknesses
    
    def _analyze_basebuilder_specific_weaknesses(self, student_id: int, learning_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """BaseBuilder特有の弱点を分析"""
        weaknesses = []
        
        basebuilder_stats = learning_data.get('basebuilder_stats', {})
        
        # 語彙習得の弱点分析
        vocabulary_mastery = basebuilder_stats.get('vocabulary_mastery', {})
        if vocabulary_mastery.get('struggling_words', 0) > vocabulary_mastery.get('mastered_words', 0):
            weakness = {
                'student_id': student_id,
                'category': "語彙習得",
                'subcategory': "基礎語彙の定着不足",
                'weakness_type': 'knowledge',
                'severity_level': 4,  # 語彙は基礎なので重要
                'confidence_score': 0.8,
                'total_attempts': vocabulary_mastery.get('total_words', 0),
                'correct_attempts': vocabulary_mastery.get('mastered_words', 0),
                'accuracy_rate': vocabulary_mastery.get('mastered_words', 0) / max(vocabulary_mastery.get('total_words', 1), 1),
                'improvement_trend': 'declining',
                'recommended_actions': [
                    "基礎語彙の集中復習", 
                    "間隔反復学習の活用",
                    "語彙カードの作成・活用",
                    "文脈での語彙学習"
                ],
                'analysis_data': {
                    'struggling_words': vocabulary_mastery.get('struggling_words', 0),
                    'mastered_words': vocabulary_mastery.get('mastered_words', 0),
                    'level_distribution': vocabulary_mastery.get('level_distribution', {})
                }
            }
            weaknesses.append(weakness)
        
        # カテゴリ別弱点分析（BaseBuilder詳細版）
        category_weaknesses = basebuilder_stats.get('category_weaknesses', {})
        for category, stats in category_weaknesses.items():
            if stats.get('is_weak', False) and stats.get('word_count', 0) >= 3:
                severity = 3 if stats['average_level'] < 1.5 else 2
                weakness = {
                    'student_id': student_id,
                    'category': f"語彙カテゴリ: {category}",
                    'subcategory': f"カテゴリ別弱点_{category}",
                    'weakness_type': 'concept',
                    'severity_level': severity,
                    'confidence_score': min(0.9, stats['word_count'] / 10.0),
                    'total_attempts': stats['word_count'],
                    'correct_attempts': int(stats['average_level'] * stats['word_count'] / 5),
                    'accuracy_rate': stats['average_level'] / 5.0,
                    'improvement_trend': 'stable',
                    'recommended_actions': [
                        f"{category}分野の基礎固め",
                        "カテゴリ特化型問題練習",
                        "関連語彙の体系的学習"
                    ],
                    'analysis_data': {
                        'average_level': stats['average_level'],
                        'level_variance': stats['level_variance'],
                        'category_name': category
                    }
                }
                weaknesses.append(weakness)
        
        # ヒント依存性の分析
        hint_dependency = basebuilder_stats.get('hint_dependency', {})
        high_dependency_levels = [
            diff for diff, usage in hint_dependency.items() 
            if usage.get('dependency_rate', 0) > 0.5 and usage.get('total', 0) >= 5
        ]
        
        if high_dependency_levels:
            weakness = {
                'student_id': student_id,
                'category': "学習方略",
                'subcategory': "ヒント依存性",
                'weakness_type': 'skill',
                'severity_level': 2,
                'confidence_score': 0.7,
                'total_attempts': sum(hint_dependency[diff]['total'] for diff in high_dependency_levels),
                'correct_attempts': 0,
                'accuracy_rate': 0.0,
                'improvement_trend': 'stable',
                'recommended_actions': [
                    "ヒントなしでの問題解決練習",
                    "思考プロセスの明確化",
                    "段階的ヒント削減",
                    "自力解答への意識向上"
                ],
                'analysis_data': {
                    'high_dependency_difficulties': high_dependency_levels,
                    'dependency_rates': {
                        diff: hint_dependency[diff]['dependency_rate'] 
                        for diff in high_dependency_levels
                    }
                }
            }
            weaknesses.append(weakness)
        
        # 間隔反復効果性の分析
        spaced_repetition = basebuilder_stats.get('spaced_repetition_effectiveness', {})
        poor_retention_reps = [
            rep for rep, stats in spaced_repetition.items()
            if stats.get('average_level', 0) < 2.0 and stats.get('sample_size', 0) >= 3
        ]
        
        if poor_retention_reps:
            weakness = {
                'student_id': student_id,
                'category': "記憶定着",
                'subcategory': "間隔反復効果不足",
                'weakness_type': 'skill',
                'severity_level': 3,
                'confidence_score': 0.6,
                'total_attempts': sum(spaced_repetition[rep]['sample_size'] for rep in poor_retention_reps),
                'correct_attempts': 0,
                'accuracy_rate': 0.0,
                'improvement_trend': 'declining',
                'recommended_actions': [
                    "復習タイミングの調整",
                    "記憶法の見直し",
                    "能動的復習の実践",
                    "記憶定着確認の強化"
                ],
                'analysis_data': {
                    'poor_retention_repetitions': poor_retention_reps,
                    'repetition_effectiveness': spaced_repetition
                }
            }
            weaknesses.append(weakness)
        
        return weaknesses
    
    def _calculate_severity(self, accuracy_rate: float, attempts: int) -> int:
        """深刻度を計算（1: 軽微, 2: 中程度, 3: 重大, 4: 緊急, 5: 最重要）"""
        if accuracy_rate < 0.3:
            return 5  # 最重要
        elif accuracy_rate < 0.5:
            return 4  # 緊急
        elif accuracy_rate < 0.6:
            return 3  # 重大
        elif accuracy_rate < 0.7:
            return 2  # 中程度
        else:
            return 1  # 軽微
    
    def _calculate_confidence(self, attempts: int, variance: float) -> float:
        """信頼度を計算（0.0-1.0）"""
        # 試行回数による信頼度
        attempt_confidence = min(attempts / 10.0, 1.0)
        
        # 分散による信頼度調整（分散が大きいと信頼度は下がる）
        variance_factor = max(0.1, 1.0 - variance / 1000.0)
        
        return min(attempt_confidence * variance_factor, 1.0)
    
    def _determine_trend(self, stats: Dict[str, Any]) -> str:
        """改善傾向を判定"""
        # 簡易実装：より詳細な時系列分析が必要
        accuracy_rates = stats.get('accuracy_rates', [])
        if len(accuracy_rates) >= 3:
            recent_avg = statistics.mean(accuracy_rates[-3:])
            earlier_avg = statistics.mean(accuracy_rates[:-3]) if len(accuracy_rates) > 3 else recent_avg
            
            if recent_avg > earlier_avg * 1.1:
                return 'improving'
            elif recent_avg < earlier_avg * 0.9:
                return 'declining'
        
        return 'stable'
    
    def _generate_concept_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """概念理解向上のための推薦を生成"""
        recommendations = []
        
        if stats['avg_accuracy'] < 0.5:
            recommendations.extend([
                "基礎概念の復習を重点的に行う",
                "より易しい問題から段階的に取り組む",
                "概念マップや図解を活用した学習"
            ])
        else:
            recommendations.extend([
                "類似問題での練習を増やす",
                "異なる角度からの問題に挑戦",
                "概念の応用例を学習"
            ])
        
        return recommendations
    
    def _generate_skill_recommendations(self, difficulty: int, stats: Dict[str, Any]) -> List[str]:
        """スキル習得向上のための推薦を生成"""
        recommendations = []
        
        if difficulty == 1:  # 基礎
            recommendations.extend([
                "基本スキルの反復練習",
                "手順の確認と定着",
                "簡単な問題での成功体験の積み重ね"
            ])
        elif difficulty == 2:  # 標準
            recommendations.extend([
                "標準的な問題パターンの習得",
                "解法手順の体系化",
                "間違いパターンの分析と対策"
            ])
        else:  # 応用
            recommendations.extend([
                "基礎スキルの再確認",
                "段階的な難易度上昇での練習",
                "応用問題への取り組み前の準備強化"
            ])
        
        return recommendations
    
    def _generate_knowledge_recommendations(self, subject_name: str, stats: Dict[str, Any]) -> List[str]:
        """知識定着向上のための推薦を生成"""
        return [
            f"{subject_name}の基礎知識の復習",
            "定期的な復習スケジュールの設定",
            "知識の体系化と整理",
            "実践的な問題での知識応用"
        ]
    
    def _generate_application_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """応用力向上のための推薦を生成"""
        return [
            "基礎から応用への段階的学習",
            "問題解決プロセスの意識化",
            "多様な問題パターンへの慣れ",
            "論理的思考力の養成"
        ]
    
    def _deduplicate_and_prioritize(self, weaknesses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """重複を排除し優先度付けを行う"""
        # カテゴリとサブカテゴリによる重複チェック
        seen = set()
        unique_weaknesses = []
        
        # 深刻度で降順ソート
        sorted_weaknesses = sorted(weaknesses, key=lambda x: x['severity_level'], reverse=True)
        
        for weakness in sorted_weaknesses:
            key = (weakness['category'], weakness['subcategory'])
            if key not in seen:
                seen.add(key)
                unique_weaknesses.append(weakness)
        
        return unique_weaknesses
    
    def _save_weakness_analysis(self, student_id: int, weaknesses: List[Dict[str, Any]]):
        """弱点分析結果をデータベースに保存"""
        try:
            # 既存の活動中の弱点を非活動化
            StudentWeakness.query.filter_by(
                student_id=student_id,
                is_active=True
            ).update({'is_active': False})
            
            # 新しい弱点を保存
            for weakness_data in weaknesses:
                # subject_idを取得
                subject_id = None
                if weakness_data.get('analysis_data', {}).get('subject_name'):
                    subject = Subject.query.filter_by(
                        name=weakness_data['analysis_data']['subject_name']
                    ).first()
                    if subject:
                        subject_id = subject.id
                
                weakness = StudentWeakness(
                    student_id=weakness_data['student_id'],
                    subject_id=subject_id,
                    category=weakness_data['category'],
                    subcategory=weakness_data['subcategory'],
                    weakness_type=weakness_data['weakness_type'],
                    severity_level=weakness_data['severity_level'],
                    confidence_score=weakness_data['confidence_score'],
                    total_attempts=weakness_data['total_attempts'],
                    correct_attempts=weakness_data['correct_attempts'],
                    accuracy_rate=weakness_data['accuracy_rate'],
                    last_attempt_at=datetime.utcnow(),
                    improvement_trend=weakness_data['improvement_trend'],
                    recommended_actions=weakness_data['recommended_actions'],
                    analysis_data=weakness_data['analysis_data'],
                    is_active=True
                )
                
                db.session.add(weakness)
            
            db.session.commit()
            logger.info(f"弱点分析結果を保存 (学生ID: {student_id}, 弱点数: {len(weaknesses)})")
            
        except Exception as e:
            logger.error(f"弱点分析保存エラー: {str(e)}")
            db.session.rollback()
            raise WeaknessAnalysisError(f"弱点分析保存中にエラーが発生しました: {str(e)}")
    
    def _weakness_to_dict(self, weakness: StudentWeakness) -> Dict[str, Any]:
        """StudentWeaknessオブジェクトを辞書に変換"""
        return {
            'id': weakness.id,
            'student_id': weakness.student_id,
            'subject_id': weakness.subject_id,
            'category': weakness.category,
            'subcategory': weakness.subcategory,
            'weakness_type': weakness.weakness_type,
            'severity_level': weakness.severity_level,
            'confidence_score': float(weakness.confidence_score),
            'total_attempts': weakness.total_attempts,
            'correct_attempts': weakness.correct_attempts,
            'accuracy_rate': float(weakness.accuracy_rate),
            'last_attempt_at': weakness.last_attempt_at.isoformat() if weakness.last_attempt_at else None,
            'improvement_trend': weakness.improvement_trend,
            'recommended_actions': weakness.recommended_actions,
            'analysis_data': weakness.analysis_data,
            'is_active': weakness.is_active,
            'created_at': weakness.created_at.isoformat() if weakness.created_at else None,
            'updated_at': weakness.updated_at.isoformat() if weakness.updated_at else None
        }
    
    def get_weakness_summary(self, student_id: int) -> Dict[str, Any]:
        """学生の弱点サマリーを取得"""
        try:
            active_weaknesses = StudentWeakness.query.filter_by(
                student_id=student_id,
                is_active=True
            ).order_by(desc(StudentWeakness.severity_level)).all()
            
            if not active_weaknesses:
                return {
                    'total_weaknesses': 0,
                    'severity_distribution': {},
                    'weakness_types': {},
                    'recommended_focus_areas': []
                }
            
            # 深刻度分布
            severity_distribution = Counter(w.severity_level for w in active_weaknesses)
            
            # 弱点タイプ分布
            weakness_types = Counter(w.weakness_type for w in active_weaknesses)
            
            # 重点改善エリア（上位3つ）
            focus_areas = [
                {
                    'category': w.category,
                    'severity_level': w.severity_level,
                    'recommended_actions': w.recommended_actions[:2]  # 上位2つの推薦アクション
                }
                for w in active_weaknesses[:3]
            ]
            
            return {
                'total_weaknesses': len(active_weaknesses),
                'severity_distribution': dict(severity_distribution),
                'weakness_types': dict(weakness_types),
                'recommended_focus_areas': focus_areas,
                'last_analysis': active_weaknesses[0].updated_at.isoformat() if active_weaknesses else None
            }
            
        except Exception as e:
            logger.error(f"弱点サマリー取得エラー: {str(e)}")
            return {}


class WeaknessRecommendationEngine:
    """弱点に基づく推薦エンジン"""
    
    def __init__(self, weakness_analyzer: WeaknessAnalyzer):
        self.weakness_analyzer = weakness_analyzer
    
    def generate_targeted_recommendations(
        self, 
        student_id: int, 
        max_recommendations: int = 5
    ) -> List[Dict[str, Any]]:
        """弱点に基づく対象推薦を生成"""
        try:
            # 活動中の弱点を取得
            weaknesses = StudentWeakness.query.filter_by(
                student_id=student_id,
                is_active=True
            ).order_by(desc(StudentWeakness.severity_level)).limit(max_recommendations).all()
            
            recommendations = []
            
            for weakness in weaknesses:
                # 弱点に対応する学習コンテンツを推薦
                content_recommendations = self._find_content_for_weakness(weakness)
                recommendations.extend(content_recommendations)
            
            return recommendations[:max_recommendations]
            
        except Exception as e:
            logger.error(f"対象推薦生成エラー: {str(e)}")
            return []
    
    def _find_content_for_weakness(self, weakness: StudentWeakness) -> List[Dict[str, Any]]:
        """弱点に対応するコンテンツを検索"""
        recommendations = []
        
        try:
            if weakness.weakness_type == 'concept':
                # 概念理解のための基礎的な単元を推薦
                basic_units = CurriculumUnit.query.filter_by(
                    difficulty_level=1
                ).filter(
                    CurriculumUnit.title.contains(weakness.category)
                ).limit(2).all()
                
                for unit in basic_units:
                    recommendations.append({
                        'type': 'unit',
                        'item_id': unit.id,
                        'title': f"基礎復習: {unit.title}",
                        'description': f"{weakness.category}の概念理解を深めるための基礎学習",
                        'weakness_id': weakness.id,
                        'priority': weakness.severity_level
                    })
            
            elif weakness.weakness_type == 'knowledge':
                # 知識定着のための問題を推薦
                if weakness.subject_id:
                    categories = ProblemCategory.query.filter_by(
                        subject_id=weakness.subject_id
                    ).limit(2).all()
                    
                    for category in categories:
                        recommendations.append({
                            'type': 'problem_set',
                            'item_id': category.id,
                            'title': f"知識定着: {category.name}",
                            'description': f"{weakness.category}の知識を定着させるための問題演習",
                            'weakness_id': weakness.id,
                            'priority': weakness.severity_level
                        })
                
                # BaseBuilder語彙学習の推薦
                if '語彙' in weakness.category:
                    # 弱点カテゴリに対応するBaseBuilder問題を推薦
                    analysis_data = weakness.analysis_data or {}
                    category_name = analysis_data.get('category_name')
                    
                    if category_name:
                        category = ProblemCategory.query.filter_by(name=category_name).first()
                        if category:
                            recommendations.append({
                                'type': 'basebuilder_category',
                                'item_id': category.id,
                                'title': f"語彙強化: {category_name}",
                                'description': f"{category_name}カテゴリの語彙を集中的に学習",
                                'weakness_id': weakness.id,
                                'priority': weakness.severity_level,
                                'learning_mode': 'vocabulary_focus'
                            })
            
            # BaseBuilder特有の学習方略改善推薦
            elif weakness.subcategory == 'ヒント依存性':
                recommendations.append({
                    'type': 'learning_strategy',
                    'item_id': 'hint_independence_training',
                    'title': "自立学習トレーニング",
                    'description': "ヒントに頼らない問題解決力を育成",
                    'weakness_id': weakness.id,
                    'priority': weakness.severity_level,
                    'strategy_type': 'hint_independence'
                })
            
            elif weakness.subcategory == '間隔反復効果不足':
                recommendations.append({
                    'type': 'learning_strategy',
                    'item_id': 'spaced_repetition_optimization',
                    'title': "記憶定着法改善",
                    'description': "効果的な間隔反復学習の実践",
                    'weakness_id': weakness.id,
                    'priority': weakness.severity_level,
                    'strategy_type': 'memory_retention'
                })
            
        except Exception as e:
            logger.warning(f"コンテンツ検索エラー: {str(e)}")
        
        return recommendations