#!/usr/bin/env python3
"""
OPENAI_API_KEY 設定確認スクリプト
QuestEd Ver.2.0用
"""

import os
import sys
from pathlib import Path

def check_api_key():
    """APIキー設定状況を確認"""
    print("🔍 OPENAI_API_KEY 設定確認")
    print("=" * 50)
    
    # 1. 環境変数確認
    env_key = os.getenv('OPENAI_API_KEY')
    if env_key:
        print(f"✅ 環境変数: 設定済み (sk-...{env_key[-10:]})")
    else:
        print("❌ 環境変数: 未設定")
    
    # 2. .envファイル確認
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r') as f:
            content = f.read()
            
        # APIキー行を検索
        lines = content.split('\n')
        api_key_lines = [line for line in lines if 'OPENAI_API_KEY=' in line and not line.strip().startswith('#')]
        
        if api_key_lines:
            key_line = api_key_lines[0]
            key_value = key_line.split('=', 1)[1].strip()
            if key_value and key_value != 'your_openai_api_key_here':
                print(f"✅ .envファイル: 設定済み (sk-...{key_value[-10:]})")
            else:
                print("❌ .envファイル: 未設定（プレースホルダー値）")
        else:
            print("❌ .envファイル: APIキー行が見つからない")
    else:
        print("❌ .envファイル: ファイルが存在しない")
    
    # 3. 設定確認（Flaskアプリケーション）
    try:
        # QuestEd設定を読み込み
        sys.path.append('.')
        from config import Config
        
        config = Config()
        if hasattr(config, 'OPENAI_API_KEY') and config.OPENAI_API_KEY:
            print(f"✅ Flask設定: 認識済み")
        else:
            print("❌ Flask設定: 未認識")
            
    except Exception as e:
        print(f"❌ Flask設定: エラー ({str(e)})")
    
    print("\n" + "=" * 50)
    
    # 総合判定
    if env_key or (env_file.exists() and api_key_lines):
        print("🎉 設定完了！QuestEd Ver.2.0でAI機能が利用可能です")
        print("\n次のステップ:")
        print("1. source venv/bin/activate")
        print("2. python run.py")
        print("3. http://localhost:5000 でアクセス")
    else:
        print("⚠️  APIキーが設定されていません")
        print("\n設定方法:")
        print("1. https://platform.openai.com/api-keys でAPIキーを取得")
        print("2. .envファイルの23行目を編集:")
        print("   OPENAI_API_KEY=sk-your-actual-api-key")
        print("3. このスクリプトを再実行して確認")

if __name__ == '__main__':
    check_api_key()