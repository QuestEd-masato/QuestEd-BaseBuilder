# QuestEd 包括的テストガイド

## 概要

このドキュメントは、QuestEdアプリケーションの包括的なテストスイートについて説明します。テストの不足を完全に解決し、本番環境での品質保証を実現するために、複数レイヤーのテスト戦略を実装しています。

## テスト戦略

### テストピラミッド構造

```
     🔺 E2E Tests (少数・高コスト)
    🔺🔺 Integration Tests (中程度)
   🔺🔺🔺 Unit Tests (多数・低コスト)
```

## テストスイート構成

### 1. 単体テスト (Unit Tests)
**場所**: `tests/unit/`

#### `test_models.py` & `test_models_extended.py`
- **対象**: データベースモデル
- **テスト内容**:
  - モデルの作成・更新・削除
  - リレーションシップの整合性
  - バリデーション機能
  - パスワードハッシュ化
  - ユーザー権限システム
  - JSON データ処理

#### `test_utils.py`
- **対象**: ユーティリティ関数
- **テスト内容**:
  - セキュリティ機能
  - 入力検証・サニタイゼーション
  - エラーハンドリング
  - データ暗号化・復号化
  - API認証
  - レート制限

### 2. 統合テスト (Integration Tests)
**場所**: `tests/integration/`

#### `test_routes.py`
- **対象**: HTTPエンドポイント
- **テスト内容**:
  - 認証フロー（ログイン・ログアウト・登録）
  - 学生機能（ダッシュボード・活動記録・テーマ管理）
  - 教師機能（クラス管理・評価・カリキュラム）
  - 管理者機能（ユーザー管理・学校管理）
  - APIエンドポイント
  - ファイルアップロード
  - エラーハンドリング

### 3. セキュリティテスト (Security Tests)
**場所**: `tests/security/`

#### `test_security.py`
- **対象**: セキュリティ機能全般
- **テスト内容**:
  - 認証セキュリティ（パスワード強度・アカウントロック）
  - 入力検証（XSS・SQLインジェクション・ディレクトリトラバーサル）
  - レート制限
  - セッションセキュリティ
  - データ保護
  - APIセキュリティヘッダー
  - 認可制御
  - ペネトレーションテストシナリオ

### 4. エンドツーエンドテスト (E2E Tests)
**場所**: `tests/e2e/`

#### `test_user_flows.py`
- **対象**: 完全なユーザーワークフロー
- **テスト内容**:
  - 学生のオンボーディング〜活動記録
  - 教師のクラス管理〜評価
  - 管理者のシステム管理
  - 役割間相互作用
  - パフォーマンス・負荷テスト

## テスト設定

### pytest.ini
- カバレッジ測定（80%以上必須）
- 並列実行対応
- マーカー設定（unit, integration, security, e2e）
- HTML・XMLレポート生成

### conftest.py
- アプリケーションインスタンス管理
- テストデータベース設定
- 認証済みクライアント
- サンプルデータ生成
- モック設定

## CI/CD パイプライン

### GitHub Actions ワークフロー
**ファイル**: `.github/workflows/test.yml`

#### テストマトリクス
- **Python バージョン**: 3.9, 3.10, 3.11
- **テストタイプ**: unit, integration, security
- **データベース**: MySQL 8.0
- **キャッシュ**: Redis 7

#### 実行ステップ
1. **環境構築**
   - Python セットアップ
   - 依存関係インストール
   - データベース初期化

2. **テスト実行**
   - 単体テスト（カバレッジ測定）
   - 統合テスト
   - セキュリティテスト
   - E2Eテスト（Python 3.10のみ）

3. **品質チェック**
   - セキュリティスキャン（Bandit, Safety）
   - コード品質（flake8, black, isort, mypy）
   - パフォーマンステスト（スケジュール実行）

4. **レポート生成**
   - カバレッジレポート（Codecov連携）
   - テスト結果アーティファクト
   - セキュリティレポート

## テスト実行方法

### ローカル環境

#### 全テスト実行
```bash
pytest -v
```

#### カテゴリ別実行
```bash
# 単体テスト
pytest tests/unit/ -v

# 統合テスト
pytest tests/integration/ -v

# セキュリティテスト
pytest tests/security/ -v

# E2Eテスト
pytest tests/e2e/ -v
```

#### マーカー別実行
```bash
# セキュリティ関連のみ
pytest -m security -v

# データベース関連のみ
pytest -m db -v

# 認証関連のみ
pytest -m auth -v
```

#### カバレッジ付き実行
```bash
pytest --cov=app --cov=basebuilder --cov-report=html --cov-report=term-missing
```

#### 並列実行
```bash
pytest -n auto  # CPU コア数に応じた並列実行
```

### 開発環境での継続的テスト

#### ファイル変更監視
```bash
# pytest-watchを使用
pip install pytest-watch
ptw
```

#### 特定ファイルのテスト
```bash
pytest tests/unit/test_models.py::TestUserModel::test_password_hashing -v
```

## カバレッジ目標

### 最低カバレッジ要件
- **全体**: 80%以上
- **重要モジュール**: 90%以上
  - `app/models/`
  - `app/utils/security.py`
  - `app/utils/input_validator.py`
  - `app/auth/`

### カバレッジレポート確認
```bash
# HTMLレポート生成
pytest --cov=app --cov-report=html
open htmlcov/index.html

# ターミナルでの詳細表示
pytest --cov=app --cov-report=term-missing
```

## テストデータ管理

### フィクスチャ設計
- **スコープ管理**: function, module, session
- **依存関係**: 最小限に抑制
- **リソース管理**: 適切なクリーンアップ

### ファクトリーボーイ活用
```python
# 将来的なテストデータ生成の改善案
import factory
from app.models import User

class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = "commit"
    
    email = factory.Faker('email')
    full_name = factory.Faker('name')
    role = 'student'
```

## パフォーマンステスト

### ベンチマーク測定
- リクエスト処理時間
- データベースクエリ性能
- メモリ使用量
- 並行処理性能

### 負荷テスト
- 同時ユーザー数
- データベース接続プール
- キャッシュ効率

## セキュリティテスト詳細

### 自動化セキュリティスキャン
1. **Bandit**: Python コードの脆弱性検出
2. **Safety**: 依存関係の既知脆弱性チェック
3. **カスタムセキュリティテスト**: アプリケーション固有の脅威

### 手動セキュリティテスト
1. **認証・認可テスト**
2. **入力検証テスト**
3. **セッション管理テスト**
4. **情報漏洩テスト**

## 継続的改善

### テスト品質指標
- **カバレッジ率**: 毎回測定
- **テスト実行時間**: パフォーマンス監視
- **失敗率**: 品質指標
- **フレーク性**: 安定性指標

### テスト追加ガイドライン
1. **新機能**: 必ずテストを追加
2. **バグ修正**: 回帰テストを追加
3. **リファクタリング**: テストでの安全性確保
4. **セキュリティ更新**: セキュリティテスト強化

## トラブルシューティング

### よくある問題

#### テストデータベース接続エラー
```bash
# 解決方法
export FLASK_ENV=testing
export DB_NAME=quested_test
```

#### カバレッジレポート生成失敗
```bash
# 解決方法
pip install coverage
coverage erase
pytest --cov=app --cov-report=html
```

#### 並列実行でのテスト失敗
```bash
# 解決方法：ファイルベースの一意性確保
pytest -n auto --dist=worksteal
```

### デバッグ支援

#### 詳細ログ有効化
```bash
pytest -v -s --log-cli-level=DEBUG
```

#### 失敗時の詳細情報
```bash
pytest --tb=long --capture=no
```

## まとめ

この包括的テストスイートにより、以下を実現しています：

✅ **完全なテストカバレッジ**: 80%以上のコードカバレッジ
✅ **多層テスト戦略**: Unit → Integration → E2E
✅ **セキュリティ保証**: 専用セキュリティテストスイート
✅ **CI/CD統合**: 自動化されたテストパイプライン
✅ **パフォーマンス監視**: ベンチマーク・負荷テスト
✅ **継続的品質保証**: 開発プロセス全体での品質チェック

これにより、本番環境での安定性とセキュリティが大幅に向上し、テスト不足の問題は完全に解決されました。

---

**最終更新**: 2025-01-15
**メンテナンス**: QuestEd 開発チーム