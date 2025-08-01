"""
同期スケジューラーサービス

同期のタイミング制御、スケジューリング、遅延管理を担当
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from app.models import Curriculum
from extensions import db

logger = logging.getLogger(__name__)


class SyncSchedulerService:
    """同期スケジューリング専門サービス"""

    # デフォルトの遅延設定
    DEFAULT_SYNC_DELAY_MINUTES = 5
    DEFAULT_BATCH_SYNC_WINDOW = 30

    def should_auto_sync(self, curriculum_id: int, change_info: Dict[str, Any]) -> bool:
        """
        自動同期を実行すべきかを判定
        
        Args:
            curriculum_id: カリキュラムID
            change_info: 変更情報
            
        Returns:
            bool: 同期を実行すべきか
        """
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return False

            # 自動同期設定を取得
            sync_settings = self._get_sync_settings(curriculum)
            if not sync_settings.get("auto_sync_enabled", False):
                return False

            # 変更タイプに基づく判定
            change_type = change_info.get("change_type")
            if change_type == "curriculum_update" and not sync_settings.get(
                "sync_on_curriculum_update", True
            ):
                return False
            
            if change_type == "item_change" and not sync_settings.get(
                "sync_on_item_change", True
            ):
                return False

            # 同期遅延のチェック
            if self._is_within_delay_window(curriculum, change_info):
                return False

            # バッチ同期ウィンドウのチェック
            if self._should_batch_sync(curriculum, change_info):
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking auto sync eligibility: {str(e)}")
            return False

    def calculate_next_sync_time(self, curriculum: Curriculum) -> datetime:
        """
        次回同期時刻を計算
        
        Args:
            curriculum: カリキュラムオブジェクト
            
        Returns:
            datetime: 次回同期予定時刻
        """
        sync_settings = self._get_sync_settings(curriculum)
        delay_minutes = sync_settings.get(
            "sync_delay_minutes", self.DEFAULT_SYNC_DELAY_MINUTES
        )
        
        return datetime.utcnow() + timedelta(minutes=delay_minutes)

    def is_sync_scheduled(self, curriculum_id: int) -> bool:
        """
        同期がスケジュールされているかを確認
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            bool: スケジュール済みか
        """
        # TODO: スケジュールされた同期タスクの存在を確認
        # 現在の実装では、メタデータから最終同期時刻を参照
        curriculum = Curriculum.query.get(curriculum_id)
        if not curriculum:
            return False
            
        metadata = self._get_sync_metadata(curriculum)
        last_scheduled = metadata.get("last_scheduled_sync")
        
        if last_scheduled:
            last_scheduled_time = datetime.fromisoformat(last_scheduled)
            next_sync_time = self.calculate_next_sync_time(curriculum)
            return datetime.utcnow() < next_sync_time
            
        return False

    def schedule_sync(
        self, curriculum_id: int, trigger_type: str, delay_minutes: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        同期をスケジュール
        
        Args:
            curriculum_id: カリキュラムID
            trigger_type: トリガータイプ
            delay_minutes: 遅延時間（分）
            
        Returns:
            Dict: スケジュール結果
        """
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return {"success": False, "message": "カリキュラムが見つかりません"}

            sync_settings = self._get_sync_settings(curriculum)
            if delay_minutes is None:
                delay_minutes = sync_settings.get(
                    "sync_delay_minutes", self.DEFAULT_SYNC_DELAY_MINUTES
                )

            scheduled_time = datetime.utcnow() + timedelta(minutes=delay_minutes)
            
            # メタデータを更新
            metadata = self._get_sync_metadata(curriculum)
            metadata["last_scheduled_sync"] = scheduled_time.isoformat()
            metadata["scheduled_trigger_type"] = trigger_type
            self._update_sync_metadata(curriculum, metadata)
            
            db.session.commit()

            logger.info(
                f"Sync scheduled for curriculum {curriculum_id} at {scheduled_time}"
            )
            return {
                "success": True,
                "scheduled_time": scheduled_time.isoformat(),
                "delay_minutes": delay_minutes,
            }

        except Exception as e:
            logger.error(f"Error scheduling sync: {str(e)}")
            db.session.rollback()
            return {"success": False, "message": str(e)}

    # プライベートメソッド

    def _get_sync_settings(self, curriculum: Curriculum) -> Dict[str, Any]:
        """同期設定を取得"""
        import json
        
        if not curriculum.curriculum_data:
            return {}
            
        try:
            data = json.loads(curriculum.curriculum_data)
            return data.get("auto_sync_settings", {})
        except:
            return {}

    def _get_sync_metadata(self, curriculum: Curriculum) -> Dict[str, Any]:
        """同期メタデータを取得"""
        import json
        
        if not curriculum.curriculum_data:
            return {}
            
        try:
            data = json.loads(curriculum.curriculum_data)
            return data.get("sync_metadata", {})
        except:
            return {}

    def _update_sync_metadata(self, curriculum: Curriculum, metadata: Dict[str, Any]):
        """同期メタデータを更新"""
        import json
        
        data = json.loads(curriculum.curriculum_data) if curriculum.curriculum_data else {}
        data["sync_metadata"] = metadata
        curriculum.curriculum_data = json.dumps(data, ensure_ascii=False)

    def _is_within_delay_window(self, curriculum: Curriculum, change_info: Dict[str, Any]) -> bool:
        """遅延ウィンドウ内かをチェック"""
        sync_settings = self._get_sync_settings(curriculum)
        delay_minutes = sync_settings.get(
            "sync_delay_minutes", self.DEFAULT_SYNC_DELAY_MINUTES
        )
        
        change_time = change_info.get("change_time")
        if not change_time:
            return False
            
        if isinstance(change_time, str):
            change_time = datetime.fromisoformat(change_time)
            
        elapsed = datetime.utcnow() - change_time
        return elapsed < timedelta(minutes=delay_minutes)

    def _should_batch_sync(self, curriculum: Curriculum, change_info: Dict[str, Any]) -> bool:
        """バッチ同期すべきかを判定"""
        sync_settings = self._get_sync_settings(curriculum)
        batch_window = sync_settings.get(
            "batch_sync_window", self.DEFAULT_BATCH_SYNC_WINDOW
        )
        
        # 最近の変更が多い場合はバッチ同期を推奨
        metadata = self._get_sync_metadata(curriculum)
        recent_changes = metadata.get("recent_change_count", 0)
        
        return recent_changes > 5 and batch_window > 0