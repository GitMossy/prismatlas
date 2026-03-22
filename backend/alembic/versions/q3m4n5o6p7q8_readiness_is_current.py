"""readiness_evaluations.is_current + performance indexes

Revision ID: q3m4n5o6p7q8
Revises: p2l3m4n5o6p7
Create Date: 2026-03-20

Changes:
  - Add is_current boolean column to readiness_evaluations (default False)
  - Add index: ix_readiness_entity_current ON readiness_evaluations(entity_id, is_current)
  - Add composite index: ix_objects_project_type_zone ON objects(project_id, object_type, zone)
  - Add CPM performance indexes:
      ix_task_instances_stage_instance_id ON task_instances(stage_instance_id)
      ix_stage_instances_workflow_instance_id ON stage_instances(workflow_instance_id)
"""
from alembic import op
import sqlalchemy as sa

revision = 'q3m4n5o6p7q8'
down_revision = 'p2l3m4n5o6p7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── E2: is_current column on readiness_evaluations ────────────────────────
    op.add_column(
        'readiness_evaluations',
        sa.Column('is_current', sa.Boolean, nullable=False, server_default='false'),
    )

    # Index for efficient "current readiness for entity" lookups
    op.create_index(
        'ix_readiness_entity_current',
        'readiness_evaluations',
        ['entity_id', 'is_current'],
    )

    # ── E2: Objects composite index for slice/filter queries ──────────────────
    op.create_index(
        'ix_objects_project_type_zone',
        'objects',
        ['project_id', 'object_type', 'zone'],
    )

    # ── E1: CPM performance indexes (stage/task lookups at scale) ─────────────
    # These are critical for run_cpm() to avoid full table scans at 50k tasks.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_task_instances_stage_instance_id "
        "ON task_instances(stage_instance_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stage_instances_workflow_instance_id "
        "ON stage_instances(workflow_instance_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_stage_instances_workflow_instance_id")
    op.execute("DROP INDEX IF EXISTS ix_task_instances_stage_instance_id")
    op.drop_index('ix_objects_project_type_zone', table_name='objects')
    op.drop_index('ix_readiness_entity_current', table_name='readiness_evaluations')
    op.drop_column('readiness_evaluations', 'is_current')
