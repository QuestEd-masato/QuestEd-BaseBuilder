# Curriculum Migration Adapter 仕様書

## 目的
curriculum_data (JSON) から curriculum_lessons (テーブル) への段階的移行を実現する中間層

## 設計原則
1. **収束的改善**: 2つのデータソースを1つに統一
2. **後方互換性**: 既存コードを壊さない
3. **段階的移行**: 一度に全部変更しない
4. **最小限の新規作成**: このアダプター1ファイルのみ

## 実装フェーズ

### Phase 4: アダプター基本実装
```python
# app/services/curriculum/migration_adapter.py

class CurriculumMigrationAdapter:
    """段階的移行のための統一インターフェース"""
    
    # 読み取り: curriculum_lessons優先、curriculum_dataフォールバック
    @classmethod
    def read_curriculum_content(cls, curriculum_id: int) -> dict
    
    # 書き込み: 両方に書き込み（後方互換性維持）
    @classmethod
    def write_curriculum_content(cls, curriculum_id: int, content: dict) -> bool
```

### Phase 5: 既存コードの段階的置き換え

#### Step 1: 読み取り専用ファイルから移行
- curriculum_validation_service.py
- curriculum_import_export_service.py

#### Step 2: 読み書きファイルの移行
- curriculum_data_service.py
- unified_curriculum_service.py

#### Step 3: 危険ファイルの慎重な移行
- app/student/modules/learning.py (両方使用)

### Phase 6: 同期サービスの無効化
```python
# config.py
ENABLE_CURRICULUM_DATA_SYNC = False  # JSONとテーブルの同期を無効化
```

### Phase 7: curriculum_dataカラムの廃止
```sql
-- 最終段階でのみ実行
ALTER TABLE curriculums DROP COLUMN curriculum_data;
```

## リスク管理

### ロールバック手順
各フェーズで以下の手順でロールバック可能：
1. アダプターを無効化
2. 元のコードに戻す
3. データ整合性を確認

### データ整合性チェック
```python
def verify_data_consistency(curriculum_id: int) -> bool:
    """データ整合性を確認"""
    json_data = read_from_curriculum_data(curriculum_id)
    table_data = read_from_curriculum_lessons(curriculum_id)
    return compare_data(json_data, table_data)
```

## 期待効果
- コード量: 30%削減（同期サービス5つ → 0）
- パフォーマンス: 40%改善（JSON解析不要）
- 保守性: 大幅向上（単一データソース）