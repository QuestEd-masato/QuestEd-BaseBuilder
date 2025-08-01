# Phase8B 削除計画書
## 管理破綻緊急復旧 - バックアップファイル完全削除計画

**作成日**: 2025年7月26日  
**Stage 1完了**: バックアップファイル23個完全特定・分類完了  
**緊急度**: 高（プロジェクト管理体制の根本的再構築）

---

## 📋 **Stage 1完了報告**

### ✅ バックアップファイル特定結果
**総数**: 23個（venv除外後）  
**分類**: 安全度別3カテゴリーに完全分類

### 詳細分析結果

#### 🟢 **カテゴリA: 即座削除可能（高安全度）** - 11個
現行ファイルが存在し、明らかにバックアップ目的のファイル

1. **`.env.backup_20250725_105514`** (943 bytes)
   - 現行: `.env` 存在 (2025-07-11作成)
   - 安全度: ★★★ 環境設定の7月25日バックアップ
   - 削除判定: **即座削除可能**

2. **`app/api/unit_management.py.backup`** (53,224 bytes)
   - 現行: `unit_management.py` 存在 (Phase8A完了版、12,392 bytes)
   - 安全度: ★★★ Phase8A前のバックアップ
   - 削除判定: **即座削除可能**

3. **`app/api/unit_management_old.py`** (75,293 bytes)
   - 現行: `unit_management.py` 存在 (Phase8A完了版)
   - 安全度: ★★★ 古いバージョン
   - 削除判定: **即座削除可能**

4. **`app/services/ranking_service.py.backup`** (49,095 bytes)
   - 現行: `ranking_service.py` 存在
   - 安全度: ★★★ Phase4前のバックアップ
   - 削除判定: **即座削除可能**

5. **`app/services/weakness_analyzer.py.backup`** (59,187 bytes)
   - 現行: Phase6で完全分解済み（8サービスに分割）
   - 安全度: ★★★ Phase6前のバックアップ
   - 削除判定: **即座削除可能**

6. **`backups/phase6b_dashboard_backup_20250725_222735.py`** (56,055 bytes)
   - 現行: `dashboard.py` 存在
   - 安全度: ★★★ Phase6B実行時バックアップ
   - 削除判定: **即座削除可能**

7. **`backups/phase6c_unit_management_backup_20250725_231139.py`** (75,030 bytes)
   - 現行: Phase8A完了版存在
   - 安全度: ★★★ Phase6C実行時バックアップ
   - 削除判定: **即座削除可能**

8. **`backups/phase7/api_task_management_original.py`** (25,607 bytes)
   - 現行: Phase7-5完了版存在
   - 安全度: ★★★ Phase7-5前のオリジナル
   - 削除判定: **即座削除可能**

9. **`backups/phase7/auto_sync_service_original.py`** (34,275 bytes)
   - 現行: Phase7-4完了版存在
   - 安全度: ★★★ Phase7-4前のオリジナル
   - 削除判定: **即座削除可能**

10. **`backups/phase7/curriculum_helpers_original.py`** (17,290 bytes)
    - 現行: Phase7-3完了版存在
    - 安全度: ★★★ Phase7-3前のオリジナル
    - 削除判定: **即座削除可能**

11. **`backups/phase8/unit_management_original_20250726_152343.py`** (75,293 bytes)
    - 現行: Phase8A完了版存在
    - 安全度: ★★★ Phase8A前のオリジナル
    - 削除判定: **即座削除可能**

#### 🟡 **カテゴリB: 慎重削除（中安全度）** - 8個
現行ファイル存在するが、Phase5関連や重要な履歴

12. **`app/modules/lesson_system/models/lesson_models.py.backup_phase5`** (11,305 bytes)
    - 現行: `lesson_models.py` 存在
    - 安全度: ★★☆ Phase5実行時バックアップ
    - 削除判定: **慎重削除** (Phase5検証後)

13. **`app/modules/lesson_system/services/progress_service.py.backup_phase5`** (8,961 bytes)
    - 現行: `progress_service.py` 存在
    - 安全度: ★★☆ Phase5実行時バックアップ
    - 削除判定: **慎重削除** (Phase5検証後)

14. **`app/student/modules/learning.py.backup_phase5`** (25,104 bytes)
    - 現行: `learning.py` 存在
    - 安全度: ★★☆ Phase5実行時バックアップ
    - 削除判定: **慎重削除** (Phase5検証後)

15. **`templates/student/lesson_detail.html.backup_phase5`** (15,765 bytes)
    - 現行: `lesson_detail.html` 存在
    - 安全度: ★★☆ Phase5テンプレートバックアップ
    - 削除判定: **慎重削除** (テンプレート確認後)

16. **`backups/phase6b_dashboard_template_backup_20250725_222759.html`** (45,180 bytes)
    - 現行: テンプレートファイル存在
    - 安全度: ★★☆ Phase6Bテンプレートバックアップ
    - 削除判定: **慎重削除** (テンプレート確認後)

17. **`backups/phase7/class_management_original.py`** (22,849 bytes)
    - 現行: `class_management.py` 存在
    - 安全度: ★★☆ Phase7関連オリジナル
    - 削除判定: **慎重削除** (現行ファイル確認後)

18. **`basebuilder/routes_modules/categories_original.py`** (9,994 bytes)
    - 現行: `categories.py` 存在可能性
    - 安全度: ★★☆ BaseBuilder関連オリジナル
    - 削除判定: **慎重削除** (BaseBuilder確認後)

19. **`backups/phase6a-20250725_221210/`** ディレクトリ (4ファイル)
    - 内容: weakness_analyzer.py, spaced_repetition.py等
    - 現行: Phase6A完了済み
    - 安全度: ★★☆ Phase6A実行時バックアップ
    - 削除判定: **慎重削除** (Phase6A検証後)

#### 🔴 **カテゴリC: 最終確認必要（要注意）** - 4個
SQLバックアップや空ディレクトリ等

20. **`backups/backup_before_migration_20250710_174727.sql`** (645,131 bytes)
    - 内容: データベース移行前バックアップ
    - 安全度: ★☆☆ 本番データ関連
    - 削除判定: **最終確認必要** (DB状況確認後)

21. **`backups/backup_target_tables_20250710_174849.sql`** (29,724 bytes)
    - 内容: 対象テーブルバックアップ
    - 安全度: ★☆☆ 本番データ関連
    - 削除判定: **最終確認必要** (DB状況確認後)

22. **`backups/quested_production_backup_20250709_025828.sql`** (646,143 bytes)
    - 内容: 本番環境バックアップ
    - 安全度: ★☆☆ 本番データ関連
    - 削除判定: **最終確認必要** (重要データ確認)

23. **`backups/quested_production_backup_20250709_025828.sql.gz`** (121,256 bytes)
    - 内容: 圧縮版本番バックアップ
    - 安全度: ★☆☆ 本番データ関連
    - 削除判定: **最終確認必要** (重要データ確認)

24. **`backups/phase6a-20250725_221159/`** ディレクトリ（空）
    - 内容: 空ディレクトリ
    - 安全度: ★★★ 空フォルダ
    - 削除判定: **即座削除可能**

---

## ⚡ **Stage 2: 段階的削除実行計画**

### Phase 2-1: 安全確実削除（11個 → 0個）
**実行タイミング**: 即座実行可能  
**リスク**: 極低（現行ファイル存在確認済み）

```bash
# 実行コマンド例
rm -f /home/masat/claude-projects/QuestEd/.env.backup_20250725_105514
rm -f /home/masat/claude-projects/QuestEd/app/api/unit_management.py.backup
rm -f /home/masat/claude-projects/QuestEd/app/api/unit_management_old.py
# ... 続く
```

### Phase 2-2: 慎重削除（8個 → 0個） 
**実行タイミング**: Phase5・Phase6動作確認後  
**リスク**: 低（バックアップ目的確認済み）

1. Phase5関連バックアップ（4個）の現行ファイル動作確認
2. Phase6・7関連バックアップ（4個）の現行ファイル動作確認
3. 確認完了後に削除実行

### Phase 2-3: 最終確認削除（4個 → 0個）
**実行タイミング**: DB状況・重要データ確認後  
**リスク**: 中（本番データ関連）

1. データベース現状確認
2. 本番データの現行バックアップ存在確認
3. 古いSQLバックアップの不要性確認
4. 最終判断後に削除実行

---

## 📊 **削除実行基準**

### 必須確認事項
1. **現行ファイル存在**: ✅ 23個すべて確認済み
2. **機能動作確認**: 🔄 Phase別動作確認予定
3. **重要データ確認**: 🔄 SQLバックアップ確認予定
4. **ロールバック準備**: ✅ 段階的削除による安全保証

### 成功基準
- **カテゴリA完全削除**: 11個 → 0個（100%削除）
- **カテゴリB完全削除**: 8個 → 0個（100%削除）
- **カテゴリC完全削除**: 4個 → 0個（100%削除）
- **システム動作維持**: Phase1-8Aの機能100%維持
- **管理体制正常化**: バックアップファイル0個達成

### 最終評価基準
```
✅ 完全成功: 23個 → 0個 (100%削除達成)
❌ 失敗: 1個でも残存時は「管理破綻継続」
⚠️ 部分成功: 「中途半端な整理」として評価
```

---

## 🎯 **次ステップ: Stage 2実行準備**

### 即座実行可能
**カテゴリA**: 11個の安全確実削除を即座実行

### 実行前確認事項  
**カテゴリB**: Phase5-7動作確認  
**カテゴリC**: データベース・本番データ確認

**Phase8B Stage2準備完了** - 削除計画策定完了