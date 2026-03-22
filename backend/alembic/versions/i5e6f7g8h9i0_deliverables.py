"""Deliverables table

Revision ID: i5e6f7g8h9i0
Revises: h4d5e6f7g8h9
Create Date: 2026-03-20

Covers:
  - FR-4.3.6: deliverables table
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'i5e6f7g8h9i0'
down_revision = 'h4d5e6f7g8h9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'deliverables',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('task_instance_id', UUID(as_uuid=True), sa.ForeignKey('task_instances.id'), nullable=True),
        sa.Column('stage_key', sa.String(100)),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('status', sa.String(20), nullable=False, server_default='not_started'),
        sa.Column('assigned_to', sa.String(255)),
        sa.Column('due_date', sa.Date),
        sa.Column('approved_by', sa.String(255)),
        sa.Column('approved_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_deliverables_project_id', 'deliverables', ['project_id'])
    op.create_index('ix_deliverables_task_instance_id', 'deliverables', ['task_instance_id'])
    op.create_index('ix_deliverables_status', 'deliverables', ['status'])


def downgrade():
    op.drop_index('ix_deliverables_status', table_name='deliverables')
    op.drop_index('ix_deliverables_task_instance_id', table_name='deliverables')
    op.drop_index('ix_deliverables_project_id', table_name='deliverables')
    op.drop_table('deliverables')
