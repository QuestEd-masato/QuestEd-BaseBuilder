"""
QuestEd セキュリティ設定

ランキングシステムおよび全体のセキュリティ設定を管理します。

Author: QuestEd Development Team
Created: 2025-01-15
Version: 1.0.0
"""

# ランキングシステムセキュリティ設定
RANKING_SECURITY = {
    # 許可されるランキング種類
    "ALLOWED_RANKING_TYPES": [
        "total_points",
        "weekly_points",
        "monthly_points",
        "accuracy_rate",
        "study_time",
        "consistency",
    ],
    # 許可されるスコープ
    "ALLOWED_SCOPES": ["school", "class"],
    # 取得件数制限
    "MAX_LIMIT": 1000,
    "MIN_LIMIT": 1,
    "DEFAULT_LIMIT": 50,
    # キャッシュ有効期限（秒）
    "CACHE_DURATIONS": {
        "total_points": 3600,  # 1時間
        "weekly_points": 1800,  # 30分
        "monthly_points": 1800,  # 30分
        "accuracy_rate": 3600,  # 1時間
        "study_time": 1800,  # 30分
        "consistency": 3600,  # 1時間
    },
    # レート制限
    "RATE_LIMIT": {"per_minute": 60, "per_hour": 3600, "burst": 10},
}

# API セキュリティ設定
API_SECURITY = {
    # CORS設定
    "CORS_ORIGINS": ["https://quest-ed.jp", "https://www.quest-ed.jp"],
    # CSRFトークン有効期限（秒）
    "CSRF_TIME_LIMIT": 3600,
    # セッションセキュリティ
    "SESSION_COOKIE_SECURE": True,
    "SESSION_COOKIE_HTTPONLY": True,
    "SESSION_COOKIE_SAMESITE": "Lax",
    # セキュリティヘッダー
    "SECURITY_HEADERS": {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
                "https://cdnjs.cloudflare.com "
                "https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' "
                "https://cdnjs.cloudflare.com "
                "https://use.fontawesome.com "
                "https://cdn.jsdelivr.net; "
            "font-src 'self' "
                "https://cdnjs.cloudflare.com "
                "https://use.fontawesome.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        ),
    },
}

# データベースセキュリティ設定
DATABASE_SECURITY = {
    # SQLインジェクション対策
    "PARAMETERIZED_QUERIES_ONLY": True,
    "DISABLE_RAW_SQL": False,  # デバッグ時のみFalse
    # ログ記録レベル
    "LOG_LEVEL": "INFO",
    "LOG_SUSPICIOUS_QUERIES": True,
    # 監査設定
    "AUDIT_ENABLED": True,
    "AUDIT_RETENTION_DAYS": 90,
    # 接続プール設定
    "POOL_SIZE": 20,
    "MAX_OVERFLOW": 30,
    "POOL_TIMEOUT": 30,
    "POOL_RECYCLE": 3600,
}

# 入力値検証設定
INPUT_VALIDATION = {
    # 最大文字数制限
    "MAX_STRING_LENGTH": 1000,
    "MAX_TEXT_LENGTH": 10000,
    "MAX_NAME_LENGTH": 100,
    # 許可される文字パターン
    "ALLOWED_USERNAME_PATTERN": r"^[a-zA-Z0-9_.-]+$",
    "ALLOWED_EMAIL_PATTERN": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    # ファイルアップロード制限
    "MAX_FILE_SIZE": 16 * 1024 * 1024,  # 16MB
    "ALLOWED_EXTENSIONS": ["jpg", "jpeg", "png", "gif", "pdf", "txt", "csv"],
    # HTMLサニタイゼーション
    "BLEACH_ALLOWED_TAGS": [
        "p",
        "br",
        "strong",
        "em",
        "u",
        "ol",
        "ul",
        "li",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "blockquote",
    ],
    "BLEACH_ALLOWED_ATTRIBUTES": {
        "*": ["class", "id"],
        "a": ["href", "title"],
        "img": ["src", "alt", "width", "height"],
    },
}

# ログ設定
LOGGING_CONFIG = {
    "VERSION": 1,
    "DISABLE_EXISTING_LOGGERS": False,
    "FORMATTERS": {
        "default": {"FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"},
        "security": {
            "FORMAT": "%(asctime)s - SECURITY - %(levelname)s - %(message)s - USER:%(user_id)s - IP:%(remote_addr)s"
        },
    },
    "HANDLERS": {
        "file": {
            "CLASS": "logging.FileHandler",
            "FILENAME": "logs/quested.log",
            "FORMATTER": "default",
        },
        "security_file": {
            "CLASS": "logging.FileHandler",
            "FILENAME": "logs/security.log",
            "FORMATTER": "security",
        },
    },
    "LOGGERS": {
        "quested": {"HANDLERS": ["file"], "LEVEL": "INFO", "PROPAGATE": False},
        "quested.security": {
            "HANDLERS": ["security_file"],
            "LEVEL": "WARNING",
            "PROPAGATE": False,
        },
    },
}


def validate_ranking_params(ranking_type, scope, scope_id, limit):
    """
    ランキングパラメータの検証

    Args:
        ranking_type: ランキング種類
        scope: スコープ
        scope_id: スコープID
        limit: 取得件数制限

    Returns:
        tuple: (is_valid, error_message)
    """
    if ranking_type not in RANKING_SECURITY["ALLOWED_RANKING_TYPES"]:
        return False, f"無効なランキング種類: {ranking_type}"

    if scope not in RANKING_SECURITY["ALLOWED_SCOPES"]:
        return False, f"無効なスコープ: {scope}"

    if scope_id is not None and (not isinstance(scope_id, int) or scope_id < 1):
        return False, f"無効なスコープID: {scope_id}"

    if (
        not isinstance(limit, int)
        or limit < RANKING_SECURITY["MIN_LIMIT"]
        or limit > RANKING_SECURITY["MAX_LIMIT"]
    ):
        return False, f"無効な取得件数: {limit}"

    return True, None


def get_cache_duration(ranking_type):
    """
    ランキング種類に応じたキャッシュ有効期限を取得

    Args:
        ranking_type: ランキング種類

    Returns:
        int: キャッシュ有効期限（秒）
    """
    return RANKING_SECURITY["CACHE_DURATIONS"].get(ranking_type, 3600)


def get_unified_csp_policy():
    """
    統一CSPポリシーを取得
    
    Returns:
        str: 統一されたContent-Security-Policyヘッダー値
    """
    return API_SECURITY["SECURITY_HEADERS"]["Content-Security-Policy"]
