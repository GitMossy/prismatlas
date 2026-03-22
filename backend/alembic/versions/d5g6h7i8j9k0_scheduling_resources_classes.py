"""scheduling: add resources, class_definitions, CPM fields, link types

Revision ID: d5g6h7i8j9k0
Revises: c4f5d6e7f8a9
Create Date: 2026-03-20

Covers:
  - Priority 1: Scheduling Foundation
      task_instances.duration_days, effort_hours, assigned_resource_id
      task_instances.early_start, early_finish, late_start, late_finish, total_float, is_critical
      dependency_rules.link_type, lag_days
  - Priority 2: Resource Entity
      resources table
  - Priority 3: Type System Enhancement
      workflow_templates.complexity, custom_attributes
  - Priority 7: Instance Set Concept
      class_definitions table
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = 'd5g6h7i8j9k0'
down_revision = 'c4f5d6e7f8a9'
branch_labels = None
depends_on = None


def upgrade():
    # ── resources table ────────────────────────────────────────────────────────
    op.create_table(
        'resources',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(100)),
        sa.Column('group', sa.String(100)),
        sa.Column('email', sa.String(255)),
        sa.Column('capacity_hours_per_day', sa.Float, nullable=False, server_default='8.0'),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_resources_project_id', 'resources', ['project_id'])

    # ── class_definitions table ────────────────────────────────────────────────
    op.create_table(
        'class_definitions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('area_id', UUID(as_uuid=True), sa.ForeignKey('areas.id')),
        sa.Column('workflow_template_id', UUID(as_uuid=True), sa.ForeignKey('workflow_templates.id')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('object_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('instance_count', sa.Integer, nullable=False, server_default='1'),
        sa.Column('complexity', sa.Float, nullable=False, server_default='1.0'),
        sa.Column('custom_attributes', JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_class_definitions_project_id', 'class_definitions', ['project_id'])

    # ── workflow_templates: complexity + custom_attributes ─────────────────────
    op.add_column('workflow_templates', sa.Column('complexity', sa.Float, nullable=False, server_default='1.0'))
    op.add_column('workflow_templates', sa.Column('custom_attributes', JSONB))

    # ── task_instances: scheduling fields ──────────────────────────────────────
    op.add_column('task_instances', sa.Column('duration_days', sa.Integer))
    op.add_column('task_instances', sa.Column('effort_hours', sa.Float))
    op.add_column('task_instances', sa.Column(
        'assigned_resource_id', UUID(as_uuid=True),
        sa.ForeignKey('resources.id', ondelete='SET NULL')
    ))
    # CPM computed dates (day offsets from project anchor date)
    op.add_column('task_instances', sa.Column('early_start', sa.Integer))
    op.add_column('task_instances', sa.Column('early_finish', sa.Integer))
    op.add_column('task_instances', sa.Column('late_start', sa.Integer))
    op.add_column('task_instances', sa.Column('late_finish', sa.Integer))
    op.add_column('task_instances', sa.Column('total_float', sa.Integer))
    op.add_column('task_instances', sa.Column('is_critical', sa.Boolean, nullable=False, server_default='false'))

    # ── dependency_rules: link_type + lag_days ─────────────────────────────────
    op.add_column('dependency_rules', sa.Column('link_type', sa.String(2), nullable=False, server_default='FS'))
    op.add_column('dependency_rules', sa.Column('lag_days', sa.Integer, nullable=False, server_default='0'))


def downgrade():
    op.drop_column('dependency_rules', 'lag_days')
    op.drop_column('dependency_rules', 'link_type')

    op.drop_column('task_instances', 'is_critical')
    op.drop_column('task_instances', 'total_float')
    op.drop_column('task_instances', 'late_finish')
    op.drop_column('task_instances', 'late_start')
    op.drop_column('task_instances', 'early_finish')
    op.drop_column('task_instances', 'early_start')
    op.drop_column('task_instances', 'assigned_resource_id')
    op.drop_column('task_instances', 'effort_hours')
    op.drop_column('task_instances', 'duration_days')

    op.drop_column('workflow_templates', 'custom_attributes')
    op.drop_column('workflow_templates', 'complexity')

    op.drop_index('ix_class_definitions_project_id', table_name='class_definitions')
    op.drop_table('class_definitions')

    op.drop_index('ix_resources_project_id', table_name='resources')
    op.drop_table('resources')
