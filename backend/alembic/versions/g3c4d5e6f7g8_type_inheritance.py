"""Type inheritance: parent_template_id, inherited_from_version_id, overridden_fields

Revision ID: g3c4d5e6f7g8
Revises: k7g8h9i0j1k2
Create Date: 2026-03-20

Covers:
  - FR-4.2.3: workflow_templates.parent_template_id (self-referential FK)
  - FR-4.2.4: workflow_template_versions.inherited_from_version_id
  - FR-4.2.5: workflow_instances.overridden_fields JSONB
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = 'g3c4d5e6f7g8'
down_revision = 'k7g8h9i0j1k2'
branch_labels = None
depends_on = None


def upgrade():
    # ── workflow_templates: self-referential parent ────────────────────────────
    op.add_column(
        'workflow_templates',
        sa.Column('parent_template_id', UUID(as_uuid=True),
                  sa.ForeignKey('workflow_templates.id'), nullable=True),
    )

    # ── workflow_template_versions: inherited_from link ───────────────────────
    op.add_column(
        'workflow_template_versions',
        sa.Column('inherited_from_version_id', UUID(as_uuid=True),
                  sa.ForeignKey('workflow_template_versions.id'), nullable=True),
    )

    # ── workflow_instances: overridden_fields ─────────────────────────────────
    op.add_column(
        'workflow_instances',
        sa.Column('overridden_fields', JSONB, nullable=False, server_default='{}'),
    )


def downgrade():
    op.drop_column('workflow_instances', 'overridden_fields')
    op.drop_column('workflow_template_versions', 'inherited_from_version_id')
    op.drop_column('workflow_templates', 'parent_template_id')
