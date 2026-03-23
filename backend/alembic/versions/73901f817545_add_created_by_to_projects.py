"""add created_by to projects

Revision ID: 73901f817545
Revises: u7q8r9s0t1u2
Create Date: 2026-03-23 13:41:56.442454

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = '73901f817545'
down_revision: Union[str, None] = 'u7q8r9s0t1u2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('created_by', UUID(as_uuid=True), nullable=True))
    op.create_index('ix_projects_created_by', 'projects', ['created_by'])


def downgrade() -> None:
    op.drop_index('ix_projects_created_by', table_name='projects')
    op.drop_column('projects', 'created_by')
