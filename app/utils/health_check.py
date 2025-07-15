"""
QuestEd ヘルスチェック機能

アプリケーションの健全性を監視し、デプロイメント時の品質保証を行います。

Author: QuestEd Development Team
Created: 2025-01-15
Version: 1.0.0
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from flask import Response, current_app, jsonify
from sqlalchemy import text

from extensions import db


class HealthChecker:
    """ヘルスチェック実行クラス"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.checks = {
            "database": self._check_database,
            "ranking_service": self._check_ranking_service,
            "cache_system": self._check_cache_system,
            "api_endpoints": self._check_api_endpoints,
            "security_headers": self._check_security_headers,
            "memory_usage": self._check_memory_usage,
        }

    def run_all_checks(self) -> Dict[str, Any]:
        """
        全てのヘルスチェックを実行

        Returns:
            Dict: チェック結果の辞書
        """
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy",
            "checks": {},
            "summary": {
                "total_checks": len(self.checks),
                "passed": 0,
                "failed": 0,
                "warnings": 0,
            },
        }

        for check_name, check_func in self.checks.items():
            try:
                start_time = time.time()
                status, message, details = check_func()
                duration = time.time() - start_time

                results["checks"][check_name] = {
                    "status": status,
                    "message": message,
                    "details": details,
                    "duration_ms": round(duration * 1000, 2),
                }

                # 統計更新
                if status == "healthy":
                    results["summary"]["passed"] += 1
                elif status == "warning":
                    results["summary"]["warnings"] += 1
                else:
                    results["summary"]["failed"] += 1
                    results["overall_status"] = "unhealthy"

            except Exception as e:
                results["checks"][check_name] = {
                    "status": "error",
                    "message": f"チェック実行エラー: {str(e)}",
                    "details": {},
                    "duration_ms": 0,
                }
                results["summary"]["failed"] += 1
                results["overall_status"] = "unhealthy"

        return results

    def _check_database(self) -> Tuple[str, str, Dict]:
        """データベース接続とテーブル存在確認"""
        try:
            # 基本接続テスト
            db.session.execute(text("SELECT 1"))

            # 重要テーブルの存在確認
            required_tables = [
                "users",
                "rankings",
                "ranking_cache",
                "schools",
                "classes",
            ]
            existing_tables = []

            for table in required_tables:
                try:
                    result = db.session.execute(
                        text(f"SELECT COUNT(*) FROM {table}")
                    ).scalar()
                    existing_tables.append({"table": table, "count": result})
                except Exception as e:
                    return "error", f"テーブル {table} にアクセスできません", {"error": str(e)}

            return "healthy", "データベース接続正常", {"tables": existing_tables}

        except Exception as e:
            return "error", f"データベース接続エラー: {str(e)}", {}

    def _check_ranking_service(self) -> Tuple[str, str, Dict]:
        """ランキングサービスの動作確認"""
        try:
            from app.services.ranking_service import RankingService

            # 基本的なランキング計算テスト
            test_start = time.time()
            ranking_data = RankingService.get_ranking("total_points", "school", 1, 5)
            test_duration = time.time() - test_start

            # 結果検証
            if not isinstance(ranking_data, dict):
                return "error", "ランキングサービスが無効なデータを返しました", {}

            required_keys = ["rankings", "total_participants", "last_updated"]
            missing_keys = [key for key in required_keys if key not in ranking_data]

            if missing_keys:
                return "warning", f"ランキングデータに不足キー: {missing_keys}", ranking_data

            status = "healthy"
            message = "ランキングサービス正常"

            # パフォーマンス警告
            if test_duration > 2.0:
                status = "warning"
                message += f" (応答時間: {test_duration:.2f}秒 - 要最適化)"

            return (
                status,
                message,
                {
                    "response_time_ms": round(test_duration * 1000, 2),
                    "participants": ranking_data.get("total_participants", 0),
                    "ranking_count": len(ranking_data.get("rankings", [])),
                },
            )

        except Exception as e:
            return "error", f"ランキングサービスエラー: {str(e)}", {}

    def _check_cache_system(self) -> Tuple[str, str, Dict]:
        """キャッシュシステムの動作確認"""
        try:
            from app.models import RankingCache

            # キャッシュテーブルアクセステスト
            cache_count = RankingCache.query.count()

            # 期限切れキャッシュの確認
            expired_count = RankingCache.query.filter(
                RankingCache.expires_at < datetime.utcnow()
            ).count()

            status = "healthy"
            message = "キャッシュシステム正常"

            if expired_count > cache_count * 0.5:  # 50%以上が期限切れ
                status = "warning"
                message += f" (期限切れキャッシュ多数: {expired_count}/{cache_count})"

            return (
                status,
                message,
                {
                    "total_cache_entries": cache_count,
                    "expired_entries": expired_count,
                    "cache_hit_rate": max(
                        0, (cache_count - expired_count) / max(cache_count, 1)
                    ),
                },
            )

        except Exception as e:
            return "error", f"キャッシュシステムエラー: {str(e)}", {}

    def _check_api_endpoints(self) -> Tuple[str, str, Dict]:
        """重要APIエンドポイントの確認"""
        try:
            from flask import url_for

            # テスト対象エンドポイント
            critical_endpoints = [
                "api.get_ranking",
                "student.ranking",
                "student.api_ranking",
            ]

            endpoint_status = []
            for endpoint in critical_endpoints:
                try:
                    url = url_for(
                        endpoint, ranking_type="total_points", _external=False
                    )
                    endpoint_status.append(
                        {"endpoint": endpoint, "url": url, "status": "registered"}
                    )
                except Exception as e:
                    endpoint_status.append(
                        {
                            "endpoint": endpoint,
                            "url": None,
                            "status": "error",
                            "error": str(e),
                        }
                    )

            failed_endpoints = [ep for ep in endpoint_status if ep["status"] == "error"]

            if failed_endpoints:
                return "error", f"APIエンドポイント登録エラー", {"endpoints": endpoint_status}

            return "healthy", "APIエンドポイント正常", {"endpoints": endpoint_status}

        except Exception as e:
            return "error", f"APIエンドポイントチェックエラー: {str(e)}", {}

    def _check_security_headers(self) -> Tuple[str, str, Dict]:
        """セキュリティヘッダーの設定確認"""
        try:
            # セキュリティ設定の確認
            security_config = {
                "csrf_enabled": current_app.config.get("WTF_CSRF_ENABLED", False),
                "session_cookie_secure": current_app.config.get(
                    "SESSION_COOKIE_SECURE", False
                ),
                "session_cookie_httponly": current_app.config.get(
                    "SESSION_COOKIE_HTTPONLY", False
                ),
                "permanent_session_lifetime": current_app.config.get(
                    "PERMANENT_SESSION_LIFETIME", "not_set"
                ),
            }

            # セキュリティレベルの評価
            security_score = 0
            max_score = 4

            if security_config["csrf_enabled"]:
                security_score += 1
            if security_config["session_cookie_secure"]:
                security_score += 1
            if security_config["session_cookie_httponly"]:
                security_score += 1
            if security_config["permanent_session_lifetime"] != "not_set":
                security_score += 1

            if security_score == max_score:
                status = "healthy"
                message = "セキュリティ設定完全"
            elif security_score >= max_score * 0.75:
                status = "warning"
                message = f"セキュリティ設定要改善 ({security_score}/{max_score})"
            else:
                status = "error"
                message = f"セキュリティ設定不十分 ({security_score}/{max_score})"

            return (
                status,
                message,
                {
                    "security_score": f"{security_score}/{max_score}",
                    "config": security_config,
                },
            )

        except Exception as e:
            return "error", f"セキュリティ設定チェックエラー: {str(e)}", {}

    def _check_memory_usage(self) -> Tuple[str, str, Dict]:
        """メモリ使用量の確認"""
        try:
            import os

            import psutil

            # プロセス情報取得
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()

            # システムメモリ情報
            system_memory = psutil.virtual_memory()

            details = {
                "process_memory_mb": round(memory_info.rss / 1024 / 1024, 2),
                "process_memory_percent": round(memory_percent, 2),
                "system_memory_total_gb": round(
                    system_memory.total / 1024 / 1024 / 1024, 2
                ),
                "system_memory_available_gb": round(
                    system_memory.available / 1024 / 1024 / 1024, 2
                ),
                "system_memory_percent": system_memory.percent,
            }

            # メモリ使用量の評価
            if memory_percent > 80:
                status = "error"
                message = f"メモリ使用量危険レベル ({memory_percent:.1f}%)"
            elif memory_percent > 60:
                status = "warning"
                message = f"メモリ使用量注意レベル ({memory_percent:.1f}%)"
            else:
                status = "healthy"
                message = f"メモリ使用量正常 ({memory_percent:.1f}%)"

            return status, message, details

        except ImportError:
            return "warning", "psutilライブラリが利用できません", {}
        except Exception as e:
            return "error", f"メモリチェックエラー: {str(e)}", {}


def create_health_endpoint(app):
    """
    ヘルスチェックエンドポイントを作成

    Args:
        app: Flaskアプリケーションインスタンス
    """

    @app.route("/health")
    def health_check():
        """基本ヘルスチェックエンドポイント"""
        try:
            # 簡単なDB接続テスト
            db.session.execute(text("SELECT 1"))
            return jsonify(
                {
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "version": app.config.get("VERSION", "1.0.0"),
                }
            )
        except Exception as e:
            return (
                jsonify(
                    {
                        "status": "unhealthy",
                        "timestamp": datetime.utcnow().isoformat(),
                        "error": str(e),
                    }
                ),
                503,
            )

    @app.route("/health/detailed")
    def detailed_health_check():
        """詳細ヘルスチェックエンドポイント"""
        checker = HealthChecker()
        results = checker.run_all_checks()

        status_code = 200 if results["overall_status"] == "healthy" else 503
        return jsonify(results), status_code

    @app.route("/health/ranking")
    def ranking_health_check():
        """ランキング機能専用ヘルスチェック"""
        checker = HealthChecker()

        ranking_result = checker._check_ranking_service()
        cache_result = checker._check_cache_system()

        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "ranking_service": {
                "status": ranking_result[0],
                "message": ranking_result[1],
                "details": ranking_result[2],
            },
            "cache_system": {
                "status": cache_result[0],
                "message": cache_result[1],
                "details": cache_result[2],
            },
        }

        overall_healthy = all(
            check["status"] in ["healthy", "warning"]
            for check in [results["ranking_service"], results["cache_system"]]
        )

        results["overall_status"] = "healthy" if overall_healthy else "unhealthy"
        status_code = 200 if overall_healthy else 503

        return jsonify(results), status_code


def setup_health_monitoring(app):
    """
    ヘルスモニタリング機能を設定

    Args:
        app: Flaskアプリケーションインスタンス
    """
    create_health_endpoint(app)

    # 定期的なヘルスチェック（バックグラウンドタスク用）
    @app.before_first_request
    def log_startup_health():
        checker = HealthChecker()
        results = checker.run_all_checks()
        app.logger.info(f"アプリケーション起動時ヘルスチェック: {results['overall_status']}")

        if results["overall_status"] != "healthy":
            app.logger.warning(f"起動時健全性問題検出: {results['summary']}")

    return app
