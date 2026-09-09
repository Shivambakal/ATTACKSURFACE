"""add_source_registry

Revision ID: b4e7c31d8a29
Revises: a3f8c21e9b47
Create Date: 2026-09-04 10:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4e7c31d8a29'
down_revision: Union[str, None] = 'a3f8c21e9b47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Add tracking_status to companies if not present
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('companies')]
    if 'tracking_status' not in columns:
        op.add_column('companies', sa.Column('tracking_status', sa.String(length=32), server_default='INITIALIZING', nullable=True))

    # 1. company_sources
    op.create_table(
        'company_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('source_type', sa.String(length=64), nullable=False),
        sa.Column('source_subtype', sa.String(length=64), nullable=True),
        sa.Column('authority_level', sa.String(length=64), nullable=False),
        sa.Column('product_scope', sa.String(length=255), nullable=True),
        sa.Column('platform_scope', sa.String(length=128), nullable=True),
        sa.Column('parser_strategy', sa.String(length=64), server_default='generic_feed', nullable=False),
        sa.Column('collection_method', sa.String(length=64), server_default='POLL', nullable=False),
        sa.Column('feed_url', sa.Text(), nullable=True),
        sa.Column('api_url', sa.Text(), nullable=True),
        sa.Column('repository_url', sa.Text(), nullable=True),
        sa.Column('requires_auth', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('credential_name', sa.String(length=64), nullable=True),
        sa.Column('poll_interval_seconds', sa.Integer(), server_default='600', nullable=False),
        sa.Column('priority', sa.String(length=16), server_default='P2', nullable=False),
        sa.Column('enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='NEVER_CHECKED', nullable=False),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_changed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_check_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('etag', sa.String(length=255), nullable=True),
        sa.Column('last_modified', sa.String(length=255), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('parser_version', sa.String(length=32), server_default='1.0.0', nullable=False),
        sa.Column('consecutive_failures', sa.Integer(), server_default='0', nullable=False),
        sa.Column('rate_limit_state', sa.String(length=64), nullable=True),
        sa.Column('last_http_status', sa.Integer(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('coverage_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('coverage_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('historical_capability', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('realtime_capability', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('terms_url', sa.Text(), nullable=True),
        sa.Column('robots_policy', sa.String(length=64), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'source_url', name='uq_company_source_url')
    )
    op.create_index(op.f('ix_company_sources_company_id'), 'company_sources', ['company_id'], unique=False)
    op.create_index(op.f('ix_company_sources_name'), 'company_sources', ['name'], unique=False)
    op.create_index(op.f('ix_company_sources_source_type'), 'company_sources', ['source_type'], unique=False)
    op.create_index(op.f('ix_company_sources_authority_level'), 'company_sources', ['authority_level'], unique=False)
    op.create_index(op.f('ix_company_sources_product_scope'), 'company_sources', ['product_scope'], unique=False)
    op.create_index(op.f('ix_company_sources_platform_scope'), 'company_sources', ['platform_scope'], unique=False)
    op.create_index(op.f('ix_company_sources_priority'), 'company_sources', ['priority'], unique=False)
    op.create_index(op.f('ix_company_sources_enabled'), 'company_sources', ['enabled'], unique=False)
    op.create_index(op.f('ix_company_sources_status'), 'company_sources', ['status'], unique=False)
    op.create_index(op.f('ix_company_sources_next_check_at'), 'company_sources', ['next_check_at'], unique=False)
    op.create_index('ix_company_sources_due', 'company_sources', ['enabled', 'next_check_at'], unique=False)

    # 2. raw_source_snapshots
    op.create_table(
        'raw_source_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('http_status', sa.Integer(), nullable=False),
        sa.Column('etag', sa.String(length=255), nullable=True),
        sa.Column('last_modified', sa.String(length=255), nullable=True),
        sa.Column('content_type', sa.String(length=128), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('body_raw', sa.Text(), nullable=False),
        sa.Column('body_size', sa.Integer(), nullable=False),
        sa.Column('parser_version', sa.String(length=32), server_default='1.0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_id'], ['company_sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_raw_source_snapshots_company_id'), 'raw_source_snapshots', ['company_id'], unique=False)
    op.create_index(op.f('ix_raw_source_snapshots_source_id'), 'raw_source_snapshots', ['source_id'], unique=False)
    op.create_index(op.f('ix_raw_source_snapshots_content_hash'), 'raw_source_snapshots', ['content_hash'], unique=False)
    op.create_index(op.f('ix_raw_source_snapshots_retrieved_at'), 'raw_source_snapshots', ['retrieved_at'], unique=False)
    op.create_index(op.f('ix_raw_source_snapshots_published_at'), 'raw_source_snapshots', ['published_at'], unique=False)
    op.create_index('ix_raw_snapshots_source_hash', 'raw_source_snapshots', ['source_id', 'content_hash'], unique=False)

    # 3. source_collection_runs
    op.create_table(
        'source_collection_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('http_status', sa.Integer(), nullable=True),
        sa.Column('items_found', sa.Integer(), nullable=False),
        sa.Column('items_changed', sa.Integer(), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('raw_snapshot_id', sa.Integer(), nullable=True),
        sa.Column('credits_used', sa.Float(), nullable=False),
        sa.Column('request_count', sa.Integer(), nullable=False),
        sa.Column('response_bytes', sa.Integer(), nullable=False),
        sa.Column('estimated_cost', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['raw_snapshot_id'], ['raw_source_snapshots.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_id'], ['company_sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_source_collection_runs_source_id'), 'source_collection_runs', ['source_id'], unique=False)
    op.create_index(op.f('ix_source_collection_runs_status'), 'source_collection_runs', ['status'], unique=False)

    # 4. normalized_source_documents
    op.create_table(
        'normalized_source_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('raw_snapshot_id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('content_type', sa.String(length=64), nullable=False),
        sa.Column('extracted_items', sa.JSON(), nullable=True),
        sa.Column('parsed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('parser_name', sa.String(length=64), nullable=False),
        sa.Column('parser_version', sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['raw_snapshot_id'], ['raw_source_snapshots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_id'], ['company_sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_normalized_source_documents_company_id'), 'normalized_source_documents', ['company_id'], unique=False)
    op.create_index(op.f('ix_normalized_source_documents_source_id'), 'normalized_source_documents', ['source_id'], unique=False)
    op.create_index(op.f('ix_normalized_source_documents_raw_snapshot_id'), 'normalized_source_documents', ['raw_snapshot_id'], unique=False)

    # 5. source_health
    op.create_table(
        'source_health',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('health_state', sa.String(length=32), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('consecutive_failures', sa.Integer(), nullable=False),
        sa.Column('failure_rate', sa.Float(), nullable=False),
        sa.Column('change_rate', sa.Float(), nullable=False),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['company_sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id')
    )
    op.create_index(op.f('ix_source_health_source_id'), 'source_health', ['source_id'], unique=True)
    op.create_index(op.f('ix_source_health_health_state'), 'source_health', ['health_state'], unique=False)


def downgrade() -> None:
    op.drop_table('source_health')
    op.drop_table('normalized_source_documents')
    op.drop_table('source_collection_runs')
    op.drop_table('raw_source_snapshots')
    op.drop_table('company_sources')
    op.drop_column('companies', 'tracking_status')
