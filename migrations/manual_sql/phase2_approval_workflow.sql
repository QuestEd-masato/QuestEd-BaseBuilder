-- Phase2: 承認ワークフロー機能追加マイグレーション
-- 実行日: 2025-01-26
-- 
-- 実行前の注意事項:
-- 1. 本番環境のバックアップを必ず取得してください
-- 2. トランザクション内で実行することを推奨します
-- 3. 各ステップで影響を受ける行数を確認してください

SET FOREIGN_KEY_CHECKS = 0;

-- ========================================
-- 1. Phase1のカラム名変更（未実施の場合のみ）
-- ========================================

-- activity_logs テーブル
SELECT COUNT(*) as activity_logs_count FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'activity_logs' 
AND COLUMN_NAME = 'timestamp';

-- timestampカラムが存在する場合のみ実行
-- ALTER TABLE activity_logs CHANGE COLUMN timestamp created_at DATETIME;

-- chat_history テーブル
SELECT COUNT(*) as chat_history_count FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'chat_history' 
AND COLUMN_NAME = 'timestamp';

-- timestampカラムが存在する場合のみ実行
-- ALTER TABLE chat_history CHANGE COLUMN timestamp created_at DATETIME;

-- answer_records テーブル
SELECT COUNT(*) as answer_records_count FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'answer_records' 
AND COLUMN_NAME = 'timestamp';

-- timestampカラムが存在する場合のみ実行
-- ALTER TABLE answer_records CHANGE COLUMN timestamp created_at DATETIME;

-- proficiency_records テーブル
SELECT COUNT(*) as proficiency_records_count FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'proficiency_records' 
AND COLUMN_NAME = 'last_updated';

-- last_updatedカラムが存在する場合のみ実行
-- ALTER TABLE proficiency_records CHANGE COLUMN last_updated updated_at DATETIME;

-- text_proficiency_records テーブル
SELECT COUNT(*) as text_proficiency_records_count FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'text_proficiency_records' 
AND COLUMN_NAME = 'last_updated';

-- last_updatedカラムが存在する場合のみ実行
-- ALTER TABLE text_proficiency_records CHANGE COLUMN last_updated updated_at DATETIME;

-- word_proficiency_records テーブル
SELECT COUNT(*) as word_proficiency_records_count FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'word_proficiency_records' 
AND COLUMN_NAME = 'last_updated';

-- last_updatedカラムが存在する場合のみ実行
-- ALTER TABLE word_proficiency_records CHANGE COLUMN last_updated updated_at DATETIME;

-- ========================================
-- 2. student_unit_selections テーブルへの承認機能追加
-- ========================================

-- 承認関連カラムの追加
ALTER TABLE student_unit_selections 
ADD COLUMN IF NOT EXISTS approval_status ENUM('none', 'pending', 'approved', 'rejected') DEFAULT 'none' COMMENT '承認状況' AFTER notes,
ADD COLUMN IF NOT EXISTS completion_request_date DATETIME NULL COMMENT '完了申請日時' AFTER approval_status,
ADD COLUMN IF NOT EXISTS teacher_comments TEXT NULL COMMENT '教師コメント' AFTER completion_request_date,
ADD COLUMN IF NOT EXISTS approved_by INT NULL COMMENT '承認者ID' AFTER teacher_comments,
ADD COLUMN IF NOT EXISTS approved_at DATETIME NULL COMMENT '承認日時' AFTER approved_by,
ADD COLUMN IF NOT EXISTS rejection_reason TEXT NULL COMMENT '却下理由' AFTER approved_at;

-- 外部キー制約の追加
ALTER TABLE student_unit_selections
ADD CONSTRAINT fk_student_unit_selections_approved_by 
FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL;

-- インデックスの追加
CREATE INDEX IF NOT EXISTS idx_approval_status ON student_unit_selections(approval_status);
CREATE INDEX IF NOT EXISTS idx_completion_request_date ON student_unit_selections(completion_request_date);
CREATE INDEX IF NOT EXISTS idx_approved_by ON student_unit_selections(approved_by);

-- ========================================
-- 3. class_learning_settings テーブルへの承認設定追加
-- ========================================

-- 承認ワークフロー設定カラムの追加
ALTER TABLE class_learning_settings
ADD COLUMN IF NOT EXISTS require_teacher_approval BOOLEAN DEFAULT TRUE COMMENT '教師承認必須' AFTER enable_peer_comparison,
ADD COLUMN IF NOT EXISTS auto_approve_threshold DECIMAL(5,2) DEFAULT 90.00 COMMENT '自動承認閾値（%）' AFTER require_teacher_approval,
ADD COLUMN IF NOT EXISTS approval_comment_required BOOLEAN DEFAULT TRUE COMMENT '承認コメント必須' AFTER auto_approve_threshold,
ADD COLUMN IF NOT EXISTS allow_resubmission BOOLEAN DEFAULT TRUE COMMENT '再申請許可' AFTER approval_comment_required;

-- ========================================
-- 4. 既存データの更新（必要に応じて）
-- ========================================

-- 完了済み単元で80%以上の進捗率を持つものを自動承認済みに更新（オプション）
UPDATE student_unit_selections 
SET approval_status = 'approved',
    approved_at = updated_at,
    teacher_comments = 'システム自動承認（Phase2移行時）'
WHERE status = 'completed' 
AND progress_percentage >= 80.00
AND approval_status = 'none';

-- 更新された行数を確認
SELECT COUNT(*) as auto_approved_count 
FROM student_unit_selections 
WHERE approval_status = 'approved' 
AND teacher_comments = 'システム自動承認（Phase2移行時）';

-- ========================================
-- 5. データ整合性の確認
-- ========================================

-- student_unit_selections の承認状態分布
SELECT approval_status, COUNT(*) as count 
FROM student_unit_selections 
GROUP BY approval_status;

-- class_learning_settings の設定状況
SELECT 
    COUNT(*) as total_classes,
    SUM(require_teacher_approval) as approval_required_count,
    AVG(auto_approve_threshold) as avg_auto_approve_threshold
FROM class_learning_settings;

-- ========================================
-- 6. パフォーマンス最適化
-- ========================================

-- 複合インデックスの追加（承認待ちの効率的な検索用）
CREATE INDEX IF NOT EXISTS idx_approval_workflow 
ON student_unit_selections(class_id, approval_status, completion_request_date);

-- 教師別承認待ち検索用インデックス
CREATE INDEX IF NOT EXISTS idx_teacher_pending_approvals
ON student_unit_selections(approval_status, class_id)
WHERE approval_status = 'pending';

SET FOREIGN_KEY_CHECKS = 1;

-- ========================================
-- 実行後の確認クエリ
-- ========================================

-- 新しいカラムが正しく追加されたか確認
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'student_unit_selections'
AND COLUMN_NAME IN ('approval_status', 'completion_request_date', 'teacher_comments', 
                    'approved_by', 'approved_at', 'rejection_reason')
ORDER BY ORDINAL_POSITION;

-- class_learning_settings の新しいカラム確認
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'class_learning_settings'
AND COLUMN_NAME IN ('require_teacher_approval', 'auto_approve_threshold', 
                    'approval_comment_required', 'allow_resubmission')
ORDER BY ORDINAL_POSITION;

-- マイグレーション完了メッセージ
SELECT 'Phase2 承認ワークフロー機能のマイグレーションが完了しました' AS status;