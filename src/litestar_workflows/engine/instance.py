"""Workflow instance data models.

This module re-exports workflow instance data classes for convenience.
"""

from __future__ import annotations

from litestar_workflows.core.models import WorkflowInstanceData

__all__ = ["WorkflowInstanceData"]

# Alias for backwards compatibility
WorkflowInstance = WorkflowInstanceData
