# -*- coding: utf-8 -*-
"""
Learning Progress Service

学習進捗管理専門サービス
Phase8E: student dashboard.pyから分離した学習進捗機能
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from flask import current_app
from flask_login import current_user
from sqlalchemy import func

from app.models import ClassEnrollment, CurriculumUnit, db

# Curriculumモデル（SQLAlchemy has()フィルター用）
try:
    from app.models import Curriculum
    CURRICULUM_MODEL_AVAILABLE = True
except ImportError:
    logger.warning("Curriculum model not available")
    Curriculum = None
    CURRICULUM_MODEL_AVAILABLE = False

logger = logging.getLogger(__name__)

# レッスンシステムモデル（エラー保護）
try:
    from app.modules.lesson_system.models.lesson_models import (
        CurriculumLesson, StudentLessonProgress, LessonTask, StudentTaskCheck
    )
    LESSON_SYSTEM_AVAILABLE = True
except ImportError:
    logger.warning("Lesson system models not available")
    CurriculumLesson = None
    StudentLessonProgress = None
    LessonTask = None
    StudentTaskCheck = None
    LESSON_SYSTEM_AVAILABLE = False

# StudentUnitSelection（Phase5対応）
try:
    from app.models import StudentUnitSelection
    UNIT_SELECTION_AVAILABLE = True
except ImportError:
    logger.warning("StudentUnitSelection model not available")
    StudentUnitSelection = None
    UNIT_SELECTION_AVAILABLE = False


class LearningProgressService:
    """学習進捗管理専門サービス"""

    def get_lesson_progress_summary(self, student_id: int) -> Dict[str, Any]:
        """
        レッスン進捗サマリー取得
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: レッスン進捗サマリー
        """
        try:
            logger.info(f"Getting lesson progress summary for student {student_id}")
            
            # 学生の所属クラス取得
            enrollments = ClassEnrollment.query.filter_by(student_id=student_id).all()
            class_ids = [e.class_id for e in enrollments]
            
            if not class_ids:
                logger.warning(f"No class enrollments found for student {student_id}")
                return self._get_empty_progress_summary()

            # レッスンシステム利用可能性に応じて処理分岐
            if LESSON_SYSTEM_AVAILABLE:
                return self._get_lesson_system_progress(student_id, class_ids)
            else:
                return self._get_legacy_progress(student_id, class_ids)
                
        except Exception as e:
            logger.error(f"Error getting lesson progress for student {student_id}: {str(e)}")
            return self._get_empty_progress_summary()

    def calculate_curriculum_progress(self, student_id: int) -> Dict[str, Any]:
        """
        カリキュラム進捗計算
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: カリキュラム進捗データ
        """
        try:
            logger.info(f"Calculating curriculum progress for student {student_id}")
            
            # 学生の所属クラス取得
            enrollments = ClassEnrollment.query.filter_by(student_id=student_id).all()
            class_ids = [e.class_id for e in enrollments]
            
            if not class_ids:
                return {"curricula": [], "total_curricula": 0}

            # カリキュラム進捗データ構築
            curricula_progress = self._build_curricula_progress(student_id, class_ids)
            
            return {
                "curricula": curricula_progress,
                "total_curricula": len(curricula_progress),
                "overall_completion_rate": self._calculate_overall_completion_rate(curricula_progress)
            }
            
        except Exception as e:
            logger.error(f"Error calculating curriculum progress for student {student_id}: {str(e)}")
            return {"curricula": [], "total_curricula": 0}

    def get_progress_statistics(self, student_id: int) -> Dict[str, Any]:
        """
        進捗統計取得
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: 進捗統計データ
        """
        try:
            logger.info(f"Getting progress statistics for student {student_id}")
            
            # 基本統計
            basic_stats = self._get_basic_progress_stats(student_id)
            
            # レッスン完了統計
            lesson_stats = self._get_lesson_completion_stats(student_id)
            
            # 単元進捗統計
            unit_stats = self._get_unit_progress_stats(student_id)
            
            return {
                **basic_stats,
                **lesson_stats,
                **unit_stats,
                "calculated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting progress statistics for student {student_id}: {str(e)}")
            return {}

    def calculate_completion_requirements(self, student_id: int) -> Dict[str, Any]:
        """
        完了要件計算
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: 完了要件データ
        """
        try:
            logger.info(f"Calculating completion requirements for student {student_id}")
            
            # 現在の進捗状況取得
            current_progress = self.get_lesson_progress_summary(student_id)
            
            # 完了要件分析
            requirements = {
                "total_required": current_progress.get("stats", {}).get("total_selected", 0),
                "currently_completed": current_progress.get("stats", {}).get("completed", 0),
                "in_progress": current_progress.get("stats", {}).get("in_progress", 0),
                "remaining": 0,
                "completion_rate": current_progress.get("stats", {}).get("completion_rate", 0),
                "estimated_completion_date": None
            }
            
            # 残り要件計算
            requirements["remaining"] = max(0, 
                requirements["total_required"] - requirements["currently_completed"]
            )
            
            # 完了予想日計算（簡易実装）
            if requirements["remaining"] > 0:
                requirements["estimated_completion_date"] = self._estimate_completion_date(
                    student_id, requirements["remaining"]
                )
            
            return requirements
            
        except Exception as e:
            logger.error(f"Error calculating completion requirements for student {student_id}: {str(e)}")
            return {}

    def integrate_basebuilder_progress(self, student_id: int) -> Dict[str, Any]:
        """
        BaseBuilder進捗統合
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: BaseBuilder統合進捗データ
        """
        try:
            logger.info(f"Integrating BaseBuilder progress for student {student_id}")
            
            # BaseBuilder進捗データ取得
            basebuilder_data = self._get_basebuilder_progress_data(student_id)
            
            # レッスン進捗との統合
            lesson_progress = self.get_lesson_progress_summary(student_id)
            
            # 統合データ構築
            integrated_data = {
                "lesson_progress": lesson_progress,
                "basebuilder_progress": basebuilder_data,
                "integration_score": self._calculate_integration_score(lesson_progress, basebuilder_data),
                "recommendations": self._generate_progress_recommendations(lesson_progress, basebuilder_data)
            }
            
            return integrated_data
            
        except Exception as e:
            logger.error(f"Error integrating BaseBuilder progress for student {student_id}: {str(e)}")
            return {}

    def _get_lesson_system_progress(self, student_id: int, class_ids: List[int]) -> Dict[str, Any]:
        """レッスンシステムベースの進捗取得"""
        try:
            # 学生が選択した単元（Phase5対応）
            selected_units = []
            if UNIT_SELECTION_AVAILABLE and StudentUnitSelection:
                active_selections = StudentUnitSelection.query.filter_by(
                    student_id=student_id
                ).filter(
                    (StudentUnitSelection.approval_status != 'approved') | 
                    (StudentUnitSelection.approval_status.is_(None))
                ).all()
                selected_unit_ids = [selection.unit_id for selection in active_selections]
                selected_units = [{"unit_id": uid} for uid in selected_unit_ids]
            else:
                selected_unit_ids = []

            # カリキュラムレッスンの進捗統計
            total_lessons = 0
            completed_lessons = 0
            in_progress_lessons = 0
            
            if CurriculumLesson and StudentLessonProgress and CURRICULUM_MODEL_AVAILABLE and Curriculum:
                # 総レッスン数（クラス関連のみ）
                total_lessons = CurriculumLesson.query.join(
                    CurriculumLesson.curriculum
                ).filter(
                    CurriculumLesson.curriculum.has(Curriculum.class_id.in_(class_ids))
                ).count()
                
                # 完了済みレッスン数
                completed_lessons = StudentLessonProgress.query.filter_by(
                    student_id=student_id,
                    approval_status='approved'
                ).join(CurriculumLesson).join(
                    CurriculumLesson.curriculum
                ).filter(
                    CurriculumLesson.curriculum.has(Curriculum.class_id.in_(class_ids))
                ).count()
                
                # 進行中レッスン数  
                in_progress_lessons = StudentLessonProgress.query.filter_by(
                    student_id=student_id
                ).filter(
                    StudentLessonProgress.approval_status != 'approved'
                ).join(CurriculumLesson).join(
                    CurriculumLesson.curriculum
                ).filter(
                    CurriculumLesson.curriculum.has(Curriculum.class_id.in_(class_ids))
                ).count()

            completion_rate = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

            return {
                "selected_units": selected_units,
                "stats": {
                    "total_selected": len(selected_unit_ids),
                    "completed": completed_lessons,
                    "in_progress": in_progress_lessons,
                    "pending_approval": in_progress_lessons,
                    "completion_rate": completion_rate,
                    "total_lessons": total_lessons
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting lesson system progress: {str(e)}")
            return self._get_empty_progress_summary()

    def _get_legacy_progress(self, student_id: int, class_ids: List[int]) -> Dict[str, Any]:
        """レガシーシステムベースの進捗取得"""
        return {
            "selected_units": [],
            "stats": {
                "total_selected": 0,
                "completed": 0,
                "in_progress": 0,
                "pending_approval": 0,
                "completion_rate": 0,
                "total_lessons": 0
            }
        }

    def _build_curricula_progress(self, student_id: int, class_ids: List[int]) -> List[Dict[str, Any]]:
        """カリキュラム進捗データ構築"""
        try:
            from app.models import Curriculum
            
            curricula_progress = []
            
            # 各クラスのカリキュラムを取得
            curricula = Curriculum.query.filter(Curriculum.class_id.in_(class_ids)).all()
            
            for curriculum in curricula:
                progress_info = {
                    "curriculum_id": curriculum.id,
                    "curriculum_title": curriculum.title,
                    "class_id": curriculum.class_id,
                    "progress_percentage": 0,
                    "completed_lessons": 0,
                    "total_lessons": 0
                }
                
                # レッスン進捗を取得
                if LESSON_SYSTEM_AVAILABLE and CurriculumLesson and StudentLessonProgress:
                    lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum.id).all()
                    progress_info["total_lessons"] = len(lessons)
                    
                    if lessons:
                        completed = StudentLessonProgress.query.filter_by(
                            student_id=student_id,
                            approval_status='approved'
                        ).join(CurriculumLesson).filter(
                            CurriculumLesson.curriculum_id == curriculum.id
                        ).count()
                        
                        progress_info["completed_lessons"] = completed
                        progress_info["progress_percentage"] = (completed / len(lessons)) * 100
                
                curricula_progress.append(progress_info)
            
            return curricula_progress
            
        except Exception as e:
            logger.error(f"Error building curricula progress: {str(e)}")
            return []

    def _get_basic_progress_stats(self, student_id: int) -> Dict[str, Any]:
        """基本進捗統計取得"""
        try:
            from app.models import Todo, Goal
            
            # Todo統計
            total_todos = Todo.query.filter_by(student_id=student_id).count()
            completed_todos = Todo.query.filter_by(student_id=student_id, is_completed=True).count()
            todo_completion_rate = (completed_todos / total_todos * 100) if total_todos > 0 else 0
            
            # Goal統計
            total_goals = Goal.query.filter_by(student_id=student_id).count()
            completed_goals = Goal.query.filter_by(student_id=student_id, is_completed=True).count()
            goal_completion_rate = (completed_goals / total_goals * 100) if total_goals > 0 else 0
            
            return {
                "todo_completion_rate": todo_completion_rate,
                "goal_completion_rate": goal_completion_rate,
                "total_todos": total_todos,
                "completed_todos": completed_todos,
                "total_goals": total_goals,
                "completed_goals": completed_goals
            }
            
        except Exception as e:
            logger.error(f"Error getting basic progress stats: {str(e)}")
            return {}

    def _get_lesson_completion_stats(self, student_id: int) -> Dict[str, Any]:
        """レッスン完了統計取得"""
        try:
            if not LESSON_SYSTEM_AVAILABLE or not StudentLessonProgress:
                return {"lesson_stats": {"total": 0, "completed": 0, "in_progress": 0}}
            
            total_lessons = StudentLessonProgress.query.filter_by(student_id=student_id).count()
            completed_lessons = StudentLessonProgress.query.filter_by(
                student_id=student_id, approval_status='approved'
            ).count()
            in_progress_lessons = total_lessons - completed_lessons
            
            return {
                "lesson_stats": {
                    "total": total_lessons,
                    "completed": completed_lessons,
                    "in_progress": in_progress_lessons,
                    "completion_rate": (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting lesson completion stats: {str(e)}")
            return {"lesson_stats": {"total": 0, "completed": 0, "in_progress": 0}}

    def _get_unit_progress_stats(self, student_id: int) -> Dict[str, Any]:
        """単元進捗統計取得"""
        try:
            # CurriculumUnit統計
            total_units = CurriculumUnit.query.filter_by(created_by=student_id).count()
            active_units = CurriculumUnit.query.filter_by(
                created_by=student_id, is_active=True
            ).count()
            
            return {
                "unit_stats": {
                    "total_units": total_units,
                    "active_units": active_units,
                    "inactive_units": total_units - active_units
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting unit progress stats: {str(e)}")
            return {"unit_stats": {"total_units": 0, "active_units": 0}}

    def _calculate_overall_completion_rate(self, curricula_progress: List[Dict[str, Any]]) -> float:
        """全体完了率計算"""
        try:
            if not curricula_progress:
                return 0.0
            
            total_progress = sum(c.get("progress_percentage", 0) for c in curricula_progress)
            return total_progress / len(curricula_progress)
            
        except Exception:
            return 0.0

    def _estimate_completion_date(self, student_id: int, remaining_items: int) -> Optional[str]:
        """完了予想日計算（簡易実装）"""
        try:
            # 過去の学習ペースから推定（仮実装）
            from datetime import timedelta
            estimated_days = remaining_items * 3  # 1項目3日と仮定
            completion_date = datetime.now() + timedelta(days=estimated_days)
            return completion_date.isoformat()
        except Exception:
            return None

    def _get_basebuilder_progress_data(self, student_id: int) -> Dict[str, Any]:
        """BaseBuilder進捗データ取得"""
        try:
            # BaseBuilder統計取得（他サービスとの連携）
            return {
                "vocabulary_progress": 0,
                "mastery_level": 0,
                "learning_streak": 0
            }
        except Exception:
            return {}

    def _calculate_integration_score(self, lesson_progress: Dict, basebuilder_data: Dict) -> float:
        """統合スコア計算"""
        try:
            lesson_rate = lesson_progress.get("stats", {}).get("completion_rate", 0)
            basebuilder_rate = basebuilder_data.get("mastery_level", 0)
            return (lesson_rate + basebuilder_rate) / 2
        except Exception:
            return 0.0

    def _generate_progress_recommendations(self, lesson_progress: Dict, basebuilder_data: Dict) -> List[str]:
        """進捗推奨事項生成"""
        recommendations = []
        try:
            lesson_rate = lesson_progress.get("stats", {}).get("completion_rate", 0)
            if lesson_rate < 50:
                recommendations.append("レッスン進捗を向上させることをお勧めします")
            
            basebuilder_rate = basebuilder_data.get("mastery_level", 0)
            if basebuilder_rate < 50:
                recommendations.append("語彙学習に重点を置くことをお勧めします")
                
        except Exception:
            pass
        
        return recommendations

    def _get_empty_progress_summary(self) -> Dict[str, Any]:
        """空の進捗サマリー"""
        return {
            "selected_units": [],
            "stats": {
                "total_selected": 0,
                "completed": 0,
                "in_progress": 0,
                "pending_approval": 0,
                "completion_rate": 0,
                "total_lessons": 0
            }
        }

    def get_service_status(self) -> Dict[str, Any]:
        """サービス状態取得"""
        return {
            "service_name": "LearningProgressService",
            "status": "active",
            "version": "1.0.0",
            "lesson_system_available": LESSON_SYSTEM_AVAILABLE,
            "unit_selection_available": UNIT_SELECTION_AVAILABLE,
            "capabilities": [
                "lesson_progress_summary",
                "curriculum_progress_calculation",
                "progress_statistics_generation",
                "completion_requirements_calculation",
                "basebuilder_progress_integration"
            ]
        }