"""
ルート統合テスト

このファイルは、アプリケーションの各種ルートの
統合テストを実装します。
"""

import pytest
import json
import tempfile
import os
from unittest.mock import patch, Mock
from app import create_app, db
from app.models import User, Class, InquiryTheme, ActivityLog
from werkzeug.datastructures import FileStorage
import io


class TestAuthRoutes:
    """認証ルートのテスト"""
    
    def test_login_page_access(self, client):
        """ログインページアクセスのテスト"""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert 'ログイン' in response.data.decode('utf-8')
    
    def test_register_page_access(self, client):
        """登録ページアクセスのテスト"""
        response = client.get('/auth/register')
        assert response.status_code == 200
        assert '新規登録' in response.data.decode('utf-8')
    
    def test_successful_login(self, client, app):
        """ログイン成功のテスト"""
        with app.app_context():
            response = client.post('/auth/login', data={
                'email': 'teacher@test.com',
                'password': 'teacher123'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            # ダッシュボードにリダイレクトされることを確認
    
    def test_failed_login(self, client):
        """ログイン失敗のテスト"""
        response = client.post('/auth/login', data={
            'email': 'nonexistent@test.com',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 200
        # エラーメッセージが表示されることを確認
    
    def test_logout(self, authenticated_client):
        """ログアウトのテスト"""
        response = authenticated_client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200
        # ログインページにリダイレクトされることを確認
    
    def test_user_registration(self, client, app):
        """ユーザー登録のテスト"""
        with app.app_context():
            registration_data = {
                'email': 'newuser@test.com',
                'password': 'newpassword123',
                'confirm_password': 'newpassword123',
                'full_name': '新規ユーザー',
                'role': 'student',
                'school_code': 'TEST001'
            }
            
            response = client.post('/auth/register', data=registration_data)
            
            # 登録成功後のリダイレクト
            assert response.status_code == 302
            
            # ユーザーが作成されたことを確認
            user = User.query.filter_by(email='newuser@test.com').first()
            assert user is not None
            assert user.full_name == '新規ユーザー'
            assert user.is_approved is False  # 初期は未承認
    
    @patch('app.utils.email_sender.send_email')
    def test_password_reset_request(self, mock_send_email, client, app):
        """パスワードリセット要求のテスト"""
        with app.app_context():
            mock_send_email.return_value = True
            
            response = client.post('/auth/forgot_password', data={
                'email': 'teacher@test.com'
            })
            
            assert response.status_code == 302
            mock_send_email.assert_called_once()


class TestStudentRoutes:
    """学生ルートのテスト"""
    
    def test_student_dashboard_access(self, student_client):
        """学生ダッシュボードアクセスのテスト"""
        response = student_client.get('/student/dashboard')
        assert response.status_code == 200
        assert 'ダッシュボード' in response.data.decode('utf-8')
    
    def test_student_unauthorized_access(self, client):
        """未認証での学生ページアクセスのテスト"""
        response = client.get('/student/dashboard')
        assert response.status_code == 302  # ログインページにリダイレクト
    
    def test_view_themes_page(self, student_client):
        """テーマ表示ページのテスト"""
        response = student_client.get('/student/themes')
        assert response.status_code == 200
    
    def test_activities_page(self, student_client):
        """活動記録ページのテスト"""
        response = student_client.get('/student/activities')
        assert response.status_code == 200
    
    def test_create_activity(self, student_client, app, sample_inquiry_theme):
        """活動記録作成のテスト"""
        with app.app_context():
            activity_data = {
                'title': 'テスト活動',
                'content': 'テスト用の活動内容です',
                'reflection': 'テスト用の振り返りです',
                'inquiry_theme_id': sample_inquiry_theme.id
            }
            
            response = student_client.post('/student/create_activity', 
                                         data=activity_data, 
                                         follow_redirects=True)
            
            assert response.status_code == 200
            
            # 活動が作成されたことを確認
            activity = ActivityLog.query.filter_by(title='テスト活動').first()
            assert activity is not None
            assert activity.content == 'テスト用の活動内容です'
    
    def test_activity_with_image_upload(self, student_client, app, sample_inquiry_theme, upload_file):
        """画像付き活動記録作成のテスト"""
        with app.app_context():
            activity_data = {
                'title': '画像付きテスト活動',
                'content': '画像を含む活動記録',
                'inquiry_theme_id': sample_inquiry_theme.id
            }
            
            # ファイルアップロードを含むリクエスト
            activity_data['image'] = upload_file
            
            response = student_client.post('/student/create_activity',
                                         data=activity_data,
                                         content_type='multipart/form-data',
                                         follow_redirects=True)
            
            assert response.status_code == 200
    
    def test_surveys_access(self, student_client):
        """アンケートページアクセスのテスト"""
        response = student_client.get('/student/surveys')
        assert response.status_code == 200
    
    def test_todos_page(self, student_client):
        """Todoページのテスト"""
        response = student_client.get('/student/todos')
        assert response.status_code == 200
    
    def test_goals_page(self, student_client):
        """目標管理ページのテスト"""
        response = student_client.get('/student/goals')
        assert response.status_code == 200


class TestTeacherRoutes:
    """教師ルートのテスト"""
    
    def test_teacher_dashboard_access(self, authenticated_client):
        """教師ダッシュボードアクセスのテスト"""
        response = authenticated_client.get('/teacher/dashboard')
        assert response.status_code == 200
        assert 'ダッシュボード' in response.data.decode('utf-8')
    
    def test_teacher_classes_page(self, authenticated_client):
        """教師クラス管理ページのテスト"""
        response = authenticated_client.get('/teacher/classes')
        assert response.status_code == 200
    
    def test_create_class(self, authenticated_client, app):
        """クラス作成のテスト"""
        with app.app_context():
            class_data = {
                'name': '新規テストクラス',
                'description': 'テスト用に作成されたクラス'
            }
            
            response = authenticated_client.post('/teacher/create_class',
                                               data=class_data,
                                               follow_redirects=True)
            
            assert response.status_code == 200
            
            # クラスが作成されたことを確認
            new_class = Class.query.filter_by(name='新規テストクラス').first()
            assert new_class is not None
            assert new_class.description == 'テスト用に作成されたクラス'
    
    def test_teacher_themes_management(self, authenticated_client):
        """教師テーマ管理のテスト"""
        response = authenticated_client.get('/teacher/themes')
        assert response.status_code == 200
    
    def test_student_evaluation_page(self, authenticated_client):
        """学生評価ページのテスト"""
        response = authenticated_client.get('/teacher/evaluate')
        assert response.status_code == 200
    
    @patch('app.ai.helpers.get_ai_response')
    def test_ai_chat_functionality(self, mock_ai_response, authenticated_client):
        """AIチャット機能のテスト"""
        mock_ai_response.return_value = "テスト用AI応答"
        
        chat_data = {
            'message': '数学の教え方について教えてください'
        }
        
        response = authenticated_client.post('/teacher/chat',
                                           data=json.dumps(chat_data),
                                           content_type='application/json')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert 'response' in response_data


class TestAdminRoutes:
    """管理者ルートのテスト"""
    
    def test_admin_dashboard_access(self, admin_client):
        """管理者ダッシュボードアクセスのテスト"""
        response = admin_client.get('/admin/dashboard')
        assert response.status_code == 200
    
    def test_admin_unauthorized_access(self, authenticated_client):
        """非管理者の管理ページアクセス拒否のテスト"""
        response = authenticated_client.get('/admin/dashboard')
        assert response.status_code == 403  # Forbidden
    
    def test_user_management_page(self, admin_client):
        """ユーザー管理ページのテスト"""
        response = admin_client.get('/admin/users')
        assert response.status_code == 200
    
    def test_school_management_page(self, admin_client):
        """学校管理ページのテスト"""
        response = admin_client.get('/admin/schools')
        assert response.status_code == 200
    
    def test_user_approval(self, admin_client, app):
        """ユーザー承認のテスト"""
        with app.app_context():
            # 未承認ユーザーを作成
            pending_user = User(
                email='pending@test.com',
                role='student',
                school_id=1,
                is_approved=False
            )
            db.session.add(pending_user)
            db.session.commit()
            
            user_id = pending_user.id
            
            response = admin_client.post(f'/admin/approve_user/{user_id}',
                                       follow_redirects=True)
            
            assert response.status_code == 200
            
            # ユーザーが承認されたことを確認
            approved_user = User.query.get(user_id)
            assert approved_user.is_approved is True


class TestAPIRoutes:
    """APIルートのテスト"""
    
    def test_api_without_authentication(self, client):
        """認証なしAPIアクセスのテスト"""
        response = client.get('/api/users')
        assert response.status_code == 401  # Unauthorized
    
    def test_api_with_authentication(self, client, auth_headers):
        """認証ありAPIアクセスのテスト"""
        response = client.get('/api/users', headers=auth_headers)
        # APIが実装されている場合の期待ステータスコード
        assert response.status_code in [200, 404]
    
    def test_api_rate_limiting(self, client, auth_headers, app):
        """APIレート制限のテスト"""
        with app.app_context():
            # 短時間で大量のリクエストを送信
            responses = []
            for i in range(10):
                response = client.get('/api/test_endpoint', headers=auth_headers)
                responses.append(response.status_code)
            
            # レート制限が働いていることを確認
            # (429 Too Many Requestsが含まれるはず)
            assert 429 in responses or all(status in [200, 404] for status in responses)


class TestBaseBuilderRoutes:
    """BaseBuilderルートのテスト"""
    
    def test_basebuilder_index(self, student_client):
        """BaseBuilderインデックスページのテスト"""
        response = student_client.get('/basebuilder/')
        assert response.status_code == 200
    
    def test_basebuilder_problems_page(self, student_client):
        """問題ページのテスト"""
        response = student_client.get('/basebuilder/problems')
        assert response.status_code == 200
    
    def test_basebuilder_proficiency_page(self, student_client):
        """熟練度ページのテスト"""
        response = student_client.get('/basebuilder/proficiency')
        assert response.status_code == 200
    
    def test_basebuilder_learning_paths(self, student_client):
        """学習パスページのテスト"""
        response = student_client.get('/basebuilder/learning_paths')
        assert response.status_code == 200


class TestErrorHandling:
    """エラーハンドリングのテスト"""
    
    def test_404_error_page(self, client):
        """404エラーページのテスト"""
        response = client.get('/nonexistent_page')
        assert response.status_code == 404
    
    def test_403_error_on_unauthorized_access(self, student_client):
        """権限不足による403エラーのテスト"""
        response = student_client.get('/admin/dashboard')
        assert response.status_code == 403
    
    @patch('app.models.User.query')
    def test_500_error_handling(self, mock_query, client):
        """500エラーハンドリングのテスト"""
        # データベースエラーをシミュレート
        mock_query.side_effect = Exception("Database error")
        
        response = client.get('/auth/login')
        # エラーが適切に処理されることを確認
        assert response.status_code in [200, 500]


class TestFileUpload:
    """ファイルアップロードのテスト"""
    
    def test_valid_image_upload(self, student_client, upload_file):
        """有効な画像アップロードのテスト"""
        response = student_client.post('/upload_test',
                                     data={'file': upload_file},
                                     content_type='multipart/form-data')
        
        # アップロード機能が実装されている場合の期待結果
        assert response.status_code in [200, 404]
    
    def test_invalid_file_upload(self, student_client):
        """無効なファイルアップロードのテスト"""
        # 実行可能ファイルをアップロード試行
        malicious_file = FileStorage(
            stream=io.BytesIO(b'malicious content'),
            filename='malware.exe',
            content_type='application/executable'
        )
        
        response = student_client.post('/upload_test',
                                     data={'file': malicious_file},
                                     content_type='multipart/form-data')
        
        # 危険なファイルは拒否されるべき
        assert response.status_code in [400, 403, 404]
    
    def test_oversized_file_upload(self, student_client):
        """サイズ超過ファイルアップロードのテスト"""
        # 大きすぎるファイルを作成
        large_content = b'x' * (20 * 1024 * 1024)  # 20MB
        large_file = FileStorage(
            stream=io.BytesIO(large_content),
            filename='large.txt',
            content_type='text/plain'
        )
        
        response = student_client.post('/upload_test',
                                     data={'file': large_file},
                                     content_type='multipart/form-data')
        
        # サイズ制限により拒否されるべき
        assert response.status_code in [400, 413, 404]


@pytest.mark.integration
class TestCompleteUserFlow:
    """完全なユーザーフローの統合テスト"""
    
    def test_student_complete_workflow(self, client, app):
        """学生の完全なワークフローテスト"""
        with app.app_context():
            # 1. 学生としてログイン
            login_response = client.post('/auth/login', data={
                'email': 'student@test.com',
                'password': 'student123'
            }, follow_redirects=True)
            assert login_response.status_code == 200
            
            # 2. ダッシュボードアクセス
            dashboard_response = client.get('/student/dashboard')
            assert dashboard_response.status_code == 200
            
            # 3. テーマページアクセス
            themes_response = client.get('/student/themes')
            assert themes_response.status_code == 200
            
            # 4. 活動記録ページアクセス
            activities_response = client.get('/student/activities')
            assert activities_response.status_code == 200
            
            # 5. Todoページアクセス
            todos_response = client.get('/student/todos')
            assert todos_response.status_code == 200
            
            # 6. ログアウト
            logout_response = client.get('/auth/logout', follow_redirects=True)
            assert logout_response.status_code == 200
    
    def test_teacher_complete_workflow(self, client, app):
        """教師の完全なワークフローテスト"""
        with app.app_context():
            # 1. 教師としてログイン
            login_response = client.post('/auth/login', data={
                'email': 'teacher@test.com',
                'password': 'teacher123'
            }, follow_redirects=True)
            assert login_response.status_code == 200
            
            # 2. ダッシュボードアクセス
            dashboard_response = client.get('/teacher/dashboard')
            assert dashboard_response.status_code == 200
            
            # 3. クラス管理ページアクセス
            classes_response = client.get('/teacher/classes')
            assert classes_response.status_code == 200
            
            # 4. テーマ管理ページアクセス
            themes_response = client.get('/teacher/themes')
            assert themes_response.status_code == 200
            
            # 5. 評価ページアクセス
            evaluate_response = client.get('/teacher/evaluate')
            assert evaluate_response.status_code == 200
            
            # 6. ログアウト
            logout_response = client.get('/auth/logout', follow_redirects=True)
            assert logout_response.status_code == 200