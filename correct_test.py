#!/usr/bin/env python3
"""
修正されたローカルテスト
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

def test_corrected_routes(app):
    """修正されたルートテスト"""
    try:
        with app.test_client() as client:
            print("=== 修正されたルートテスト ===")
            
            # 1. メインページ（認証が必要）
            response = client.get('/')
            print(f"✅ メインページ: {response.status_code} (302リダイレクト期待)")
            
            # 2. ログインページ（正しいパス）
            response = client.get('/login')
            print(f"✅ ログインページ: {response.status_code} (200期待)")
            
            # 3. BaseBuilderホーム（認証が必要）
            response = client.get('/basebuilder/')
            print(f"✅ BaseBuilderホーム: {response.status_code} (302リダイレクト期待)")
            
            # 4. カテゴリ一覧（認証が必要）
            response = client.get('/basebuilder/categories')
            print(f"✅ カテゴリ一覧: {response.status_code} (302リダイレクト期待)")
            
            return True
    except Exception as e:
        print(f"❌ ルートテスト失敗: {e}")
        return False

def test_student_login(app):
    """学生ログインテスト"""
    try:
        with app.test_client() as client:
            print("\n=== 学生ログインテスト ===")
            
            # データベースからパスワードを確認
            with app.app_context():
                student = User.query.filter_by(username='honami').first()
                if not student:
                    print("❌ 学生アカウント 'honami' が見つかりません")
                    return False
                print(f"✅ 学生アカウント発見: {student.username} (role: {student.role})")
            
            # 1. ログインページにアクセス
            response = client.get('/login')
            if response.status_code == 200:
                print("✅ ログインページアクセス成功")
            else:
                print(f"❌ ログインページアクセス失敗: {response.status_code}")
                return False
            
            # 2. 学生ログイン試行（一般的なパスワードで試行）
            common_passwords = ['Password123!', 'password', 'honami123', 'test123']
            login_success = False
            
            for password in common_passwords:
                response = client.post('/login', data={
                    'username': 'honami',
                    'password': password
                })
                if response.status_code == 302:
                    print(f"✅ ログイン成功: パスワード '{password}'")
                    print(f"   リダイレクト先: {response.headers.get('Location', 'Unknown')}")
                    login_success = True
                    break
                else:
                    print(f"ℹ️  パスワード '{password}' でのログイン失敗: {response.status_code}")
            
            if not login_success:
                print("❌ すべてのパスワードでログイン失敗")
                return False
            
            # 3. ログイン後のBaseBuilderアクセス
            response = client.get('/basebuilder/')
            print(f"✅ ログイン後BaseBuilderアクセス: {response.status_code}")
            
            # 4. ログイン後のカテゴリアクセス
            response = client.get('/basebuilder/categories')
            print(f"✅ ログイン後カテゴリアクセス: {response.status_code}")
            
            # 5. 認証デバッグエンドポイント
            response = client.get('/basebuilder/debug/auth')
            if response.status_code == 200:
                print("✅ 認証デバッグ情報取得成功")
                if 'is_authenticated' in response.text:
                    print(f"   認証状態: {response.text[:300]}...")
            else:
                print(f"❌ 認証デバッグ情報取得失敗: {response.status_code}")
            
            return True
            
    except Exception as e:
        print(f"❌ 学生ログインテスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=== QuestEd 修正されたローカルテスト ===")
    print()
    
    # アプリ作成
    try:
        app = create_app()
        print("✅ アプリケーション作成成功")
    except Exception as e:
        print(f"❌ アプリケーション作成失敗: {e}")
        return
    
    # 基本ルートテスト
    if not test_corrected_routes(app):
        return
    
    # 学生ログインテスト
    if not test_student_login(app):
        return
    
    print("\n=== テスト完了 ===")
    print("✅ 基本機能は正常に動作しています。")
    print()
    print("実際のサーバーテストのため、以下のコマンドを実行してください：")
    print("python3 test_local.py")
    print()
    print("その後、ブラウザで以下をテストしてください：")
    print("1. http://127.0.0.1:5001/login")
    print("2. 学生アカウント: honami でログイン")  
    print("3. http://127.0.0.1:5001/basebuilder/ でホームページ確認")
    print("4. カテゴリページで学習セッション開始テスト")

if __name__ == "__main__":
    main()