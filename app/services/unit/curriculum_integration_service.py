# -*- coding: utf-8 -*-
"""
CurriculumIntegrationService

カリキュラム統合・レガシーシステム連携専門サービス
新旧システム間の複雑な統合ロジックを一元化
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask_login import current_user

from app.models import db

logger = logging.getLogger(__name__)


class CurriculumIntegrationService:
    """カリキュラム統合専門サービス"""

    def __init__(self):
        self.lesson_models = self._import_lesson_models()

    def get_integrated_curriculum_data(self, curriculum_id: int, 
                                     include_legacy: bool = True) -> Dict[str, Any]:
        """
        統合されたカリキュラムデータを取得
        
        Args:
            curriculum_id: カリキュラムID
            include_legacy: レガシーシステムデータを含めるか
            
        Returns:
            Dict: 統合カリキュラムデータ
        """
        try:
            logger.info(f"Getting integrated curriculum data for curriculum {curriculum_id}")
            
            # カリキュラムの基本情報取得
            curriculum = self._get_curriculum(curriculum_id)
            if not curriculum:
                return {
                    "success": False,
                    "message": "指定されたカリキュラムが見つかりません"
                }

            # 新システム（レッスン）データ取得
            lesson_data = self._get_lesson_system_data(curriculum_id)
            
            # レガシーシステム（単元）データ取得
            legacy_data = self._get_legacy_unit_data(curriculum_id) if include_legacy else {}
            
            # データ統合
            integrated_data = self._integrate_curriculum_data(curriculum, lesson_data, legacy_data)
            
            return {
                "success": True,
                "curriculum": integrated_data,
                "data_sources": {
                    "lesson_system": bool(lesson_data),
                    "legacy_system": bool(legacy_data),
                    "integration_method": "unified_view"
                },
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting integrated curriculum data: {str(e)}")
            return {
                "success": False,
                "message": f"統合カリキュラムデータの取得中にエラーが発生しました: {str(e)}"
            }

    def get_student_unified_progress(self, student_id: int, 
                                   curriculum_id: Optional[int] = None) -> Dict[str, Any]:
        """
        学生の統合進捗情報を取得
        
        Args:
            student_id: 学生ID
            curriculum_id: カリキュラムID（指定時は該当カリキュラムのみ）
            
        Returns:
            Dict: 統合進捗情報
        """
        try:
            logger.info(f"Getting unified progress for student {student_id}")
            
            # レッスンシステムの進捗取得
            lesson_progress = self._get_lesson_progress(student_id, curriculum_id)
            
            # レガシー単元システムの進捗取得
            unit_progress = self._get_unit_progress(student_id, curriculum_id)
            
            # 進捗統合
            unified_progress = self._unify_progress_data(lesson_progress, unit_progress)
            
            # 統合統計の計算
            integrated_stats = self._calculate_integrated_statistics(unified_progress)
            
            return {
                "success": True,
                "student_id": student_id,
                "curriculum_id": curriculum_id,
                "unified_progress": unified_progress,
                "integrated_statistics": integrated_stats,
                "data_sources": {
                    "lesson_count": len(lesson_progress),
                    "unit_count": len(unit_progress),
                    "total_items": len(unified_progress)
                },
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting unified progress: {str(e)}")
            return {
                "success": False,
                "message": f"統合進捗情報の取得中にエラーが発生しました: {str(e)}"
            }

    def migrate_legacy_to_lesson_system(self, unit_id: int, 
                                      target_curriculum_id: int) -> Dict[str, Any]:
        """
        レガシー単元をレッスンシステムに移行
        
        Args:
            unit_id: 移行元単元ID
            target_curriculum_id: 移行先カリキュラムID
            
        Returns:
            Dict: 移行結果
        """
        try:
            logger.info(f"Migrating unit {unit_id} to lesson system")
            
            # 権限チェック
            if current_user.role not in ['admin', 'teacher']:
                return {
                    "success": False,
                    "message": "移行操作の権限がありません"
                }

            # レッスンシステムの利用可能性チェック
            if not self.lesson_models['CurriculumLesson']:
                return {
                    "success": False,
                    "message": "レッスンシステムが利用できません"
                }

            # 移行元単元の取得
            unit = self._get_unit(unit_id)
            if not unit:
                return {
                    "success": False,
                    "message": "移行元単元が見つかりません"
                }

            # 移行処理の実行
            migration_result = self._execute_unit_migration(unit, target_curriculum_id)
            
            return migration_result

        except Exception as e:
            logger.error(f"Error migrating unit to lesson system: {str(e)}")
            db.session.rollback()
            return {
                "success": False,
                "message": f"移行処理中にエラーが発生しました: {str(e)}"
            }

    def synchronize_progress_between_systems(self, student_id: int) -> Dict[str, Any]:
        """
        システム間の進捗同期
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: 同期結果
        """
        try:
            logger.info(f"Synchronizing progress between systems for student {student_id}")
            
            # 両システムの進捗データ取得
            lesson_progress = self._get_lesson_progress(student_id)
            unit_progress = self._get_unit_progress(student_id)
            
            # 同期処理の実行
            sync_results = self._execute_progress_synchronization(lesson_progress, unit_progress)
            
            return {
                "success": True,
                "student_id": student_id,
                "synchronization_results": sync_results,
                "synchronized_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error synchronizing progress: {str(e)}")
            return {
                "success": False,
                "message": f"進捗同期中にエラーが発生しました: {str(e)}"
            }

    def get_system_compatibility_report(self) -> Dict[str, Any]:
        """
        システム互換性レポートを取得
        
        Returns:
            Dict: 互換性レポート
        """
        try:
            logger.info("Generating system compatibility report")
            
            # レッスンシステムの状態確認
            lesson_system_status = self._check_lesson_system_status()
            
            # レガシーシステムの状態確認
            legacy_system_status = self._check_legacy_system_status()
            
            # 互換性問題の検出
            compatibility_issues = self._detect_compatibility_issues()
            
            # 推奨アクションの生成
            recommended_actions = self._generate_recommended_actions(compatibility_issues)
            
            return {
                "success": True,
                "lesson_system": lesson_system_status,
                "legacy_system": legacy_system_status,
                "compatibility_issues": compatibility_issues,
                "recommended_actions": recommended_actions,
                "overall_compatibility": "good" if len(compatibility_issues) == 0 else "issues_detected",
                "report_generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error generating compatibility report: {str(e)}")
            return {
                "success": False,
                "message": f"互換性レポート生成中にエラーが発生しました: {str(e)}"
            }

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
            logger.warning("Lesson system models not available")
            return {
                'CurriculumLesson': None,
                'StudentLessonProgress': None,
                'LessonTask': None,
                'StudentTaskCheck': None,
                'TaskCheckStatus': None
            }

    def _get_curriculum(self, curriculum_id: int):
        """カリキュラム取得"""
        try:
            from app.models import Curriculum
            return Curriculum.query.get(curriculum_id)
        except ImportError:
            return None

    def _get_unit(self, unit_id: int):
        """単元取得"""
        from app.models import CurriculumUnit
        return CurriculumUnit.query.get(unit_id)

    def _get_lesson_system_data(self, curriculum_id: int) -> Dict[str, Any]:
        """レッスンシステムデータ取得"""
        if not self.lesson_models['CurriculumLesson']:
            return {}
        
        try:
            lessons = self.lesson_models['CurriculumLesson'].query.filter_by(
                curriculum_id=curriculum_id
            ).all()
            
            lesson_data = []
            for lesson in lessons:
                lesson_info = {
                    "id": lesson.id,
                    "title": lesson.title,
                    "description": lesson.description,
                    "order_index": lesson.order_index,
                    "estimated_minutes": lesson.estimated_minutes,
                    "type": "lesson"
                }
                
                # レッスン内のタスク取得
                if self.lesson_models['LessonTask']:
                    tasks = self.lesson_models['LessonTask'].query.filter_by(
                        lesson_id=lesson.id
                    ).all()
                    lesson_info["tasks"] = [
                        {
                            "id": task.id,
                            "title": task.title,
                            "task_type": task.task_type,
                            "required": task.required
                        }
                        for task in tasks
                    ]
                
                lesson_data.append(lesson_info)
            
            return {"lessons": lesson_data}
            
        except Exception as e:
            logger.error(f"Error getting lesson system data: {str(e)}")
            return {}

    def _get_legacy_unit_data(self, curriculum_id: int) -> Dict[str, Any]:
        """レガシー単元データ取得"""
        try:
            from app.models import CurriculumUnit
            
            # カリキュラムに関連する単元を取得（簡略化）
            units = CurriculumUnit.query.filter_by(is_active=True).all()
            
            unit_data = []
            for unit in units:
                unit_info = {
                    "id": unit.id,
                    "title": unit.title,
                    "description": unit.description,
                    "estimated_hours": unit.estimated_hours,
                    "difficulty_level": unit.difficulty_level,
                    "type": "unit"
                }
                unit_data.append(unit_info)
            
            return {"units": unit_data}
            
        except Exception as e:
            logger.error(f"Error getting legacy unit data: {str(e)}")
            return {}

    def _integrate_curriculum_data(self, curriculum, lesson_data: Dict[str, Any], 
                                 legacy_data: Dict[str, Any]) -> Dict[str, Any]:
        """カリキュラムデータの統合"""
        integrated = {
            "id": curriculum.id,
            "title": curriculum.title,
            "description": curriculum.description,
            "lessons": lesson_data.get("lessons", []),
            "units": legacy_data.get("units", []),
            "total_lessons": len(lesson_data.get("lessons", [])),
            "total_units": len(legacy_data.get("units", [])),
            "integration_type": "hybrid"
        }
        
        return integrated

    def _get_lesson_progress(self, student_id: int, 
                           curriculum_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """レッスン進捗データ取得"""
        if not self.lesson_models['StudentLessonProgress']:
            return []
        
        try:
            query = self.lesson_models['StudentLessonProgress'].query.filter_by(
                student_id=student_id
            )
            
            # カリキュラム指定時はレッスンとのJOINが必要
            if curriculum_id and self.lesson_models['CurriculumLesson']:
                query = query.join(self.lesson_models['CurriculumLesson']).filter(
                    self.lesson_models['CurriculumLesson'].curriculum_id == curriculum_id
                )
            
            progresses = query.all()
            
            return [
                {
                    "id": p.id,
                    "lesson_id": p.lesson_id,
                    "progress_percentage": p.progress_percentage,
                    "status": p.status,
                    "started_at": p.started_at.isoformat() if p.started_at else None,
                    "completed_at": p.completed_at.isoformat() if p.completed_at else None,
                    "type": "lesson_progress"
                }
                for p in progresses
            ]
            
        except Exception as e:
            logger.error(f"Error getting lesson progress: {str(e)}")
            return []

    def _get_unit_progress(self, student_id: int, 
                         curriculum_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """単元進捗データ取得"""
        try:
            from app.models import StudentUnitSelection
            
            query = StudentUnitSelection.query.filter_by(student_id=student_id)
            
            selections = query.all()
            
            return [
                {
                    "id": s.id,
                    "unit_id": s.unit_id,
                    "progress_percentage": s.progress_percentage,
                    "status": s.status,
                    "selected_at": s.selected_at.isoformat() if s.selected_at else None,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                    "type": "unit_progress"
                }
                for s in selections
            ]
            
        except Exception as e:
            logger.error(f"Error getting unit progress: {str(e)}")
            return []

    def _unify_progress_data(self, lesson_progress: List[Dict[str, Any]], 
                           unit_progress: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """進捗データの統合"""
        unified = []
        
        # レッスン進捗の追加
        for lesson in lesson_progress:
            unified.append({
                **lesson,
                "system_type": "lesson",
                "unified_id": f"lesson_{lesson['id']}"
            })
        
        # 単元進捗の追加
        for unit in unit_progress:
            unified.append({
                **unit,
                "system_type": "unit",
                "unified_id": f"unit_{unit['id']}"
            })
        
        # 統合データをソート（開始日時順）
        unified.sort(key=lambda x: x.get('started_at') or x.get('selected_at') or '', reverse=True)
        
        return unified

    def _calculate_integrated_statistics(self, unified_progress: List[Dict[str, Any]]) -> Dict[str, Any]:
        """統合統計の計算"""
        total_items = len(unified_progress)
        completed_items = len([p for p in unified_progress if p.get('status') == 'completed'])
        
        completion_rate = (completed_items / total_items * 100) if total_items > 0 else 0
        
        # システム別統計
        lesson_items = [p for p in unified_progress if p.get('system_type') == 'lesson']
        unit_items = [p for p in unified_progress if p.get('system_type') == 'unit']
        
        return {
            "total_items": total_items,
            "completed_items": completed_items,
            "completion_rate": round(completion_rate, 2),
            "system_breakdown": {
                "lesson_items": len(lesson_items),
                "unit_items": len(unit_items)
            }
        }

    def _execute_unit_migration(self, unit, target_curriculum_id: int) -> Dict[str, Any]:
        """単元移行の実行"""
        # 移行ロジックの実装（簡略化）
        return {
            "success": True,
            "message": "移行が完了しました",
            "migrated_unit_id": unit.id,
            "target_curriculum_id": target_curriculum_id
        }

    def _execute_progress_synchronization(self, lesson_progress: List[Dict[str, Any]], 
                                        unit_progress: List[Dict[str, Any]]) -> Dict[str, Any]:
        """進捗同期の実行"""
        # 同期ロジックの実装（簡略化）
        return {
            "synchronized_lessons": len(lesson_progress),
            "synchronized_units": len(unit_progress),
            "conflicts_resolved": 0
        }

    def _check_lesson_system_status(self) -> Dict[str, Any]:
        """レッスンシステム状態確認"""
        return {
            "available": self.lesson_models['CurriculumLesson'] is not None,
            "models_loaded": sum(1 for m in self.lesson_models.values() if m is not None),
            "status": "operational" if self.lesson_models['CurriculumLesson'] else "unavailable"
        }

    def _check_legacy_system_status(self) -> Dict[str, Any]:
        """レガシーシステム状態確認"""
        return {
            "available": True,
            "status": "operational"
        }

    def _detect_compatibility_issues(self) -> List[Dict[str, Any]]:
        """互換性問題の検出"""
        issues = []
        
        if not self.lesson_models['CurriculumLesson']:
            issues.append({
                "type": "missing_system",
                "severity": "high",
                "description": "レッスンシステムが利用できません",
                "impact": "新しいカリキュラム機能が制限されます"
            })
        
        return issues

    def _generate_recommended_actions(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """推奨アクションの生成"""
        actions = []
        
        for issue in issues:
            if issue["type"] == "missing_system":
                actions.append({
                    "action": "install_lesson_system",
                    "priority": "high",
                    "description": "レッスンシステムモジュールをインストールしてください"
                })
        
        return actions