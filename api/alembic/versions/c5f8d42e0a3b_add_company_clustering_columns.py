"""add_company_clustering_columns

Revision ID: c5f8d42e0a3b
Revises: b4e7c31d8a29
Create Date: 2026-09-04 10:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5f8d42e0a3b'
down_revision: Union[str, None] = 'b4e7c31d8a29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('change_clusters')]

    if 'company_id' not in columns:
        op.add_column('change_clusters', sa.Column('company_id', sa.Integer(), nullable=True))
        op.create_index(op.f('ix_change_clusters_company_id'), 'change_clusters', ['company_id'], unique=False)
        op.create_foreign_key('fk_change_clusters_company_id', 'change_clusters', 'companies', ['company_id'], ['id'], ondelete='CASCADE')

    if 'meta' not in columns:
        op.add_column('change_clusters', sa.Column('meta', sa.JSON(), nullable=True))

    # Allow target_id to be nullable for company-level clusters
    op.alter_column('change_clusters', 'target_id', existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.alter_column('change_clusters', 'target_id', existing_type=sa.Integer(), nullable=False)
    op.drop_column('change_clusters', 'meta')
    op.drop_constraint('fk_change_clusters_company_id', 'change_clusters', type_='foreignkey')
    op.drop_index(op.f('ix_change_clusters_company_id'), table_name='change_clusters')
    op.drop_column('change_clusters', 'company_id')
