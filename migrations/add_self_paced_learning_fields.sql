-- カリキュラム作成フォームの50分コマベース・自由進度学習対応のためのDBスキーマ変更
-- 実行日: 2025-07-09

-- 1. curriculumsテーブルに新しいフィールドを追加
ALTER TABLE curriculums 
ADD COLUMN total_classes INT DEFAULT 35 COMMENT '50分コマの総数' AFTER total_hours,
ADD COLUMN difficulty_level INT DEFAULT 2 COMMENT '難易度レベル（1-5）' AFTER total_classes,
ADD COLUMN mastery_threshold INT DEFAULT 80 COMMENT '習熟度判定基準（%）' AFTER difficulty_level,
ADD COLUMN self_paced_mode VARCHAR(20) DEFAULT 'flexible' COMMENT '自由進度設定' AFTER mastery_threshold,
ADD COLUMN prerequisite_skills TEXT COMMENT '前提スキル・知識' AFTER self_paced_mode;

-- 2. total_hoursフィールドをFLOATに変更（50分コマから計算した小数点を含む時間に対応）
ALTER TABLE curriculums 
MODIFY COLUMN total_hours FLOAT DEFAULT 29.2 COMMENT '50分コマから計算した総時間数';

-- 3. curriculum_unitsテーブルに新しいフィールドを追加
ALTER TABLE curriculum_units 
ADD COLUMN estimated_classes FLOAT DEFAULT 1.0 COMMENT '推定コマ数（50分/コマ基準）' AFTER estimated_minutes,
ADD COLUMN mastery_threshold INT DEFAULT 80 COMMENT '習熟度判定基準（%）' AFTER estimated_classes,
ADD COLUMN self_paced_mode VARCHAR(20) DEFAULT 'flexible' COMMENT '自由進度設定' AFTER mastery_threshold,
ADD COLUMN prerequisite_skills TEXT COMMENT '前提スキル・知識' AFTER self_paced_mode,
ADD COLUMN prerequisites JSON COMMENT '前提単元ID配列' AFTER prerequisite_skills,
ADD COLUMN learning_objectives TEXT COMMENT '学習目標' AFTER prerequisites,
ADD COLUMN tags JSON COMMENT 'タグ配列' AFTER learning_objectives;

-- 4. estimated_minutesのデフォルト値を50分に変更
ALTER TABLE curriculum_units 
MODIFY COLUMN estimated_minutes INT DEFAULT 50 COMMENT '推定学習時間（分） - 50分/コマ基準';

-- 5. インデックスを追加（検索・フィルタリング性能向上のため）
CREATE INDEX idx_curriculums_difficulty_level ON curriculums(difficulty_level);
CREATE INDEX idx_curriculums_self_paced_mode ON curriculums(self_paced_mode);
CREATE INDEX idx_curriculums_total_classes ON curriculums(total_classes);
CREATE INDEX idx_curriculum_units_difficulty_level ON curriculum_units(difficulty_level);
CREATE INDEX idx_curriculum_units_self_paced_mode ON curriculum_units(self_paced_mode);
CREATE INDEX idx_curriculum_units_mastery_threshold ON curriculum_units(mastery_threshold);
CREATE INDEX idx_curriculum_units_estimated_classes ON curriculum_units(estimated_classes);

-- 6. 既存データの更新（total_classesからtotal_hoursを再計算）
UPDATE curriculums 
SET total_classes = CASE 
    WHEN total_hours IS NOT NULL THEN CEIL(total_hours * 60 / 50)
    ELSE 35 
END,
total_hours = CASE 
    WHEN total_hours IS NOT NULL THEN total_hours
    ELSE (total_classes * 50.0 / 60)
END;

-- 7. curriculum_unitsテーブルの既存データも更新
UPDATE curriculum_units 
SET estimated_classes = CASE 
    WHEN estimated_minutes IS NOT NULL THEN ROUND(estimated_minutes / 50.0, 1)
    ELSE 1.0 
END;

-- 8. コメント追加でスキーマ変更の記録
INSERT INTO migration_log (migration_name, executed_at, description) 
VALUES (
    'add_self_paced_learning_fields',
    NOW(),
    '50分コマベース設計と自由進度学習メタデータの追加。教師のカリキュラム作成時に必要な情報を追加し、生徒の学習選択支援を強化。'
);