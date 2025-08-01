-- Step 3: Create student_lesson_progress table
CREATE TABLE student_lesson_progress (
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
    
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (lesson_id) REFERENCES curriculum_lessons(id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (rejected_by) REFERENCES users(id) ON DELETE SET NULL,
    
    UNIQUE KEY unique_student_lesson (student_id, lesson_id),
    INDEX idx_student_progress (student_id, started_at),
    INDEX idx_lesson_progress (lesson_id),
    INDEX idx_approval_status (approval_status),
    INDEX idx_completion_request_date (completion_request_date)
);

SELECT 'student_lesson_progress table created' AS result;