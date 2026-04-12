"""add composite index for transactions

Revision ID: 004_composite_idx
Revises: 003
Create Date: 2026-04-12

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '004_composite_idx'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # Add composite index for user_id + timestamp (common query pattern)
    op.create_index('idx_user_timestamp', 'transactions', ['user_id', 'timestamp'], if_not_exists=True)


def downgrade():
    op.drop_index('idx_user_timestamp', table_name='transactions')
