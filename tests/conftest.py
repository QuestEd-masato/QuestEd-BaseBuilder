import pytest
import tempfile
import os
from app import create_app, db
from app.models import User, School, Class, InquiryTheme, ActivityLog
from app.utils.api_security import APIAuthentication
from config import TestingConfig
from datetime import datetime, timedelta
import json

# 追加のフィクスチャをインポート
from .conftest_fixtures import *

@pytest.fixture(scope='function')
def app():
    """テスト用アプリケーションインスタンス"""
    # テスト用の一時的なデータベースファイル
    db_fd, db_path = tempfile.mkstemp()
    
    # テスト設定の拡張
    class TestConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'
        WTF_CSRF_ENABLED = False
        TESTING = True
        SECRET_KEY = 'test-secret-key'
        UPLOAD_FOLDER = tempfile.mkdtemp()
    
    app = create_app(TestConfig)
    
    with app.app_context():
        # データベース初期化
        db.create_all()
        
        # テストデータのシード
        _seed_test_data()
        
        yield app
        
        # クリーンアップ
        db.session.remove()
        db.drop_all()
        
    # テンポラリファイルの削除
    os.close(db_fd)
    os.unlink(db_path)
    
    # アップロードフォルダの削除
    import shutil
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        shutil.rmtree(app.config['UPLOAD_FOLDER'])

def _seed_test_data():
    """テスト用基本データの投入"""
    # 基本学校データ
    school = School(
        name='テスト学校',
        school_code='TEST001',
        address='東京都テスト区'
    )
    db.session.add(school)
    db.session.commit()
    
    # 基本ユーザーデータ
    admin = User(
        email='admin@test.com',
        role='admin',
        full_name='テスト管理者',
        school_id=school.id,
        is_approved=True,
        email_verified=True
    )
    admin.set_password('admin123')
    
    teacher = User(
        email='teacher@test.com',
        role='teacher', 
        full_name='テスト教師',
        school_id=school.id,
        is_approved=True,
        email_verified=True
    )
    teacher.set_password('teacher123')
    
    student = User(
        email='student@test.com',
        role='student',
        full_name='テスト生徒',
        school_id=school.id,
        is_approved=True,
        email_verified=True
    )
    student.set_password('student123')
    
    db.session.add_all([admin, teacher, student])
    db.session.commit()

@pytest.fixture
def client(app):
    """テストクライアント"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """テストランナー"""
    return app.test_cli_runner()

@pytest.fixture
def auth_headers(app):
    """認証済みAPIヘッダー"""
    with app.app_context():
        # APIトークン生成
        token = APIAuthentication.generate_api_token(
            user_id=2,  # teacher user
            role='teacher'
        )
        return {'Authorization': f'Bearer {token}'}

@pytest.fixture
def authenticated_client(client, app):
    """認証済みクライアント（セッションベース）"""
    with app.app_context():
        # 教師でログイン
        response = client.post('/auth/login', data={
            'email': 'teacher@test.com',
            'password': 'teacher123'
        }, follow_redirects=True)
        
        return client

@pytest.fixture
def student_client(client, app):
    """生徒として認証済みのクライアント"""
    with app.app_context():
        response = client.post('/auth/login', data={
            'email': 'student@test.com',
            'password': 'student123'
        }, follow_redirects=True)
        
        return client

@pytest.fixture
def admin_client(client, app):
    """管理者として認証済みのクライアント"""
    with app.app_context():
        response = client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'admin123'
        }, follow_redirects=True)
        
        return client

@pytest.fixture
def sample_school(app):
    """テスト用学校データ"""
    with app.app_context():
        return School.query.filter_by(school_code='TEST001').first()

@pytest.fixture  
def sample_users(app):
    """テスト用ユーザーデータ"""
    with app.app_context():
        admin = User.query.filter_by(email='admin@test.com').first()
        teacher = User.query.filter_by(email='teacher@test.com').first()
        student = User.query.filter_by(email='student@test.com').first()
        return [admin, teacher, student]

@pytest.fixture
def sample_class(app, sample_users):
    """テスト用クラスデータ"""
    with app.app_context():
        teacher = sample_users[1]  # teacher
        test_class = Class(
            name='テストクラス',
            description='テスト用のクラスです',
            teacher_id=teacher.id
        )
        db.session.add(test_class)
        db.session.commit()
        return test_class

@pytest.fixture
def sample_inquiry_theme(app, sample_users, sample_class):
    """テスト用探究テーマデータ"""
    with app.app_context():
        student = sample_users[2]  # student
        theme = InquiryTheme(
            title='テスト探究テーマ',
            description='テスト用の探究テーマです',
            user_id=student.id,
            class_id=sample_class.id
        )
        db.session.add(theme)
        db.session.commit()
        return theme

@pytest.fixture
def sample_activity_log(app, sample_users, sample_inquiry_theme):
    """テスト用活動ログデータ"""
    with app.app_context():
        student = sample_users[2]  # student
        activity = ActivityLog(
            title='テスト活動',
            content='テスト用の活動内容です',
            user_id=student.id,
            inquiry_theme_id=sample_inquiry_theme.id
        )
        db.session.add(activity)
        db.session.commit()
        return activity

@pytest.fixture
def mock_openai_response():
    """OpenAI APIのモックレスポンス"""
    return {
        'choices': [{
            'message': {
                'content': 'テスト用AI応答'
            }
        }]
    }

@pytest.fixture
def upload_file(app):
    """テスト用アップロードファイル"""
    import io
    from werkzeug.datastructures import FileStorage
    
    # テスト用画像ファイル（1x1 PNG）
    test_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
    
    return FileStorage(
        stream=io.BytesIO(test_image_data),
        filename='test.png',
        content_type='image/png'
    )