"""SAQ (Simple Async Queue) execution engine integration.

This module provides a SAQ-based execution engine for distributed workflow
execution. SAQ is an async-native job queue built on Redis with a simple API.

Installation:
    .. code-block:: bash

        pip install litestar-workflows[saq]

Note:
    This integration is planned for Phase 6 (v0.7.0) and is currently a stub.
    See PLAN.md for the implementation roadmap.

Example (planned API):
    .. code-block:: python

        from saq import Queue
        from litestar_workflows.contrib.saq import SAQExecutionEngine

        queue = Queue.from_url("redis://localhost:6379/0")
        engine = SAQExecutionEngine(
            queue=queue,
            registry=workflow_registry,
            persistence=workflow_persistence,
        )

        # Steps execute as SAQ jobs
        instance = await engine.start_workflow(ApprovalWorkflow, initial_data={...})

See Also:
    - SAQ documentation: https://github.com/tobymao/saq
"""

from __future__ import annotations

__all__ = ["SAQExecutionEngine"]


class SAQExecutionEngine:
    """SAQ-based distributed execution engine (stub).

    This engine delegates step execution to SAQ workers, enabling async-native
    distributed workflow execution with Redis.

    Note:
        This is a stub implementation. The actual implementation is planned
        for Phase 6 (v0.7.0).

    Raises:
        NotImplementedError: Always raised as this is a stub.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize SAQExecutionEngine.

        Raises:
            NotImplementedError: This is a stub implementation.
        """
        msg = (
            "SAQExecutionEngine is not yet implemented. "
            "This feature is planned for Phase 6 (v0.7.0). "
            "See PLAN.md for the implementation roadmap."
        )
        raise NotImplementedError(msg)
