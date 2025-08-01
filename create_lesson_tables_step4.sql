-- Step 4: Create student_task_checks table
CREATE TABLE student_task_checks (
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
    
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (lesson_progress_id) REFERENCES student_lesson_progress(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES lesson_tasks(id) ON DELETE CASCADE,
    
    UNIQUE KEY unique_student_task_check (student_id, lesson_progress_id, task_id),
    INDEX idx_student_task_status (student_id, status),
    INDEX idx_lesson_progress_tasks (lesson_progress_id),
    INDEX idx_task_checks (task_id),
    INDEX idx_checked_at (checked_at)
);

SELECT 'student_task_checks table created' AS result;