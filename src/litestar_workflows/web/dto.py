"""Data Transfer Objects for the workflow web API.

This module defines DTOs for serializing and deserializing workflow data
in REST API requests and responses.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

__all__ = [
    "CompleteTaskDTO",
    "GraphDTO",
    "HumanTaskDTO",
    "ReassignTaskDTO",
    "StartWorkflowDTO",
    "StepExecutionDTO",
    "WorkflowDefinitionDTO",
    "WorkflowInstanceDTO",
    "WorkflowInstanceDetailDTO",
]


@dataclass
class StartWorkflowDTO:
    """DTO for starting a new workflow instance.

    Attributes:
        definition_name: Name of the workflow definition to instantiate.
        input_data: Initial data to pass to the workflow context.
        correlation_id: Optional correlation ID for tracking related workflows.
        user_id: Optional user ID who started the workflow.
        tenant_id: Optional tenant ID for multi-tenancy.
    """

    definition_name: str
    input_data: dict[str, Any] | None = None
    correlation_id: str | None = None
    user_id: str | None = None
    tenant_id: str | None = None


@dataclass
class WorkflowDefinitionDTO:
    """DTO for workflow definition metadata.

    Attributes:
        name: Workflow name.
        version: Workflow version.
        description: Human-readable description.
        steps: List of step names in the workflow.
        edges: List of edge definitions (source, target, condition).
        initial_step: Name of the starting step.
        terminal_steps: List of terminal step names.
    """

    name: str
    version: str
    description: str
    steps: list[str]
    edges: list[dict[str, Any]]
    initial_step: str
    terminal_steps: list[str]


@dataclass
class StepExecutionDTO:
    """DTO for step execution record.

    Attributes:
        id: Step execution ID.
        step_name: Name of the executed step.
        status: Execution status (PENDING, RUNNING, SUCCEEDED, etc.).
        started_at: When execution started.
        completed_at: When execution completed (if finished).
        error: Error message if execution failed.
    """

    id: UUID
    step_name: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None


@dataclass
class WorkflowInstanceDTO:
    """DTO for workflow instance summary.

    Attributes:
        id: Instance ID.
        definition_name: Name of the workflow definition.
        status: Current execution status.
        current_step: Currently executing step (if applicable).
        started_at: When the workflow started.
        completed_at: When the workflow completed (if finished).
        created_by: User who started the workflow.
    """

    id: UUID
    definition_name: str
    status: str
    current_step: str | None
    started_at: datetime
    completed_at: datetime | None = None
    created_by: str | None = None


@dataclass
class WorkflowInstanceDetailDTO:
    """DTO for detailed workflow instance information.

    Extends WorkflowInstanceDTO with full context and execution history.

    Attributes:
        id: Instance ID.
        definition_name: Name of the workflow definition.
        status: Current execution status.
        current_step: Currently executing step (if applicable).
        started_at: When the workflow started.
        completed_at: When the workflow completed (if finished).
        created_by: User who started the workflow.
        context_data: Current workflow context data.
        metadata: Workflow metadata.
        step_history: List of step executions.
        error: Error message if workflow failed.
    """

    id: UUID
    definition_name: str
    status: str
    current_step: str | None
    started_at: datetime
    completed_at: datetime | None
    created_by: str | None
    context_data: dict[str, Any]
    metadata: dict[str, Any]
    step_history: list[StepExecutionDTO]
    error: str | None = None


@dataclass
class HumanTaskDTO:
    """DTO for human task summary.

    Attributes:
        id: Task ID.
        instance_id: Workflow instance ID.
        step_name: Name of the human task step.
        title: Display title for the task.
        description: Detailed task description.
        assignee: User ID assigned to complete the task.
        status: Task status (pending, completed, canceled).
        due_date: Optional due date for task completion.
        created_at: When the task was created.
        form_schema: Optional JSON Schema for task form.
    """

    id: UUID
    instance_id: UUID
    step_name: str
    title: str
    description: str | None
    assignee: str | None
    status: str
    due_date: datetime | None
    created_at: datetime
    form_schema: dict[str, Any] | None = None


@dataclass
class CompleteTaskDTO:
    """DTO for completing a human task.

    Attributes:
        output_data: Data submitted by the user completing the task.
        completed_by: User ID who completed the task.
        comment: Optional comment about the completion.
    """

    output_data: dict[str, Any]
    completed_by: str
    comment: str | None = None


@dataclass
class ReassignTaskDTO:
    """DTO for reassigning a human task.

    Attributes:
        new_assignee: User ID to assign the task to.
        reason: Optional reason for reassignment.
    """

    new_assignee: str
    reason: str | None = None


@dataclass
class GraphDTO:
    """DTO for workflow graph visualization.

    Attributes:
        mermaid_source: MermaidJS graph definition.
        nodes: List of node definitions.
        edges: List of edge definitions.
    """

    mermaid_source: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
