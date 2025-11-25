"""Initial workflow tables.

Revision ID: 001_initial
Revises:
Create Date: 2024-11-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create initial workflow tables."""
    # Create workflow_definitions table
    op.create_table(
        "workflow_definitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("definition_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workflow_definitions_name",
        "workflow_definitions",
        ["name"],
    )
    op.create_index(
        "ix_workflow_definitions_name_version",
        "workflow_definitions",
        ["name", "version"],
        unique=True,
    )
    op.create_index(
        "ix_workflow_definitions_name_active",
        "workflow_definitions",
        ["name", "is_active"],
    )

    # Create workflow_instances table
    op.create_table(
        "workflow_instances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("definition_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_name", sa.String(length=255), nullable=False),
        sa.Column("workflow_version", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("current_step", sa.String(length=255), nullable=True),
        sa.Column("context_data", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["definition_id"],
            ["workflow_definitions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workflow_instances_status",
        "workflow_instances",
        ["status"],
    )
    op.create_index(
        "ix_workflow_instances_workflow_name",
        "workflow_instances",
        ["workflow_name"],
    )
    op.create_index(
        "ix_workflow_instances_tenant_id",
        "workflow_instances",
        ["tenant_id"],
    )
    op.create_index(
        "ix_workflow_instances_created_by",
        "workflow_instances",
        ["created_by"],
    )

    # Create workflow_step_executions table
    op.create_table(
        "workflow_step_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("instance_id", sa.Uuid(), nullable=False),
        sa.Column("step_name", sa.String(length=255), nullable=False),
        sa.Column("step_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("input_data", sa.JSON(), nullable=True),
        sa.Column("output_data", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_to", sa.String(length=255), nullable=True),
        sa.Column("completed_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["instance_id"],
            ["workflow_instances.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_step_executions_instance_id",
        "workflow_step_executions",
        ["instance_id"],
    )
    op.create_index(
        "ix_step_executions_step_name",
        "workflow_step_executions",
        ["step_name"],
    )
    op.create_index(
        "ix_step_executions_status",
        "workflow_step_executions",
        ["status"],
    )

    # Create workflow_human_tasks table
    op.create_table(
        "workflow_human_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("instance_id", sa.Uuid(), nullable=False),
        sa.Column("step_execution_id", sa.Uuid(), nullable=False),
        sa.Column("step_name", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("form_schema", sa.JSON(), nullable=True),
        sa.Column("assignee_id", sa.String(length=255), nullable=True),
        sa.Column("assignee_group", sa.String(length=255), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminder_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, default="pending"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["instance_id"],
            ["workflow_instances.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["step_execution_id"],
            ["workflow_step_executions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_human_tasks_assignee_id",
        "workflow_human_tasks",
        ["assignee_id"],
    )
    op.create_index(
        "ix_human_tasks_assignee_group",
        "workflow_human_tasks",
        ["assignee_group"],
    )
    op.create_index(
        "ix_human_tasks_status",
        "workflow_human_tasks",
        ["status"],
    )
    op.create_index(
        "ix_human_tasks_due_at",
        "workflow_human_tasks",
        ["due_at"],
    )


def downgrade() -> None:
    """Drop workflow tables."""
    op.drop_table("workflow_human_tasks")
    op.drop_table("workflow_step_executions")
    op.drop_table("workflow_instances")
    op.drop_table("workflow_definitions")
