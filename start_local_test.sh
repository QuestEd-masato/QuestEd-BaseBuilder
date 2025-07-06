#!/bin/bash

echo "=== QuestEd ローカルテストサーバー起動 ==="
echo

# 既存プロセスを停止
echo "1. 既存プロセスの停止..."
pkill -f "python.*test_fixes.py" 2>/dev/null || echo "   実行中のプロセスなし"
pkill -f "python.*run.py" 2>/dev/null || echo "   run.pyプロセスなし"
sleep 2

# 環境変数設定
echo "2. 環境変数設定..."
export SECRET_KEY='dev-secret-key-123'
export DB_USERNAME='QuestEd'
export DB_PASSWORD='QuestEd-03012025MySQL'
export DB_HOST='localhost'
export DB_NAME='quested'
export FLASK_DEBUG='1'

# ポート確認
echo "3. ポート確認..."
if ss -tulpn | grep -q ":5002"; then
    echo "   ⚠️ ポート5002が使用中。ポート5003を使用します"
    PORT=5003
else
    echo "   ✅ ポート5002が利用可能"
    PORT=5002
fi

echo "4. サーバー起動中..."
echo "   URL: http://127.0.0.1:$PORT"
echo "   停止: Ctrl+C"
echo

# サーバー起動
python3 -c "
import os
os.environ['SECRET_KEY'] = 'dev-secret-key-123'
os.environ['DB_USERNAME'] = 'QuestEd'
os.environ['DB_PASSWORD'] = 'QuestEd-03012025MySQL'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_NAME'] = 'quested'
os.environ['FLASK_DEBUG'] = '1'

from app import create_app

print('=' * 60)
print('🎯 QuestEd ローカルテスト環境')
print('=' * 60)
print()
print(f'📍 URL: http://127.0.0.1:$PORT')
print()
print('🔍 テスト項目:')
print()
print('【生徒アカウント - honami】')
print('1. ログイン → ダッシュボード')
print('2. BaseBuilder完璧単語数の表示')
print('3. テーマボタンのリンク確認')
print('4. BaseBuilderホーム → カテゴリ学習')
print()
print('【教師アカウント - yoshimi】')
print('1. ログイン → 管理機能')
print('2. 問題作成・管理機能')
print('3. テキスト管理機能')
print('4. 各種リンクの動作確認')
print()
print('=' * 60)

app = create_app()
app.run(host='0.0.0.0', port=$PORT, debug=False)
"