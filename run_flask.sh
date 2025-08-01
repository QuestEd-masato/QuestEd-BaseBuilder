#!/bin/bash
# Flask起動スクリプト

echo "Starting QuestEd Flask Application..."
echo "======================================="

# 仮想環境をアクティベート
source venv/bin/activate

# 環境変数を設定
export FLASK_APP=app.py
export FLASK_ENV=development
export FLASK_DEBUG=1

# IPアドレス情報を表示
echo "Network Information:"
echo "WSL2 IP: $(hostname -I | awk '{print $1}')"
echo ""

# Flaskを起動
echo "Starting Flask on port 8092..."
echo "Access URLs:"
echo "  - From WSL2: http://localhost:8092"
echo "  - From Windows: Use PowerShell port forwarding"
echo ""
echo "To forward port from Windows PowerShell (Admin):"
echo "netsh interface portproxy add v4tov4 listenport=8092 listenaddress=0.0.0.0 connectport=8092 connectaddress=$(hostname -I | awk '{print $1}')"
echo ""

# Flaskを起動（デバッグ出力付き）
python -m flask run --host=0.0.0.0 --port=8092 --debugger --reload