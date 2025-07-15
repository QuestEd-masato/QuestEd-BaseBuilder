"""
QuestEd 包括的エラーハンドリングシステム

このモジュールは、アプリケーション全体で発生する様々なエラーを
統一的に処理し、適切なログ記録とユーザー向けメッセージを提供します。

主な機能:
- 例外の種類に応じた適切な処理
- セキュリティインシデントの検出と記録
- ユーザー向けの分かりやすいエラーメッセージ
- 開発者向けの詳細なデバッグ情報
- エラー発生時の自動通知機能

エラー分類:
1. セキュリティエラー（悪意のあるアクセスなど）
2. バリデーションエラー（入力データの不備）
3. データベースエラー（接続失敗、制約違反など）
4. 外部APIエラー（OpenAI API、外部サービス）
5. システムエラー（サーバー障害、メモリ不足など）

Author: QuestEd Development Team
Created: 2025-01-15
Version: 1.0.0
"""

import json
import logging
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from flask import current_app, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

# ログ設定
logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    統一エラーハンドリングクラス

    アプリケーション全体のエラーを統一的に処理し、
    適切なレスポンスとログ記録を行います。
    """

    # エラーレベル定義
    ERROR_LEVELS = {
        "CRITICAL": 50,  # システム停止レベル
        "ERROR": 40,  # 機能停止レベル
        "WARNING": 30,  # 注意が必要
        "INFO": 20,  # 情報記録
        "DEBUG": 10,  # デバッグ情報
    }

    # ユーザー向けエラーメッセージ
    USER_MESSAGES = {
        "security": "セキュリティ上の理由によりアクセスが拒否されました。",
        "validation": "入力データに不備があります。内容を確認してください。",
        "database": "データベースアクセス中にエラーが発生しました。時間をおいて再試行してください。",
        "api": "外部サービスとの通信中にエラーが発生しました。",
        "system": "システムエラーが発生しました。管理者にお問い合わせください。",
        "not_found": "要求されたリソースが見つかりませんでした。",
        "permission": "この操作を実行する権限がありません。",
        "rate_limit": "アクセス頻度が制限を超えています。時間をおいて再試行してください。",
    }

    @classmethod
    def handle_exception(
        cls, error: Exception, context: Dict[str, Any] = None
    ) -> Tuple[Dict[str, Any], int]:
        """
        例外を統一的に処理

        Args:
            error: 発生した例外
            context: エラーコンテキスト情報

        Returns:
            Tuple[Dict, int]: (エラーレスポンス, HTTPステータスコード)
        """
        if context is None:
            context = {}

        # エラー分類
        error_type = cls._classify_error(error)
        error_level = cls._determine_log_level(error_type, error)

        # エラー情報の収集
        error_info = cls._collect_error_info(error, context)

        # ログ記録
        cls._log_error(error_level, error_type, error_info)

        # セキュリティインシデントの検出
        if error_type == "security":
            cls._handle_security_incident(error, error_info)

        # レスポンス生成
        response_data = cls._generate_response(error_type, error_info)
        status_code = cls._get_http_status(error_type, error)

        return response_data, status_code

    @classmethod
    def _classify_error(cls, error: Exception) -> str:
        """
        エラーを分類

        Args:
            error: 例外オブジェクト

        Returns:
            str: エラー分類
        """
        from app.utils.exceptions import (
            AuthorizationError,
            NotFoundError,
            SecurityError,
            ValidationError,
        )

        if isinstance(error, (SecurityError, AuthorizationError)):
            return "security"
        elif isinstance(error, ValidationError):
            return "validation"
        elif isinstance(error, NotFoundError):
            return "not_found"
        elif isinstance(error, HTTPException):
            if error.code == 404:
                return "not_found"
            elif error.code == 403:
                return "permission"
            elif error.code == 429:
                return "rate_limit"
            else:
                return "http"
        elif "database" in str(error).lower() or "sql" in str(error).lower():
            return "database"
        elif "api" in str(error).lower() or "request" in str(error).lower():
            return "api"
        else:
            return "system"

    @classmethod
    def _determine_log_level(cls, error_type: str, error: Exception) -> str:
        """
        ログレベルを決定

        Args:
            error_type: エラー分類
            error: 例外オブジェクト

        Returns:
            str: ログレベル
        """
        if error_type == "security":
            return "CRITICAL"
        elif error_type in ["database", "system"]:
            return "ERROR"
        elif error_type in ["api", "validation"]:
            return "WARNING"
        else:
            return "INFO"

    @classmethod
    def _collect_error_info(
        cls, error: Exception, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        エラー情報を収集

        Args:
            error: 例外オブジェクト
            context: 追加コンテキスト

        Returns:
            Dict: エラー情報
        """
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.utcnow().isoformat(),
            "traceback": traceback.format_exc() if current_app.debug else None,
            "context": context,
        }

        # リクエスト情報の追加（可能な場合）
        if request:
            error_info.update(
                {
                    "request_method": request.method,
                    "request_url": request.url,
                    "request_endpoint": request.endpoint,
                    "user_agent": request.headers.get("User-Agent"),
                    "remote_addr": request.remote_addr,
                    "request_id": getattr(request, "id", None),
                }
            )

            # 現在のユーザー情報（ログイン済みの場合）
            try:
                from flask_login import current_user

                if current_user.is_authenticated:
                    error_info["user_id"] = current_user.id
                    error_info["user_role"] = current_user.role
            except:
                pass

        return error_info

    @classmethod
    def _log_error(
        cls, level: str, error_type: str, error_info: Dict[str, Any]
    ) -> None:
        """
        エラーをログに記録

        Args:
            level: ログレベル
            error_type: エラー分類
            error_info: エラー情報
        """
        log_message = f"[{error_type.upper()}] {error_info['error_message']}"

        # 構造化ログ情報
        log_data = {
            "level": level,
            "error_type": error_type,
            "timestamp": error_info["timestamp"],
            "context": error_info.get("context", {}),
            "request_info": {
                "method": error_info.get("request_method"),
                "url": error_info.get("request_url"),
                "endpoint": error_info.get("request_endpoint"),
                "remote_addr": error_info.get("remote_addr"),
                "user_id": error_info.get("user_id"),
                "user_role": error_info.get("user_role"),
            },
        }

        # ログレベルに応じて出力
        log_level_value = cls.ERROR_LEVELS.get(level, 30)
        logger.log(log_level_value, log_message, extra={"error_data": log_data})

        # 開発環境では詳細なトレースバックも出力
        if current_app.debug and error_info.get("traceback"):
            logger.debug(f"Traceback: {error_info['traceback']}")

    @classmethod
    def _handle_security_incident(
        cls, error: Exception, error_info: Dict[str, Any]
    ) -> None:
        """
        セキュリティインシデントの処理

        Args:
            error: セキュリティ関連の例外
            error_info: エラー情報
        """
        # セキュリティログに記録
        security_log = {
            "incident_type": "security_error",
            "severity": "high",
            "error_message": str(error),
            "timestamp": error_info["timestamp"],
            "source_ip": error_info.get("remote_addr"),
            "user_id": error_info.get("user_id"),
            "request_url": error_info.get("request_url"),
            "user_agent": error_info.get("user_agent"),
        }

        logger.critical(f"SECURITY_INCIDENT: {json.dumps(security_log)}")

        # 必要に応じて外部通知システムへの送信
        # （メール、Slack、監視システムなど）
        cls._notify_security_team(security_log)

    @classmethod
    def _notify_security_team(cls, incident_data: Dict[str, Any]) -> None:
        """
        セキュリティチームへの通知

        Args:
            incident_data: インシデント情報
        """
        # 実装例：管理者メール送信、Slack通知など
        # 本番環境では実際の通知システムと連携
        logger.info(f"Security team notification: {incident_data['incident_type']}")

    @classmethod
    def _generate_response(
        cls, error_type: str, error_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        エラーレスポンスを生成

        Args:
            error_type: エラー分類
            error_info: エラー情報

        Returns:
            Dict: レスポンスデータ
        """
        response = {
            "success": False,
            "error": {
                "type": error_type,
                "message": cls.USER_MESSAGES.get(error_type, "予期しないエラーが発生しました。"),
                "timestamp": error_info["timestamp"],
            },
        }

        # 開発環境では詳細情報も含める
        if current_app.debug:
            response["error"]["debug"] = {
                "error_type": error_info["error_type"],
                "error_message": error_info["error_message"],
                "context": error_info.get("context", {}),
            }

        return response

    @classmethod
    def _get_http_status(cls, error_type: str, error: Exception) -> int:
        """
        HTTPステータスコードを決定

        Args:
            error_type: エラー分類
            error: 例外オブジェクト

        Returns:
            int: HTTPステータスコード
        """
        status_map = {
            "validation": 400,  # Bad Request
            "security": 403,  # Forbidden
            "permission": 403,  # Forbidden
            "not_found": 404,  # Not Found
            "rate_limit": 429,  # Too Many Requests
            "database": 503,  # Service Unavailable
            "api": 503,  # Service Unavailable
            "system": 500,  # Internal Server Error
        }

        # HTTPExceptionの場合は元のステータスコードを使用
        if isinstance(error, HTTPException):
            return error.code

        return status_map.get(error_type, 500)


def setup_error_handlers(app):
    """
    Flaskアプリケーションにエラーハンドラを登録

    Args:
        app: Flaskアプリケーション
    """

    @app.errorhandler(Exception)
    def handle_general_exception(error):
        """すべての例外をキャッチ"""
        response_data, status_code = ErrorHandler.handle_exception(error)

        # JSON APIリクエストの場合
        if request.is_json or "api/" in request.path:
            return jsonify(response_data), status_code

        # Web UIリクエストの場合
        return (
            render_template(
                "errors/500.html", error_message=response_data["error"]["message"]
            ),
            status_code,
        )

    @app.errorhandler(404)
    def handle_not_found(error):
        """404エラーの処理"""
        response_data, status_code = ErrorHandler.handle_exception(error)

        if request.is_json or "api/" in request.path:
            return jsonify(response_data), status_code

        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def handle_internal_error(error):
        """500エラーの処理"""
        response_data, status_code = ErrorHandler.handle_exception(error)

        if request.is_json or "api/" in request.path:
            return jsonify(response_data), status_code

        return (
            render_template(
                "errors/500.html", error_message=response_data["error"]["message"]
            ),
            500,
        )


class RequestContextLogger:
    """
    リクエストコンテキストの詳細ログ記録

    各リクエストの詳細情報を記録し、問題発生時の
    デバッグとセキュリティ監査に活用します。
    """

    @staticmethod
    def log_request_start():
        """リクエスト開始時のログ"""
        if current_app.debug:
            logger.info(f"REQUEST_START: {request.method} {request.url}")

    @staticmethod
    def log_request_end(response):
        """リクエスト終了時のログ"""
        if current_app.debug:
            logger.info(
                f"REQUEST_END: {response.status_code} {request.method} {request.url}"
            )
        return response

    @staticmethod
    def log_slow_request(threshold_ms=1000):
        """遅いリクエストの記録"""
        # 実装：リクエスト処理時間の測定と記録
        pass
