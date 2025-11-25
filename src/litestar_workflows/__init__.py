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
    Basic plugin usage::

        from litestar import Litestar
        from litestar_workflows import WorkflowPlugin

        app = Litestar(plugins=[WorkflowPlugin()])

    Defining a workflow::

        from litestar_workflows import (
            WorkflowDefinition,
            BaseMachineStep,
            Edge,
            WorkflowContext,
        )


        class ProcessOrder(BaseMachineStep):
            name = "process_order"
            description = "Process the customer order"

            async def execute(self, context: WorkflowContext) -> dict:
                order_id = context.get("order_id")
                # Process order logic here
                return {"processed": True, "order_id": order_id}


        workflow = WorkflowDefinition(
            name="order_workflow",
            version="1.0.0",
            steps={"process": ProcessOrder()},
            edges=[],
            initial_step="process",
            terminal_steps={"process"},
        )
"""

from __future__ import annotations

from litestar_workflows.__metadata__ import __project__, __version__
from litestar_workflows.core.context import StepExecution, WorkflowContext
from litestar_workflows.core.definition import Edge, WorkflowDefinition
from litestar_workflows.core.types import StepStatus, StepType, WorkflowStatus
from litestar_workflows.engine.local import LocalExecutionEngine
from litestar_workflows.engine.registry import WorkflowRegistry
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
from litestar_workflows.plugin import WorkflowPlugin, WorkflowPluginConfig
from litestar_workflows.steps.base import BaseHumanStep, BaseMachineStep
from litestar_workflows.steps.gateway import ExclusiveGateway, ParallelGateway
from litestar_workflows.steps.groups import ConditionalGroup, ParallelGroup, SequentialGroup
from litestar_workflows.steps.timer import TimerStep

__all__ = (
    "BaseHumanStep",
    "BaseMachineStep",
    "ConditionalGroup",
    "Edge",
    "ExclusiveGateway",
    "HumanTaskError",
    "InvalidTransitionError",
    "LocalExecutionEngine",
    "ParallelGateway",
    "ParallelGroup",
    "SequentialGroup",
    "StepExecution",
    "StepExecutionError",
    "StepStatus",
    "StepType",
    "TaskAlreadyCompletedError",
    "TaskNotFoundError",
    "TimerStep",
    "UnauthorizedTaskError",
    "WorkflowAlreadyCompletedError",
    "WorkflowContext",
    "WorkflowDefinition",
    "WorkflowInstanceNotFoundError",
    "WorkflowNotFoundError",
    "WorkflowPlugin",
    "WorkflowPluginConfig",
    "WorkflowRegistry",
    "WorkflowStatus",
    "WorkflowValidationError",
    "WorkflowsError",
    "__project__",
    "__version__",
)
