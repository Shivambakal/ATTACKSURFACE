"""add_50_target_trial_ledger

Revision ID: a6d4e9f2b7c1
Revises: f2b9c6d1a4e7
Create Date: 2026-09-04 12:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a6d4e9f2b7c1"
down_revision: Union[str, None] = "f2b9c6d1a4e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trial_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, server_default="50 Target Trial"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("status", sa.String(32), nullable=False, server_default="created"),
        sa.Column("registry_source", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )
    op.create_index("ix_trial_runs_started_at", "trial_runs", ["started_at"])
    op.create_index("ix_trial_runs_status", "trial_runs", ["status"])
    op.create_table(
        "trial_targets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trial_run_id", sa.Integer(), sa.ForeignKey("trial_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_id", sa.Integer(), sa.ForeignKey("targets.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("primary_domain", sa.String(255), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("authorization_source", sa.Text(), nullable=False),
        sa.Column("source", sa.String(128), nullable=False),
        sa.Column("collection_status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("last_successful_collection", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.UniqueConstraint("trial_run_id", "target_id", name="uq_trial_target_run_target"),
    )
    op.create_index("ix_trial_targets_trial_run_id", "trial_targets", ["trial_run_id"])
    op.create_index("ix_trial_targets_target_id", "trial_targets", ["target_id"])
    op.create_index("ix_trial_targets_company_id", "trial_targets", ["company_id"])
    op.create_index("ix_trial_targets_collection_status", "trial_targets", ["collection_status"])


def downgrade() -> None:
    op.drop_table("trial_targets")
    op.drop_table("trial_runs")
