"""add slice fields to objects

Revision ID: b3e4f5a6c7d8
Revises: aa6b7c1619a7
Create Date: 2026-03-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3e4f5a6c7d8'
down_revision: Union[str, None] = 'aa6b7c1619a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new dimension columns to objects
    op.add_column('objects', sa.Column('zone', sa.String(100), nullable=True))
    op.add_column('objects', sa.Column('planned_start', sa.Date, nullable=True))
    op.add_column('objects', sa.Column('planned_end', sa.Date, nullable=True))
    op.add_column('objects', sa.Column('owner', sa.String(255), nullable=True))

    # Indexes for slice filtering
    op.create_index('ix_objects_zone', 'objects', ['zone'])
    op.create_index('ix_objects_owner', 'objects', ['owner'])
    op.create_index('ix_objects_planned_start', 'objects', ['planned_start'])

    # Composite index for stage filter subquery
    op.create_index(
        'ix_stage_instances_workflow_key_status',
        'stage_instances',
        ['workflow_instance_id', 'stage_key', 'status'],
    )


def downgrade() -> None:
    op.drop_index('ix_stage_instances_workflow_key_status', table_name='stage_instances')
    op.drop_index('ix_objects_planned_start', table_name='objects')
    op.drop_index('ix_objects_owner', table_name='objects')
    op.drop_index('ix_objects_zone', table_name='objects')
    op.drop_column('objects', 'owner')
    op.drop_column('objects', 'planned_end')
    op.drop_column('objects', 'planned_start')
    op.drop_column('objects', 'zone')
