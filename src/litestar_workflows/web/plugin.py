"""Litestar plugin for workflow web routes.

.. deprecated:: 0.2.0
    WorkflowWebPlugin is deprecated. Use WorkflowPlugin with enable_api=True instead.
    The REST API is now automatically available through the main WorkflowPlugin.

This module provides the legacy WorkflowWebPlugin that registers REST API controllers
for workflow management. This plugin is no longer needed as the functionality has been
merged into the main WorkflowPlugin.

Use WorkflowPlugin instead::

    from litestar_workflows import WorkflowPlugin, WorkflowPluginConfig

    app = Litestar(
        plugins=[
            WorkflowPlugin(
                config=WorkflowPluginConfig(
                    enable_api=True,  # This is the default
                    api_path_prefix="/workflows",
                )
            )
        ]
    )
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.plugins import InitPluginProtocol

from litestar_workflows.web.config import WorkflowWebConfig
from litestar_workflows.web.controllers import (
    HumanTaskController,
    WorkflowDefinitionController,
    WorkflowInstanceController,
)

if TYPE_CHECKING:
    from litestar.config.app import AppConfig

__all__ = ["WorkflowWebPlugin"]


class WorkflowWebPlugin(InitPluginProtocol):
    """Litestar plugin for workflow web routes.

    This plugin registers REST API controllers for managing workflows, instances,
    and human tasks. It should be used alongside the base WorkflowPlugin which
    provides the core workflow registry and execution engine.

    The plugin creates three controller groups:
    - WorkflowDefinitionController: List and view workflow definitions
    - WorkflowInstanceController: Start and manage workflow instances
    - HumanTaskController: Manage human approval tasks

    Example:
        Basic usage with default configuration::

            from litestar import Litestar
            from litestar_workflows import WorkflowPlugin, WorkflowPluginConfig
            from litestar_workflows.web import WorkflowWebPlugin, WorkflowWebConfig

            app = Litestar(
                plugins=[
                    WorkflowPlugin(config=WorkflowPluginConfig()),
                    WorkflowWebPlugin(config=WorkflowWebConfig()),
                ],
            )

        Custom configuration with authentication::

            from litestar_workflows.web import WorkflowWebConfig

            config = WorkflowWebConfig(
                path_prefix="/api/v1/workflows",
                guards=[require_auth_guard],
                enable_graph_endpoints=True,
            )

            app = Litestar(
                plugins=[
                    WorkflowPlugin(),
                    WorkflowWebPlugin(config=config),
                ],
            )

    Attributes:
        config: Configuration for the web plugin.
    """

    __slots__ = ("_config",)

    def __init__(self, config: WorkflowWebConfig | None = None) -> None:
        """Initialize the web plugin.

        Args:
            config: Optional configuration for the plugin. If not provided,
                default configuration will be used.
        """
        self._config = config or WorkflowWebConfig()

    @property
    def config(self) -> WorkflowWebConfig:
        """Get the plugin configuration.

        Returns:
            The WorkflowWebConfig instance.
        """
        return self._config

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Register workflow web routes on app initialization.

        This method is called by Litestar during app initialization. It registers
        the workflow controllers under the configured path prefix and applies
        any configured guards.

        The following endpoints are registered:

        **Workflow Definitions:**
        - GET {path_prefix}/definitions - List all definitions
        - GET {path_prefix}/definitions/{name} - Get specific definition
        - GET {path_prefix}/definitions/{name}/graph - Get definition graph

        **Workflow Instances:**
        - POST {path_prefix}/instances - Start new workflow
        - GET {path_prefix}/instances - List instances
        - GET {path_prefix}/instances/{id} - Get instance details
        - GET {path_prefix}/instances/{id}/graph - Get instance graph with state
        - POST {path_prefix}/instances/{id}/cancel - Cancel instance
        - POST {path_prefix}/instances/{id}/retry - Retry failed instance

        **Human Tasks:**
        - GET {path_prefix}/tasks - List tasks
        - GET {path_prefix}/tasks/{id} - Get task details
        - POST {path_prefix}/tasks/{id}/complete - Complete task
        - POST {path_prefix}/tasks/{id}/reassign - Reassign task

        Args:
            app_config: The Litestar application configuration.

        Returns:
            The modified application configuration with workflow routes registered.
        """
        from litestar import Router

        # Create controllers with path prefix
        controllers = [
            WorkflowDefinitionController,
            WorkflowInstanceController,
            HumanTaskController,
        ]

        # Create main router with configured options
        workflow_router = Router(
            path=self._config.path_prefix,
            route_handlers=controllers,
            guards=self._config.guards,
            tags=self._config.tags,
            include_in_schema=self._config.include_in_schema,
        )

        # Register router with app
        app_config.route_handlers.append(workflow_router)

        return app_config
