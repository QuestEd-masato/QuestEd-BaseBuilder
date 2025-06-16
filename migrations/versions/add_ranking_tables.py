"""Add ranking tables

Revision ID: ranking_tables_001
Revises: [previous_revision]
Create Date: 2025-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers
revision = 'ranking_tables_001'
down_revision = None  # 実際の前のリビジョンIDに置き換える
branch_labels = None
depends_on = None


def upgrade():
    # Rankings table
    op.create_table('rankings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('school_id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=True),
        sa.Column('ranking_type', sa.Enum('total_points', 'weekly_points', 'monthly_points', 'accuracy_rate', 'study_time', 'consistency'), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('rank_position', sa.Integer(), nullable=False),
        sa.Column('score', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('total_participants', sa.Integer(), nullable=False),
        sa.Column('detailed_stats', sa.JSON(), nullable=True),
        sa.Column('calculated_at', sa.DateTime(), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], ),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Rankings indexes
    op.create_index('idx_ranking_type_period', 'rankings', ['ranking_type', 'period_start', 'period_end'])
    op.create_index('idx_ranking_student_type', 'rankings', ['student_id', 'ranking_type'])
    op.create_index('idx_ranking_class_type', 'rankings', ['class_id', 'ranking_type'])
    op.create_index('idx_ranking_current', 'rankings', ['is_current', 'ranking_type'])
    
    # Ranking cache table
    op.create_table('ranking_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cache_key', sa.String(length=200), nullable=False),
        sa.Column('ranking_type', sa.String(length=50), nullable=False),
        sa.Column('scope', sa.Enum('school', 'class'), nullable=False),
        sa.Column('scope_id', sa.Integer(), nullable=False),
        sa.Column('ranking_data', sa.JSON(), nullable=False),
        sa.Column('participant_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Ranking cache indexes
    op.create_index(op.f('ix_ranking_cache_cache_key'), 'ranking_cache', ['cache_key'], unique=True)
    op.create_index('idx_ranking_cache_expires', 'ranking_cache', ['expires_at'])


def downgrade():
    op.drop_index('idx_ranking_cache_expires', table_name='ranking_cache')
    op.drop_index(op.f('ix_ranking_cache_cache_key'), table_name='ranking_cache')
    op.drop_table('ranking_cache')
    
    op.drop_index('idx_ranking_current', table_name='rankings')
    op.drop_index('idx_ranking_class_type', table_name='rankings')
    op.drop_index('idx_ranking_student_type', table_name='rankings')
    op.drop_index('idx_ranking_type_period', table_name='rankings')
    op.drop_table('rankings')