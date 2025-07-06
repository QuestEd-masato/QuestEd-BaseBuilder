#!/usr/bin/env python3
"""
ローカルテスト実行スクリプト
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:5001"

def test_endpoint(url, description, expected_status=200):
    """エンドポイントのテスト"""
    try:
        response = requests.get(url, timeout=5)
        status = "✅" if response.status_code == expected_status else "❌"
        print(f"{status} {description}")
        print(f"   URL: {url}")
        print(f"   Status: {response.status_code}")
        if response.status_code != expected_status:
            print(f"   Error: Expected {expected_status}, got {response.status_code}")
        print()
        return response.status_code == expected_status
    except Exception as e:
        print(f"❌ {description}")
        print(f"   URL: {url}")
        print(f"   Error: {str(e)}")
        print()
        return False

def test_login_flow():
    """ログインフローのテスト"""
    print("=== ログインフローテスト ===")
    
    # セッションを維持
    session = requests.Session()
    
    try:
        # 1. ログインページのアクセス
        login_url = f"{BASE_URL}/auth/login"
        response = session.get(login_url)
        print(f"✅ ログインページアクセス: {response.status_code}")
        
        # 2. 学生ログイン試行
        login_data = {
            'username': 'honami',
            'password': 'Password123!'  # デフォルトパスワードを推測
        }
        
        response = session.post(login_url, data=login_data)
        print(f"ℹ️  学生ログイン試行: {response.status_code}")
        if response.status_code == 302:
            print(f"   リダイレクト先: {response.headers.get('Location', 'Unknown')}")
        
        # 3. 認証デバッグの確認
        debug_url = f"{BASE_URL}/basebuilder/debug/auth"
        response = session.get(debug_url)
        if response.status_code == 200:
            print(f"✅ 認証状態確認: {response.status_code}")
            print(f"   認証情報: {response.text[:200]}...")
        else:
            print(f"❌ 認証状態確認失敗: {response.status_code}")
        
    except Exception as e:
        print(f"❌ ログインフローエラー: {str(e)}")
    
    print()

def main():
    print("=== QuestEd ローカルテスト実行 ===")
    print("対象サーバー: http://127.0.0.1:5001")
    print()
    
    # 基本的なエンドポイントテスト
    print("=== 基本エンドポイントテスト ===")
    
    tests = [
        (f"{BASE_URL}/", "メインページ", 302),  # ログインが必要でリダイレクト
        (f"{BASE_URL}/auth/login", "ログインページ", 200),
        (f"{BASE_URL}/basebuilder/", "BaseBuilderホーム", 302),  # ログインが必要
        (f"{BASE_URL}/basebuilder/categories", "カテゴリ一覧", 302),  # ログインが必要
        (f"{BASE_URL}/basebuilder/debug/auth", "認証デバッグ", 200),  # デバッグモードで利用可能
    ]
    
    passed = 0
    total = len(tests)
    
    for url, description, expected_status in tests:
        if test_endpoint(url, description, expected_status):
            passed += 1
    
    print(f"基本テスト結果: {passed}/{total} 成功")
    print()
    
    # ログインフローテスト
    test_login_flow()
    
    print("=== テスト完了 ===")
    print()
    print("手動テスト項目:")
    print("1. ブラウザで http://127.0.0.1:5001 にアクセス")
    print("2. 学生アカウント (honami) でログイン")
    print("3. BaseBuilderホーム (/basebuilder/) の表示確認")
    print("4. カテゴリ一覧での学習セッション開始テスト")
    print("5. 教師アカウント (yoshimi) でのログインテスト")

if __name__ == "__main__":
    main()