"""Concrete data models for litestar-workflows.

This module provides concrete dataclass implementations for workflow runtime data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from litestar_workflows.core.context import WorkflowContext
    from litestar_workflows.core.types import WorkflowStatus


__all__ = ["WorkflowInstanceData"]


@dataclass
class WorkflowInstanceData:
    """Concrete data model for workflow instance state.

    This class provides the concrete implementation of workflow instance data,
    used for persistence and runtime state tracking.

    Attributes:
        id: Unique identifier for this workflow instance.
        workflow_id: Identifier of the workflow definition.
        workflow_name: Name of the workflow definition.
        workflow_version: Version of the workflow definition.
        status: Current execution status.
        context: Runtime execution context.
        current_step: Name of the currently executing or next step.
        started_at: Timestamp when the instance was created.
        completed_at: Timestamp when the instance finished.
        error: Error message if the workflow failed.
    """

    id: UUID
    workflow_name: str
    workflow_version: str
    status: WorkflowStatus
    context: WorkflowContext
    current_step: str | None
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None
    workflow_id: UUID | None = None
