"""Merge all migration heads for clean EC2 to RDS migration

Revision ID: e98ec96c00ef
Revises: c551f5848565
Create Date: 2025-07-09 01:41:24.123097

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e98ec96c00ef'
down_revision = 'c551f5848565'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
