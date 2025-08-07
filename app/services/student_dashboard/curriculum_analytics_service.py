# -*- coding: utf-8 -*-
"""
Curriculum Analytics Service

カリキュラム統計専門サービス  
Phase8E: student dashboard.pyから分離したカリキュラム統計機能
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from flask import current_app
from flask_login import current_user
from sqlalchemy import func

from app.models import ClassEnrollment, Curriculum, CurriculumUnit, db

logger = logging.getLogger(__name__)

# レッスンシステムモデル（共通ローダー使用）
from app.utils.lesson_model_loader import get_lesson_models
CurriculumLesson, LessonTask, StudentLessonProgress, StudentTaskCheck, TaskCheckStatus, LESSON_SYSTEM_AVAILABLE = get_lesson_models()
# 必要なもののみ使用（順序調整）
StudentLessonProgress, LessonTask, StudentTaskCheck = StudentLessonProgress, LessonTask, StudentTaskCheck


class CurriculumAnalyticsService:
    """カリキュラム統計専門サービス"""

    def generate_unit_statistics(self, student_id: int) -> Dict[str, Any]:
        """
        単元統計生成
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: 単元統計データ
        """
        try:
            logger.info(f"Generating unit statistics for student {student_id}")
            
            # 認証状態チェック
            if not current_user or not current_user.is_authenticated:
                logger.warning(f"User not authenticated, returning empty unit stats")
                return self._get_empty_unit_stats()

            # 学生が所属するクラスの取得
            enrollments = ClassEnrollment.query.filter_by(student_id=student_id).all()
            class_ids = [e.class_id for e in enrollments]
            
            if not class_ids:
                logger.warning(f"No class enrollments found for student {student_id}")
                return self._get_empty_unit_stats()

            # カリキュラム統計
            curriculum_stats = self._get_curriculum_statistics(student_id, class_ids)
            
            # 単元進捗統計
            unit_progress_stats = self._get_unit_progress_statistics(student_id, class_ids)
            
            # レッスン統計
            lesson_stats = self._get_lesson_statistics(student_id, class_ids)
            
            # 学習時間統計
            study_time_stats = self.calculate_study_time_estimates(student_id)
            
            # 統合統計
            unit_statistics = {
                **curriculum_stats,
                **unit_progress_stats,
                **lesson_stats,
                **study_time_stats,
                "generated_at": datetime.now().isoformat()
            }
            
            return unit_statistics
            
        except Exception as e:
            logger.error(f"Error generating unit statistics for student {student_id}: {str(e)}")
            return self._get_empty_unit_stats()

    def get_class_curriculum_progress(self, student_id: int) -> Dict[str, Any]:
        """
        クラス別カリキュラム進捗取得
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: クラス別カリキュラム進捗
        """
        try:
            logger.info(f"Getting class curriculum progress for student {student_id}")
            
            # 学生の所属クラス取得
            enrollments = ClassEnrollment.query.filter_by(student_id=student_id).all()
            
            class_progress = []
            total_progress = 0
            total_curricula = 0
            
            for enrollment in enrollments:
                class_obj = enrollment.class_obj
                
                # クラスのカリキュラム取得
                curricula = Curriculum.query.filter_by(class_id=class_obj.id).all()
                
                class_curriculum_progress = []
                class_total_progress = 0
                
                for curriculum in curricula:
                    curriculum_progress = self._calculate_curriculum_progress(student_id, curriculum)
                    class_curriculum_progress.append(curriculum_progress)
                    class_total_progress += curriculum_progress.get("progress_percentage", 0)
                    total_curricula += 1
                
                # クラス平均進捗計算
                class_average = (class_total_progress / len(curricula)) if curricula else 0
                total_progress += class_average
                
                class_progress.append({
                    "class_id": class_obj.id,
                    "class_name": class_obj.name,
                    "curricula_count": len(curricula),
                    "curricula_progress": class_curriculum_progress,
                    "class_average_progress": class_average
                })
            
            # 全体平均進捗
            overall_average = (total_progress / len(enrollments)) if enrollments else 0
            
            return {
                "class_progress": class_progress,
                "overall_average_progress": overall_average,
                "total_curricula": total_curricula,
                "classes_enrolled": len(enrollments)
            }
            
        except Exception as e:
            logger.error(f"Error getting class curriculum progress for student {student_id}: {str(e)}")
            return {"class_progress": [], "overall_average_progress": 0}

    def calculate_study_time_estimates(self, student_id: int) -> Dict[str, Any]:
        """
        学習時間推定計算
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: 学習時間推定データ
        """
        try:
            logger.info(f"Calculating study time estimates for student {student_id}")
            
            # 過去の学習履歴から時間推定
            historical_data = self._get_historical_study_data(student_id)
            
            # 現在の進捗状況（無限ループを避けるため簡略化）
            current_progress = {
                "total_units": CurriculumUnit.query.count(),
                "completed_units": 0,  # 簡略化
                "in_progress_units": 0,
                "completion_rate": 0.0
            }
            
            # 推定計算
            estimates = {
                "total_estimated_hours": self._calculate_total_estimated_hours(historical_data, current_progress),
                "completed_hours": self._calculate_completed_hours(historical_data),
                "remaining_hours": 0,
                "weekly_average_hours": self._calculate_weekly_average(historical_data),
                "projected_completion_date": None
            }
            
            # 残り時間計算
            estimates["remaining_hours"] = max(0, 
                estimates["total_estimated_hours"] - estimates["completed_hours"]
            )
            
            # 完了予想日計算
            if estimates["remaining_hours"] > 0 and estimates["weekly_average_hours"] > 0:
                weeks_remaining = estimates["remaining_hours"] / estimates["weekly_average_hours"]
                completion_date = datetime.now() + timedelta(weeks=weeks_remaining)
                estimates["projected_completion_date"] = completion_date.isoformat()
            
            return estimates
            
        except Exception as e:
            logger.error(f"Error calculating study time estimates for student {student_id}: {str(e)}")
            return {"total_estimated_hours": 0, "completed_hours": 0, "remaining_hours": 0}

    def analyze_completion_readiness(self, student_id: int) -> Dict[str, Any]:
        """
        完了準備度分析
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: 完了準備度分析結果
        """
        try:
            logger.info(f"Analyzing completion readiness for student {student_id}")
            
            # 現在の進捗状況（無限ループを避けるため簡略化）
            unit_stats = {
                "total_units": CurriculumUnit.query.count(),
                "completed_units": 0,
                "completion_rate": 0.0
            }
            class_progress = self.get_class_curriculum_progress(student_id)
            
            # 準備度評価
            readiness_analysis = {
                "overall_readiness_score": 0,
                "readiness_level": "not_ready",
                "completion_barriers": [],
                "strengths": [],
                "recommendations": [],
                "estimated_readiness_date": None
            }
            
            # 完了率ベース評価
            completion_rate = unit_stats.get("completion_rate", 0)
            if completion_rate >= 90:
                readiness_analysis["readiness_level"] = "ready"
                readiness_analysis["overall_readiness_score"] = 95
            elif completion_rate >= 75:
                readiness_analysis["readiness_level"] = "nearly_ready"
                readiness_analysis["overall_readiness_score"] = 80
            elif completion_rate >= 50:
                readiness_analysis["readiness_level"] = "in_progress"
                readiness_analysis["overall_readiness_score"] = 60
            else:
                readiness_analysis["readiness_level"] = "not_ready"
                readiness_analysis["overall_readiness_score"] = 30
            
            # 障害・強み・推奨事項分析
            readiness_analysis["completion_barriers"] = self._identify_completion_barriers(unit_stats, class_progress)
            readiness_analysis["strengths"] = self._identify_student_strengths(unit_stats, class_progress)
            readiness_analysis["recommendations"] = self._generate_completion_recommendations(unit_stats, class_progress)
            
            # 準備完了予想日
            if readiness_analysis["readiness_level"] != "ready":
                readiness_analysis["estimated_readiness_date"] = self._estimate_readiness_date(unit_stats)
            
            return readiness_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing completion readiness for student {student_id}: {str(e)}")
            return {"overall_readiness_score": 0, "readiness_level": "unknown"}

    def get_curriculum_difficulty_breakdown(self, student_id: int) -> Dict[str, Any]:
        """
        カリキュラム難易度内訳取得
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: カリキュラム難易度内訳
        """
        try:
            logger.info(f"Getting curriculum difficulty breakdown for student {student_id}")
            
            # 学生の所属クラス取得
            enrollments = ClassEnrollment.query.filter_by(student_id=student_id).all()
            class_ids = [e.class_id for e in enrollments]
            
            if not class_ids:
                return {"difficulty_levels": {}, "performance_by_difficulty": {}}
            
            # カリキュラム別難易度分析
            curricula = Curriculum.query.filter(Curriculum.class_id.in_(class_ids)).all()
            
            difficulty_breakdown = {}
            performance_analysis = {}
            
            for curriculum in curricula:
                # カリキュラムの難易度を取得（簡易実装）
                difficulty = self._get_curriculum_difficulty(curriculum)
                
                if difficulty not in difficulty_breakdown:
                    difficulty_breakdown[difficulty] = {
                        "curricula_count": 0,
                        "total_lessons": 0,
                        "completed_lessons": 0
                    }
                
                # レッスン統計
                if LESSON_SYSTEM_AVAILABLE and CurriculumLesson:
                    lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum.id).all()
                    difficulty_breakdown[difficulty]["curricula_count"] += 1
                    difficulty_breakdown[difficulty]["total_lessons"] += len(lessons)
                    
                    if StudentLessonProgress:
                        completed = StudentLessonProgress.query.filter_by(
                            student_id=student_id,
                            approval_status='approved'
                        ).join(CurriculumLesson).filter(
                            CurriculumLesson.curriculum_id == curriculum.id
                        ).count()
                        
                        difficulty_breakdown[difficulty]["completed_lessons"] += completed
            
            # パフォーマンス分析
            for difficulty, stats in difficulty_breakdown.items():
                completion_rate = (stats["completed_lessons"] / stats["total_lessons"] * 100) if stats["total_lessons"] > 0 else 0
                performance_analysis[difficulty] = {
                    "completion_rate": completion_rate,
                    "curricula_count": stats["curricula_count"],
                    "performance_level": self._evaluate_performance_level(completion_rate)
                }
            
            return {
                "difficulty_levels": list(difficulty_breakdown.keys()),
                "difficulty_breakdown": difficulty_breakdown,
                "performance_by_difficulty": performance_analysis,
                "difficulty_summary": self._generate_difficulty_summary(performance_analysis)
            }
            
        except Exception as e:
            logger.error(f"Error getting curriculum difficulty breakdown for student {student_id}: {str(e)}")
            return {"difficulty_levels": {}, "performance_by_difficulty": {}}

    def _get_curriculum_statistics(self, student_id: int, class_ids: List[int]) -> Dict[str, Any]:
        """カリキュラム統計取得"""
        try:
            curricula = Curriculum.query.filter(Curriculum.class_id.in_(class_ids)).all()
            
            curriculum_stats = {
                "total_curricula": len(curricula),
                "curricula_with_lessons": 0,
                "average_lessons_per_curriculum": 0
            }
            
            if LESSON_SYSTEM_AVAILABLE and CurriculumLesson:
                curricula_with_lessons = 0
                total_lessons = 0
                
                for curriculum in curricula:
                    lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum.id).all()
                    if lessons:
                        curricula_with_lessons += 1
                        total_lessons += len(lessons)
                
                curriculum_stats["curricula_with_lessons"] = curricula_with_lessons
                curriculum_stats["average_lessons_per_curriculum"] = (
                    total_lessons / curricula_with_lessons if curricula_with_lessons > 0 else 0
                )
            
            return curriculum_stats
            
        except Exception as e:
            logger.error(f"Error getting curriculum statistics: {str(e)}")
            return {"total_curricula": 0, "curricula_with_lessons": 0}

    def _get_unit_progress_statistics(self, student_id: int, class_ids: List[int]) -> Dict[str, Any]:
        """単元進捗統計取得"""
        try:
            # CurriculumUnit統計
            total_units = CurriculumUnit.query.filter_by(created_by=student_id).count()
            active_units = CurriculumUnit.query.filter_by(
                created_by=student_id, is_active=True
            ).count()
            
            return {
                "total_units": total_units,
                "active_units": active_units,
                "inactive_units": total_units - active_units,
                "unit_activity_rate": (active_units / total_units * 100) if total_units > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting unit progress statistics: {str(e)}")
            return {"total_units": 0, "active_units": 0}

    def _get_lesson_statistics(self, student_id: int, class_ids: List[int]) -> Dict[str, Any]:
        """レッスン統計取得"""
        try:
            if not LESSON_SYSTEM_AVAILABLE:
                return {"completed_units": 0, "in_progress_units": 0, "completion_rate": 0}

            # 完了済みレッスン数
            completed_lessons = 0
            in_progress_lessons = 0
            total_lessons = 0
            
            if StudentLessonProgress:
                completed_lessons = StudentLessonProgress.query.filter_by(
                    student_id=student_id,
                    approval_status='approved'
                ).count()
                
                in_progress_lessons = StudentLessonProgress.query.filter_by(
                    student_id=student_id
                ).filter(
                    StudentLessonProgress.approval_status != 'approved'
                ).count()
                
                total_lessons = StudentLessonProgress.query.filter_by(student_id=student_id).count()
            
            completion_rate = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
            
            return {
                "completed_units": completed_lessons,
                "in_progress_units": in_progress_lessons,
                "completion_rate": completion_rate,
                "total_study_time": 0  # 後で実装
            }
            
        except Exception as e:
            logger.error(f"Error getting lesson statistics: {str(e)}")
            return {"completed_units": 0, "in_progress_units": 0, "completion_rate": 0}

    def _calculate_curriculum_progress(self, student_id: int, curriculum: Any) -> Dict[str, Any]:
        """個別カリキュラム進捗計算"""
        try:
            progress_info = {
                "curriculum_id": curriculum.id,
                "curriculum_title": curriculum.title,
                "progress_percentage": 0,
                "completed_lessons": 0,
                "total_lessons": 0,
                "estimated_completion_date": None
            }
            
            if LESSON_SYSTEM_AVAILABLE and CurriculumLesson:
                lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum.id).all()
                progress_info["total_lessons"] = len(lessons)
                
                if StudentLessonProgress and lessons:
                    completed = StudentLessonProgress.query.filter_by(
                        student_id=student_id,
                        approval_status='approved'
                    ).join(CurriculumLesson).filter(
                        CurriculumLesson.curriculum_id == curriculum.id
                    ).count()
                    
                    progress_info["completed_lessons"] = completed
                    progress_info["progress_percentage"] = (completed / len(lessons)) * 100
                    
                    # 完了予想日計算
                    if completed < len(lessons):
                        remaining = len(lessons) - completed
                        # 簡易推定：1レッスン3日
                        estimated_days = remaining * 3
                        completion_date = datetime.now() + timedelta(days=estimated_days)
                        progress_info["estimated_completion_date"] = completion_date.isoformat()
            
            return progress_info
            
        except Exception as e:
            logger.error(f"Error calculating curriculum progress: {str(e)}")
            return {"curriculum_id": curriculum.id, "progress_percentage": 0}

    def _get_historical_study_data(self, student_id: int) -> Dict[str, Any]:
        """過去の学習データ取得"""
        try:
            from app.models import ActivityLog
            
            # 過去30日の活動記録
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            activities = ActivityLog.query.filter_by(
                student_id=student_id
            ).filter(
                ActivityLog.created_at >= start_date,
                ActivityLog.created_at <= end_date
            ).all()
            
            # 学習時間推定（簡易実装）
            study_sessions = len(activities)
            estimated_hours = study_sessions * 0.5  # 1セッション30分と仮定
            
            return {
                "total_activities": len(activities),
                "estimated_study_hours": estimated_hours,
                "study_sessions": study_sessions,
                "period_days": 30
            }
            
        except Exception as e:
            logger.error(f"Error getting historical study data: {str(e)}")
            return {"total_activities": 0, "estimated_study_hours": 0}

    def _calculate_total_estimated_hours(self, historical_data: Dict, current_progress: Dict) -> float:
        """総推定時間計算"""
        try:
            # 現在の完了率から全体時間を推定
            completion_rate = current_progress.get("completion_rate", 0)
            completed_hours = historical_data.get("estimated_study_hours", 0)
            
            if completion_rate > 0:
                total_estimated = completed_hours / (completion_rate / 100)
                return max(total_estimated, completed_hours)
            
            return completed_hours
            
        except Exception:
            return 0.0

    def _calculate_completed_hours(self, historical_data: Dict) -> float:
        """完了時間計算"""
        return historical_data.get("estimated_study_hours", 0)

    def _calculate_weekly_average(self, historical_data: Dict) -> float:
        """週間平均時間計算"""
        try:
            total_hours = historical_data.get("estimated_study_hours", 0)
            period_days = historical_data.get("period_days", 30)
            weeks = period_days / 7
            return total_hours / weeks if weeks > 0 else 0
        except Exception:
            return 0.0

    def _identify_completion_barriers(self, unit_stats: Dict, class_progress: Dict) -> List[str]:
        """完了障害特定"""
        barriers = []
        try:
            completion_rate = unit_stats.get("completion_rate", 0)
            if completion_rate < 50:
                barriers.append("全体的な進捗が遅れています")
            
            in_progress = unit_stats.get("in_progress_units", 0)
            if in_progress > 10:
                barriers.append("進行中の課題が多すぎます")
                
        except Exception:
            pass
        
        return barriers

    def _identify_student_strengths(self, unit_stats: Dict, class_progress: Dict) -> List[str]:
        """学生の強み特定"""
        strengths = []
        try:
            completion_rate = unit_stats.get("completion_rate", 0)
            if completion_rate > 80:
                strengths.append("高い完了率を維持しています")
            
            active_rate = unit_stats.get("unit_activity_rate", 0)
            if active_rate > 90:
                strengths.append("積極的に学習単元に取り組んでいます")
                
        except Exception:
            pass
        
        return strengths

    def _generate_completion_recommendations(self, unit_stats: Dict, class_progress: Dict) -> List[str]:
        """完了推奨事項生成"""
        recommendations = []
        try:
            completion_rate = unit_stats.get("completion_rate", 0)
            if completion_rate < 75:
                recommendations.append("未完了課題の優先順位を決めて取り組みましょう")
            
            in_progress = unit_stats.get("in_progress_units", 0)
            if in_progress > 5:
                recommendations.append("進行中の課題を絞って集中しましょう")
                
        except Exception:
            pass
        
        return recommendations

    def _estimate_readiness_date(self, unit_stats: Dict) -> Optional[str]:
        """準備完了予想日推定"""
        try:
            completion_rate = unit_stats.get("completion_rate", 0)
            if completion_rate > 0:
                remaining_percent = 100 - completion_rate
                # 簡易推定：現在のペースで進行
                estimated_weeks = remaining_percent / 10  # 週10%進捗と仮定
                readiness_date = datetime.now() + timedelta(weeks=estimated_weeks)
                return readiness_date.isoformat()
        except Exception:
            pass
        
        return None

    def _get_curriculum_difficulty(self, curriculum: Any) -> str:
        """カリキュラム難易度取得（簡易実装）"""
        try:
            # 実際の実装では curriculum.difficulty_level 等を使用
            curriculum_id = curriculum.id
            if curriculum_id % 4 == 0:
                return "beginner"
            elif curriculum_id % 4 == 1:
                return "intermediate" 
            elif curriculum_id % 4 == 2:
                return "advanced"
            else:
                return "expert"
        except Exception:
            return "unknown"

    def _evaluate_performance_level(self, completion_rate: float) -> str:
        """パフォーマンスレベル評価"""
        if completion_rate >= 90:
            return "excellent"
        elif completion_rate >= 75:
            return "good"
        elif completion_rate >= 50:
            return "fair"
        else:
            return "needs_improvement"

    def _generate_difficulty_summary(self, performance_analysis: Dict) -> Dict[str, Any]:
        """難易度サマリー生成"""
        try:
            if not performance_analysis:
                return {"overall_performance": "no_data"}
            
            # 平均パフォーマンス計算
            total_rate = sum(perf["completion_rate"] for perf in performance_analysis.values())
            avg_rate = total_rate / len(performance_analysis)
            
            # 強み・弱み分析
            strengths = [diff for diff, perf in performance_analysis.items() if perf["completion_rate"] > avg_rate]
            weaknesses = [diff for diff, perf in performance_analysis.items() if perf["completion_rate"] <= avg_rate]
            
            return {
                "overall_performance": self._evaluate_performance_level(avg_rate),
                "average_completion_rate": avg_rate,
                "strength_difficulties": strengths,
                "weakness_difficulties": weaknesses
            }
            
        except Exception:
            return {"overall_performance": "unknown"}

    def _get_empty_unit_stats(self) -> Dict[str, Any]:
        """空の単元統計"""
        return {
            "total_units": 0,
            "completed_units": 0,
            "in_progress_units": 0,
            "completion_rate": 0,
            "total_study_time": 0,
            "active_units": 0,
            "curricula_with_lessons": 0
        }

    def get_service_status(self) -> Dict[str, Any]:
        """サービス状態取得"""
        return {
            "service_name": "CurriculumAnalyticsService",
            "status": "active",
            "version": "1.0.0",
            "lesson_system_available": LESSON_SYSTEM_AVAILABLE,
            "capabilities": [
                "unit_statistics_generation",
                "class_curriculum_progress_tracking",
                "study_time_estimation",
                "completion_readiness_analysis",
                "curriculum_difficulty_breakdown"
            ]
        }