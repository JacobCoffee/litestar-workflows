"""ARQ (Async Redis Queue) execution engine integration.

This module provides an ARQ-based execution engine for distributed workflow
execution. ARQ is a fast async job queue built on Redis with type hints.

Installation:
    .. code-block:: bash

        pip install litestar-workflows[arq]

Note:
    This integration is planned for Phase 6 (v0.7.0) and is currently a stub.
    See PLAN.md for the implementation roadmap.

Example (planned API):
    .. code-block:: python

        from arq import create_pool
        from arq.connections import RedisSettings
        from litestar_workflows.contrib.arq import ARQExecutionEngine

        redis = await create_pool(RedisSettings())
        engine = ARQExecutionEngine(
            redis_pool=redis,
            registry=workflow_registry,
            persistence=workflow_persistence,
        )

        # Steps execute as ARQ jobs
        instance = await engine.start_workflow(ApprovalWorkflow, initial_data={...})

See Also:
    - ARQ documentation: https://arq-docs.helpmanual.io/
"""

from __future__ import annotations

__all__ = ["ARQExecutionEngine"]


class ARQExecutionEngine:  # pragma: no cover
    """ARQ-based distributed execution engine (stub).

    This engine delegates step execution to ARQ workers, enabling async-native
    distributed workflow execution with Redis and full type hint support.

    Note:
        This is a stub implementation. The actual implementation is planned
        for Phase 6 (v0.7.0).

    Raises:
        NotImplementedError: Always raised as this is a stub.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize ARQExecutionEngine.

        Raises:
            NotImplementedError: This is a stub implementation.
        """
        msg = (
            "ARQExecutionEngine is not yet implemented. "
            "This feature is planned for Phase 6 (v0.7.0). "
            "See PLAN.md for the implementation roadmap."
        )
        raise NotImplementedError(msg)
