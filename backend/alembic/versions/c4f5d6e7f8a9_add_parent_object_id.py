"""add parent_object_id to objects

Revision ID: c4f5d6e7f8a9
Revises: b3e4f5a6c7d8
Create Date: 2026-03-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'c4f5d6e7f8a9'
down_revision = 'b3e4f5a6c7d8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('objects', sa.Column('parent_object_id', UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_objects_parent_object_id', 'objects', 'objects',
        ['parent_object_id'], ['id'], ondelete='SET NULL'
    )
    op.create_index('ix_objects_parent_object_id', 'objects', ['parent_object_id'])
    op.create_index('ix_objects_area_id', 'objects', ['area_id'])
    op.create_index('ix_objects_unit_id', 'objects', ['unit_id'])


def downgrade():
    op.drop_index('ix_objects_unit_id', table_name='objects')
    op.drop_index('ix_objects_area_id', table_name='objects')
    op.drop_index('ix_objects_parent_object_id', table_name='objects')
    op.drop_constraint('fk_objects_parent_object_id', 'objects', type_='foreignkey')
    op.drop_column('objects', 'parent_object_id')
