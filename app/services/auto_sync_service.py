# -*- coding: utf-8 -*-
"""
自動同期サービス (Phase7-4: リファクタリング版)

Phase7-4で4つの専門サービスに分割:
- SyncSchedulerService: スケジューリング・タイミング制御
- SyncExecutorService: 同期実行・状態管理・通知  
- ConflictResolverService: 競合検出・解決
- SyncValidatorService: 検証・エラー処理

このファイルは後方互換性を維持するためのファサードクラスです。
"""
import hashlib
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app
from sqlalchemy import and_, func, or_, text

from app.models import Class, Curriculum, CurriculumUnit, StudentUnitSelection, User
from app.services.curriculum_bridge_service import CurriculumBridgeService
from app.services.sync import (
    ConflictResolverService,
    SyncExecutorService,  
    SyncSchedulerService,
    SyncValidatorService
)
from extensions import db

logger = logging.getLogger(__name__)


class SyncTriggerType(Enum):
    """同期トリガーの種類"""
    MANUAL = "manual"
    AUTO_UPDATE = "auto_update"
    SCHEDULED = "scheduled"
    CONFLICT_RESOLUTION = "conflict_resolution"


class SyncStatus(Enum):
    """同期ステータス"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


class ChangeType(Enum):
    """変更タイプ"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MOVE = "move"


class AutoSyncService:
    """
    自動同期サービス (リファクタリング版)
    
    Phase7-4: 4つの専門サービスを統合するファサードクラス
    既存のインターフェースを100%維持しながら、内部実装を最適化
    """

    # 自動同期設定のデフォルト値
    DEFAULT_SYNC_SETTINGS = {
        "auto_sync_enabled": True,
        "sync_on_curriculum_update": True,
        "sync_on_item_change": True,
        "conflict_resolution_strategy": "prompt",
        "sync_delay_minutes": 5,
        "batch_sync_window": 30,
    }

    def __init__(self):
        """専門サービスを初期化"""
        self.scheduler = SyncSchedulerService()
        self.executor = SyncExecutorService()
        self.resolver = ConflictResolverService()
        self.validator = SyncValidatorService()

    @classmethod
    def enable_auto_sync_for_curriculum(
        cls, curriculum_id: int, user_id: int
    ) -> Dict[str, Any]:
        """カリキュラムの自動同期を有効化"""
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return {"success": False, "message": "カリキュラムが見つかりません"}

            # 権限チェック
            if curriculum.teacher_id != user_id:
                return {"success": False, "message": "権限がありません"}

            # 自動同期設定を追加/更新
            sync_settings = cls.DEFAULT_SYNC_SETTINGS.copy()
            sync_settings["enabled_by"] = user_id
            sync_settings["enabled_at"] = datetime.utcnow().isoformat()

            # curriculum_dataに同期設定を保存
            curriculum_data = (
                json.loads(curriculum.curriculum_data)
                if curriculum.curriculum_data
                else {}
            )
            curriculum_data["auto_sync_settings"] = sync_settings
            curriculum.curriculum_data = json.dumps(curriculum_data, ensure_ascii=False)

            db.session.commit()

            logger.info(
                f"Auto sync enabled for curriculum {curriculum_id} by user {user_id}"
            )
            return {
                "success": True,
                "message": "自動同期が有効になりました",
                "settings": sync_settings,
            }

        except Exception as e:
            logger.error(f"Error enabling auto sync: {str(e)}")
            db.session.rollback()
            return {"success": False, "message": str(e)}

    def detect_curriculum_changes(
        self, curriculum_id: int, previous_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """カリキュラムの変更を検知"""
        try:
            # 現在の状態をキャプチャ
            current_state = self.executor.capture_curriculum_state(curriculum_id)
            
            if not previous_state:
                # 前回の状態をデータベースから取得
                curriculum = Curriculum.query.get(curriculum_id)
                if curriculum and curriculum.curriculum_data:
                    data = json.loads(curriculum.curriculum_data)
                    previous_state = data.get("last_known_state", {})

            if not previous_state:
                return {
                    "has_changes": False,
                    "message": "比較する前回の状態がありません",
                    "current_state": current_state,
                }

            # 変更を分析
            changes = self._analyze_curriculum_changes(
                curriculum_id, previous_state, current_state
            )

            return {
                "has_changes": len(changes) > 0,
                "change_count": len(changes),
                "changes": changes,
                "current_state": current_state,
                "previous_state": previous_state,
            }

        except Exception as e:
            logger.error(f"Error detecting curriculum changes: {str(e)}")
            return {"has_changes": False, "error": str(e)}

    def should_auto_sync(self, curriculum_id: int, change_info: Dict[str, Any]) -> bool:
        """自動同期を実行すべきかを判定 (スケジューラーサービスに委譲)"""
        return self.scheduler.should_auto_sync(curriculum_id, change_info)

    def execute_auto_sync(
        self, curriculum_id: int, trigger_type: str, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """自動同期を実行 (エグゼキューターサービスに委譲)"""
        # 事前検証
        validation_result = self.validator.validate_sync_prerequisites(curriculum_id)
        if not validation_result["valid"]:
            return {
                "success": False,
                "message": "同期の前提条件を満たしていません",
                "validation_errors": validation_result["errors"],
            }

        # 競合チェック
        conflict_check = self.resolver.check_for_conflicts(curriculum_id, {})
        if conflict_check["has_conflicts"]:
            # 競合解決を試行
            resolution_result = self.resolver.handle_conflicts(
                curriculum_id,
                conflict_check["conflicts"],
                "auto",  # 自動解決を試行
                user_id
            )
            if not resolution_result["success"]:
                return {
                    "success": False,
                    "message": "競合の解決に失敗しました",
                    "conflicts": conflict_check["conflicts"],
                }

        # 同期実行
        result = self.executor.execute_auto_sync(curriculum_id, trigger_type, user_id)
        
        # 結果検証
        if result["success"]:
            validation_result = self.validator.validate_sync_result(
                curriculum_id, result["details"]
            )
            if not validation_result["valid"]:
                logger.warning(
                    f"Sync completed but validation failed: {validation_result['issues']}"
                )

        return result

    def _check_for_conflicts(
        self, curriculum_id: int, sync_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """競合をチェック (競合解決サービスに委譲)"""
        return self.resolver.check_for_conflicts(curriculum_id, sync_data)

    def _handle_conflicts(
        self,
        curriculum_id: int,
        conflicts: List[Dict[str, Any]],
        resolution_strategy: str = "prompt",
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """競合を処理 (競合解決サービスに委譲)"""
        return self.resolver.handle_conflicts(
            curriculum_id, conflicts, resolution_strategy, user_id
        )

    def _auto_resolve_conflicts(
        self, conflicts: List[Dict[str, Any]], curriculum_id: int
    ) -> Dict[str, Any]:
        """競合を自動解決 (競合解決サービスに委譲)"""
        return self.resolver.auto_resolve_conflicts(conflicts, curriculum_id)

    def _create_sync_log(
        self, curriculum_id: int, trigger_type: str, user_id: Optional[int] = None
    ) -> int:
        """同期ログを作成 (エグゼキューターサービスに委譲)"""
        return self.executor.create_sync_log(curriculum_id, trigger_type, user_id)

    def _complete_sync_log(
        self, sync_log_id: int, status: SyncStatus, result: Dict[str, Any]
    ):
        """同期ログを完了 (エグゼキューターサービスに委譲)"""
        self.executor.complete_sync_log(sync_log_id, status, result)

    def _update_sync_metadata(
        self, curriculum_id: int, metadata: Dict[str, Any]
    ):
        """同期メタデータを更新"""
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return

            data = json.loads(curriculum.curriculum_data) if curriculum.curriculum_data else {}
            data["sync_metadata"] = metadata
            curriculum.curriculum_data = json.dumps(data, ensure_ascii=False)
            db.session.commit()

        except Exception as e:
            logger.error(f"Error updating sync metadata: {str(e)}")
            db.session.rollback()

    def _is_sync_in_progress(self, curriculum_id: int) -> bool:
        """同期が実行中かを確認 (エグゼキューターサービスに委譲)"""
        return self.executor.is_sync_in_progress(curriculum_id)

    def _capture_curriculum_state(self, curriculum_id: int) -> Dict[str, Any]:
        """カリキュラムの現在状態をキャプチャ (エグゼキューターサービスに委譲)"""
        return self.executor.capture_curriculum_state(curriculum_id)

    def _send_sync_notification(
        self, curriculum_id: int, event_type: str, data: Dict[str, Any]
    ):
        """同期通知を送信 (エグゼキューターサービスに委譲)"""
        self.executor.send_sync_notification(curriculum_id, event_type, data)

    def get_sync_history(self, curriculum_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """同期履歴を取得"""
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum or not curriculum.curriculum_data:
                return []

            data = json.loads(curriculum.curriculum_data)
            sync_logs = data.get("sync_logs", [])
            
            # 最新のログから指定数を返す
            return sorted(sync_logs, key=lambda x: x.get("started_at", ""), reverse=True)[:limit]

        except Exception as e:
            logger.error(f"Error getting sync history: {str(e)}")
            return []

    def get_sync_settings(self, curriculum_id: int) -> Dict[str, Any]:
        """同期設定を取得"""
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return {}

            if not curriculum.curriculum_data:
                return self.DEFAULT_SYNC_SETTINGS.copy()

            data = json.loads(curriculum.curriculum_data)
            settings = data.get("auto_sync_settings", {})
            
            # デフォルト値とマージ
            merged_settings = self.DEFAULT_SYNC_SETTINGS.copy()
            merged_settings.update(settings)
            
            return merged_settings

        except Exception as e:
            logger.error(f"Error getting sync settings: {str(e)}")
            return self.DEFAULT_SYNC_SETTINGS.copy()

    def update_sync_settings(
        self, curriculum_id: int, settings: Dict[str, Any], user_id: int
    ) -> Dict[str, Any]:
        """同期設定を更新"""
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return {"success": False, "message": "カリキュラムが見つかりません"}

            # 権限チェック
            if curriculum.teacher_id != user_id:
                return {"success": False, "message": "権限がありません"}

            # 設定の検証
            validation_result = self.validator.validate_sync_settings(curriculum_id)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "message": "設定に不正な値が含まれています",
                    "validation_errors": validation_result["issues"],
                }

            # 設定を更新
            data = json.loads(curriculum.curriculum_data) if curriculum.curriculum_data else {}
            current_settings = data.get("auto_sync_settings", {})
            
            # 更新者と更新時刻を記録
            settings["updated_by"] = user_id
            settings["updated_at"] = datetime.utcnow().isoformat()
            
            current_settings.update(settings)
            data["auto_sync_settings"] = current_settings
            
            curriculum.curriculum_data = json.dumps(data, ensure_ascii=False)
            db.session.commit()

            logger.info(f"Sync settings updated for curriculum {curriculum_id} by user {user_id}")
            return {"success": True, "message": "設定が更新されました", "settings": current_settings}

        except Exception as e:
            logger.error(f"Error updating sync settings: {str(e)}")
            db.session.rollback()
            return {"success": False, "message": str(e)}

    # プライベートメソッド

    def _analyze_curriculum_changes(
        self,
        curriculum_id: int,
        previous_state: Dict[str, Any],
        current_state: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """カリキュラムの変更を分析"""
        changes = []

        try:
            # 単元数の変更
            prev_units = previous_state.get("unit_count", 0)
            curr_units = current_state.get("unit_count", 0)
            
            if prev_units != curr_units:
                changes.append({
                    "type": ChangeType.UPDATE.value,
                    "target": "unit_count",
                    "previous_value": prev_units,
                    "current_value": curr_units,
                    "change_magnitude": abs(curr_units - prev_units),
                })

            # クラス割り当ての変更
            prev_classes = previous_state.get("assigned_classes", 0)
            curr_classes = current_state.get("assigned_classes", 0)
            
            if prev_classes != curr_classes:
                changes.append({
                    "type": ChangeType.UPDATE.value,
                    "target": "assigned_classes",
                    "previous_value": prev_classes,
                    "current_value": curr_classes,
                    "change_magnitude": abs(curr_classes - prev_classes),
                })

            # 学生選択の変更
            prev_selections = previous_state.get("active_selections", 0)
            curr_selections = current_state.get("active_selections", 0)
            
            if prev_selections != curr_selections:
                changes.append({
                    "type": ChangeType.UPDATE.value,
                    "target": "active_selections",
                    "previous_value": prev_selections,
                    "current_value": curr_selections,
                    "change_magnitude": abs(curr_selections - prev_selections),
                })

            # 変更時刻を記録
            for change in changes:
                change["detected_at"] = datetime.utcnow().isoformat()
                change["curriculum_id"] = curriculum_id

        except Exception as e:
            logger.error(f"Error analyzing curriculum changes: {str(e)}")

        return changes