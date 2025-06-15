# EC2環境変数マイグレーションガイド

## 📋 現在のEC2環境変数分析

### ✅ 既存設定済み（活用可能）
```bash
FLASK_APP=app.py
FLASK_DEBUG=false  # 本番環境適切設定
SECRET_KEY=***  # 設定済み
DB_USERNAME=***  # MySQL接続情報
DB_PASSWORD=***
DB_HOST=***
DB_NAME=***
SMTP_SERVER=***  # メール送信機能
SMTP_PORT=***
SMTP_USER=***
SMTP_PASSWORD=***
SENDER_EMAIL=***
OPENAI_API_KEY=***  # AI機能利用可能
```

## 🔴 追加必須項目（新機能対応）

### 1. セキュリティ強化用キー
```bash
# 機密データ暗号化用（32文字の安全なキー）
ENCRYPTION_KEY=<32文字のランダム文字列>

# JWT認証用（SECRET_KEYとは別のキー）
JWT_SECRET_KEY=<64文字のランダム文字列>
```

**生成方法**:
```bash
# EC2サーバーで実行
python3 -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(32))"
```

### 2. レート制限設定（推奨）
```bash
# Redis使用時（推奨）
RATELIMIT_STORAGE_URL=redis://localhost:6379/1

# または簡易設定
RATELIMIT_DEFAULT=100 per hour
RATELIMIT_LOGIN=5 per minute
MAX_LOGIN_ATTEMPTS=5
```

### 3. セキュリティ設定
```bash
# パスワード要件
PASSWORD_MIN_LENGTH=8

# セッション設定
SESSION_TIMEOUT_MINUTES=30

# 機能フラグ（セキュリティ上重要）
VOICE_INPUT_ENABLED=false  # 一時的に無効化
```

## 🟡 推奨追加項目

### 4. ログ・監視設定
```bash
LOG_LEVEL=WARNING  # 本番環境適切レベル
SECURITY_LOG_ENABLED=true
```

### 5. ファイルアップロード制限
```bash
MAX_CONTENT_LENGTH=16777216  # 16MB制限
ALLOWED_EXTENSIONS=jpg,jpeg,png,gif,pdf,doc,docx
```

### 6. 環境識別
```bash
FLASK_ENV=production
APP_VERSION=1.0.0
```

## 🚀 EC2での設定手順

### ステップ1: 必須キー生成
```bash
# EC2にSSH接続後
cd /path/to/quested

# セキュリティキー生成
python3 -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_urlsafe(32))" >> .env
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(32))" >> .env
```

### ステップ2: 基本セキュリティ設定追加
```bash
# セキュリティ設定を.envに追加
cat >> .env << 'EOF'

# セキュリティ強化設定
PASSWORD_MIN_LENGTH=8
SESSION_TIMEOUT_MINUTES=30
MAX_LOGIN_ATTEMPTS=5
VOICE_INPUT_ENABLED=false

# ログ設定
LOG_LEVEL=WARNING
SECURITY_LOG_ENABLED=true

# ファイルアップロード制限
MAX_CONTENT_LENGTH=16777216
ALLOWED_EXTENSIONS=jpg,jpeg,png,gif,pdf,doc,docx

# 環境設定
FLASK_ENV=production
APP_VERSION=1.0.0
EOF
```

### ステップ3: Redisベースレート制限（オプション）
```bash
# Redisがインストール済みの場合
echo "RATELIMIT_STORAGE_URL=redis://localhost:6379/1" >> .env

# Redisが未インストールの場合は簡易設定
echo "RATELIMIT_DEFAULT=100 per hour" >> .env
echo "RATELIMIT_LOGIN=5 per minute" >> .env
```

### ステップ4: アプリケーション再起動
```bash
# サービス再起動（設定により異なる）
sudo systemctl restart quested
# または
sudo systemctl restart nginx
sudo systemctl restart gunicorn
```

## 🔧 既存設定の活用方法

### 1. メール設定の統合
既存のSMTP設定をFlask-Mailフォーマットに統合：
```python
# config.pyで既存設定を活用
MAIL_SERVER = os.getenv('SMTP_SERVER')
MAIL_PORT = int(os.getenv('SMTP_PORT', 587))
MAIL_USERNAME = os.getenv('SMTP_USER')  
MAIL_PASSWORD = os.getenv('SMTP_PASSWORD')
MAIL_DEFAULT_SENDER = os.getenv('SENDER_EMAIL')
```

### 2. OpenAI設定の確認
```bash
# AI機能テスト
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('OpenAI API Key:', 'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET')
"
```

### 3. データベース接続確認
```bash
# DB接続テスト
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
print(f'DB: {os.getenv(\"DB_HOST\")}:{os.getenv(\"DB_NAME\")}')
"
```

## ⚡ 最小限追加（即座に適用可能）

本番稼働中でも安全に追加できる最小限設定：

```bash
# EC2で実行（1行ずつ）
echo "ENCRYPTION_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" >> .env
echo "JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')" >> .env
echo "VOICE_INPUT_ENABLED=false" >> .env
echo "LOG_LEVEL=WARNING" >> .env
echo "MAX_CONTENT_LENGTH=16777216" >> .env
echo "FLASK_ENV=production" >> .env
```

## 🔍 設定確認方法

### 1. 環境変数一覧表示
```bash
cat .env | grep -v '^#' | sort
```

### 2. 重要設定の確認
```bash
# セキュリティキー確認（値は表示されない）
grep -E "(SECRET_KEY|ENCRYPTION_KEY)" .env | cut -d'=' -f1
```

### 3. アプリケーション設定確認
```bash
python3 -c "
from config import get_config
config = get_config()
print('Flask環境:', config.ENV if hasattr(config, 'ENV') else 'Unknown')
print('デバッグモード:', config.DEBUG)
print('データベース:', 'MySQL' if 'mysql' in str(config.SQLALCHEMY_DATABASE_URI) else 'Other')
"
```

## 🛡️ セキュリティチェックリスト

### ✅ 確認事項
- [ ] SECRET_KEY が設定済み（既存）
- [ ] ENCRYPTION_KEY を新規追加
- [ ] JWT_SECRET_KEY を新規追加  
- [ ] FLASK_DEBUG=false（既存確認）
- [ ] VOICE_INPUT_ENABLED=false
- [ ] LOG_LEVEL=WARNING
- [ ] MAX_CONTENT_LENGTH設定

### ⚠️ 本番環境注意事項
1. **キー生成は本番サーバーで実行**（開発環境で生成したキーは使用禁止）
2. **ENCRYPTION_KEYは既存暗号化データとの互換性なし**（新規データのみ暗号化）
3. **設定変更後はアプリケーション再起動必須**
4. **.envファイルの権限確認**（600推奨）

## 🚨 トラブルシューティング

### 問題1: アプリケーション起動エラー
```bash
# ログ確認
sudo journalctl -u quested -f

# 設定ファイル構文確認
python3 -c "from dotenv import load_dotenv; load_dotenv(); print('OK')"
```

### 問題2: セキュリティキーエラー
```bash
# キーの長さ確認
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('SECRET_KEY length:', len(os.getenv('SECRET_KEY', '')))
print('ENCRYPTION_KEY length:', len(os.getenv('ENCRYPTION_KEY', '')))
"
```

### 問題3: データベース接続エラー
```bash
# 既存設定の確認
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine
try:
    engine = create_engine(f'mysql+pymysql://{os.getenv(\"DB_USERNAME\")}:{os.getenv(\"DB_PASSWORD\")}@{os.getenv(\"DB_HOST\")}/{os.getenv(\"DB_NAME\")}')
    conn = engine.connect()
    print('データベース接続: OK')
    conn.close()
except Exception as e:
    print('データベース接続エラー:', e)
"
```

## 📞 実装支援

### 段階的実装プラン

#### Phase 1: 即座実装（5分）
- セキュリティキー追加
- 基本設定追加

#### Phase 2: 機能強化（15分）
- レート制限設定
- ログ設定

#### Phase 3: 最適化（30分）  
- Redis設定
- 監視設定

---

**次のステップ**: 上記の設定を適用後、新しいセキュリティテストスイートを実行して動作確認を行ってください。

```bash
# テスト実行
pytest tests/security/test_security.py::TestAuthenticationSecurity -v
```