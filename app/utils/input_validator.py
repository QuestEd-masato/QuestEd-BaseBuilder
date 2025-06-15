"""
QuestEd 入力検証・サニタイゼーションモジュール

このモジュールは、全ての外部入力データの検証とサニタイゼーションを担当します。
セキュリティ脆弱性（XSS、SQLインジェクション、ディレクトリトラバーサルなど）
を防ぐための包括的な機能を提供します。

新規開発者へのガイド:
1. 全ての外部入力（フォーム、URL、API）は必ずこのモジュールで検証する
2. データベース保存前に適切なサニタイゼーションを実行する
3. HTMLエスケープで XSS攻撃を防ぐ
4. ファイルアップロードは厳格に検証する
5. SQLクエリはパラメータ化クエリを使用する

Author: QuestEd Development Team
Created: 2025-01-15
Version: 1.0.0
"""

import re
import html
import bleach
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from werkzeug.utils import secure_filename
from flask import current_app
import logging

# ログ設定
logger = logging.getLogger(__name__)


class InputValidator:
    """
    入力データ検証クラス
    
    全ての外部入力データを検証し、アプリケーションの整合性と
    セキュリティを保護します。
    """
    
    # 許可される文字セット（正規表現パターン）
    PATTERNS = {
        'username': r'^[a-zA-Z0-9_-]{3,30}$',  # 英数字、アンダースコア、ハイフンのみ
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'school_code': r'^[A-Z0-9]{4,10}$',  # 大文字英数字のみ
        'phone': r'^\+?[\d\s-()]{10,15}$',  # 電話番号（国際対応）
        'japanese_text': r'^[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\u3000-\u303F\w\s.,!?()「」【】・]+$',  # 日本語文字
        'safe_html': r'^[a-zA-Z0-9\s.,!?()「」【】・\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+$'
    }
    
    # 危険な文字列パターン
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # JavaScriptタグ
        r'javascript:',  # JavaScript URI
        r'on\w+\s*=',  # イベントハンドラ
        r'expression\s*\(',  # CSS expression
        r'\.\./|\.\.\\',  # ディレクトリトラバーサル
        r'union\s+select|select\s+.*\s+from',  # SQLインジェクション
        r'exec\s*\(|eval\s*\(',  # コード実行
        r'<iframe|<object|<embed',  # 危険なHTMLタグ
    ]
    
    @classmethod
    def validate_and_sanitize(cls, data: Dict[str, Any], rules: Dict[str, Dict]) -> Dict[str, Any]:
        """
        複数フィールドの一括検証・サニタイゼーション
        
        Args:
            data: 検証するデータ辞書
            rules: フィールドごとの検証ルール
            
        Returns:
            Dict: 検証・サニタイズ済みデータ
            
        Raises:
            ValidationError: 検証失敗時
            
        Example:
            rules = {
                'username': {'type': 'username', 'required': True},
                'email': {'type': 'email', 'required': True},
                'bio': {'type': 'safe_text', 'max_length': 500}
            }
            clean_data = InputValidator.validate_and_sanitize(form_data, rules)
        """
        clean_data = {}
        errors = []
        
        for field, rule in rules.items():
            try:
                if field in data:
                    clean_data[field] = cls._validate_field(data[field], rule)
                elif rule.get('required', False):
                    errors.append(f"{field} は必須項目です")
                else:
                    clean_data[field] = rule.get('default', None)
            except ValidationError as e:
                errors.append(f"{field}: {str(e)}")
        
        if errors:
            raise ValidationError("; ".join(errors))
        
        return clean_data
    
    @classmethod
    def _validate_field(cls, value: Any, rule: Dict) -> Any:
        """
        単一フィールドの検証
        
        Args:
            value: 検証する値
            rule: 検証ルール
            
        Returns:
            Any: 検証・サニタイズ済みの値
        """
        if value is None:
            if rule.get('required', False):
                raise ValidationError("必須項目です")
            return None
        
        # 文字列の場合の処理
        if isinstance(value, str):
            # 前後の空白を除去
            value = value.strip()
            
            # 空文字列チェック
            if not value and rule.get('required', False):
                raise ValidationError("空の値は許可されていません")
            
            # 長さチェック
            if 'max_length' in rule and len(value) > rule['max_length']:
                raise ValidationError(f"最大長{rule['max_length']}文字を超えています")
            
            if 'min_length' in rule and len(value) < rule['min_length']:
                raise ValidationError(f"最小長{rule['min_length']}文字未満です")
            
            # 危険パターンチェック
            cls._check_dangerous_patterns(value)
            
            # タイプ別検証
            field_type = rule.get('type', 'text')
            value = cls._validate_by_type(value, field_type)
        
        return value
    
    @classmethod
    def _check_dangerous_patterns(cls, text: str) -> None:
        """
        危険なパターンをチェック
        
        Args:
            text: チェックする文字列
            
        Raises:
            SecurityError: 危険なパターンが見つかった場合
        """
        text_lower = text.lower()
        
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.warning(f"危険なパターンを検出: {pattern}")
                raise SecurityError(f"許可されていない文字列が含まれています")
    
    @classmethod
    def _validate_by_type(cls, value: str, field_type: str) -> str:
        """
        フィールドタイプ別の検証
        
        Args:
            value: 検証する文字列
            field_type: フィールドタイプ
            
        Returns:
            str: 検証済みの文字列
        """
        if field_type in cls.PATTERNS:
            if not re.match(cls.PATTERNS[field_type], value):
                raise ValidationError(f"無効な{field_type}形式です")
        
        # タイプ別の特別処理
        if field_type == 'email':
            return value.lower()  # メールアドレスは小文字に統一
        elif field_type == 'safe_html':
            return cls.sanitize_html(value)
        elif field_type == 'safe_text':
            return cls.sanitize_text(value)
        elif field_type == 'filename':
            return cls.sanitize_filename(value)
        
        return value
    
    @staticmethod
    def sanitize_html(text: str, allowed_tags: Optional[List[str]] = None) -> str:
        """
        HTMLをサニタイズ（XSS対策）
        
        Args:
            text: サニタイズするHTML文字列
            allowed_tags: 許可するHTMLタグのリスト
            
        Returns:
            str: サニタイズされたHTML
        """
        if allowed_tags is None:
            # デフォルトで許可するタグ
            allowed_tags = ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li']
        
        # 許可する属性
        allowed_attributes = {
            '*': ['class'],
            'a': ['href', 'title'],
            'img': ['src', 'alt', 'width', 'height']
        }
        
        return bleach.clean(
            text,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True
        )
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """
        プレーンテキストをサニタイズ
        
        Args:
            text: サニタイズするテキスト
            
        Returns:
            str: サニタイズされたテキスト
        """
        # HTMLエスケープ
        text = html.escape(text)
        
        # 制御文字を除去
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
        
        return text
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        ファイル名をサニタイズ（ディレクトリトラバーサル対策）
        
        Args:
            filename: 元のファイル名
            
        Returns:
            str: 安全なファイル名
        """
        # Werkzeugのsecure_filenameを使用
        safe_name = secure_filename(filename)
        
        # 追加のチェック
        if not safe_name or safe_name == '.' or safe_name == '..':
            safe_name = 'unnamed_file'
        
        # 長すぎるファイル名を制限
        if len(safe_name) > 255:
            name, ext = os.path.splitext(safe_name)
            safe_name = name[:250] + ext
        
        return safe_name
    
    @staticmethod
    def validate_file_upload(file_obj, allowed_extensions: List[str], max_size: int) -> Tuple[bool, str]:
        """
        ファイルアップロードの安全性を検証
        
        Args:
            file_obj: アップロードファイルオブジェクト
            allowed_extensions: 許可する拡張子リスト
            max_size: 最大ファイルサイズ（バイト）
            
        Returns:
            Tuple[bool, str]: (検証結果, エラーメッセージ)
        """
        if not file_obj or not file_obj.filename:
            return False, "ファイルが選択されていません"
        
        # ファイル名の検証
        filename = InputValidator.sanitize_filename(file_obj.filename)
        if not filename:
            return False, "無効なファイル名です"
        
        # 拡張子の検証
        ext = Path(filename).suffix.lower()
        if ext not in [f'.{ext}' for ext in allowed_extensions]:
            return False, f"許可されていないファイル形式です。許可形式: {', '.join(allowed_extensions)}"
        
        # ファイルサイズの検証
        file_obj.seek(0, os.SEEK_END)
        file_size = file_obj.tell()
        file_obj.seek(0)  # ポインタを先頭に戻す
        
        if file_size > max_size:
            return False, f"ファイルサイズが大きすぎます。最大: {max_size // (1024*1024)}MB"
        
        # ファイル内容の簡易チェック
        file_content = file_obj.read(1024)  # 最初の1KBをチェック
        file_obj.seek(0)  # ポインタを先頭に戻す
        
        # 実行可能ファイルのヘッダーをチェック
        dangerous_headers = [
            b'MZ',  # Windows実行ファイル
            b'\x7fELF',  # Linux実行ファイル
            b'#!/',  # シェルスクリプト
            b'<?php',  # PHPスクリプト
        ]
        
        for header in dangerous_headers:
            if file_content.startswith(header):
                return False, "実行可能ファイルはアップロードできません"
        
        return True, ""


class ValidationError(Exception):
    """入力検証エラー"""
    pass


class SecurityError(Exception):
    """セキュリティ関連エラー"""
    pass


# 使用例と設定例
VALIDATION_RULES = {
    'user_registration': {
        'username': {'type': 'username', 'required': True, 'min_length': 3, 'max_length': 30},
        'email': {'type': 'email', 'required': True},
        'full_name': {'type': 'japanese_text', 'required': True, 'max_length': 100},
        'school_code': {'type': 'school_code', 'required': False}
    },
    'activity_log': {
        'title': {'type': 'safe_text', 'required': True, 'max_length': 200},
        'content': {'type': 'safe_html', 'required': True, 'max_length': 5000},
        'reflection': {'type': 'safe_text', 'required': False, 'max_length': 2000}
    },
    'file_upload': {
        'allowed_extensions': ['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx'],
        'max_size': 16 * 1024 * 1024  # 16MB
    }
}