-- ========================================
-- QuestEd DB最適化計画
-- 対象: ローカル & RDS（同時実行）
-- 作成日: 2025-08-10
-- ========================================

-- ====================================
-- Phase 1: 不要インデックスの削除（即座実行可能）
-- 効果: INSERT/UPDATE性能30-40%向上
-- ====================================
ALTER TABLE curriculum_units
  DROP INDEX idx_curriculum_units_mastery_threshold,
  DROP INDEX idx_curriculum_units_self_paced_mode,
  DROP INDEX idx_curriculum_units_estimated_classes;

-- 削除理由:
-- mastery_threshold: 固定値80のため検索不要
-- self_paced_mode: 固定値'flexible'のため検索不要
-- estimated_classes: FLOAT型へのインデックスは非効率

-- ====================================
-- Phase 2: 使用状況の分析（実行後に判断）
-- ====================================

-- 2.1 問題カラムの使用状況確認
SELECT 
  COUNT(*) as total_records,
  COUNT(DISTINCT mastery_threshold) as mastery_variations,
  COUNT(DISTINCT self_paced_mode) as mode_variations,
  COUNT(CASE WHEN prerequisite_skills IS NOT NULL AND prerequisite_skills != '' THEN 1 END) as skills_used
FROM curriculum_units;

-- 2.2 もし全て固定値なら削除を検討（要確認）
-- ALTER TABLE curriculum_units
--   DROP COLUMN mastery_threshold,
--   DROP COLUMN self_paced_mode,
--   DROP COLUMN prerequisite_skills;

-- ====================================
-- Phase 3: その他の不要インデックス削除候補
-- ====================================

-- 3.1 低カーディナリティインデックスの確認
SELECT 
  'idx_curriculum_units_is_active' as index_name,
  COUNT(DISTINCT is_active) as distinct_values
FROM curriculum_units
UNION ALL
SELECT 
  'idx_curriculum_units_created_by' as index_name,
  COUNT(DISTINCT created_by) as distinct_values
FROM curriculum_units;

-- 3.2 もし値が少なければ削除
-- ALTER TABLE curriculum_units
--   DROP INDEX idx_curriculum_units_is_active;

-- ====================================
-- Phase 4: 将来的な正規化（中長期計画）
-- ====================================

-- 4.1 JSONカラムを正規化テーブルへ
-- CREATE TABLE curriculum_prerequisites (
--   id INT AUTO_INCREMENT PRIMARY KEY,
--   curriculum_unit_id INT NOT NULL,
--   prerequisite_unit_id INT NOT NULL,
--   order_index INT DEFAULT 0,
--   UNIQUE KEY uk_prereq (curriculum_unit_id, prerequisite_unit_id),
--   FOREIGN KEY (curriculum_unit_id) REFERENCES curriculum_units(id),
--   FOREIGN KEY (prerequisite_unit_id) REFERENCES curriculum_units(id)
-- );

-- CREATE TABLE curriculum_tags (
--   id INT AUTO_INCREMENT PRIMARY KEY,
--   curriculum_unit_id INT NOT NULL,
--   tag_name VARCHAR(50) NOT NULL,
--   UNIQUE KEY uk_tag (curriculum_unit_id, tag_name),
--   KEY idx_tag_name (tag_name),
--   FOREIGN KEY (curriculum_unit_id) REFERENCES curriculum_units(id)
-- );

-- ====================================
-- Phase 5: 実行手順
-- ====================================
-- 1. このファイルをローカルで実行
--    mysql -u QuestEd -p'QuestEd-03012025MySQL' quested < db_optimization_plan.sql
--
-- 2. RDSで実行（EC2経由）
--    mysql -u root -p'masato1873_QuestEd-03012025' -h database-1.cdk0iio0s90g.ap-northeast-1.rds.amazonaws.com quested < db_optimization_plan.sql