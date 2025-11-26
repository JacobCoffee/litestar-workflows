"""Optional integrations for litestar-workflows.

This module contains optional execution engine implementations for distributed
task queue systems. Each integration requires installing the corresponding extra:

- ``celery``: Celery distributed task queue (``pip install litestar-workflows[celery]``)
- ``saq``: Simple Async Queue for Redis (``pip install litestar-workflows[saq]``)
- ``arq``: Async Redis Queue (``pip install litestar-workflows[arq]``)

These engines extend the base ``ExecutionEngine`` protocol to enable distributed
workflow execution across multiple workers.

Example:
    .. code-block:: python

        # When celery extra is installed
        from litestar_workflows.contrib.celery import CeleryExecutionEngine

        engine = CeleryExecutionEngine(celery_app=app, registry=registry)
        await engine.start_workflow(MyWorkflow, initial_data={"key": "value"})

Note:
    These integrations are planned for Phase 6 (v0.7.0) and are currently
    stub implementations. See PLAN.md for the implementation roadmap.
"""

from __future__ import annotations

__all__: list[str] = []  # pragma: no cover
