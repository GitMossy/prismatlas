"""Sprints: releases, sprints, task_sprint_assignments; projects.havsts_config

Revision ID: h4d5e6f7g8h9
Revises: g3c4d5e6f7g8
Create Date: 2026-03-20

Covers:
  - FR-4.7: Agile overlay — releases, sprints, task_sprint_assignments
  - projects.havsts_config JSONB for HAVSTS integration metadata
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = 'h4d5e6f7g8h9'
down_revision = 'g3c4d5e6f7g8'
branch_labels = None
depends_on = None


def upgrade():
    # ── releases ──────────────────────────────────────────────────────────────
    op.create_table(
        'releases',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('target_date', sa.Date),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_releases_project_id', 'releases', ['project_id'])

    # ── sprints ───────────────────────────────────────────────────────────────
    op.create_table(
        'sprints',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('release_id', UUID(as_uuid=True), sa.ForeignKey('releases.id'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('start_date', sa.Date),
        sa.Column('end_date', sa.Date),
        sa.Column('capacity_hours', sa.Float),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_sprints_project_id', 'sprints', ['project_id'])
    op.create_index('ix_sprints_release_id', 'sprints', ['release_id'])

    # ── task_sprint_assignments ───────────────────────────────────────────────
    op.create_table(
        'task_sprint_assignments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('task_instance_id', UUID(as_uuid=True), sa.ForeignKey('task_instances.id'), nullable=False),
        sa.Column('sprint_id', UUID(as_uuid=True), sa.ForeignKey('sprints.id'), nullable=False),
        sa.Column('assigned_hours', sa.Float),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_task_sprint_assignments_sprint_id', 'task_sprint_assignments', ['sprint_id'])
    op.create_index('ix_task_sprint_assignments_task_id', 'task_sprint_assignments', ['task_instance_id'])

    # ── projects: HAVSTS integration metadata ─────────────────────────────────
    op.add_column('projects', sa.Column('havsts_config', JSONB))


def downgrade():
    op.drop_column('projects', 'havsts_config')

    op.drop_index('ix_task_sprint_assignments_task_id', table_name='task_sprint_assignments')
    op.drop_index('ix_task_sprint_assignments_sprint_id', table_name='task_sprint_assignments')
    op.drop_table('task_sprint_assignments')

    op.drop_index('ix_sprints_release_id', table_name='sprints')
    op.drop_index('ix_sprints_project_id', table_name='sprints')
    op.drop_table('sprints')

    op.drop_index('ix_releases_project_id', table_name='releases')
    op.drop_table('releases')
