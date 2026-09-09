"""add_security_knowledge_base

Revision ID: a3f8c21e9b47
Revises: 9a61f2e4b7c8
Create Date: 2026-09-04 03:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f8c21e9b47'
down_revision: Union[str, None] = '9a61f2e4b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. cwe_entries table
    op.create_table(
        'cwe_entries',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('cwe_id', sa.String(length=32), unique=True, index=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=64), nullable=False, server_default='MITRE'),
        sa.Column('source_version', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 2. owasp_categories table
    op.create_table(
        'owasp_categories',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('taxonomy', sa.String(length=32), nullable=False, server_default='OWASP'),
        sa.Column('taxonomy_version', sa.String(length=32), index=True, nullable=False),
        sa.Column('category_id', sa.String(length=32), index=True, nullable=False),
        sa.Column('category_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('taxonomy_version', 'category_id', name='uq_owasp_taxonomy_version_cat'),
    )

    # 3. security_advisories table
    op.create_table(
        'security_advisories',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('canonical_id', sa.String(length=128), unique=True, index=True, nullable=False),
        sa.Column('provider', sa.String(length=64), index=True, nullable=False),
        sa.Column('provider_record_id', sa.String(length=128), index=True, nullable=False),
        sa.Column('cve_id', sa.String(length=32), index=True, nullable=True),
        sa.Column('ghsa_id', sa.String(length=64), index=True, nullable=True),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('vendor', sa.String(length=255), index=True, nullable=True),
        sa.Column('product', sa.String(length=255), index=True, nullable=True),
        sa.Column('affected_versions', sa.JSON(), nullable=True),
        sa.Column('severity', sa.String(length=32), nullable=True),
        sa.Column('cvss_score', sa.Float(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('date_added', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('known_ransomware_use', sa.String(length=32), nullable=True),
        sa.Column('forensic_triage', sa.String(length=32), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('raw_hash', sa.String(length=64), nullable=True),
        sa.Column('raw_payload_reference', sa.JSON(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.95'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 4. vulnerability_references table
    op.create_table(
        'vulnerability_references',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('advisory_id', sa.Integer(), sa.ForeignKey('security_advisories.id', ondelete='CASCADE'), index=True, nullable=False),
        sa.Column('reference_type', sa.String(length=32), nullable=False),
        sa.Column('reference_value', sa.String(length=255), nullable=False),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 5. knowledge_sources table
    op.create_table(
        'knowledge_sources',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_type', sa.String(length=64), unique=True, index=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('version', sa.String(length=64), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('record_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='ACTIVE'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 6. knowledge_sync_runs table
    op.create_table(
        'knowledge_sync_runs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_id', sa.Integer(), sa.ForeignKey('knowledge_sources.id'), index=True, nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='RUNNING'),
        sa.Column('records_seen', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_created', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_updated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_skipped', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
    )

    # 7. Junction tables
    op.create_table(
        'advisory_cwe_association',
        sa.Column('advisory_id', sa.Integer(), sa.ForeignKey('security_advisories.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('cwe_id', sa.Integer(), sa.ForeignKey('cwe_entries.id', ondelete='CASCADE'), primary_key=True),
    )

    op.create_table(
        'cwe_owasp_association',
        sa.Column('cwe_id', sa.Integer(), sa.ForeignKey('cwe_entries.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('owasp_category_id', sa.Integer(), sa.ForeignKey('owasp_categories.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('mapping_type', sa.String(length=32), nullable=False, server_default='HEURISTIC'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.8'),
    )

    op.create_table(
        'advisory_owasp_association',
        sa.Column('advisory_id', sa.Integer(), sa.ForeignKey('security_advisories.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('owasp_category_id', sa.Integer(), sa.ForeignKey('owasp_categories.id', ondelete='CASCADE'), primary_key=True),
    )

    # 8. Tenant-isolated private program models
    op.create_table(
        'private_programs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), index=True, nullable=False),
        sa.Column('platform', sa.String(length=64), nullable=False),
        sa.Column('program_name', sa.String(length=255), nullable=False),
        sa.Column('program_identifier', sa.String(length=255), nullable=True),
        sa.Column('policy_url', sa.Text(), nullable=True),
        sa.Column('bounty_eligible', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('authorized_acknowledged', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'private_reports',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('program_id', sa.Integer(), sa.ForeignKey('private_programs.id'), index=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), index=True, nullable=False),
        sa.Column('report_identifier', sa.String(length=128), nullable=True),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=True),
        sa.Column('status', sa.String(length=64), nullable=True),
        sa.Column('bounty_amount', sa.Float(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'private_findings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('program_id', sa.Integer(), sa.ForeignKey('private_programs.id'), index=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), index=True, nullable=False),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('cwe_id', sa.String(length=32), nullable=True),
        sa.Column('asset_identifier', sa.String(length=255), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=32), nullable=True),
        sa.Column('status', sa.String(length=64), nullable=False, server_default='NEW'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'private_scope_rules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('program_id', sa.Integer(), sa.ForeignKey('private_programs.id'), index=True, nullable=False),
        sa.Column('asset_type', sa.String(length=64), nullable=False),
        sa.Column('asset_identifier', sa.String(length=512), nullable=False),
        sa.Column('is_in_scope', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 9. Alter security_events to link to security_advisories
    with op.batch_alter_table('security_events') as batch_op:
        batch_op.add_column(sa.Column('security_advisory_id', sa.Integer(), sa.ForeignKey('security_advisories.id'), nullable=True))
        batch_op.add_column(sa.Column('relationship_type', sa.String(length=64), nullable=True))
        batch_op.create_index('ix_security_events_security_advisory_id', ['security_advisory_id'])
        batch_op.create_index('ix_security_events_relationship_type', ['relationship_type'])


def downgrade() -> None:
    with op.batch_alter_table('security_events') as batch_op:
        batch_op.drop_index('ix_security_events_relationship_type')
        batch_op.drop_index('ix_security_events_security_advisory_id')
        batch_op.drop_column('relationship_type')
        batch_op.drop_column('security_advisory_id')

    op.drop_table('private_scope_rules')
    op.drop_table('private_findings')
    op.drop_table('private_reports')
    op.drop_table('private_programs')
    op.drop_table('advisory_owasp_association')
    op.drop_table('cwe_owasp_association')
    op.drop_table('advisory_cwe_association')
    op.drop_table('knowledge_sync_runs')
    op.drop_table('knowledge_sources')
    op.drop_table('vulnerability_references')
    op.drop_table('security_advisories')
    op.drop_table('owasp_categories')
    op.drop_table('cwe_entries')
