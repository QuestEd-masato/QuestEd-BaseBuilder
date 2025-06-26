-- Phase2: 承認ワークフロー機能のロールバックスクリプト
-- 実行日: 2025-01-26
-- 
-- 警告: このスクリプトは承認ワークフロー機能を削除します
-- 実行前に必ずバックアップを取得してください

SET FOREIGN_KEY_CHECKS = 0;

-- ========================================
-- 1. student_unit_selections テーブルのロールバック
-- ========================================

-- 外部キー制約の削除
ALTER TABLE student_unit_selections
DROP FOREIGN KEY IF EXISTS fk_student_unit_selections_approved_by;

-- インデックスの削除
DROP INDEX IF EXISTS idx_approval_status ON student_unit_selections;
DROP INDEX IF EXISTS idx_completion_request_date ON student_unit_selections;
DROP INDEX IF EXISTS idx_approved_by ON student_unit_selections;
DROP INDEX IF EXISTS idx_approval_workflow ON student_unit_selections;
DROP INDEX IF EXISTS idx_teacher_pending_approvals ON student_unit_selections;

-- カラムの削除
ALTER TABLE student_unit_selections
DROP COLUMN IF EXISTS approval_status,
DROP COLUMN IF EXISTS completion_request_date,
DROP COLUMN IF EXISTS teacher_comments,
DROP COLUMN IF EXISTS approved_by,
DROP COLUMN IF EXISTS approved_at,
DROP COLUMN IF EXISTS rejection_reason;

-- ========================================
-- 2. class_learning_settings テーブルのロールバック
-- ========================================

-- カラムの削除
ALTER TABLE class_learning_settings
DROP COLUMN IF EXISTS require_teacher_approval,
DROP COLUMN IF EXISTS auto_approve_threshold,
DROP COLUMN IF EXISTS approval_comment_required,
DROP COLUMN IF EXISTS allow_resubmission;

-- ========================================
-- 3. Phase1のカラム名変更のロールバック（必要な場合）
-- ========================================

-- 注意: これらのロールバックは慎重に行ってください
-- アプリケーションコードが古いカラム名を使用している場合のみ実行

-- ALTER TABLE activity_logs CHANGE COLUMN created_at timestamp DATETIME;
-- ALTER TABLE chat_history CHANGE COLUMN created_at timestamp DATETIME;
-- ALTER TABLE answer_records CHANGE COLUMN created_at timestamp DATETIME;
-- ALTER TABLE proficiency_records CHANGE COLUMN updated_at last_updated DATETIME;
-- ALTER TABLE text_proficiency_records CHANGE COLUMN updated_at last_updated DATETIME;
-- ALTER TABLE word_proficiency_records CHANGE COLUMN updated_at last_updated DATETIME;

SET FOREIGN_KEY_CHECKS = 1;

-- ========================================
-- ロールバック後の確認
-- ========================================

-- student_unit_selections の承認関連カラムが削除されたか確認
SELECT COUNT(*) as remaining_approval_columns
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'student_unit_selections'
AND COLUMN_NAME IN ('approval_status', 'completion_request_date', 'teacher_comments', 
                    'approved_by', 'approved_at', 'rejection_reason');

-- class_learning_settings の承認設定カラムが削除されたか確認
SELECT COUNT(*) as remaining_setting_columns
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'class_learning_settings'
AND COLUMN_NAME IN ('require_teacher_approval', 'auto_approve_threshold', 
                    'approval_comment_required', 'allow_resubmission');

-- ロールバック完了メッセージ
SELECT 'Phase2 承認ワークフロー機能のロールバックが完了しました' AS status;