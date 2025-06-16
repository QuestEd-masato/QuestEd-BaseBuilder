"""
QuestEd 独立した入力値検証ユーティリティ

外部依存を最小限に抑えた完全独立型バリデーター

Author: QuestEd Development Team
Created: 2025-01-15
Version: 2.0.0
"""

import re
import json
from typing import Any, Optional, Union, Dict, List


class ValidationError(Exception):
    """カスタムバリデーションエラー"""
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


class EmailValidator:
    """メールアドレスバリデーター"""
    
    # RFC 5322準拠の簡略版パターン
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}'
        r'[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
    )
    
    @classmethod
    def validate(cls, email: str) -> bool:
        """メールアドレスの形式を検証"""
        if not email or not isinstance(email, str):
            return False
        
        # 長さチェック
        if len(email) > 254:  # RFC 5321
            return False
            
        return bool(cls.EMAIL_PATTERN.match(email.lower()))
    
    @classmethod
    def validate_with_error(cls, email: str) -> None:
        """検証失敗時に例外を投げる"""
        if not cls.validate(email):
            raise ValidationError("有効なメールアドレスを入力してください", "email")


class PasswordValidator:
    """パスワードバリデーター"""
    
    DEFAULT_MIN_LENGTH = 8
    DEFAULT_MAX_LENGTH = 128
    
    @classmethod
    def validate(cls, password: str, 
                min_length: int = DEFAULT_MIN_LENGTH,
                max_length: int = DEFAULT_MAX_LENGTH,
                require_uppercase: bool = True,
                require_lowercase: bool = True,
                require_digit: bool = True,
                require_special: bool = False) -> Dict[str, Any]:
        """パスワードの強度を検証"""
        
        errors: List[str] = []
        
        if not password or not isinstance(password, str):
            errors.append("パスワードを入力してください")
            return {'valid': False, 'errors': errors, 'strength': 0}
        
        # 長さチェック
        if len(password) < min_length:
            errors.append(f"パスワードは{min_length}文字以上必要です")
        if len(password) > max_length:
            errors.append(f"パスワードは{max_length}文字以下にしてください")
        
        # 文字種チェック
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'[0-9]', password))
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
        
        if require_uppercase and not has_upper:
            errors.append("大文字を1文字以上含めてください")
        if require_lowercase and not has_lower:
            errors.append("小文字を1文字以上含めてください")
        if require_digit and not has_digit:
            errors.append("数字を1文字以上含めてください")
        if require_special and not has_special:
            errors.append("特殊文字を1文字以上含めてください")
        
        # 強度計算
        strength = 0
        if len(password) >= min_length:
            strength += 25
        if has_upper and has_lower:
            strength += 25
        if has_digit:
            strength += 25
        if has_special:
            strength += 25
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'strength': strength,
            'has_uppercase': has_upper,
            'has_lowercase': has_lower,
            'has_digit': has_digit,
            'has_special': has_special
        }


def validate_ranking_type(ranking_type: str) -> bool:
    """
    ランキング種類の検証
    
    Args:
        ranking_type: ランキング種類
        
    Returns:
        bool: 有効な場合True
    """
    valid_types = [
        'total_points', 
        'weekly_points', 
        'monthly_points',
        'accuracy_rate', 
        'study_time', 
        'consistency'
    ]
    return ranking_type in valid_types


def validate_scope(scope: str) -> bool:
    """
    スコープの検証
    
    Args:
        scope: スコープ (school, class)
        
    Returns:
        bool: 有効な場合True
    """
    return scope in ['school', 'class']


def validate_limit(limit: Union[str, int]) -> bool:
    """
    取得件数制限の検証
    
    Args:
        limit: 取得件数
        
    Returns:
        bool: 有効な場合True
    """
    try:
        limit = int(limit)
        return 1 <= limit <= 1000
    except (ValueError, TypeError):
        return False


def validate_scope_id(scope_id: Union[str, int, None]) -> bool:
    """
    スコープIDの検証
    
    Args:
        scope_id: スコープID
        
    Returns:
        bool: 有効な場合True
    """
    if scope_id is None:
        return True
    try:
        scope_id = int(scope_id)
        return scope_id > 0
    except (ValueError, TypeError):
        return False


def validate_student_id(student_id: Union[str, int]) -> bool:
    """
    学生IDの検証
    
    Args:
        student_id: 学生ID
        
    Returns:
        bool: 有効な場合True
    """
    try:
        student_id = int(student_id)
        return student_id > 0
    except (ValueError, TypeError):
        return False


def validate_class_id(class_id: Union[str, int]) -> bool:
    """
    クラスIDの検証
    
    Args:
        class_id: クラスID
        
    Returns:
        bool: 有効な場合True
    """
    try:
        class_id = int(class_id)
        return class_id > 0
    except (ValueError, TypeError):
        return False


def validate_email(email: str) -> bool:
    """
    メールアドレスの検証
    
    Args:
        email: メールアドレス
        
    Returns:
        bool: 有効な場合True
    """
    if not email or not isinstance(email, str):
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_username(username: str) -> bool:
    """
    ユーザー名の検証
    
    Args:
        username: ユーザー名
        
    Returns:
        bool: 有効な場合True
    """
    if not username or not isinstance(username, str):
        return False
    
    # 3-50文字、英数字とアンダースコア、ハイフン、ドットのみ
    pattern = r'^[a-zA-Z0-9_.-]{3,50}$'
    return bool(re.match(pattern, username))


def validate_string_length(text: str, min_length: int = 0, max_length: int = 1000) -> bool:
    """
    文字列長の検証
    
    Args:
        text: 検証対象文字列
        min_length: 最小長
        max_length: 最大長
        
    Returns:
        bool: 有効な場合True
    """
    if not isinstance(text, str):
        return False
    
    return min_length <= len(text) <= max_length


def sanitize_string(text: str) -> str:
    """
    文字列のサニタイズ
    
    Args:
        text: サニタイズ対象文字列
        
    Returns:
        str: サニタイズ済み文字列
    """
    if not isinstance(text, str):
        return ""
    
    # HTMLタグの除去
    text = re.sub(r'<[^>]+>', '', text)
    
    # 制御文字の除去
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
    
    # 前後の空白除去
    text = text.strip()
    
    return text


def validate_file_extension(filename: str, allowed_extensions: list = None) -> bool:
    """
    ファイル拡張子の検証
    
    Args:
        filename: ファイル名
        allowed_extensions: 許可する拡張子のリスト
        
    Returns:
        bool: 有効な場合True
    """
    if not filename or not isinstance(filename, str):
        return False
    
    if allowed_extensions is None:
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'pdf', 'txt', 'csv']
    
    # ファイル拡張子を取得
    if '.' not in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in allowed_extensions


def validate_json_data(data: Any) -> bool:
    """
    JSONデータの基本検証
    
    Args:
        data: 検証対象データ
        
    Returns:
        bool: 有効な場合True
    """
    import json
    
    try:
        if isinstance(data, str):
            json.loads(data)
        elif isinstance(data, (dict, list)):
            json.dumps(data)
        else:
            return False
        return True
    except (json.JSONDecodeError, TypeError):
        return False


class ValidationError(Exception):
    """検証エラー例外"""
    pass


def validate_curriculum_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """カリキュラムデータの検証"""
    
    errors = {}
    
    # 必須フィールド
    if not data.get('title'):
        errors['title'] = 'タイトルは必須です'
    elif len(data['title']) > 200:
        errors['title'] = 'タイトルは200文字以下にしてください'
    
    # 任意フィールド
    if data.get('description') and len(data['description']) > 1000:
        errors['description'] = '説明は1000文字以下にしてください'
    
    if errors:
        raise ValidationError("入力内容に誤りがあります", errors)
    
    return data


def validate_ranking_params(ranking_type: str, scope: str, scope_id: Optional[int] = None, limit: int = 50) -> dict:
    """
    ランキングパラメータの包括的検証（独立実装版）
    
    Args:
        ranking_type: ランキング種類
        scope: スコープ
        scope_id: スコープID
        limit: 取得件数
        
    Returns:
        dict: 検証結果と正規化されたパラメータ
        
    Raises:
        ValidationError: 検証エラー時
    """
    # 直接検証（外部依存を排除）
    VALID_TYPES = {
        'total_points', 'weekly_points', 'monthly_points',
        'accuracy_rate', 'study_time', 'continuation_rate', 'consistency'
    }
    VALID_SCOPES = {'school', 'class'}
    
    if ranking_type not in VALID_TYPES:
        raise ValidationError(
            f"無効なランキングタイプです。有効な値: {', '.join(VALID_TYPES)}",
            "ranking_type"
        )
    
    if scope not in VALID_SCOPES:
        raise ValidationError(
            f"無効なスコープです。有効な値: {', '.join(VALID_SCOPES)}",
            "scope"
        )
    
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValidationError(
            "表示件数は1から100の間で指定してください",
            "limit"
        )
    
    return {
        'ranking_type': ranking_type,
        'scope': scope,
        'scope_id': int(scope_id) if scope_id is not None else None,
        'limit': int(limit)
    }


# 後方互換性のための旧関数名も保持
def validate_ranking_type(ranking_type: str) -> bool:
    """ランキング種類の検証（後方互換性用）"""
    VALID_TYPES = {
        'total_points', 'weekly_points', 'monthly_points',
        'accuracy_rate', 'study_time', 'continuation_rate', 'consistency'
    }
    return ranking_type in VALID_TYPES


def validate_scope(scope: str) -> bool:
    """スコープの検証（後方互換性用）"""
    return scope in ['school', 'class']


def validate_limit(limit: Union[str, int]) -> bool:
    """取得件数制限の検証（後方互換性用）"""
    try:
        limit = int(limit)
        return 1 <= limit <= 1000
    except (ValueError, TypeError):
        return False