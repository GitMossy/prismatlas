"""near_critical and effort_scaling_mode

Revision ID: e1a2b3c4d5e6
Revises: d5g6h7i8j9k0
Create Date: 2026-03-20

Covers:
  - FR-4.4.3: Near-Critical Path
      task_instances.is_near_critical boolean column
  - BR-5.5: Effort Scaling Mode
      class_definitions.effort_scaling_mode varchar(10) column
"""
from alembic import op
import sqlalchemy as sa

revision = 'e1a2b3c4d5e6'
down_revision = 'd5g6h7i8j9k0'
branch_labels = None
depends_on = None


def upgrade():
    # ── task_instances: near-critical flag ────────────────────────────────────
    op.add_column(
        'task_instances',
        sa.Column('is_near_critical', sa.Boolean, nullable=False, server_default='false'),
    )

    # ── class_definitions: effort scaling mode ────────────────────────────────
    op.add_column(
        'class_definitions',
        sa.Column('effort_scaling_mode', sa.String(10), nullable=False, server_default='linear'),
    )


def downgrade():
    op.drop_column('class_definitions', 'effort_scaling_mode')
    op.drop_column('task_instances', 'is_near_critical')
