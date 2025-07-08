"""Add grade and classroom fields to users and classes

Revision ID: add_grade_classroom
Revises: 6dc600a81f1f
Create Date: 2025-01-08 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_grade_classroom'
down_revision = 'add_ranking_system'
branch_labels = None
depends_on = None


def upgrade():
    # Add grade, classroom, and student_number to users table
    op.add_column('users', sa.Column('grade', sa.Integer(), nullable=True, comment='学年(1-12)'))
    op.add_column('users', sa.Column('classroom', sa.String(10), nullable=True, comment='学級(1組、A組等)'))
    op.add_column('users', sa.Column('student_number', sa.String(20), nullable=True, comment='生徒番号'))
    
    # Add grade and classroom to classes table
    op.add_column('classes', sa.Column('grade', sa.Integer(), nullable=True, comment='対象学年'))
    op.add_column('classes', sa.Column('classroom', sa.String(10), nullable=True, comment='学級名'))
    
    # Create indexes for better query performance
    op.create_index('idx_users_grade_classroom', 'users', ['grade', 'classroom'])
    op.create_index('idx_users_student_number', 'users', ['student_number'])
    op.create_index('idx_classes_grade_classroom', 'classes', ['grade', 'classroom'])
    
    # Add check constraints to ensure valid grade values
    op.execute("""
        ALTER TABLE users ADD CONSTRAINT chk_users_grade 
        CHECK (grade IS NULL OR (grade >= 1 AND grade <= 12))
    """)
    
    op.execute("""
        ALTER TABLE classes ADD CONSTRAINT chk_classes_grade 
        CHECK (grade IS NULL OR (grade >= 1 AND grade <= 12))
    """)


def downgrade():
    # Remove constraints
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_grade")
    op.execute("ALTER TABLE classes DROP CONSTRAINT IF EXISTS chk_classes_grade")
    
    # Remove indexes
    op.drop_index('idx_classes_grade_classroom', 'classes')
    op.drop_index('idx_users_student_number', 'users')
    op.drop_index('idx_users_grade_classroom', 'users')
    
    # Remove columns
    op.drop_column('classes', 'classroom')
    op.drop_column('classes', 'grade')
    op.drop_column('users', 'student_number')
    op.drop_column('users', 'classroom')
    op.drop_column('users', 'grade')