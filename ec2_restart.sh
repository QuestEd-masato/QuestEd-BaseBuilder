#!/bin/bash
echo "=== QuestEd EC2 完全再起動スクリプト ==="

# 1. 現在のプロセスを停止
echo "1. 現在のプロセスを停止中..."
sudo pkill -f "python.*questEd" 2>/dev/null || echo "   プロセスが見つかりません"
sudo pkill -f "gunicorn.*questEd" 2>/dev/null || echo "   Gunicornプロセスが見つかりません"

# systemdサービスが存在する場合
if systemctl list-units --type=service | grep -q questEd; then
    echo "   systemdサービスを停止中..."
    sudo systemctl stop questEd
fi

sleep 3

# 2. Pythonキャッシュクリア
echo "2. Pythonキャッシュをクリア中..."
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# 3. Git状態確認
echo "3. Git状態確認..."
git status --porcelain
echo "最新コミット: $(git log --oneline -1)"

# 4. 必要なファイルの存在確認
echo "4. 重要ファイルの確認..."
files=(
    "templates/basebuilder/problem_session.html"
    "templates/basebuilder/categories_student.html"
    "templates/basebuilder/categories_simple.html"
    "basebuilder/routes_modules/sessions.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file - 見つかりません"
    fi
done

# 5. データベース修正スクリプト実行
echo "5. データベース修正スクリプト実行..."
python3 ec2_fix.py

# 6. アプリケーション再起動
echo "6. アプリケーション再起動..."

# systemdサービスがある場合
if systemctl list-units --type=service | grep -q questEd; then
    echo "   systemdサービスで再起動中..."
    sudo systemctl start questEd
    sleep 5
    sudo systemctl status questEd --no-pager
else
    # 手動起動の場合
    echo "   手動起動モード..."
    echo "   以下のコマンドでアプリケーションを起動してください："
    echo "   export SECRET_KEY='your-secret-key'"
    echo "   export DB_USERNAME='QuestEd'"
    echo "   export DB_PASSWORD='QuestEd-03012025MySQL'"
    echo "   export DB_HOST='localhost'"
    echo "   export DB_NAME='quested'"
    echo "   python3 run.py"
fi

# 7. 起動確認
echo "7. 起動確認..."
sleep 5
if curl -s -I http://localhost:5000 | grep -q "200\|302"; then
    echo "   ✅ アプリケーションが起動しています"
else
    echo "   ❌ アプリケーションの起動に失敗した可能性があります"
    echo "   ログを確認してください："
    echo "   tail -50 app.log"
    echo "   journalctl -u questEd -f"
fi

echo "=== 完了 ==="