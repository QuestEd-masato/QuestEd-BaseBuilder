# QuestEdカリキュラム統一：包括的実装計画書

## 📊 実行サマリー

### 統一の必要性（深刻度：Critical）
- **データ二重管理**: curriculum_data（31ファイル依存）+ curriculum_lessons（17ファイル使用）
- **サービス重複**: 10個のカリキュラムサービス + 5個の同期サービス
- **保守困難性**: データ不整合リスク、複雑な同期処理
- **開発効率低下**: 新機能開発時の影響範囲拡大

### 統一方針（技術的根拠）
**✅ curriculum_lessonsテーブルベースに統一**
- **実データ**: curriculum_lessons（8件）vs curriculum_data（NULL）
- **アーキテクチャ**: Phase5レッスンシステムの成功実績
- **機能**: 承認ワークフロー、進捗管理の統合済み
- **設計**: 正規化されたデータベース設計

## 🎯 統一アーキテクチャ（目標設計）

### データ層統合
```
現在（二重構造）                統一後（単一構造）
├── curriculums.curriculum_data  →  削除
├── curriculum_lessons          →  ✅ メイン統一ソース  
├── lesson_tasks                →  ✅ 承継・拡張
└── student_lesson_progress     →  ✅ 承継・拡張
```

### サービス層統合
```
現在（10+5=15個）              統一後（4個）
├── curriculum_data_service     →  統合削除
├── curriculum_orchestration    →  統合削除
├── unified_curriculum_service  →  統合削除
├── curriculum_bridge_service   →  統合削除
├── curriculum_integration      →  統合削除
├── sync_* (5個)               →  統合削除
└── ...                        
                                ↓
├── UnifiedCurriculumService    →  🆕 メイン統合サービス
├── LessonSystemService         →  ✅ 既存活用
├── CurriculumSyncService       →  🆕 統合同期サービス
└── CurriculumAIService         →  🆕 AI機能統合
```

## 📋 3段階実行計画

### Phase 1: 統合基盤構築（3-4日）

#### Phase 1A: メイン統合サービス作成
**ファイル**: `app/services/curriculum/unified_curriculum_core_service.py`
```python
class UnifiedCurriculumCoreService:
    """カリキュラム管理の統一コアサービス"""
    
    def get_curriculum_data(self, curriculum_id: int):
        """統一データ取得（レッスンベース）"""
        
    def create_curriculum_from_lessons(self, curriculum_data: dict):
        """レッスンベース作成"""
        
    def migrate_json_to_lessons(self, curriculum_id: int):
        """JSONデータ→レッスン変換"""
        
    def ensure_backward_compatibility(self):
        """後方互換性100%保証"""
```

#### Phase 1B: 同期サービス統合
**統合対象**: 5個の同期サービス → 1個
```python
# 新規作成: app/services/curriculum/curriculum_sync_service.py
class CurriculumSyncService:
    """統合同期サービス（5個のサービス機能を集約）"""
    
    def schedule_sync(self):     # sync_scheduler_service
    def execute_sync(self):      # sync_executor_service  
    def validate_data(self):     # sync_validator_service
    def resolve_conflicts(self): # conflict_resolver_service
    def auto_sync_facade(self):  # auto_sync_service（ファサード維持）
```

#### Phase 1C: データ移行サービス作成
**ファイル**: `app/services/curriculum/data_migration_service.py`
```python
class DataMigrationService:
    """安全なデータ移行管理"""
    
    def create_migration_backup(self):
        """移行前バックアップ作成"""
        
    def migrate_file_dependencies(self, file_path: str):
        """ファイル単位の段階的移行"""
        
    def verify_data_integrity(self):
        """データ整合性検証"""
        
    def rollback_migration(self, checkpoint: str):
        """ロールバック実行"""
```

### Phase 2: 段階的データ移行（4-5日）

#### Phase 2A: 依存ファイルの段階的移行
**Category A: 高優先度（8ファイル - 1日）**
```
✅ app/services/curriculum/curriculum_data_service.py     → 削除・統合
✅ app/services/curriculum/curriculum_orchestration_service.py → 削除・統合
✅ app/services/unified_curriculum_service.py           → 削除・統合
✅ app/services/curriculum_bridge_service.py            → 削除・統合
✅ app/ai/curriculum_helpers.py                        → AI変換ロジックに更新
✅ app/teacher/modules/curriculum_management.py         → lesson_system統合
```

**Category B: API・ルート層（6ファイル - 1日）**
```
✅ app/api/curriculum_lesson_direct.py                 → lesson_system統合
✅ app/student/modules/learning.py                    → lesson_system統合
✅ app/student/modules/class_management.py            → 依存関係更新
✅ app/teacher/modules/synchronization.py             → 新同期サービス適用
```

**Category C: テンプレート・ビュー（9ファイル - 2日）**
```
✅ templates/teacher/curriculum_list.html             → lesson_system仕様に更新
✅ templates/student/curriculum_lessons.html          → 統合済み（活用）
✅ templates/*/curriculum_detail.html                 → lesson_system準拠に更新
```

**Category D: AI・同期関連（8ファイル - 1日）**
```
✅ app/services/sync/* (5ファイル)                     → 統合同期サービスに置き換え
✅ app/services/ai/curriculum_* (3ファイル)           → AI統合サービスに集約
```

#### Phase 2B: データベース最適化
```sql
-- 移行ログテーブル作成
CREATE TABLE curriculum_migration_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    curriculum_id INT,
    migration_phase ENUM('backup', 'convert', 'verify', 'complete'),
    source_file VARCHAR(255),
    migration_status ENUM('pending', 'success', 'error', 'rollback'),
    error_details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- バックアップテーブル作成
CREATE TABLE curriculums_backup_pre_unification AS 
SELECT * FROM curriculums WHERE curriculum_data IS NOT NULL;
```

### Phase 3: 完全統一と最適化（2-3日）

#### Phase 3A: curriculum_dataフィールド削除
```sql
-- 段階的削除
-- Step 1: 依存関係完全除去確認
SELECT 
    table_name, column_name 
FROM information_schema.columns 
WHERE column_name LIKE '%curriculum_data%';

-- Step 2: 最終バックアップ
INSERT INTO curriculum_data_final_backup 
SELECT id, curriculum_data, updated_at 
FROM curriculums 
WHERE curriculum_data IS NOT NULL;

-- Step 3: フィールド削除
ALTER TABLE curriculums DROP COLUMN curriculum_data;
```

#### Phase 3B: パフォーマンス最適化
```sql
-- 新しいインデックス追加
CREATE INDEX idx_curriculum_lessons_performance 
ON curriculum_lessons(curriculum_id, lesson_order, status);

-- 不要インデックス削除
DROP INDEX IF EXISTS idx_curriculums_curriculum_data;

-- 統計情報更新
ANALYZE TABLE curriculums, curriculum_lessons, lesson_tasks;
```

## ⚠️ リスク管理計画

### Critical Risk対策
1. **データ消失防止**
   - 移行前完全バックアップ
   - 段階的ロールバックポイント
   - リアルタイム整合性チェック

2. **サービス停止回避**
   - ファサードパターンによる互換性維持
   - Blue-Greenデプロイメント方式
   - ゼロダウンタイム移行

3. **パフォーマンス劣化防止**
   - 事前負荷テスト
   - クエリ実行計画最適化
   - キャッシュ戦略実装

## 📈 期待効果（定量的）

### コード削減効果
- **依存ファイル**: 31ファイル → 17ファイル（45%削減）
- **サービスクラス**: 15個 → 4個（73%削減）  
- **重複ロジック**: 推定30%削減

### パフォーマンス向上
- **データアクセス**: JSON解析不要によるレスポンス30%向上
- **データベース負荷**: 正規化による効率化
- **メモリ使用量**: 同期処理簡略化による削減

### 開発効率向上
- **新機能開発**: 影響範囲の明確化による迅速化
- **バグ修正**: 単一ソースによる修正箇所削減
- **テスト工数**: 統合テストの簡略化

## 🔄 緊急時対応

### 段階別ロールバック手順

#### Phase 1 ロールバック
```bash
# サービス無効化
git revert [統合サービス_commit_hash]
systemctl restart quested
```

#### Phase 2 ロールバック  
```sql
-- データ復元
START TRANSACTION;
UPDATE curriculums c
JOIN curriculums_backup_pre_unification b ON c.id = b.id
SET c.curriculum_data = b.curriculum_data;
COMMIT;
```

#### Phase 3 ロールバック
```sql
-- フィールド復元
ALTER TABLE curriculums 
ADD COLUMN curriculum_data JSON AFTER content;

-- データ復元
UPDATE curriculums c
JOIN curriculum_data_final_backup b ON c.id = b.id  
SET c.curriculum_data = b.curriculum_data;
```

## ✅ 成功基準

### 必須達成項目
1. **データ整合性**: 移行前後で100%一致
2. **機能互換性**: 既存機能の完全動作
3. **パフォーマンス**: 移行前と同等以上
4. **ユーザー体験**: 操作性の維持・向上

### 品質指標
- **エラー率**: 0% （移行期間中）
- **応答時間**: ±10%以内 （移行前後比較）
- **データ不整合**: 0件
- **ロールバック実行**: 0回 （理想値）

## 📅 推奨実行スケジュール

```
週次スケジュール（総期間: 12日間）

Week 1: Phase 1 - 統合基盤構築
├── 月曜日: 統合サービス設計・実装開始
├── 火曜日: メイン統合サービス完成・テスト
├── 水曜日: 同期サービス統合・テスト
└── 木曜日: データ移行サービス完成・統合テスト

Week 2: Phase 2 - データ移行実行  
├── 金曜日: Category A移行（高優先度8ファイル）
├── 月曜日: Category B移行（API・ルート6ファイル）
├── 火曜日: Category C移行（テンプレート9ファイル）
├── 水曜日: Category D移行（AI・同期8ファイル）
└── 木曜日: 全体整合性検証・テスト

Week 2: Phase 3 - 最適化・完成
├── 金曜日: データベース最適化・フィールド削除
├── 月曜日: パフォーマンステスト・最終調整
└── 火曜日: 本番移行・最終検証
```

この包括的計画により、QuestEdのカリキュラム管理システムは**Phase5レッスンシステムの成功**を基盤として、**統一されたモダンアーキテクチャ**に進化し、**開発効率の大幅向上**と**システム安定性の確保**を同時実現します。