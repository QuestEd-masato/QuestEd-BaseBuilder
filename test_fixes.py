#!/usr/bin/env python3
"""
修正内容のローカルテスト用起動スクリプト
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
    
    print("=" * 60)
    print("🎯 QuestEd 修正内容ローカルテスト環境")
    print("=" * 60)
    print()
    print("📍 アクセスURL: http://127.0.0.1:5002")
    print()
    print("🔍 テスト項目:")
    print()
    print("【生徒アカウント】")
    print("1. ログイン: http://127.0.0.1:5002/login")
    print("   - ユーザー名: honami")
    print("   - パスワード: [確認が必要]")
    print()
    print("2. 生徒ダッシュボード:")
    print("   - BaseBuilder完璧単語数の表示確認")
    print("   - 「テーマ」ボタンのリンク動作確認")
    print()
    print("3. BaseBuilderホーム: http://127.0.0.1:5002/basebuilder/")
    print("   - 「カテゴリから学習」ボタン動作確認") 
    print("   - 「ランダム学習」ボタン動作確認")
    print()
    print("4. 学習導線:")
    print("   - カテゴリ選択 → 学習セッション開始 → 問題解答")
    print()
    print("【教師アカウント】")
    print("1. ログイン:")
    print("   - ユーザー名: yoshimi")
    print("   - パスワード: [確認が必要]")
    print()
    print("2. BaseBuilderホーム: http://127.0.0.1:5002/basebuilder/")
    print("   - 問題作成リンク")
    print("   - カテゴリ作成リンク")
    print("   - テキスト作成リンク")
    print("   - 分析画面リンク")
    print()
    print("3. 管理機能:")
    print("   - 問題管理: http://127.0.0.1:5002/basebuilder/problems")
    print("   - カテゴリ管理: http://127.0.0.1:5002/basebuilder/categories")
    print("   - テキスト管理: http://127.0.0.1:5002/basebuilder/text_sets")
    print()
    print("=" * 60)
    print("💡 Ctrl+C で停止")
    print("=" * 60)
    
    app = create_app()
    app.run(host='127.0.0.1', port=5002, debug=True, use_reloader=False)
    
except Exception as e:
    import traceback
    print(f"❌ アプリケーション起動エラー: {e}")
    print(f"詳細: {traceback.format_exc()}")
    sys.exit(1)