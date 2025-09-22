-- ================================================================
-- ローカルDB → RDS 安全な同期スクリプト
-- 作成日: 2025年8月9日
-- 目的: classesテーブルのgrade/classroomデータのみを修復
-- ================================================================

-- 1. 実行前の現状確認
SELECT '📊 実行前の状態確認' as step;
SELECT id, name, grade, classroom 
FROM classes 
ORDER BY id;

-- 2. grade/classroomのみを安全に更新
-- （他のカラムは一切触らない）

SELECT '🔧 grade/classroom データ修復開始' as step;

-- id=2: 3年2組
UPDATE classes 
SET grade = 3, classroom = '2組' 
WHERE id = 2 AND teacher_id = 5;

-- id=4: 2年３組
UPDATE classes 
SET grade = 2, classroom = '3組' 
WHERE id = 4 AND teacher_id = 5;

-- id=6: Test Class（NULL のまま）
-- 更新なし（元々NULL）

-- id=7: ２年１組
UPDATE classes 
SET grade = 2, classroom = '1組' 
WHERE id = 7 AND teacher_id = 18;

-- id=8: ２年１組　理科
UPDATE classes 
SET grade = 3, classroom = '1組' 
WHERE id = 8 AND teacher_id = 18;

-- id=9: 2年３組 理科
UPDATE classes 
SET grade = 2, classroom = '3組' 
WHERE id = 9 AND teacher_id = 5;

-- id=10: 2年３組 (探究)
UPDATE classes 
SET grade = 2, classroom = '3組' 
WHERE id = 10 AND teacher_id = 5;

-- id=11: １年１組 (理科)
UPDATE classes 
SET grade = 1, classroom = '1組' 
WHERE id = 11 AND teacher_id = 18;

-- 3. 実行後の確認
SELECT '✅ 実行後の状態確認' as step;
SELECT id, name, grade, classroom 
FROM classes 
ORDER BY id;

-- 4. 影響を受けた行数の確認
SELECT '📊 更新された行数' as step;
SELECT ROW_COUNT() as updated_rows;

-- ================================================================
-- ロールバック用SQL（必要な場合のみ使用）
-- ================================================================
-- UPDATE classes SET grade = NULL, classroom = NULL WHERE id IN (2,4,7,8,9,10,11);
-- または
-- DROP TABLE classes;
-- RENAME TABLE classes_backup_20250809 TO classes;