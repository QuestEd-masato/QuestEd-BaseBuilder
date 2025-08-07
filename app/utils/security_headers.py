"""
QuestEd セキュリティヘッダー設定

Webアプリケーションのセキュリティヘッダーを管理します。

Author: QuestEd Development Team
Created: 2025-01-15
Version: 1.0.0
"""

from functools import wraps

from flask import Response


def add_security_headers(app):
    """
    セキュリティヘッダーを追加するデコレータを設定

    Args:
        app: Flaskアプリケーションインスタンス
    """

    @app.after_request
    def set_security_headers(response: Response) -> Response:
        """
        レスポンスにセキュリティヘッダーを追加

        Args:
            response: Flaskレスポンスオブジェクト

        Returns:
            Response: セキュリティヘッダー付きレスポンス
        """
        # XSS保護
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # コンテンツタイプスニッフィング防止
        response.headers["X-Content-Type-Options"] = "nosniff"

        # クリックジャッキング防止
        response.headers["X-Frame-Options"] = "DENY"

        # HTTPS強制（本番環境でのみ有効）
        if not app.debug:
            response.headers[
                "Strict-Transport-Security"
            ] = "max-age=31536000; includeSubDomains; preload"

        # CSP統一管理: security_config.pyから統一設定を取得
        from app.config.security_config import get_unified_csp_policy
        response.headers["Content-Security-Policy"] = get_unified_csp_policy()

        # 参照元ポリシー
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 権限ポリシー
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "bluetooth=()"
        )

        return response

    return app


def require_https(f):
    """
    HTTPS必須デコレータ（本番環境用）

    Args:
        f: デコレート対象関数

    Returns:
        function: デコレートされた関数
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import current_app, redirect, request, url_for

        # 本番環境でHTTPSが必須
        if not current_app.debug and not request.is_secure:
            return redirect(
                url_for(
                    request.endpoint,
                    _external=True,
                    _scheme="https",
                    **request.view_args
                )
            )

        return f(*args, **kwargs)

    return decorated_function


def secure_cookie_config(app):
    """
    セキュアなクッキー設定

    Args:
        app: Flaskアプリケーションインスタンス
    """
    if not app.debug:
        # 本番環境でのセキュアクッキー設定
        app.config.update(
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE="Lax",
            PERMANENT_SESSION_LIFETIME=3600,  # 1時間
        )
    else:
        # 開発環境設定
        app.config.update(
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE="Lax",
            PERMANENT_SESSION_LIFETIME=3600,
        )


def rate_limit_headers(
    response: Response, limit: int, remaining: int, reset_time: int
) -> Response:
    """
    レート制限ヘッダーを追加

    Args:
        response: Flaskレスポンスオブジェクト
        limit: 制限値
        remaining: 残り回数
        reset_time: リセット時刻（UNIX タイムスタンプ）

    Returns:
        Response: レート制限ヘッダー付きレスポンス
    """
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_time)

    if remaining <= 0:
        response.headers["Retry-After"] = str(reset_time)

    return response


class SecurityHeaderMiddleware:
    """
    セキュリティヘッダー設定用ミドルウェア
    """

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """
        アプリケーションにミドルウェアを設定

        Args:
            app: Flaskアプリケーションインスタンス
        """
        add_security_headers(app)
        secure_cookie_config(app)

        # セキュリティ設定のログ出力
        app.logger.info("セキュリティヘッダーミドルウェアが設定されました")


def cors_headers(response: Response, allowed_origins: list = None) -> Response:
    """
    CORSヘッダーを追加（API用）

    Args:
        response: Flaskレスポンスオブジェクト
        allowed_origins: 許可するオリジンのリスト

    Returns:
        Response: CORSヘッダー付きレスポンス
    """
    if allowed_origins is None:
        allowed_origins = ["https://quest-ed.jp", "https://www.quest-ed.jp"]

    # 本番環境では厳密な制御
    from flask import current_app, request

    origin = request.headers.get("Origin")
    if origin in allowed_origins or current_app.debug:
        response.headers["Access-Control-Allow-Origin"] = origin or "*"
        response.headers[
            "Access-Control-Allow-Methods"
        ] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers[
            "Access-Control-Allow-Headers"
        ] = "Content-Type, Authorization, X-Requested-With"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "86400"  # 24時間

    return response
