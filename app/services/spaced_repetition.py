# app/services/spaced_repetition.py

import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass
from sqlalchemy import and_, or_, desc, func

from app.models import (
    User, ReviewSet, ReviewSetItem, StudentWeakness, ProficiencyRecord,
    BasicKnowledgeItem, ProblemCategory, StudentUnitSelection
)
from app.services.weakness_analyzer import WeaknessAnalyzer
from app.utils.exceptions import SpacedRepetitionError, InsufficientDataError
from extensions import db

logger = logging.getLogger(__name__)


class DifficultyLevel(Enum):
    """問題難易度レベル"""
    BEGINNER = 1    # 初級
    INTERMEDIATE = 2  # 中級
    ADVANCED = 3    # 上級


class ReviewResult(Enum):
    """復習結果"""
    PERFECT = 5     # 完璧
    GOOD = 4        # 良い
    SATISFACTORY = 3  # 普通
    DIFFICULT = 2   # 困難
    FAILED = 1      # 失敗


@dataclass
class SpacedRepetitionCard:
    """間隔反復学習カード"""
    item_id: int
    difficulty: float = 2.5
    interval: int = 1  # 日数
    repetition: int = 0
    ease_factor: float = 2.5
    next_review: datetime = None
    last_reviewed: datetime = None
    review_count: int = 0
    success_count: int = 0


class SuperMemoAlgorithm:
    """SuperMemo SM-2アルゴリズムの実装"""
    
    def __init__(self):
        self.min_ease_factor = 1.3
        self.initial_ease_factor = 2.5
        self.initial_interval = 1
    
    def calculate_next_review(
        self, 
        card: SpacedRepetitionCard, 
        result: ReviewResult
    ) -> SpacedRepetitionCard:
        """
        次回復習日を計算
        
        Args:
            card: 復習カード
            result: 復習結果
            
        Returns:
            更新されたカード
        """
        card.last_reviewed = datetime.utcnow()
        card.review_count += 1
        
        quality = result.value
        
        if quality >= 3:  # 正解
            card.success_count += 1
            
            if card.repetition == 0:
                card.interval = 1
            elif card.repetition == 1:
                card.interval = 6
            else:
                card.interval = int(card.interval * card.ease_factor)
            
            card.repetition += 1
        else:  # 不正解
            card.repetition = 0
            card.interval = 1
        
        # 易しさ係数の更新
        card.ease_factor = max(
            self.min_ease_factor,
            card.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        )
        
        # 次回復習日の設定
        card.next_review = card.last_reviewed + timedelta(days=card.interval)
        
        return card


class AdaptiveDifficultyAdjuster:
    """適応的難易度調整システム"""
    
    def __init__(self):
        self.target_accuracy = 0.75  # 目標正答率
        self.adjustment_threshold = 0.1  # 調整閾値
    
    def adjust_difficulty(
        self, 
        current_accuracy: float, 
        current_difficulty: float,
        sample_size: int = 1
    ) -> float:
        """
        正答率に基づいて難易度を調整
        
        Args:
            current_accuracy: 現在の正答率
            current_difficulty: 現在の難易度
            sample_size: サンプルサイズ
            
        Returns:
            調整後の難易度
        """
        if sample_size < 3:  # サンプルが少ない場合は調整しない
            return current_difficulty
        
        accuracy_diff = current_accuracy - self.target_accuracy
        
        if abs(accuracy_diff) < self.adjustment_threshold:
            return current_difficulty  # 調整不要
        
        # 正答率が高すぎる場合は難易度を上げる
        if accuracy_diff > self.adjustment_threshold:
            adjustment = min(0.2, accuracy_diff * 0.5)
            return min(5.0, current_difficulty + adjustment)
        
        # 正答率が低すぎる場合は難易度を下げる
        else:
            adjustment = min(0.2, abs(accuracy_diff) * 0.5)
            return max(1.0, current_difficulty - adjustment)


class SpacedRepetitionEngine:
    """間隔反復学習エンジン"""
    
    def __init__(self):
        self.sm2_algorithm = SuperMemoAlgorithm()
        self.difficulty_adjuster = AdaptiveDifficultyAdjuster()
        self.weakness_analyzer = WeaknessAnalyzer()
    
    def create_review_set(
        self,
        student_id: int,
        review_type: str = 'spaced_repetition',
        target_problems: int = 20,
        focus_weaknesses: bool = True
    ) -> ReviewSet:
        """
        間隔反復学習用の復習セットを作成
        
        Args:
            student_id: 学生ID
            review_type: 復習タイプ
            target_problems: 目標問題数
            focus_weaknesses: 弱点重視フラグ
            
        Returns:
            作成された復習セット
        """
        try:
            student = User.query.get(student_id)
            if not student or student.role != 'student':
                raise SpacedRepetitionError("有効な学生が見つかりません")
            
            # 復習対象問題を選択
            review_items = self._select_review_items(
                student_id, target_problems, focus_weaknesses
            )
            
            if not review_items:
                raise InsufficientDataError("復習対象の問題が見つかりません")
            
            # 復習セットを作成
            review_set = ReviewSet(
                student_id=student_id,
                title=self._generate_review_title(review_type, len(review_items)),
                description=self._generate_review_description(review_type, focus_weaknesses),
                generation_type='automatic',
                review_type=review_type,
                total_problems=len(review_items),
                estimated_time_minutes=self._estimate_review_time(review_items),
                status='active',
                expires_at=datetime.utcnow() + timedelta(days=7)  # 1週間で期限切れ
            )
            
            db.session.add(review_set)
            db.session.flush()  # IDを取得
            
            # 復習問題を追加
            for order_index, item_data in enumerate(review_items):
                review_item = ReviewSetItem(
                    review_set_id=review_set.id,
                    problem_id=item_data['problem_id'],
                    order_index=order_index,
                    weight=item_data.get('weight', 1.0),
                    expected_difficulty=item_data.get('difficulty', 2.5),
                    weakness_category=item_data.get('weakness_category'),
                    selection_reason=item_data.get('selection_reason', 'スケジュールされた復習')
                )
                db.session.add(review_item)
            
            db.session.commit()
            
            logger.info(f"復習セットを作成 (学生ID: {student_id}, 問題数: {len(review_items)})")
            return review_set
            
        except Exception as e:
            logger.error(f"復習セット作成エラー: {str(e)}")
            db.session.rollback()
            raise SpacedRepetitionError(f"復習セット作成中にエラーが発生しました: {str(e)}")
    
    def _select_review_items(
        self, 
        student_id: int, 
        target_count: int, 
        focus_weaknesses: bool
    ) -> List[Dict[str, Any]]:
        """復習対象問題を選択"""
        review_items = []
        
        try:
            # 1. 間隔反復対象の問題を選択
            spaced_items = self._get_spaced_repetition_items(student_id)
            review_items.extend(spaced_items)
            
            # 2. 弱点フォーカスの場合、弱点問題を追加
            if focus_weaknesses:
                weakness_items = self._get_weakness_focused_items(
                    student_id, 
                    max(target_count - len(review_items), 0)
                )
                review_items.extend(weakness_items)
            
            # 3. 不足分をランダム復習問題で補完
            if len(review_items) < target_count:
                random_items = self._get_random_review_items(
                    student_id, 
                    target_count - len(review_items)
                )
                review_items.extend(random_items)
            
            # 目標数に調整
            return review_items[:target_count]
            
        except Exception as e:
            logger.error(f"復習問題選択エラー: {str(e)}")
            return []
    
    def _get_spaced_repetition_items(self, student_id: int) -> List[Dict[str, Any]]:
        """間隔反復スケジュールに基づく問題を取得"""
        items = []
        
        try:
            # 過去の学習履歴から間隔反復対象を特定
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            # 正答率70-85%の問題を間隔反復対象とする
            proficiency_records = ProficiencyRecord.query.filter(
                and_(
                    ProficiencyRecord.student_id == student_id,
                    ProficiencyRecord.accuracy_rate >= 0.7,
                    ProficiencyRecord.accuracy_rate <= 0.85,
                    ProficiencyRecord.total_attempted >= 3,
                    ProficiencyRecord.last_updated >= cutoff_date
                )
            ).all()
            
            for record in proficiency_records:
                # カテゴリ内の問題を取得
                problems = BasicKnowledgeItem.query.filter_by(
                    category_id=record.category_id
                ).limit(3).all()  # カテゴリあたり最大3問
                
                for problem in problems:
                    # 間隔反復カードを作成/取得
                    card = self._get_or_create_card(student_id, problem.id, record)
                    
                    # 復習タイミングかチェック
                    if self._should_review_now(card):
                        items.append({
                            'problem_id': problem.id,
                            'weight': 1.0,
                            'difficulty': card.difficulty,
                            'selection_reason': f'間隔反復復習 (間隔: {card.interval}日)',
                            'card_data': card
                        })
            
        except Exception as e:
            logger.warning(f"間隔反復問題取得エラー: {str(e)}")
        
        return items
    
    def _get_weakness_focused_items(self, student_id: int, max_count: int) -> List[Dict[str, Any]]:
        """弱点に焦点を当てた問題を取得"""
        items = []
        
        try:
            # 活動中の弱点を取得
            weaknesses = StudentWeakness.query.filter_by(
                student_id=student_id,
                is_active=True
            ).order_by(desc(StudentWeakness.severity_level)).limit(5).all()
            
            for weakness in weaknesses:
                if len(items) >= max_count:
                    break
                
                # 弱点に関連する問題を検索
                weakness_problems = self._find_problems_for_weakness(weakness)
                
                for problem in weakness_problems[:2]:  # 弱点あたり最大2問
                    if len(items) >= max_count:
                        break
                    
                    items.append({
                        'problem_id': problem.id,
                        'weight': 1.5,  # 弱点問題は重み付けを大きく
                        'difficulty': 2.0,  # 基本的な難易度から開始
                        'weakness_category': weakness.category,
                        'selection_reason': f'弱点改善: {weakness.category} (深刻度: {weakness.severity_level})'
                    })
            
        except Exception as e:
            logger.warning(f"弱点問題取得エラー: {str(e)}")
        
        return items
    
    def _get_random_review_items(self, student_id: int, max_count: int) -> List[Dict[str, Any]]:
        """ランダム復習問題を取得"""
        items = []
        
        try:
            # 過去に学習した問題からランダムに選択
            studied_categories = db.session.query(ProficiencyRecord.category_id).filter_by(
                student_id=student_id
            ).subquery()
            
            problems = db.session.query(BasicKnowledgeItem).filter(
                BasicKnowledgeItem.category_id.in_(studied_categories)
            ).order_by(func.random()).limit(max_count).all()
            
            for problem in problems:
                items.append({
                    'problem_id': problem.id,
                    'weight': 0.8,  # ランダム問題は重み付けを小さく
                    'difficulty': 2.5,  # 標準難易度
                    'selection_reason': 'ランダム復習'
                })
            
        except Exception as e:
            logger.warning(f"ランダム問題取得エラー: {str(e)}")
        
        return items
    
    def _get_or_create_card(
        self, 
        student_id: int, 
        problem_id: int, 
        proficiency_record: ProficiencyRecord
    ) -> SpacedRepetitionCard:
        """間隔反復カードを取得または作成"""
        
        # 初期難易度を正答率から推定
        initial_difficulty = self._estimate_initial_difficulty(proficiency_record)
        
        # 前回の復習からの経過日数を計算
        days_since_last = (datetime.utcnow() - proficiency_record.last_updated).days
        
        card = SpacedRepetitionCard(
            item_id=problem_id,
            difficulty=initial_difficulty,
            interval=max(1, min(days_since_last, 30)),  # 1-30日の範囲
            repetition=proficiency_record.total_attempted,
            ease_factor=self._calculate_ease_factor(proficiency_record.accuracy_rate),
            last_reviewed=proficiency_record.last_updated,
            review_count=proficiency_record.total_attempted,
            success_count=proficiency_record.total_correct
        )
        
        return card
    
    def _estimate_initial_difficulty(self, proficiency_record: ProficiencyRecord) -> float:
        """初期難易度を推定"""
        accuracy = proficiency_record.accuracy_rate
        
        if accuracy >= 0.9:
            return 1.5  # 簡単
        elif accuracy >= 0.75:
            return 2.5  # 標準
        elif accuracy >= 0.6:
            return 3.5  # やや困難
        else:
            return 4.5  # 困難
    
    def _calculate_ease_factor(self, accuracy_rate: float) -> float:
        """正答率から易しさ係数を計算"""
        if accuracy_rate >= 0.9:
            return 2.8
        elif accuracy_rate >= 0.8:
            return 2.5
        elif accuracy_rate >= 0.7:
            return 2.2
        elif accuracy_rate >= 0.6:
            return 1.9
        else:
            return 1.6
    
    def _should_review_now(self, card: SpacedRepetitionCard) -> bool:
        """今復習すべきかどうか判定"""
        if card.next_review is None:
            return True  # 初回復習
        
        return datetime.utcnow() >= card.next_review
    
    def _find_problems_for_weakness(self, weakness: StudentWeakness) -> List[BasicKnowledgeItem]:
        """弱点に対応する問題を検索"""
        problems = []
        
        try:
            if weakness.analysis_data and 'category_id' in weakness.analysis_data:
                # 特定カテゴリの問題
                category_id = weakness.analysis_data['category_id']
                problems = BasicKnowledgeItem.query.filter_by(
                    category_id=category_id
                ).limit(5).all()
            else:
                # カテゴリ名での検索
                categories = ProblemCategory.query.filter(
                    ProblemCategory.name.contains(weakness.category)
                ).limit(3).all()
                
                for category in categories:
                    category_problems = BasicKnowledgeItem.query.filter_by(
                        category_id=category.id
                    ).limit(2).all()
                    problems.extend(category_problems)
            
        except Exception as e:
            logger.warning(f"弱点対応問題検索エラー: {str(e)}")
        
        return problems
    
    def _generate_review_title(self, review_type: str, problem_count: int) -> str:
        """復習セットのタイトルを生成"""
        type_names = {
            'spaced_repetition': '間隔反復復習',
            'weakness_focused': '弱点克服復習',
            'comprehensive': '総合復習',
            'exam_prep': '試験対策復習'
        }
        
        type_name = type_names.get(review_type, '復習')
        today = datetime.utcnow().strftime('%m/%d')
        
        return f"{type_name} - {today} ({problem_count}問)"
    
    def _generate_review_description(self, review_type: str, focus_weaknesses: bool) -> str:
        """復習セットの説明を生成"""
        descriptions = {
            'spaced_repetition': '効果的な記憶定着のため、最適なタイミングで復習問題を出題します。',
            'weakness_focused': '学習データから特定された弱点分野を重点的に復習します。',
            'comprehensive': '幅広い分野をバランス良く復習します。',
            'exam_prep': '試験対策として重要な問題を厳選しました。'
        }
        
        base_desc = descriptions.get(review_type, '復習問題を集めました。')
        
        if focus_weaknesses:
            base_desc += ' 弱点分野に重点を置いています。'
        
        return base_desc
    
    def _estimate_review_time(self, review_items: List[Dict[str, Any]]) -> int:
        """復習時間を推定"""
        base_time_per_problem = 2  # 問題あたり2分
        difficulty_multiplier = 1.0
        
        for item in review_items:
            difficulty = item.get('difficulty', 2.5)
            if difficulty > 3.5:
                difficulty_multiplier += 0.1
            elif difficulty < 2.0:
                difficulty_multiplier -= 0.05
        
        total_time = len(review_items) * base_time_per_problem * difficulty_multiplier
        return max(10, int(total_time))  # 最低10分
    
    def process_review_result(
        self,
        review_set_item_id: int,
        student_answer: str,
        is_correct: bool,
        time_spent_seconds: int,
        confidence_level: int = 3
    ) -> Dict[str, Any]:
        """
        復習結果を処理し、間隔反復アルゴリズムを適用
        
        Args:
            review_set_item_id: 復習問題ID
            student_answer: 学生の回答
            is_correct: 正解フラグ
            time_spent_seconds: 回答時間（秒）
            confidence_level: 自信レベル (1-5)
            
        Returns:
            処理結果
        """
        try:
            review_item = ReviewSetItem.query.get(review_set_item_id)
            if not review_item:
                raise SpacedRepetitionError("復習問題が見つかりません")
            
            # 復習結果を記録
            review_item.student_answer = student_answer
            review_item.is_correct = is_correct
            review_item.time_spent_seconds = time_spent_seconds
            review_item.attempts_count += 1
            review_item.completed_at = datetime.utcnow()
            review_item.is_completed = True
            
            # 結果から品質スコアを計算
            quality_score = self._calculate_quality_score(
                is_correct, confidence_level, time_spent_seconds
            )
            
            # 間隔反復カードを更新（仮想的な実装）
            if hasattr(review_item, 'card_data') and review_item.card_data:
                card = review_item.card_data
                result = ReviewResult(quality_score)
                updated_card = self.sm2_algorithm.calculate_next_review(card, result)
                
                # 次回復習の情報を返却
                next_review_info = {
                    'next_review_date': updated_card.next_review.isoformat(),
                    'interval_days': updated_card.interval,
                    'ease_factor': updated_card.ease_factor,
                    'repetition_count': updated_card.repetition
                }
            else:
                next_review_info = None
            
            # 難易度を調整
            new_difficulty = self.difficulty_adjuster.adjust_difficulty(
                current_accuracy=1.0 if is_correct else 0.0,
                current_difficulty=review_item.expected_difficulty or 2.5,
                sample_size=review_item.attempts_count
            )
            review_item.expected_difficulty = new_difficulty
            
            db.session.commit()
            
            result_data = {
                'review_item_id': review_item_id,
                'is_correct': is_correct,
                'quality_score': quality_score,
                'new_difficulty': new_difficulty,
                'time_spent': time_spent_seconds,
                'next_review_info': next_review_info
            }
            
            logger.info(f"復習結果を処理 (問題ID: {review_item_id}, 正解: {is_correct})")
            return result_data
            
        except Exception as e:
            logger.error(f"復習結果処理エラー: {str(e)}")
            db.session.rollback()
            raise SpacedRepetitionError(f"復習結果処理中にエラーが発生しました: {str(e)}")
    
    def _calculate_quality_score(
        self, 
        is_correct: bool, 
        confidence_level: int, 
        time_spent_seconds: int
    ) -> int:
        """品質スコア（1-5）を計算"""
        if not is_correct:
            return 1  # 不正解は最低スコア
        
        # 基本スコア
        base_score = 3
        
        # 自信レベルによる調整
        if confidence_level >= 4:
            base_score += 1
        elif confidence_level <= 2:
            base_score -= 1
        
        # 回答時間による調整（速すぎず遅すぎず）
        if 10 <= time_spent_seconds <= 120:  # 10秒-2分の範囲
            base_score += 1
        elif time_spent_seconds > 300:  # 5分以上は減点
            base_score -= 1
        
        return max(1, min(5, base_score))
    
    def get_review_statistics(self, student_id: int) -> Dict[str, Any]:
        """復習統計を取得"""
        try:
            # 最近30日の復習セット
            recent_cutoff = datetime.utcnow() - timedelta(days=30)
            
            recent_sets = ReviewSet.query.filter(
                and_(
                    ReviewSet.student_id == student_id,
                    ReviewSet.created_at >= recent_cutoff
                )
            ).all()
            
            if not recent_sets:
                return {
                    'total_review_sets': 0,
                    'total_problems_reviewed': 0,
                    'average_accuracy': 0.0,
                    'total_study_time_minutes': 0,
                    'review_streak_days': 0
                }
            
            # 統計計算
            total_sets = len(recent_sets)
            total_problems = sum(rs.total_problems for rs in recent_sets)
            
            # 正答率計算
            all_items = []
            total_time_seconds = 0
            
            for review_set in recent_sets:
                items = ReviewSetItem.query.filter_by(
                    review_set_id=review_set.id,
                    is_completed=True
                ).all()
                all_items.extend(items)
                total_time_seconds += sum(
                    item.time_spent_seconds or 0 for item in items
                )
            
            correct_items = sum(1 for item in all_items if item.is_correct)
            accuracy = correct_items / len(all_items) if all_items else 0.0
            
            # 連続復習日数を計算
            streak_days = self._calculate_review_streak(student_id)
            
            return {
                'total_review_sets': total_sets,
                'total_problems_reviewed': len(all_items),
                'average_accuracy': accuracy,
                'total_study_time_minutes': total_time_seconds // 60,
                'review_streak_days': streak_days,
                'recent_performance': {
                    'last_7_days': self._get_recent_performance(student_id, 7),
                    'last_30_days': self._get_recent_performance(student_id, 30)
                }
            }
            
        except Exception as e:
            logger.error(f"復習統計取得エラー: {str(e)}")
            return {}
    
    def _calculate_review_streak(self, student_id: int) -> int:
        """連続復習日数を計算"""
        try:
            # 最近の復習セット完了日を取得
            completed_sets = ReviewSet.query.filter(
                and_(
                    ReviewSet.student_id == student_id,
                    ReviewSet.status == 'completed'
                )
            ).order_by(desc(ReviewSet.created_at)).limit(30).all()
            
            if not completed_sets:
                return 0
            
            # 日付のセットを作成
            completion_dates = set()
            for review_set in completed_sets:
                completion_dates.add(review_set.created_at.date())
            
            # 連続日数を計算
            streak = 0
            current_date = datetime.utcnow().date()
            
            while current_date in completion_dates:
                streak += 1
                current_date -= timedelta(days=1)
            
            return streak
            
        except Exception:
            return 0
    
    def _get_recent_performance(self, student_id: int, days: int) -> Dict[str, Any]:
        """最近のパフォーマンスを取得"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            recent_items = db.session.query(ReviewSetItem).join(ReviewSet).filter(
                and_(
                    ReviewSet.student_id == student_id,
                    ReviewSetItem.is_completed == True,
                    ReviewSetItem.completed_at >= cutoff_date
                )
            ).all()
            
            if not recent_items:
                return {'problems_count': 0, 'accuracy': 0.0, 'avg_time_per_problem': 0}
            
            correct_count = sum(1 for item in recent_items if item.is_correct)
            total_time = sum(item.time_spent_seconds or 0 for item in recent_items)
            
            return {
                'problems_count': len(recent_items),
                'accuracy': correct_count / len(recent_items),
                'avg_time_per_problem': total_time / len(recent_items) if recent_items else 0
            }
            
        except Exception:
            return {'problems_count': 0, 'accuracy': 0.0, 'avg_time_per_problem': 0}