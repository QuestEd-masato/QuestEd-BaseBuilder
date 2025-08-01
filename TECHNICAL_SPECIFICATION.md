# QuestEd 技術仕様書
## 包括的システムアーキテクチャ・開発ガイド

**バージョン**: 2.1 (Phase8完了版)  
**最終更新**: 2025-07-31  
**文書種別**: 技術仕様書  
**対象**: 開発者、システムアーキテクト、DevOpsエンジニア

---

## 📚 目次

1. [システム概要](#system-overview)
2. [技術スタック](#technology-stack)
3. [アーキテクチャ分析](#architecture-analysis)
4. [データベース設計](#database-schema)
5. [APIエンドポイント](#api-endpoints)
6. [セキュリティアーキテクチャ](#security-architecture)
7. [デプロイメント](#deployment-architecture)
8. [開発ガイドライン](#development-guidelines)
9. [パフォーマンス考慮事項](#performance-considerations)
10. [テスト戦略](#testing-strategy)

---

## 1. システム概要 {#system-overview}

### 1.1 プロジェクト概要
QuestEdは、中学校・高等学校向けの探究型学習を支援する総合的な教育プラットフォームです。AI技術を活用して、生徒一人ひとりに最適化された学習体験を提供し、教師の指導をサポートします。

### 1.2 主要機能
- **🤖 AI学習支援**: 各教科に特化したAIプロンプトによる個別指導
- **📊 進捗管理**: リアルタイムの学習進捗追跡と可視化
- **👥 多役割対応**: 管理者・教師・生徒の各役割に応じた機能
- **🏫 学校管理**: クラス編成、生徒管理、年度管理
- **📝 自動レポート**: AI生成の日次学習レポート
- **🔒 セキュリティ**: 多要素認証（MFA）、FERPA/COPPA準拠

### 1.3 技術的特徴
- **教科統合**: 6教科対応（理科、数学、国語、社会、英語、総合）
- **セキュリティファースト設計**: XSS対策、CSRF保護、ロールベースアクセス制御
- **スケーラブルアーキテクチャ**: Celeryベース非同期処理
- **メール統合**: SMTP/Gmail API デュアルサポート
- **ファイルセキュリティ**: 包括的ファイル検証・サンドボックス化

---

## 2. 技術スタック {#technology-stack}

### 2.1 バックエンドフレームワーク
```
フレームワーク: Flask 2.2.3
ORM: SQLAlchemy (Flask-SQLAlchemy 3.0.3)
データベース: MySQL 8.0 with PyMySQL 1.0.3
タスクキュー: Celery with Redis backend
認証: Flask-Login 0.6.2
フォーム・CSRF: Flask-WTF 1.1.1
管理画面: Flask-Admin 1.6.1
データベースマイグレーション: Flask-Migrate 4.0.4
レート制限: Flask-Limiter 3.5.0
```

### 2.2 フロントエンド技術
```
CSSフレームワーク: Bootstrap 5.x
JavaScript: Vanilla JS + jQuery (最小使用)
アイコン: Font Awesome
テンプレート: Jinja2 (Flask内蔵)
チャートライブラリ: Chart.js (分析用)
```

### 2.3 外部サービス
```
AIサービス: OpenAI GPT-4/GPT-3.5-turbo (API 0.27.2)
メール: Gmail SMTP / Gmail API
ファイル処理: Pillow 11.0.0
PDF生成: ReportLab 4.0.4
セキュリティ: bleach 6.1.0 HTML サニタイゼーション
```

### 2.4 インフラストラクチャ
```
アプリケーションサーバー: Gunicorn 20.1.0
リバースプロキシ: Nginx
データベース: MySQL 8.0
キャッシュ/メッセージブローカー: Redis 6.0+
プロセス管理: systemd
サーバー: AWS EC2 (推奨: t3a.medium+)
```

---

## 3. アーキテクチャ分析 {#architecture-analysis}

### 3.1 Blueprintベースモジュラーアーキテクチャ

#### アプリケーション構造
```
app/
├── __init__.py           # アプリケーションファクトリ
├── admin/               # 管理者機能
├── ai/                  # AI統合機能
├── api/                 # RESTful API
├── auth/                # 認証・認可
├── models/              # データベースモデル
├── student/             # 生徒機能
├── teacher/             # 教師機能
└── utils/               # ユーティリティ
```

#### 主要モジュール

**1. 認証モジュール (`app/auth/`)**
- ロールベース認証システム
- 多要素認証（MFA）実装
- リソース所有権検証

**2. AIモジュール (`app/ai/`)**
- OpenAI API統合
- 教科別プロンプト管理
- AI応答処理・フィルタリング

**3. 学生モジュール (`app/student/`)**
- 探究テーマ管理
- 学習活動記録
- 目標・TODO管理
- AI チューター機能

**4. 教師モジュール (`app/teacher/`)**
- カリキュラム作成・管理
- 生徒進捗モニタリング
- 評価・採点機能
- レポート生成

### 3.2 データベースアーキテクチャ

**テーブル数**: 69テーブル  
**主要エンティティ**: users, classes, curriculum_units, activity_logs, ai_recommendations

#### 重要なテーブル関係
```sql
users (基本ユーザー情報)
├── student_enrollments (生徒登録)
├── teacher_assignments (教師割り当て)
└── class_enrollments (クラス登録)

curriculum_units (カリキュラム単元)
├── curriculum_items (単元項目)
├── learning_paths (学習パス)
└── proficiency_records (習熟度記録)

inquiry_themes (探究テーマ)
├── inquiry_activities (探究活動)
├── student_evaluations (生徒評価)
└── ai_recommendations (AI推奨)
```

---

## 4. セキュリティアーキテクチャ {#security-architecture}

### 4.1 認証・認可システム

#### 多要素認証（MFA）
- **TOTP方式**: Time-based One-Time Password
- **QRコード生成**: Google Authenticator等対応
- **バックアップコード**: 緊急時アクセス用
- **デバイス信頼**: 信頼済みデバイス管理

#### ロールベースアクセス制御
```python
# 役割定義
ROLES = {
    'admin': ['*'],  # 全権限
    'teacher': ['view_students', 'edit_curriculum', 'create_reports'],
    'student': ['view_own_data', 'submit_activities', 'chat_ai']
}
```

### 4.2 データ保護

#### 暗号化
- **データ暗号化**: Fernet (AES-128)
- **パスワードハッシュ**: bcrypt
- **セッション管理**: Flask-Session + Redis

#### セキュリティヘッダー
```python
# CSPヘッダー設定例
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
```

### 4.3 入力検証・サニタイゼーション

#### XSS対策
```python
import bleach

# HTMLサニタイゼーション
safe_html = bleach.clean(user_input, tags=['p', 'br'], strip=True)
```

#### CSRF対策
```python
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)
```

---

## 5. APIエンドポイント {#api-endpoints}

### 5.1 RESTful API設計

#### 認証API
```
POST /api/auth/login          # ログイン
POST /api/auth/logout         # ログアウト
POST /api/auth/mfa/setup      # MFA設定
POST /api/auth/mfa/verify     # MFA検証
```

#### 学生API
```
GET  /api/students/profile          # プロフィール取得
PUT  /api/students/profile          # プロフィール更新
GET  /api/students/activities       # 活動一覧
POST /api/students/activities       # 活動作成
GET  /api/students/ai/chat          # AIチャット履歴
POST /api/students/ai/chat          # AIチャット送信
```

#### 教師API
```
GET  /api/teachers/classes          # 担当クラス一覧
GET  /api/teachers/students         # 担当生徒一覧
POST /api/teachers/evaluations      # 評価作成
GET  /api/teachers/reports          # レポート生成
```

### 5.2 AI統合API

#### プロンプト管理
```python
# 教科別プロンプトテンプレート
SUBJECT_PROMPTS = {
    'science': 'あなたは理科の専門教師です...',
    'math': 'あなたは数学の専門教師です...',
    'japanese': 'あなたは国語の専門教師です...'
}
```

---

## 6. デプロイメントアーキテクチャ {#deployment-architecture}

### 6.1 推奨構成

#### 本番環境
```
[Internet] → [ALB] → [EC2 instances] → [RDS MySQL]
                           ↓
                    [ElastiCache Redis]
```

#### システム要件
- **EC2インスタンス**: t3a.medium以上 (2 vCPU, 4GB RAM)
- **RDS**: MySQL 8.0, db.t3.micro以上
- **ElastiCache**: Redis 6.x, cache.t3.micro以上

### 6.2 設定管理

#### 環境変数
```bash
# アプリケーション設定
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=your-secret-key

# データベース設定
DATABASE_URL=mysql://user:pass@host:port/db
REDIS_URL=redis://host:port/0

# AI設定
OPENAI_API_KEY=your-openai-key
```

---

## 7. 開発ガイドライン {#development-guidelines}

### 7.1 コーディング規約

#### Python スタイル
- **PEP 8準拠**: Black フォーマッター使用
- **型ヒント**: Python 3.8+ 型注釈
- **ドキュメンテーション**: Google スタイル docstring

#### ファイル構造規約
```python
# モジュール構造例
from flask import Blueprint
from app.utils.decorators import role_required

bp = Blueprint('example', __name__)

@bp.route('/endpoint')
@role_required('teacher')
def example_function():
    """関数の説明
    
    Returns:
        dict: レスポンスデータ
    """
    pass
```

### 7.2 データベース設計原則

#### 命名規約
- **テーブル名**: 複数形、スネークケース（例: `student_enrollments`）
- **カラム名**: スネークケース（例: `created_at`）
- **インデックス名**: `ix_table_column` 形式

#### マイグレーション管理
```bash
# マイグレーション生成
flask db migrate -m "Add new feature"

# マイグレーション適用
flask db upgrade
```

---

## 8. パフォーマンス考慮事項 {#performance-considerations}

### 8.1 データベース最適化

#### インデックス戦略
```sql
-- 頻繁に検索されるカラムにインデックス
CREATE INDEX ix_users_email ON users(email);
CREATE INDEX ix_activities_student_id ON activities(student_id);
CREATE INDEX ix_activities_created_at ON activities(created_at);

-- 複合インデックス
CREATE INDEX ix_enrollments_student_class ON enrollments(student_id, class_id);
```

#### クエリ最適化
```python
# N+1問題の回避
students = Student.query.options(
    joinedload(Student.enrollments).joinedload(Enrollment.class_group)
).all()
```

### 8.2 キャッシュ戦略

#### Redis キャッシュ
```python
import redis
from flask import current_app

def get_cached_data(key, timeout=300):
    """キャッシュからデータを取得"""
    r = redis.from_url(current_app.config['REDIS_URL'])
    data = r.get(key)
    if data:
        return json.loads(data)
    return None
```

---

## 9. テスト戦略 {#testing-strategy}

### 9.1 テスト構造

#### テストタイプ
```
tests/
├── unit/           # 単体テスト
├── integration/    # 統合テスト
├── functional/     # 機能テスト
└── fixtures/       # テストデータ
```

#### テスト実行
```bash
# 全テスト実行
python -m pytest

# カバレッジレポート
python -m pytest --cov=app --cov-report=html

# 特定テストのみ
python -m pytest tests/unit/test_auth.py
```

### 9.2 テストデータ管理

#### ファクトリパターン
```python
import factory
from app.models import User

class UserFactory(factory.Factory):
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    role = "student"
```

---

## 10. セキュリティ実装状況

### 10.1 完了済みセキュリティ機能

#### MFA（多要素認証）システム
- **実装ファイル**: `app/auth/mfa.py` (502行)
- **機能**: TOTP、QRコード生成、バックアップコード管理、デバイス信頼機能
- **状況**: ✅ 完全実装済み

#### リソース所有権検証システム
- **実装ファイル**: `app/utils/resource_ownership.py`, `app/utils/enhanced_decorators.py`
- **機能**: ロールベースアクセス制御、データ分離
- **状況**: ✅ 実装済み

#### XSS/CSRF対策
- **修正箇所**: 8箇所修正完了
- **実装**: HTMLサニタイゼーション、CSRFトークン検証
- **状況**: ✅ 修正完了

#### データ暗号化
- **方式**: Fernet (AES-128)
- **対象**: 機密データ、パスワード
- **状況**: ✅ 実装済み

#### 監査ログ
- **機能**: 全重要操作の記録
- **実装**: activity_logs テーブル、自動ログ記録
- **状況**: ✅ 実装済み

---

## 11. システム統計情報

### 11.1 現在のシステム規模

| 項目 | 数量 | 備考 |
|------|-----:|------|
| **総テーブル数** | 69 | MySQL データベース |
| **Python ファイル数** | 5,292 | アプリケーション全体 |
| **API エンドポイント** | 259 | RESTful API |
| **Blueprint モジュール** | 7 | 主要機能モジュール |
| **データベース警告** | 59 | 最適化対象 |

### 11.2 Phase6-8B 技術的負債解消実績

#### 神クラス・神関数解消（Phase6-7）
| ファイル | 修正前 | 修正後 | 削減量 | 削減率 |
|----------|------:|------:|------:|-------:|
| `weakness_analyzer.py` | 1,945行 | **削除** | 1,945行 | **100%** ✅ |
| `dashboard.py` | 1,398行 | 1,249行 | 334行 | 21% |
| `task_management.py` | 472行 | 259行 | 213行 | 45% |
| `curriculum_helpers.py` | 422行 | 178行 | 244行 | 58% |
| `auto_sync_service.py` | 864行 | 428行 | 436行 | 50% |

#### Phase8A-8B 劇的改革成果
| 項目 | 修正前 | 修正後 | 削減量 | 削減率 |
|------|------:|------:|------:|-------:|
| **unit_management.py** | 1,766行 | 262行 | 1,504行 | **85.2%** ⭐ |
| **バックアップファイル** | 23個 | 0個 | 23個 | **100%** ✅ |
| **専門サービス創設** | 0個 | 8個 | +8個 | - |
| **技術的負債レベル** | Grade D | Grade B+ | - | **劇的改善** ⭐ |

---

## 12. Phase9以降の発展計画

### 12.1 Phase9A: 残存巨大ファイル最適化（2025年8月上旬）
- `ranking_service.py` (1,125行) の専門サービス分割
- `curriculum_management.py` (1,209行) の機能別分解
- Service Layer Architecture の完全適用

### 12.2 Phase9B: フロントエンド現代化（2025年8月中旬～9月）
- React/Next.js 部分導入検討
- モダンUI/UX実装
- 既存jQuery/Bootstrap からの段階的移行

### 12.3 Phase10: モジュラーモノリス化（2025年9月～10月）
- マイクロサービス準備
- API レスポンス時間最適化
- テストカバレッジ向上（目標80%以上）

### 12.4 長期発展項目（2025年10月以降）
- CI/CD パイプライン強化
- Redis クラスター導入
- AI モデル最適化

---

**文書管理情報**
- 作成者: QuestEd Development Team
- レビュー周期: 月次
- 関連文書: README.md, PROJECT_HISTORY.md
- バージョン管理: Git タグ連動