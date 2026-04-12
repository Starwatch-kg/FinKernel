"""Initial database schema

Revision ID: 000
Revises:
Create Date: 2026-04-11

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column("balance", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    # Create transactions table
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column(
            "type", sa.Enum("income", "expense", name="transactiontype"), nullable=True
        ),
        sa.Column(
            "category",
            sa.Enum(
                "food",
                "transport",
                "entertainment",
                "education",
                "salary",
                "other",
                name="transactioncategory",
            ),
            nullable=True,
        ),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_transactions_id"), "transactions", ["id"], unique=False)
    op.create_index(
        op.f("ix_transactions_timestamp"), "transactions", ["timestamp"], unique=False
    )
    op.create_index(
        op.f("ix_transactions_user_id"), "transactions", ["user_id"], unique=False
    )

    # Create predictions table
    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("days_left", sa.Float(), nullable=True),
        sa.Column("predicted_date", sa.DateTime(), nullable=True),
        sa.Column(
            "risk_level",
            sa.Enum("safe", "warning", "danger", "critical", name="risklevel"),
            nullable=True,
        ),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("features", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("recommendation", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_predictions_created_at"), "predictions", ["created_at"], unique=False
    )
    op.create_index(op.f("ix_predictions_id"), "predictions", ["id"], unique=False)
    op.create_index(
        op.f("ix_predictions_is_active"), "predictions", ["is_active"], unique=False
    )
    op.create_index(
        op.f("ix_predictions_user_id"), "predictions", ["user_id"], unique=False
    )

    # Create stocks table
    op.create_table(
        "stocks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("change_percent", sa.Float(), nullable=True),
        sa.Column("volume", sa.Integer(), nullable=True),
        sa.Column("market_cap", sa.Float(), nullable=True),
        sa.Column("sector", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stocks_id"), "stocks", ["id"], unique=False)
    op.create_index(op.f("ix_stocks_ticker"), "stocks", ["ticker"], unique=True)

    # Create portfolios table
    op.create_table(
        "portfolios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("ticker", sa.String(), nullable=True),
        sa.Column("shares", sa.Integer(), nullable=True),
        sa.Column("avg_price", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_portfolios_id"), "portfolios", ["id"], unique=False)
    op.create_index(
        op.f("ix_portfolios_ticker"), "portfolios", ["ticker"], unique=False
    )
    op.create_index(
        op.f("ix_portfolios_user_id"), "portfolios", ["user_id"], unique=False
    )

    # Create modules table
    op.create_table(
        "modules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("icon", sa.String(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_modules_id"), "modules", ["id"], unique=False)

    # Create lessons table
    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("module_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("content", sa.String(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("xp_reward", sa.Integer(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=True),
        sa.Column("questions", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(
            ["module_id"],
            ["modules.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lessons_id"), "lessons", ["id"], unique=False)
    op.create_index(
        op.f("ix_lessons_module_id"), "lessons", ["module_id"], unique=False
    )

    # Create user_progress table
    op.create_table(
        "user_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("lesson_id", sa.Integer(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_progress_id"), "user_progress", ["id"], unique=False)
    op.create_index(
        op.f("ix_user_progress_lesson_id"), "user_progress", ["lesson_id"], unique=False
    )
    op.create_index(
        op.f("ix_user_progress_user_id"), "user_progress", ["user_id"], unique=False
    )

    # Create achievements table
    op.create_table(
        "achievements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("icon", sa.String(), nullable=True),
        sa.Column("xp_reward", sa.Integer(), nullable=True),
        sa.Column("unlocked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_achievements_id"), "achievements", ["id"], unique=False)
    op.create_index(
        op.f("ix_achievements_user_id"), "achievements", ["user_id"], unique=False
    )

    # Create daily_missions table
    op.create_table(
        "daily_missions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=True),
        sa.Column("target", sa.Integer(), nullable=True),
        sa.Column("xp_reward", sa.Integer(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=True),
        sa.Column("date", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_daily_missions_date"), "daily_missions", ["date"], unique=False
    )
    op.create_index(
        op.f("ix_daily_missions_id"), "daily_missions", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_daily_missions_user_id"), "daily_missions", ["user_id"], unique=False
    )

    # Create market_events table
    op.create_table(
        "market_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("impact", sa.String(), nullable=True),
        sa.Column("options", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("correct_option", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_market_events_id"), "market_events", ["id"], unique=False)

    # Create user_market_responses table
    op.create_table(
        "user_market_responses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("event_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("xp_earned", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["market_events.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_market_responses_event_id"),
        "user_market_responses",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_market_responses_id"),
        "user_market_responses",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_market_responses_user_id"),
        "user_market_responses",
        ["user_id"],
        unique=False,
    )

    # Create adaptive_profiles table
    op.create_table(
        "adaptive_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column(
            "mastery_scores", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("learning_velocity", sa.Float(), nullable=True),
        sa.Column("preferred_difficulty", sa.String(), nullable=True),
        sa.Column("weak_topics", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "strong_topics", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("total_questions", sa.Integer(), nullable=True),
        sa.Column("correct_answers", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_adaptive_profiles_id"), "adaptive_profiles", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_adaptive_profiles_user_id"),
        "adaptive_profiles",
        ["user_id"],
        unique=True,
    )

    # Create adaptive_answers table
    op.create_table(
        "adaptive_answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("topic", sa.String(), nullable=True),
        sa.Column("question_id", sa.String(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("time_ms", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_adaptive_answers_created_at"),
        "adaptive_answers",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_adaptive_answers_id"), "adaptive_answers", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_adaptive_answers_topic"), "adaptive_answers", ["topic"], unique=False
    )
    op.create_index(
        op.f("ix_adaptive_answers_user_id"),
        "adaptive_answers",
        ["user_id"],
        unique=False,
    )

    # Create diary_entries table
    op.create_table(
        "diary_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("content", sa.String(), nullable=True),
        sa.Column("mood", sa.String(), nullable=True),
        sa.Column("tags", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_diary_entries_created_at"),
        "diary_entries",
        ["created_at"],
        unique=False,
    )
    op.create_index(op.f("ix_diary_entries_id"), "diary_entries", ["id"], unique=False)
    op.create_index(
        op.f("ix_diary_entries_user_id"), "diary_entries", ["user_id"], unique=False
    )


def downgrade():
    op.drop_table("diary_entries")
    op.drop_table("adaptive_answers")
    op.drop_table("adaptive_profiles")
    op.drop_table("user_market_responses")
    op.drop_table("market_events")
    op.drop_table("daily_missions")
    op.drop_table("achievements")
    op.drop_table("user_progress")
    op.drop_table("lessons")
    op.drop_table("modules")
    op.drop_table("portfolios")
    op.drop_table("stocks")
    op.drop_table("predictions")
    op.drop_table("transactions")
    op.drop_table("users")
