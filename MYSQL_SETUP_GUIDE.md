# QuestEd MySQL Development Environment Setup Guide

## 📋 前提条件

このガイドはUbuntuでDocker Composeを使用したMySQL環境構築を説明します。

### 必要なソフトウェア

1. **Docker** (20.10以上)
2. **Docker Compose** (2.0以上)
3. **Python** (3.8以上)

## 🔧 1. Docker環境の準備

### Dockerのインストール（未インストールの場合）

```bash
# システム更新
sudo apt update

# 必要なパッケージのインストール
sudo apt install apt-transport-https ca-certificates curl gnupg lsb-release

# Docker公式GPGキーの追加
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Dockerリポジトリの追加
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Dockerのインストール
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 現在のユーザーをdockerグループに追加
sudo usermod -aG docker $USER

# 再ログインまたは以下を実行
newgrp docker
```

### インストール確認

```bash
docker --version
docker compose version
```

## 🚀 2. MySQL環境の起動

### 手順1: 環境設定ファイルの準備

```bash
# プロジェクトディレクトリに移動
cd /home/masat/claude-projects/QuestEd

# 開発用環境設定をコピー
cp .env.dev .env

# 必要に応じて設定を編集
nano .env
```

### 手順2: MySQL Dockerコンテナの起動

```bash
# MySQLコンテナを起動（バックグラウンド実行）
docker compose -f docker-compose.dev.yml up -d

# 起動状況確認
docker ps

# ログ確認（初回起動時は1-2分かかります）
docker logs quested_mysql_dev -f
```

### 手順3: MySQL接続確認

```bash
# コンテナ内でMySQLクライアント接続
docker exec -it quested_mysql_dev mysql -u quested_user -p quested_dev

# パスワード: quested_pass_2025
```

MySQLプロンプトで以下を実行して接続確認：

```sql
-- データベース確認
SHOW DATABASES;

-- テーブル確認（初回は空）
SHOW TABLES;

-- 接続終了
EXIT;
```

## 🐍 3. Python環境の設定

### 手順1: 仮想環境の作成（推奨）

```bash
# プロジェクトディレクトリで仮想環境作成
python3 -m venv venv

# 仮想環境を有効化
source venv/bin/activate

# pip更新
pip install --upgrade pip
```

### 手順2: 依存関係のインストール

```bash
# 必要なPythonライブラリのインストール
pip install flask flask-sqlalchemy flask-migrate pymysql cryptography python-dotenv

# requirements.txtが存在する場合
pip install -r requirements.txt
```

## 🗄️ 4. データベースの初期化

### 手順1: Flask アプリケーションの設定

```bash
# Flask環境変数の設定
export FLASK_APP=app.py
export FLASK_ENV=development

# 環境設定読み込み確認
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('DB_HOST:', os.getenv('DB_HOST'))"
```

### 手順2: データベースマイグレーション

```bash
# マイグレーション初期化（初回のみ）
flask db init

# マイグレーションファイル作成
flask db migrate -m "Initial migration"

# データベースにマイグレーション適用
flask db upgrade
```

## 🧪 5. BaseBuilder機能のテスト

### 手順1: 基本構造確認

```bash
# BaseBuilderエンドポイント構造確認スクリプト実行
python scripts/check_basebuilder_endpoints.py
```

### 手順2: アプリケーション起動

```bash
# 開発サーバー起動
python app.py

# または
flask run
```

### 手順3: ブラウザでアクセス

1. **メインページ**: http://localhost:5000
2. **BaseBuilderモジュール**: http://localhost:5000/basebuilder/
3. **管理画面**: http://localhost:5000/admin（管理者権限必要）

## 🔧 6. トラブルシューティング

### よくある問題と解決法

#### Docker関連

```bash
# Docker権限エラーの場合
sudo chmod 666 /var/run/docker.sock

# コンテナ再起動
docker compose -f docker-compose.dev.yml restart

# コンテナ完全リセット
docker compose -f docker-compose.dev.yml down
docker volume rm quested_mysql_data
docker compose -f docker-compose.dev.yml up -d
```

#### MySQL接続エラー

```bash
# ポート使用状況確認
sudo netstat -tulpn | grep 3306

# MySQLログ確認
docker logs quested_mysql_dev

# データベース接続テスト
python -c "
import pymysql
from dotenv import load_dotenv
import os
load_dotenv()

try:
    conn = pymysql.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT')),
        user=os.getenv('DB_USERNAME'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    print('✅ Database connection successful')
    conn.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
"
```

#### Flask アプリケーション起動エラー

```bash
# 環境変数確認
env | grep -E "(FLASK|DB_)"

# Pythonパス確認
python -c "import sys; print('\n'.join(sys.path))"

# 必要モジュール確認
python -c "import flask, flask_sqlalchemy, pymysql; print('All modules imported successfully')"
```

## 📊 7. 開発環境の状態確認

### システム状態チェックスクリプト

```bash
#!/bin/bash
echo "🔍 QuestEd Development Environment Status"
echo "========================================"

# Docker状態
echo "📦 Docker Status:"
docker ps --filter "name=quested_mysql_dev" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# データベース接続
echo -e "\n🗄️ Database Connection:"
python -c "
import pymysql
from dotenv import load_dotenv
import os
load_dotenv()

try:
    conn = pymysql.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT')),
        user=os.getenv('DB_USERNAME'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    print('✅ Database: Connected')
    
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s', (os.getenv('DB_NAME'),))
    table_count = cursor.fetchone()[0]
    print(f'📊 Tables: {table_count} found')
    
    conn.close()
except Exception as e:
    print(f'❌ Database: {e}')
"

# Flask環境
echo -e "\n🐍 Flask Environment:"
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

print(f'FLASK_ENV: {os.getenv(\"FLASK_ENV\", \"Not set\")}')
print(f'FLASK_DEBUG: {os.getenv(\"FLASK_DEBUG\", \"Not set\")}')
print(f'DATABASE_URL: {os.getenv(\"DATABASE_URL\", \"Not set\")[:50]}...')
"

echo -e "\n✅ Environment check completed"
```

## 🎯 8. 次のステップ

環境構築完了後は以下を実行してください：

1. **BaseBuilder機能テスト**:
   ```bash
   python scripts/check_basebuilder_endpoints.py
   ```

2. **実際のデータでテスト**:
   - 管理者アカウントでログイン
   - BaseBuilderモジュールにアクセス
   - 各機能の動作確認

3. **開発作業開始**:
   - 「安全な改善提案」(CLAUDE.md) のPhase Aから実装開始
   - 段階的な品質向上作業

## 📝 設定ファイル一覧

- **docker-compose.dev.yml**: MySQL Docker設定
- **.env.dev**: 開発環境設定テンプレート
- **.env**: 実際の環境設定（.env.devからコピー）
- **CLAUDE.md**: 開発ガイドライン

---

これで QuestEd の MySQL 開発環境が構築できます。問題が発生した場合は、トラブルシューティングセクションを参照してください。