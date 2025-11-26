"""Core type definitions for litestar-workflows.

This module defines the fundamental types, enums, and type aliases used throughout
the workflow system.
"""

from __future__ import annotations

import sys
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, TypeVar

# StrEnum backport for Python < 3.11
if sys.version_info >= (3, 11):
    from enum import StrEnum
else:

    class StrEnum(str, Enum):
        """String enumeration compatibility for Python < 3.11."""

        def __str__(self) -> str:
            return str(self.value)


# TypeAlias backport for Python < 3.10
from typing import TypeAlias

if TYPE_CHECKING:
    from litestar_workflows.core.protocols import Step, Workflow

# Re-export for convenience
from litestar_workflows.core.context import StepExecution

__all__ = [
    "Context",
    "StepExecution",
    "StepStatus",
    "StepT",
    "StepType",
    "T",
    "WorkflowStatus",
    "WorkflowT",
]


class StepType(StrEnum):
    """Classification of step types within a workflow.

    Attributes:
        MACHINE: Automated execution without human intervention.
        HUMAN: Requires user interaction and input.
        WEBHOOK: Waits for external callback or event.
        TIMER: Waits for a time-based condition to be met.
        GATEWAY: Decision or branching point in the workflow.
    """

    MACHINE = auto()
    HUMAN = auto()
    WEBHOOK = auto()
    TIMER = auto()
    GATEWAY = auto()


class StepStatus(StrEnum):
    """Execution status of a workflow step.

    Attributes:
        PENDING: Step has not yet been scheduled for execution.
        SCHEDULED: Step is queued and awaiting execution.
        RUNNING: Step is currently executing.
        WAITING: Step is paused, waiting for external input or event.
        SUCCEEDED: Step completed successfully.
        FAILED: Step execution encountered an error.
        CANCELED: Step was manually canceled before completion.
        SKIPPED: Step was skipped due to conditional logic.
    """

    PENDING = auto()
    SCHEDULED = auto()
    RUNNING = auto()
    WAITING = auto()
    SUCCEEDED = auto()
    FAILED = auto()
    CANCELED = auto()
    SKIPPED = auto()


class WorkflowStatus(StrEnum):
    """Overall status of a workflow instance.

    Attributes:
        PENDING: Workflow has been created but not yet started.
        RUNNING: Workflow is actively executing steps.
        PAUSED: Workflow execution is temporarily paused.
        WAITING: Workflow is waiting for human input or external event.
        COMPLETED: Workflow finished successfully.
        FAILED: Workflow terminated due to an error.
        CANCELED: Workflow was manually canceled.
    """

    PENDING = auto()
    RUNNING = auto()
    PAUSED = auto()
    WAITING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELED = auto()


# Type aliases for workflow data
Context: TypeAlias = dict[str, Any]
"""Type alias for workflow context data dictionary."""

# Generic type variables
StepT = TypeVar("StepT", bound="Step")
"""Type variable bound to the Step protocol."""

WorkflowT = TypeVar("WorkflowT", bound="Workflow")
"""Type variable bound to the Workflow protocol."""

T = TypeVar("T")
"""Generic type variable for return values."""
