-- レッスンシステムテーブル復旧SQL
-- 慎重な段階的復旧: 外部キー制約を考慮した正しい順序

-- 1. CurriculumLessonテーブル（メイン）
CREATE TABLE IF NOT EXISTS curriculum_lessons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    curriculum_id INT NOT NULL,
    lesson_number INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    lesson_type ENUM('lecture', 'practice', 'discussion', 'presentation', 'experiment', 'review') DEFAULT 'lecture',
    duration_minutes INT DEFAULT 50,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 外部キー制約
    FOREIGN KEY (curriculum_id) REFERENCES curriculums(id) ON DELETE CASCADE,
    
    -- インデックス
    INDEX idx_curriculum_lesson (curriculum_id, lesson_number),
    INDEX idx_lesson_type (lesson_type)
);

-- 2. LessonTaskテーブル（レッスン内タスク）
CREATE TABLE IF NOT EXISTS lesson_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lesson_id INT NOT NULL,
    task_number INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    instructions TEXT,
    estimated_minutes INT DEFAULT 10,
    is_required BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 外部キー制約
    FOREIGN KEY (lesson_id) REFERENCES curriculum_lessons(id) ON DELETE CASCADE,
    
    -- インデックス
    INDEX idx_lesson_task (lesson_id, task_number),
    INDEX idx_task_required (is_required)
);

-- 3. StudentLessonProgressテーブル（学生のレッスン進捗）
CREATE TABLE IF NOT EXISTS student_lesson_progress (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    lesson_id INT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 承認システム関連
    approval_status ENUM('none', 'pending', 'approved', 'rejected') DEFAULT 'none',
    completion_request_date TIMESTAMP NULL,
    teacher_comments TEXT NULL,
    approved_by INT NULL,
    approved_at TIMESTAMP NULL,
    rejected_at TIMESTAMP NULL,
    rejected_by INT NULL,
    rejection_reason TEXT NULL,
    rejection_date TIMESTAMP NULL,
    
    -- 外部キー制約
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (lesson_id) REFERENCES curriculum_lessons(id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (rejected_by) REFERENCES users(id) ON DELETE SET NULL,
    
    -- ユニーク制約
    UNIQUE KEY unique_student_lesson (student_id, lesson_id),
    
    -- インデックス
    INDEX idx_student_progress (student_id, started_at),
    INDEX idx_lesson_progress (lesson_id),
    INDEX idx_approval_status (approval_status),
    INDEX idx_completion_request_date (completion_request_date),
    INDEX idx_pending_approval (approval_status, completion_request_date)
);

-- 4. StudentTaskCheckテーブル（タスクチェック記録）
CREATE TABLE IF NOT EXISTS student_task_checks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    lesson_progress_id INT NOT NULL,
    task_id INT NOT NULL,
    status ENUM('not_checked', 'checked', 'completed') DEFAULT 'not_checked',
    checked_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    time_spent_minutes INT DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 外部キー制約
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (lesson_progress_id) REFERENCES student_lesson_progress(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES lesson_tasks(id) ON DELETE CASCADE,
    
    -- ユニーク制約
    UNIQUE KEY unique_student_task_check (student_id, lesson_progress_id, task_id),
    
    -- インデックス
    INDEX idx_student_task_status (student_id, status),
    INDEX idx_lesson_progress_tasks (lesson_progress_id),
    INDEX idx_task_checks (task_id),
    INDEX idx_checked_at (checked_at),
    INDEX idx_task_status_time (status, checked_at)
);

-- パフォーマンス最適化のための追加インデックス
CREATE INDEX IF NOT EXISTS idx_lesson_progress_approval_status ON student_lesson_progress(approval_status);
CREATE INDEX IF NOT EXISTS idx_lesson_progress_completion_request_date ON student_lesson_progress(completion_request_date);
CREATE INDEX IF NOT EXISTS idx_lesson_progress_pending_approval ON student_lesson_progress(approval_status, completion_request_date);

-- テーブル作成完了メッセージ
SELECT 'レッスンシステムテーブル復旧完了' as result;