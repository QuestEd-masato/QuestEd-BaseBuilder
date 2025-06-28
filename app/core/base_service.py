"""
Base Service Class
==================
すべてのサービスクラスの基底クラス

共通機能:
- エラーハンドリング
- ログ記録
- データベースセッション管理
- 権限チェック
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

from extensions import db
from flask import current_app
from flask_login import current_user


class BaseService(ABC):
    """全サービスの基底クラス"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._db = db
    
    def execute_with_transaction(self, operation, *args, **kwargs):
        """
        トランザクション付きで操作を実行
        
        Args:
            operation: 実行する操作関数
            *args, **kwargs: 操作関数の引数
            
        Returns:
            操作結果
        """
        try:
            result = operation(*args, **kwargs)
            self._db.session.commit()
            return result
        except Exception as e:
            self._db.session.rollback()
            self.log_error(f"Transaction failed: {str(e)}")
            raise
    
    def log_info(self, message: str, extra: Optional[Dict] = None):
        """情報ログ記録"""
        self.logger.info(message, extra=extra or {})
    
    def log_warning(self, message: str, extra: Optional[Dict] = None):
        """警告ログ記録"""
        self.logger.warning(message, extra=extra or {})
    
    def log_error(self, message: str, extra: Optional[Dict] = None):
        """エラーログ記録"""
        self.logger.error(message, extra=extra or {})
    
    def check_permission(self, required_roles: List[str]) -> bool:
        """
        権限チェック
        
        Args:
            required_roles: 必要な役割のリスト
            
        Returns:
            bool: 権限があるかどうか
        """
        if not current_user.is_authenticated:
            return False
        
        return current_user.role in required_roles
    
    def ensure_permission(self, required_roles: List[str]):
        """
        権限確認（例外発生）
        
        Args:
            required_roles: 必要な役割のリスト
            
        Raises:
            PermissionError: 権限がない場合
        """
        if not self.check_permission(required_roles):
            raise PermissionError(f"Required roles: {required_roles}, current role: {current_user.role if current_user.is_authenticated else 'anonymous'}")
    
    def get_current_user_id(self) -> Optional[int]:
        """現在のユーザーIDを取得"""
        return current_user.id if current_user.is_authenticated else None
    
    def validate_input(self, data: Dict[str, Any], required_fields: List[str]) -> Dict[str, str]:
        """
        入力データのバリデーション
        
        Args:
            data: 検証するデータ
            required_fields: 必須フィールドのリスト
            
        Returns:
            Dict[str, str]: エラーメッセージ（キー: フィールド名、値: エラーメッセージ）
        """
        errors = {}
        
        for field in required_fields:
            if field not in data or not data[field]:
                errors[field] = f"{field} is required"
        
        return errors
    
    @abstractmethod
    def get_service_name(self) -> str:
        """サービス名を返す（サブクラスで実装必須）"""
        pass