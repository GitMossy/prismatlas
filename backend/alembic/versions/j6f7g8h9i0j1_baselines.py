"""Baselines and baseline_tasks

Revision ID: j6f7g8h9i0j1
Revises: i5e6f7g8h9i0
Create Date: 2026-03-20

Covers:
  - FR-4.4.5: baselines table (schedule snapshot)
  - FR-4.4.5: baseline_tasks table (per-task planned values + CPM floats)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'j6f7g8h9i0j1'
down_revision = 'i5e6f7g8h9i0'
branch_labels = None
depends_on = None


def upgrade():
    # ── baselines ─────────────────────────────────────────────────────────────
    op.create_table(
        'baselines',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
    )
    op.create_index('ix_baselines_project_id', 'baselines', ['project_id'])

    # ── baseline_tasks ────────────────────────────────────────────────────────
    op.create_table(
        'baseline_tasks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('baseline_id', UUID(as_uuid=True), sa.ForeignKey('baselines.id'), nullable=False),
        sa.Column('task_instance_id', UUID(as_uuid=True), sa.ForeignKey('task_instances.id'), nullable=False),
        sa.Column('planned_start', sa.Integer),
        sa.Column('planned_finish', sa.Integer),
        sa.Column('planned_effort_hours', sa.Float),
        sa.Column('planned_cost', sa.Float),
        sa.Column('early_start', sa.Integer),
        sa.Column('early_finish', sa.Integer),
        sa.Column('late_start', sa.Integer),
        sa.Column('late_finish', sa.Integer),
        sa.Column('total_float', sa.Integer),
    )
    op.create_index('ix_baseline_tasks_baseline_id', 'baseline_tasks', ['baseline_id'])
    op.create_index('ix_baseline_tasks_task_instance_id', 'baseline_tasks', ['task_instance_id'])


def downgrade():
    op.drop_index('ix_baseline_tasks_task_instance_id', table_name='baseline_tasks')
    op.drop_index('ix_baseline_tasks_baseline_id', table_name='baseline_tasks')
    op.drop_table('baseline_tasks')

    op.drop_index('ix_baselines_project_id', table_name='baselines')
    op.drop_table('baselines')
