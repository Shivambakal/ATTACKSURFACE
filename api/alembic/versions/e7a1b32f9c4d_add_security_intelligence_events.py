"""add_security_intelligence_events

Revision ID: e7a1b32f9c4d
Revises: c5f8d42e0a3b
Create Date: 2026-09-04 11:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7a1b32f9c4d'
down_revision: Union[str, None] = 'c5f8d42e0a3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'security_intelligence_events' not in tables:
        op.create_table(
            'security_intelligence_events',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=500), nullable=False),
            sa.Column('summary', sa.Text(), nullable=False),
            sa.Column('event_type', sa.String(length=64), nullable=False, server_default='SECURITY_NEWS'),
            sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('source_url', sa.Text(), nullable=False),
            sa.Column('source_name', sa.String(length=255), nullable=False, server_default='Web'),
            sa.Column('additional_sources', sa.JSON(), nullable=False, server_default='[]'),
            sa.Column('cve_ids', sa.JSON(), nullable=False, server_default='[]'),
            sa.Column('cwe_ids', sa.JSON(), nullable=False, server_default='[]'),
            sa.Column('affected_products', sa.JSON(), nullable=False, server_default='[]'),
            sa.Column('affected_companies', sa.JSON(), nullable=False, server_default='[]'),
            sa.Column('severity', sa.String(length=32), nullable=False, server_default='UNKNOWN'),
            sa.Column('actively_exploited', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('known_exploitation_evidence', sa.Text(), nullable=True),
            sa.Column('security_relevance', sa.Text(), nullable=True),
            sa.Column('confidence', sa.Float(), nullable=False, server_default='0.7'),
            sa.Column('fingerprint', sa.String(length=64), nullable=False),
            sa.Column('parser_version', sa.String(length=32), nullable=False, server_default='1.0.0'),
            sa.Column('severity_score', sa.Integer(), nullable=False, server_default='50'),
            sa.Column('freshness_score', sa.Integer(), nullable=False, server_default='50'),
            sa.Column('exploitation_score', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('relevance_score', sa.Integer(), nullable=False, server_default='50'),
            sa.Column('priority_score', sa.Integer(), nullable=False, server_default='50'),
            sa.Column('priority', sa.String(length=16), nullable=False, server_default='MEDIUM'),
            sa.Column('grounding_metadata', sa.JSON(), nullable=True),
            sa.Column('raw_model_response', sa.JSON(), nullable=True),
            sa.Column('correlated_company_ids', sa.JSON(), nullable=False, server_default='[]'),
            sa.Column('correlated_product_ids', sa.JSON(), nullable=False, server_default='[]'),
            sa.Column('correlated_technology_ids', sa.JSON(), nullable=False, server_default='[]'),
            sa.Column('correlated_advisory_ids', sa.JSON(), nullable=False, server_default='[]'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_security_intelligence_events_title'), 'security_intelligence_events', ['title'], unique=False)
        op.create_index(op.f('ix_security_intelligence_events_event_type'), 'security_intelligence_events', ['event_type'], unique=False)
        op.create_index(op.f('ix_security_intelligence_events_published_at'), 'security_intelligence_events', ['published_at'], unique=False)
        op.create_index(op.f('ix_security_intelligence_events_severity'), 'security_intelligence_events', ['severity'], unique=False)
        op.create_index(op.f('ix_security_intelligence_events_actively_exploited'), 'security_intelligence_events', ['actively_exploited'], unique=False)
        op.create_index(op.f('ix_security_intelligence_events_fingerprint'), 'security_intelligence_events', ['fingerprint'], unique=True)
        op.create_index(op.f('ix_security_intelligence_events_priority_score'), 'security_intelligence_events', ['priority_score'], unique=False)
        op.create_index(op.f('ix_security_intelligence_events_priority'), 'security_intelligence_events', ['priority'], unique=False)
        op.create_index(op.f('ix_security_intelligence_events_created_at'), 'security_intelligence_events', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_security_intelligence_events_created_at'), table_name='security_intelligence_events')
    op.drop_index(op.f('ix_security_intelligence_events_priority'), table_name='security_intelligence_events')
    op.drop_index(op.f('ix_security_intelligence_events_priority_score'), table_name='security_intelligence_events')
    op.drop_index(op.f('ix_security_intelligence_events_fingerprint'), table_name='security_intelligence_events')
    op.drop_index(op.f('ix_security_intelligence_events_actively_exploited'), table_name='security_intelligence_events')
    op.drop_index(op.f('ix_security_intelligence_events_severity'), table_name='security_intelligence_events')
    op.drop_index(op.f('ix_security_intelligence_events_published_at'), table_name='security_intelligence_events')
    op.drop_index(op.f('ix_security_intelligence_events_event_type'), table_name='security_intelligence_events')
    op.drop_index(op.f('ix_security_intelligence_events_title'), table_name='security_intelligence_events')
    op.drop_table('security_intelligence_events')
