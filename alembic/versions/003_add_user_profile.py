"""add user profile fields

Revision ID: 003
Revises: 002
Create Date: 2026-04-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to users table
    op.add_column('users', sa.Column('monthly_income', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('financial_goal', sa.String(), nullable=True))
    op.add_column('users', sa.Column('savings_target_percent', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('income_frequency', sa.String(), nullable=True))
    op.add_column('users', sa.Column('onboarding_completed', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('users', sa.Column('onboarding_completed_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('users', 'onboarding_completed_at')
    op.drop_column('users', 'onboarding_completed')
    op.drop_column('users', 'income_frequency')
    op.drop_column('users', 'savings_target_percent')
    op.drop_column('users', 'financial_goal')
    op.drop_column('users', 'monthly_income')
