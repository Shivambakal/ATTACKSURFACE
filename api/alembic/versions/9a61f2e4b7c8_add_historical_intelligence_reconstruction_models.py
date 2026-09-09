"""add_historical_intelligence_reconstruction_models

Revision ID: 9a61f2e4b7c8
Revises: 8950e15cebcb
Create Date: 2026-09-04 01:50:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a61f2e4b7c8'
down_revision: Union[str, None] = '8950e15cebcb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create historical_coverages table
    op.create_table(
        'historical_coverages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), unique=True, index=True, nullable=False),
        sa.Column('coverage_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('coverage_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('sources_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('confirmed_events_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('estimated_events_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('partial_periods', sa.JSON(), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 2. Create historical_releases table
    op.create_table(
        'historical_releases',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), index=True, nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), index=True, nullable=True),
        sa.Column('repository_id', sa.String(length=255), nullable=True, index=True),
        sa.Column('version', sa.String(length=64), nullable=True),
        sa.Column('tag', sa.String(length=128), nullable=False, index=True),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.95'),
        sa.Column('semantic_changes', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 3. Alter security_events table with vulnerability_class and historical fields
    with op.batch_alter_table('security_events') as batch_op:
        batch_op.add_column(sa.Column('vulnerability_class', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('affected_component', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('affected_versions', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('confidence', sa.Float(), nullable=False, server_default='0.9'))
        batch_op.add_column(sa.Column('evidence', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('source_url', sa.Text(), nullable=True))

    # 4. Alter timeline_events table
    with op.batch_alter_table('timeline_events') as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=True))
        batch_op.add_column(sa.Column('provenance_category', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('temporal_category', sa.String(length=32), nullable=False, server_default='CURRENT'))
        batch_op.add_column(sa.Column('quality_badge', sa.String(length=32), nullable=False, server_default='CONFIRMED_HISTORY'))
        batch_op.add_column(sa.Column('effective_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.alter_column('target_id', existing_type=sa.Integer(), nullable=True)

    # 5. Alter program_scope_rules table
    with op.batch_alter_table('program_scope_rules') as batch_op:
        batch_op.add_column(sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('valid_to', sa.DateTime(timezone=True), nullable=True))

    # 6. Alter assets table
    with op.batch_alter_table('assets') as batch_op:
        batch_op.add_column(sa.Column('lifecycle_status', sa.String(length=32), nullable=False, server_default='ACTIVE'))


def downgrade() -> None:
    with op.batch_alter_table('assets') as batch_op:
        batch_op.drop_column('lifecycle_status')

    with op.batch_alter_table('program_scope_rules') as batch_op:
        batch_op.drop_column('valid_to')
        batch_op.drop_column('valid_from')

    with op.batch_alter_table('timeline_events') as batch_op:
        batch_op.drop_column('effective_at')
        batch_op.drop_column('quality_badge')
        batch_op.drop_column('temporal_category')
        batch_op.drop_column('provenance_category')
        batch_op.drop_column('company_id')

    with op.batch_alter_table('security_events') as batch_op:
        batch_op.drop_column('source_url')
        batch_op.drop_column('evidence')
        batch_op.drop_column('confidence')
        batch_op.drop_column('affected_versions')
        batch_op.drop_column('affected_component')
        batch_op.drop_column('vulnerability_class')

    op.drop_table('historical_releases')
    op.drop_table('historical_coverages')
