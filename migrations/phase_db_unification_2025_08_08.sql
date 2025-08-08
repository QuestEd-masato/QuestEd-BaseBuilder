-- QuestEd Database Structure Unification Script
-- Date: 2025-08-08
-- Purpose: Synchronize RDS database structure with local development structure
-- Author: Claude Code Assistant
-- 
-- IMPORTANT: This script should be executed on RDS through EC2 instance
-- Run with: mysql -u QuestEd -p'QuestEd-03012025MySQL' -h database-1.cdk0iio0s90g.ap-northeast-1.rds.amazonaws.com quested < phase_db_unification_2025_08_08.sql

-- =============================================================================
-- Phase 1: Zero Risk Updates - student_milestones table (0 records)
-- =============================================================================

-- Backup verification
SELECT 'Phase 1: Starting student_milestones updates' as status, NOW() as timestamp;
SELECT 'Current student_milestones record count:' as info, COUNT(*) as count FROM student_milestones;

-- Add is_completed column if it doesn't exist
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = 'quested' 
       AND TABLE_NAME = 'student_milestones' 
       AND COLUMN_NAME = 'is_completed') = 0,
    'ALTER TABLE student_milestones ADD COLUMN is_completed TINYINT(1) DEFAULT 0',
    'SELECT "is_completed column already exists" as status'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT 'Phase 1 completed successfully' as status, NOW() as timestamp;

-- =============================================================================
-- Phase 2: Low Risk Updates - curriculum_units table (8 records)  
-- =============================================================================

SELECT 'Phase 2: Starting curriculum_units updates' as status, NOW() as timestamp;
SELECT 'Current curriculum_units record count:' as info, COUNT(*) as count FROM curriculum_units;

-- Add mastery_threshold column if it doesn't exist
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = 'quested' 
       AND TABLE_NAME = 'curriculum_units' 
       AND COLUMN_NAME = 'mastery_threshold') = 0,
    'ALTER TABLE curriculum_units ADD COLUMN mastery_threshold INT DEFAULT 80',
    'SELECT "mastery_threshold column already exists" as status'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add self_paced_mode column if it doesn't exist
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = 'quested' 
       AND TABLE_NAME = 'curriculum_units' 
       AND COLUMN_NAME = 'self_paced_mode') = 0,
    'ALTER TABLE curriculum_units ADD COLUMN self_paced_mode TINYINT(1) DEFAULT 0',
    'SELECT "self_paced_mode column already exists" as status'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add prerequisite_skills column if it doesn't exist
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = 'quested' 
       AND TABLE_NAME = 'curriculum_units' 
       AND COLUMN_NAME = 'prerequisite_skills') = 0,
    'ALTER TABLE curriculum_units ADD COLUMN prerequisite_skills TEXT',
    'SELECT "prerequisite_skills column already exists" as status'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT 'Phase 2 completed successfully' as status, NOW() as timestamp;

-- =============================================================================
-- Phase 3: Medium Risk Updates - student_unit_selections table (546 records)
-- =============================================================================

SELECT 'Phase 3: Starting student_unit_selections updates' as status, NOW() as timestamp;
SELECT 'Current student_unit_selections record count:' as info, COUNT(*) as count FROM student_unit_selections;

-- Add rejection_date column if it doesn't exist  
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = 'quested' 
       AND TABLE_NAME = 'student_unit_selections' 
       AND COLUMN_NAME = 'rejection_date') = 0,
    'ALTER TABLE student_unit_selections ADD COLUMN rejection_date DATETIME NULL',
    'SELECT "rejection_date column already exists" as status'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add rejection_reason column if it doesn't exist
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = 'quested' 
       AND TABLE_NAME = 'student_unit_selections' 
       AND COLUMN_NAME = 'rejection_reason') = 0,
    'ALTER TABLE student_unit_selections ADD COLUMN rejection_reason TEXT',
    'SELECT "rejection_reason column already exists" as status'  
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add notes column if it doesn't exist
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = 'quested' 
       AND TABLE_NAME = 'student_unit_selections' 
       AND COLUMN_NAME = 'notes') = 0,
    'ALTER TABLE student_unit_selections ADD COLUMN notes TEXT',
    'SELECT "notes column already exists" as status'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add completion_notes column if it doesn't exist
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = 'quested' 
       AND TABLE_NAME = 'student_unit_selections' 
       AND COLUMN_NAME = 'completion_notes') = 0,
    'ALTER TABLE student_unit_selections ADD COLUMN completion_notes TEXT',
    'SELECT "completion_notes column already exists" as status'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add points_awarded column if it doesn't exist
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = 'quested' 
       AND TABLE_NAME = 'student_unit_selections' 
       AND COLUMN_NAME = 'points_awarded') = 0,
    'ALTER TABLE student_unit_selections ADD COLUMN points_awarded TINYINT(1) DEFAULT 0',
    'SELECT "points_awarded column already exists" as status'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add points_awarded_at column if it doesn't exist
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = 'quested' 
       AND TABLE_NAME = 'student_unit_selections' 
       AND COLUMN_NAME = 'points_awarded_at') = 0,
    'ALTER TABLE student_unit_selections ADD COLUMN points_awarded_at DATETIME NULL',
    'SELECT "points_awarded_at column already exists" as status'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT 'Phase 3 completed successfully' as status, NOW() as timestamp;

-- =============================================================================
-- Final Verification and Summary
-- =============================================================================

SELECT 'DATABASE UNIFICATION COMPLETED' as status, NOW() as completion_time;

-- Verify all columns were added successfully
SELECT 'Final verification - student_milestones columns:' as info;
SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = 'quested' AND TABLE_NAME = 'student_milestones'
ORDER BY ORDINAL_POSITION;

SELECT 'Final verification - curriculum_units columns:' as info;
SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = 'quested' AND TABLE_NAME = 'curriculum_units'  
ORDER BY ORDINAL_POSITION;

SELECT 'Final verification - student_unit_selections columns:' as info;
SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = 'quested' AND TABLE_NAME = 'student_unit_selections'
ORDER BY ORDINAL_POSITION;

-- Record counts should be unchanged
SELECT 'student_milestones' as table_name, COUNT(*) as records FROM student_milestones;
SELECT 'curriculum_units' as table_name, COUNT(*) as records FROM curriculum_units;
SELECT 'student_unit_selections' as table_name, COUNT(*) as records FROM student_unit_selections;

SELECT 'All phases completed successfully! RDS structure now matches local database.' as final_status;