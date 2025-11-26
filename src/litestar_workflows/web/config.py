"""Configuration for the workflow web plugin.

This module provides configuration options for the WorkflowWebPlugin, including
path prefix, schema inclusion, guards, and feature flags.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from litestar.types import Guard

__all__ = ["WorkflowWebConfig"]


@dataclass
class WorkflowWebConfig:
    """Configuration for the workflow web plugin.

    This dataclass defines all configurable options for the WorkflowWebPlugin,
    allowing users to customize the REST API endpoints, authentication, and
    feature availability.

    Attributes:
        path_prefix: URL path prefix for all workflow endpoints.
        include_in_schema: Whether to include endpoints in OpenAPI schema.
        guards: List of Litestar guards to apply to all workflow endpoints.
        enable_graph_endpoints: Whether to enable graph visualization endpoints.
        tags: OpenAPI tags to apply to workflow endpoints.

    Example:
        >>> from litestar_workflows.web import WorkflowWebConfig
        >>> config = WorkflowWebConfig(
        ...     path_prefix="/api/v1/workflows",
        ...     guards=[require_auth],
        ...     enable_graph_endpoints=True,
        ... )
    """

    path_prefix: str = "/workflows"
    include_in_schema: bool = True
    guards: list[Guard] = field(default_factory=list)
    enable_graph_endpoints: bool = True
    tags: list[str] = field(default_factory=lambda: ["Workflows"])
