"""
データ処理用のNULL安全ユーティリティ関数

QuestEdアプリケーションでのデータ整合性問題を予防するための
汎用的なヘルパー関数集です。
"""

def safe_sum(iterable, attribute=None, default=0):
    """
    NULL安全な合計計算
    
    Args:
        iterable: 反復可能なオブジェクト
        attribute: 合計したい属性名（Noneの場合は要素自体を合計）
        default: NULL値の場合のデフォルト値
        
    Returns:
        int/float: 安全に計算された合計値
    """
    try:
        if attribute:
            return sum((getattr(item, attribute) or default) for item in iterable)
        return sum((item or default) for item in iterable)
    except (TypeError, AttributeError):
        return default

def safe_get(obj, attribute, default=None):
    """
    NULL安全な属性取得
    
    Args:
        obj: 対象オブジェクト
        attribute: 取得したい属性名
        default: 属性が存在しない/Noneの場合のデフォルト値
        
    Returns:
        any: 安全に取得された属性値
    """
    try:
        value = getattr(obj, attribute, default)
        return value if value is not None else default
    except (TypeError, AttributeError):
        return default

def safe_divide(numerator, denominator, default=0):
    """
    ゼロ除算安全な除算
    
    Args:
        numerator: 分子
        denominator: 分母
        default: 除算不可能な場合のデフォルト値
        
    Returns:
        float: 安全に計算された除算結果
    """
    try:
        if denominator and denominator != 0:
            return numerator / denominator
        return default
    except (TypeError, ZeroDivisionError):
        return default

def safe_percentage(part, total, default=0.0, precision=1):
    """
    安全なパーセンテージ計算
    
    Args:
        part: 部分値
        total: 全体値
        default: 計算不可能な場合のデフォルト値
        precision: 小数点以下の桁数
        
    Returns:
        float: 安全に計算されたパーセンテージ
    """
    try:
        if total and total > 0:
            result = (part / total) * 100
            return round(result, precision)
        return default
    except (TypeError, ZeroDivisionError):
        return default

def safe_average(values, default=0.0, precision=1):
    """
    NULL安全な平均値計算
    
    Args:
        values: 値のリスト
        default: 計算不可能な場合のデフォルト値
        precision: 小数点以下の桁数
        
    Returns:
        float: 安全に計算された平均値
    """
    try:
        filtered_values = [v for v in values if v is not None]
        if filtered_values:
            result = sum(filtered_values) / len(filtered_values)
            return round(result, precision)
        return default
    except (TypeError, ZeroDivisionError):
        return default

def safe_int(value, default=0):
    """
    安全な整数変換
    
    Args:
        value: 変換する値
        default: 変換失敗時のデフォルト値
        
    Returns:
        int: 安全に変換された整数値
    """
    try:
        if value is not None:
            return int(value)
        return default
    except (ValueError, TypeError):
        return default

def safe_float(value, default=0.0):
    """
    安全な浮動小数点変換
    
    Args:
        value: 変換する値
        default: 変換失敗時のデフォルト値
        
    Returns:
        float: 安全に変換された浮動小数点値
    """
    try:
        if value is not None:
            return float(value)
        return default
    except (ValueError, TypeError):
        return default