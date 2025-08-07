"""
同期実行サービス

実際の同期処理、状態管理、通知を担当
"""
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from flask import current_app
from sqlalchemy import and_, func

from app.models import Class, Curriculum, CurriculumUnit, StudentUnitSelection, User
from app.services.curriculum_bridge_service import CurriculumBridgeService
from extensions import db

logger = logging.getLogger(__name__)


class SyncStatus(Enum):
    """同期ステータス"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


class SyncExecutorService:
    """同期実行専門サービス"""

    def execute_auto_sync(
        self, curriculum_id: int, trigger_type: str, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        自動同期を実行
        
        Args:
            curriculum_id: カリキュラムID
            trigger_type: トリガータイプ
            user_id: 実行ユーザーID
            
        Returns:
            Dict: 同期結果
        """
        try:
            # 同期中チェック
            if self.is_sync_in_progress(curriculum_id):
                return {
                    "success": False,
                    "message": "別の同期が実行中です",
                    "status": SyncStatus.IN_PROGRESS.value,
                }

            # 同期ログ作成
            sync_log_id = self.create_sync_log(curriculum_id, trigger_type, user_id)

            # 状態を実行中に更新
            self._update_sync_status(curriculum_id, SyncStatus.IN_PROGRESS)

            # カリキュラムブリッジサービスを使用して同期
            bridge_service = CurriculumBridgeService()
            result = bridge_service.sync_curriculum_to_classes(curriculum_id, user_id)

            if result["success"]:
                # 同期完了
                self._update_sync_status(curriculum_id, SyncStatus.COMPLETED)
                self.complete_sync_log(sync_log_id, SyncStatus.COMPLETED, result)
                
                # 通知送信
                self.send_sync_notification(
                    curriculum_id,
                    "sync_completed",
                    {
                        "trigger_type": trigger_type,
                        "synced_classes": result.get("synced_classes", 0),
                        "updated_units": result.get("updated_units", 0),
                    },
                )
                
                return {
                    "success": True,
                    "message": "同期が完了しました",
                    "sync_log_id": sync_log_id,
                    "details": result,
                }
            else:
                # 同期失敗
                self._update_sync_status(curriculum_id, SyncStatus.FAILED)
                self.complete_sync_log(sync_log_id, SyncStatus.FAILED, result)
                
                return {
                    "success": False,
                    "message": result.get("message", "同期に失敗しました"),
                    "sync_log_id": sync_log_id,
                    "details": result,
                }

        except Exception as e:
            logger.error(f"Error executing auto sync: {str(e)}")
            self._update_sync_status(curriculum_id, SyncStatus.FAILED)
            
            if "sync_log_id" in locals():
                self.complete_sync_log(
                    sync_log_id, SyncStatus.FAILED, {"error": str(e)}
                )
                
            return {
                "success": False,
                "message": f"同期エラー: {str(e)}",
                "status": SyncStatus.FAILED.value,
            }

    def create_sync_log(
        self, curriculum_id: int, trigger_type: str, user_id: Optional[int] = None
    ) -> int:
        """
        同期ログを作成
        
        Args:
            curriculum_id: カリキュラムID
            trigger_type: トリガータイプ
            user_id: 実行ユーザーID
            
        Returns:
            int: 同期ログID
        """
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                raise ValueError("カリキュラムが見つかりません")

            # 同期前の状態をキャプチャ
            pre_sync_state = self.capture_curriculum_state(curriculum_id)

            # ログデータを作成
            log_entry = {
                "id": datetime.utcnow().timestamp(),  # 一時的なID
                "curriculum_id": curriculum_id,
                "trigger_type": trigger_type,
                "user_id": user_id,
                "started_at": datetime.utcnow().isoformat(),
                "status": SyncStatus.IN_PROGRESS.value,
                "pre_sync_state": pre_sync_state,
            }

            # curriculum_dataに同期ログを追加
            data = json.loads(curriculum.curriculum_data) if curriculum.curriculum_data else {}
            if "sync_logs" not in data:
                data["sync_logs"] = []
            data["sync_logs"].append(log_entry)
            
            # 最新10件のみ保持
            data["sync_logs"] = data["sync_logs"][-10:]
            
            curriculum.curriculum_data = json.dumps(data, ensure_ascii=False)
            db.session.commit()

            logger.info(f"Sync log created for curriculum {curriculum_id}")
            return int(log_entry["id"])

        except Exception as e:
            logger.error(f"Error creating sync log: {str(e)}")
            db.session.rollback()
            raise

    def complete_sync_log(
        self, sync_log_id: int, status: SyncStatus, result: Dict[str, Any]
    ):
        """
        同期ログを完了
        
        Args:
            sync_log_id: 同期ログID
            status: 完了ステータス
            result: 同期結果
        """
        try:
            # すべてのカリキュラムから該当するログを検索
            curriculums = Curriculum.query.all()
            
            for curriculum in curriculums:
                if not curriculum.curriculum_data:
                    continue
                    
                data = json.loads(curriculum.curriculum_data)
                sync_logs = data.get("sync_logs", [])
                
                for log in sync_logs:
                    if int(log.get("id", 0)) == sync_log_id:
                        # ログを更新
                        log["completed_at"] = datetime.utcnow().isoformat()
                        log["status"] = status.value
                        log["result"] = result
                        
                        # 同期後の状態をキャプチャ
                        if status == SyncStatus.COMPLETED:
                            log["post_sync_state"] = self.capture_curriculum_state(
                                curriculum.id
                            )
                        
                        curriculum.curriculum_data = json.dumps(data, ensure_ascii=False)
                        db.session.commit()
                        
                        logger.info(f"Sync log {sync_log_id} completed with status {status.value}")
                        return

        except Exception as e:
            logger.error(f"Error completing sync log: {str(e)}")
            db.session.rollback()

    def is_sync_in_progress(self, curriculum_id: int) -> bool:
        """
        同期が実行中かを確認
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            bool: 実行中か
        """
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum or not curriculum.curriculum_data:
                return False

            data = json.loads(curriculum.curriculum_data)
            sync_metadata = data.get("sync_metadata", {})
            
            status = sync_metadata.get("current_status")
            if status == SyncStatus.IN_PROGRESS.value:
                # タイムアウトチェック（30分）
                last_update = sync_metadata.get("last_status_update")
                if last_update:
                    last_update_time = datetime.fromisoformat(last_update)
                    if datetime.utcnow() - last_update_time > timedelta(minutes=30):
                        # タイムアウトした同期をリセット
                        self._update_sync_status(curriculum_id, SyncStatus.FAILED)
                        return False
                return True
                
            return False

        except Exception as e:
            logger.error(f"Error checking sync progress: {str(e)}")
            return False

    def capture_curriculum_state(self, curriculum_id: int) -> Dict[str, Any]:
        """
        カリキュラムの現在状態をキャプチャ
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            Dict: 状態情報
        """
        try:
            # カリキュラム単元数
            unit_count = CurriculumUnit.query.filter_by(
                curriculum_id=curriculum_id
            ).count()

            # クラス割り当て数
            assigned_classes = (
                db.session.query(Class)
                .filter(Class.curriculum_id == curriculum_id)
                .count()
            )

            # アクティブな学生選択数
            active_selections = (
                db.session.query(StudentUnitSelection)
                .join(CurriculumUnit)
                .filter(CurriculumUnit.legacy_curriculum_id == curriculum_id)
                .count()
            )

            return {
                "captured_at": datetime.utcnow().isoformat(),
                "unit_count": unit_count,
                "assigned_classes": assigned_classes,
                "active_selections": active_selections,
            }

        except Exception as e:
            logger.error(f"Error capturing curriculum state: {str(e)}")
            return {}

    def send_sync_notification(
        self, curriculum_id: int, event_type: str, data: Dict[str, Any]
    ):
        """
        同期通知を送信
        
        Args:
            curriculum_id: カリキュラムID
            event_type: イベントタイプ
            data: 通知データ
        """
        try:
            # リアルタイム通知が有効な場合
            if hasattr(current_app, "socketio"):
                notification_data = {
                    "type": "sync_notification",
                    "event": event_type,
                    "curriculum_id": curriculum_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": data,
                }

                # 関連する教師に通知
                curriculum = Curriculum.query.get(curriculum_id)
                if curriculum:
                    current_app.socketio.emit(
                        "sync_update",
                        notification_data,
                        room=f"teacher_{curriculum.teacher_id}",
                    )

                logger.info(
                    f"Sync notification sent for curriculum {curriculum_id}: {event_type}"
                )

        except Exception as e:
            logger.error(f"Error sending sync notification: {str(e)}")

    # プライベートメソッド

    def _update_sync_status(self, curriculum_id: int, status: SyncStatus):
        """同期ステータスを更新"""
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return

            data = json.loads(curriculum.curriculum_data) if curriculum.curriculum_data else {}
            if "sync_metadata" not in data:
                data["sync_metadata"] = {}
                
            data["sync_metadata"]["current_status"] = status.value
            data["sync_metadata"]["last_status_update"] = datetime.utcnow().isoformat()
            
            curriculum.curriculum_data = json.dumps(data, ensure_ascii=False)
            db.session.commit()

        except Exception as e:
            logger.error(f"Error updating sync status: {str(e)}")
            db.session.rollback()