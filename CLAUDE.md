# QuestEd Development Reference - Master Index

*📅 Last Updated: 2025-07-02 | Status: ✅ Production Operational*

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
- **Application Layer**: 🔄 実装・修復進行中
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
4. **高度なエラーハンドリング復旧**
5. **完全なサービス層再構築**

### 🔄 残存する技術的課題

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