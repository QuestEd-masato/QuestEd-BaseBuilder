# QuestEd インストールガイド

<div align="center">
  <h3>🛠️ QuestEd開発環境構築完全マニュアル</h3>
  <p>
    <a href="#前提条件">前提条件</a> •
    <a href="#基本インストール">基本インストール</a> •
    <a href="#データベース設定">データベース</a> •
    <a href="#設定">設定</a> •
    <a href="#トラブルシューティング">トラブルシューティング</a>
  </p>
</div>

---

## 📋 前提条件

### システム要件

| コンポーネント | 最小要件 | 推奨要件 |
|---------------|----------|----------|
| **OS** | Linux/macOS/Windows 10+ | Ubuntu 20.04 LTS / macOS Monterey+ |
| **Python** | 3.8+ | 3.11+ |
| **MySQL** | 8.0+ | 8.0.35+ |
| **メモリ** | 2GB | 4GB+ |
| **ディスク容量** | 1GB | 5GB+ |
| **ネットワーク** | インターネット接続必須 | 高速ブロードバンド |

### 必要なソフトウェア

#### 1. Python のインストール

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-pip python3.11-venv python3.11-dev
```

**CentOS/RHEL/Fedora:**
```bash
sudo dnf install python3.11 python3.11-pip python3.11-devel
# または sudo yum install python3.11 python3.11-pip python3.11-devel
```

**macOS (Homebrew):**
```bash
brew install python@3.11
```

**Windows:**
1. [Python公式サイト](https://www.python.org/downloads/)からインストーラーをダウンロード
2. インストール時に「Add to PATH」をチェック

#### 2. MySQL のインストール

**Ubuntu/Debian:**
```bash
sudo apt install mysql-server mysql-client
sudo mysql_secure_installation
```

**CentOS/RHEL/Fedora:**
```bash
sudo dnf install mysql-server mysql-client
sudo systemctl enable mysqld
sudo systemctl start mysqld
sudo mysql_secure_installation
```

**macOS (Homebrew):**
```bash
brew install mysql
brew services start mysql
mysql_secure_installation
```

**Windows:**
1. [MySQL公式サイト](https://dev.mysql.com/downloads/installer/)からインストーラーをダウンロード
2. MySQL Server 8.0以上をインストール

#### 3. Git のインストール

**Ubuntu/Debian:**
```bash
sudo apt install git
```

**macOS:**
```bash
brew install git
```

**Windows:**
[Git for Windows](https://gitforwindows.org/)をダウンロードしてインストール

---

## 🚀 基本インストール

### Step 1: プロジェクトのクローン

```bash
# HTTPSでクローン（推奨）
git clone https://github.com/yourusername/QuestEd.git
cd QuestEd

# SSHでクローン（SSH鍵設定済みの場合）
git clone git@github.com:yourusername/QuestEd.git
cd QuestEd
```

### Step 2: 仮想環境の作成

```bash
# 仮想環境を作成
python3 -m venv venv

# 仮想環境を有効化
# Linux/macOS:
source venv/bin/activate

# Windows (PowerShell):
venv\Scripts\Activate.ps1

# Windows (Command Prompt):
venv\Scripts\activate.bat
```

> **注意**: 仮想環境が有効化されると、プロンプトの前に `(venv)` が表示されます。

### Step 3: 依存関係のインストール

```bash
# Pythonパッケージのインストール
pip install --upgrade pip
pip install -r requirements.txt

# 開発環境用の追加パッケージ（オプション）
pip install -r requirements-dev.txt  # 存在する場合
```

---

## 🗄️ データベース設定

### Step 1: MySQLの設定確認

```bash
# MySQLサービスの状態確認
sudo systemctl status mysql  # Linux
brew services list | grep mysql  # macOS

# MySQLへの接続テスト
mysql -u root -p
```

### Step 2: データベースとユーザーの作成

MySQLにrootでログインし、以下のSQLを実行：

```sql
-- データベースの作成
CREATE DATABASE quested 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- 専用ユーザーの作成
CREATE USER 'quested_user'@'localhost' 
IDENTIFIED BY 'secure_password_here';

-- 権限の付与
GRANT ALL PRIVILEGES ON quested.* 
TO 'quested_user'@'localhost';

-- 権限の反映
FLUSH PRIVILEGES;

-- 作成確認
SHOW DATABASES;
SELECT User, Host FROM mysql.user WHERE User = 'quested_user';

EXIT;
```

### Step 3: データベース接続の確認

```bash
# 作成したユーザーでの接続テスト
mysql -u quested_user -p quested
```

---

## ⚙️ 環境設定

### Step 1: 環境変数ファイルの作成

```bash
# .env.example を .env にコピー
cp .env.example .env

# エディタで.envを編集
nano .env  # または vim .env、code .env
```

### Step 2: 必須設定項目の編集

`.env`ファイルで以下を設定：

```bash
# データベース設定
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_NAME=quested
DATABASE_USER=quested_user
DATABASE_PASSWORD=secure_password_here

# Flask設定
SECRET_KEY=your-very-long-random-secret-key-generate-this
FLASK_ENV=development
DEBUG=True

# OpenAI API設定（後で設定可能）
OPENAI_API_KEY=your-openai-api-key-here

# MFA暗号化キー
MFA_ENCRYPTION_KEY=generate-this-key-using-python-command-below
```

### Step 3: セキュリティキーの生成

```bash
# Flaskのシークレットキーを生成
python -c "import secrets; print(secrets.token_urlsafe(32))"

# MFA暗号化キーを生成
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

生成された値を`.env`ファイルにコピーしてください。

---

## 🏗️ アプリケーションの初期化

### Step 1: データベースマイグレーション

```bash
# マイグレーションリポジトリの初期化（初回のみ）
flask db init  # 既にmigrationsフォルダがある場合は不要

# マイグレーションファイルの生成
flask db migrate -m "Initial migration"

# マイグレーションの適用
flask db upgrade
```

### Step 2: 初期データの投入（オプション）

```bash
# 管理者ユーザーの作成スクリプトがある場合
python scripts/create_admin.py

# サンプルデータの投入（開発環境）
python scripts/seed_data.py  # ファイルが存在する場合
```

### Step 3: アプリケーションの起動

```bash
# 開発サーバーの起動
flask run

# または
python run.py

# カスタムポートで起動
flask run --port 8080 --host 0.0.0.0
```

成功すると以下のようなメッセージが表示されます：
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

ブラウザで `http://localhost:5000` にアクセスしてQuestEdにアクセスできます。

---

## 🌐 外部サービス設定

### OpenAI API設定

1. [OpenAI](https://platform.openai.com/)でアカウントを作成
2. API Keyを生成
3. `.env`ファイルの`OPENAI_API_KEY`に設定

### Gmail SMTP設定（メール送信用）

1. Gmailで「アプリパスワード」を生成
2. `.env`ファイルで以下を設定：

```bash
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-16-character-app-password
MAIL_DEFAULT_SENDER=noreply@yourdomain.com
```

---

## 🧪 インストール確認

### 基本動作テスト

```bash
# システム動作確認
python -c "
import app
from app.models import db, User
print('✅ アプリケーション読み込み成功')
print('✅ モデル読み込み成功')
"

# データベース接続確認
flask shell
>>> from app.models import db
>>> db.engine.execute('SELECT 1').scalar()
1
>>> exit()
```

### ユニットテストの実行

```bash
# テスト環境の準備
export FLASK_ENV=testing

# 全テストの実行
python -m pytest

# カバレッジレポート付き
python -m pytest --cov=app --cov-report=html
```

---

## 🔧 トラブルシューティング

### よくある問題と解決策

#### 1. MySQL接続エラー

**エラー**: `Access denied for user 'quested_user'@'localhost'`

**解決策**:
```bash
# MySQLにrootでログイン
mysql -u root -p

# ユーザー権限の再確認
SHOW GRANTS FOR 'quested_user'@'localhost';

# 権限の再付与
GRANT ALL PRIVILEGES ON quested.* TO 'quested_user'@'localhost';
FLUSH PRIVILEGES;
```

#### 2. Pythonパッケージインストールエラー

**エラー**: `pip install` が失敗する

**解決策**:
```bash
# pipのアップグレード
pip install --upgrade pip setuptools wheel

# キャッシュクリア
pip cache purge

# 個別インストール
pip install -r requirements.txt --no-cache-dir
```

#### 3. ポート5000が使用中

**エラー**: `Address already in use`

**解決策**:
```bash
# 使用中のプロセスを確認
lsof -i :5000

# プロセスを終了
kill -9 <PID>

# または異なるポートで起動
flask run --port 8080
```

#### 4. MFA関連エラー

**エラー**: `cryptography` モジュール関連エラー

**解決策**:
```bash
# 必要な開発パッケージをインストール
sudo apt install build-essential libffi-dev libssl-dev  # Ubuntu
brew install libffi openssl  # macOS

# cryptographyを再インストール
pip uninstall cryptography
pip install cryptography
```

### ログの確認

```bash
# アプリケーションログの確認
tail -f logs/quested.log

# デバッグモードでの起動
export FLASK_ENV=development
export FLASK_DEBUG=1
flask run
```

---

## 🔄 開発環境のメンテナンス

### 依存関係の更新

```bash
# requirements.txtの更新
pip freeze > requirements.txt

# セキュリティ脆弱性のチェック
pip audit

# パッケージのアップデート
pip-review --auto  # pip-toolsが必要
```

### データベースのリセット

```bash
# 開発環境でのデータベースリセット
flask db downgrade base
flask db upgrade

# または完全なリセット
mysql -u root -p -e "DROP DATABASE quested; CREATE DATABASE quested CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
flask db upgrade
```

---

## 📚 次のステップ

インストールが完了したら、以下のドキュメントを参照してください：

- [ユーザーマニュアル](../guides/USER_MANUAL.md) - システムの使い方
- [API仕様書](../api/API_SPECIFICATION.md) - API開発情報
- [デプロイメントガイド](../../DEPLOYMENT_GUIDE.md) - 本番環境構築
- [トラブルシューティング](../troubleshooting.md) - 問題解決

---

## 📞 サポート

インストールで問題が発生した場合：

- **GitHub Issues**: [プロジェクトのIssues](https://github.com/yourusername/QuestEd/issues)
- **Email**: support@quested.example.com
- **Wiki**: [プロジェクトWiki](https://github.com/yourusername/QuestEd/wiki)

---

<div align="center">
  <p>
    インストール完了おめでとうございます！🎉<br>
    QuestEdでの開発をお楽しみください
  </p>
  <p>
    <a href="#quested-インストールガイド">トップに戻る ⬆️</a>
  </p>
</div>