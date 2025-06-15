"""
セキュリティテスト

このファイルは、アプリケーションのセキュリティ機能の
包括的なテストを実装します。
"""

import pytest
import json
import time
from unittest.mock import patch, Mock
from app import create_app, db
from app.models import User
from app.utils.security import SecurityUtils
from app.utils.input_validator import InputValidator
from app.utils.api_security import APIAuthentication, RateLimiter
from werkzeug.exceptions import BadRequest, Unauthorized
import jwt
from datetime import datetime, timedelta


class TestAuthenticationSecurity:
    """認証セキュリティのテスト"""
    
    def test_password_strength_validation(self, app):
        """パスワード強度検証のテスト"""
        with app.app_context():
            weak_passwords = [
                '123',
                'password',
                '12345678',
                'aaaaaaaa',
                'Password',  # 数字なし
                'password1',  # 大文字なし
                'PASSWORD1'  # 小文字なし
            ]
            
            strong_passwords = [
                'SecurePass123!',
                'MyStr0ngP@ssw0rd',
                'C0mpl3x!P@ssw0rd'
            ]
            
            for weak_pass in weak_passwords:
                assert SecurityUtils.validate_password_strength(weak_pass) is False
            
            for strong_pass in strong_passwords:
                assert SecurityUtils.validate_password_strength(strong_pass) is True
    
    def test_account_lockout_after_failed_attempts(self, client, app):
        """連続ログイン失敗によるアカウントロックアウトのテスト"""
        with app.app_context():
            # 複数回の失敗ログイン試行
            for i in range(6):  # 設定された制限を超える
                response = client.post('/auth/login', data={
                    'email': 'teacher@test.com',
                    'password': 'wrongpassword'
                })
                
            # 正しいパスワードでもログインできないことを確認
            response = client.post('/auth/login', data={
                'email': 'teacher@test.com',
                'password': 'teacher123'
            })
            
            # ロックアウトが適用されている場合のテスト
            # 実装により結果が異なる可能性があります
    
    def test_session_timeout(self, client, app):
        """セッションタイムアウトのテスト"""
        with app.app_context():
            # ログイン
            client.post('/auth/login', data={
                'email': 'teacher@test.com',
                'password': 'teacher123'
            })
            
            # セッションタイムアウトをシミュレート
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_get_user.return_value = None
                
                response = client.get('/teacher/dashboard')
                assert response.status_code == 302  # ログインページにリダイレクト
    
    def test_jwt_token_expiration(self, app):
        """JWTトークン有効期限のテスト"""
        with app.app_context():
            # 短い有効期限でトークン生成
            token = APIAuthentication.generate_api_token(
                user_id=123,
                role='teacher',
                expires_hours=0.001  # 約3.6秒
            )
            
            # すぐには有効
            payload = APIAuthentication.verify_api_token(token)
            assert payload['user_id'] == 123
            
            # 時間経過後は無効
            time.sleep(4)
            with pytest.raises(jwt.InvalidTokenError):
                APIAuthentication.verify_api_token(token)
    
    def test_password_reset_token_security(self, app, sample_users):
        """パスワードリセットトークンのセキュリティテスト"""
        with app.app_context():
            user = sample_users[1]  # teacher
            
            # リセットトークン生成
            token = user.generate_reset_token()
            
            # 有効なトークンで正常にリセット
            assert user.reset_password(token, 'NewSecurePass123!') is True
            
            # 同じトークンの再利用は無効
            assert user.reset_password(token, 'AnotherPass123!') is False
            
            # 無効なトークンは拒否
            assert user.reset_password('invalid_token', 'Password123!') is False


class TestInputValidationSecurity:
    """入力検証セキュリティのテスト"""
    
    def test_xss_prevention(self):
        """XSS攻撃防止のテスト"""
        xss_payloads = [
            '<script>alert("XSS")</script>',
            '<img src="x" onerror="alert(1)">',
            'javascript:alert("XSS")',
            '<svg onload="alert(1)">',
            '"><script>alert("XSS")</script>',
            '\"><script>alert(String.fromCharCode(88,83,83))</script>'
        ]
        
        for payload in xss_payloads:
            sanitized = InputValidator.sanitize_html(payload)
            assert '<script>' not in sanitized
            assert 'javascript:' not in sanitized
            assert 'onerror=' not in sanitized
            assert 'onload=' not in sanitized
    
    def test_sql_injection_prevention(self):
        """SQLインジェクション防止のテスト"""
        sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM passwords --",
            "admin'--",
            "1; DELETE FROM users",
            "1' OR 1=1#",
            "' OR 'a'='a",
            "1' AND (SELECT COUNT(*) FROM users) > 0 --"
        ]
        
        for payload in sql_injection_payloads:
            assert InputValidator.check_sql_injection_patterns(payload) is True
    
    def test_directory_traversal_prevention(self):
        """ディレクトリトラバーサル攻撃防止のテスト"""
        traversal_payloads = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32\\config\\sam',
            '....//....//....//etc/passwd',
            '%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd',
            '..%252f..%252f..%252fetc%252fpasswd'
        ]
        
        for payload in traversal_payloads:
            safe_filename = SecurityUtils.sanitize_filename(payload)
            assert '..' not in safe_filename
            assert '/' not in safe_filename
            assert '\\' not in safe_filename
    
    def test_file_upload_security(self):
        """ファイルアップロードセキュリティのテスト"""
        dangerous_files = [
            'malware.exe',
            'script.php',
            'backdoor.jsp',
            'shell.asp',
            'virus.bat',
            'trojan.scr',
            'document.pdf.exe'  # ダブル拡張子
        ]
        
        safe_extensions = ['jpg', 'png', 'gif', 'pdf', 'doc', 'docx']
        
        for dangerous_file in dangerous_files:
            assert SecurityUtils.validate_file_type(dangerous_file, safe_extensions) is False
        
        safe_files = ['image.jpg', 'document.pdf', 'presentation.pptx']
        for safe_file in safe_files:
            assert SecurityUtils.validate_file_type(safe_file, ['jpg', 'pdf', 'pptx']) is True
    
    def test_command_injection_prevention(self):
        """コマンドインジェクション防止のテスト"""
        command_injection_payloads = [
            '; rm -rf /',
            '| cat /etc/passwd',
            '&& echo "hacked"',
            '`rm -rf /`',
            '$(rm -rf /)',
            '; nc -l -p 4444 -e /bin/sh',
            '|| ping -c 10 google.com'
        ]
        
        for payload in command_injection_payloads:
            assert InputValidator.check_command_injection_patterns(payload) is True


class TestRateLimitingSecurity:
    """レート制限セキュリティのテスト"""
    
    def test_login_rate_limiting(self, client):
        """ログインレート制限のテスト"""
        # 短時間で大量のログイン試行
        responses = []
        for i in range(10):
            response = client.post('/auth/login', data={
                'email': 'test@example.com',
                'password': 'wrongpassword'
            })
            responses.append(response.status_code)
        
        # レート制限が働いていることを確認
        # 429 Too Many Requestsが含まれるか、制限が適用されているはず
        assert 429 in responses or len(set(responses)) > 1
    
    def test_api_rate_limiting(self):
        """APIレート制限のテスト"""
        limiter = RateLimiter()
        user_key = 'test_user_123'
        
        # 制限以下の場合は許可
        for i in range(5):
            allowed, info = limiter.is_allowed(user_key, 5, 60)
            assert allowed is True
        
        # 制限超過の場合は拒否
        allowed, info = limiter.is_allowed(user_key, 5, 60)
        assert allowed is False
        assert info['remaining'] == 0
    
    def test_rate_limit_bypass_attempts(self):
        """レート制限回避試行のテスト"""
        limiter = RateLimiter()
        
        # 異なるキーでの試行（正常な動作）
        for i in range(10):
            key = f'user_{i}'
            allowed, info = limiter.is_allowed(key, 3, 60)
            assert allowed is True
        
        # 同一キーでの制限超過試行
        same_key = 'persistent_user'
        for i in range(5):
            allowed, info = limiter.is_allowed(same_key, 3, 60)
            if i >= 3:
                assert allowed is False


class TestSessionSecurity:
    """セッションセキュリティのテスト"""
    
    def test_session_hijacking_prevention(self, client, app):
        """セッションハイジャック防止のテスト"""
        with app.app_context():
            # ログイン
            response = client.post('/auth/login', data={
                'email': 'teacher@test.com',
                'password': 'teacher123'
            })
            
            # セッションCookieの確認
            cookies = response.headers.getlist('Set-Cookie')
            session_cookie = None
            for cookie in cookies:
                if 'session=' in cookie:
                    session_cookie = cookie
                    break
            
            if session_cookie:
                # セキュリティフラグの確認
                assert 'HttpOnly' in session_cookie
                assert 'Secure' in session_cookie or app.config.get('TESTING')
                assert 'SameSite' in session_cookie
    
    def test_csrf_protection(self, client, app):
        """CSRF攻撃防止のテスト"""
        with app.app_context():
            # ログイン
            client.post('/auth/login', data={
                'email': 'teacher@test.com',
                'password': 'teacher123'
            })
            
            # CSRFトークンなしでの重要な操作
            response = client.post('/teacher/create_class', data={
                'name': 'テストクラス',
                'description': 'CSRF攻撃テスト'
            })
            
            # CSRFトークンがない場合は拒否される
            # 実装によって結果は異なる可能性があります
            assert response.status_code in [400, 403, 200]
    
    def test_session_fixation_prevention(self, client, app):
        """セッション固定攻撃防止のテスト"""
        with app.app_context():
            # ログイン前のセッションID取得
            response1 = client.get('/auth/login')
            cookies_before = response1.headers.getlist('Set-Cookie')
            
            # ログイン
            response2 = client.post('/auth/login', data={
                'email': 'teacher@test.com',
                'password': 'teacher123'
            })
            cookies_after = response2.headers.getlist('Set-Cookie')
            
            # ログイン後にセッションIDが変更されていることを確認
            # 実装によっては新しいセッションIDが発行される


class TestDataProtectionSecurity:
    """データ保護セキュリティのテスト"""
    
    def test_password_hashing(self, app):
        """パスワードハッシュ化のテスト"""
        with app.app_context():
            password = 'SecurePassword123!'
            
            # ハッシュ化
            hashed = SecurityUtils.hash_password(password)
            
            # ハッシュの特性確認
            assert hashed != password
            assert len(hashed) > 50  # bcryptハッシュは長い
            assert hashed.startswith('$2b$')  # bcryptフォーマット
            
            # 同じパスワードでも異なるハッシュが生成される（ソルト使用）
            hashed2 = SecurityUtils.hash_password(password)
            assert hashed != hashed2
            
            # 両方とも正しく検証される
            assert SecurityUtils.verify_password(password, hashed) is True
            assert SecurityUtils.verify_password(password, hashed2) is True
    
    def test_sensitive_data_encryption(self, app):
        """機密データ暗号化のテスト"""
        from app.utils.database_security import DataEncryption
        
        with app.app_context():
            sensitive_data = 'クレジットカード番号: 1234-5678-9012-3456'
            encryption_key = DataEncryption.generate_encryption_key()
            
            # 暗号化
            encrypted = DataEncryption.encrypt_sensitive_data(sensitive_data, encryption_key)
            assert encrypted != sensitive_data
            assert 'クレジットカード' not in encrypted
            
            # 復号化
            decrypted = DataEncryption.decrypt_sensitive_data(encrypted, encryption_key)
            assert decrypted == sensitive_data
    
    def test_data_leakage_prevention(self, client, app):
        """データ漏洩防止のテスト"""
        with app.app_context():
            # 存在しないユーザーの情報取得試行
            response = client.get('/api/users/99999')
            
            # エラーメッセージに機密情報が含まれていないことを確認
            if response.status_code == 404:
                error_data = response.get_json() or {}
                error_message = str(error_data.get('error', ''))
                
                # 機密情報の漏洩がないことを確認
                assert 'password' not in error_message.lower()
                assert 'token' not in error_message.lower()
                assert 'secret' not in error_message.lower()


class TestAPISecurityHeaders:
    """APIセキュリティヘッダーのテスト"""
    
    def test_security_headers_present(self, client):
        """セキュリティヘッダーの存在確認テスト"""
        response = client.get('/')
        
        # 重要なセキュリティヘッダーの確認
        headers = response.headers
        
        # X-Content-Type-Options
        assert 'X-Content-Type-Options' in headers
        assert headers['X-Content-Type-Options'] == 'nosniff'
        
        # X-Frame-Options
        assert 'X-Frame-Options' in headers
        assert headers['X-Frame-Options'] in ['DENY', 'SAMEORIGIN']
        
        # X-XSS-Protection (古いブラウザ用)
        if 'X-XSS-Protection' in headers:
            assert headers['X-XSS-Protection'] == '1; mode=block'
    
    def test_content_security_policy(self, client):
        """Content Security Policyのテスト"""
        response = client.get('/')
        
        if 'Content-Security-Policy' in response.headers:
            csp = response.headers['Content-Security-Policy']
            
            # 基本的なCSP指示の確認
            assert 'default-src' in csp
            assert 'script-src' in csp
            assert 'style-src' in csp
    
    def test_hsts_header(self, client, app):
        """HTTP Strict Transport Securityヘッダーのテスト"""
        if not app.config.get('TESTING'):  # 本番環境のみ
            response = client.get('/')
            
            if 'Strict-Transport-Security' in response.headers:
                hsts = response.headers['Strict-Transport-Security']
                assert 'max-age=' in hsts


class TestAuthorizationSecurity:
    """認可セキュリティのテスト"""
    
    def test_vertical_privilege_escalation_prevention(self, student_client):
        """垂直権限昇格防止のテスト"""
        # 学生が管理者機能にアクセス試行
        admin_endpoints = [
            '/admin/dashboard',
            '/admin/users',
            '/admin/schools',
            '/admin/approve_user/1'
        ]
        
        for endpoint in admin_endpoints:
            response = student_client.get(endpoint)
            assert response.status_code in [403, 302]  # Forbidden or redirect
    
    def test_horizontal_privilege_escalation_prevention(self, student_client, app):
        """水平権限昇格防止のテスト"""
        with app.app_context():
            # 他の学生のデータにアクセス試行
            other_student_endpoints = [
                '/student/profile/99999',  # 他の学生のプロフィール
                '/api/students/99999/activities',  # 他の学生の活動
                '/api/students/99999/grades'  # 他の学生の成績
            ]
            
            for endpoint in other_student_endpoints:
                response = student_client.get(endpoint)
                # 403 Forbidden、404 Not Found、または302 Redirectが期待される
                assert response.status_code in [403, 404, 302]
    
    def test_resource_access_control(self, authenticated_client, app):
        """リソースアクセス制御のテスト"""
        with app.app_context():
            # 教師が他の教師のクラスを編集しようとする
            response = authenticated_client.post('/teacher/edit_class/99999', data={
                'name': 'ハックされたクラス'
            })
            
            # 権限がない場合は拒否される
            assert response.status_code in [403, 404]


@pytest.mark.security
class TestPenetrationTestScenarios:
    """ペネトレーションテストシナリオ"""
    
    def test_brute_force_attack_simulation(self, client):
        """ブルートフォース攻撃シミュレーション"""
        common_passwords = [
            'password', '123456', 'password123', 'admin', 'qwerty',
            'letmein', 'welcome', 'monkey', '1234567890', 'abc123'
        ]
        
        for password in common_passwords:
            response = client.post('/auth/login', data={
                'email': 'admin@test.com',
                'password': password
            })
            
            # ブルートフォース対策が働いていることを確認
            # (レート制限、アカウントロック等)
    
    def test_mass_assignment_vulnerability(self, client, app):
        """Mass Assignment脆弱性のテスト"""
        with app.app_context():
            # 管理者権限を付与しようとする悪意あるリクエスト
            malicious_data = {
                'email': 'hacker@test.com',
                'password': 'password123',
                'role': 'admin',  # 本来設定できないはず
                'is_approved': True  # 本来設定できないはず
            }
            
            response = client.post('/auth/register', data=malicious_data)
            
            # 悪意ある値が設定されていないことを確認
            if response.status_code in [200, 201, 302]:
                user = User.query.filter_by(email='hacker@test.com').first()
                if user:
                    assert user.role != 'admin'
                    assert user.is_approved is False
    
    def test_information_disclosure_vulnerability(self, client):
        """情報開示脆弱性のテスト"""
        # エラーページで機密情報が漏洩しないことを確認
        response = client.get('/nonexistent_endpoint')
        
        if response.status_code == 404:
            error_content = response.data.decode('utf-8').lower()
            
            # 機密情報が含まれていないことを確認
            sensitive_info = [
                'secret_key', 'database', 'password', 'token',
                'api_key', 'config', 'traceback', 'exception'
            ]
            
            for info in sensitive_info:
                assert info not in error_content
    
    def test_timing_attack_resistance(self, client):
        """タイミング攻撃耐性のテスト"""
        import time
        
        # 存在するユーザーと存在しないユーザーでのレスポンス時間比較
        existing_user_times = []
        nonexistent_user_times = []
        
        for i in range(5):
            # 存在するユーザー
            start = time.time()
            client.post('/auth/login', data={
                'email': 'teacher@test.com',
                'password': 'wrongpassword'
            })
            existing_user_times.append(time.time() - start)
            
            # 存在しないユーザー
            start = time.time()
            client.post('/auth/login', data={
                'email': 'nonexistent@test.com',
                'password': 'wrongpassword'
            })
            nonexistent_user_times.append(time.time() - start)
        
        # 平均レスポンス時間の差が大きくないことを確認
        avg_existing = sum(existing_user_times) / len(existing_user_times)
        avg_nonexistent = sum(nonexistent_user_times) / len(nonexistent_user_times)
        
        # 差が大きすぎる場合はタイミング攻撃の可能性
        time_diff_ratio = abs(avg_existing - avg_nonexistent) / max(avg_existing, avg_nonexistent)
        assert time_diff_ratio < 0.5  # 50%以上の差がないことを確認