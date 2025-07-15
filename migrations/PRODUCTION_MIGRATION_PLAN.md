# QuestEd Database Migration Plan - 自由進度学習フィールド追加

**作成日**: 2025-07-10  
**対象環境**: 本番環境  
**影響範囲**: curriculums, curriculum_units テーブル  
**ダウンタイム**: 約2-3分  

## 📊 事前調査結果 (2025-07-10)

### 現在のデータ状況
- curriculum_units: 8レコード
- curriculums: 6レコード
- 既存データは全て保持される

### 追加予定フィールド

#### curriculums テーブル
- `total_classes` INT DEFAULT 35 - 50分コマの総数
- `difficulty_level` INT DEFAULT 2 - 難易度レベル（1-5）
- `mastery_threshold` INT DEFAULT 80 - 習熟度判定基準（%）
- `self_paced_mode` VARCHAR(20) DEFAULT 'flexible' - 自由進度設定
- `prerequisite_skills` TEXT - 前提スキル・知識
- `total_hours` FLOAT 変更 - 小数点対応

#### curriculum_units テーブル
- `estimated_classes` FLOAT DEFAULT 1.0 - 推定コマ数
- `mastery_threshold` INT DEFAULT 80 - 習熟度判定基準（%）
- `self_paced_mode` VARCHAR(20) DEFAULT 'flexible' - 自由進度設定
- `prerequisite_skills` TEXT - 前提スキル・知識

## 🛡️ 事前準備 (本番実行前)

### 1. 完全バックアップ取得
```bash
# データベース全体バックアップ
mysqldump -u QuestEd -p'QuestEd-03012025MySQL' quested > backup_before_migration_$(date +%Y%m%d_%H%M%S).sql

# 対象テーブル個別バックアップ
mysqldump -u QuestEd -p'QuestEd-03012025MySQL' quested curriculums curriculum_units > backup_target_tables_$(date +%Y%m%d_%H%M%S).sql
```

### 2. アプリケーション停止
```bash
# Webサーバー停止
sudo systemctl stop nginx
sudo systemctl stop gunicorn

# または開発環境の場合
pkill -f "python.*app.py"
```

### 3. 整合性チェック
```sql
-- 既存データの整合性確認
SELECT COUNT(*) FROM curriculum_units WHERE id IS NULL;
SELECT COUNT(*) FROM curriculums WHERE id IS NULL;
```

## 📋 マイグレーション実行手順

### Phase 1: curriculums テーブル修正

```sql
USE quested;

-- 1. 新フィールド追加
ALTER TABLE curriculums 
ADD COLUMN total_classes INT DEFAULT 35 COMMENT '50分コマの総数' AFTER total_hours,
ADD COLUMN difficulty_level INT DEFAULT 2 COMMENT '難易度レベル（1-5）' AFTER total_classes,
ADD COLUMN mastery_threshold INT DEFAULT 80 COMMENT '習熟度判定基準（%）' AFTER difficulty_level,
ADD COLUMN self_paced_mode VARCHAR(20) DEFAULT 'flexible' COMMENT '自由進度設定' AFTER mastery_threshold,
ADD COLUMN prerequisite_skills TEXT COMMENT '前提スキル・知識' AFTER self_paced_mode;

-- 2. total_hoursをFLOATに変更
ALTER TABLE curriculums 
MODIFY COLUMN total_hours FLOAT DEFAULT 29.2 COMMENT '50分コマから計算した総時間数';

-- 3. インデックス追加
CREATE INDEX idx_curriculums_difficulty_level ON curriculums(difficulty_level);
CREATE INDEX idx_curriculums_self_paced_mode ON curriculums(self_paced_mode);
CREATE INDEX idx_curriculums_total_classes ON curriculums(total_classes);
```

### Phase 2: curriculum_units テーブル修正

```sql
-- 1. 不足フィールド追加
ALTER TABLE curriculum_units 
ADD COLUMN estimated_classes FLOAT DEFAULT 1.0 COMMENT '推定コマ数（50分/コマ基準）' AFTER estimated_minutes,
ADD COLUMN mastery_threshold INT DEFAULT 80 COMMENT '習熟度判定基準（%）' AFTER estimated_classes,
ADD COLUMN self_paced_mode VARCHAR(20) DEFAULT 'flexible' COMMENT '自由進度設定' AFTER mastery_threshold,
ADD COLUMN prerequisite_skills TEXT COMMENT '前提スキル・知識' AFTER self_paced_mode;

-- 2. estimated_minutesデフォルト値変更
ALTER TABLE curriculum_units 
MODIFY COLUMN estimated_minutes INT DEFAULT 50 COMMENT '推定学習時間（分） - 50分/コマ基準';

-- 3. インデックス追加
CREATE INDEX idx_curriculum_units_difficulty_level ON curriculum_units(difficulty_level);
CREATE INDEX idx_curriculum_units_self_paced_mode ON curriculum_units(self_paced_mode);
CREATE INDEX idx_curriculum_units_mastery_threshold ON curriculum_units(mastery_threshold);
CREATE INDEX idx_curriculum_units_estimated_classes ON curriculum_units(estimated_classes);
```

### Phase 3: 既存データ更新

```sql
-- 1. curriculumsテーブルのデータ更新
UPDATE curriculums 
SET total_classes = CASE 
    WHEN total_hours IS NOT NULL THEN CEIL(total_hours * 60 / 50)
    ELSE 35 
END,
total_hours = CASE 
    WHEN total_hours IS NOT NULL THEN total_hours
    ELSE (total_classes * 50.0 / 60)
END;

-- 2. curriculum_unitsテーブルのデータ更新
UPDATE curriculum_units 
SET estimated_classes = CASE 
    WHEN estimated_minutes IS NOT NULL THEN ROUND(estimated_minutes / 50.0, 1)
    ELSE 1.0 
END;

-- 3. NULLフィールドにデフォルト値設定
UPDATE curriculum_units 
SET 
    difficulty_level = COALESCE(difficulty_level, 2),
    estimated_minutes = COALESCE(estimated_minutes, 50),
    mastery_threshold = COALESCE(mastery_threshold, 80),
    self_paced_mode = COALESCE(self_paced_mode, 'flexible')
WHERE 
    difficulty_level IS NULL 
    OR estimated_minutes IS NULL 
    OR mastery_threshold IS NULL 
    OR self_paced_mode IS NULL;
```

## ✅ 検証手順

### 1. スキーマ確認
```sql
-- テーブル構造確認
DESCRIBE curriculums;
DESCRIBE curriculum_units;

-- インデックス確認
SHOW INDEX FROM curriculums;
SHOW INDEX FROM curriculum_units;
```

### 2. データ整合性確認
```sql
-- レコード数確認
SELECT COUNT(*) FROM curriculums;
SELECT COUNT(*) FROM curriculum_units;

-- 新フィールド値確認
SELECT id, total_classes, difficulty_level, mastery_threshold, self_paced_mode 
FROM curriculums LIMIT 5;

SELECT id, estimated_classes, mastery_threshold, self_paced_mode 
FROM curriculum_units LIMIT 5;
```

### 3. アプリケーション動作確認
```bash
# アプリケーション再起動
sudo systemctl start gunicorn
sudo systemctl start nginx

# カリキュラム表示テスト
curl -I http://127.0.0.1:5000/teacher/curriculum/6
```

## 🔄 ロールバック手順

### 緊急時ロールバック
```sql
-- フィールド削除（必要に応じて）
ALTER TABLE curriculums 
DROP COLUMN total_classes,
DROP COLUMN difficulty_level,
DROP COLUMN mastery_threshold,
DROP COLUMN self_paced_mode,
DROP COLUMN prerequisite_skills;

ALTER TABLE curriculum_units 
DROP COLUMN estimated_classes,
DROP COLUMN mastery_threshold,
DROP COLUMN self_paced_mode,
DROP COLUMN prerequisite_skills;

-- total_hoursをINTに戻す
ALTER TABLE curriculums 
MODIFY COLUMN total_hours INT DEFAULT NULL;
```

### 完全ロールバック
```bash
# バックアップからの復旧
mysql -u QuestEd -p'QuestEd-03012025MySQL' quested < backup_before_migration_YYYYMMDD_HHMMSS.sql
```

## 📝 実行記録テンプレート

```
実行日時: _______________
実行者: _______________
バックアップファイル: _______________

Phase 1 実行時刻: _______________
Phase 2 実行時刻: _______________
Phase 3 実行時刻: _______________

検証結果:
- スキーマ確認: _______________
- データ整合性: _______________
- アプリケーション動作: _______________

問題発生時の対応:
_______________

完了時刻: _______________
```

## ⚠️ 注意事項

1. **ダウンタイム**: 2-3分程度のサービス停止が発生
2. **データ保護**: 全ての既存データは保持される
3. **性能影響**: 新しいインデックスによりクエリ性能が向上
4. **互換性**: 既存のアプリケーションコードとの完全互換性
5. **監視**: マイグレーション後24時間はログを監視

## 📞 緊急連絡先

- システム管理者: _______________
- 開発責任者: _______________
- データベース管理者: _______________