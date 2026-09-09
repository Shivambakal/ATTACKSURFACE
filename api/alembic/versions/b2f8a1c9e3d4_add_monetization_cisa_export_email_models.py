"""add_monetization_cisa_export_email_models

Revision ID: b2f8a1c9e3d4
Revises: d1c8f4e2a9b3
Create Date: 2026-09-09 22:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2f8a1c9e3d4'
down_revision: Union[str, None] = 'd1c8f4e2a9b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. cisa_feed_snapshots
    op.create_table(
        'cisa_feed_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('http_status', sa.Integer(), nullable=False, server_default='200'),
        sa.Column('content_sha256', sa.String(length=64), nullable=False),
        sa.Column('catalog_version', sa.String(length=64), nullable=False),
        sa.Column('date_released', sa.DateTime(timezone=True), nullable=True),
        sa.Column('declared_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('raw_payload', sa.Text(), nullable=False),
        sa.Column('parser_version', sa.String(length=32), nullable=False, server_default='1.0.0'),
        sa.Column('fetch_duration_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_cisa_snapshots_hash', 'cisa_feed_snapshots', ['content_sha256'], unique=False)
    op.create_index('ix_cisa_snapshots_version', 'cisa_feed_snapshots', ['catalog_version'], unique=False)
    op.create_index(op.f('ix_cisa_feed_snapshots_fetched_at'), 'cisa_feed_snapshots', ['fetched_at'], unique=False)

    # 2. cisa_kev_items
    op.create_table(
        'cisa_kev_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('cve_id', sa.String(length=32), nullable=False),
        sa.Column('vendor_project', sa.String(length=255), nullable=False),
        sa.Column('product', sa.String(length=255), nullable=False),
        sa.Column('vulnerability_name', sa.Text(), nullable=False),
        sa.Column('date_added', sa.DateTime(timezone=True), nullable=True),
        sa.Column('short_description', sa.Text(), nullable=False),
        sa.Column('required_action', sa.Text(), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('known_ransomware_campaign_use', sa.String(length=32), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('cwes', sa.JSON(), nullable=True),
        sa.Column('first_seen_catalog_version', sa.String(length=64), nullable=True),
        sa.Column('last_seen_catalog_version', sa.String(length=64), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source_snapshot_id', sa.Integer(), sa.ForeignKey('cisa_feed_snapshots.id', ondelete='SET NULL'), nullable=True),
        sa.Column('raw_source_hash', sa.String(length=64), nullable=True),
        sa.Column('data_origin', sa.String(length=32), nullable=False, server_default='SOURCE_VERIFIED'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    )
    op.create_index(op.f('ix_cisa_kev_items_cve_id'), 'cisa_kev_items', ['cve_id'], unique=True)
    op.create_index(op.f('ix_cisa_kev_items_vendor_project'), 'cisa_kev_items', ['vendor_project'], unique=False)
    op.create_index(op.f('ix_cisa_kev_items_product'), 'cisa_kev_items', ['product'], unique=False)
    op.create_index('ix_cisa_kev_vendor_product', 'cisa_kev_items', ['vendor_project', 'product'], unique=False)
    op.create_index('ix_cisa_kev_date_added', 'cisa_kev_items', ['date_added'], unique=False)

    # 3. export_jobs
    op.create_table(
        'export_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('export_uuid', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('export_type', sa.String(length=64), nullable=False),
        sa.Column('format', sa.String(length=16), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='QUEUED'),
        sa.Column('filters', sa.JSON(), nullable=True),
        sa.Column('scope', sa.String(length=64), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('checksum_sha256', sa.String(length=64), nullable=True),
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('download_token', sa.String(length=64), nullable=False),
        sa.Column('download_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
    )
    op.create_index(op.f('ix_export_jobs_export_uuid'), 'export_jobs', ['export_uuid'], unique=True)
    op.create_index(op.f('ix_export_jobs_download_token'), 'export_jobs', ['download_token'], unique=True)
    op.create_index(op.f('ix_export_jobs_user_id'), 'export_jobs', ['user_id'], unique=False)
    op.create_index('ix_export_jobs_user_status', 'export_jobs', ['user_id', 'status'], unique=False)

    # 4. subscriptions
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tier', sa.String(length=32), nullable=False, server_default='FREE'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='ACTIVE'),
        sa.Column('provider', sa.String(length=32), nullable=False, server_default='INTERNAL'),
        sa.Column('provider_subscription_id', sa.String(length=128), nullable=True),
        sa.Column('provider_customer_id', sa.String(length=128), nullable=True),
        sa.Column('is_verified_payment', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=True)
    op.create_index(op.f('ix_subscriptions_tier'), 'subscriptions', ['tier'], unique=False)
    op.create_index(op.f('ix_subscriptions_status'), 'subscriptions', ['status'], unique=False)

    # 5. payment_transactions
    op.create_table(
        'payment_transactions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order_id', sa.String(length=128), nullable=False),
        sa.Column('payment_id', sa.String(length=128), nullable=True),
        sa.Column('plan_tier', sa.String(length=32), nullable=False, server_default='RESEARCHER'),
        sa.Column('billing_interval', sa.String(length=16), nullable=False, server_default='monthly'),
        sa.Column('amount_inr', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('expected_amount_paisa', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='CREATED'),
        sa.Column('payment_state', sa.String(length=32), nullable=False, server_default='CREATED'),
        sa.Column('gateway_status', sa.String(length=32), nullable=True),
        sa.Column('environment', sa.String(length=32), nullable=False, server_default='TEST MODE'),
        sa.Column('gateway_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('signature', sa.String(length=255), nullable=True),
        sa.Column('receipt', sa.String(length=128), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_payment_transactions_order_id'), 'payment_transactions', ['order_id'], unique=True)
    op.create_index(op.f('ix_payment_transactions_payment_id'), 'payment_transactions', ['payment_id'], unique=False)
    op.create_index(op.f('ix_payment_transactions_user_id'), 'payment_transactions', ['user_id'], unique=False)

    # 6. email_events
    op.create_table(
        'email_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('type', sa.String(length=64), nullable=False),
        sa.Column('recipient_hash', sa.String(length=64), nullable=False),
        sa.Column('recipient_masked', sa.String(length=128), nullable=True),
        sa.Column('provider', sa.String(length=32), nullable=False, server_default='resend'),
        sa.Column('provider_message_id', sa.String(length=128), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='queued'),
        sa.Column('failure_reason_safe', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_email_events_user_id'), 'email_events', ['user_id'], unique=False)
    op.create_index(op.f('ix_email_events_type'), 'email_events', ['type'], unique=False)
    op.create_index(op.f('ix_email_events_recipient_hash'), 'email_events', ['recipient_hash'], unique=False)


def downgrade() -> None:
    op.drop_table('email_events')
    op.drop_table('payment_transactions')
    op.drop_table('subscriptions')
    op.drop_table('export_jobs')
    op.drop_table('cisa_kev_items')
    op.drop_table('cisa_feed_snapshots')
