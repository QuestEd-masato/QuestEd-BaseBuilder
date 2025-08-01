# -*- coding: utf-8 -*-
"""
BaseBuilder Analytics Service

BaseBuilder統計専門サービス
Phase8E: student dashboard.pyから分離したBaseBuilder統合機能
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from flask import current_app
from flask_login import current_user
from sqlalchemy import func

from app.models import db

logger = logging.getLogger(__name__)

# BaseBuilderモデル（エラー保護）
try:
    from basebuilder.models import WordProficiency, AnswerRecord
    BASEBUILDER_AVAILABLE = True
except ImportError:
    logger.warning("BaseBuilder models not available")
    WordProficiency = None
    AnswerRecord = None
    BASEBUILDER_AVAILABLE = False


class BaseBuilderAnalyticsService:
    """BaseBuilder統計専門サービス"""

    def generate_vocabulary_stats(self, student_id: int) -> Dict[str, Any]:
        """
        語彙学習統計生成
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: 語彙学習統計
        """
        try:
            logger.info(f"Generating vocabulary stats for student {student_id}")
            
            if not BASEBUILDER_AVAILABLE:
                logger.warning("BaseBuilder not available, returning empty stats")
                return self._get_empty_basebuilder_stats()

            # 認証状態チェック
            if not current_user or not current_user.is_authenticated:
                logger.warning(f"User not authenticated, returning empty BaseBuilder stats")
                return self._get_empty_basebuilder_stats()

            # 基本語彙統計
            basic_stats = self._get_basic_vocabulary_stats(student_id)
            
            # 習熟度統計
            proficiency_stats = self.calculate_proficiency_breakdown(student_id)
            
            # 学習履歴統計
            learning_history = self._get_learning_history_stats(student_id)
            
            # 週間進捗統計
            weekly_progress = self.get_weekly_learning_metrics(student_id)
            
            # 統計統合
            vocabulary_stats = {
                **basic_stats,
                **proficiency_stats,
                **learning_history,
                **weekly_progress,
                "generated_at": datetime.now().isoformat()
            }
            
            return vocabulary_stats
            
        except Exception as e:
            logger.error(f"Error generating vocabulary stats for student {student_id}: {str(e)}")
            return self._get_empty_basebuilder_stats()

    def calculate_proficiency_breakdown(self, student_id: int) -> Dict[str, Any]:
        """
        熟練度内訳計算
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: 熟練度レベル別内訳
        """
        try:
            logger.info(f"Calculating proficiency breakdown for student {student_id}")
            
            if not BASEBUILDER_AVAILABLE or not WordProficiency:
                return {
                    "proficiency_breakdown": {
                        "level_5": 0, "level_4": 0, "level_3": 0,
                        "level_2": 0, "level_1": 0
                    },
                    "total_words_learned": 0
                }

            # WordProficiencyから熟練度分布を取得
            proficiency_records = WordProficiency.query.filter_by(student_id=student_id).all()
            
            breakdown = {
                "level_5": 0, "level_4": 0, "level_3": 0,
                "level_2": 0, "level_1": 0
            }
            
            total_words = 0
            for record in proficiency_records:
                level = record.level  # WordProficiencyモデルではlevelカラムを使用
                if 1 <= level <= 5:
                    breakdown[f"level_{level}"] += 1
                    total_words += 1

            # 習熟度分析
            mastery_analysis = self._analyze_mastery_distribution(breakdown, total_words)
            
            return {
                "proficiency_breakdown": breakdown,
                "total_words_learned": total_words,
                "mastery_analysis": mastery_analysis
            }
            
        except Exception as e:
            logger.error(f"Error calculating proficiency breakdown for student {student_id}: {str(e)}")
            return {
                "proficiency_breakdown": {"level_5": 0, "level_4": 0, "level_3": 0, "level_2": 0, "level_1": 0},
                "total_words_learned": 0
            }

    def get_weekly_learning_metrics(self, student_id: int) -> Dict[str, Any]:
        """
        週間学習メトリクス取得
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: 週間学習メトリクス
        """
        try:
            logger.info(f"Getting weekly learning metrics for student {student_id}")
            
            if not BASEBUILDER_AVAILABLE or not AnswerRecord:
                return {
                    "weekly_words_learned": 0,
                    "weekly_target": 20,
                    "achievement_rate": 0,
                    "daily_average": 0
                }

            # 週間学習データ取得
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            weekly_records = AnswerRecord.query.filter_by(
                student_id=student_id
            ).filter(
                AnswerRecord.created_at >= start_date,
                AnswerRecord.created_at <= end_date
            ).all()
            
            # 週間学習単語数（ユニーク）
            weekly_word_ids = set()
            correct_answers = 0
            total_attempts = len(weekly_records)
            
            for record in weekly_records:
                weekly_word_ids.add(record.problem_id)
                if record.is_correct:
                    correct_answers += 1
            
            weekly_words_learned = len(weekly_word_ids)
            weekly_target = 20  # 目標値
            achievement_rate = (weekly_words_learned / weekly_target * 100) if weekly_target > 0 else 0
            daily_average = weekly_words_learned / 7
            accuracy_rate = (correct_answers / total_attempts * 100) if total_attempts > 0 else 0
            
            # 学習パターン分析
            learning_pattern = self._analyze_weekly_learning_pattern(weekly_records)
            
            return {
                "weekly_words_learned": weekly_words_learned,
                "weekly_target": weekly_target,
                "achievement_rate": int(min(achievement_rate, 100)),  # 100%を上限（整数）
                "daily_average": daily_average,
                "accuracy_rate": int(accuracy_rate),
                "total_attempts": total_attempts,
                "learning_pattern": learning_pattern
            }
            
        except Exception as e:
            logger.error(f"Error getting weekly learning metrics for student {student_id}: {str(e)}")
            return {
                "weekly_words_learned": 0,
                "weekly_target": 20,
                "achievement_rate": 0,
                "daily_average": 0
            }

    def analyze_mastery_patterns(self, student_id: int) -> Dict[str, Any]:
        """
        習得パターン分析
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: 習得パターン分析結果
        """
        try:
            logger.info(f"Analyzing mastery patterns for student {student_id}")
            
            if not BASEBUILDER_AVAILABLE or not AnswerRecord:
                return {"patterns": [], "recommendations": []}

            # 回答記録から習得パターンを分析
            answer_records = AnswerRecord.query.filter_by(student_id=student_id).all()
            
            if not answer_records:
                return {"patterns": [], "recommendations": []}

            # 単語別習得パターン分析
            word_patterns = self._analyze_word_mastery_patterns(answer_records)
            
            # 時間帯別パフォーマンス分析
            time_patterns = self._analyze_time_based_patterns(answer_records)
            
            # 難易度別習得パターン
            difficulty_patterns = self._analyze_difficulty_patterns(answer_records)
            
            # 推奨事項生成
            recommendations = self._generate_mastery_recommendations(
                word_patterns, time_patterns, difficulty_patterns
            )
            
            return {
                "patterns": {
                    "word_mastery": word_patterns,
                    "time_based": time_patterns,
                    "difficulty_based": difficulty_patterns
                },
                "recommendations": recommendations,
                "analysis_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing mastery patterns for student {student_id}: {str(e)}")
            return {"patterns": [], "recommendations": []}

    def get_word_difficulty_analysis(self, student_id: int) -> Dict[str, Any]:
        """
        単語難易度分析
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: 単語難易度分析結果
        """
        try:
            logger.info(f"Getting word difficulty analysis for student {student_id}")
            
            if not BASEBUILDER_AVAILABLE or not AnswerRecord:
                return {"difficulty_levels": {}, "performance_by_level": {}}

            # 回答記録から難易度別パフォーマンス分析
            answer_records = AnswerRecord.query.filter_by(student_id=student_id).all()
            
            difficulty_analysis = {}
            
            for record in answer_records:
                # 単語の難易度を取得（仮実装：単語IDベース）
                difficulty = self._get_word_difficulty(record.problem_id)
                
                if difficulty not in difficulty_analysis:
                    difficulty_analysis[difficulty] = {
                        "total_attempts": 0,
                        "correct_attempts": 0,
                        "unique_words": set()
                    }
                
                difficulty_analysis[difficulty]["total_attempts"] += 1
                if record.is_correct:
                    difficulty_analysis[difficulty]["correct_attempts"] += 1
                difficulty_analysis[difficulty]["unique_words"].add(record.problem_id)
            
            # 統計計算
            performance_by_level = {}
            for difficulty, stats in difficulty_analysis.items():
                accuracy = (stats["correct_attempts"] / stats["total_attempts"] * 100) if stats["total_attempts"] > 0 else 0
                performance_by_level[difficulty] = {
                    "accuracy_rate": accuracy,
                    "total_attempts": stats["total_attempts"],
                    "unique_words_count": len(stats["unique_words"])
                }
            
            return {
                "difficulty_levels": list(difficulty_analysis.keys()),
                "performance_by_level": performance_by_level,
                "analysis_summary": self._generate_difficulty_summary(performance_by_level)
            }
            
        except Exception as e:
            logger.error(f"Error getting word difficulty analysis for student {student_id}: {str(e)}")
            return {"difficulty_levels": {}, "performance_by_level": {}}

    def _get_basic_vocabulary_stats(self, student_id: int) -> Dict[str, Any]:
        """基本語彙統計取得"""
        try:
            if not BASEBUILDER_AVAILABLE or not AnswerRecord:
                return {
                    "total_words_attempted": 0,
                    "total_mastered_words": 0,
                    "mastery_rate": 0,
                    "total_basic_words": 0
                }

            # 総挑戦単語数
            total_attempted = AnswerRecord.query.filter_by(student_id=student_id).count()
            
            # ユニーク問題数（単語数の代替）
            unique_words = db.session.query(
                func.count(func.distinct(AnswerRecord.problem_id))
            ).filter_by(student_id=student_id).scalar() or 0

            # 習得済み単語数計算
            mastered_words = self._calculate_mastered_words(student_id)
            
            # 習得率計算
            mastery_rate = (mastered_words / unique_words * 100) if unique_words > 0 else 0
            
            return {
                "total_words_attempted": total_attempted,
                "total_mastered_words": mastered_words,
                "mastery_rate": int(mastery_rate),
                "total_basic_words": unique_words
            }
            
        except Exception as e:
            logger.error(f"Error getting basic vocabulary stats: {str(e)}")
            return {
                "total_words_attempted": 0,
                "total_mastered_words": 0,
                "mastery_rate": 0,
                "total_basic_words": 0
            }

    def _get_learning_history_stats(self, student_id: int, days: int = 30) -> Dict[str, Any]:
        """学習履歴統計取得"""
        try:
            if not BASEBUILDER_AVAILABLE or not AnswerRecord:
                return {"learning_streak": 0, "total_study_days": 0}

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 日別学習統計
            daily_stats = (
                db.session.query(
                    func.date(AnswerRecord.created_at).label("date"),
                    func.count(AnswerRecord.id).label("answer_count")
                )
                .filter_by(student_id=student_id)
                .filter(
                    AnswerRecord.created_at >= start_date,
                    AnswerRecord.created_at <= end_date
                )
                .group_by(func.date(AnswerRecord.created_at))
                .all()
            )

            # 学習ストリーク計算
            learning_streak = self._calculate_learning_streak(daily_stats)
            
            return {
                "learning_streak": learning_streak,
                "total_study_days": len(daily_stats),
                "study_period_days": days
            }
            
        except Exception as e:
            logger.error(f"Error getting learning history stats: {str(e)}")
            return {"learning_streak": 0, "total_study_days": 0}

    def _calculate_mastered_words(self, student_id: int) -> int:
        """習得済み単語数計算"""
        try:
            if not AnswerRecord:
                return 0
                
            # 単語別統計計算
            answer_records = AnswerRecord.query.filter_by(student_id=student_id).all()
            word_stats = {}
            
            for record in answer_records:
                problem_id = record.problem_id
                if problem_id not in word_stats:
                    word_stats[problem_id] = {"total": 0, "correct": 0}
                
                word_stats[problem_id]["total"] += 1
                if record.is_correct:
                    word_stats[problem_id]["correct"] += 1

            # 習得基準：最低3回挑戦、80%以上正答
            mastered_count = 0
            for problem_id, stats in word_stats.items():
                if stats["total"] >= 3:
                    accuracy = stats["correct"] / stats["total"]
                    if accuracy >= 0.8:
                        mastered_count += 1
                        
            return mastered_count
            
        except Exception:
            return 0

    def _analyze_mastery_distribution(self, breakdown: Dict[str, int], total_words: int) -> Dict[str, Any]:
        """習熟度分布分析"""
        try:
            if total_words == 0:
                return {"dominant_level": None, "distribution_balance": "empty"}
            
            # 最多レベル特定
            max_count = max(breakdown.values())
            dominant_levels = [level for level, count in breakdown.items() if count == max_count]
            
            # 分布バランス評価
            high_levels = breakdown.get("level_5", 0) + breakdown.get("level_4", 0)
            balance = "high_proficiency" if high_levels > total_words * 0.6 else "balanced"
            
            return {
                "dominant_level": dominant_levels[0] if len(dominant_levels) == 1 else "mixed",
                "distribution_balance": balance,
                "high_proficiency_ratio": high_levels / total_words if total_words > 0 else 0
            }
            
        except Exception:
            return {"dominant_level": None, "distribution_balance": "unknown"}

    def _analyze_weekly_learning_pattern(self, weekly_records: List[Any]) -> Dict[str, Any]:
        """週間学習パターン分析"""
        try:
            if not weekly_records:
                return {"pattern_type": "inactive", "peak_times": []}
            
            # 日別分布
            daily_counts = {}
            for record in weekly_records:
                day = record.created_at.strftime("%A")
                daily_counts[day] = daily_counts.get(day, 0) + 1
            
            # ピーク時間帯分析
            peak_day = max(daily_counts.items(), key=lambda x: x[1])[0] if daily_counts else None
            
            return {
                "pattern_type": "consistent" if len(daily_counts) >= 5 else "sporadic",
                "peak_day": peak_day,
                "daily_distribution": daily_counts
            }
            
        except Exception:
            return {"pattern_type": "unknown", "peak_times": []}

    def _analyze_word_mastery_patterns(self, answer_records: List[Any]) -> Dict[str, Any]:
        """単語習得パターン分析"""
        try:
            word_stats = {}
            for record in answer_records:
                problem_id = record.problem_id
                if problem_id not in word_stats:
                    word_stats[problem_id] = {"attempts": 0, "correct": 0, "first_attempt": record.created_at}
                
                word_stats[problem_id]["attempts"] += 1
                if record.is_correct:
                    word_stats[problem_id]["correct"] += 1
            
            # 習得パターン分類
            quick_learners = sum(1 for stats in word_stats.values() 
                               if stats["attempts"] <= 3 and stats["correct"] / stats["attempts"] >= 0.8)
            
            return {
                "total_words_studied": len(word_stats),
                "quick_mastery_count": quick_learners,
                "average_attempts_per_word": sum(s["attempts"] for s in word_stats.values()) / len(word_stats) if word_stats else 0
            }
            
        except Exception:
            return {"total_words_studied": 0, "quick_mastery_count": 0}

    def _analyze_time_based_patterns(self, answer_records: List[Any]) -> Dict[str, Any]:  
        """時間ベースパターン分析"""
        try:
            hour_stats = {}
            for record in answer_records:
                hour = record.created_at.hour
                if hour not in hour_stats:
                    hour_stats[hour] = {"total": 0, "correct": 0}
                
                hour_stats[hour]["total"] += 1
                if record.is_correct:
                    hour_stats[hour]["correct"] += 1
            
            # ベストパフォーマンス時間帯
            best_hour = None
            best_accuracy = 0
            for hour, stats in hour_stats.items():
                if stats["total"] >= 5:  # 最低5回の試行
                    accuracy = stats["correct"] / stats["total"]
                    if accuracy > best_accuracy:
                        best_accuracy = accuracy
                        best_hour = hour
            
            return {
                "best_performance_hour": best_hour,
                "best_accuracy": best_accuracy,
                "active_hours": list(hour_stats.keys())
            }
            
        except Exception:
            return {"best_performance_hour": None, "best_accuracy": 0}

    def _analyze_difficulty_patterns(self, answer_records: List[Any]) -> Dict[str, Any]:
        """難易度パターン分析"""
        try:
            difficulty_stats = {}
            for record in answer_records:
                difficulty = self._get_word_difficulty(record.problem_id)
                if difficulty not in difficulty_stats:
                    difficulty_stats[difficulty] = {"total": 0, "correct": 0}
                
                difficulty_stats[difficulty]["total"] += 1
                if record.is_correct:
                    difficulty_stats[difficulty]["correct"] += 1
            
            # 得意・苦手難易度特定
            strengths = []
            weaknesses = []
            for difficulty, stats in difficulty_stats.items():
                if stats["total"] >= 5:
                    accuracy = stats["correct"] / stats["total"]
                    if accuracy >= 0.8:
                        strengths.append(difficulty)
                    elif accuracy <= 0.5:
                        weaknesses.append(difficulty)
            
            return {
                "strength_levels": strengths,
                "weakness_levels": weaknesses,
                "difficulty_distribution": difficulty_stats
            }
            
        except Exception:
            return {"strength_levels": [], "weakness_levels": []}

    def _generate_mastery_recommendations(self, word_patterns: Dict, time_patterns: Dict, difficulty_patterns: Dict) -> List[str]:
        """習得推奨事項生成"""
        recommendations = []
        try:
            # 時間ベース推奨
            if time_patterns.get("best_performance_hour"):
                recommendations.append(f"{time_patterns['best_performance_hour']}時頃の学習が効果的です")
            
            # 難易度ベース推奨
            if difficulty_patterns.get("weakness_levels"):
                recommendations.append(f"難易度{difficulty_patterns['weakness_levels']}の単語に重点を置きましょう")
            
            # 学習量ベース推奨
            avg_attempts = word_patterns.get("average_attempts_per_word", 0)
            if avg_attempts > 5:
                recommendations.append("復習頻度を上げて記憶の定着を図りましょう")
                
        except Exception:
            pass
        
        return recommendations

    def _get_word_difficulty(self, problem_id: int) -> str:
        """単語難易度取得（簡易実装）"""
        try:
            # 実際の実装では単語データベースから取得
            if problem_id % 4 == 0:
                return "beginner"
            elif problem_id % 4 == 1:
                return "intermediate"
            elif problem_id % 4 == 2:
                return "advanced"
            else:
                return "expert"
        except Exception:
            return "unknown"

    def _generate_difficulty_summary(self, performance_by_level: Dict) -> Dict[str, Any]:
        """難易度サマリー生成"""
        try:
            if not performance_by_level:
                return {"overall_trend": "no_data"}
            
            # 平均正答率計算
            total_accuracy = sum(stats["accuracy_rate"] for stats in performance_by_level.values())
            avg_accuracy = total_accuracy / len(performance_by_level)
            
            # トレンド分析
            trend = "improving" if avg_accuracy > 70 else "needs_improvement"
            
            return {
                "overall_trend": trend,
                "average_accuracy": avg_accuracy,
                "levels_analyzed": len(performance_by_level)
            }
            
        except Exception:
            return {"overall_trend": "unknown"}

    def _calculate_learning_streak(self, daily_stats: List[Any]) -> int:
        """学習ストリーク計算"""
        try:
            if not daily_stats:
                return 0
            
            # 連続学習日数計算（簡易実装）
            return min(len(daily_stats), 30)  # 最大30日
            
        except Exception:
            return 0

    def _get_empty_basebuilder_stats(self) -> Dict[str, Any]:
        """空のBaseBuilder統計"""
        return {
            "total_words_attempted": 0,
            "total_mastered_words": 0,
            "mastery_rate": 0,
            "weekly_words_learned": 0,
            "weekly_target": 20,
            "total_basic_words": 0,
            "proficiency_breakdown": {
                "level_5": 0, "level_4": 0, "level_3": 0,
                "level_2": 0, "level_1": 0
            },
            "learning_streak": 0,
            "basebuilder_available": False
        }

    # =============================================================================
    # 統合メソッド: BaseBuilderIntegrationService互換性
    # Phase8統合: 重複排除のため、IntegrationServiceのメソッドをサポート
    # =============================================================================
    
    def generate_basebuilder_statistics(self, student_id: int) -> Dict[str, Any]:
        """
        BaseBuilder統計を生成（IntegrationService互換）
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: BaseBuilder統計
        """
        # 既存のgenerate_vocabulary_statsメソッドを使用
        return self.generate_vocabulary_stats(student_id)
    
    def calculate_mastery_rates(self, student_id: int) -> Dict[str, Any]:
        """
        習熟度を計算（IntegrationService互換）
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: 習熟度統計
        """
        try:
            if not BASEBUILDER_AVAILABLE or not AnswerRecord:
                return {"mastery_rate": 0, "total_mastered_words": 0}

            # 回答記録から習熟度計算
            answer_records = AnswerRecord.query.filter_by(student_id=student_id).all()
            
            if not answer_records:
                return {"mastery_rate": 0, "total_mastered_words": 0}

            total_answers = len(answer_records)
            correct_answers = len([r for r in answer_records if r.is_correct])
            
            mastery_rate = (correct_answers / total_answers * 100) if total_answers > 0 else 0

            # 習得済み単語数（正答率80%以上と仮定）
            word_stats = {}
            for record in answer_records:
                problem_id = record.problem_id
                if problem_id not in word_stats:
                    word_stats[problem_id] = {"total": 0, "correct": 0}
                
                word_stats[problem_id]["total"] += 1
                if record.is_correct:
                    word_stats[problem_id]["correct"] += 1

            mastered_words = 0
            for problem_id, stats in word_stats.items():
                if stats["total"] >= 3:  # 最低3回挑戦
                    word_mastery_rate = stats["correct"] / stats["total"]
                    if word_mastery_rate >= 0.8:  # 80%以上正答
                        mastered_words += 1

            return {
                "mastery_rate": int(mastery_rate),
                "total_mastered_words": mastered_words,
                "total_answers": total_answers,
                "correct_answers": correct_answers
            }

        except Exception as e:
            logger.error(f"Mastery rates calculation error for student {student_id}: {str(e)}")
            return {"mastery_rate": 0, "total_mastered_words": 0}
    
    def calculate_weekly_progress(self, student_id: int) -> Dict[str, Any]:
        """
        週間進捗を計算（IntegrationService互換）
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: 週間進捗統計
        """
        # 既存のget_weekly_learning_metricsメソッドを使用し、形式を調整
        weekly_metrics = self.get_weekly_learning_metrics(student_id)
        
        return {
            "weekly_words_learned": weekly_metrics.get("weekly_words_learned", 0),
            "weekly_target": weekly_metrics.get("weekly_target", 20),
            "weekly_achievement_rate": weekly_metrics.get("achievement_rate", 0)
        }

    def get_proficiency_breakdown(self, student_id: int) -> Dict[str, int]:
        """
        熟練度内訳を取得（IntegrationService互換）
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: 熟練度レベル別内訳
        """
        # 既存のcalculate_proficiency_breakdownメソッドを使用し、形式を調整
        proficiency_data = self.calculate_proficiency_breakdown(student_id)
        
        return proficiency_data.get("proficiency_breakdown", {
            "level_5": 0, "level_4": 0, "level_3": 0,
            "level_2": 0, "level_1": 0
        })

    def generate_teacher_basebuilder_summary(self, teacher_id: int, class_ids: List[int]) -> Dict[str, Any]:
        """
        教師向けBaseBuilderサマリー生成（IntegrationService互換）
        
        Args:
            teacher_id: 教師ID
            class_ids: クラスIDリスト
            
        Returns:
            Dict: 教師向けBaseBuilderサマリー
        """
        try:
            logger.info(f"Generating teacher BaseBuilder summary for teacher {teacher_id}")
            
            if not BASEBUILDER_AVAILABLE:
                return {
                    "total_students": 0,
                    "average_mastery_rate": 0,
                    "total_words_learned": 0,
                    "active_students": 0
                }

            # クラスの学生一覧を取得（簡略実装）
            from app.models import ClassEnrollment
            students = ClassEnrollment.query.filter(
                ClassEnrollment.class_id.in_(class_ids)
            ).all()
            
            if not students:
                return {
                    "total_students": 0,
                    "average_mastery_rate": 0,
                    "total_words_learned": 0,
                    "active_students": 0
                }

            # 各学生の統計を集計
            total_mastery_rate = 0
            total_words_learned = 0
            active_students = 0
            
            for student in students:
                student_stats = self.generate_vocabulary_stats(student.student_id)
                if student_stats.get("total_words_attempted", 0) > 0:
                    active_students += 1
                    total_mastery_rate += student_stats.get("mastery_rate", 0)
                    total_words_learned += student_stats.get("total_mastered_words", 0)
            
            average_mastery_rate = (total_mastery_rate / active_students) if active_students > 0 else 0
            
            return {
                "total_students": len(students),
                "average_mastery_rate": int(average_mastery_rate),
                "total_words_learned": total_words_learned,
                "active_students": active_students
            }

        except Exception as e:
            logger.error(f"Error generating teacher BaseBuilder summary: {str(e)}")
            return {
                "total_students": 0,
                "average_mastery_rate": 0,
                "total_words_learned": 0,
                "active_students": 0
            }

    def get_service_status(self) -> Dict[str, Any]:
        """サービス状態取得"""
        return {
            "service_name": "BaseBuilderAnalyticsService",
            "status": "active",
            "version": "1.0.0",
            "basebuilder_available": BASEBUILDER_AVAILABLE,
            "integration_compatible": True,  # IntegrationService互換
            "capabilities": [
                "vocabulary_statistics_generation",
                "proficiency_breakdown_calculation",
                "weekly_learning_metrics",
                "mastery_pattern_analysis",
                "word_difficulty_analysis",
                # IntegrationService互換メソッド
                "generate_basebuilder_statistics",
                "calculate_mastery_rates", 
                "calculate_weekly_progress",
                "get_proficiency_breakdown",
                "generate_teacher_basebuilder_summary"
            ]
        }