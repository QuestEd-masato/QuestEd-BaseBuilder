"""
同期バックグラウンドタスク

Celeryを使用したカリキュラム・単元の非同期同期処理
"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from app.tasks import CELERY_AVAILABLE, celery

logger = logging.getLogger(__name__)

if CELERY_AVAILABLE:

    @celery.task(bind=True, name="sync_tasks.execute_curriculum_sync")
    def execute_curriculum_sync(
        self,
        curriculum_id: int,
        trigger_type: str = "manual",
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        カリキュラム同期のバックグラウンドタスク

        Args:
            curriculum_id: カリキュラムID
            trigger_type: 同期トリガータイプ
            user_id: 実行ユーザーID（オプション）

        Returns:
            同期結果の辞書
        """
        try:
            from app.realtime import RealtimeSyncNotifier
            from app.services.auto_sync_service import AutoSyncService, SyncTriggerType

            # タスク開始ログ
            logger.info(
                f"Starting background curriculum sync: {curriculum_id} (trigger: {trigger_type})"
            )

            # 進捗通知
            self.update_state(
                state="PROGRESS",
                meta={"current": 0, "total": 100, "status": "同期を開始しています..."},
            )

            # 同期トリガータイプの変換
            try:
                sync_trigger = SyncTriggerType(trigger_type)
            except ValueError:
                sync_trigger = SyncTriggerType.MANUAL

            # 進捗通知: 準備完了
            self.update_state(
                state="PROGRESS",
                meta={"current": 20, "total": 100, "status": "同期準備中..."},
            )

            # リアルタイム通知
            RealtimeSyncNotifier.notify_sync_progress(
                curriculum_id, user_id or 0, {"percentage": 20, "status": "同期準備中..."}
            )

            # 実際の同期実行
            sync_result = AutoSyncService.execute_auto_sync(curriculum_id, sync_trigger)

            # 進捗通知: 同期実行中
            self.update_state(
                state="PROGRESS",
                meta={"current": 80, "total": 100, "status": "同期実行中..."},
            )

            # リアルタイム通知
            RealtimeSyncNotifier.notify_sync_progress(
                curriculum_id, user_id or 0, {"percentage": 80, "status": "同期実行中..."}
            )

            # 結果の処理
            if sync_result.get("success"):
                # 成功時
                self.update_state(
                    state="SUCCESS",
                    meta={
                        "current": 100,
                        "total": 100,
                        "status": "同期完了",
                        "result": sync_result,
                    },
                )

                logger.info(
                    f"Background curriculum sync completed successfully: {curriculum_id}"
                )

                return {
                    "success": True,
                    "message": "背景同期が正常に完了しました",
                    "curriculum_id": curriculum_id,
                    "sync_result": sync_result,
                    "task_id": self.request.id,
                    "completed_at": datetime.utcnow().isoformat(),
                }
            else:
                # 失敗時
                error_message = sync_result.get("message", "不明なエラー")
                logger.error(
                    f"Background curriculum sync failed: {curriculum_id} - {error_message}"
                )

                self.update_state(
                    state="FAILURE",
                    meta={
                        "current": 100,
                        "total": 100,
                        "status": f"同期失敗: {error_message}",
                        "error": error_message,
                    },
                )

                return {
                    "success": False,
                    "message": f"背景同期に失敗しました: {error_message}",
                    "curriculum_id": curriculum_id,
                    "error": error_message,
                    "task_id": self.request.id,
                    "failed_at": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"Background curriculum sync error: {curriculum_id} - {error_msg}",
                exc_info=True,
            )

            # エラー状態の更新
            self.update_state(
                state="FAILURE",
                meta={
                    "current": 100,
                    "total": 100,
                    "status": f"エラー: {error_msg}",
                    "error": error_msg,
                },
            )

            # リアルタイム通知
            try:
                from app.realtime import RealtimeSyncNotifier

                RealtimeSyncNotifier.notify_sync_conflict(
                    curriculum_id,
                    user_id or 0,
                    {"error": error_msg, "type": "task_error"},
                )
            except Exception:
                pass  # 通知に失敗してもタスク自体は継続

            return {
                "success": False,
                "message": f"背景同期でエラーが発生しました: {error_msg}",
                "curriculum_id": curriculum_id,
                "error": error_msg,
                "task_id": self.request.id,
                "failed_at": datetime.utcnow().isoformat(),
            }

    @celery.task(bind=True, name="sync_tasks.batch_curriculum_sync")
    def batch_curriculum_sync(
        self,
        curriculum_ids: list,
        trigger_type: str = "manual",
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        複数カリキュラムの一括同期バックグラウンドタスク

        Args:
            curriculum_ids: カリキュラムIDのリスト
            trigger_type: 同期トリガータイプ
            user_id: 実行ユーザーID（オプション）

        Returns:
            一括同期結果の辞書
        """
        try:
            logger.info(
                f"Starting batch curriculum sync: {len(curriculum_ids)} curricula (trigger: {trigger_type})"
            )

            total_curricula = len(curriculum_ids)
            completed = 0
            successful = 0
            failed = 0
            results = []

            # 初期進捗通知
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": 0,
                    "total": total_curricula,
                    "status": f"一括同期を開始しています... (0/{total_curricula})",
                    "completed": 0,
                    "successful": 0,
                    "failed": 0,
                },
            )

            # 各カリキュラムを順次処理
            for i, curriculum_id in enumerate(curriculum_ids):
                try:
                    # 個別同期実行
                    sync_result = execute_curriculum_sync.apply_async(
                        args=[curriculum_id, trigger_type, user_id]
                    ).get(
                        timeout=300
                    )  # 5分タイムアウト

                    results.append(
                        {"curriculum_id": curriculum_id, "result": sync_result}
                    )

                    if sync_result.get("success"):
                        successful += 1
                    else:
                        failed += 1

                    completed += 1

                    # 進捗更新
                    progress_percentage = int((completed / total_curricula) * 100)
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "current": completed,
                            "total": total_curricula,
                            "status": f"同期中... ({completed}/{total_curricula})",
                            "completed": completed,
                            "successful": successful,
                            "failed": failed,
                            "percentage": progress_percentage,
                        },
                    )

                    # リアルタイム通知
                    try:
                        from app.realtime import RealtimeSyncNotifier

                        RealtimeSyncNotifier.notify_sync_progress(
                            0,  # 一括処理なので特定のカリキュラムIDはなし
                            user_id or 0,
                            {
                                "type": "batch_progress",
                                "completed": completed,
                                "total": total_curricula,
                                "successful": successful,
                                "failed": failed,
                                "percentage": progress_percentage,
                            },
                        )
                    except Exception:
                        pass  # 通知失敗は無視

                except Exception as e:
                    error_msg = str(e)
                    logger.error(
                        f"Batch sync error for curriculum {curriculum_id}: {error_msg}"
                    )

                    results.append(
                        {
                            "curriculum_id": curriculum_id,
                            "result": {
                                "success": False,
                                "error": error_msg,
                                "message": f"同期エラー: {error_msg}",
                            },
                        }
                    )

                    failed += 1
                    completed += 1

            # 最終結果
            final_result = {
                "success": failed == 0,  # 失敗がなければ成功
                "message": f"一括同期完了: {successful}件成功, {failed}件失敗",
                "total_processed": total_curricula,
                "successful_count": successful,
                "failed_count": failed,
                "results": results,
                "task_id": self.request.id,
                "completed_at": datetime.utcnow().isoformat(),
            }

            # 最終状態更新
            self.update_state(
                state="SUCCESS",
                meta={
                    "current": total_curricula,
                    "total": total_curricula,
                    "status": "一括同期完了",
                    "completed": completed,
                    "successful": successful,
                    "failed": failed,
                    "percentage": 100,
                    "final_result": final_result,
                },
            )

            logger.info(
                f"Batch curriculum sync completed: {successful}/{total_curricula} successful"
            )

            return final_result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Batch curriculum sync error: {error_msg}", exc_info=True)

            self.update_state(
                state="FAILURE",
                meta={
                    "current": 0,
                    "total": len(curriculum_ids),
                    "status": f"一括同期エラー: {error_msg}",
                    "error": error_msg,
                },
            )

            return {
                "success": False,
                "message": f"一括同期でエラーが発生しました: {error_msg}",
                "error": error_msg,
                "task_id": self.request.id,
                "failed_at": datetime.utcnow().isoformat(),
            }

    @celery.task(name="sync_tasks.scheduled_sync_check")
    def scheduled_sync_check() -> Dict[str, Any]:
        """
        スケジュール同期チェックのバックグラウンドタスク

        Returns:
            スケジュール同期チェック結果
        """
        try:
            from app.services.scheduled_sync_service import ScheduledSyncService

            logger.info("Starting scheduled sync check")

            # スケジュール同期チェック実行
            check_result = ScheduledSyncService.run_scheduled_sync_check()

            logger.info(
                f"Scheduled sync check completed: {check_result.get('message', 'No message')}"
            )

            return {
                "success": True,
                "message": "スケジュール同期チェック完了",
                "check_result": check_result,
                "executed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Scheduled sync check error: {error_msg}", exc_info=True)

            return {
                "success": False,
                "message": f"スケジュール同期チェックでエラーが発生しました: {error_msg}",
                "error": error_msg,
                "executed_at": datetime.utcnow().isoformat(),
            }

else:
    # Celeryが利用できない場合のフォールバック関数
    def execute_curriculum_sync(
        curriculum_id: int, trigger_type: str = "manual", user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """同期フォールバック処理（同期実行）"""
        logger.warning("Celery not available - executing sync synchronously")

        try:
            from app.services.auto_sync_service import AutoSyncService, SyncTriggerType

            # 同期トリガータイプの変換
            try:
                sync_trigger = SyncTriggerType(trigger_type)
            except ValueError:
                sync_trigger = SyncTriggerType.MANUAL

            # 同期実行
            result = AutoSyncService.execute_auto_sync(curriculum_id, sync_trigger)

            return {
                "success": result.get("success", False),
                "message": "同期実行完了（同期モード）",
                "curriculum_id": curriculum_id,
                "sync_result": result,
                "executed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"同期実行エラー: {str(e)}",
                "curriculum_id": curriculum_id,
                "error": str(e),
                "executed_at": datetime.utcnow().isoformat(),
            }

    def batch_curriculum_sync(
        curriculum_ids: list,
        trigger_type: str = "manual",
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """一括同期フォールバック処理（同期実行）"""
        logger.warning("Celery not available - executing batch sync synchronously")

        results = []
        successful = 0
        failed = 0

        for curriculum_id in curriculum_ids:
            result = execute_curriculum_sync(curriculum_id, trigger_type, user_id)
            results.append({"curriculum_id": curriculum_id, "result": result})

            if result.get("success"):
                successful += 1
            else:
                failed += 1

        return {
            "success": failed == 0,
            "message": f"一括同期完了（同期モード）: {successful}件成功, {failed}件失敗",
            "total_processed": len(curriculum_ids),
            "successful_count": successful,
            "failed_count": failed,
            "results": results,
            "executed_at": datetime.utcnow().isoformat(),
        }

    def scheduled_sync_check() -> Dict[str, Any]:
        """スケジュール同期チェックフォールバック処理"""
        logger.warning(
            "Celery not available - executing scheduled sync check synchronously"
        )

        try:
            from app.services.scheduled_sync_service import ScheduledSyncService

            result = ScheduledSyncService.run_scheduled_sync_check()

            return {
                "success": True,
                "message": "スケジュール同期チェック完了（同期モード）",
                "check_result": result,
                "executed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"スケジュール同期チェックエラー: {str(e)}",
                "error": str(e),
                "executed_at": datetime.utcnow().isoformat(),
            }


# 同期タスクのユーティリティ関数
class SyncTaskManager:
    """同期タスク管理クラス"""

    @staticmethod
    def start_background_sync(
        curriculum_id: int, trigger_type: str = "manual", user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        バックグラウンド同期の開始

        Returns:
            タスク情報または実行結果
        """
        if CELERY_AVAILABLE:
            # Celeryタスクとして実行
            task = execute_curriculum_sync.delay(curriculum_id, trigger_type, user_id)

            return {
                "task_id": task.id,
                "status": "PENDING",
                "message": "バックグラウンド同期を開始しました",
                "curriculum_id": curriculum_id,
                "is_async": True,
            }
        else:
            # 同期実行
            result = execute_curriculum_sync(curriculum_id, trigger_type, user_id)

            return {
                "task_id": None,
                "status": "COMPLETED",
                "message": result.get("message", "同期完了"),
                "curriculum_id": curriculum_id,
                "result": result,
                "is_async": False,
            }

    @staticmethod
    def start_batch_sync(
        curriculum_ids: list,
        trigger_type: str = "manual",
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        一括バックグラウンド同期の開始

        Returns:
            タスク情報または実行結果
        """
        if CELERY_AVAILABLE:
            # Celeryタスクとして実行
            task = batch_curriculum_sync.delay(curriculum_ids, trigger_type, user_id)

            return {
                "task_id": task.id,
                "status": "PENDING",
                "message": f"{len(curriculum_ids)}件の一括同期を開始しました",
                "curriculum_count": len(curriculum_ids),
                "is_async": True,
            }
        else:
            # 同期実行
            result = batch_curriculum_sync(curriculum_ids, trigger_type, user_id)

            return {
                "task_id": None,
                "status": "COMPLETED",
                "message": result.get("message", "一括同期完了"),
                "curriculum_count": len(curriculum_ids),
                "result": result,
                "is_async": False,
            }

    @staticmethod
    def get_task_status(task_id: str) -> Dict[str, Any]:
        """
        タスクステータスの取得

        Returns:
            タスクステータス情報
        """
        if not CELERY_AVAILABLE or not task_id:
            return {
                "task_id": task_id,
                "status": "UNKNOWN",
                "message": "タスクの状態を取得できません",
            }

        try:
            from celery.result import AsyncResult

            task_result = AsyncResult(task_id, app=celery)

            status_info = {
                "task_id": task_id,
                "status": task_result.status,
                "ready": task_result.ready(),
                "successful": task_result.successful() if task_result.ready() else None,
            }

            if task_result.info:
                if isinstance(task_result.info, dict):
                    status_info.update(task_result.info)
                else:
                    status_info["info"] = str(task_result.info)

            if task_result.ready():
                if task_result.successful():
                    status_info["result"] = task_result.result
                else:
                    status_info["error"] = str(task_result.info)

            return status_info

        except Exception as e:
            return {
                "task_id": task_id,
                "status": "ERROR",
                "error": str(e),
                "message": "タスクステータス取得エラー",
            }
