"""Add idempotency support for transactions and trades

Revision ID: 002
Revises: 001
Create Date: 2026-04-11

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "security_hardening_v1"
branch_labels = None
depends_on = None


def upgrade():
    # Add idempotency_key to transactions table
    op.add_column(
        "transactions", sa.Column("idempotency_key", sa.String(), nullable=True)
    )
    op.create_index(
        "ix_transactions_idempotency_key",
        "transactions",
        ["idempotency_key"],
        unique=True,
    )

    # Create trade_history table for idempotent trade operations
    op.create_table(
        "trade_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(), nullable=False),
        sa.Column("shares", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("total_cost", sa.Float(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trade_history_user_id", "trade_history", ["user_id"])
    op.create_index("ix_trade_history_ticker", "trade_history", ["ticker"])
    op.create_index(
        "ix_trade_history_idempotency_key",
        "trade_history",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index("ix_trade_history_created_at", "trade_history", ["created_at"])


def downgrade():
    # Drop trade_history table
    op.drop_index("ix_trade_history_created_at", table_name="trade_history")
    op.drop_index("ix_trade_history_idempotency_key", table_name="trade_history")
    op.drop_index("ix_trade_history_ticker", table_name="trade_history")
    op.drop_index("ix_trade_history_user_id", table_name="trade_history")
    op.drop_table("trade_history")

    # Remove idempotency_key from transactions
    op.drop_index("ix_transactions_idempotency_key", table_name="transactions")
    op.drop_column("transactions", "idempotency_key")
