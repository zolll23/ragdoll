"""add_failed_reindexing_fields

Revision ID: add_failed_reindexing_fields
Revises: add_tokens_used
Create Date: 2025-12-26 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'add_failed_reindexing_fields'
down_revision = 'add_tokens_used'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('projects', sa.Column('is_reindexing_failed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('projects', sa.Column('reindexing_failed_task_id', sa.String(255), nullable=True))
    op.add_column('projects', sa.Column('failed_entities_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('projects', sa.Column('reindexed_failed_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('projects', sa.Column('reindexing_failed_status', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('projects', 'reindexing_failed_status')
    op.drop_column('projects', 'reindexed_failed_count')
    op.drop_column('projects', 'failed_entities_count')
    op.drop_column('projects', 'reindexing_failed_task_id')
    op.drop_column('projects', 'is_reindexing_failed')
