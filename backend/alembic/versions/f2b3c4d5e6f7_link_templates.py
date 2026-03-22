"""link_templates table

Revision ID: f2b3c4d5e6f7
Revises: e1a2b3c4d5e6
Create Date: 2026-03-20

Covers:
  - FR-4.5.4: Link Templates
      link_templates table — stores reusable Relationship patterns that are
      automatically applied when a new Object is added to a project.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'f2b3c4d5e6f7'
down_revision = 'e1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'link_templates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('source_object_type', sa.String(50), nullable=False),
        sa.Column('source_stage_key', sa.String(100)),
        sa.Column('target_object_type', sa.String(50), nullable=False),
        sa.Column('target_stage_key', sa.String(100)),
        sa.Column('link_type', sa.String(2), nullable=False, server_default='FS'),
        sa.Column('lag_days', sa.Integer, nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_link_templates_project_id', 'link_templates', ['project_id'])


def downgrade():
    op.drop_index('ix_link_templates_project_id', table_name='link_templates')
    op.drop_table('link_templates')
