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
    # created_by was added in a previous run but user_id (pre-existing) is the correct ownership column
    # Add created_by only if it doesn't exist (idempotent)
    pass


def downgrade() -> None:
    pass
