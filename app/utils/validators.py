"""
QuestEd 入力値検証ユーティリティ

ランキングシステムおよび全般的な入力値検証機能を提供します。

Author: QuestEd Development Team
Created: 2025-01-15
Version: 1.0.0
"""

import re
from typing import Any, Optional, Union


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


def validate_ranking_params(ranking_type: str, scope: str, scope_id: Optional[int] = None, limit: int = 50) -> dict:
    """
    ランキングパラメータの包括的検証
    
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
    errors = []
    
    # ランキング種類の検証
    if not validate_ranking_type(ranking_type):
        errors.append(f"無効なランキング種類: {ranking_type}")
    
    # スコープの検証
    if not validate_scope(scope):
        errors.append(f"無効なスコープ: {scope}")
    
    # スコープIDの検証
    if not validate_scope_id(scope_id):
        errors.append(f"無効なスコープID: {scope_id}")
    
    # 取得件数の検証
    if not validate_limit(limit):
        errors.append(f"無効な取得件数: {limit}")
    
    if errors:
        raise ValidationError("; ".join(errors))
    
    return {
        'ranking_type': ranking_type,
        'scope': scope,
        'scope_id': int(scope_id) if scope_id is not None else None,
        'limit': int(limit)
    }