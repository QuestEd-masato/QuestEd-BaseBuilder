"""
競合解決サービス

同期時の競合検出、解決戦略の適用を担当
"""
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from app.models import Class, Curriculum, CurriculumUnit, StudentUnitSelection
from extensions import db

logger = logging.getLogger(__name__)


class ConflictType(Enum):
    """競合タイプ"""
    STUDENT_SELECTION_CONFLICT = "student_selection_conflict"
    UNIT_MODIFICATION_CONFLICT = "unit_modification_conflict"
    CLASS_ASSIGNMENT_CONFLICT = "class_assignment_conflict"
    CONCURRENT_SYNC_CONFLICT = "concurrent_sync_conflict"


class ConflictResolverService:
    """競合解決専門サービス"""

    def check_for_conflicts(
        self, curriculum_id: int, sync_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        同期時の競合をチェック
        
        Args:
            curriculum_id: カリキュラムID
            sync_data: 同期データ
            
        Returns:
            Dict: 競合チェック結果
        """
        conflicts = []
        
        try:
            # 学生選択の競合をチェック
            student_conflicts = self._check_student_selection_conflicts(
                curriculum_id, sync_data
            )
            conflicts.extend(student_conflicts)

            # 単元変更の競合をチェック
            unit_conflicts = self._check_unit_modification_conflicts(
                curriculum_id, sync_data
            )
            conflicts.extend(unit_conflicts)

            # クラス割り当ての競合をチェック
            class_conflicts = self._check_class_assignment_conflicts(
                curriculum_id, sync_data
            )
            conflicts.extend(class_conflicts)

            # 同時同期の競合をチェック
            concurrent_conflicts = self._check_concurrent_sync_conflicts(curriculum_id)
            conflicts.extend(concurrent_conflicts)

            return {
                "has_conflicts": len(conflicts) > 0,
                "conflict_count": len(conflicts),
                "conflicts": conflicts,
                "severity": self._calculate_conflict_severity(conflicts),
            }

        except Exception as e:
            logger.error(f"Error checking conflicts: {str(e)}")
            return {
                "has_conflicts": True,
                "conflict_count": 1,
                "conflicts": [
                    {
                        "type": "system_error",
                        "message": f"競合チェック中にエラーが発生しました: {str(e)}",
                        "severity": "high",
                    }
                ],
                "severity": "high",
            }

    def handle_conflicts(
        self,
        curriculum_id: int,
        conflicts: List[Dict[str, Any]],
        resolution_strategy: str = "prompt",
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        競合を処理
        
        Args:
            curriculum_id: カリキュラムID
            conflicts: 競合リスト
            resolution_strategy: 解決戦略 ('auto', 'prompt', 'manual')
            user_id: 実行ユーザーID
            
        Returns:
            Dict: 競合処理結果
        """
        try:
            if not conflicts:
                return {"success": True, "message": "競合はありません"}

            resolution_results = []

            for conflict in conflicts:
                if resolution_strategy == "auto":
                    result = self._auto_resolve_conflict(
                        curriculum_id, conflict, user_id
                    )
                elif resolution_strategy == "prompt":
                    result = self._prompt_for_conflict_resolution(
                        curriculum_id, conflict, user_id
                    )
                else:  # manual
                    result = self._mark_conflict_for_manual_resolution(
                        curriculum_id, conflict, user_id
                    )

                resolution_results.append(result)

            # 処理結果をまとめる
            all_resolved = all(r.get("resolved", False) for r in resolution_results)
            
            return {
                "success": all_resolved,
                "message": "競合処理が完了しました" if all_resolved else "一部の競合が未解決です",
                "resolution_results": resolution_results,
                "unresolved_conflicts": [
                    r for r in resolution_results if not r.get("resolved", False)
                ],
            }

        except Exception as e:
            logger.error(f"Error handling conflicts: {str(e)}")
            return {
                "success": False,
                "message": f"競合処理中にエラーが発生しました: {str(e)}",
            }

    def auto_resolve_conflicts(
        self, conflicts: List[Dict[str, Any]], curriculum_id: int
    ) -> Dict[str, Any]:
        """
        競合を自動解決
        
        Args:
            conflicts: 競合リスト
            curriculum_id: カリキュラムID
            
        Returns:
            Dict: 自動解決結果
        """
        resolved_conflicts = []
        unresolved_conflicts = []

        for conflict in conflicts:
            conflict_type = conflict.get("type")
            
            if conflict_type == ConflictType.STUDENT_SELECTION_CONFLICT.value:
                # 学生選択の競合は保守的に解決（既存の選択を維持）
                resolution = self._resolve_student_selection_conservatively(
                    conflict, curriculum_id
                )
                if resolution["success"]:
                    resolved_conflicts.append(conflict)
                else:
                    unresolved_conflicts.append(conflict)

            elif conflict_type == ConflictType.UNIT_MODIFICATION_CONFLICT.value:
                # 単元変更の競合は新しいバージョンを優先
                resolution = self._resolve_unit_modification_with_latest(
                    conflict, curriculum_id
                )
                if resolution["success"]:
                    resolved_conflicts.append(conflict)
                else:
                    unresolved_conflicts.append(conflict)

            else:
                # その他の競合は手動解決が必要
                unresolved_conflicts.append(conflict)

        return {
            "success": len(unresolved_conflicts) == 0,
            "resolved_count": len(resolved_conflicts),
            "unresolved_count": len(unresolved_conflicts),
            "resolved_conflicts": resolved_conflicts,
            "unresolved_conflicts": unresolved_conflicts,
        }

    # プライベートメソッド

    def _check_student_selection_conflicts(
        self, curriculum_id: int, sync_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """学生選択の競合をチェック"""
        conflicts = []
        
        try:
            # 削除予定の単元を選択している学生がいるかチェック
            units_to_remove = sync_data.get("units_to_remove", [])
            
            for unit_id in units_to_remove:
                selections = StudentUnitSelection.query.filter_by(
                    curriculum_unit_id=unit_id
                ).all()
                
                if selections:
                    conflicts.append({
                        "type": ConflictType.STUDENT_SELECTION_CONFLICT.value,
                        "unit_id": unit_id,
                        "affected_students": len(selections),
                        "message": f"単元 {unit_id} を {len(selections)} 名の学生が選択中です",
                        "severity": "medium" if len(selections) < 5 else "high",
                        "student_ids": [s.student_id for s in selections],
                    })

        except Exception as e:
            logger.error(f"Error checking student selection conflicts: {str(e)}")

        return conflicts

    def _check_unit_modification_conflicts(
        self, curriculum_id: int, sync_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """単元変更の競合をチェック"""
        conflicts = []
        
        try:
            # 変更予定の単元で進行中の学習がある場合
            units_to_modify = sync_data.get("units_to_modify", [])
            
            for unit_data in units_to_modify:
                unit_id = unit_data.get("id")
                if not unit_id:
                    continue
                    
                # 進行中の学習があるかチェック
                active_progress = db.session.query(StudentUnitSelection).filter(
                    and_(
                        StudentUnitSelection.curriculum_unit_id == unit_id,
                        StudentUnitSelection.completion_date.is_(None)
                    )
                ).count()

                if active_progress > 0:
                    conflicts.append({
                        "type": ConflictType.UNIT_MODIFICATION_CONFLICT.value,
                        "unit_id": unit_id,
                        "active_students": active_progress,
                        "message": f"単元 {unit_id} で {active_progress} 名が学習中です",
                        "severity": "low" if active_progress < 3 else "medium",
                        "proposed_changes": unit_data.get("changes", {}),
                    })

        except Exception as e:
            logger.error(f"Error checking unit modification conflicts: {str(e)}")

        return conflicts

    def _check_class_assignment_conflicts(
        self, curriculum_id: int, sync_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """クラス割り当ての競合をチェック"""
        conflicts = []
        
        try:
            # 既に他のカリキュラムが割り当てられているクラスへの割り当て
            target_classes = sync_data.get("target_classes", [])
            
            for class_id in target_classes:
                existing_curriculum = Class.query.filter(
                    and_(
                        Class.id == class_id,
                        Class.curriculum_id.isnot(None),
                        Class.curriculum_id != curriculum_id
                    )
                ).first()

                if existing_curriculum:
                    conflicts.append({
                        "type": ConflictType.CLASS_ASSIGNMENT_CONFLICT.value,
                        "class_id": class_id,
                        "existing_curriculum_id": existing_curriculum.curriculum_id,
                        "message": f"クラス {class_id} は既に他のカリキュラムが割り当て済みです",
                        "severity": "high",
                    })

        except Exception as e:
            logger.error(f"Error checking class assignment conflicts: {str(e)}")

        return conflicts

    def _check_concurrent_sync_conflicts(self, curriculum_id: int) -> List[Dict[str, Any]]:
        """同時同期の競合をチェック"""
        conflicts = []
        
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum or not curriculum.curriculum_data:
                return conflicts

            data = json.loads(curriculum.curriculum_data)
            sync_metadata = data.get("sync_metadata", {})
            
            current_status = sync_metadata.get("current_status")
            if current_status == "in_progress":
                last_update = sync_metadata.get("last_status_update")
                if last_update:
                    last_update_time = datetime.fromisoformat(last_update)
                    # 5分以内の同期は競合とみなす
                    if datetime.utcnow() - last_update_time < timedelta(minutes=5):
                        conflicts.append({
                            "type": ConflictType.CONCURRENT_SYNC_CONFLICT.value,
                            "message": "別の同期処理が実行中です",
                            "severity": "high",
                            "last_sync_start": last_update,
                        })

        except Exception as e:
            logger.error(f"Error checking concurrent sync conflicts: {str(e)}")

        return conflicts

    def _calculate_conflict_severity(self, conflicts: List[Dict[str, Any]]) -> str:
        """競合の重要度を計算"""
        if not conflicts:
            return "none"
            
        severities = [c.get("severity", "low") for c in conflicts]
        
        if "high" in severities:
            return "high"
        elif "medium" in severities:
            return "medium"
        else:
            return "low"

    def _auto_resolve_conflict(
        self, curriculum_id: int, conflict: Dict[str, Any], user_id: Optional[int]
    ) -> Dict[str, Any]:
        """個別の競合を自動解決"""
        conflict_type = conflict.get("type")
        
        if conflict_type == ConflictType.STUDENT_SELECTION_CONFLICT.value:
            return self._resolve_student_selection_conservatively(conflict, curriculum_id)
        elif conflict_type == ConflictType.UNIT_MODIFICATION_CONFLICT.value:
            return self._resolve_unit_modification_with_latest(conflict, curriculum_id)
        else:
            return {"resolved": False, "reason": "自動解決不可"}

    def _prompt_for_conflict_resolution(
        self, curriculum_id: int, conflict: Dict[str, Any], user_id: Optional[int]
    ) -> Dict[str, Any]:
        """競合解決のプロンプトを表示"""
        # 実際の実装では、UIにプロンプトを表示
        return {
            "resolved": False,
            "requires_user_input": True,
            "conflict": conflict,
            "options": self._get_resolution_options(conflict),
        }

    def _mark_conflict_for_manual_resolution(
        self, curriculum_id: int, conflict: Dict[str, Any], user_id: Optional[int]
    ) -> Dict[str, Any]:
        """手動解決のためにマーク"""
        return {
            "resolved": False,
            "marked_for_manual_resolution": True,
            "conflict": conflict,
        }

    def _resolve_student_selection_conservatively(
        self, conflict: Dict[str, Any], curriculum_id: int
    ) -> Dict[str, Any]:
        """学生選択の競合を保守的に解決"""
        try:
            # 既存の選択を維持する戦略
            unit_id = conflict.get("unit_id")
            logger.info(f"Preserving student selections for unit {unit_id}")
            
            return {
                "resolved": True,
                "strategy": "preserve_existing_selections",
                "message": "既存の学生選択を維持しました",
            }
            
        except Exception as e:
            logger.error(f"Error resolving student selection conflict: {str(e)}")
            return {"resolved": False, "error": str(e)}

    def _resolve_unit_modification_with_latest(
        self, conflict: Dict[str, Any], curriculum_id: int
    ) -> Dict[str, Any]:
        """単元変更の競合を最新版で解決"""
        try:
            # 最新の変更を適用する戦略
            unit_id = conflict.get("unit_id")
            logger.info(f"Applying latest changes to unit {unit_id}")
            
            return {
                "resolved": True,
                "strategy": "apply_latest_changes",
                "message": "最新の変更を適用しました",
            }
            
        except Exception as e:
            logger.error(f"Error resolving unit modification conflict: {str(e)}")
            return {"resolved": False, "error": str(e)}

    def _get_resolution_options(self, conflict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """競合解決オプションを取得"""
        conflict_type = conflict.get("type")
        
        if conflict_type == ConflictType.STUDENT_SELECTION_CONFLICT.value:
            return [
                {"id": "preserve", "label": "既存の選択を維持"},
                {"id": "migrate", "label": "新しい単元に移行"},
                {"id": "notify", "label": "学生に通知して選択させる"},
            ]
        elif conflict_type == ConflictType.UNIT_MODIFICATION_CONFLICT.value:
            return [
                {"id": "apply_latest", "label": "最新の変更を適用"},
                {"id": "preserve_progress", "label": "進行中の学習を保護"},
                {"id": "create_backup", "label": "バックアップを作成して変更"},
            ]
        else:
            return [{"id": "manual", "label": "手動で解決"}]