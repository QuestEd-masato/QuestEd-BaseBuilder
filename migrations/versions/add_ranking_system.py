"""Add ranking system models

Revision ID: add_ranking_system
Revises: 
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'add_ranking_system'
down_revision = None  # 最新のリビジョンIDに置き換える必要があります
branch_labels = None
depends_on = None

def upgrade():
    # Ranking テーブルの作成
    op.create_table(
        'ranking',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('ranking_type', sa.Enum('total_points', 'weekly_points', 'monthly_points', 'accuracy_rate', 'study_time', 'consistency'), nullable=False),
        sa.Column('score', sa.Numeric(precision=10, scale=2), nullable=False, default=0.00),
        sa.Column('rank_position', sa.Integer(), nullable=True),
        sa.Column('scope', sa.Enum('school', 'class'), nullable=False, default='school'),
        sa.Column('scope_id', sa.Integer(), nullable=True),
        sa.Column('period_start', sa.DateTime(), nullable=True),
        sa.Column('period_end', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['student_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # インデックスの作成
    op.create_index('idx_student_type', 'ranking', ['student_id', 'ranking_type'])
    op.create_index('idx_scope_type', 'ranking', ['scope', 'scope_id', 'ranking_type'])
    op.create_index('idx_rank_period', 'ranking', ['rank_position', 'period_start', 'period_end'])
    
    # RankingCache テーブルの作成
    op.create_table(
        'ranking_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cache_key', sa.String(255), nullable=False),
        sa.Column('ranking_type', sa.Enum('total_points', 'weekly_points', 'monthly_points', 'accuracy_rate', 'study_time', 'consistency'), nullable=False),
        sa.Column('scope', sa.Enum('school', 'class'), nullable=False),
        sa.Column('scope_id', sa.Integer(), nullable=True),
        sa.Column('ranking_data', sa.Text(), nullable=False),
        sa.Column('participant_count', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cache_key')
    )
    
    # インデックスの作成
    op.create_index('idx_cache_key', 'ranking_cache', ['cache_key'])
    op.create_index('idx_expiry', 'ranking_cache', ['expires_at'])

def downgrade():
    # インデックスの削除
    op.drop_index('idx_expiry', 'ranking_cache')
    op.drop_index('idx_cache_key', 'ranking_cache')
    op.drop_index('idx_rank_period', 'ranking')
    op.drop_index('idx_scope_type', 'ranking')
    op.drop_index('idx_student_type', 'ranking')
    
    # テーブルの削除
    op.drop_table('ranking_cache')
    op.drop_table('ranking')