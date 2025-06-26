-- Phase2: データ整合性修正スクリプト
-- 実行日: 2025-01-26
-- 
-- CLAUDE.mdで指摘された問題の修正

-- ========================================
-- 1. curriculum_units の権限修正
-- ========================================

-- 現在の状況確認
SELECT 
    cu.id,
    cu.title,
    cu.created_by,
    c.teacher_id as original_teacher_id,
    cu.school_id,
    cl.school_id as class_school_id
FROM curriculum_units cu
LEFT JOIN curriculums c ON cu.legacy_curriculum_id = c.id
LEFT JOIN classes cl ON c.class_id = cl.id
WHERE cu.legacy_curriculum_id IS NOT NULL;

-- created_by を正しい教師IDに修正
UPDATE curriculum_units cu
JOIN curriculums c ON cu.legacy_curriculum_id = c.id
SET cu.created_by = c.teacher_id
WHERE cu.legacy_curriculum_id IS NOT NULL
AND cu.created_by != c.teacher_id;

-- school_id を正しく設定
UPDATE curriculum_units cu
JOIN curriculums c ON cu.legacy_curriculum_id = c.id
JOIN classes cl ON c.class_id = cl.id
SET cu.school_id = cl.school_id
WHERE cu.legacy_curriculum_id IS NOT NULL
AND (cu.school_id IS NULL OR cu.school_id != cl.school_id);

-- subject_id の継承確認と修正
UPDATE curriculum_units cu
JOIN curriculums c ON cu.legacy_curriculum_id = c.id
SET cu.subject_id = c.subject_id
WHERE cu.legacy_curriculum_id IS NOT NULL
AND cu.subject_id IS NULL
AND c.subject_id IS NOT NULL;

-- ========================================
-- 2. unit_item_mappings の自動生成
-- ========================================

-- 既存のマッピング数を確認
SELECT COUNT(*) as existing_mappings FROM unit_item_mappings;

-- 単元の教科と難易度に基づいて問題を自動マッピング（英語の例）
INSERT INTO unit_item_mappings (unit_id, item_id, weight, order_index, is_required, created_at)
SELECT 
    cu.id as unit_id,
    bki.id as item_id,
    1.00 as weight,
    ROW_NUMBER() OVER (PARTITION BY cu.id ORDER BY bki.difficulty_level, bki.id) as order_index,
    TRUE as is_required,
    NOW() as created_at
FROM curriculum_units cu
JOIN basic_knowledge_items bki ON cu.subject_id = bki.subject_id
WHERE cu.subject_id = 1  -- 英語
AND cu.difficulty_level = bki.difficulty_level
AND NOT EXISTS (
    SELECT 1 FROM unit_item_mappings uim 
    WHERE uim.unit_id = cu.id AND uim.item_id = bki.id
)
LIMIT 100;  -- 一度に大量のデータを作成しないよう制限

-- ========================================
-- 3. student_unit_selections の進捗更新
-- ========================================

-- answer_records から実際の学習進捗を反映
UPDATE student_unit_selections sus
JOIN (
    SELECT 
        sus.id,
        sus.student_id,
        sus.unit_id,
        COUNT(DISTINCT uim.item_id) as total_items,
        COUNT(DISTINCT ar.problem_id) as completed_items,
        SUM(CASE WHEN ar.is_correct = 1 THEN 1 ELSE 0 END) as correct_items
    FROM student_unit_selections sus
    JOIN unit_item_mappings uim ON sus.unit_id = uim.unit_id
    LEFT JOIN answer_records ar ON ar.student_id = sus.student_id AND ar.problem_id = uim.item_id
    GROUP BY sus.id, sus.student_id, sus.unit_id
) progress ON sus.id = progress.id
SET 
    sus.total_items = progress.total_items,
    sus.completed_items = progress.completed_items,
    sus.correct_items = progress.correct_items,
    sus.progress_percentage = CASE 
        WHEN progress.total_items > 0 THEN (progress.completed_items / progress.total_items) * 100
        ELSE 0
    END,
    sus.status = CASE
        WHEN progress.completed_items = 0 THEN 'not_started'
        WHEN progress.completed_items = progress.total_items THEN 'completed'
        ELSE 'in_progress'
    END,
    sus.started_at = CASE
        WHEN sus.started_at IS NULL AND progress.completed_items > 0 THEN NOW()
        ELSE sus.started_at
    END,
    sus.completed_at = CASE
        WHEN progress.completed_items = progress.total_items AND sus.completed_at IS NULL THEN NOW()
        ELSE sus.completed_at
    END,
    sus.last_activity_at = NOW()
WHERE sus.status = 'not_started' OR sus.progress_percentage = 0;

-- ========================================
-- 4. ランキングデータの修正準備
-- ========================================

-- users.class_id と class_enrollments の不整合を確認
SELECT 
    u.id,
    u.username,
    u.class_id as user_class_id,
    GROUP_CONCAT(ce.class_id) as enrolled_class_ids
FROM users u
LEFT JOIN class_enrollments ce ON u.id = ce.student_id
WHERE u.role = 'student'
GROUP BY u.id, u.username, u.class_id
HAVING user_class_id IS NULL OR user_class_id NOT IN (enrolled_class_ids);

-- ========================================
-- 5. 統計情報の更新
-- ========================================

-- 修正後の統計
SELECT 'データ修正完了統計' as status;

-- curriculum_units の修正結果
SELECT 
    COUNT(*) as total_units,
    COUNT(DISTINCT created_by) as unique_creators,
    COUNT(school_id) as units_with_school,
    COUNT(subject_id) as units_with_subject
FROM curriculum_units;

-- unit_item_mappings の状況
SELECT 
    COUNT(DISTINCT unit_id) as mapped_units,
    COUNT(*) as total_mappings,
    AVG(items_per_unit) as avg_items_per_unit
FROM (
    SELECT unit_id, COUNT(*) as items_per_unit
    FROM unit_item_mappings
    GROUP BY unit_id
) unit_stats;

-- student_unit_selections の進捗状況
SELECT 
    status,
    COUNT(*) as count,
    AVG(progress_percentage) as avg_progress,
    AVG(CASE WHEN completed_items > 0 THEN correct_items / completed_items * 100 ELSE 0 END) as avg_accuracy
FROM student_unit_selections
GROUP BY status;

-- 承認ワークフロー準備状況
SELECT 
    approval_status,
    COUNT(*) as count
FROM student_unit_selections
WHERE progress_percentage >= 80
GROUP BY approval_status;

-- ========================================
-- 完了メッセージ
-- ========================================
SELECT 'Phase2 データ整合性修正が完了しました' AS status;