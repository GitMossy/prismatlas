"""zone_diagrams and zone_diagram_pins tables

Revision ID: n0j1k2l3m4n5
Revises: m9i0j1k2l3m4
Create Date: 2026-03-20

Creates:
  - zone_diagrams table (FR-4.6.3)
  - zone_diagram_pins table (FR-4.6.3)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'n0j1k2l3m4n5'
down_revision = 'm9i0j1k2l3m4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'zone_diagrams',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('area_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('areas.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('image_url', sa.String(1024), nullable=False),
        sa.Column('image_width', sa.Integer, nullable=False, server_default='1920'),
        sa.Column('image_height', sa.Integer, nullable=False, server_default='1080'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_zone_diagrams_area_id', 'zone_diagrams', ['area_id'])

    op.create_table(
        'zone_diagram_pins',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('zone_diagram_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('zone_diagrams.id', ondelete='CASCADE'), nullable=False),
        sa.Column('object_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('objects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('x_pct', sa.Float, nullable=False),
        sa.Column('y_pct', sa.Float, nullable=False),
    )
    op.create_index('ix_zone_diagram_pins_diagram_id', 'zone_diagram_pins', ['zone_diagram_id'])


def downgrade():
    op.drop_index('ix_zone_diagram_pins_diagram_id', 'zone_diagram_pins')
    op.drop_table('zone_diagram_pins')
    op.drop_index('ix_zone_diagrams_area_id', 'zone_diagrams')
    op.drop_table('zone_diagrams')
