"""Base execution engine protocol definition.

This module re-exports the ExecutionEngine protocol from core.protocols
for convenience and organizational purposes.
"""

from __future__ import annotations

from litestar_workflows.core.protocols import ExecutionEngine

__all__ = ["ExecutionEngine"]
