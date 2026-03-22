"""add class_definition_id to objects

Revision ID: r4n5o6p7q8r9
Revises: q3m4n5o6p7q8
Create Date: 2026-03-21

Changes:
  - Add nullable class_definition_id FK on objects → class_definitions (SET NULL on delete)
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = 'r4n5o6p7q8r9'
down_revision = 'q3m4n5o6p7q8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'objects',
        sa.Column('class_definition_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_objects_class_definition_id',
        'objects', 'class_definitions',
        ['class_definition_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade():
    op.drop_constraint('fk_objects_class_definition_id', 'objects', type_='foreignkey')
    op.drop_column('objects', 'class_definition_id')
