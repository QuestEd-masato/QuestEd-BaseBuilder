"""
QuestEd セキュリティユーティリティモジュール

このモジュールは、QuestEdアプリケーションの包括的なセキュリティ機能を提供します。
新規開発者向けに詳細なコメントとドキュメントを含んでいます。

主な機能:
- セキュアなトークン生成
- パスワード強度検証
- 入力データのサニタイゼーション
- セキュリティイベントのログ記録
- レート制限チェック
- セキュリティヘッダーの設定

セキュリティのベストプラクティス:
1. 全ての外部入力は検証・サニタイズする
2. 機密データは適切にハッシュ化する
3. セキュリティイベントをログに記録する
4. レート制限でDoS攻撃を防ぐ
5. セキュリティヘッダーでクライアント側攻撃を防ぐ

Author: QuestEd Development Team
Created: 2025
Last Modified: 2025-01-15
Version: 2.0.0
"""

import hashlib
import logging
import re
import secrets
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from flask import current_app, request, url_for


class SecurityUtils:
    """
    セキュリティ関連のユーティリティクラス

    このクラスは、QuestEdアプリケーション全体で使用されるセキュリティ機能を
    静的メソッドとして提供します。全てのメソッドは独立して使用でき、
    外部依存を最小限に抑えています。

    使用例:
        # セキュアなトークン生成
        token = SecurityUtils.generate_secure_token()

        # パスワード強度チェック
        is_valid, errors = SecurityUtils.validate_password_strength("password123")

        # ファイル名のサニタイズ
        safe_name = SecurityUtils.sanitize_filename("../../../etc/passwd")
    """

    # クラス定数: セキュリティ設定のデフォルト値
    DEFAULT_TOKEN_LENGTH = 32
    MIN_PASSWORD_LENGTH = 12
    MAX_FILENAME_LENGTH = 255
    RATE_LIMIT_WINDOW = 3600  # 1時間（秒）

    @staticmethod
    def generate_secure_token(length: int = DEFAULT_TOKEN_LENGTH) -> str:
        """
        暗号学的に安全なランダムトークンを生成

        このメソッドは、セッショントークン、CSRFトークン、
        パスワードリセットトークンなどの生成に使用されます。

        セキュリティ上の注意:
        - secrets.token_urlsafe()を使用して予測不可能なトークンを生成
        - 長さは最低32文字を推奨（エントロピー確保のため）
        - URLセーフな文字のみ使用（Base64エンコード）

        Args:
            length (int): トークンの長さ（デフォルト: 32文字）

        Returns:
            str: Base64エンコードされたセキュアなトークン

        Raises:
            ValueError: 長さが8文字未満の場合

        Example:
            >>> token = SecurityUtils.generate_secure_token()
            >>> len(token) >= 32
            True
        """
        if length < 8:
            raise ValueError("トークンの長さは最低8文字である必要があります")

        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_csrf_token():
        """
        CSRFトークンを生成

        Returns:
            str: CSRFトークン
        """
        return secrets.token_hex(16)

    @staticmethod
    def validate_password_strength(password):
        """
        パスワード強度を検証

        Args:
            password (str): 検証するパスワード

        Returns:
            tuple: (is_valid, errors)
        """
        errors = []

        if len(password) < 12:
            errors.append("パスワードは12文字以上である必要があります")

        if not re.search(r"[A-Z]", password):
            errors.append("パスワードには大文字が含まれている必要があります")

        if not re.search(r"[a-z]", password):
            errors.append("パスワードには小文字が含まれている必要があります")

        if not re.search(r"\d", password):
            errors.append("パスワードには数字が含まれている必要があります")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("パスワードには特殊文字が含まれている必要があります")

        # 連続する同じ文字をチェック
        if re.search(r"(.)\1{2,}", password):
            errors.append("パスワードに同じ文字を3回以上連続して使用することはできません")

        return len(errors) == 0, errors

    @staticmethod
    def hash_sensitive_data(data, salt=None):
        """
        機密データをハッシュ化

        Args:
            data (str): ハッシュ化するデータ
            salt (str, optional): ソルト

        Returns:
            str: ハッシュ化されたデータ
        """
        if salt is None:
            salt = secrets.token_hex(16)

        combined = f"{salt}{data}"
        return hashlib.sha256(combined.encode()).hexdigest()

    @staticmethod
    def sanitize_filename(filename):
        """
        ファイル名をサニタイズ

        Args:
            filename (str): 元のファイル名

        Returns:
            str: サニタイズされたファイル名
        """
        # 危険な文字を除去
        filename = re.sub(r'[<>:"/\\|?*]', "_", filename)

        # ドットで始まるファイル名を防止
        if filename.startswith("."):
            filename = "_" + filename[1:]

        # 長すぎるファイル名を制限
        if len(filename) > 255:
            name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
            filename = name[:250] + ("." + ext if ext else "")

        return filename

    @staticmethod
    def is_safe_url(target):
        """
        リダイレクト先URLが安全かチェック

        Args:
            target (str): チェックするURL

        Returns:
            bool: 安全なURLかどうか
        """
        ref_url = urlparse(request.host_url)
        test_url = urlparse(urljoin(request.host_url, target))
        return (
            test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc
        )

    @staticmethod
    def validate_email_format(email):
        """
        メールアドレス形式を検証

        Args:
            email (str): 検証するメールアドレス

        Returns:
            bool: 有効なメールアドレス形式かどうか
        """
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    @staticmethod
    def log_security_event(event_type, user_id=None, details=None):
        """
        セキュリティイベントをログに記録

        Args:
            event_type (str): イベントタイプ
            user_id (int, optional): ユーザーID
            details (str, optional): 詳細情報
        """
        log_entry = f"SECURITY_EVENT: {event_type}"

        if user_id:
            log_entry += f" | User ID: {user_id}"

        if details:
            log_entry += f" | Details: {details}"

        log_entry += f" | IP: {request.remote_addr if request else 'Unknown'}"

        logging.warning(log_entry)

    @staticmethod
    def check_rate_limit_exceeded(user_id, action, limit=10, window=3600):
        """
        レート制限をチェック（簡易版）

        Args:
            user_id (int): ユーザーID
            action (str): アクション名
            limit (int): 制限回数
            window (int): 時間窓（秒）

        Returns:
            bool: レート制限を超えているかどうか
        """
        # 実装が必要：Redisやメモリストアを使用したレート制限
        # 現在は常にFalseを返す（レート制限なし）
        return False


def setup_security_headers(app):
    """
    セキュリティヘッダーを設定

    Args:
        app: Flaskアプリケーション
    """

    @app.after_request
    def set_security_headers(response):
        # XSS保護
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # HTTPS強制（本番環境のみ）
        if app.config.get("ENV") == "production":
            response.headers[
                "Strict-Transport-Security"
            ] = "max-age=31536000; includeSubDomains"

        # CSP統一管理: security_config.pyで一元管理されるため、重複設定を無効化
        # response.headers["Content-Security-Policy"] = (
        #     "default-src 'self'; "
        #     "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        #     "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        #     "img-src 'self' data: https:; "
        #     "font-src 'self' https://cdn.jsdelivr.net"
        # )

        return response
