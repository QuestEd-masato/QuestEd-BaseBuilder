#!/usr/bin/env python3
"""
ローカル開発用の起動スクリプト
"""
import os
import sys
from app import create_app

# 環境変数設定
os.environ['FLASK_ENV'] = 'development'
os.environ['FLASK_DEBUG'] = '1'

def main():
    """アプリケーションを起動"""
    try:
        print("🚀 QuestEd ローカル開発サーバーを起動中...")
        print("=" * 50)
        
        # アプリケーション作成
        app = create_app()
        
        print("✅ アプリケーションの初期化完了")
        print("📍 アクセスURL: http://localhost:5001")
        print("🛑 停止するには Ctrl+C を押してください")
        print("=" * 50)
        
        # サーバー起動
        app.run(
            host='127.0.0.1',  # ローカルホストのみ
            port=5001,         # ポート5001を使用
            debug=True,        # デバッグモード
            use_reloader=False # リローダーを無効化（プロセス重複回避）
        )
        
    except KeyboardInterrupt:
        print("\n🛑 サーバーを停止しました")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()