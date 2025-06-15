# QuestEd 環境変数設定ガイド

## 📋 概要

QuestEdの新しいセキュリティ機能とテストスイートに対応するため、追加の環境変数が必要になりました。このガイドでは、必要な設定を段階的に説明します。

## 🚀 クイックスタート（最小限設定）

### 1. 最小限の .env ファイル作成

```bash
cp .env.template.minimal .env
```

### 2. 必須項目の設定

`.env` ファイルを編集して以下を設定：

```bash
# 必ず変更が必要
SECRET_KEY=your-random-32-character-secret-key-here
ENCRYPTION_KEY=your-32-character-encryption-key-here
DB_PASSWORD=your-secure-database-password

# AI機能を使用する場合
OPENAI_API_KEY=your-openai-api-key

# メール機能を使用する場合
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

## 📝 新規追加された重要な環境変数

### 🔒 セキュリティ関連（必須）

| 変数名 | 説明 | 例 | 必須度 |
|--------|------|----|----|
| `ENCRYPTION_KEY` | 機密データ暗号化キー | `your-32-char-encryption-key` | ⚠️ 必須 |
| `JWT_SECRET_KEY` | JWT認証用秘密鍵 | `jwt-secret-different-from-main` | 🔴 高 |
| `PASSWORD_MIN_LENGTH` | パスワード最小長 | `8` | 🟡 推奨 |
| `MAX_LOGIN_ATTEMPTS` | ログイン試行回数制限 | `5` | 🟡 推奨 |

### 📊 レート制限（推奨）

| 変数名 | 説明 | 例 | 必須度 |
|--------|------|----|----|
| `RATELIMIT_STORAGE_URL` | レート制限データ保存先 | `redis://localhost:6379/1` | 🟡 推奨 |
| `RATELIMIT_LOGIN` | ログインレート制限 | `5 per minute` | 🟡 推奨 |
| `RATELIMIT_API` | APIレート制限 | `1000 per hour` | 🟡 推奨 |

### 📧 メール設定（重要）

| 変数名 | 説明 | 例 | 必須度 |
|--------|------|----|----|
| `MAIL_ENABLED` | メール機能有効化 | `true` | 🔴 高 |
| `MAIL_SERVER` | SMTPサーバー | `smtp.gmail.com` | 🔴 高 |
| `MAIL_USERNAME` | メールアドレス | `your-email@gmail.com` | 🔴 高 |
| `MAIL_PASSWORD` | メールパスワード | `your-app-password` | 🔴 高 |

### 📁 ファイルアップロード

| 変数名 | 説明 | 例 | 必須度 |
|--------|------|----|----|
| `MAX_CONTENT_LENGTH` | 最大ファイルサイズ | `16777216` (16MB) | 🟡 推奨 |
| `ALLOWED_EXTENSIONS` | 許可拡張子 | `jpg,jpeg,png,gif,pdf` | 🟡 推奨 |

### 📋 ログ設定

| 変数名 | 説明 | 例 | 必須度 |
|--------|------|----|----|
| `LOG_LEVEL` | ログレベル | `INFO` | 🟡 推奨 |
| `SECURITY_LOG_ENABLED` | セキュリティログ | `true` | 🟡 推奨 |

### 🔧 機能フラグ

| 変数名 | 説明 | 例 | 必須度 |
|--------|------|----|----|
| `VOICE_INPUT_ENABLED` | 音声入力機能 | `false` | ⚠️ セキュリティ上無効 |
| `AI_FEATURES_ENABLED` | AI機能全般 | `true` | 🟡 推奨 |

## 🎯 環境別設定

### 開発環境 (.env)

```bash
# 開発環境設定例
FLASK_ENV=development
FLASK_DEBUG=true
SECRET_KEY=dev-secret-key-change-in-production
ENCRYPTION_KEY=dev-encryption-key-32-characters
DB_HOST=localhost
DB_NAME=quested
LOG_LEVEL=DEBUG
VOICE_INPUT_ENABLED=false
```

### テスト環境

```bash
# テスト実行時の環境変数
TESTING=true
FLASK_ENV=testing
SECRET_KEY=test-secret-key-for-testing-only
WTF_CSRF_ENABLED=false
MAIL_ENABLED=false
```

### 本番環境

```bash
# 本番環境では AWS Secrets Manager 推奨
FLASK_ENV=production
FLASK_DEBUG=false
SECRET_KEY=${SECRET_KEY}  # AWS Secrets Manager
ENCRYPTION_KEY=${ENCRYPTION_KEY}  # AWS Secrets Manager
FORCE_HTTPS=true
SESSION_COOKIE_SECURE=true
LOG_LEVEL=WARNING
```

## 🔐 セキュリティキーの生成方法

### SECRET_KEY の生成

```python
import secrets
print(secrets.token_hex(32))  # 64文字の16進数文字列
```

### ENCRYPTION_KEY の生成

```python
import secrets
print(secrets.token_urlsafe(32))  # 32文字のURL安全な文字列
```

### コマンドラインでの生成

```bash
# SECRET_KEY 生成
python -c "import secrets; print(secrets.token_hex(32))"

# ENCRYPTION_KEY 生成
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 📧 Gmail設定（メール機能用）

### 1. Googleアカウントでアプリパスワード生成

1. Googleアカウント → セキュリティ
2. 2段階認証を有効化
3. アプリパスワードを生成
4. 生成されたパスワードを `MAIL_PASSWORD` に設定

### 2. 設定例

```bash
MAIL_ENABLED=true
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=generated-app-password
```

## 🔍 設定確認方法

### 1. 設定ファイルの検証

```bash
python -c "
from config import get_config
config = get_config()
print('設定確認:')
print(f'SECRET_KEY: {\"設定済み\" if config.SECRET_KEY else \"未設定\"}')
print(f'ENCRYPTION_KEY: {\"設定済み\" if hasattr(config, \"ENCRYPTION_KEY\") else \"未設定\"}')
print(f'OPENAI_API_KEY: {\"設定済み\" if config.OPENAI_API_KEY else \"未設定\"}')
"
```

### 2. テスト実行での確認

```bash
# テスト実行
pytest tests/unit/test_utils.py::TestSecurityUtils::test_generate_secure_token -v

# セキュリティテスト
pytest tests/security/ -v
```

## ⚠️ セキュリティ注意事項

### 🚨 絶対にやってはいけないこと

1. **秘密鍵のハードコード**
   ```python
   # ❌ 危険
   SECRET_KEY = "hardcoded-secret"
   
   # ✅ 正しい
   SECRET_KEY = os.getenv('SECRET_KEY')
   ```

2. **本番環境でのDEBUGモード**
   ```bash
   # ❌ 危険
   FLASK_DEBUG=true
   
   # ✅ 正しい
   FLASK_DEBUG=false
   ```

3. **脆弱なパスワード**
   ```bash
   # ❌ 危険
   DB_PASSWORD=password123
   
   # ✅ 正しい
   DB_PASSWORD=Complex!Password#2025
   ```

### 🔒 必須セキュリティ設定

```bash
# 本番環境必須設定
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
WTF_CSRF_ENABLED=true
FORCE_HTTPS=true
VOICE_INPUT_ENABLED=false  # セキュリティ上無効化
```

## 🚀 すぐに始める手順

### 1. 最小限設定でスタート

```bash
# 1. テンプレートをコピー
cp .env.template.minimal .env

# 2. 必須項目を編集
nano .env

# 3. シークレットキー生成・設定
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" >> .env
python -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_urlsafe(32))" >> .env

# 4. アプリケーション起動
python app.py
```

### 2. テスト実行確認

```bash
# テストが通ることを確認
pytest tests/unit/ -v

# セキュリティテスト実行
pytest tests/security/test_security.py::TestAuthenticationSecurity -v
```

### 3. 段階的に機能を有効化

```bash
# AI機能を使用する場合
echo "OPENAI_API_KEY=your-api-key" >> .env

# メール機能を使用する場合
echo "MAIL_USERNAME=your-email@gmail.com" >> .env
echo "MAIL_PASSWORD=your-app-password" >> .env

# Redis を使用する場合
echo "CELERY_BROKER_URL=redis://localhost:6379/0" >> .env
echo "RATELIMIT_STORAGE_URL=redis://localhost:6379/1" >> .env
```

## 🆘 トラブルシューティング

### よくある問題と解決方法

#### 1. SECRET_KEY エラー
```
ValueError: 本番環境でSECRET_KEYが設定されていません
```
**解決方法**: SECRET_KEYを環境変数に設定

#### 2. データベース接続エラー
```
Access denied for user 'quested_user'@'localhost'
```
**解決方法**: DB_PASSWORD の確認

#### 3. メール送信エラー
```
SMTPAuthenticationError: Username and Password not accepted
```
**解決方法**: Googleアプリパスワードの生成・設定

#### 4. Redis接続エラー
```
ConnectionError: Error connecting to Redis
```
**解決方法**: Redisサーバーの起動、またはRedis設定の無効化

## 📞 サポート

設定に関して問題がある場合：

1. **ドキュメント確認**: `TESTING_COMPREHENSIVE_GUIDE.md`
2. **テスト実行**: `pytest tests/unit/test_utils.py -v`
3. **ログ確認**: `logs/` ディレクトリ内のログファイル

---

**重要**: 本番環境では AWS Secrets Manager や環境変数を使用し、秘密鍵をコードに含めないようにしてください。