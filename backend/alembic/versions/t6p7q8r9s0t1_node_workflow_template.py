"""Add workflow_template_id to hierarchy_nodes

Revision ID: t6p7q8r9s0t1
Revises: s5o6p7q8r9s0
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 't6p7q8r9s0t1'
down_revision = 's5o6p7q8r9s0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'hierarchy_nodes',
        sa.Column(
            'workflow_template_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('workflow_templates.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('hierarchy_nodes', 'workflow_template_id')
