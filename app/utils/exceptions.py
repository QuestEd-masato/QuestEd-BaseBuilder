# app/utils/exceptions.py

"""
QuestEd カスタム例外クラス定義
"""


class QuestEdBaseException(Exception):
    """QuestEd基底例外クラス"""

    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class PatternAnalysisError(QuestEdBaseException):
    """学習パターン分析エラー"""

    pass


class InsufficientDataError(QuestEdBaseException):
    """データ不足エラー"""

    pass


class AIRecommendationError(QuestEdBaseException):
    """AI推薦エラー"""

    pass


class WeaknessAnalysisError(QuestEdBaseException):
    """弱点分析エラー"""

    pass


class SpacedRepetitionError(QuestEdBaseException):
    """間隔反復学習エラー"""

    pass


class ValidationError(QuestEdBaseException):
    """バリデーションエラー"""

    pass


class AuthorizationError(QuestEdBaseException):
    """認証・認可エラー"""

    pass


class NotFoundError(QuestEdBaseException):
    """リソースが見つからないエラー"""

    pass


class PermissionError(QuestEdBaseException):
    """権限エラー"""

    pass


class ConfigurationError(QuestEdBaseException):
    """設定エラー"""

    pass


class SecurityError(QuestEdBaseException):
    """セキュリティ関連のエラー"""

    pass
