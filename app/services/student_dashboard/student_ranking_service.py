# -*- coding: utf-8 -*-
"""
Student Ranking Service

学生ランキング専門サービス
Phase8E: student dashboard.pyから分離したランキング計算機能
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from flask import current_app
from flask_login import current_user
from sqlalchemy import func, desc

from app.models import User, ClassEnrollment, ActivityLog, Goal, Todo, db

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

# レッスンシステムモデル（エラー保護）
try:
    from app.modules.lesson_system.models.lesson_models import StudentLessonProgress
    LESSON_SYSTEM_AVAILABLE = True
except ImportError:
    logger.warning("Lesson system models not available")
    StudentLessonProgress = None
    LESSON_SYSTEM_AVAILABLE = False


class StudentRankingService:
    """学生ランキング専門サービス"""

    def get_class_top_learners(self, class_ids: List[int], limit: int = 10) -> List[Dict[str, Any]]:
        """
        クラス内トップ学習者取得
        
        Args:
            class_ids: クラスIDリスト
            limit: 取得件数制限
            
        Returns:
            List[Dict]: クラス内トップ学習者リスト
        """
        try:
            logger.info(f"Getting class top learners for classes {class_ids}")
            
            if not class_ids:
                return []

            # クラス所属学生取得
            enrollments = ClassEnrollment.query.filter(
                ClassEnrollment.class_id.in_(class_ids)
            ).all()
            
            student_ids = [e.student_id for e in enrollments]
            
            if not student_ids:
                return []

            # 学習者スコア計算
            learner_scores = self._calculate_learner_scores(student_ids)
            
            # トップ学習者抽出
            top_learners = sorted(
                learner_scores.items(), 
                key=lambda x: x[1]["total_score"], 
                reverse=True
            )[:limit]
            
            # 学習者詳細情報構築
            top_learners_details = []
            for student_id, score_data in top_learners:
                student = User.query.get(student_id)
                if student:
                    learner_info = {
                        "rank": len(top_learners_details) + 1,
                        "student_id": student_id,
                        "username": student.username,
                        "display_name": getattr(student, "display_name", student.username),
                        "total_score": score_data["total_score"],
                        "activity_score": score_data["activity_score"],
                        "completion_score": score_data["completion_score"],
                        "basebuilder_score": score_data.get("basebuilder_score", 0),
                        "lesson_score": score_data.get("lesson_score", 0),
                        "class_id": self._get_student_primary_class(student_id, class_ids)
                    }
                    top_learners_details.append(learner_info)
            
            return top_learners_details
            
        except Exception as e:
            logger.error(f"Error getting class top learners: {str(e)}")
            return []

    def get_weekly_top_learners(self, class_ids: List[int], limit: int = 10) -> List[Dict[str, Any]]:
        """
        週間トップ学習者取得
        
        Args:
            class_ids: クラスIDリスト  
            limit: 取得件数制限
            
        Returns:
            List[Dict]: 週間トップ学習者リスト
        """
        try:
            logger.info(f"Getting weekly top learners for classes {class_ids}")
            
            if not class_ids:
                return []

            # 週間期間設定
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            # クラス所属学生取得
            enrollments = ClassEnrollment.query.filter(
                ClassEnrollment.class_id.in_(class_ids)
            ).all()
            
            student_ids = [e.student_id for e in enrollments]
            
            if not student_ids:
                return []

            # 週間学習スコア計算
            weekly_scores = self._calculate_weekly_scores(student_ids, start_date, end_date)
            
            # 週間トップ学習者抽出
            weekly_top_learners = sorted(
                weekly_scores.items(),
                key=lambda x: x[1]["weekly_total_score"],
                reverse=True
            )[:limit]
            
            # 週間学習者詳細情報構築
            weekly_learners_details = []
            for student_id, score_data in weekly_top_learners:
                student = User.query.get(student_id)
                if student:
                    learner_info = {
                        "rank": len(weekly_learners_details) + 1,
                        "student_id": student_id,
                        "username": student.username,
                        "display_name": getattr(student, "display_name", student.username),
                        "weekly_total_score": score_data["weekly_total_score"],
                        "weekly_activities": score_data["weekly_activities"],
                        "weekly_completions": score_data["weekly_completions"],
                        "weekly_basebuilder": score_data.get("weekly_basebuilder", 0),
                        "improvement_rate": score_data.get("improvement_rate", 0),
                        "class_id": self._get_student_primary_class(student_id, class_ids)
                    }
                    weekly_learners_details.append(learner_info)
            
            return weekly_learners_details
            
        except Exception as e:
            logger.error(f"Error getting weekly top learners: {str(e)}")
            return []

    def calculate_ranking_metrics(self, student_id: int) -> Dict[str, Any]:
        """
        学生のランキングメトリクス計算
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: ランキングメトリクス
        """
        try:
            logger.info(f"Calculating ranking metrics for student {student_id}")
            
            # 学生の所属クラス取得
            enrollments = ClassEnrollment.query.filter_by(student_id=student_id).all()
            class_ids = [e.class_id for e in enrollments]
            
            if not class_ids:
                return self._get_empty_ranking_metrics()

            # 同じクラスの学生取得
            peer_students = self._get_peer_students(class_ids, exclude_student_id=student_id)
            
            # 自分のスコア計算
            my_scores = self._calculate_learner_scores([student_id])
            my_total_score = my_scores.get(student_id, {}).get("total_score", 0)
            
            # 同級生のスコア計算
            peer_scores = self._calculate_learner_scores(peer_students)
            
            # ランキング計算
            all_scores = list(peer_scores.values()) + [my_scores.get(student_id, {})]
            all_scores_sorted = sorted(all_scores, key=lambda x: x.get("total_score", 0), reverse=True)
            
            # 自分の順位特定
            my_rank = None
            for i, score_data in enumerate(all_scores_sorted):
                if score_data.get("total_score", 0) == my_total_score:
                    my_rank = i + 1
                    break
            
            # 週間ランキング
            weekly_metrics = self._calculate_weekly_ranking_metrics(student_id, class_ids)
            
            ranking_metrics = {
                "overall_rank": my_rank or len(all_scores_sorted),
                "total_participants": len(all_scores_sorted),
                "percentile": self._calculate_percentile(my_rank, len(all_scores_sorted)) if my_rank else 0,
                "my_total_score": my_total_score,
                "class_average_score": sum(s.get("total_score", 0) for s in all_scores_sorted) / len(all_scores_sorted) if all_scores_sorted else 0,
                "score_above_average": my_total_score > (sum(s.get("total_score", 0) for s in all_scores_sorted) / len(all_scores_sorted)) if all_scores_sorted else False,
                **weekly_metrics,
                "calculated_at": datetime.now().isoformat()
            }
            
            return ranking_metrics
            
        except Exception as e:
            logger.error(f"Error calculating ranking metrics for student {student_id}: {str(e)}")
            return self._get_empty_ranking_metrics()

    def get_peer_comparison_data(self, student_id: int) -> Dict[str, Any]:
        """
        同級生比較データ取得
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: 同級生比較データ
        """
        try:
            logger.info(f"Getting peer comparison data for student {student_id}")
            
            # 学生の所属クラス取得
            enrollments = ClassEnrollment.query.filter_by(student_id=student_id).all()
            class_ids = [e.class_id for e in enrollments]
            
            if not class_ids:
                return {"comparison_data": {}, "peer_count": 0}

            # 同級生取得
            peer_students = self._get_peer_students(class_ids, exclude_student_id=student_id)
            
            # 自分と同級生のパフォーマンス比較
            my_performance = self._get_detailed_performance(student_id)
            peer_performances = [self._get_detailed_performance(peer_id) for peer_id in peer_students]
            
            # 比較分析
            comparison_data = {
                "activity_comparison": self._compare_activities(my_performance, peer_performances),
                "completion_comparison": self._compare_completions(my_performance, peer_performances),
                "basebuilder_comparison": self._compare_basebuilder(my_performance, peer_performances),
                "learning_pace_comparison": self._compare_learning_pace(my_performance, peer_performances),
                "strength_areas": self._identify_strength_areas(my_performance, peer_performances),
                "improvement_areas": self._identify_improvement_areas(my_performance, peer_performances)
            }
            
            return {
                "comparison_data": comparison_data,
                "peer_count": len(peer_students),
                "my_performance": my_performance,
                "comparison_summary": self._generate_comparison_summary(comparison_data)
            }
            
        except Exception as e:
            logger.error(f"Error getting peer comparison data for student {student_id}: {str(e)}")
            return {"comparison_data": {}, "peer_count": 0}

    def generate_activity_rankings(self, class_ids: List[int]) -> Dict[str, Any]:
        """
        活動ランキング生成
        
        Args:
            class_ids: クラスIDリスト
            
        Returns:
            Dict: 活動ランキングデータ
        """
        try:
            logger.info(f"Generating activity rankings for classes {class_ids}")
            
            if not class_ids:
                return {"rankings": {}, "statistics": {}}

            # クラス所属学生取得
            enrollments = ClassEnrollment.query.filter(
                ClassEnrollment.class_id.in_(class_ids)
            ).all()
            
            student_ids = [e.student_id for e in enrollments]
            
            if not student_ids:
                return {"rankings": {}, "statistics": {}}

            # 各種活動ランキング生成
            activity_rankings = {
                "most_active_students": self._get_most_active_students(student_ids),
                "highest_completion_rate": self._get_highest_completion_students(student_ids),
                "most_improved_students": self._get_most_improved_students(student_ids),
                "consistent_learners": self._get_consistent_learners(student_ids),
                "basebuilder_champions": self._get_basebuilder_champions(student_ids) if BASEBUILDER_AVAILABLE else []
            }
            
            # 統計情報
            statistics = {
                "total_students": len(student_ids),
                "active_students_this_week": self._count_active_students_this_week(student_ids),
                "average_activity_per_student": self._calculate_average_activity(student_ids),
                "class_completion_rate": self._calculate_class_completion_rate(student_ids)
            }
            
            return {
                "rankings": activity_rankings,
                "statistics": statistics,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating activity rankings: {str(e)}")
            return {"rankings": {}, "statistics": {}}

    def _calculate_learner_scores(self, student_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """学習者スコア計算"""
        try:
            learner_scores = {}
            
            for student_id in student_ids:
                # 活動スコア
                activity_score = self._calculate_activity_score(student_id)
                
                # 完了スコア
                completion_score = self._calculate_completion_score(student_id)
                
                # BaseBuilderスコア
                basebuilder_score = self._calculate_basebuilder_score(student_id) if BASEBUILDER_AVAILABLE else 0
                
                # レッスンスコア
                lesson_score = self._calculate_lesson_score(student_id) if LESSON_SYSTEM_AVAILABLE else 0
                
                # 総合スコア
                total_score = activity_score + completion_score + basebuilder_score + lesson_score
                
                learner_scores[student_id] = {
                    "total_score": total_score,
                    "activity_score": activity_score,
                    "completion_score": completion_score,
                    "basebuilder_score": basebuilder_score,
                    "lesson_score": lesson_score
                }
            
            return learner_scores
            
        except Exception as e:
            logger.error(f"Error calculating learner scores: {str(e)}")
            return {}

    def _calculate_weekly_scores(self, student_ids: List[int], start_date: datetime, end_date: datetime) -> Dict[int, Dict[str, Any]]:
        """週間スコア計算"""
        try:
            weekly_scores = {}
            
            for student_id in student_ids:
                # 週間活動数
                weekly_activities = ActivityLog.query.filter_by(
                    student_id=student_id
                ).filter(
                    ActivityLog.created_at >= start_date,
                    ActivityLog.created_at <= end_date
                ).count()
                
                # 週間完了数
                weekly_completions = self._count_weekly_completions(student_id, start_date, end_date)
                
                # 週間BaseBuilder活動
                weekly_basebuilder = self._count_weekly_basebuilder(student_id, start_date, end_date) if BASEBUILDER_AVAILABLE else 0
                
                # 週間総合スコア
                weekly_total_score = (weekly_activities * 1) + (weekly_completions * 5) + (weekly_basebuilder * 2)
                
                # 改善率計算
                improvement_rate = self._calculate_improvement_rate(student_id, start_date, end_date)
                
                weekly_scores[student_id] = {
                    "weekly_total_score": weekly_total_score,
                    "weekly_activities": weekly_activities,
                    "weekly_completions": weekly_completions,
                    "weekly_basebuilder": weekly_basebuilder,
                    "improvement_rate": improvement_rate
                }
            
            return weekly_scores
            
        except Exception as e:
            logger.error(f"Error calculating weekly scores: {str(e)}")
            return {}

    def _calculate_activity_score(self, student_id: int) -> int:
        """活動スコア計算"""
        try:
            # 総活動数
            total_activities = ActivityLog.query.filter_by(student_id=student_id).count()
            
            # 最近30日の活動
            recent_date = datetime.now() - timedelta(days=30)
            recent_activities = ActivityLog.query.filter_by(
                student_id=student_id
            ).filter(ActivityLog.created_at >= recent_date).count()
            
            # スコア計算（総活動 + 最近の活動ボーナス）
            return total_activities + (recent_activities * 2)
            
        except Exception:
            return 0

    def _calculate_completion_score(self, student_id: int) -> int:
        """完了スコア計算"""
        try:
            # Todo完了数
            completed_todos = Todo.query.filter_by(
                student_id=student_id, is_completed=True
            ).count()
            
            # Goal完了数
            completed_goals = Goal.query.filter_by(
                student_id=student_id, is_completed=True
            ).count()
            
            # スコア計算
            return (completed_todos * 2) + (completed_goals * 5)
            
        except Exception:
            return 0

    def _calculate_basebuilder_score(self, student_id: int) -> int:
        """BaseBuilderスコア計算"""
        try:
            if not BASEBUILDER_AVAILABLE or not AnswerRecord:
                return 0
            
            # 正答数
            correct_answers = AnswerRecord.query.filter_by(
                student_id=student_id, is_correct=True
            ).count()
            
            # 習熟度レベル
            mastery_levels = WordProficiency.query.filter_by(
                student_id=student_id
            ).count() if WordProficiency else 0
            
            return (correct_answers * 1) + (mastery_levels * 3)
            
        except Exception:
            return 0

    def _calculate_lesson_score(self, student_id: int) -> int:
        """レッスンスコア計算"""
        try:
            if not LESSON_SYSTEM_AVAILABLE or not StudentLessonProgress:
                return 0
            
            # 承認済みレッスン数
            approved_lessons = StudentLessonProgress.query.filter_by(
                student_id=student_id, approval_status='approved'
            ).count()
            
            return approved_lessons * 10
            
        except Exception:
            return 0

    def _get_student_primary_class(self, student_id: int, class_ids: List[int]) -> Optional[int]:
        """学生の主要クラス取得"""
        try:
            enrollment = ClassEnrollment.query.filter_by(
                student_id=student_id
            ).filter(
                ClassEnrollment.class_id.in_(class_ids)
            ).first()
            
            return enrollment.class_id if enrollment else None
            
        except Exception:
            return None

    def _calculate_weekly_ranking_metrics(self, student_id: int, class_ids: List[int]) -> Dict[str, Any]:
        """週間ランキングメトリクス計算"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            # 週間スコア計算
            weekly_scores = self._calculate_weekly_scores([student_id], start_date, end_date)
            my_weekly_score = weekly_scores.get(student_id, {}).get("weekly_total_score", 0)
            
            # 同級生の週間スコア
            peer_students = self._get_peer_students(class_ids, exclude_student_id=student_id)
            peer_weekly_scores = self._calculate_weekly_scores(peer_students, start_date, end_date)
            
            # 週間ランキング計算
            all_weekly_scores = [score_data["weekly_total_score"] for score_data in peer_weekly_scores.values()]
            all_weekly_scores.append(my_weekly_score)
            all_weekly_scores.sort(reverse=True)
            
            weekly_rank = all_weekly_scores.index(my_weekly_score) + 1 if my_weekly_score in all_weekly_scores else len(all_weekly_scores)
            
            return {
                "weekly_rank": weekly_rank,
                "weekly_total_score": my_weekly_score,
                "weekly_participants": len(all_weekly_scores),
                "weekly_percentile": self._calculate_percentile(weekly_rank, len(all_weekly_scores))
            }
            
        except Exception:
            return {"weekly_rank": 0, "weekly_total_score": 0}

    def _get_peer_students(self, class_ids: List[int], exclude_student_id: int) -> List[int]:
        """同級生取得"""
        try:
            enrollments = ClassEnrollment.query.filter(
                ClassEnrollment.class_id.in_(class_ids),
                ClassEnrollment.student_id != exclude_student_id
            ).all()
            
            return [e.student_id for e in enrollments]
            
        except Exception:
            return []

    def _get_detailed_performance(self, student_id: int) -> Dict[str, Any]:
        """詳細パフォーマンス取得"""
        try:
            # 各種パフォーマンス指標
            return {
                "total_activities": ActivityLog.query.filter_by(student_id=student_id).count(),
                "completed_todos": Todo.query.filter_by(student_id=student_id, is_completed=True).count(),
                "completed_goals": Goal.query.filter_by(student_id=student_id, is_completed=True).count(),
                "basebuilder_score": self._calculate_basebuilder_score(student_id),
                "lesson_score": self._calculate_lesson_score(student_id),
                "recent_activity_count": self._get_recent_activity_count(student_id)
            }
            
        except Exception:
            return {}

    def _compare_activities(self, my_performance: Dict, peer_performances: List[Dict]) -> Dict[str, Any]:
        """活動比較"""
        try:
            my_activities = my_performance.get("total_activities", 0)
            peer_activities = [p.get("total_activities", 0) for p in peer_performances if p]
            
            if not peer_activities:
                return {"comparison_result": "no_peers", "percentile": 0}
            
            peer_average = sum(peer_activities) / len(peer_activities)
            above_average = my_activities > peer_average
            percentile = len([a for a in peer_activities if my_activities > a]) / len(peer_activities) * 100
            
            return {
                "my_activities": my_activities,
                "peer_average": peer_average,
                "above_average": above_average,
                "percentile": percentile,
                "comparison_result": "above_average" if above_average else "below_average"
            }
            
        except Exception:
            return {"comparison_result": "error", "percentile": 0}

    def _compare_completions(self, my_performance: Dict, peer_performances: List[Dict]) -> Dict[str, Any]:
        """完了比較"""
        try:
            my_completions = my_performance.get("completed_todos", 0) + my_performance.get("completed_goals", 0)
            peer_completions = [(p.get("completed_todos", 0) + p.get("completed_goals", 0)) for p in peer_performances if p]
            
            if not peer_completions:
                return {"comparison_result": "no_peers", "percentile": 0}
            
            peer_average = sum(peer_completions) / len(peer_completions)
            above_average = my_completions > peer_average
            percentile = len([c for c in peer_completions if my_completions > c]) / len(peer_completions) * 100
            
            return {
                "my_completions": my_completions,
                "peer_average": peer_average,
                "above_average": above_average,
                "percentile": percentile,
                "comparison_result": "above_average" if above_average else "below_average"
            }
            
        except Exception:
            return {"comparison_result": "error", "percentile": 0}

    def _compare_basebuilder(self, my_performance: Dict, peer_performances: List[Dict]) -> Dict[str, Any]:
        """BaseBuilder比較"""
        try:
            my_basebuilder = my_performance.get("basebuilder_score", 0)
            peer_basebuilder = [p.get("basebuilder_score", 0) for p in peer_performances if p]
            
            if not peer_basebuilder:
                return {"comparison_result": "no_peers", "percentile": 0}
            
            peer_average = sum(peer_basebuilder) / len(peer_basebuilder)
            above_average = my_basebuilder > peer_average
            percentile = len([b for b in peer_basebuilder if my_basebuilder > b]) / len(peer_basebuilder) * 100
            
            return {
                "my_basebuilder_score": my_basebuilder,
                "peer_average": peer_average,
                "above_average": above_average,
                "percentile": percentile,
                "comparison_result": "above_average" if above_average else "below_average"
            }
            
        except Exception:
            return {"comparison_result": "error", "percentile": 0}

    def _compare_learning_pace(self, my_performance: Dict, peer_performances: List[Dict]) -> Dict[str, Any]:
        """学習ペース比較"""
        try:
            my_recent = my_performance.get("recent_activity_count", 0)
            peer_recent = [p.get("recent_activity_count", 0) for p in peer_performances if p]
            
            if not peer_recent:
                return {"comparison_result": "no_peers", "pace_level": "unknown"}
            
            peer_average = sum(peer_recent) / len(peer_recent)
            
            if my_recent > peer_average * 1.5:
                pace_level = "fast"
            elif my_recent > peer_average * 0.8:
                pace_level = "average"
            else:
                pace_level = "slow"
            
            return {
                "my_recent_activities": my_recent,
                "peer_average": peer_average,
                "pace_level": pace_level,
                "comparison_result": f"learning_pace_{pace_level}"
            }
            
        except Exception:
            return {"comparison_result": "error", "pace_level": "unknown"}

    def _identify_strength_areas(self, my_performance: Dict, peer_performances: List[Dict]) -> List[str]:
        """強み領域特定"""
        strengths = []
        try:
            comparisons = {
                "activities": self._compare_activities(my_performance, peer_performances),
                "completions": self._compare_completions(my_performance, peer_performances),
                "basebuilder": self._compare_basebuilder(my_performance, peer_performances)
            }
            
            for area, comparison in comparisons.items():
                if comparison.get("above_average", False) and comparison.get("percentile", 0) > 70:
                    strengths.append(area)
                    
        except Exception:
            pass
        
        return strengths

    def _identify_improvement_areas(self, my_performance: Dict, peer_performances: List[Dict]) -> List[str]:
        """改善領域特定"""
        improvements = []
        try:
            comparisons = {
                "activities": self._compare_activities(my_performance, peer_performances),
                "completions": self._compare_completions(my_performance, peer_performances),
                "basebuilder": self._compare_basebuilder(my_performance, peer_performances)
            }
            
            for area, comparison in comparisons.items():
                if not comparison.get("above_average", True) and comparison.get("percentile", 100) < 30:
                    improvements.append(area)
                    
        except Exception:
            pass
        
        return improvements

    def _generate_comparison_summary(self, comparison_data: Dict) -> Dict[str, Any]:
        """比較サマリー生成"""
        try:
            strengths = comparison_data.get("strength_areas", [])
            improvements = comparison_data.get("improvement_areas", [])
            
            if len(strengths) > len(improvements):
                overall_performance = "above_average"
            elif len(improvements) > len(strengths):
                overall_performance = "below_average"
            else:
                overall_performance = "average"
            
            return {
                "overall_performance": overall_performance,
                "strength_count": len(strengths),
                "improvement_count": len(improvements),
                "primary_strength": strengths[0] if strengths else None,
                "primary_improvement": improvements[0] if improvements else None
            }
            
        except Exception:
            return {"overall_performance": "unknown"}

    def _count_weekly_completions(self, student_id: int, start_date: datetime, end_date: datetime) -> int:
        """週間完了数カウント"""
        try:
            # Todo完了
            todo_completions = Todo.query.filter_by(
                student_id=student_id, is_completed=True
            ).filter(
                Todo.updated_at >= start_date,
                Todo.updated_at <= end_date
            ).count()
            
            # Goal完了
            goal_completions = Goal.query.filter_by(
                student_id=student_id, is_completed=True
            ).filter(
                Goal.updated_at >= start_date,
                Goal.updated_at <= end_date
            ).count()
            
            return todo_completions + goal_completions
            
        except Exception:
            return 0

    def _count_weekly_basebuilder(self, student_id: int, start_date: datetime, end_date: datetime) -> int:
        """週間BaseBuilder活動カウント"""
        try:
            if not BASEBUILDER_AVAILABLE or not AnswerRecord:
                return 0
            
            return AnswerRecord.query.filter_by(
                student_id=student_id
            ).filter(
                AnswerRecord.created_at >= start_date,
                AnswerRecord.created_at <= end_date
            ).count()
            
        except Exception:
            return 0

    def _calculate_improvement_rate(self, student_id: int, start_date: datetime, end_date: datetime) -> float:
        """改善率計算"""
        try:
            # 前週と今週のスコア比較（簡易実装）
            current_week_activities = ActivityLog.query.filter_by(
                student_id=student_id
            ).filter(
                ActivityLog.created_at >= start_date,
                ActivityLog.created_at <= end_date
            ).count()
            
            # 前週
            prev_start = start_date - timedelta(days=7)
            prev_end = start_date
            prev_week_activities = ActivityLog.query.filter_by(
                student_id=student_id
            ).filter(
                ActivityLog.created_at >= prev_start,
                ActivityLog.created_at < prev_end
            ).count()
            
            if prev_week_activities == 0:
                return 100.0 if current_week_activities > 0 else 0.0
            
            improvement = ((current_week_activities - prev_week_activities) / prev_week_activities) * 100
            return max(-100.0, min(100.0, improvement))  # -100%から100%の範囲
            
        except Exception:
            return 0.0

    def _get_most_active_students(self, student_ids: List[int], limit: int = 5) -> List[Dict[str, Any]]:
        """最も活発な学生取得"""
        try:
            # 学生別活動数取得
            student_activities = []
            for student_id in student_ids:
                activity_count = ActivityLog.query.filter_by(student_id=student_id).count()
                student = User.query.get(student_id)
                if student and activity_count > 0:
                    student_activities.append({
                        "student_id": student_id,
                        "username": student.username,
                        "activity_count": activity_count
                    })
            
            # 活動数で降順ソート
            student_activities.sort(key=lambda x: x["activity_count"], reverse=True)
            return student_activities[:limit]
            
        except Exception:
            return []

    def _get_highest_completion_students(self, student_ids: List[int], limit: int = 5) -> List[Dict[str, Any]]:
        """最高完了率学生取得"""
        try:
            student_completions = []
            for student_id in student_ids:
                completion_score = self._calculate_completion_score(student_id)
                student = User.query.get(student_id)
                if student and completion_score > 0:
                    student_completions.append({
                        "student_id": student_id,
                        "username": student.username,
                        "completion_score": completion_score
                    })
            
            student_completions.sort(key=lambda x: x["completion_score"], reverse=True)
            return student_completions[:limit]
            
        except Exception:
            return []

    def _get_most_improved_students(self, student_ids: List[int], limit: int = 5) -> List[Dict[str, Any]]:
        """最も改善した学生取得"""
        try:
            student_improvements = []
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            for student_id in student_ids:
                improvement_rate = self._calculate_improvement_rate(student_id, start_date, end_date)
                student = User.query.get(student_id)
                if student and improvement_rate > 0:
                    student_improvements.append({
                        "student_id": student_id,
                        "username": student.username,
                        "improvement_rate": improvement_rate
                    })
            
            student_improvements.sort(key=lambda x: x["improvement_rate"], reverse=True)
            return student_improvements[:limit]
            
        except Exception:
            return []

    def _get_consistent_learners(self, student_ids: List[int], limit: int = 5) -> List[Dict[str, Any]]:
        """継続的学習者取得"""
        try:
            consistent_learners = []
            
            for student_id in student_ids:
                # 過去7日の活動日数
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                
                daily_activities = db.session.query(
                    func.date(ActivityLog.created_at)
                ).filter_by(
                    student_id=student_id
                ).filter(
                    ActivityLog.created_at >= start_date,
                    ActivityLog.created_at <= end_date
                ).distinct().count()
                
                student = User.query.get(student_id)
                if student and daily_activities >= 5:  # 週5日以上活動
                    consistent_learners.append({
                        "student_id": student_id,
                        "username": student.username,
                        "active_days": daily_activities
                    })
            
            consistent_learners.sort(key=lambda x: x["active_days"], reverse=True)
            return consistent_learners[:limit]
            
        except Exception:
            return []

    def _get_basebuilder_champions(self, student_ids: List[int], limit: int = 5) -> List[Dict[str, Any]]:
        """BaseBuilderチャンピオン取得"""
        try:
            if not BASEBUILDER_AVAILABLE:
                return []
            
            basebuilder_champions = []
            for student_id in student_ids:
                basebuilder_score = self._calculate_basebuilder_score(student_id)
                student = User.query.get(student_id)
                if student and basebuilder_score > 0:
                    basebuilder_champions.append({
                        "student_id": student_id,
                        "username": student.username,
                        "basebuilder_score": basebuilder_score
                    })
            
            basebuilder_champions.sort(key=lambda x: x["basebuilder_score"], reverse=True)
            return basebuilder_champions[:limit]
            
        except Exception:
            return []

    def _count_active_students_this_week(self, student_ids: List[int]) -> int:
        """今週のアクティブ学生数カウント"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            active_students = db.session.query(
                ActivityLog.student_id
            ).filter(
                ActivityLog.student_id.in_(student_ids),
                ActivityLog.created_at >= start_date,
                ActivityLog.created_at <= end_date
            ).distinct().count()
            
            return active_students
            
        except Exception:
            return 0

    def _calculate_average_activity(self, student_ids: List[int]) -> float:
        """平均活動数計算"""
        try:
            total_activities = ActivityLog.query.filter(
                ActivityLog.student_id.in_(student_ids)
            ).count()
            
            return total_activities / len(student_ids) if student_ids else 0.0
            
        except Exception:
            return 0.0

    def _calculate_class_completion_rate(self, student_ids: List[int]) -> float:
        """クラス完了率計算"""
        try:
            total_todos = Todo.query.filter(Todo.student_id.in_(student_ids)).count()
            completed_todos = Todo.query.filter(
                Todo.student_id.in_(student_ids),
                Todo.is_completed == True
            ).count()
            
            return (completed_todos / total_todos * 100) if total_todos > 0 else 0.0
            
        except Exception:
            return 0.0

    def _calculate_percentile(self, rank: int, total: int) -> float:
        """パーセンタイル計算"""
        try:
            if total <= 1:
                return 100.0
            return ((total - rank) / (total - 1)) * 100
        except Exception:
            return 0.0

    def _get_recent_activity_count(self, student_id: int, days: int = 7) -> int:
        """最近の活動数取得"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            return ActivityLog.query.filter_by(
                student_id=student_id
            ).filter(
                ActivityLog.created_at >= start_date,
                ActivityLog.created_at <= end_date
            ).count()
            
        except Exception:
            return 0

    def _get_empty_ranking_metrics(self) -> Dict[str, Any]:
        """空のランキングメトリクス"""
        return {
            "overall_rank": 0,
            "total_participants": 0,
            "percentile": 0,
            "my_total_score": 0,
            "class_average_score": 0,
            "score_above_average": False,
            "weekly_rank": 0,
            "weekly_total_score": 0,
            "weekly_participants": 0,
            "weekly_percentile": 0
        }

    def get_service_status(self) -> Dict[str, Any]:
        """サービス状態取得"""
        return {
            "service_name": "StudentRankingService",
            "status": "active",
            "version": "1.0.0",
            "basebuilder_available": BASEBUILDER_AVAILABLE,
            "lesson_system_available": LESSON_SYSTEM_AVAILABLE,
            "capabilities": [
                "class_top_learners_ranking",
                "weekly_top_learners_ranking",
                "ranking_metrics_calculation",
                "peer_comparison_analysis",
                "activity_rankings_generation"
            ]
        }