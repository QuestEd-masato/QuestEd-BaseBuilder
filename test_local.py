#!/usr/bin/env python3
"""
ローカルテスト用起動スクリプト
"""
import os
import sys

# 環境変数の設定
required_env_vars = {
    'SECRET_KEY': 'dev-secret-key-123',
    'DB_USERNAME': 'QuestEd', 
    'DB_PASSWORD': 'QuestEd-03012025MySQL',
    'DB_HOST': 'localhost',
    'DB_NAME': 'quested',
    'FLASK_DEBUG': '1'
}

for key, value in required_env_vars.items():
    if key not in os.environ:
        os.environ[key] = value

try:
    from app import create_app
    
    print("=== QuestEd ローカルテスト環境 ===")
    print("ポート: 5001")
    print("アクセスURL: http://127.0.0.1:5001")
    print()
    print("テスト項目:")
    print("1. ログイン: http://127.0.0.1:5001/auth/login")
    print("2. BaseBuilderホーム: http://127.0.0.1:5001/basebuilder/")
    print("3. 学習カテゴリ: http://127.0.0.1:5001/basebuilder/categories")
    print("4. 認証デバッグ: http://127.0.0.1:5001/basebuilder/debug/auth")
    print()
    print("テストアカウント:")
    print("- 学生: honami")
    print("- 教師: yoshimi")
    print()
    print("Ctrl+C で停止")
    print("=" * 40)
    
    app = create_app()
    app.run(host='127.0.0.1', port=5001, debug=True, use_reloader=False)
    
except Exception as e:
    import traceback
    print(f"❌ アプリケーション起動エラー: {e}")
    print(f"詳細: {traceback.format_exc()}")
    sys.exit(1)