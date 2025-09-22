# 🗄️ データベース最適化計画 - QuestEd

## 📊 現状分析結果

### **データベース構成状況**
- **総テーブル数**: 約50個
- **総データサイズ**: 約2MB
- **最大テーブル**: answer_records (3,953レコード, 0.42MB)
- **アクティブユーザー**: 46ユーザー（開発アカウント3個含む）

### **発見された最適化対象**

#### **カテゴリA: 安全削除対象（即座実行可能）**
1. **バックアップテーブル**: 3個のバックアップテーブル
2. **開発アカウント**: 3個のテスト用ユーザーアカウント
3. **孤立レコード**: 0個（良好な整合性）

#### **カテゴリB: 慎重検討対象**
1. **大容量テーブル**: answer_records (3,953レコード)
2. **レガシーテーブル**: word_proficiency_records_backup_*
3. **未使用カラム**: curriculum_units の拡張カラム群

---

## 🎯 優先度2: データベース最適化詳細計画

### **Phase 1: 軽微クリーンアップ（低リスク）**

#### **1-1: バックアップテーブル削除**
```sql
-- バックアップテーブル特定・削除
DROP TABLE IF EXISTS word_proficiency_records_backup_20250623_002108;

-- 実行前確認
SELECT TABLE_NAME, TABLE_ROWS, 
       ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as size_mb
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'quested' AND TABLE_NAME LIKE '%backup%';
```

**期待効果**: 0.06MB削減、テーブル数削減

#### **1-2: 開発アカウント削除**
```sql
-- 開発アカウント特定
SELECT id, username, email, created_at
FROM users 
WHERE email LIKE '%test%' OR email LIKE '%dev%' OR username LIKE '%test%';

-- 関連データ確認（削除前に要確認）
SELECT 'activity_logs', COUNT(*) FROM activity_logs WHERE student_id IN (開発アカウントID);
SELECT 'answer_records', COUNT(*) FROM answer_records WHERE student_id IN (開発アカウントID);

-- 安全削除（外部キー制約により関連データも自動削除）
DELETE FROM users WHERE id IN (開発アカウントID);
```

**期待効果**: 整合性向上、管理簡素化

#### **1-3: 未使用インデックス最適化**
```sql
-- 低使用頻度インデックスの特定
SELECT 
    TABLE_NAME, INDEX_NAME, CARDINALITY,
    CASE 
        WHEN CARDINALITY = 0 THEN 'unused'
        WHEN CARDINALITY < 10 THEN 'low_usage'
        ELSE 'normal'
    END as usage_level
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = 'quested' AND NON_UNIQUE = 1;

-- 必要に応じてインデックス削除（慎重に）
-- DROP INDEX index_name ON table_name;
```

**期待効果**: わずかなパフォーマンス向上

### **Phase 2: 中規模最適化（中リスク）**

#### **2-1: 未使用カラム調査・削除**
```sql
-- curriculum_units の拡張カラム使用状況確認
SELECT 
    mastery_threshold, self_paced_mode, prerequisite_skills,
    COUNT(*) as usage_count
FROM curriculum_units 
WHERE mastery_threshold IS NOT NULL 
   OR self_paced_mode IS NOT NULL 
   OR prerequisite_skills IS NOT NULL;

-- 使用されていない場合の削除検討
-- ALTER TABLE curriculum_units 
-- DROP COLUMN mastery_threshold,
-- DROP COLUMN self_paced_mode, 
-- DROP COLUMN prerequisite_skills;
```

**期待効果**: スキーマ簡素化、保守性向上

#### **2-2: 大容量テーブル最適化**
```sql
-- answer_records の最適化検討
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT student_id) as unique_students,
    COUNT(DISTINCT problem_id) as unique_problems,
    MIN(created_at) as oldest_record,
    MAX(created_at) as newest_record
FROM answer_records;

-- 古いデータのアーカイブ検討（6ヶ月以上前）
-- CREATE TABLE answer_records_archive AS 
-- SELECT * FROM answer_records WHERE created_at < '2024-08-01';
-- DELETE FROM answer_records WHERE created_at < '2024-08-01';
```

**期待効果**: パフォーマンス向上、サイズ削減

### **Phase 3: カリキュラム統一（高価値・高リスク）**

#### **3-1: 現状のデータ二重管理分析**
```python
# JSON形式データ（curriculum.curriculum_data）
curriculum_data_usage = {
    "dependent_files": 31,  # JSONに依存するファイル数
    "complexity": "high",    # 同期処理の複雑性
    "performance": "low"     # JSON解析によるパフォーマンス低下
}

# テーブル形式データ（curriculum_lessons）
curriculum_lessons_usage = {  
    "dependent_files": 17,   # テーブルに依存するファイル数
    "complexity": "medium",  # 標準的なORM操作
    "performance": "high"    # インデックス最適化済み
}
```

#### **3-2: 統一戦略（6週間計画）**

##### **Week 1-2: 準備フェーズ**
```sql
-- データ整合性確認
SELECT 
    c.id as curriculum_id,
    c.title,
    CASE 
        WHEN c.curriculum_data IS NOT NULL THEN 
            JSON_LENGTH(JSON_EXTRACT(c.curriculum_data, '$.table_content'))
        ELSE 0 
    END as json_lessons,
    COUNT(cl.id) as table_lessons
FROM curriculums c
LEFT JOIN curriculum_lessons cl ON c.id = cl.curriculum_id
GROUP BY c.id;

-- 移行スクリプト作成
CREATE TABLE curriculum_migration_log (
    curriculum_id INT,
    migration_status ENUM('pending', 'completed', 'failed'),
    json_count INT,
    table_count INT,
    migrated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

##### **Week 3-4: 段階的移行**
```python
# 移行アダプターによるデータ変換
class CurriculumUnificationMigrator:
    def migrate_json_to_table(self, curriculum_id):
        # 1. JSONデータ取得
        curriculum = Curriculum.query.get(curriculum_id)
        table_content = curriculum.curriculum_data.get('table_content', [])
        
        # 2. テーブル形式に変換
        for index, item in enumerate(table_content):
            lesson = CurriculumLesson(
                curriculum_id=curriculum_id,
                lesson_number=index + 1,
                title=item.get('item', ''),
                duration_minutes=item.get('time', 50),
                # ... 他のフィールドマッピング
            )
            db.session.add(lesson)
        
        # 3. 検証
        db.session.commit()
        return True
```

##### **Week 5-6: 完全統合**
```python
# 同期処理サービス削除
deprecated_services = [
    'auto_sync_service.py',
    'sync_executor_service.py', 
    'conflict_resolver_service.py',
    'sync_scheduler_service.py',
    'sync_validator_service.py'
]

# JSONカラム段階的廃止
# ALTER TABLE curriculums DROP COLUMN curriculum_data;
```

#### **3-3: 期待効果**
- **コード削減**: 30% (5つの同期サービス削除)
- **パフォーマンス向上**: 30-40% (JSON解析 → インデックス検索)
- **保守性向上**: 複雑性大幅削減
- **メモリ使用量削減**: JSON解析処理の削除

---

## ⚠️ リスク評価・安全対策

### **リスクレベル分類**

#### **低リスク（Grade A）**
- **バックアップテーブル削除**: 完全可逆、影響範囲ゼロ
- **開発アカウント削除**: テストデータのみ、本番影響なし
- **インデックス最適化**: パフォーマンス影響のみ

#### **中リスク（Grade B）**  
- **未使用カラム削除**: アプリケーション動作への影響可能性
- **大容量テーブル最適化**: データ整合性への注意が必要

#### **高リスク（Grade C）**
- **カリキュラム統一**: 既存機能への影響大、段階的実施必須

### **安全対策**

#### **必須準備**
1. **完全バックアップ**: 全データのダンプファイル作成
2. **ロールバック計画**: 各段階でのロールバック手順策定  
3. **段階的実施**: 一度に1つのPhaseのみ実行
4. **動作確認**: 各段階での機能テスト実施

#### **緊急時対応**
```bash
# 緊急ロールバック手順
mysql -u QuestEd -p'QuestEd-03012025MySQL' -h localhost -P 3306 quested < backup_before_optimization.sql

# サービス再起動
sudo systemctl restart quested

# 動作確認
curl -s http://localhost:5000/student/learning
```

## 📋 実施順序推奨

### **第1段階: 軽微最適化（1週間）**
1. バックアップテーブル削除
2. 開発アカウントクリーンアップ
3. 基本的な整合性チェック

### **第2段階: 中規模最適化（2-3週間）**
1. 未使用カラム調査・削除
2. インデックス最適化
3. 大容量テーブル検討

### **第3段階: カリキュラム統一（6週間）**
1. 詳細設計・テスト環境構築
2. 段階的移行実施
3. 同期処理サービス削除

この計画により、QuestEdのデータベースを安全かつ効果的に最適化し、長期的な保守性とパフォーマンスを大幅に向上させることができます。