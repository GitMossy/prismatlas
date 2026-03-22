"""RBAC: users, project_roles, area_permissions + audit_logs

Revision ID: k7g8h9i0j1k2
Revises: e1a2b3c4d5e6
Create Date: 2026-03-20

Covers:
  - NFR-7.3: RBAC tables (users, project_roles, area_permissions)
  - NFR-7.3: audit_logs table for GMP-compliant change tracking
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = 'k7g8h9i0j1k2'
down_revision = 'f2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade():
    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('supabase_user_id', UUID(as_uuid=True), unique=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('display_name', sa.String(255)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # ── project_roles ─────────────────────────────────────────────────────────
    op.create_table(
        'project_roles',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='viewer'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_project_roles_user_id', 'project_roles', ['user_id'])
    op.create_index('ix_project_roles_project_id', 'project_roles', ['project_id'])

    # ── area_permissions ──────────────────────────────────────────────────────
    op.create_table(
        'area_permissions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('area_id', UUID(as_uuid=True), sa.ForeignKey('areas.id'), nullable=False),
        sa.Column('can_read', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('can_write', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_area_permissions_user_id', 'area_permissions', ['user_id'])
    op.create_index('ix_area_permissions_area_id', 'area_permissions', ['area_id'])

    # ── audit_logs ────────────────────────────────────────────────────────────
    op.create_table(
        'audit_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('field_name', sa.String(100)),
        sa.Column('old_value', JSONB),
        sa.Column('new_value', JSONB),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'])
    op.create_index('ix_audit_logs_project_id', 'audit_logs', ['project_id'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])


def downgrade():
    op.drop_index('ix_audit_logs_timestamp', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_project_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_entity', table_name='audit_logs')
    op.drop_table('audit_logs')

    op.drop_index('ix_area_permissions_area_id', table_name='area_permissions')
    op.drop_index('ix_area_permissions_user_id', table_name='area_permissions')
    op.drop_table('area_permissions')

    op.drop_index('ix_project_roles_project_id', table_name='project_roles')
    op.drop_index('ix_project_roles_user_id', table_name='project_roles')
    op.drop_table('project_roles')

    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
