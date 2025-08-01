# -*- coding: utf-8 -*-
"""
LearningProgressService

学習進捗・単元進捗の専門管理サービス
Phase8D: dashboard.pyから分離した学習進捗管理機能
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from flask import current_app
from flask_login import current_user
from sqlalchemy import func

from app.models import (
    ClassEnrollment, Curriculum, CurriculumUnit, db
)

logger = logging.getLogger(__name__)

# レッスンシステムモデル（エラー保護）
try:
    from app.modules.lesson_system.models.lesson_models import (
        CurriculumLesson, LessonTask, StudentLessonProgress, 
        StudentTaskCheck, TaskCheckStatus
    )
    LESSON_SYSTEM_AVAILABLE = True
except ImportError:
    logger.warning("Lesson system models not available")
    CurriculumLesson = None
    LessonTask = None
    StudentLessonProgress = None
    StudentTaskCheck = None
    TaskCheckStatus = None
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

    def get_learning_progress_summary(self, student_id: int) -> Dict[str, Any]:
        """
        学習進捗サマリーを取得
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: 学習進捗サマリー
        """
        try:
            # 認証状態チェック
            if not current_user or not current_user.is_authenticated:
                logger.warning(f"User not authenticated, returning empty learning progress")
                return self._get_empty_progress_summary()

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
            logger.error(f"Error getting learning progress for student {student_id}: {str(e)}")
            return self._get_empty_progress_summary()

    def generate_unit_statistics(self, student_id: int) -> Dict[str, Any]:
        """
        単元統計を生成
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: 単元統計
        """
        try:
            # 認証状態チェック
            if not current_user or not current_user.is_authenticated:
                logger.warning(f"User not authenticated, returning empty unit stats")
                return self._get_empty_unit_stats()

            logger.info(f"Generating unit stats for student {student_id}")

            # 学生が所属するクラスの取得
            enrollments = ClassEnrollment.query.filter_by(student_id=student_id).all()
            class_ids = [e.class_id for e in enrollments]
            
            if not class_ids:
                logger.warning(f"No class enrollments found for student {student_id}")
                return self._get_empty_unit_stats()

            # 利用可能なカリキュラム統計
            curricula_stats = self._get_curricula_statistics(class_ids, student_id)
            
            # レッスンシステム統計
            lesson_stats = self._get_lesson_statistics(student_id, class_ids)
            
            # 統計統合
            return self._merge_unit_statistics(curricula_stats, lesson_stats)

        except Exception as e:
            logger.error(f"Error generating unit statistics for student {student_id}: {str(e)}")
            return self._get_empty_unit_stats()

    def calculate_completion_rates(self, student_id: int) -> Dict[str, float]:
        """
        完了率を計算
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: 各種完了率
        """
        try:
            if LESSON_SYSTEM_AVAILABLE and StudentLessonProgress:
                # レッスンベースの完了率計算
                total_lessons = CurriculumLesson.query.count()
                if total_lessons == 0:
                    return {"lesson_completion_rate": 0.0, "overall_completion_rate": 0.0}

                completed_lessons = StudentLessonProgress.query.filter_by(
                    student_id=student_id,
                    approval_status='approved'
                ).count()

                lesson_completion_rate = (completed_lessons / total_lessons) * 100

                return {
                    "lesson_completion_rate": lesson_completion_rate,
                    "overall_completion_rate": lesson_completion_rate,
                    "completed_lessons": completed_lessons,
                    "total_lessons": total_lessons
                }
            else:
                # レガシーシステムの完了率計算
                return {"lesson_completion_rate": 0.0, "overall_completion_rate": 0.0}

        except Exception as e:
            logger.error(f"Error calculating completion rates for student {student_id}: {str(e)}")
            return {"lesson_completion_rate": 0.0, "overall_completion_rate": 0.0}

    def get_curriculum_progress(self, student_id: int) -> Dict[str, Any]:
        """
        カリキュラム進捗を取得
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: カリキュラム進捗
        """
        try:
            enrollments = ClassEnrollment.query.filter_by(student_id=student_id).all()
            class_ids = [e.class_id for e in enrollments]
            
            if not class_ids:
                return {"curricula": [], "total_curricula": 0}

            curricula_progress = []
            
            for class_id in class_ids:
                class_curricula = Curriculum.query.filter_by(class_id=class_id).all()
                
                for curriculum in class_curricula:
                    progress_info = {
                        "curriculum_id": curriculum.id,
                        "curriculum_title": curriculum.title,
                        "class_id": class_id,
                        "progress_percentage": 0,
                        "completed_lessons": 0,
                        "total_lessons": 0
                    }
                    
                    # レッスン進捗を取得
                    if LESSON_SYSTEM_AVAILABLE and CurriculumLesson:
                        lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum.id).all()
                        progress_info["total_lessons"] = len(lessons)
                        
                        if StudentLessonProgress:
                            completed = StudentLessonProgress.query.filter_by(
                                student_id=student_id,
                                approval_status='approved'
                            ).join(CurriculumLesson).filter(
                                CurriculumLesson.curriculum_id == curriculum.id
                            ).count()
                            
                            progress_info["completed_lessons"] = completed
                            if len(lessons) > 0:
                                progress_info["progress_percentage"] = (completed / len(lessons)) * 100
                    
                    curricula_progress.append(progress_info)
            
            return {
                "curricula": curricula_progress,
                "total_curricula": len(curricula_progress)
            }

        except Exception as e:
            logger.error(f"Error getting curriculum progress for student {student_id}: {str(e)}")
            return {"curricula": [], "total_curricula": 0}

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
            else:
                selected_unit_ids = []

            # カリキュラムレッスンの進捗
            curricula = Curriculum.query.filter(Curriculum.class_id.in_(class_ids)).all()
            
            total_lessons = 0
            completed_lessons = 0
            in_progress_lessons = 0
            
            for curriculum in curricula:
                lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum.id).all()
                total_lessons += len(lessons)
                
                for lesson in lessons:
                    progress = StudentLessonProgress.query.filter_by(
                        student_id=student_id,
                        lesson_id=lesson.id
                    ).first()
                    
                    if progress:
                        if progress.approval_status == 'approved':
                            completed_lessons += 1
                        else:
                            in_progress_lessons += 1

            completion_rate = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

            return {
                "selected_units": selected_units,
                "stats": {
                    "total_selected": len(selected_unit_ids),
                    "completed": completed_lessons,
                    "in_progress": in_progress_lessons,
                    "pending_approval": in_progress_lessons,
                    "completion_rate": completion_rate,
                },
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
            },
        }

    def _get_curricula_statistics(self, class_ids: List[int], student_id: int) -> Dict[str, Any]:
        """カリキュラム統計取得"""
        try:
            curricula_with_lessons = []
            
            for class_id in class_ids:
                class_curricula = Curriculum.query.filter_by(class_id=class_id).all()
                logger.info(f"Class {class_id} has {len(class_curricula)} curricula")
                
                for curriculum in class_curricula:
                    if LESSON_SYSTEM_AVAILABLE and CurriculumLesson:
                        lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum.id).all()
                        if lessons:
                            curricula_with_lessons.append({
                                "curriculum": curriculum,
                                "lessons_count": len(lessons),
                                "class_id": class_id
                            })
            
            return {
                "curricula_with_lessons": curricula_with_lessons,
                "total_curriculum_units": len(curricula_with_lessons)
            }

        except Exception as e:
            logger.error(f"Error getting curricula statistics: {str(e)}")
            return {"curricula_with_lessons": [], "total_curriculum_units": 0}

    def _get_lesson_statistics(self, student_id: int, class_ids: List[int]) -> Dict[str, Any]:
        """レッスン統計取得"""
        try:
            if not LESSON_SYSTEM_AVAILABLE:
                return {"completed_units": 0, "in_progress_units": 0, "completion_rate": 0}

            # 完了済みレッスン数
            completed_lessons = StudentLessonProgress.query.filter_by(
                student_id=student_id,
                approval_status='approved'
            ).count() if StudentLessonProgress else 0

            # 進行中レッスン数
            in_progress_lessons = StudentLessonProgress.query.filter_by(
                student_id=student_id
            ).filter(
                StudentLessonProgress.approval_status != 'approved'
            ).count() if StudentLessonProgress else 0

            # 全体レッスン数
            total_lessons = CurriculumLesson.query.count() if CurriculumLesson else 0
            
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

    def _merge_unit_statistics(self, curricula_stats: Dict, lesson_stats: Dict) -> Dict[str, Any]:
        """統計をマージ"""
        return {
            "total_units": curricula_stats.get("total_curriculum_units", 0),
            "completed_units": lesson_stats.get("completed_units", 0),
            "in_progress_units": lesson_stats.get("in_progress_units", 0),
            "completion_rate": lesson_stats.get("completion_rate", 0),
            "total_study_time": lesson_stats.get("total_study_time", 0),
            "available_units": curricula_stats.get("total_curriculum_units", 0),
            "selected_units": curricula_stats.get("curricula_with_lessons", []),
        }

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
            },
        }

    def _get_empty_unit_stats(self) -> Dict[str, Any]:
        """空の単元統計"""
        return {
            "total_units": 0,
            "completed_units": 0,
            "in_progress_units": 0,
            "completion_rate": 0,
            "total_study_time": 0,
            "available_units": 0,
            "selected_units": [],
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
                "learning_progress_summary",
                "unit_statistics_generation",
                "completion_rate_calculation",
                "curriculum_progress_tracking"
            ]
        }