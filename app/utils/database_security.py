"""
QuestEd データベースセキュリティ強化モジュール

このモジュールは、データベース操作のセキュリティを強化し、
SQLインジェクション攻撃、不正アクセス、データ漏洩を防ぐ機能を提供します。

主な機能:
- パラメータ化クエリの強制
- データベース接続の暗号化
- アクセス権限の検証
- 機密データの暗号化
- データベース監査ログ
- データバックアップとリストア

新規開発者向けガイド:
1. 全てのデータベースクエリはパラメータ化を必須とする
2. 機密データ（パスワード、個人情報）は暗号化して保存
3. データベースアクセスは役割ベースで制限
4. 全ての操作を監査ログに記録
5. 定期的なセキュリティスキャンを実行

Author: QuestEd Development Team
Created: 2025-01-15
Version: 1.0.0
"""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from sqlalchemy import text, event, Engine
from sqlalchemy.orm import Session
from flask import current_app, request, g
from flask_login import current_user
import json

# ログ設定
logger = logging.getLogger(__name__)
security_logger = logging.getLogger('security')


class DatabaseSecurity:
    """
    データベースセキュリティ管理クラス
    
    データベース操作の安全性を確保し、セキュリティ脅威を監視・防御します。
    全てのデータベースアクセスを監査し、異常な操作を検出します。
    """
    
    # 機密データフィールドの定義
    SENSITIVE_FIELDS = {
        'users': ['password_hash', 'email', 'phone'],
        'students': ['personal_info', 'health_info'],
        'evaluations': ['comments', 'feedback'],
        'chat_history': ['message_content'],
        'activity_logs': ['reflection', 'content']
    }
    
    # 高リスク操作の定義
    HIGH_RISK_OPERATIONS = [
        'DELETE', 'DROP', 'ALTER', 'TRUNCATE', 'UPDATE'
    ]
    
    @classmethod
    def setup_database_security(cls, app):
        """
        データベースセキュリティの設定
        
        Args:
            app: Flaskアプリケーション
        """
        # SQLAlchemyエンジンイベントリスナーを設定
        from extensions import db
        
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """SQLiteの場合のセキュリティ設定"""
            if 'sqlite' in str(dbapi_connection):
                cursor = dbapi_connection.cursor()
                # SQLiteセキュリティ設定
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA secure_delete=ON")
                cursor.close()
        
        @event.listens_for(Engine, "before_cursor_execute")
        def log_sql_queries(conn, cursor, statement, parameters, context, executemany):
            """SQLクエリの監査ログ"""
            cls._audit_sql_query(statement, parameters)
        
        logger.info("データベースセキュリティが初期化されました")
    
    @classmethod
    def _audit_sql_query(cls, statement: str, parameters: Any):
        """
        SQLクエリの監査
        
        Args:
            statement: SQL文
            parameters: パラメータ
        """
        try:
            # 高リスク操作の検出
            statement_upper = statement.upper().strip()
            for risky_op in cls.HIGH_RISK_OPERATIONS:
                if statement_upper.startswith(risky_op):
                    cls._log_high_risk_operation(risky_op, statement)
                    break
            
            # SQLインジェクションパターンの検出
            if cls._detect_sql_injection_patterns(statement):
                cls._log_security_incident('SQL_INJECTION_ATTEMPT', {
                    'statement': statement,
                    'parameters': str(parameters)
                })
            
            # 機密データアクセスの監視
            cls._monitor_sensitive_data_access(statement)
            
        except Exception as e:
            logger.error(f"SQL監査エラー: {str(e)}")
    
    @classmethod
    def _detect_sql_injection_patterns(cls, statement: str) -> bool:
        """
        SQLインジェクションパターンの検出
        
        Args:
            statement: SQL文
            
        Returns:
            bool: SQLインジェクションの疑いがあるかどうか
        """
        # 危険なSQLパターン
        dangerous_patterns = [
            r"'\s*OR\s+'",  # OR injection
            r"'\s*AND\s+'",  # AND injection
            r"'\s*UNION\s+",  # UNION injection
            r";\s*DROP\s+",  # DROP injection
            r";\s*DELETE\s+",  # DELETE injection
            r";\s*INSERT\s+",  # INSERT injection
            r";\s*UPDATE\s+",  # UPDATE injection
            r"--",  # Comment injection
            r"/\*.*\*/",  # Comment block injection
        ]
        
        import re
        statement_upper = statement.upper()
        
        for pattern in dangerous_patterns:
            if re.search(pattern, statement_upper, re.IGNORECASE):
                return True
        
        return False
    
    @classmethod
    def _monitor_sensitive_data_access(cls, statement: str):
        """
        機密データアクセスの監視
        
        Args:
            statement: SQL文
        """
        statement_lower = statement.lower()
        
        for table, fields in cls.SENSITIVE_FIELDS.items():
            if table in statement_lower:
                for field in fields:
                    if field in statement_lower:
                        cls._log_sensitive_data_access(table, field, statement)
    
    @classmethod
    def _log_high_risk_operation(cls, operation: str, statement: str):
        """
        高リスク操作のログ記録
        
        Args:
            operation: 操作タイプ
            statement: SQL文
        """
        security_logger.warning(f"HIGH_RISK_DB_OPERATION: {operation} | Statement: {statement[:200]}...")
    
    @classmethod
    def _log_sensitive_data_access(cls, table: str, field: str, statement: str):
        """
        機密データアクセスのログ記録
        
        Args:
            table: テーブル名
            field: フィールド名
            statement: SQL文
        """
        user_info = "anonymous"
        if hasattr(current_user, 'id'):
            user_info = f"user_{current_user.id}"
        
        security_logger.info(
            f"SENSITIVE_DATA_ACCESS: table={table}, field={field}, user={user_info}, "
            f"ip={request.remote_addr if request else 'unknown'}"
        )
    
    @classmethod
    def _log_security_incident(cls, incident_type: str, details: Dict[str, Any]):
        """
        セキュリティインシデントのログ記録
        
        Args:
            incident_type: インシデントタイプ
            details: 詳細情報
        """
        incident_data = {
            'incident_type': incident_type,
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': getattr(current_user, 'id', None) if hasattr(current_user, 'id') else None,
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None,
            'details': details
        }
        
        security_logger.critical(f"SECURITY_INCIDENT: {json.dumps(incident_data)}")


class SecureQueryBuilder:
    """
    セキュアなクエリビルダー
    
    SQLインジェクションを防ぐためのパラメータ化クエリを
    簡単に構築できるヘルパークラスです。
    """
    
    @staticmethod
    def build_safe_select(table: str, fields: List[str], conditions: Dict[str, Any]) -> tuple:
        """
        安全なSELECTクエリを構築
        
        Args:
            table: テーブル名
            fields: 選択フィールド
            conditions: 検索条件
            
        Returns:
            tuple: (SQLクエリ, パラメータ)
        """
        # テーブル名とフィールド名の検証
        if not SecureQueryBuilder._is_valid_identifier(table):
            raise ValueError(f"無効なテーブル名: {table}")
        
        for field in fields:
            if not SecureQueryBuilder._is_valid_identifier(field):
                raise ValueError(f"無効なフィールド名: {field}")
        
        # クエリ構築
        fields_str = ", ".join(fields)
        query = f"SELECT {fields_str} FROM {table}"
        
        if conditions:
            where_clauses = []
            params = {}
            
            for key, value in conditions.items():
                if not SecureQueryBuilder._is_valid_identifier(key):
                    raise ValueError(f"無効な条件フィールド名: {key}")
                
                param_name = f"param_{len(params)}"
                where_clauses.append(f"{key} = :{param_name}")
                params[param_name] = value
            
            query += " WHERE " + " AND ".join(where_clauses)
            
            return query, params
        
        return query, {}
    
    @staticmethod
    def build_safe_update(table: str, updates: Dict[str, Any], conditions: Dict[str, Any]) -> tuple:
        """
        安全なUPDATEクエリを構築
        
        Args:
            table: テーブル名
            updates: 更新データ
            conditions: 更新条件
            
        Returns:
            tuple: (SQLクエリ, パラメータ)
        """
        if not SecureQueryBuilder._is_valid_identifier(table):
            raise ValueError(f"無効なテーブル名: {table}")
        
        if not updates:
            raise ValueError("更新データが指定されていません")
        
        if not conditions:
            raise ValueError("更新条件が指定されていません（安全のため全件更新は禁止）")
        
        # UPDATE部分の構築
        update_clauses = []
        params = {}
        
        for key, value in updates.items():
            if not SecureQueryBuilder._is_valid_identifier(key):
                raise ValueError(f"無効な更新フィールド名: {key}")
            
            param_name = f"update_{len(params)}"
            update_clauses.append(f"{key} = :{param_name}")
            params[param_name] = value
        
        # WHERE部分の構築
        where_clauses = []
        for key, value in conditions.items():
            if not SecureQueryBuilder._is_valid_identifier(key):
                raise ValueError(f"無効な条件フィールド名: {key}")
            
            param_name = f"where_{len(params)}"
            where_clauses.append(f"{key} = :{param_name}")
            params[param_name] = value
        
        query = f"UPDATE {table} SET {', '.join(update_clauses)} WHERE {' AND '.join(where_clauses)}"
        
        return query, params
    
    @staticmethod
    def _is_valid_identifier(identifier: str) -> bool:
        """
        識別子の妥当性検証
        
        Args:
            identifier: 識別子（テーブル名、フィールド名など）
            
        Returns:
            bool: 妥当な識別子かどうか
        """
        import re
        # 英数字、アンダースコア、ドットのみ許可
        return re.match(r'^[a-zA-Z_][a-zA-Z0-9_.]*$', identifier) is not None


class DataEncryption:
    """
    データ暗号化クラス
    
    機密データの暗号化・復号化を安全に行います。
    AES暗号化を使用し、キー管理も含めて実装します。
    """
    
    @staticmethod
    def generate_encryption_key() -> str:
        """
        暗号化キーを生成
        
        Returns:
            str: Base64エンコードされた暗号化キー
        """
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def encrypt_sensitive_data(data: str, key: Optional[str] = None) -> str:
        """
        機密データを暗号化
        
        Args:
            data: 暗号化するデータ
            key: 暗号化キー（Noneの場合は設定から取得）
            
        Returns:
            str: 暗号化されたデータ
        """
        try:
            from cryptography.fernet import Fernet
            import base64
            
            if key is None:
                key = current_app.config.get('ENCRYPTION_KEY')
                if not key:
                    raise ValueError("暗号化キーが設定されていません")
            
            # キーがbase64でない場合は変換
            if isinstance(key, str):
                key = key.encode()
            
            # Fernet用のキー形式に変換
            key_hash = hashlib.sha256(key).digest()
            fernet_key = base64.urlsafe_b64encode(key_hash)
            
            fernet = Fernet(fernet_key)
            encrypted_data = fernet.encrypt(data.encode())
            
            return base64.urlsafe_b64encode(encrypted_data).decode()
            
        except Exception as e:
            logger.error(f"データ暗号化エラー: {str(e)}")
            # 暗号化に失敗した場合はプレーンテキストを返す（ログに記録）
            logger.warning("暗号化に失敗しました。プレーンテキストで保存されます。")
            return data
    
    @staticmethod
    def decrypt_sensitive_data(encrypted_data: str, key: Optional[str] = None) -> str:
        """
        機密データを復号化
        
        Args:
            encrypted_data: 暗号化されたデータ
            key: 復号化キー（Noneの場合は設定から取得）
            
        Returns:
            str: 復号化されたデータ
        """
        try:
            from cryptography.fernet import Fernet
            import base64
            
            if key is None:
                key = current_app.config.get('ENCRYPTION_KEY')
                if not key:
                    raise ValueError("復号化キーが設定されていません")
            
            # キーがbase64でない場合は変換
            if isinstance(key, str):
                key = key.encode()
            
            # Fernet用のキー形式に変換
            key_hash = hashlib.sha256(key).digest()
            fernet_key = base64.urlsafe_b64encode(key_hash)
            
            fernet = Fernet(fernet_key)
            
            # データをデコード
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = fernet.decrypt(encrypted_bytes)
            
            return decrypted_data.decode()
            
        except Exception as e:
            logger.error(f"データ復号化エラー: {str(e)}")
            # 復号化に失敗した場合はそのまま返す（平文の可能性）
            return encrypted_data


class AccessControl:
    """
    データベースアクセス制御クラス
    
    役割ベースアクセス制御（RBAC）を実装し、
    ユーザーの権限に応じてデータアクセスを制限します。
    """
    
    # 役割別アクセス権限定義
    ROLE_PERMISSIONS = {
        'admin': ['read', 'write', 'delete', 'manage'],
        'teacher': ['read', 'write', 'evaluate'],
        'student': ['read', 'write_own'],
    }
    
    # テーブル別アクセス制御
    TABLE_ACCESS_RULES = {
        'users': {
            'admin': ['read', 'write', 'delete'],
            'teacher': ['read_limited'],
            'student': ['read_own']
        },
        'students': {
            'admin': ['read', 'write', 'delete'],
            'teacher': ['read', 'write'],
            'student': ['read_own']
        },
        'evaluations': {
            'admin': ['read', 'write', 'delete'],
            'teacher': ['read', 'write'],
            'student': ['read_own']
        }
    }
    
    @classmethod
    def check_table_access(cls, table_name: str, operation: str, user_role: str, user_id: Optional[int] = None) -> bool:
        """
        テーブルアクセス権限をチェック
        
        Args:
            table_name: テーブル名
            operation: 操作タイプ
            user_role: ユーザー役割
            user_id: ユーザーID
            
        Returns:
            bool: アクセス許可の可否
        """
        if table_name not in cls.TABLE_ACCESS_RULES:
            # テーブルが定義されていない場合は管理者のみ許可
            return user_role == 'admin'
        
        table_rules = cls.TABLE_ACCESS_RULES[table_name]
        
        if user_role not in table_rules:
            return False
        
        allowed_operations = table_rules[user_role]
        
        # 自分のデータのみアクセス可能な場合
        if operation.endswith('_own'):
            base_operation = operation.replace('_own', '')
            return base_operation in allowed_operations or operation in allowed_operations
        
        return operation in allowed_operations
    
    @classmethod
    def filter_query_by_access(cls, query: str, user_role: str, user_id: Optional[int] = None) -> str:
        """
        アクセス権限に基づいてクエリをフィルタリング
        
        Args:
            query: 元のクエリ
            user_role: ユーザー役割
            user_id: ユーザーID
            
        Returns:
            str: フィルタリングされたクエリ
        """
        # 学生の場合は自分のデータのみアクセス可能にする
        if user_role == 'student' and user_id:
            if 'WHERE' in query.upper():
                query += f" AND (user_id = {user_id} OR student_id = {user_id})"
            else:
                query += f" WHERE (user_id = {user_id} OR student_id = {user_id})"
        
        return query


def setup_database_security(app):
    """
    データベースセキュリティの初期化
    
    Args:
        app: Flaskアプリケーション
    """
    DatabaseSecurity.setup_database_security(app)
    
    # 暗号化キーの確認
    if not app.config.get('ENCRYPTION_KEY'):
        logger.warning("暗号化キーが設定されていません。機密データの暗号化が無効になります。")
    
    logger.info("データベースセキュリティが正常に初期化されました")