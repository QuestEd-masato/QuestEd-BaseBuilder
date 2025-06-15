"""
ユーティリティ関数の単体テスト

このファイルは、app/utils以下の各種ユーティリティ関数の
単体テストを実装します。
"""

import pytest
import jwt
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from app.utils.security import SecurityUtils
from app.utils.input_validator import InputValidator
from app.utils.error_handler import ErrorHandler
from app.utils.database_security import DatabaseSecurity, SecureQueryBuilder, DataEncryption
from app.utils.api_security import APIAuthentication, RateLimiter, APISecurityDecorator
from werkzeug.exceptions import ValidationError, BadRequest
import time


class TestSecurityUtils:
    """セキュリティユーティリティのテスト"""
    
    def test_generate_secure_token(self):
        """セキュアトークン生成のテスト"""
        token = SecurityUtils.generate_secure_token()
        assert len(token) == 64  # 32バイト = 64文字（hex）
        assert isinstance(token, str)
        
        # 複数回生成して異なることを確認
        token2 = SecurityUtils.generate_secure_token()
        assert token != token2
    
    def test_hash_password(self):
        """パスワードハッシュ化のテスト"""
        password = "test_password_123"
        hashed = SecurityUtils.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcryptハッシュは長い
        assert SecurityUtils.verify_password(password, hashed) is True
        assert SecurityUtils.verify_password("wrong_password", hashed) is False
    
    def test_sanitize_filename(self):
        """ファイル名サニタイズのテスト"""
        dangerous_filename = "../../../etc/passwd"
        safe_filename = SecurityUtils.sanitize_filename(dangerous_filename)
        assert ".." not in safe_filename
        assert "/" not in safe_filename
        
        normal_filename = "document.pdf"
        assert SecurityUtils.sanitize_filename(normal_filename) == normal_filename
    
    def test_validate_file_type(self):
        """ファイルタイプ検証のテスト"""
        # 許可されるファイル
        assert SecurityUtils.validate_file_type("image.jpg", ['jpg', 'png']) is True
        assert SecurityUtils.validate_file_type("document.pdf", ['pdf', 'doc']) is True
        
        # 許可されないファイル
        assert SecurityUtils.validate_file_type("script.exe", ['jpg', 'png']) is False
        assert SecurityUtils.validate_file_type("file.php", ['jpg', 'png']) is False


class TestInputValidator:
    """入力検証のテスト"""
    
    def test_validate_email(self):
        """メールアドレス検証のテスト"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.jp",
            "admin@school.edu"
        ]
        
        invalid_emails = [
            "invalid_email",
            "@domain.com",
            "user@",
            "user space@domain.com",
            "<script>alert('xss')</script>@domain.com"
        ]
        
        for email in valid_emails:
            assert InputValidator.validate_email(email) is True
        
        for email in invalid_emails:
            assert InputValidator.validate_email(email) is False
    
    def test_sanitize_html(self):
        """HTML サニタイゼーションのテスト"""
        dangerous_html = "<script>alert('XSS')</script><p>Normal content</p>"
        sanitized = InputValidator.sanitize_html(dangerous_html)
        
        assert "<script>" not in sanitized
        assert "alert" not in sanitized
        assert "<p>Normal content</p>" in sanitized
    
    def test_validate_and_sanitize_data(self):
        """データ検証・サニタイゼーションのテスト"""
        schema = {
            'name': {'required': True, 'type': 'string', 'max_length': 50},
            'email': {'required': True, 'type': 'email'},
            'age': {'required': False, 'type': 'integer', 'min': 0, 'max': 150}
        }
        
        valid_data = {
            'name': 'テストユーザー',
            'email': 'test@example.com',
            'age': 25
        }
        
        result = InputValidator.validate_and_sanitize(valid_data, schema)
        assert result['name'] == 'テストユーザー'
        assert result['email'] == 'test@example.com'
        assert result['age'] == 25
        
        # 無効なデータ
        invalid_data = {
            'name': '<script>alert("xss")</script>',
            'email': 'invalid-email',
            'age': -5
        }
        
        with pytest.raises(ValidationError):
            InputValidator.validate_and_sanitize(invalid_data, schema)
    
    def test_check_sql_injection_patterns(self):
        """SQLインジェクションパターン検出のテスト"""
        safe_inputs = [
            "normal text",
            "user@example.com",
            "SELECT * FROM users"  # 通常のSQLは許可
        ]
        
        dangerous_inputs = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "UNION SELECT password FROM users",
            "admin' --",
            "1; DELETE FROM users"
        ]
        
        for safe_input in safe_inputs:
            assert InputValidator.check_sql_injection_patterns(safe_input) is False
        
        for dangerous_input in dangerous_inputs:
            assert InputValidator.check_sql_injection_patterns(dangerous_input) is True


class TestErrorHandler:
    """エラーハンドリングのテスト"""
    
    def test_handle_validation_error(self):
        """バリデーションエラー処理のテスト"""
        error = ValidationError("Invalid input data")
        response_data, status_code = ErrorHandler.handle_validation_error(error)
        
        assert status_code == 400
        assert 'error' in response_data
        assert response_data['error'] == "Invalid input data"
    
    def test_handle_authentication_error(self):
        """認証エラー処理のテスト"""
        response_data, status_code = ErrorHandler.handle_authentication_error("Invalid credentials")
        
        assert status_code == 401
        assert response_data['error'] == "Invalid credentials"
    
    def test_handle_authorization_error(self):
        """認可エラー処理のテスト"""
        response_data, status_code = ErrorHandler.handle_authorization_error("Access denied")
        
        assert status_code == 403
        assert response_data['error'] == "Access denied"
    
    def test_handle_database_error(self):
        """データベースエラー処理のテスト"""
        error = Exception("Database connection failed")
        response_data, status_code = ErrorHandler.handle_database_error(error)
        
        assert status_code == 500
        assert 'error' in response_data
        # 本番環境では詳細なエラー情報は隠蔽される
        assert "internal error" in response_data['error'].lower()


class TestSecureQueryBuilder:
    """セキュアクエリビルダーのテスト"""
    
    def test_build_safe_select(self):
        """安全なSELECTクエリ構築のテスト"""
        table = "users"
        fields = ["id", "username", "email"]
        conditions = {"role": "student", "is_active": True}
        
        query, params = SecureQueryBuilder.build_safe_select(table, fields, conditions)
        
        assert "SELECT id, username, email FROM users" in query
        assert "WHERE" in query
        assert "role = :param_0" in query
        assert "is_active = :param_1" in query
        assert params['param_0'] == "student"
        assert params['param_1'] is True
    
    def test_build_safe_update(self):
        """安全なUPDATEクエリ構築のテスト"""
        table = "users"
        updates = {"last_login": datetime.now(), "login_count": 5}
        conditions = {"id": 123}
        
        query, params = SecureQueryBuilder.build_safe_update(table, updates, conditions)
        
        assert "UPDATE users SET" in query
        assert "WHERE id = :where_" in query
        assert len(params) == 3  # 2 updates + 1 condition
    
    def test_invalid_identifier_rejection(self):
        """無効な識別子の拒否テスト"""
        with pytest.raises(ValueError):
            SecureQueryBuilder.build_safe_select("users; DROP TABLE", ["id"], {})
        
        with pytest.raises(ValueError):
            SecureQueryBuilder.build_safe_select("users", ["id'; DROP TABLE users; --"], {})


class TestDataEncryption:
    """データ暗号化のテスト"""
    
    def test_encryption_decryption_cycle(self, app):
        """暗号化・復号化サイクルのテスト"""
        with app.app_context():
            original_data = "機密情報：パスワード123"
            encryption_key = DataEncryption.generate_encryption_key()
            
            # 暗号化
            encrypted_data = DataEncryption.encrypt_sensitive_data(original_data, encryption_key)
            assert encrypted_data != original_data
            assert len(encrypted_data) > len(original_data)
            
            # 復号化
            decrypted_data = DataEncryption.decrypt_sensitive_data(encrypted_data, encryption_key)
            assert decrypted_data == original_data
    
    def test_different_keys_fail_decryption(self):
        """異なるキーでの復号化失敗テスト"""
        original_data = "secret data"
        key1 = DataEncryption.generate_encryption_key()
        key2 = DataEncryption.generate_encryption_key()
        
        encrypted_data = DataEncryption.encrypt_sensitive_data(original_data, key1)
        
        # 異なるキーでの復号化は元のデータと異なる結果になる
        decrypted_with_wrong_key = DataEncryption.decrypt_sensitive_data(encrypted_data, key2)
        assert decrypted_with_wrong_key != original_data


class TestAPIAuthentication:
    """API認証のテスト"""
    
    def test_generate_and_verify_token(self, app):
        """APIトークン生成・検証のテスト"""
        with app.app_context():
            user_id = 123
            role = "teacher"
            
            # トークン生成
            token = APIAuthentication.generate_api_token(user_id, role)
            assert isinstance(token, str)
            assert len(token) > 100  # JWTトークンは長い
            
            # トークン検証
            payload = APIAuthentication.verify_api_token(token)
            assert payload['user_id'] == user_id
            assert payload['role'] == role
            assert 'exp' in payload
            assert 'iat' in payload
            assert 'jti' in payload
    
    def test_expired_token_rejection(self, app):
        """期限切れトークンの拒否テスト"""
        with app.app_context():
            # 負の有効期限でトークン生成（即座に期限切れ）
            with patch('app.utils.api_security.datetime') as mock_datetime:
                # 過去の時間を設定
                past_time = datetime.utcnow() - timedelta(hours=1)
                mock_datetime.utcnow.return_value = past_time
                
                token = APIAuthentication.generate_api_token(123, "teacher", expires_hours=-1)
                
                # 現在時刻に戻して検証
                mock_datetime.utcnow.return_value = datetime.utcnow()
                
                with pytest.raises(jwt.InvalidTokenError):
                    APIAuthentication.verify_api_token(token)
    
    def test_invalid_token_rejection(self, app):
        """無効なトークンの拒否テスト"""
        with app.app_context():
            invalid_tokens = [
                "invalid.token.here",
                "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid",
                "",
                "not.a.jwt.token.at.all"
            ]
            
            for invalid_token in invalid_tokens:
                with pytest.raises(jwt.InvalidTokenError):
                    APIAuthentication.verify_api_token(invalid_token)


class TestRateLimiter:
    """レート制限のテスト"""
    
    def test_rate_limit_allows_under_limit(self):
        """制限以下でのアクセス許可テスト"""
        limiter = RateLimiter()
        key = "test_user_123"
        limit = 5
        window = 60
        
        # 制限以下のリクエスト
        for i in range(limit):
            allowed, info = limiter.is_allowed(key, limit, window)
            assert allowed is True
            assert info['remaining'] >= 0
    
    def test_rate_limit_blocks_over_limit(self):
        """制限超過でのアクセス拒否テスト"""
        limiter = RateLimiter()
        key = "test_user_456"
        limit = 3
        window = 60
        
        # 制限まで使い切る
        for i in range(limit):
            allowed, info = limiter.is_allowed(key, limit, window)
            assert allowed is True
        
        # 制限超過
        allowed, info = limiter.is_allowed(key, limit, window)
        assert allowed is False
        assert info['remaining'] == 0
    
    def test_rate_limit_window_reset(self):
        """時間窓リセットのテスト"""
        limiter = RateLimiter()
        key = "test_user_789"
        limit = 2
        window = 1  # 1秒の窓
        
        # 制限まで使い切る
        for i in range(limit):
            allowed, info = limiter.is_allowed(key, limit, window)
            assert allowed is True
        
        # 制限超過
        allowed, info = limiter.is_allowed(key, limit, window)
        assert allowed is False
        
        # 時間窓が過ぎるまで待機
        time.sleep(1.1)
        
        # 制限がリセットされることを確認
        allowed, info = limiter.is_allowed(key, limit, window)
        assert allowed is True


class TestDatabaseSecurity:
    """データベースセキュリティのテスト"""
    
    def test_sql_injection_pattern_detection(self):
        """SQLインジェクションパターン検出のテスト"""
        safe_statements = [
            "SELECT * FROM users WHERE id = ?",
            "INSERT INTO logs (message) VALUES (?)",
            "UPDATE users SET last_login = NOW() WHERE id = ?"
        ]
        
        dangerous_statements = [
            "SELECT * FROM users WHERE id = 1 OR 1=1",
            "'; DROP TABLE users; --",
            "SELECT * FROM users UNION SELECT * FROM passwords",
            "DELETE FROM users WHERE 1=1"
        ]
        
        for statement in safe_statements:
            assert DatabaseSecurity._detect_sql_injection_patterns(statement) is False
        
        for statement in dangerous_statements:
            assert DatabaseSecurity._detect_sql_injection_patterns(statement) is True
    
    @patch('app.utils.database_security.security_logger')
    def test_high_risk_operation_logging(self, mock_logger):
        """高リスク操作のログ記録テスト"""
        dangerous_statement = "DROP TABLE users"
        
        DatabaseSecurity._audit_sql_query(dangerous_statement, [])
        
        # ログが記録されることを確認
        mock_logger.warning.assert_called()
        call_args = mock_logger.warning.call_args[0][0]
        assert "HIGH_RISK_DB_OPERATION" in call_args
        assert "DROP" in call_args
    
    @patch('app.utils.database_security.security_logger')
    def test_sensitive_data_access_logging(self, mock_logger):
        """機密データアクセスのログ記録テスト"""
        sensitive_statement = "SELECT password_hash FROM users WHERE id = 1"
        
        DatabaseSecurity._audit_sql_query(sensitive_statement, [])
        
        # 機密データアクセスがログに記録されることを確認
        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args[0][0]
        assert "SENSITIVE_DATA_ACCESS" in call_args
        assert "password_hash" in call_args


@pytest.mark.integration
class TestSecurityIntegration:
    """セキュリティ機能の統合テスト"""
    
    def test_complete_security_flow(self, app):
        """完全なセキュリティフローのテスト"""
        with app.app_context():
            # 1. 入力データの検証・サニタイゼーション
            user_input = {
                'username': '<script>alert("xss")</script>admin',
                'password': 'secure_password_123',
                'email': 'admin@test.com'
            }
            
            schema = {
                'username': {'required': True, 'type': 'string', 'max_length': 50},
                'password': {'required': True, 'type': 'string', 'min_length': 8},
                'email': {'required': True, 'type': 'email'}
            }
            
            # サニタイゼーション
            clean_data = InputValidator.validate_and_sanitize(user_input, schema)
            assert '<script>' not in clean_data['username']
            
            # 2. パスワードハッシュ化
            password_hash = SecurityUtils.hash_password(clean_data['password'])
            
            # 3. 機密データ暗号化
            encryption_key = DataEncryption.generate_encryption_key()
            encrypted_email = DataEncryption.encrypt_sensitive_data(clean_data['email'], encryption_key)
            
            # 4. APIトークン生成
            api_token = APIAuthentication.generate_api_token(123, 'admin')
            
            # 5. トークン検証
            payload = APIAuthentication.verify_api_token(api_token)
            assert payload['user_id'] == 123
            assert payload['role'] == 'admin'
            
            # 6. データ復号化
            decrypted_email = DataEncryption.decrypt_sensitive_data(encrypted_email, encryption_key)
            assert decrypted_email == clean_data['email']
            
            # 7. パスワード検証
            assert SecurityUtils.verify_password(clean_data['password'], password_hash) is True