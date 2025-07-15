"""
スケジュール同期サービス

定期的な自動同期チェック・実行を管理します。
将来的にはCeleryやAPScheduler等のタスクスケジューラーと統合予定です。
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from flask import current_app

from app.models import Curriculum, User
from app.services.auto_sync_service import AutoSyncService, SyncTriggerType
from extensions import db

logger = logging.getLogger(__name__)


class ScheduledSyncService:
    """スケジュール同期サービス"""

    @classmethod
    def run_scheduled_sync_check(cls) -> Dict[str, any]:
        """
        スケジュール同期チェックの実行

        定期的に呼び出されて、自動同期が必要なカリキュラムを検出・実行します。
        """
        try:
            logger.info("Starting scheduled sync check")

            # 自動同期が有効になっているカリキュラムを取得
            sync_enabled_curriculums = cls._get_auto_sync_enabled_curriculums()

            sync_results = {
                "total_checked": len(sync_enabled_curriculums),
                "sync_executed": 0,
                "sync_successful": 0,
                "sync_failed": 0,
                "sync_conflicts": 0,
                "details": [],
            }

            for curriculum in sync_enabled_curriculums:
                try:
                    # 同期が必要かチェック
                    should_sync, sync_info = AutoSyncService.should_auto_sync(
                        curriculum.id
                    )

                    if should_sync:
                        sync_results["sync_executed"] += 1

                        # 自動同期を実行
                        result = AutoSyncService.execute_auto_sync(
                            curriculum.id, SyncTriggerType.SCHEDULED
                        )

                        if result["success"]:
                            sync_results["sync_successful"] += 1
                            logger.info(
                                f"Scheduled sync successful for curriculum {curriculum.id}"
                            )
                        elif result.get("requires_user_action"):
                            sync_results["sync_conflicts"] += 1
                            logger.warning(
                                f"Scheduled sync conflict for curriculum {curriculum.id}"
                            )
                        else:
                            sync_results["sync_failed"] += 1
                            logger.error(
                                f"Scheduled sync failed for curriculum {curriculum.id}"
                            )

                        sync_results["details"].append(
                            {
                                "curriculum_id": curriculum.id,
                                "curriculum_title": curriculum.title,
                                "teacher_id": curriculum.teacher_id,
                                "result": result,
                            }
                        )

                except Exception as e:
                    logger.error(
                        f"Scheduled sync error for curriculum {curriculum.id}: {str(e)}",
                        exc_info=True,
                    )
                    sync_results["sync_failed"] += 1
                    sync_results["details"].append(
                        {
                            "curriculum_id": curriculum.id,
                            "curriculum_title": curriculum.title,
                            "teacher_id": curriculum.teacher_id,
                            "error": str(e),
                        }
                    )

            logger.info(f"Scheduled sync check completed: {sync_results}")
            return {
                "success": True,
                "message": f'スケジュール同期チェック完了: {sync_results["sync_executed"]}件実行',
                "results": sync_results,
            }

        except Exception as e:
            logger.error(f"Scheduled sync check error: {str(e)}", exc_info=True)
            return {"success": False, "message": f"スケジュール同期チェック中にエラーが発生しました: {str(e)}"}

    @classmethod
    def _get_auto_sync_enabled_curriculums(cls) -> List[Curriculum]:
        """自動同期が有効なカリキュラムを取得"""
        try:
            # curriculum_dataに自動同期設定があるカリキュラムを取得
            curriculums = Curriculum.query.filter(
                Curriculum.curriculum_data.isnot(None)
            ).all()

            auto_sync_enabled = []

            for curriculum in curriculums:
                try:
                    import json

                    curriculum_data = (
                        json.loads(curriculum.curriculum_data)
                        if curriculum.curriculum_data
                        else {}
                    )
                    sync_settings = curriculum_data.get("auto_sync_settings", {})

                    if sync_settings.get("auto_sync_enabled", False):
                        auto_sync_enabled.append(curriculum)

                except (json.JSONDecodeError, TypeError):
                    continue

            return auto_sync_enabled

        except Exception as e:
            logger.error(
                f"Get auto sync enabled curriculums error: {str(e)}", exc_info=True
            )
            return []

    @classmethod
    def get_scheduled_sync_summary(cls) -> Dict[str, any]:
        """スケジュール同期の概要を取得"""
        try:
            # 自動同期が有効なカリキュラム数
            enabled_count = len(cls._get_auto_sync_enabled_curriculums())

            # 最近の同期実行状況（簡易実装）
            # 実際の運用では専用のログテーブルを使用
            recent_sync_count = 0
            pending_sync_count = 0

            # 有効なカリキュラムの同期必要性をチェック
            for curriculum in cls._get_auto_sync_enabled_curriculums():
                should_sync, _ = AutoSyncService.should_auto_sync(curriculum.id)
                if should_sync:
                    pending_sync_count += 1

                # 最近の同期実行をカウント（簡易実装）
                import json

                curriculum_data = (
                    json.loads(curriculum.curriculum_data)
                    if curriculum.curriculum_data
                    else {}
                )
                sync_logs = curriculum_data.get("sync_logs", [])

                # 過去24時間の同期をカウント
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                for log in sync_logs:
                    try:
                        started_at = datetime.fromisoformat(log["started_at"])
                        if (
                            started_at > cutoff_time
                            and log.get("trigger_type") == "scheduled"
                        ):
                            recent_sync_count += 1
                    except (ValueError, KeyError):
                        continue

            return {
                "enabled_curriculums": enabled_count,
                "pending_syncs": pending_sync_count,
                "recent_syncs_24h": recent_sync_count,
                "last_check": datetime.utcnow().isoformat(),
                "next_check": (
                    datetime.utcnow() + timedelta(hours=1)
                ).isoformat(),  # 1時間後
            }

        except Exception as e:
            logger.error(f"Scheduled sync summary error: {str(e)}", exc_info=True)
            return {
                "enabled_curriculums": 0,
                "pending_syncs": 0,
                "recent_syncs_24h": 0,
                "error": str(e),
            }

    @classmethod
    def setup_scheduled_sync(cls, interval_hours: int = 1) -> None:
        """
        スケジュール同期のセットアップ

        Args:
            interval_hours: チェック間隔（時間）

        Note:
            実際の運用では、Celery Beat、APScheduler、cron等を使用してください。
            これはデモンストレーション用の簡易実装です。
        """
        logger.info(f"Scheduled sync setup requested with {interval_hours}h interval")

        # 実装例（実際にはタスクスケジューラーを使用）:
        #
        # from celery import Celery
        # from celery.schedules import crontab
        #
        # app = Celery('questedt')
        #
        # @app.task
        # def scheduled_sync_task():
        #     return ScheduledSyncService.run_scheduled_sync_check()
        #
        # app.conf.beat_schedule = {
        #     'auto-sync-check': {
        #         'task': 'app.services.scheduled_sync_service.scheduled_sync_task',
        #         'schedule': crontab(minute=0),  # 毎時実行
        #     },
        # }

        # または APScheduler を使用:
        #
        # from apscheduler.schedulers.background import BackgroundScheduler
        #
        # scheduler = BackgroundScheduler()
        # scheduler.add_job(
        #     func=cls.run_scheduled_sync_check,
        #     trigger="interval",
        #     hours=interval_hours,
        #     id='auto_sync_check'
        # )
        # scheduler.start()

        logger.warning("Scheduled sync setup is not implemented in demo mode")

    @classmethod
    def test_scheduled_sync(cls) -> Dict[str, any]:
        """スケジュール同期のテスト実行"""
        try:
            logger.info("Running test scheduled sync")

            # 実際の同期は実行せず、チェックのみ
            sync_enabled_curriculums = cls._get_auto_sync_enabled_curriculums()

            test_results = {
                "enabled_curriculums": len(sync_enabled_curriculums),
                "curricula_details": [],
            }

            for curriculum in sync_enabled_curriculums:
                should_sync, sync_info = AutoSyncService.should_auto_sync(curriculum.id)

                test_results["curricula_details"].append(
                    {
                        "curriculum_id": curriculum.id,
                        "title": curriculum.title,
                        "teacher_id": curriculum.teacher_id,
                        "should_sync": should_sync,
                        "sync_info": sync_info,
                    }
                )

            return {
                "success": True,
                "message": "スケジュール同期テスト完了",
                "test_results": test_results,
            }

        except Exception as e:
            logger.error(f"Test scheduled sync error: {str(e)}", exc_info=True)
            return {"success": False, "message": f"テスト実行中にエラーが発生しました: {str(e)}"}
