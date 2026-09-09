"""add_user_roles_and_target_onboarding

Revision ID: d1c8f4e2a9b3
Revises: a6d4e9f2b7c1
Create Date: 2026-09-04 16:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d1c8f4e2a9b3"
down_revision: Union[str, None] = "a6d4e9f2b7c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. User roles
    op.add_column(
        "users",
        sa.Column("role", sa.String(32), server_default="RESEARCHER", nullable=False),
    )
    op.create_index("ix_users_role", "users", ["role"])
    
    # Sync existing admin accounts to OWNER role
    op.execute("UPDATE users SET role = 'OWNER' WHERE is_admin = true")

    # 2. Target onboarding fields
    op.add_column("targets", sa.Column("company_name", sa.String(255), nullable=True))
    op.add_column("targets", sa.Column("program_source", sa.String(128), server_default="Direct Authorization", nullable=True))
    op.add_column("targets", sa.Column("authorization_source", sa.Text(), nullable=True))
    op.add_column("targets", sa.Column("scope", sa.JSON(), nullable=True))
    op.add_column("targets", sa.Column("scope_type", sa.String(32), server_default="DOMAIN", nullable=True))
    op.add_column("targets", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("targets", sa.Column("authorization_record", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("targets", "authorization_record")
    op.drop_column("targets", "notes")
    op.drop_column("targets", "scope_type")
    op.drop_column("targets", "scope")
    op.drop_column("targets", "authorization_source")
    op.drop_column("targets", "program_source")
    op.drop_column("targets", "company_name")

    op.drop_index("ix_users_role", table_name="users")
    op.drop_column("users", "role")
