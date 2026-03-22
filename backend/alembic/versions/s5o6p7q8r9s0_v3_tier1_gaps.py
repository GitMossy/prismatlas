"""V3 Tier-1 architectural gap resolution

Revision ID: s5o6p7q8r9s0
Revises: r4n5o6p7q8r9
Create Date: 2026-03-21

Changes (from gap analysis Software-Requirements-V3.md):

CONFLICT-1  object_type generalisation
  - No schema change; object_type is already String(50) free-text.
  - Removes implicit constraint from application code (not DB-enforced).

CONFLICT-3  Add CBS, ABS, SBS hierarchy dimensions
  - No schema change; dimension is already String(10) free-text.
  - HIERARCHY_DIMENSIONS constant updated in model layer.
  - EBS added as alias for ZBS in V3 terminology.

FR-4.3.2  Decimal duration/lag
  - ALTER COLUMN task_instances.duration_days  INTEGER → DOUBLE PRECISION
  - ALTER COLUMN task_instances.early_start    INTEGER → DOUBLE PRECISION
  - ALTER COLUMN task_instances.early_finish   INTEGER → DOUBLE PRECISION
  - ALTER COLUMN task_instances.late_start     INTEGER → DOUBLE PRECISION
  - ALTER COLUMN task_instances.late_finish    INTEGER → DOUBLE PRECISION
  - ALTER COLUMN task_instances.total_float    INTEGER → DOUBLE PRECISION
  - ALTER COLUMN dependency_rules.lag_days     INTEGER → DOUBLE PRECISION

FR-4.3.3  Effort Estimation Matrix
  - CREATE TABLE effort_matrix_cells

FR-4.4.2  Calendar-aware CPM
  - CREATE TABLE work_calendars
  - CREATE TABLE calendar_exceptions
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = 's5o6p7q8r9s0'
down_revision = 'r4n5o6p7q8r9'
branch_labels = None
depends_on = None


def upgrade():
    # ── FR-4.3.2  Convert integer scheduling fields to float ─────────────────

    for col in ('duration_days', 'early_start', 'early_finish',
                'late_start', 'late_finish', 'total_float'):
        op.alter_column(
            'task_instances',
            col,
            existing_type=sa.Integer(),
            type_=sa.Float(),
            existing_nullable=True,
        )

    op.alter_column(
        'dependency_rules',
        'lag_days',
        existing_type=sa.Integer(),
        type_=sa.Float(),
        existing_nullable=False,
        existing_server_default='0',
    )

    # ── FR-4.3.3  Effort Estimation Matrix ───────────────────────────────────

    op.create_table(
        'effort_matrix_cells',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workflow_template_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('workflow_templates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_key', sa.String(100), nullable=False),
        sa.Column('step_name', sa.String(255), nullable=True),
        sa.Column('base_effort_hours', sa.Float(), nullable=False, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('workflow_template_id', 'step_key',
                            name='uq_effort_matrix_cell'),
    )
    op.create_index(
        'ix_effort_matrix_cells_template_id',
        'effort_matrix_cells',
        ['workflow_template_id'],
    )

    # ── FR-4.4.2  Work Calendars ──────────────────────────────────────────────

    op.create_table(
        'work_calendars',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('working_days', postgresql.JSONB(), nullable=False,
                  server_default='[1,2,3,4,5]'),
        sa.Column('hours_per_day', sa.Float(), nullable=False, server_default='8'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
    )

    op.create_table(
        'calendar_exceptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('calendar_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('work_calendars.id', ondelete='CASCADE'), nullable=False),
        sa.Column('exception_date', sa.Date(), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('is_working', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.create_index(
        'ix_calendar_exceptions_calendar_date',
        'calendar_exceptions',
        ['calendar_id', 'exception_date'],
    )


def downgrade():
    op.drop_index('ix_calendar_exceptions_calendar_date', table_name='calendar_exceptions')
    op.drop_table('calendar_exceptions')
    op.drop_table('work_calendars')

    op.drop_index('ix_effort_matrix_cells_template_id', table_name='effort_matrix_cells')
    op.drop_table('effort_matrix_cells')

    op.alter_column(
        'dependency_rules',
        'lag_days',
        existing_type=sa.Float(),
        type_=sa.Integer(),
        existing_nullable=False,
        existing_server_default='0',
    )

    for col in ('duration_days', 'early_start', 'early_finish',
                'late_start', 'late_finish', 'total_float'):
        op.alter_column(
            'task_instances',
            col,
            existing_type=sa.Float(),
            type_=sa.Integer(),
            existing_nullable=True,
        )
