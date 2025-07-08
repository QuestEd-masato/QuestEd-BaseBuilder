#!/usr/bin/env python3
"""
シンプルな起動スクリプト
"""
from app import create_app

if __name__ == '__main__':
    app = create_app()
    print("\n" + "="*60)
    print("🚀 QuestEd サーバー起動中...")
    print("📍 ローカルアクセス: http://127.0.0.1:8000")
    print("📍 ネットワークアクセス: http://0.0.0.0:8000")
    print("🛑 停止: Ctrl+C")
    print("="*60 + "\n")
    
    app.run(
        host='0.0.0.0',
        port=8000,
        debug=False,
        use_reloader=False,
        threaded=True
    )