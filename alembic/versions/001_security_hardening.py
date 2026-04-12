"""
Database Migration: Add Security Constraints and Audit Tables

Run with: alembic upgrade head
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision = "security_hardening_v1"
down_revision = "000"
branch_labels = None
depends_on = None


def upgrade():
    """Apply security hardening"""

    # Add audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column("details", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "timestamp", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for audit logs
    op.create_index("idx_audit_user_id", "audit_logs", ["user_id"])
    op.create_index("idx_audit_action", "audit_logs", ["action"])
    op.create_index("idx_audit_resource", "audit_logs", ["resource"])
    op.create_index("idx_audit_status", "audit_logs", ["status"])
    op.create_index("idx_audit_timestamp", "audit_logs", ["timestamp"])
    op.create_index("idx_audit_request_id", "audit_logs", ["request_id"])
    op.create_index(
        "idx_audit_user_action_time", "audit_logs", ["user_id", "action", "timestamp"]
    )
    op.create_index("idx_audit_resource_time", "audit_logs", ["resource", "timestamp"])

    # Add check constraints to existing tables

    # Users table
    op.create_check_constraint("check_balance_non_negative", "users", "balance >= 0")

    op.create_check_constraint(
        "check_password_hash_not_empty", "users", "length(password_hash) > 0"
    )

    # Transactions table
    op.create_check_constraint("check_amount_positive", "transactions", "amount > 0")

    # Add composite indexes
    op.create_index("idx_user_timestamp", "transactions", ["user_id", "timestamp"])
    op.create_index("idx_user_type", "transactions", ["user_id", "type"])

    # Predictions table
    op.create_check_constraint(
        "check_confidence_range", "predictions", "confidence >= 0 AND confidence <= 1"
    )

    op.create_check_constraint(
        "check_days_left_non_negative",
        "predictions",
        "days_left IS NULL OR days_left >= 0",
    )

    op.create_index("idx_user_active", "predictions", ["user_id", "is_active"])

    # Stocks table
    op.create_check_constraint("check_price_positive", "stocks", "price > 0")

    op.create_check_constraint("check_volume_non_negative", "stocks", "volume >= 0")

    # Portfolios table
    op.create_check_constraint("check_shares_positive", "portfolios", "shares > 0")

    op.create_check_constraint(
        "check_avg_price_positive", "portfolios", "avg_price > 0"
    )

    op.create_index("idx_user_ticker", "portfolios", ["user_id", "ticker"])

    # Lessons table
    op.create_check_constraint(
        "check_duration_positive", "lessons", "duration_minutes > 0"
    )

    op.create_check_constraint("check_xp_non_negative", "lessons", "xp_reward >= 0")

    # User progress table
    op.create_check_constraint(
        "check_score_range",
        "user_progress",
        "score IS NULL OR (score >= 0 AND score <= 100)",
    )

    op.create_index("idx_user_lesson", "user_progress", ["user_id", "lesson_id"])

    # Achievements table
    op.create_check_constraint(
        "check_achievement_xp_non_negative", "achievements", "xp_reward >= 0"
    )

    # Daily missions table
    op.create_check_constraint(
        "check_progress_non_negative", "daily_missions", "progress >= 0"
    )

    op.create_check_constraint("check_target_positive", "daily_missions", "target > 0")

    op.create_check_constraint(
        "check_mission_xp_non_negative", "daily_missions", "xp_reward >= 0"
    )

    # User market responses table
    op.create_check_constraint(
        "check_response_xp_non_negative", "user_market_responses", "xp_earned >= 0"
    )

    # Adaptive profiles table
    op.create_check_constraint(
        "check_velocity_positive", "adaptive_profiles", "learning_velocity > 0"
    )

    op.create_check_constraint(
        "check_total_questions_non_negative",
        "adaptive_profiles",
        "total_questions >= 0",
    )

    op.create_check_constraint(
        "check_correct_answers_non_negative",
        "adaptive_profiles",
        "correct_answers >= 0",
    )

    op.create_check_constraint(
        "check_correct_lte_total",
        "adaptive_profiles",
        "correct_answers <= total_questions",
    )

    # Adaptive answers table
    op.create_check_constraint(
        "check_time_non_negative", "adaptive_answers", "time_ms >= 0"
    )

    op.create_index("idx_user_topic", "adaptive_answers", ["user_id", "topic"])

    print("✅ Security constraints and audit tables created successfully")


def downgrade():
    """Remove security hardening"""

    # Drop audit logs table
    op.drop_table("audit_logs")

    # Drop check constraints (order matters - reverse of upgrade)
    op.drop_constraint("check_time_non_negative", "adaptive_answers")
    op.drop_constraint("check_correct_lte_total", "adaptive_profiles")
    op.drop_constraint("check_correct_answers_non_negative", "adaptive_profiles")
    op.drop_constraint("check_total_questions_non_negative", "adaptive_profiles")
    op.drop_constraint("check_velocity_positive", "adaptive_profiles")
    op.drop_constraint("check_response_xp_non_negative", "user_market_responses")
    op.drop_constraint("check_mission_xp_non_negative", "daily_missions")
    op.drop_constraint("check_target_positive", "daily_missions")
    op.drop_constraint("check_progress_non_negative", "daily_missions")
    op.drop_constraint("check_achievement_xp_non_negative", "achievements")
    op.drop_constraint("check_score_range", "user_progress")
    op.drop_constraint("check_xp_non_negative", "lessons")
    op.drop_constraint("check_duration_positive", "lessons")
    op.drop_constraint("check_avg_price_positive", "portfolios")
    op.drop_constraint("check_shares_positive", "portfolios")
    op.drop_constraint("check_volume_non_negative", "stocks")
    op.drop_constraint("check_price_positive", "stocks")
    op.drop_constraint("check_days_left_non_negative", "predictions")
    op.drop_constraint("check_confidence_range", "predictions")
    op.drop_constraint("check_amount_positive", "transactions")
    op.drop_constraint("check_password_hash_not_empty", "users")
    op.drop_constraint("check_balance_non_negative", "users")

    print("⚠️  Security constraints removed")
