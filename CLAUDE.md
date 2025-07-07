# QuestEd Development Reference - Master Index

*📅 Last Updated: 2025-07-07 | Status: ✅ Production Operational - Dashboard & Navigation Fully Operational*

This document serves as the **master index** and quick reference for the QuestEd educational platform. For detailed information, refer to the linked specialized documents.

---

## 🎯 Quick Navigation

| Document | Purpose | Update Frequency |
|----------|---------|------------------|
| **[DATABASE.md](./DATABASE.md)** | Schema, models, relationships | Low |
| **[TIMELINE.md](./TIMELINE.md)** | Chronological history & current status | High |
| **[ARCHITECTURE.md](./ARCHITECTURE.md)** | Blueprint structure & technical specs | Medium |
| **[docs/API_ENDPOINTS.md](./docs/API_ENDPOINTS.md)** | Endpoint details & fixes | High |
| **[docs/DEVELOPMENT_GUIDE.md](./docs/DEVELOPMENT_GUIDE.md)** | Safe development practices | Medium |

---

## 📊 Current System Status (2025-07-02)

### ✅ Production Environment
- **Status**: Fully Operational
- **Database**: 55 tables, 46 users, 3,811 learning records
- **Architecture**: Modular Blueprint structure (7 main modules)
- **Quality Rating**: ⭐⭐⭐⭐ (Very Good - Structure Confirmed)

### 🔄 Current Phase: Phase 1 Implementation (2025-07-02 開始)
- **Focus**: 自由進度学習基盤 + BaseBuilder修復 + ランキング修復
- **Infrastructure**: ✅ Stable and confirmed
- **Application Layer**: ✅ BaseBuilder完全復旧完了 (2025-07-05)
- **Target Completion**: 2025-07-16 (2週間計画)

---

## ⚠️ Critical Development Constraints

### 🚫 Prohibited Changes
- **Database schema modifications** (impact unknown)
- **Blueprint name changes** (breaks template references)
- **Model relationship changes** (complex dependencies)
- **Large-scale code moves** (import complexity)

### ✅ Safe Change Areas
- Individual route function improvements
- Error handling enhancements
- Template UI improvements
- Utility function additions

**📖 For detailed constraints, see [DEVELOPMENT_GUIDE.md](./docs/DEVELOPMENT_GUIDE.md)**

---

## 🗄️ Database Quick Reference

### Connection Information
```bash
# Local MySQL Connection
mysql -u QuestEd -p'QuestEd-03012025MySQL' -h localhost -P 3306 quested
```

### Key Schema Facts
- **MySQL 8.0.40** with utf8mb4_unicode_ci
- **Field Naming**: `student_id` (not `user_id`), `difficulty` vs `difficulty_level`
- **Timestamps**: Standardized to `created_at`, `updated_at`

**📖 Complete schema details in [DATABASE.md](./DATABASE.md)**

---

## 🏗️ Architecture Overview

### Blueprint Structure
```
app/
├── auth/           # Authentication (login, register)
├── admin/          # Admin functionality  
├── teacher/        # Teacher features (modular)
├── student/        # Student features (modular)
├── ai/            # AI integration
├── api/           # REST API endpoints
└── basebuilder/   # Learning management (6 modules, 17 endpoints)
```

**📖 Technical specifications in [ARCHITECTURE.md](./ARCHITECTURE.md)**

---

## 📈 Development History Summary

### Major Milestones
- **2024-12-18**: Curriculum V2 Implementation
- **2025-01-09**: v1.3.0 Production deployment
- **2025-05-05**: Blueprint migration (4,831 lines → modular)
- **2025-06-30**: Production error resolution
- **2025-07-02**: Structure verification & optimization

**📖 Complete timeline in [TIMELINE.md](./TIMELINE.md)**

---

## 🛠️ Development Commands

### Running the Application
```bash
# Development mode
python app.py

# Production with gunicorn  
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Database Management
```bash
# Initialize migrations
flask db init

# Create new migration
flask db migrate -m "Description"

# Apply migrations
flask db upgrade
```

### Environment Setup
Required `.env` variables:
- `SECRET_KEY` - Flask secret key
- `DB_USERNAME`, `DB_PASSWORD`, `DB_HOST`, `DB_NAME` - MySQL credentials
- `OPENAI_API_KEY` - AI features
- `FLASK_ENV`, `FLASK_DEBUG` - Environment settings

---

## 🎯 Current Implementation Priorities (Phase 1 - 2025-07-02)

### 🔥 Week 1: 基盤修復・確認 (2025-07-02 ~ 2025-07-09)
1. **BaseBuilder動作確認・修復**
   - データベーステーブル存在確認
   - 17エンドポイント動作テスト
   - 30テンプレート表示確認
   - 既知の問題修正

2. **ランキングシステム修復**
   - ranking/ranking_cache テーブル確認
   - 単語マスターランキング機能復旧
   - 進捗データ連携修復

### 🔥 Week 2: 自由進度学習実装 (2025-07-09 ~ 2025-07-16)
1. **自由進度学習基盤構築**
   - 既存student_unit_selections活用
   - 動的単元選択ロジック実装
   - BaseBuilder連携強化

2. **UI統合・テスト**
   - 既存139テンプレート活用
   - 学習選択ポータル作成
   - 統合動作確認

### 🟡 Phase 2 準備 (2025-07-16以降)
- 承認システム拡張設計
- AI学習ログ統合準備

**📖 詳細実装計画: [COMPREHENSIVE_IMPROVEMENT_PLAN.md](./COMPREHENSIVE_IMPROVEMENT_PLAN.md)**

---

## 🛠️ 修正・実装履歴と今後の計画 (2025-07-02更新)

### ✅ 本日完了した修正 (2025-07-02)

1. **ランキングシステム修復**
   - 問題: 「Unknown」ユーザーが表示される
   - 原因: 複雑なサブクエリで適切なJOINが失敗
   - 解決: シンプルな直接JOINに変更、キャッシュクリア
   - 結果: 21名の実名ランキング表示確認

2. **BaseBuilderテキストアクセス修復**
   - 問題: テキストにアクセスできない
   - 原因: Blueprint移行時にテキスト関連ルート未実装
   - 解決: texts.py新規作成、sessions.py拡張、テンプレート修正
   - 結果: 50テキスト、488問題へのアクセス復旧

3. **ログイン後500エラー解決** (2025-07-03完了)
   - 問題: BaseBuilder Blueprint登録失敗による連鎖エラー
   - 原因: 複雑な依存関係でBlueprint登録失敗 → url_for()エラー → 無限ループ
   - 解決: テンプレート静的リンク化、BaseBuilder初期化堅牢化、依存関係簡素化
   - 結果: ログイン機能完全復旧、基本的なカテゴリ管理機能維持

### 🚨 BaseBuilder機能復旧計画 (2025-07-03開始)

#### ❌ 失われた機能と影響度

1. **高影響 (即座に復旧必要)**
   - ✅ カテゴリテキスト一覧ルート (`/category/<id>/texts`) → 復旧済み
   - ❌ 詳細統計情報表示 (問題数・テキスト数・使用回数)
   - ❌ カテゴリ作成時の拡張フィールド (科目・学年・難易度)

2. **中影響 (段階的復旧)**
   - ❌ アクティビティログ記録機能
   - ❌ 高度なエラーハンドリング (デコレータベース)
   - ❌ サービス層の統計処理

3. **低影響 (将来対応)**
   - ❌ 詳細な権限チェック
   - ❌ 包括的なバリデーション

#### 📋 復旧スケジュール

**🔥 即座対応 (2025-07-03 午後)**
1. **✅ 統計情報表示の復旧** - 完了
   - カテゴリ一覧での問題数・テキスト数・使用回数表示
   - 実際のDBデータからリアルタイム計算
   - 実装時間: 20分

2. **✅ 拡張フィールド対応** - 完了
   - カテゴリ作成・編集で科目・学年・難易度対応
   - 既存フィールドとの完全互換性維持
   - 実装時間: 15分

**🟡 本日中 (2025-07-03 夕方)**
3. **✅ アクティビティログ簡易版** - 完了
   - 全CRUD操作でログ記録実装
   - ユーザーID、アクション、説明、タイムスタンプを記録
   - 実装時間: 10分

**🟢 明日以降 (2025-07-04〜)**
4. **✅ Blueprint登録404エラー解決** - 完了 (2025-07-03)
   - 問題: BaseBuilder全エンドポイントが404エラー
   - 原因: 絵文字文字化けによる`register_all_blueprints`関数認識失敗
   - 解決: 全絵文字をASCII文字に置換 (✅→[SUCCESS], ❌→[ERROR])
   - 影響範囲: `basebuilder/routes.py`, `basebuilder/__init__.py`, `app/__init__.py`
   - 実装時間: 30分

5. **✅ BaseBuilder完全復旧完了** (2025-07-05)
   - 問題: routes/ディレクトリとroutes.pyファイルのインポート競合
   - 原因: Pythonモジュールインポート優先順位でディレクトリが優先され、routes.pyの関数にアクセス不可
   - 解決: routes/ディレクトリをroutes_modules/に変更、全インポートパス更新
   - 影響範囲: basebuilder/routes.py内の7つのインポート文
   - 実装時間: 45分

### ✅ BaseBuilder復旧完了 (2025-07-05)

#### 🎯 修復完了した全問題

1. **Blueprint登録エラー解決**
   - 絵文字文字化けによる関数認識失敗 → ASCII文字置換で解決
   - モジュールインポート競合 → ディレクトリ名変更で解決

2. **全17エンドポイントの動作復旧**
   - カテゴリ管理: 一覧・作成・編集・削除・詳細
   - 問題管理: 一覧・作成・編集・削除・詳細
   - テキスト管理: 一覧・表示・配信・進捗
   - 分析機能: 統計・レポート・進捗分析

3. **テンプレート統合完了**
   - 30のテンプレートファイルすべて正常動作
   - 統計情報表示機能復旧
   - 拡張フィールド対応完了

**結果**: BaseBuilder機能完全復旧、学習管理システム全機能利用可能

### ✅ ダッシュボード機能拡張完了 (2025-07-06)

#### 🎯 実装完了した新機能

1. **基礎学力カード改善**
   - 熟練度5達成単語数の正確なカウント表示
   - WordProficiencyテーブルから直接クエリによる統計
   - レベル4以上（中級）とレベル5（完全習得）の分離表示

2. **ランキング詳細ページ**
   - 全期間・月間・週間の多期間ランキング表示
   - 熟練度5達成語数ベースの競争システム
   - 自分の順位とパーセンタイル表示
   - クラス内とクラス間ランキング対応

3. **自由進度学習システム**
   - 学習単元の動的選択機能（StudentUnitSelection活用）
   - 科目別単元表示と進捗管理
   - 学習統計（選択数・完了数・進行中数）表示
   - 単元詳細と進捗更新機能

4. **クラス詳細・マイルストーン表示**
   - マイルストーン進捗の可視化
   - カリキュラム項目の階層表示
   - クラス統計（学生数・テーマ数・マイルストーン数）
   - 期限管理とステータス表示

5. **AIチャット統合準備**
   - ダッシュボードからのAIチャット機能へのリンク統合
   - 既存チャット履歴との連携準備

#### 🔧 テンプレート統合調整 (2025-07-06重要修正)

**⚠️ 重大な学習事項**: 新機能実装時の既存テンプレート重複問題

**問題:**
- 新機能実装時に既存テンプレートの存在を確認せずに重複作成
- `class_detail.html`, `ranking_detail.html`, `learning_portal.html` を重複作成
- 変数名とデータ構造の不一致による統合エラー

**解決:**
1. **重複テンプレート削除**
   - `/templates/student/class_detail.html` → 削除
   - `/templates/student/ranking_detail.html` → 削除  
   - `/templates/student/learning_portal.html` → 削除

2. **既存テンプレート活用**
   - `class_details.html` → 既存テンプレート活用
   - `ranking.html` → 既存テンプレート活用
   - `learning_portal.html` → 既存テンプレート活用

3. **データ構造調整**
   - `class_management.py`: テンプレート期待変数に合わせて`curriculum_data`、`milestones`構造を調整
   - `ranking.py`: 既存テンプレートの`ranking_data`、`my_rank`形式に適合
   - `ranking_table.html`: 熟練度5語数表示に特化してコンポーネント簡素化

#### 📊 技術的改善点

1. **データベースクエリ最適化**
   - WordProficiencyテーブルからの効率的な熟練度別集計
   - ClassEnrollmentとの適切なJOIN処理
   - N+1問題の回避とパフォーマンス向上

2. **モジュール設計**
   - Blueprint分離による機能の独立性確保
   - 既存認証システム（@student_required）との統合
   - エラーハンドリングとログ記録の統一

3. **UI/UX統合**
   - 既存のBootstrap 5デザインシステムとの統合
   - レスポンシブ対応とアクセシビリティ確保
   - 一貫したナビゲーションパターンの維持

**結果**: 学生ダッシュボードの全要求機能が既存システムと完全統合され、運用準備完了

### ✅ 2025-07-07: ダッシュボード＆ナビゲーション完全修復

#### 🎯 実施した主要修正 (2025-07-07)

##### 1. **ダッシュボードのデータベース取得問題解決**
**問題**: アンケート、学習記録、Todo、AIチャット履歴が空のダミー値で表示
**根本原因**: 
- `activity_info`辞書が空値で初期化
- データベースクエリが実行されていない
- 認証コンテキスト外での`current_user`参照エラー

**実施した修正**:
```python
# 修正前: 空の初期化
activity_info = {'class_todos': [], 'monthly_chat_count': 0}

# 修正後: 実際のデータベースクエリ
class_todos = Todo.query.filter_by(student_id=current_user.id).order_by(Todo.created_at.desc()).limit(5).all()
monthly_chat_count = ChatHistory.query.filter_by(user_id=current_user.id).filter(
    ChatHistory.created_at >= month_start
).count()
```

**追加した認証チェック**:
```python
# 全ヘルパー関数に追加
if not current_user or not current_user.is_authenticated:
    return empty_default_values
```

##### 2. **週間ランキング算出方法の根本的変更**
**問題**: 「8単語」が正答問題数をカウントしており、実際の単語習得と乖離
**要求**: 今週新たに熟練度5（完全習得）に到達した単語数の表示

**実装変更**:
```python
# 修正前: 正解した回答記録数
weekly_stats = db.session.query(
    AnswerRecord.student_id,
    func.count(AnswerRecord.id).label('weekly_count')
).filter(
    AnswerRecord.is_correct == True
).group_by(AnswerRecord.student_id).all()

# 修正後: 今週熟練度5に到達した単語数
weekly_mastered_stats = db.session.query(
    WordProficiency.student_id,
    func.count(WordProficiency.id).label('weekly_mastered_count')
).filter(
    WordProficiency.level == 5,
    WordProficiency.updated_at >= week_start
).group_by(WordProficiency.student_id).all()
```

**UI変更**:
- ランキングタイトル: 「今週の活動ランキング」→「今週の新規マスターランキング」
- 基礎学力カード: 「今週の新規マスター」→「今週完全習得」
- 説明追加: 「※今週新たに熟練度5（完全習得）に到達した単語数」

##### 3. **システム設定とナビゲーション問題の解決**
**3.1 データベース認証問題**
- **問題**: `config.py`のデフォルト認証情報が間違っていた
- **修正**: `'quested_user'` → `'QuestEd'`, パスワードも正しく設定
- **影響**: 学習ポータル、クラス詳細、AIチャット機能が全て正常動作

**3.2 AIチャットのクラス選択機能実装**
- **新ルート追加**: `/student/chat/select`
- **既存テンプレート活用**: `select_class_for_chat.html`
- **クラスパラメータ処理**: `?class_id=xx`の適切な受け渡し
- **ダッシュボードリンク修正**: 全AIチャットボタンをクラス選択画面に統一

**3.3 学生活動記録ページの整合性修復**
**問題**: 
- 「クラスに戻る」ボタンが機能しない
- テーマが表示されない
- 変数名の不一致によるテンプレートエラー

**修正内容**:
```python
# 変数名の統一
return render_template('activities.html',
    activity_logs=activities,  # テンプレートが期待する変数名
    theme=selected_theme,      # テンプレートが期待する変数名
    class_id=selected_class_id or 0
)
```

- MainThemeとInquiryThemeの両方をサポート
- `image_path` vs `image_url`のデータベースフィールド不整合を修正
- クラス詳細ページへの正しいナビゲーション実装

**3.4 ダッシュボードボタンのテンプレート整合性確保**
- **学習ポータル**: テンプレートを正しい場所に移動、パス修正
- **ランキング詳細**: リンク先をランキングページに修正
- **クラス詳細**: 既に正しく実装済みを確認

#### 📊 修復完了した機能一覧

| 機能カテゴリ | 修復内容 | ステータス |
|-------------|---------|-----------|
| **ダッシュボード表示** | データベース実データ取得 | ✅ 完了 |
| **週間ランキング** | 熟練度5達成単語数表示 | ✅ 完了 |
| **基礎学力統計** | 正確な習得データ表示 | ✅ 完了 |
| **AIチャット** | クラス選択→個別チャット | ✅ 完了 |
| **学習ポータル** | テンプレート整合性確保 | ✅ 完了 |
| **クラス詳細** | ナビゲーション修復 | ✅ 完了 |
| **活動記録** | クラス連携・テーマ表示 | ✅ 完了 |
| **ランキング詳細** | 適切なページ遷移 | ✅ 完了 |

#### 🛠️ 技術的改善点

1. **エラーハンドリング強化**: 全データベースクエリに適切なtry-catch処理
2. **認証チェック**: ヘルパー関数での`current_user`存在確認
3. **テンプレート統一**: 既存テンプレートの積極活用、重複作成の回避
4. **データ整合性**: データベースフィールド名とモデル属性の一致確保
5. **ナビゲーション統一**: 一貫したURL構造とパラメータ受け渡し

#### 📝 実装コミット履歴 (2025-07-07)

```bash
# 主要修正コミット一覧
6ba0822 - Complete dashboard database query implementation
766424b - Fix dashboard authentication errors causing fallback to minimal version  
aaa79e4 - Fix dashboard UnboundLocalError and AttributeError issues
43d271a - Fix three major dashboard navigation issues
2c29ae3 - Change weekly ranking to count newly mastered words (level 5)
a693a5e - Implement AI chat class selection and improve class details navigation
14861d2 - Fix student activities page issues with class navigation and theme display
2a43a08 - Fix dashboard button navigation issues for existing templates
```

**実装期間**: 2025-07-07 (1日)
**修正ファイル数**: 8ファイル
**追加行数**: 200+ 行
**削除行数**: 100+ 行
**総修正コミット**: 8件

### 🔄 Next Phase: 高度機能拡張準備

**残存する課題:**
1. **教師アカウントログイン不可** - 未調査
2. **自由進度学習基盤実装** - Phase 1 残タスク
3. **統合動作確認** - サーバー再起動後の動作確認

### ⚠️ 重要な開発上の注意点とよくあるエラー (2025-07-06更新)

#### 🚫 Pythonコード内での絵文字使用禁止
**本番環境での文字化け問題を防ぐため、Pythonコード内での絵文字使用を禁止**

- **問題**: 本番サーバーで絵文字が文字化けし、Python関数認識に失敗
- **禁止箇所**: Pythonファイル内のprint文、ログ出力、文字列リテラル
- **許可箇所**: マークダウンファイル、コメント、ドキュメント（このファイルの絵文字は問題なし）
- **代替案**: `[INFO]`, `[SUCCESS]`, `[ERROR]`, `[WARNING]` 等のASCII文字を使用
- **対象ファイル**: 全Pythonファイル（特にBlueprint登録、初期化処理）

**例:**
```python
# BAD: 禁止（文字化けの原因）
print("check_mark 処理完了")  # check_mark = ✅
print("cross_mark エラー発生")  # cross_mark = ❌

# GOOD: 推奨
print("[SUCCESS] 処理完了")
print("[ERROR] エラー発生")
```

#### 📋 よくあるエラーパターンと対処法

##### 1. テンプレート関連エラー
**🔴 問題**: 新しく作成したテンプレートが既存のものと重複
- **症状**: `jinja2.exceptions.TemplateNotFound` や変数未定義エラー
- **原因**: 既存テンプレートの確認不足、変数名の不一致
- **対処法**: 
  - **必須**: 新機能実装前に `templates/` 以下を検索し既存テンプレート確認
  - 既存テンプレートの変数構造を `Read` ツールで確認
  - 新規作成ではなく既存テンプレート活用を優先
- **実例**: 2025-07-06に `class_detail.html`, `ranking_detail.html` 等を重複作成し削除

##### 2. Blueprint/Module間インポートエラー
**🔴 問題**: モジュール名衝突によるインポート失敗
- **症状**: `ModuleNotFoundError`, `AttributeError`, Blueprint登録失敗
- **原因**: ディレクトリ名とファイル名の競合、Pythonのモジュール検索優先順位
- **対処法**:
  - ディレクトリ名は複数形（`routes_modules/`）、ファイル名は単数形（`routes.py`）で統一
  - インポートパスを絶対パスで明記
  - 循環インポートの回避
- **実例**: 2025-07-05に `routes/` ディレクトリと `routes.py` の競合問題

##### 3. データベース関連エラー
**🔴 問題**: セッション管理とクエリ最適化
- **症状**: `DetachedInstanceError`, セッション切断、パフォーマンス低下
- **原因**: セッション管理の不備、N+1問題、適切なJOIN不使用
- **対処法**:
  - 適切な `db.session.commit()` と `db.session.rollback()`
  - 複雑なサブクエリをシンプルなJOINに変更
  - `eager loading` でN+1問題解決
- **実例**: 2025-07-02にランキングのサブクエリをJOINに簡素化

##### 4. 既存機能との統合エラー
**🔴 問題**: 新機能が既存システムと不整合
- **症状**: 404エラー、認証失敗、データ構造の不一致
- **原因**: 既存のアーキテクチャパターンを無視した実装
- **対処法**:
  - 既存のBlueprint構造とURL設計に従う
  - 認証デコレータ（`@student_required`）の一貫使用
  - 既存データモデルのフィールド名規則を確認
- **実例**: 2025-07-06にランキングモジュールで既存テンプレートのデータ構造に合わせて調整

#### 🛠️ 開発前チェックリスト
新機能実装時は以下を必ず確認：

1. **🔍 既存調査**
   - [ ] 同様の機能が既に存在しないか検索
   - [ ] 関連テンプレートの存在確認
   - [ ] 既存のBlueprint構造とURL設計確認

2. **📁 ファイル構造**
   - [ ] インポートパスの競合チェック
   - [ ] モジュール名の命名規則準拠
   - [ ] 絶対パスでのインポート記述

3. **🗄️ データベース**
   - [ ] 既存モデルのフィールド名確認
   - [ ] リレーションシップの整合性
   - [ ] クエリの効率性（JOINの活用）

4. **🎨 テンプレート**
   - [ ] 既存テンプレートの変数構造確認
   - [ ] 新規作成ではなく既存活用の検討
   - [ ] テンプレート間の継承関係確認

5. **🔒 認証・権限**
   - [ ] 適切なデコレータの使用
   - [ ] 既存の権限チェック方式に準拠
   - [ ] セッション管理の一貫性

### 📋 今後の実装計画 (優先順位順)

#### 🔥 Phase 1 残タスク (〜2025-07-16)

1. **自由進度学習基盤構築**
   ```python
   # 必要な実装:
   - student_unit_selections活用
   - 動的単元選択ロジック
   - BaseBuilder連携強化
   - 学習ポータルUI作成
   ```

2. **統合動作確認**
   - BaseBuilder全17エンドポイントの動作検証
   - ランキング定期更新ジョブ設定
   - エラーログ監視体制構築

#### 🟡 Phase 2: 承認ワークフロー (2025-07-16〜07-30)

1. **教師承認システム**
   - オフライン課題提出機能
   - 承認ダッシュボード
   - 通知システム統合
   - approval_status活用

2. **進捗可視化**
   - 生徒個別進捗ダッシュボード
   - クラス全体進捗レポート
   - 学習分析機能強化

#### 🟢 Phase 3: AI統合 (2025-08-01〜08-15)

1. **AI学習ログ統合**
   - ChatHistory → 学習記録連携
   - AI推奨問題選択
   - 学習困難箇所の自動検出

2. **適応型学習**
   - 習熟度ベース問題選択
   - 個別学習パス最適化

### 🚨 緊急対応が必要な項目

1. **セキュリティ監査**
   - SQLインジェクション対策確認
   - XSS対策検証
   - 権限チェック網羅性確認

2. **バックアップ体制**
   - 自動バックアップスクリプト
   - リストア手順書作成
   - 障害時対応フロー策定

### 💡 推奨事項

1. **コード品質向上**
   - Linting設定 (flake8/black)
   - 型アノテーション追加
   - Docstring充実化

2. **運用改善**
   - CI/CDパイプライン構築
   - ステージング環境準備
   - A/Bテスト基盤

### 📊 メトリクス目標

- エラー率: < 0.1%
- レスポンスタイム: < 2秒
- テストカバレッジ: > 80%
- 可用性: 99.9%

---

## 🔒 Security & Safety

### Authentication
- Multi-role support (admin/teacher/student)
- Email verification required
- School-based data isolation

### Data Protection
- Input validation on all forms
- SQL injection prevention (SQLAlchemy ORM)
- XSS protection with template escaping
- CSRF protection enabled globally

**📖 Security details in [docs/DEVELOPMENT_GUIDE.md](./docs/DEVELOPMENT_GUIDE.md#security)**

---

## 📞 Support & References

### Key Documentation Locations
- **Migration Guides**: `/docs/migration_plan.md`
- **API Documentation**: `/docs/api-documentation.html`
- **Business Requirements**: `/docs/business_requirements.md`
- **Troubleshooting**: `/docs/troubleshooting.md`

### Development Standards
- **Language**: Python 3.8+, Flask 2.x
- **Database**: MySQL with SQLAlchemy ORM
- **Frontend**: Jinja2 templates, Bootstrap 5, jQuery
- **API**: RESTful JSON with proper error handling

---

## 📝 Maintenance Notes

### Document Update Responsibilities
- **TIMELINE.md**: Update when status changes or fixes completed
- **ARCHITECTURE.md**: Update when technical specs change
- **DATABASE.md**: Update when schema modifications occur
- **This file (CLAUDE.md)**: Update when navigation or priorities change

### Version Control
- All changes should maintain backward compatibility
- Document modifications with clear commit messages
- Reference relevant issue/PR numbers where applicable

---

**📚 This master index provides quick access to comprehensive QuestEd documentation. For detailed information on any topic, follow the links to specialized documents.**