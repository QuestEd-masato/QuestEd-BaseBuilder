#!/usr/bin/env python3
"""
シンプルなローカルサーバー起動
"""
import os
import sys

# 環境変数設定
os.environ['SECRET_KEY'] = 'dev-secret-key-123'
os.environ['DB_USERNAME'] = 'QuestEd'
os.environ['DB_PASSWORD'] = 'QuestEd-03012025MySQL'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_NAME'] = 'quested'
os.environ['FLASK_DEBUG'] = '0'  # デバッグ無効

print("🔧 環境変数設定完了")

try:
    print("📦 アプリケーション読み込み中...")
    from app import create_app
    
    print("🚀 Flask アプリ作成中...")
    app = create_app()
    
    print("=" * 50)
    print("✅ QuestEd ローカルサーバー起動")
    print("=" * 50)
    print(f"📍 URL: http://localhost:8000")
    print(f"📍 代替: http://127.0.0.1:8000")
    print()
    print("🔍 テスト内容:")
    print("• 生徒アカウント: honami")
    print("• 教師アカウント: yoshimi") 
    print("• BaseBuilder機能の修正確認")
    print()
    print("⏹️  停止: Ctrl+C")
    print("=" * 50)
    
    # シンプルな設定でサーバー起動
    app.run(
        host='0.0.0.0',  # 全てのインターフェースでリッスン
        port=8000,       # ポート8000を使用
        debug=False,     # デバッグ無効
        threaded=True,   # スレッド有効
        use_reloader=False  # リローダー無効
    )
    
except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    print("必要なモジュールがインストールされていない可能性があります")
    sys.exit(1)
except Exception as e:
    print(f"❌ エラー: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)