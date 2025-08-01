-- Step 2: Create lesson_tasks table
CREATE TABLE lesson_tasks (
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
    
    FOREIGN KEY (lesson_id) REFERENCES curriculum_lessons(id) ON DELETE CASCADE,
    INDEX idx_lesson_task (lesson_id, task_number),
    INDEX idx_task_required (is_required)
);

SELECT 'lesson_tasks table created' AS result;