"""Celery execution engine integration.

This module provides a Celery-based execution engine for distributed workflow
execution. Celery is a distributed task queue that supports multiple message
brokers (Redis, RabbitMQ, etc.).

Installation:
    .. code-block:: bash

        pip install litestar-workflows[celery]

Note:
    This integration is planned for Phase 6 (v0.7.0) and is currently a stub.
    See PLAN.md for the implementation roadmap.

Example (planned API):
    .. code-block:: python

        from celery import Celery
        from litestar_workflows.contrib.celery import CeleryExecutionEngine

        celery_app = Celery("workflows", broker="redis://localhost:6379/0")
        engine = CeleryExecutionEngine(
            celery_app=celery_app,
            registry=workflow_registry,
            persistence=workflow_persistence,
        )

        # Steps execute as Celery tasks
        instance = await engine.start_workflow(ApprovalWorkflow, initial_data={...})
"""

from __future__ import annotations

__all__ = ["CeleryExecutionEngine"]


class CeleryExecutionEngine:  # pragma: no cover
    """Celery-based distributed execution engine (stub).

    This engine delegates step execution to Celery workers, enabling horizontal
    scaling of workflow execution across multiple machines.

    Note:
        This is a stub implementation. The actual implementation is planned
        for Phase 6 (v0.7.0).

    Raises:
        NotImplementedError: Always raised as this is a stub.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize CeleryExecutionEngine.

        Raises:
            NotImplementedError: This is a stub implementation.
        """
        msg = (
            "CeleryExecutionEngine is not yet implemented. "
            "This feature is planned for Phase 6 (v0.7.0). "
            "See PLAN.md for the implementation roadmap."
        )
        raise NotImplementedError(msg)
