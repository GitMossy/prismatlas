"""Add cross-node dependency fields to hierarchy_nodes

Revision ID: u7q8r9s0t1u2
Revises: t6p7q8r9s0t1
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'u7q8r9s0t1u2'
down_revision = 't6p7q8r9s0t1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'hierarchy_nodes',
        sa.Column(
            'depends_on_node_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('hierarchy_nodes.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )
    op.add_column(
        'hierarchy_nodes',
        sa.Column('dependency_condition', postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('hierarchy_nodes', 'dependency_condition')
    op.drop_column('hierarchy_nodes', 'depends_on_node_id')
