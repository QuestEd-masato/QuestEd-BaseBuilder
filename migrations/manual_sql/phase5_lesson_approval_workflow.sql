-- Phase5: Lesson Approval Workflow
-- レッスン完了申請・承認機能のためのデータベース拡張
-- 作成日: 2025-07-25
-- 目的: StudentLessonProgressテーブルに承認ワークフロー機能を追加

-- ===================================================
-- ステップ1: StudentLessonProgressテーブルの拡張
-- ===================================================

-- 承認関連カラムの追加
ALTER TABLE student_lesson_progress 
ADD COLUMN approval_status ENUM('none', 'pending', 'approved', 'rejected') DEFAULT 'none' COMMENT '承認状況';

ALTER TABLE student_lesson_progress 
ADD COLUMN completion_request_date DATETIME NULL COMMENT '完了申請日時';

ALTER TABLE student_lesson_progress 
ADD COLUMN teacher_comments TEXT NULL COMMENT '教師コメント';

ALTER TABLE student_lesson_progress 
ADD COLUMN approved_by INT NULL COMMENT '承認者ID';

-- 外部キー制約の追加
ALTER TABLE student_lesson_progress 
ADD CONSTRAINT fk_lesson_progress_approved_by 
FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL;

-- ===================================================
-- ステップ2: パフォーマンス向上のためのインデックス追加
-- ===================================================

-- 承認状況でのクエリ最適化
CREATE INDEX idx_lesson_progress_approval_status ON student_lesson_progress(approval_status);

-- 申請日時でのクエリ最適化
CREATE INDEX idx_lesson_progress_completion_request_date ON student_lesson_progress(completion_request_date);

-- 承認者による検索最適化
CREATE INDEX idx_lesson_progress_approved_by ON student_lesson_progress(approved_by);

-- 教師の承認待ち一覧クエリ最適化（複合インデックス）
CREATE INDEX idx_lesson_progress_pending_approval ON student_lesson_progress(approval_status, completion_request_date) 
WHERE approval_status = 'pending';

-- ===================================================
-- ステップ3: データ整合性確認
-- ===================================================

-- 既存データの整合性チェック
SELECT 
    COUNT(*) as total_records,
    COUNT(CASE WHEN approval_status = 'none' THEN 1 END) as none_status,
    COUNT(CASE WHEN completion_request_date IS NOT NULL THEN 1 END) as with_request_date
FROM student_lesson_progress;

-- 外部キー制約の確認
SELECT 
    CONSTRAINT_NAME, 
    TABLE_NAME, 
    COLUMN_NAME, 
    REFERENCED_TABLE_NAME, 
    REFERENCED_COLUMN_NAME 
FROM information_schema.KEY_COLUMN_USAGE 
WHERE TABLE_NAME = 'student_lesson_progress' 
AND CONSTRAINT_NAME LIKE 'fk_%';

-- ===================================================
-- ロールバック用スクリプト（緊急時用）
-- ===================================================

/*
-- 緊急時のロールバック手順:

-- 1. インデックス削除
DROP INDEX idx_lesson_progress_pending_approval ON student_lesson_progress;
DROP INDEX idx_lesson_progress_approved_by ON student_lesson_progress;
DROP INDEX idx_lesson_progress_completion_request_date ON student_lesson_progress;
DROP INDEX idx_lesson_progress_approval_status ON student_lesson_progress;

-- 2. 外部キー制約削除
ALTER TABLE student_lesson_progress 
DROP FOREIGN KEY fk_lesson_progress_approved_by;

-- 3. 追加カラム削除
ALTER TABLE student_lesson_progress 
DROP COLUMN approved_by,
DROP COLUMN teacher_comments,
DROP COLUMN completion_request_date,
DROP COLUMN approval_status;
*/

-- マイグレーション完了確認
SELECT 'Phase5 lesson approval workflow migration completed successfully' as status;