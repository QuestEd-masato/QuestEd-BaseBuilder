-- Curriculum Task System Database Schema
-- Week 1: 基盤整備
-- Created: 2025-07-10

-- 1. curriculum_tasks テーブル: 週次課題データ
CREATE TABLE curriculum_tasks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    curriculum_id INT NOT NULL,
    week_number INT NOT NULL,           -- 第何週の課題か
    order_in_week INT NOT NULL,         -- 週内での順序
    title VARCHAR(200) NOT NULL,        -- 課題タイトル
    description TEXT,                   -- 詳細説明
    
    -- 課題分類
    task_type ENUM('worksheet', 'report', 'test', 'presentation', 'project', 'discussion') NOT NULL,
    estimated_minutes INT DEFAULT 50,   -- 推定所要時間
    difficulty_level INT DEFAULT 2,     -- 1-5段階
    is_required BOOLEAN DEFAULT TRUE,   -- 必須/選択
    
    -- 提出要件
    submission_requirements JSON,       -- 提出形式・文字数・必須要素
    evaluation_criteria JSON,          -- ルーブリック評価基準
    
    -- 期限管理
    due_date_type ENUM('relative_to_week_start', 'relative_to_previous', 'fixed_date') DEFAULT 'relative_to_week_start',
    due_date_offset_days INT DEFAULT 7, -- 期限オフセット
    fixed_due_date DATE NULL,          -- 固定期限
    
    -- メタデータ
    resources JSON,                     -- 参考資料・リンク
    teacher_notes TEXT,                 -- 教師用メモ
    auto_approval_enabled BOOLEAN DEFAULT FALSE,
    auto_approval_threshold INT DEFAULT 80,
    
    -- 管理情報
    created_by INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (curriculum_id) REFERENCES curriculums(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id),
    INDEX idx_curriculum_week (curriculum_id, week_number, order_in_week),
    INDEX idx_task_type (task_type),
    INDEX idx_due_date (due_date_type, due_date_offset_days)
);

-- 2. student_task_progress テーブル: 学生課題進捗
CREATE TABLE student_task_progress (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    task_id INT NOT NULL,
    
    -- 進捗状況
    status ENUM('not_started', 'in_progress', 'submitted', 'completed', 'needs_revision') DEFAULT 'not_started',
    progress_percentage INT DEFAULT 0,
    
    -- タイムスタンプ
    started_at DATETIME NULL,
    submitted_at DATETIME NULL,
    completed_at DATETIME NULL,
    last_activity_at DATETIME NULL,
    
    -- 提出データ
    submission_data JSON,              -- 提出ファイル・内容
    self_evaluation JSON,              -- 自己評価
    time_spent_minutes INT DEFAULT 0,  -- 実際の作業時間
    
    -- 教師評価
    teacher_evaluation JSON,           -- ルーブリック評価結果
    teacher_feedback TEXT,             -- コメント
    approved_by INT NULL,              -- 承認教師
    approval_requested_at DATETIME NULL,
    
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES curriculum_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by) REFERENCES users(id),
    UNIQUE KEY unique_student_task (student_id, task_id),
    INDEX idx_student_progress (student_id, status),
    INDEX idx_task_submissions (task_id, status),
    INDEX idx_approval_queue (status, approval_requested_at)
);

-- 3. task_dependencies テーブル: 課題依存関係（将来拡張用）
CREATE TABLE task_dependencies (
    id INT PRIMARY KEY AUTO_INCREMENT,
    task_id INT NOT NULL,
    prerequisite_task_id INT NOT NULL,
    dependency_type ENUM('required', 'recommended') DEFAULT 'required',
    
    FOREIGN KEY (task_id) REFERENCES curriculum_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (prerequisite_task_id) REFERENCES curriculum_tasks(id) ON DELETE CASCADE,
    UNIQUE KEY unique_task_dependency (task_id, prerequisite_task_id)
);

-- 4. task_file_attachments テーブル: 課題添付ファイル管理
CREATE TABLE task_file_attachments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    task_progress_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (task_progress_id) REFERENCES student_task_progress(id) ON DELETE CASCADE,
    INDEX idx_task_files (task_progress_id)
);

-- Sample data insertion for testing
-- Note: This will be replaced with actual curriculum data
INSERT INTO curriculum_tasks (
    curriculum_id, week_number, order_in_week, title, description, 
    task_type, estimated_minutes, difficulty_level, is_required,
    submission_requirements, evaluation_criteria, created_by
) VALUES (
    1, 1, 1, 
    '探究問い設定ワークシート',
    '大テーマから具体的な探究問いを3つ設定し、各問いの根拠と期待される学習成果を記述する',
    'worksheet', 30, 2, TRUE,
    JSON_OBJECT(
        'format', 'document',
        'min_word_count', 200,
        'required_elements', JSON_ARRAY('探究問い', '根拠', '期待成果')
    ),
    JSON_OBJECT(
        '問いの具体性', JSON_OBJECT('excellent', 5, 'good', 3, 'needs_improvement', 1),
        '根拠の妥当性', JSON_OBJECT('excellent', 5, 'good', 3, 'needs_improvement', 1)
    ),
    1
);