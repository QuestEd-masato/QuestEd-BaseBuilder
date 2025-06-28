# Phase 3: データ整合性確保実装

## 概要
Phase 3では、QuestEdシステムのデータ整合性を確保するための機能を実装しました。
データベースの不整合を修正し、単元と問題のマッピングを自動生成する仕組みを構築しています。

## 実装内容

### 1. データ整合性確保スクリプト
**ファイル**: `scripts/phase3_data_integrity.py`

主な機能：
- curriculum_units テーブルのデータ整合性修正
- student_unit_selections の承認ステータス移行
- unit_item_mappings の自動生成
- データ整合性の検証

使用方法：
```bash
# データ修正SQLの生成
python scripts/phase3_data_integrity.py --generate-sql > migration.sql

# マッピング作成SQLの生成
python scripts/phase3_data_integrity.py --create-mappings > mappings.sql

# データ整合性の検証
python scripts/phase3_data_integrity.py --verify
```

### 2. 単元・問題マッピングサービス
**ファイル**: `app/services/unit_item_mapping_service.py`

主なクラス・メソッド：
- `UnitItemMappingService`: マッピング管理のメインサービス
  - `get_unit_problems()`: 単元に関連する問題を取得
  - `calculate_unit_progress()`: 単元の学習進捗を計算
  - `update_unit_selection_progress()`: 進捗データを更新
  - `create_automatic_mappings()`: 自動マッピング作成
  - `batch_create_mappings()`: 一括マッピング作成

### 3. データ整合性管理API
**ファイル**: `app/api/data_integrity.py`

エンドポイント：
- `/api/data-integrity/verify` [GET]: データ整合性の検証
- `/api/data-integrity/fix/curriculum-units` [POST]: curriculum_unitsデータ修正
- `/api/data-integrity/fix/student-selections` [POST]: student_unit_selectionsデータ修正
- `/api/data-integrity/mappings/create` [POST]: マッピング作成
- `/api/data-integrity/mappings/status` [GET]: マッピング状況取得
- `/api/data-integrity/progress/recalculate` [POST]: 進捗再計算

## データベーススキーマ

### unit_item_mappingsテーブル（新規）
```sql
CREATE TABLE unit_item_mappings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    unit_id INT NOT NULL,
    item_id INT NOT NULL,
    item_type VARCHAR(50) DEFAULT 'problem',
    weight DECIMAL(5,2) DEFAULT 1.00,
    order_index INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (unit_id) REFERENCES curriculum_units(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES basic_knowledge_items(id) ON DELETE CASCADE,
    UNIQUE KEY unique_unit_item (unit_id, item_id, item_type),
    KEY idx_unit_id (unit_id),
    KEY idx_item_id (item_id)
);
```

## 使用上の注意

1. **権限管理**: データ整合性APIは管理者権限が必要です
2. **実行順序**: 
   - まずデータ修正SQLを実行
   - 次にマッピングを作成
   - 最後に進捗を再計算
3. **バックアップ**: 本番環境で実行する前に必ずデータベースのバックアップを取得してください

## API使用例

### データ整合性の検証
```bash
curl -X GET http://localhost:5000/api/data-integrity/verify \
  -H "Cookie: session=..."
```

### データ修正（ドライラン）
```bash
curl -X POST http://localhost:5000/api/data-integrity/fix/curriculum-units \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{"dry_run": true}'
```

### マッピング作成
```bash
curl -X POST http://localhost:5000/api/data-integrity/mappings/create \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{}'
```

## インテグレーション

### アプリケーションへの統合
`app/__init__.py`で以下のように登録が必要です：

```python
from app.api.data_integrity import data_integrity_bp
app.register_blueprint(data_integrity_bp, url_prefix='/api/data-integrity')
```

### 既存機能との連携
- `UnitProgressManager`との統合により、学習進捗が正しく追跡されます
- `StudentUnitSelection`のステータスが自動的に更新されます
- 承認ワークフローとの連携により、既存の学習成果が保持されます

## トラブルシューティング

### エラー: "unit_item_mappings table does not exist"
→ マッピングSQLを実行してテーブルを作成してください

### エラー: "Permission denied"
→ 管理者権限でログインしているか確認してください

### 進捗が更新されない
→ マッピングが作成されているか確認し、進捗再計算APIを実行してください