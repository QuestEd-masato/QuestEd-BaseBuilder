-- Migration: Add resubmission_count field to student_unit_selections table
-- Purpose: Track the number of times a student has resubmitted an approval request
-- Date: 2025-01-16
-- Author: Claude Code Assistant

-- Add resubmission_count column to student_unit_selections table
ALTER TABLE student_unit_selections 
ADD COLUMN resubmission_count INT DEFAULT 0 
COMMENT 'Number of times resubmitted after rejection';

-- Update existing records to have 0 resubmissions
UPDATE student_unit_selections 
SET resubmission_count = 0 
WHERE resubmission_count IS NULL;

-- Add index for better query performance
CREATE INDEX idx_resubmission_count ON student_unit_selections(resubmission_count);

-- Add a few additional fields that might be useful for approval workflow
ALTER TABLE student_unit_selections 
ADD COLUMN completion_notes TEXT 
COMMENT 'Student notes when requesting completion';

ALTER TABLE student_unit_selections 
ADD COLUMN resubmission_notes TEXT 
COMMENT 'Student notes explaining improvements for resubmission';

ALTER TABLE student_unit_selections 
ADD COLUMN rejection_date DATETIME 
COMMENT 'Date when the request was rejected';

ALTER TABLE student_unit_selections 
ADD COLUMN rejected_by INT 
COMMENT 'Teacher ID who rejected the request';

-- Add foreign key constraint for rejected_by
ALTER TABLE student_unit_selections 
ADD CONSTRAINT fk_rejected_by 
FOREIGN KEY (rejected_by) REFERENCES users(id);

-- Add index for rejection tracking
CREATE INDEX idx_rejection_date ON student_unit_selections(rejection_date);
CREATE INDEX idx_rejected_by ON student_unit_selections(rejected_by);

-- Verify the schema changes
DESCRIBE student_unit_selections;