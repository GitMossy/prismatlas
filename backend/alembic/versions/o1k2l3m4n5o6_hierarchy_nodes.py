"""hierarchy_nodes, entity_hierarchy_memberships, hierarchy_versions tables

Revision ID: o1k2l3m4n5o6
Revises: n0j1k2l3m4n5
Create Date: 2026-03-20

Creates:
  - hierarchy_nodes table (FR-4.1 — unlimited-depth hierarchy)
  - entity_hierarchy_memberships table
  - hierarchy_versions table
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'o1k2l3m4n5o6'
down_revision = 'n0j1k2l3m4n5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'hierarchy_nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dimension', sa.String(10), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('hierarchy_nodes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('position', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_hierarchy_nodes_project_dim', 'hierarchy_nodes', ['project_id', 'dimension'])
    op.create_index('ix_hierarchy_nodes_parent_id', 'hierarchy_nodes', ['parent_id'])

    op.create_table(
        'entity_hierarchy_memberships',
        sa.Column('entity_type', sa.String(20), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('node_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('hierarchy_nodes.id', ondelete='CASCADE'),
                  nullable=False),
        sa.PrimaryKeyConstraint('entity_id', 'node_id'),
        sa.UniqueConstraint('entity_id', 'node_id', name='uq_entity_node'),
    )
    op.create_index('ix_entity_hierarchy_node_id', 'entity_hierarchy_memberships', ['node_id'])

    op.create_table(
        'hierarchy_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dimension', sa.String(10), nullable=False),
        sa.Column('snapshot', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_hierarchy_versions_project_id', 'hierarchy_versions', ['project_id'])


def downgrade():
    op.drop_index('ix_hierarchy_versions_project_id', 'hierarchy_versions')
    op.drop_table('hierarchy_versions')
    op.drop_index('ix_entity_hierarchy_node_id', 'entity_hierarchy_memberships')
    op.drop_table('entity_hierarchy_memberships')
    op.drop_index('ix_hierarchy_nodes_parent_id', 'hierarchy_nodes')
    op.drop_index('ix_hierarchy_nodes_project_dim', 'hierarchy_nodes')
    op.drop_table('hierarchy_nodes')
