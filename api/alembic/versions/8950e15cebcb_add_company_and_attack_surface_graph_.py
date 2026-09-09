"""add_company_and_attack_surface_graph_models

Revision ID: 8950e15cebcb
Revises: 
Create Date: 2026-09-04 01:29:10.117731
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8950e15cebcb'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create companies table
    op.create_table(
        'companies',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('canonical_domain', sa.String(length=255), nullable=False),
        sa.Column('legal_name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('industry', sa.String(length=128), nullable=True),
        sa.Column('country', sa.String(length=64), nullable=True),
        sa.Column('logo_url', sa.Text(), nullable=True),
        sa.Column('website_url', sa.Text(), nullable=True),
        sa.Column('security_policy_url', sa.Text(), nullable=True),
        sa.Column('bug_bounty_url', sa.Text(), nullable=True),
        sa.Column('disclosure_policy_url', sa.Text(), nullable=True),
        sa.Column('source_confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('aliases', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('last_enriched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_companies_canonical_domain'), 'companies', ['canonical_domain'], unique=True)
    op.create_index(op.f('ix_companies_name'), 'companies', ['name'], unique=False)

    # 2. Create security_programs table
    op.create_table(
        'security_programs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('platform', sa.String(length=64), nullable=False, server_default='Self-Hosted'),
        sa.Column('program_url', sa.Text(), nullable=True),
        sa.Column('policy_url', sa.Text(), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='ACTIVE'),
        sa.Column('scope_summary', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('discovered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_security_programs_company_id'), 'security_programs', ['company_id'], unique=False)

    # 3. Create program_scope_rules table
    op.create_table(
        'program_scope_rules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('security_program_id', sa.Integer(), sa.ForeignKey('security_programs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('pattern', sa.String(length=255), nullable=False),
        sa.Column('asset_type', sa.String(length=64), nullable=True),
        sa.Column('inclusion_type', sa.String(length=32), nullable=False, server_default='INCLUDE'),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('evidence', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.9'),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_program_scope_rules_security_program_id'), 'program_scope_rules', ['security_program_id'], unique=False)
    op.create_index(op.f('ix_program_scope_rules_pattern'), 'program_scope_rules', ['pattern'], unique=False)
    op.create_index(op.f('ix_program_scope_rules_inclusion_type'), 'program_scope_rules', ['inclusion_type'], unique=False)

    # 4. Create products table
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('domain_ids', sa.JSON(), nullable=True),
        sa.Column('source_urls', sa.JSON(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.9'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='ACTIVE'),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_products_company_id'), 'products', ['company_id'], unique=False)
    op.create_index(op.f('ix_products_name'), 'products', ['name'], unique=False)

    # 5. Create asset_evidence table
    op.create_table(
        'asset_evidence',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('asset_id', sa.Integer(), sa.ForeignKey('assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_type', sa.String(length=64), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('evidence_text', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.9'),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_asset_evidence_asset_id'), 'asset_evidence', ['asset_id'], unique=False)
    op.create_index(op.f('ix_asset_evidence_source_type'), 'asset_evidence', ['source_type'], unique=False)

    # 6. Add foreign key company_id to targets
    with op.batch_alter_table('targets') as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id', ondelete='SET NULL'), nullable=True))
        batch_op.create_index('ix_targets_company_id', ['company_id'], unique=False)

    # 7. Add columns to assets
    with op.batch_alter_table('assets') as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=True))
        batch_op.add_column(sa.Column('hostname', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('normalized_hostname', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('scheme', sa.String(length=16), server_default='https', nullable=True))
        batch_op.add_column(sa.Column('parent_domain', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('source', sa.String(length=64), server_default='discovery', nullable=False))
        batch_op.add_column(sa.Column('source_url', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('scope_status', sa.String(length=32), server_default='UNKNOWN', nullable=False))
        batch_op.add_column(sa.Column('verification_status', sa.String(length=32), server_default='UNVERIFIED', nullable=False))
        batch_op.add_column(sa.Column('active', sa.Boolean(), server_default='1', nullable=False))
        batch_op.add_column(sa.Column('notes', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('discovered_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.alter_column('target_id', existing_type=sa.Integer(), nullable=True)
        batch_op.create_index('ix_assets_company_id', ['company_id'], unique=False)
        batch_op.create_index('ix_assets_hostname', ['hostname'], unique=False)
        batch_op.create_index('ix_assets_normalized_hostname', ['normalized_hostname'], unique=False)
        batch_op.create_index('ix_assets_scope_status', ['scope_status'], unique=False)
        batch_op.create_index('ix_assets_verification_status', ['verification_status'], unique=False)

    # 8. Add columns to features
    with op.batch_alter_table('features') as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=True))
        batch_op.add_column(sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True))
        batch_op.add_column(sa.Column('asset_id', sa.Integer(), sa.ForeignKey('assets.id', ondelete='SET NULL'), nullable=True))
        batch_op.add_column(sa.Column('category', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('active', sa.Boolean(), server_default='1', nullable=False))
        batch_op.alter_column('target_id', existing_type=sa.Integer(), nullable=True)
        batch_op.create_index('ix_features_company_id', ['company_id'], unique=False)
        batch_op.create_index('ix_features_product_id', ['product_id'], unique=False)
        batch_op.create_index('ix_features_asset_id', ['asset_id'], unique=False)
        batch_op.create_index('ix_features_category', ['category'], unique=False)

    # 9. Add columns to api_surfaces
    with op.batch_alter_table('api_surfaces') as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=True))
        batch_op.add_column(sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True))
        batch_op.add_column(sa.Column('asset_id', sa.Integer(), sa.ForeignKey('assets.id', ondelete='SET NULL'), nullable=True))
        batch_op.alter_column('target_id', existing_type=sa.Integer(), nullable=True)
        batch_op.create_index('ix_api_surfaces_company_id', ['company_id'], unique=False)
        batch_op.create_index('ix_api_surfaces_product_id', ['product_id'], unique=False)
        batch_op.create_index('ix_api_surfaces_asset_id', ['asset_id'], unique=False)

    # 10. Add columns to security_events
    with op.batch_alter_table('security_events') as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=True))
        batch_op.add_column(sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True))
        batch_op.add_column(sa.Column('asset_id', sa.Integer(), sa.ForeignKey('assets.id', ondelete='SET NULL'), nullable=True))
        batch_op.create_index('ix_security_events_company_id', ['company_id'], unique=False)
        batch_op.create_index('ix_security_events_product_id', ['product_id'], unique=False)
        batch_op.create_index('ix_security_events_asset_id', ['asset_id'], unique=False)

    # 11. Add columns to research_signals
    with op.batch_alter_table('research_signals') as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=True))
        batch_op.add_column(sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True))
        batch_op.add_column(sa.Column('asset_id', sa.Integer(), sa.ForeignKey('assets.id', ondelete='SET NULL'), nullable=True))
        batch_op.alter_column('target_id', existing_type=sa.Integer(), nullable=True)
        batch_op.create_index('ix_research_signals_company_id', ['company_id'], unique=False)
        batch_op.create_index('ix_research_signals_product_id', ['product_id'], unique=False)
        batch_op.create_index('ix_research_signals_asset_id', ['asset_id'], unique=False)


def downgrade() -> None:
    # Downgrade drops
    op.drop_table('asset_evidence')
    op.drop_table('products')
    op.drop_table('program_scope_rules')
    op.drop_table('security_programs')
    op.drop_table('companies')
