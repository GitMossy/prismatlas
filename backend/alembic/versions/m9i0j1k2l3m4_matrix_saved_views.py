"""matrix saved_views table

Revision ID: m9i0j1k2l3m4
Revises: l8h9i0j1k2l3
Create Date: 2026-03-20

Creates:
  - saved_views table (FR-4.6.1, FR-4.6.2)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'm9i0j1k2l3m4'
down_revision = 'l8h9i0j1k2l3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'saved_views',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('config', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_saved_views_project_id', 'saved_views', ['project_id'])


def downgrade():
    op.drop_index('ix_saved_views_project_id', 'saved_views')
    op.drop_table('saved_views')
