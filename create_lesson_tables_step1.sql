-- Step 1: Create curriculum_lessons table
CREATE TABLE curriculum_lessons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    curriculum_id INT NOT NULL,
    lesson_number INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    lesson_type ENUM('lecture', 'practice', 'discussion', 'presentation', 'experiment', 'review') DEFAULT 'lecture',
    duration_minutes INT DEFAULT 50,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (curriculum_id) REFERENCES curriculums(id) ON DELETE CASCADE,
    INDEX idx_curriculum_lesson (curriculum_id, lesson_number),
    INDEX idx_lesson_type (lesson_type)
);

SELECT 'curriculum_lessons table created' AS result;