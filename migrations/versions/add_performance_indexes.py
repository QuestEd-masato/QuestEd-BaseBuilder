"""Add performance indexes for ranking queries

Revision ID: performance_indexes_001
Revises: ranking_tables_001
Create Date: 2025-01-15 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'performance_indexes_001'
down_revision = 'ranking_tables_001'
branch_labels = None
depends_on = None


def upgrade():
    # ActivityLog indexes for ranking calculations
    op.create_index('idx_activity_log_student_created', 'activity_logs', ['student_id', 'created_at'])
    op.create_index('idx_activity_log_duration', 'activity_logs', ['study_duration'])
    
    # StudentUnitSelection indexes
    op.create_index('idx_unit_selection_student_progress', 'student_unit_selections', ['student_id', 'progress_percentage'])
    op.create_index('idx_unit_selection_completed', 'student_unit_selections', ['student_id', 'status'])
    
    # User indexes for ranking queries
    op.create_index('idx_users_role_active_school', 'users', ['role', 'is_active', 'school_id'])
    
    # ClassEnrollment indexes
    op.create_index('idx_class_enrollment_active', 'class_enrollments', ['class_id', 'student_id', 'is_active'])


def downgrade():
    op.drop_index('idx_class_enrollment_active', table_name='class_enrollments')
    op.drop_index('idx_users_role_active_school', table_name='users')
    op.drop_index('idx_unit_selection_completed', table_name='student_unit_selections')
    op.drop_index('idx_unit_selection_student_progress', table_name='student_unit_selections')
    op.drop_index('idx_activity_log_duration', table_name='activity_logs')
    op.drop_index('idx_activity_log_student_created', table_name='activity_logs')