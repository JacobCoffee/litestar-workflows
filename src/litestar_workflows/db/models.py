"""SQLAlchemy models for workflow persistence.

This module defines the database models for persisting workflow state:
- WorkflowDefinitionModel: Stores workflow definition metadata and schema
- WorkflowInstanceModel: Stores running/completed workflow instances
- StepExecutionModel: Records individual step executions
- HumanTaskModel: Tracks pending human approval tasks
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from litestar_workflows.core.types import StepStatus, StepType, WorkflowStatus

__all__ = [
    "HumanTaskModel",
    "StepExecutionModel",
    "WorkflowDefinitionModel",
    "WorkflowInstanceModel",
]


# Cross-database JSON type: uses JSONB for PostgreSQL, JSON for others (SQLite, MySQL, etc.)
JSONType = JSON().with_variant(JSONB, "postgresql")


class WorkflowDefinitionModel(UUIDAuditBase):
    """Persisted workflow definition for versioning and storage.

    Stores the serialized workflow definition along with metadata for
    querying and managing workflow versions.

    Attributes:
        name: Unique name identifier for the workflow.
        version: Semantic version string (e.g., "1.0.0").
        description: Human-readable description of the workflow.
        definition_json: Serialized WorkflowDefinition as JSON.
        is_active: Whether this version is active for new instances.
        instances: Related workflow instances.
    """

    __tablename__ = "workflow_definitions"
    __table_args__ = (
        Index("ix_workflow_definitions_name_version", "name", "version", unique=True),
        Index("ix_workflow_definitions_name_active", "name", "is_active"),
    )

    name: Mapped[str] = mapped_column(String(255), index=True)
    version: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    definition_json: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    instances: Mapped[list[WorkflowInstanceModel]] = relationship(
        back_populates="definition",
        lazy="noload",
    )


class WorkflowInstanceModel(UUIDAuditBase):
    """Persisted workflow instance representing a running or completed execution.

    Stores the current state of a workflow execution including context data,
    current step, and execution history.

    Attributes:
        definition_id: Foreign key to the workflow definition.
        workflow_name: Denormalized workflow name for quick queries.
        workflow_version: Denormalized workflow version.
        status: Current execution status.
        current_step: Name of the currently executing step (None if complete).
        context_data: Mutable workflow context data as JSON.
        metadata: Immutable metadata about the execution.
        error: Error message if workflow failed.
        started_at: Timestamp when execution began.
        completed_at: Timestamp when execution finished.
        tenant_id: Optional tenant identifier for multi-tenancy.
        created_by: Optional user who started the workflow.
    """

    __tablename__ = "workflow_instances"
    __table_args__ = (
        Index("ix_workflow_instances_status", "status"),
        Index("ix_workflow_instances_workflow_name", "workflow_name"),
        Index("ix_workflow_instances_tenant_id", "tenant_id"),
        Index("ix_workflow_instances_created_by", "created_by"),
    )

    definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
    )
    workflow_name: Mapped[str] = mapped_column(String(255))
    workflow_version: Mapped[str] = mapped_column(String(50))
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus, native_enum=False, length=50),
        default=WorkflowStatus.PENDING,
    )
    current_step: Mapped[str | None] = mapped_column(String(255), nullable=True)
    context_data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONType,
        default=dict,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Multi-tenancy support
    tenant_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    definition: Mapped[WorkflowDefinitionModel] = relationship(
        back_populates="instances",
        lazy="joined",
    )
    step_executions: Mapped[list[StepExecutionModel]] = relationship(
        back_populates="instance",
        lazy="noload",
        order_by="StepExecutionModel.started_at",
    )
    human_tasks: Mapped[list[HumanTaskModel]] = relationship(
        back_populates="instance",
        lazy="noload",
    )


class StepExecutionModel(UUIDAuditBase):
    """Record of a single step execution within a workflow instance.

    Tracks the execution of each step including timing, status, and
    input/output data for debugging and audit purposes.

    Attributes:
        instance_id: Foreign key to the workflow instance.
        step_name: Name of the executed step.
        step_type: Type of step (MACHINE, HUMAN, etc.).
        status: Execution status of the step.
        input_data: Input data passed to the step.
        output_data: Output data produced by the step.
        error: Error message if step failed.
        started_at: Timestamp when step execution began.
        completed_at: Timestamp when step execution finished.
        assigned_to: User ID assigned to human tasks.
        completed_by: User ID who completed human tasks.
    """

    __tablename__ = "workflow_step_executions"
    __table_args__ = (
        Index("ix_step_executions_instance_id", "instance_id"),
        Index("ix_step_executions_step_name", "step_name"),
        Index("ix_step_executions_status", "status"),
    )

    instance_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_instances.id", ondelete="CASCADE"),
    )
    step_name: Mapped[str] = mapped_column(String(255))
    step_type: Mapped[StepType] = mapped_column(
        Enum(StepType, native_enum=False, length=50),
    )
    status: Mapped[StepStatus] = mapped_column(
        Enum(StepStatus, native_enum=False, length=50),
        default=StepStatus.PENDING,
    )
    input_data: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # For human tasks
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    completed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    instance: Mapped[WorkflowInstanceModel] = relationship(
        back_populates="step_executions",
    )


class HumanTaskModel(UUIDAuditBase):
    """Pending human task for quick querying and assignment.

    Provides a denormalized view of pending human approval tasks for
    efficient querying by assignee, due date, and status.

    Attributes:
        instance_id: Foreign key to the workflow instance.
        step_execution_id: Foreign key to the step execution.
        step_name: Name of the human task step.
        title: Display title for the task.
        description: Detailed description of the task.
        form_schema: JSON Schema defining the task form.
        assignee_id: User ID assigned to complete the task.
        assignee_group: Group/role that can complete the task.
        due_at: Deadline for task completion.
        reminder_at: When to send a reminder.
        status: Current task status (PENDING, COMPLETED, CANCELED).
        completed_at: When the task was completed.
        completed_by: User who completed the task.
    """

    __tablename__ = "workflow_human_tasks"
    __table_args__ = (
        Index("ix_human_tasks_assignee_id", "assignee_id"),
        Index("ix_human_tasks_assignee_group", "assignee_group"),
        Index("ix_human_tasks_status", "status"),
        Index("ix_human_tasks_due_at", "due_at"),
    )

    instance_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_instances.id", ondelete="CASCADE"),
    )
    step_execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_step_executions.id", ondelete="CASCADE"),
    )
    step_name: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    form_schema: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)

    # Assignment
    assignee_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assignee_group: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Deadlines
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    reminder_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Status
    status: Mapped[str] = mapped_column(String(50), default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    instance: Mapped[WorkflowInstanceModel] = relationship(
        back_populates="human_tasks",
    )
