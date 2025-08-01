# -*- coding: utf-8 -*-
"""
UnitDataService

純粋なデータ取得・変換専門サービス
UnitSelectionManagerのデータ取得ロジックを抽出・統合
"""
import logging
from typing import Any, Dict, List, Optional

from flask_login import current_user

from app.models import (
    Class, ClassEnrollment, CurriculumUnit, db
)

logger = logging.getLogger(__name__)


class UnitDataService:
    """単元データ取得専門サービス"""

    def get_units_data(self, subject_id: Optional[int] = None, 
                      school_id: Optional[int] = None, 
                      include_progress: bool = True) -> List[Dict[str, Any]]:
        """
        単元一覧データを取得
        
        Args:
            subject_id: 科目ID
            school_id: 学校ID  
            include_progress: 進捗情報を含めるか
            
        Returns:
            list: 単元データのリスト
        """
        try:
            logger.info(f"get_units_data called by user {current_user.id} ({current_user.role})")
            logger.info(f"Parameters: subject_id={subject_id}, school_id={school_id}, include_progress={include_progress}")

            unit_data = []

            # 学生の場合、所属クラスのカリキュラムを取得
            if current_user.role == "student":
                unit_data.extend(self._get_student_curriculum_data(include_progress))
                unit_data.extend(self._get_student_unit_data(subject_id, include_progress))
            # 教師・管理者の場合
            else:
                unit_data.extend(self._get_teacher_unit_data(subject_id, school_id, include_progress))

            # 重複排除（idベース）
            unique_units = self._remove_duplicates(unit_data)

            logger.info(f"Total unique units returned: {len(unique_units)}")
            return unique_units

        except Exception as e:
            logger.error(f"Error in get_units_data: {str(e)}")
            raise

    def _get_student_curriculum_data(self, include_progress: bool) -> List[Dict[str, Any]]:
        """学生用カリキュラムデータ取得"""
        unit_data = []
        
        try:
            from app.models import ClassEnrollment, Curriculum
            
            # 学生の所属クラスを取得
            enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
            class_ids = [e.class_id for e in enrollments]
            
            if class_ids:
                # レッスンシステムの動的インポート
                lesson_models = self._import_lesson_models()
                
                if lesson_models['CurriculumLesson']:
                    # 新しいカリキュラムシステム（レッスン）
                    curricula = Curriculum.query.filter(Curriculum.class_id.in_(class_ids)).all()
                    
                    for curriculum in curricula:
                        # レッスン数を確認
                        lessons = lesson_models['CurriculumLesson'].query.filter_by(
                            curriculum_id=curriculum.id
                        ).all()
                        
                        if len(lessons) > 0:  # レッスンがある場合のみ追加
                            curriculum_info = self._build_curriculum_info(curriculum)
                            
                            # プログレス情報を含める場合
                            if include_progress:
                                curriculum_info.update(self._get_curriculum_progress(
                                    curriculum, lessons, lesson_models
                                ))
                            
                            unit_data.append(curriculum_info)
        
        except Exception as e:
            logger.error(f"Error getting student curriculum data: {str(e)}")
        
        return unit_data

    def _get_student_unit_data(self, subject_id: Optional[int], 
                             include_progress: bool) -> List[Dict[str, Any]]:
        """学生用単元データ取得"""
        unit_data = []
        
        try:
            from app.models import ClassEnrollment
            
            # 学生の所属クラスを取得
            enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
            class_ids = [e.class_id for e in enrollments]
            
            if class_ids:
                # CurriculumUnit の取得
                query = CurriculumUnit.query.filter(
                    CurriculumUnit.school_id.in_([
                        enrollment.class_obj.school_id for enrollment in enrollments 
                        if enrollment.class_obj
                    ])
                )
                
                if subject_id:
                    query = query.filter(CurriculumUnit.subject_id == subject_id)
                
                units = query.filter(CurriculumUnit.is_active == True).all()
                
                for unit in units:
                    unit_info = self._build_unit_info(unit)
                    
                    # プログレスを含める場合
                    if include_progress:
                        unit_info.update(self._get_unit_progress(unit))
                    
                    unit_data.append(unit_info)
        
        except Exception as e:
            logger.error(f"Error getting student unit data: {str(e)}")
        
        return unit_data

    def _get_teacher_unit_data(self, subject_id: Optional[int], 
                             school_id: Optional[int], 
                             include_progress: bool) -> List[Dict[str, Any]]:
        """教師用単元データ取得"""
        unit_data = []
        
        try:
            # CurriculumUnit の取得
            query = CurriculumUnit.query
            
            if subject_id:
                query = query.filter(CurriculumUnit.subject_id == subject_id)
            
            if school_id:
                query = query.filter(CurriculumUnit.school_id == school_id)
            
            units = query.filter(CurriculumUnit.is_active == True).all()
            
            for unit in units:
                unit_info = self._build_unit_info(unit)
                
                # 教師用の統計情報を含める場合
                if include_progress:
                    unit_info.update(self._get_teacher_unit_statistics(unit))
                
                unit_data.append(unit_info)
        
        except Exception as e:
            logger.error(f"Error getting teacher unit data: {str(e)}")
        
        return unit_data

    def _import_lesson_models(self) -> Dict[str, Any]:
        """レッスンシステムモジュールの動的インポート"""
        try:
            from app.modules.lesson_system.models.lesson_models import (
                CurriculumLesson, StudentLessonProgress, LessonTask, 
                StudentTaskCheck, TaskCheckStatus
            )
            return {
                'CurriculumLesson': CurriculumLesson,
                'StudentLessonProgress': StudentLessonProgress,
                'LessonTask': LessonTask,
                'StudentTaskCheck': StudentTaskCheck,
                'TaskCheckStatus': TaskCheckStatus
            }
        except ImportError:
            # レッスンシステムが利用できない場合
            return {
                'CurriculumLesson': None,
                'StudentLessonProgress': None,
                'LessonTask': None,
                'StudentTaskCheck': None,
                'TaskCheckStatus': None
            }

    def _build_curriculum_info(self, curriculum) -> Dict[str, Any]:
        """カリキュラム情報の基本構造構築"""
        estimated_hours = getattr(curriculum, 'total_hours', None) or 1
        difficulty_level = getattr(curriculum, 'difficulty_level', None) or 2
        
        return {
            "id": curriculum.id,
            "title": curriculum.title,
            "description": curriculum.description,
            "subject_id": curriculum.subject_id,
            "type": "curriculum",
            "estimated_hours": estimated_hours,
            "difficulty_level": difficulty_level,
            "is_active": getattr(curriculum, 'is_active', True),
            "lessons": []
        }

    def _build_unit_info(self, unit) -> Dict[str, Any]:
        """単元情報の基本構造構築"""
        return {
            "id": unit.id,
            "title": unit.title,
            "description": unit.description,
            "subject_id": unit.subject_id,
            "type": "unit",
            "estimated_hours": unit.estimated_hours,
            "difficulty_level": unit.difficulty_level,
            "is_active": unit.is_active,
            "school_id": unit.school_id
        }

    def _get_curriculum_progress(self, curriculum, lessons, lesson_models) -> Dict[str, Any]:
        """カリキュラム進捗情報取得"""
        try:
            if not lesson_models['StudentLessonProgress']:
                return {"progress": 0, "status": "unavailable"}

            # レッスン進捗の取得
            lesson_progresses = lesson_models['StudentLessonProgress'].query.filter(
                lesson_models['StudentLessonProgress'].lesson_id.in_([l.id for l in lessons]),
                lesson_models['StudentLessonProgress'].student_id == current_user.id
            ).all()

            total_lessons = len(lessons)
            completed_lessons = len([p for p in lesson_progresses if p.is_completed])
            
            progress_percentage = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

            return {
                "progress": progress_percentage,
                "completed_lessons": completed_lessons,
                "total_lessons": total_lessons,
                "status": "completed" if progress_percentage >= 100 else "in_progress"
            }
        
        except Exception as e:
            logger.error(f"Error getting curriculum progress: {str(e)}")
            return {"progress": 0, "status": "error"}

    def _get_unit_progress(self, unit) -> Dict[str, Any]:
        """単元進捗情報取得"""
        try:
            from app.models import StudentUnitSelection
            
            selection = StudentUnitSelection.query.filter_by(
                unit_id=unit.id,
                student_id=current_user.id
            ).first()

            if selection:
                return {
                    "progress": selection.progress_percentage or 0,
                    "status": selection.status or "not_started",
                    "selected_at": selection.selected_at.isoformat() if selection.selected_at else None
                }
            else:
                return {
                    "progress": 0,
                    "status": "not_selected",
                    "selected_at": None
                }
        
        except Exception as e:
            logger.error(f"Error getting unit progress: {str(e)}")
            return {"progress": 0, "status": "error"}

    def _get_teacher_unit_statistics(self, unit) -> Dict[str, Any]:
        """教師用単元統計情報取得"""
        try:
            from app.models import StudentUnitSelection
            
            # この単元を選択している学生数
            total_selections = StudentUnitSelection.query.filter_by(unit_id=unit.id).count()
            completed_selections = StudentUnitSelection.query.filter_by(
                unit_id=unit.id, 
                status='completed'
            ).count()
            
            completion_rate = (completed_selections / total_selections * 100) if total_selections > 0 else 0
            
            return {
                "total_selections": total_selections,
                "completed_selections": completed_selections,
                "completion_rate": completion_rate,
                "status": "active" if total_selections > 0 else "unused"
            }
        
        except Exception as e:
            logger.error(f"Error getting teacher unit statistics: {str(e)}")
            return {"total_selections": 0, "completed_selections": 0, "completion_rate": 0}

    def _remove_duplicates(self, unit_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """重複排除（idベース）"""
        seen_ids = set()
        unique_units = []
        
        for unit in unit_data:
            unit_id = unit.get("id")
            if unit_id and unit_id not in seen_ids:
                seen_ids.add(unit_id)
                unique_units.append(unit)
        
        return unique_units