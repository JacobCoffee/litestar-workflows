"""Litestar Workflows - Workflow automation library for Litestar.

This package provides a comprehensive workflow orchestration framework for Litestar
applications, supporting both automated and human-in-the-loop workflows.

Key Features:
    - DAG-based workflow definitions with validation
    - Sequential, parallel, and conditional execution
    - Human task integration
    - Event-driven architecture
    - Flexible execution engines (local, distributed)
    - Type-safe workflow definitions

Example:
    >>> from litestar_workflows import WorkflowDefinition, BaseStep
    >>>
    >>> class SendEmail(BaseStep):
    ...     async def execute(self, context):
    ...         await send_email(context.data["email"])
    >>>
    >>> workflow = WorkflowDefinition(
    ...     name="welcome_flow",
    ...     steps=[SendEmail(name="send_welcome")],
    ... )
"""

from __future__ import annotations

from litestar_workflows.__metadata__ import __project__, __version__
from litestar_workflows.exceptions import (
    HumanTaskError,
    InvalidTransitionError,
    StepExecutionError,
    TaskAlreadyCompletedError,
    TaskNotFoundError,
    UnauthorizedTaskError,
    WorkflowAlreadyCompletedError,
    WorkflowInstanceNotFoundError,
    WorkflowNotFoundError,
    WorkflowsError,
    WorkflowValidationError,
)

__all__ = (
    "HumanTaskError",
    "InvalidTransitionError",
    "StepExecutionError",
    "TaskAlreadyCompletedError",
    "TaskNotFoundError",
    "UnauthorizedTaskError",
    "WorkflowAlreadyCompletedError",
    "WorkflowInstanceNotFoundError",
    "WorkflowNotFoundError",
    "WorkflowValidationError",
    "WorkflowsError",
    "__project__",
    "__version__",
)
