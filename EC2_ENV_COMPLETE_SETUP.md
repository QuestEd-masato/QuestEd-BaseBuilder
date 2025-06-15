# EC2 .envファイル完全セットアップガイド

## 📋 完成形の.envファイル構成

### EC2サーバーの `/path/to/quested/.env` ファイル内容

```bash
# ========================================
# 基本Flask設定（既存）
# ========================================
FLASK_APP=app.py
FLASK_ENV=production
FLASK_DEBUG=false

# ========================================
# セキュリティキー（既存 + 新規追加）
# ========================================
SECRET_KEY=your-existing-secret-key-64-chars-long
ENCRYPTION_KEY=your-new-32-char-encryption-key
JWT_SECRET_KEY=your-new-64-char-jwt-secret-key

# ========================================
# データベース設定（既存）
# ========================================
DB_USERNAME=your-existing-db-username
DB_PASSWORD=your-existing-db-password
DB_HOST=your-existing-db-host
DB_NAME=your-existing-db-name

# ========================================
# メール設定（既存）
# ========================================
SMTP_SERVER=your-existing-smtp-server
SMTP_PORT=your-existing-smtp-port
SMTP_USER=your-existing-smtp-user
SMTP_PASSWORD=your-existing-smtp-password
SENDER_EMAIL=your-existing-sender-email

# ========================================
# AI機能（既存）
# ========================================
OPENAI_API_KEY=your-existing-openai-api-key

# ========================================
# 新規追加：セキュリティ設定
# ========================================
# パスワード要件
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBERS=true

# ログイン制限
MAX_LOGIN_ATTEMPTS=5
LOGIN_LOCKOUT_DURATION=300

# セッション設定
SESSION_TIMEOUT_MINUTES=30
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Strict

# ========================================
# 新規追加：機能制御
# ========================================
# セキュリティ上無効化
VOICE_INPUT_ENABLED=false

# AI機能制御
AI_FEATURES_ENABLED=true
AI_CHAT_ENABLED=true
AI_CURRICULUM_GENERATION_ENABLED=true

# ========================================
# 新規追加：ログ・監視設定
# ========================================
LOG_LEVEL=WARNING
SECURITY_LOG_ENABLED=true
ACCESS_LOG_ENABLED=true

# ========================================
# 新規追加：ファイルアップロード制限
# ========================================
MAX_CONTENT_LENGTH=16777216
ALLOWED_EXTENSIONS=jpg,jpeg,png,gif,pdf,doc,docx,txt
UPLOAD_FOLDER=static/uploads

# ========================================
# 新規追加：レート制限設定
# ========================================
# Redis使用時（推奨）
RATELIMIT_STORAGE_URL=redis://localhost:6379/1
RATELIMIT_DEFAULT=100 per hour
RATELIMIT_LOGIN=5 per minute
RATELIMIT_API=1000 per hour

# ========================================
# 新規追加：CSRF・CORS設定
# ========================================
WTF_CSRF_ENABLED=true
WTF_CSRF_TIME_LIMIT=3600
CORS_ENABLED=true

# ========================================
# 新規追加：アプリケーション情報
# ========================================
APP_VERSION=1.0.0
ENVIRONMENT=production
```

## 🔧 各値の作成方法

### 1. 新しいセキュリティキー生成

#### EC2サーバーで実行：
```bash
# SSH接続後、QuestEdディレクトリで実行

# ENCRYPTION_KEY生成（32文字）
python3 -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_urlsafe(32))"

# JWT_SECRET_KEY生成（64文字）
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(32))"

# 結果例：
# ENCRYPTION_KEY=aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789abcd
# JWT_SECRET_KEY=1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
```

#### 安全な手順：
```bash
# 1. キー生成
ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# 2. 確認
echo "生成されたENCRYPTION_KEY: $ENCRYPTION_KEY"
echo "生成されたJWT_SECRET_KEY: $JWT_SECRET_KEY"

# 3. .envファイルに追加
echo "ENCRYPTION_KEY=$ENCRYPTION_KEY" >> .env
echo "JWT_SECRET_KEY=$JWT_SECRET_KEY" >> .env
```

### 2. Redisの設定確認

#### Redisが既にインストールされている場合：
```bash
# Redis動作確認
redis-cli ping
# 応答: PONG

# レート制限用Redis URL設定
echo "RATELIMIT_STORAGE_URL=redis://localhost:6379/1" >> .env
```

#### Redisが未インストールの場合：
```bash
# シンプルなレート制限設定（メモリベース）
cat >> .env << 'EOF'
RATELIMIT_DEFAULT=100 per hour
RATELIMIT_LOGIN=5 per minute
RATELIMIT_API=1000 per hour
EOF
```

### 3. ログディレクトリの作成

```bash
# ログディレクトリ作成
mkdir -p logs
chmod 755 logs

# ログ設定を.envに追加
cat >> .env << 'EOF'
LOG_LEVEL=WARNING
SECURITY_LOG_ENABLED=true
ACCESS_LOG_ENABLED=true
LOG_FILE=logs/quested.log
SECURITY_LOG_FILE=logs/security.log
ACCESS_LOG_FILE=logs/access.log
EOF
```

## 🚀 完全なセットアップスクリプト

### EC2で実行する完全スクリプト：

```bash
#!/bin/bash
# EC2 QuestEd 環境変数完全セットアップスクリプト

# QuestEdディレクトリに移動
cd /path/to/quested  # 実際のパスに変更

echo "=== QuestEd EC2環境変数セットアップ開始 ==="

# 1. バックアップ作成
echo "既存.envファイルをバックアップ中..."
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# 2. 新しいセキュリティキー生成
echo "セキュリティキーを生成中..."
ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

echo "生成完了:"
echo "  ENCRYPTION_KEY: ${ENCRYPTION_KEY:0:8}..."
echo "  JWT_SECRET_KEY: ${JWT_SECRET_KEY:0:8}..."

# 3. ログディレクトリ作成
echo "ログディレクトリを作成中..."
mkdir -p logs
chmod 755 logs

# 4. 新しい設定を.envに追加
echo "新しい設定を.envに追加中..."
cat >> .env << EOF

# ========================================
# セキュリティ強化設定（追加日: $(date +%Y-%m-%d)）
# ========================================
ENCRYPTION_KEY=$ENCRYPTION_KEY
JWT_SECRET_KEY=$JWT_SECRET_KEY

# セキュリティ設定
VOICE_INPUT_ENABLED=false
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBERS=true
MAX_LOGIN_ATTEMPTS=5
LOGIN_LOCKOUT_DURATION=300

# セッション設定
SESSION_TIMEOUT_MINUTES=30
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Strict

# 機能制御
AI_FEATURES_ENABLED=true
AI_CHAT_ENABLED=true
AI_CURRICULUM_GENERATION_ENABLED=true

# ログ設定
LOG_LEVEL=WARNING
SECURITY_LOG_ENABLED=true
ACCESS_LOG_ENABLED=true
LOG_FILE=logs/quested.log
SECURITY_LOG_FILE=logs/security.log
ACCESS_LOG_FILE=logs/access.log

# ファイルアップロード制限
MAX_CONTENT_LENGTH=16777216
ALLOWED_EXTENSIONS=jpg,jpeg,png,gif,pdf,doc,docx,txt
UPLOAD_FOLDER=static/uploads

# レート制限設定
RATELIMIT_DEFAULT=100 per hour
RATELIMIT_LOGIN=5 per minute
RATELIMIT_API=1000 per hour

# CSRF・CORS設定
WTF_CSRF_ENABLED=true
WTF_CSRF_TIME_LIMIT=3600
CORS_ENABLED=true

# アプリケーション情報
APP_VERSION=1.0.0
ENVIRONMENT=production
FLASK_ENV=production
EOF

# 5. Redis確認とレート制限設定
echo "Redis接続を確認中..."
if redis-cli ping >/dev/null 2>&1; then
    echo "Redisが利用可能です。Redis-based rate limitingを設定します。"
    echo "RATELIMIT_STORAGE_URL=redis://localhost:6379/1" >> .env
else
    echo "Redisが利用できません。メモリベースのrate limitingを使用します。"
fi

# 6. 権限設定
echo "ファイル権限を設定中..."
chmod 600 .env

# 7. 設定確認
echo "=== 設定確認 ==="
echo "FLASK_ENV: $(grep FLASK_ENV .env | cut -d'=' -f2)"
echo "LOG_LEVEL: $(grep LOG_LEVEL .env | cut -d'=' -f2)"
echo "VOICE_INPUT_ENABLED: $(grep VOICE_INPUT_ENABLED .env | cut -d'=' -f2)"

# 8. 設定ファイル構文チェック
echo "設定ファイルの構文をチェック中..."
if python3 -c "from dotenv import load_dotenv; load_dotenv(); print('設定ファイル: OK')" 2>/dev/null; then
    echo "✅ 設定ファイルの構文は正常です"
else
    echo "❌ 設定ファイルに問題があります"
    exit 1
fi

echo "=== セットアップ完了 ==="
echo "次のステップ:"
echo "1. sudo systemctl restart quested"
echo "2. pytest tests/security/ -v (テスト実行)"
echo "3. tail -f logs/quested.log (ログ確認)"
```

## 📝 手動セットアップ手順

### ステップ1: バックアップ作成
```bash
cd /path/to/quested
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
```

### ステップ2: セキュリティキー生成
```bash
# 新しいキーを生成
python3 -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_urlsafe(32))" >> .env
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(32))" >> .env
```

### ステップ3: 基本設定追加
```bash
cat >> .env << 'EOF'

# セキュリティ強化設定
VOICE_INPUT_ENABLED=false
PASSWORD_MIN_LENGTH=8
MAX_LOGIN_ATTEMPTS=5
SESSION_TIMEOUT_MINUTES=30
LOG_LEVEL=WARNING
MAX_CONTENT_LENGTH=16777216
FLASK_ENV=production
WTF_CSRF_ENABLED=true
AI_FEATURES_ENABLED=true
EOF
```

### ステップ4: ログディレクトリ作成
```bash
mkdir -p logs
chmod 755 logs
echo "LOG_FILE=logs/quested.log" >> .env
```

### ステップ5: ファイル権限設定
```bash
chmod 600 .env
```

### ステップ6: アプリケーション再起動
```bash
# サービス再起動（実際のサービス名に置き換え）
sudo systemctl restart quested
# または
sudo systemctl restart nginx && sudo systemctl restart gunicorn
```

## 🔍 設定確認方法

### 1. 環境変数確認
```bash
# 重要な設定の確認
grep -E "(FLASK_ENV|VOICE_INPUT|LOG_LEVEL)" .env

# セキュリティキーの存在確認（値は表示しない）
grep -E "(SECRET_KEY|ENCRYPTION_KEY|JWT_SECRET_KEY)" .env | cut -d'=' -f1
```

### 2. アプリケーション動作確認
```bash
# Python設定確認
python3 -c "
from config import get_config
config = get_config()
print('Flask環境:', getattr(config, 'ENV', 'Unknown'))
print('デバッグモード:', getattr(config, 'DEBUG', 'Unknown'))
print('設定ロード: 成功')
"
```

### 3. セキュリティテスト実行
```bash
# 新しいセキュリティ機能のテスト
pytest tests/security/test_security.py::TestAuthenticationSecurity -v
```

## ⚠️ 重要な注意事項

### セキュリティ
1. **キー生成は必ずEC2サーバーで実行**
2. **.envファイルの権限は600に設定**
3. **既存のSECRET_KEYは変更しない**
4. **バックアップを必ず作成**

### トラブルシューティング
```bash
# ログ確認
sudo journalctl -u quested -f

# 設定エラー確認
python3 -c "from dotenv import load_dotenv; load_dotenv()"

# ファイル権限確認
ls -la .env
```

---

この設定により、QuestEdの新しいセキュリティ機能とテストスイートが完全に動作し、本番環境での安全性が大幅に向上します。