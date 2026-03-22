"""What-if scenarios and scenario_task_overrides

Revision ID: l8h9i0j1k2l3
Revises: j6f7g8h9i0j1
Create Date: 2026-03-20

Covers:
  - FR-4.4.6: scenarios table
  - FR-4.4.6: scenario_task_overrides table
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'l8h9i0j1k2l3'
down_revision = 'j6f7g8h9i0j1'
branch_labels = None
depends_on = None


def upgrade():
    # ── scenarios ─────────────────────────────────────────────────────────────
    op.create_table(
        'scenarios',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('source_baseline_id', UUID(as_uuid=True), sa.ForeignKey('baselines.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
    )
    op.create_index('ix_scenarios_project_id', 'scenarios', ['project_id'])

    # ── scenario_task_overrides ───────────────────────────────────────────────
    op.create_table(
        'scenario_task_overrides',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('scenario_id', UUID(as_uuid=True), sa.ForeignKey('scenarios.id'), nullable=False),
        sa.Column('task_instance_id', UUID(as_uuid=True), sa.ForeignKey('task_instances.id'), nullable=False),
        sa.Column('duration_days', sa.Integer),
        sa.Column('effort_hours', sa.Float),
        sa.Column('start_offset_days', sa.Integer),
    )
    op.create_index('ix_scenario_task_overrides_scenario_id', 'scenario_task_overrides', ['scenario_id'])
    op.create_index('ix_scenario_task_overrides_task_id', 'scenario_task_overrides', ['task_instance_id'])


def downgrade():
    op.drop_index('ix_scenario_task_overrides_task_id', table_name='scenario_task_overrides')
    op.drop_index('ix_scenario_task_overrides_scenario_id', table_name='scenario_task_overrides')
    op.drop_table('scenario_task_overrides')

    op.drop_index('ix_scenarios_project_id', table_name='scenarios')
    op.drop_table('scenarios')
