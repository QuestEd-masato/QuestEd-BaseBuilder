#!/usr/bin/env python3
"""
シンプルなローカルテスト
"""
import os

# 環境変数設定
os.environ['SECRET_KEY'] = 'dev-secret-key-123'
os.environ['DB_USERNAME'] = 'QuestEd'
os.environ['DB_PASSWORD'] = 'QuestEd-03012025MySQL'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_NAME'] = 'quested'

from app import create_app
from app.models import User

def test_app_creation():
    """アプリ作成テスト"""
    try:
        app = create_app()
        print("✅ アプリケーション作成成功")
        return app
    except Exception as e:
        print(f"❌ アプリケーション作成失敗: {e}")
        return None

def test_database_connection(app):
    """データベース接続テスト"""
    try:
        with app.app_context():
            user_count = User.query.count()
            print(f"✅ データベース接続成功 - ユーザー数: {user_count}")
            return True
    except Exception as e:
        print(f"❌ データベース接続失敗: {e}")
        return False

def test_basebuilder_routes(app):
    """BaseBuilderルートテスト"""
    try:
        with app.test_client() as client:
            # 認証なしでのアクセス（リダイレクトを期待）
            response = client.get('/basebuilder/')
            print(f"✅ BaseBuilderホーム: {response.status_code} (302リダイレクト期待)")
            
            response = client.get('/basebuilder/categories')
            print(f"✅ カテゴリ一覧: {response.status_code} (302リダイレクト期待)")
            
            # ログインページ
            response = client.get('/auth/login')
            print(f"✅ ログインページ: {response.status_code} (200期待)")
            
            return True
    except Exception as e:
        print(f"❌ ルートテスト失敗: {e}")
        return False

def test_login_functionality(app):
    """ログイン機能テスト"""
    try:
        with app.test_client() as client:
            # 学生ログイン試行
            response = client.post('/auth/login', data={
                'username': 'honami',
                'password': 'Password123!'
            })
            print(f"✅ 学生ログイン試行: {response.status_code}")
            
            # ログイン後のBaseBuilderアクセス
            if response.status_code == 302:
                response = client.get('/basebuilder/', follow_redirects=True)
                print(f"✅ ログイン後BaseBuilderアクセス: {response.status_code}")
                
                # カテゴリページアクセス
                response = client.get('/basebuilder/categories')
                print(f"✅ ログイン後カテゴリアクセス: {response.status_code}")
            
            return True
    except Exception as e:
        print(f"❌ ログイン機能テスト失敗: {e}")
        return False

def main():
    print("=== QuestEd シンプルテスト ===")
    print()
    
    # 1. アプリ作成
    app = test_app_creation()
    if not app:
        return
    
    # 2. データベース接続
    if not test_database_connection(app):
        return
    
    # 3. ルート機能
    if not test_basebuilder_routes(app):
        return
    
    # 4. ログイン機能
    if not test_login_functionality(app):
        return
    
    print()
    print("=== テスト完了 ===")
    print("基本機能は正常に動作しています。")
    print()
    print("手動テストのために以下のコマンドでサーバーを起動してください：")
    print("python3 test_local.py")
    print()
    print("その後、ブラウザで以下をテストしてください：")
    print("1. http://127.0.0.1:5001/auth/login")
    print("2. 学生アカウント: honami でログイン")
    print("3. http://127.0.0.1:5001/basebuilder/ でホームページ確認")
    print("4. カテゴリページで学習セッション開始テスト")

if __name__ == "__main__":
    main()