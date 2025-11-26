"""Litestar plugin for workflow integration.

This module provides the WorkflowPlugin for seamless integration of
litestar-workflows with Litestar applications.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from litestar.di import Provide
from litestar.plugins import InitPluginProtocol

from litestar_workflows.engine.local import LocalExecutionEngine
from litestar_workflows.engine.registry import WorkflowRegistry

if TYPE_CHECKING:
    from litestar.config.app import AppConfig

__all__ = ["WorkflowPlugin", "WorkflowPluginConfig"]


@dataclass
class WorkflowPluginConfig:
    """Configuration for the WorkflowPlugin.

    Attributes:
        registry: Optional pre-configured WorkflowRegistry. If not provided,
            a new one will be created.
        engine: Optional pre-configured ExecutionEngine. If not provided,
            a LocalExecutionEngine will be created using the registry.
        auto_register_workflows: List of workflow classes to automatically
            register with the registry on app startup.
        dependency_key_registry: The key used for dependency injection of
            the WorkflowRegistry. Defaults to "workflow_registry".
        dependency_key_engine: The key used for dependency injection of
            the ExecutionEngine. Defaults to "workflow_engine".
        enable_api: Whether to enable the REST API endpoints. Defaults to True.
        api_path_prefix: URL path prefix for all workflow API endpoints.
            Defaults to "/workflows".
        api_guards: List of Litestar guards to apply to all workflow API endpoints.
        api_tags: OpenAPI tags to apply to workflow API endpoints.
        include_api_in_schema: Whether to include API endpoints in OpenAPI schema.
            Defaults to True.
    """

    registry: WorkflowRegistry | None = None
    engine: LocalExecutionEngine | None = None
    auto_register_workflows: list[type[Any]] = field(default_factory=list)
    dependency_key_registry: str = "workflow_registry"
    dependency_key_engine: str = "workflow_engine"
    enable_api: bool = True
    api_path_prefix: str = "/workflows"
    api_guards: list[Any] = field(default_factory=list)
    api_tags: list[str] = field(default_factory=lambda: ["Workflows"])
    include_api_in_schema: bool = True


class WorkflowPlugin(InitPluginProtocol):
    """Litestar plugin for workflow management.

    This plugin integrates litestar-workflows with a Litestar application,
    providing dependency injection for the WorkflowRegistry and ExecutionEngine.

    Example:
        Basic usage with auto-registration::

            from litestar import Litestar
            from litestar_workflows import WorkflowPlugin, WorkflowPluginConfig


            class MyWorkflow:
                __workflow_name__ = "my_workflow"
                __workflow_version__ = "1.0.0"
                # ... workflow definition


            app = Litestar(
                plugins=[
                    WorkflowPlugin(
                        config=WorkflowPluginConfig(auto_register_workflows=[MyWorkflow])
                    )
                ]
            )

        Using in a route handler::

            from litestar import get
            from litestar_workflows import WorkflowRegistry, LocalExecutionEngine


            @get("/workflows")
            async def list_workflows(
                workflow_registry: WorkflowRegistry,
            ) -> list[dict]:
                definitions = workflow_registry.list_definitions()
                return [{"name": d.name, "version": d.version} for d in definitions]


            @post("/workflows/{name}/start")
            async def start_workflow(
                name: str,
                workflow_engine: LocalExecutionEngine,
                workflow_registry: WorkflowRegistry,
            ) -> dict:
                workflow_class = workflow_registry.get_workflow_class(name)
                instance = await workflow_engine.start_workflow(workflow_class)
                return {"instance_id": str(instance.id), "status": instance.status}
    """

    __slots__ = ("_config", "_engine", "_registry")

    def __init__(self, config: WorkflowPluginConfig | None = None) -> None:
        """Initialize the plugin.

        Args:
            config: Optional configuration for the plugin.
        """
        self._config = config or WorkflowPluginConfig()
        self._registry: WorkflowRegistry | None = None
        self._engine: LocalExecutionEngine | None = None

    @property
    def registry(self) -> WorkflowRegistry:
        """Get the workflow registry.

        Returns:
            The WorkflowRegistry instance.

        Raises:
            RuntimeError: If accessed before plugin initialization.
        """
        if self._registry is None:
            msg = "WorkflowPlugin has not been initialized. Access registry after app startup."
            raise RuntimeError(msg)
        return self._registry

    @property
    def engine(self) -> LocalExecutionEngine:
        """Get the execution engine.

        Returns:
            The ExecutionEngine instance.

        Raises:
            RuntimeError: If accessed before plugin initialization.
        """
        if self._engine is None:
            msg = "WorkflowPlugin has not been initialized. Access engine after app startup."
            raise RuntimeError(msg)
        return self._engine

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Initialize the plugin when the Litestar app starts.

        This method:
        1. Creates or uses the provided WorkflowRegistry
        2. Creates or uses the provided ExecutionEngine
        3. Registers any auto_register_workflows
        4. Adds dependency providers to the app config
        5. Optionally registers REST API controllers if enable_api=True

        Args:
            app_config: The Litestar application configuration.

        Returns:
            The modified application configuration.
        """
        # Initialize registry
        self._registry = self._config.registry or WorkflowRegistry()

        # Initialize engine
        self._engine = self._config.engine or LocalExecutionEngine(registry=self._registry)

        # Auto-register workflows
        for workflow_class in self._config.auto_register_workflows:
            self._registry.register(workflow_class)

        # Create dependency providers
        def provide_registry() -> WorkflowRegistry:
            return self._registry  # type: ignore[return-value]

        def provide_engine() -> LocalExecutionEngine:
            return self._engine  # type: ignore[return-value]

        # Add dependencies to app config
        app_config.dependencies[self._config.dependency_key_registry] = Provide(
            provide_registry,
            sync_to_thread=False,
        )
        app_config.dependencies[self._config.dependency_key_engine] = Provide(
            provide_engine,
            sync_to_thread=False,
        )

        # Register REST API controllers if enabled
        if self._config.enable_api:
            from litestar import Router

            from litestar_workflows.web.controllers import (
                HumanTaskController,
                WorkflowDefinitionController,
                WorkflowInstanceController,
            )
            from litestar_workflows.web.exceptions import (
                DatabaseRequiredError,
                database_required_handler,
                provide_human_task_repository,
                provide_workflow_instance_repository,
            )

            # Add repository providers (these will raise errors if DB not installed)
            app_config.dependencies["workflow_instance_repo"] = Provide(
                provide_workflow_instance_repository,
            )
            app_config.dependencies["human_task_repo"] = Provide(
                provide_human_task_repository,
            )

            # Create controllers with path prefix
            controllers = [
                WorkflowDefinitionController,
                WorkflowInstanceController,
                HumanTaskController,
            ]

            # Create main router with configured options
            workflow_router = Router(
                path=self._config.api_path_prefix,
                route_handlers=controllers,
                guards=self._config.api_guards,
                tags=self._config.api_tags,
                include_in_schema=self._config.include_api_in_schema,
            )

            # Register router with app
            app_config.route_handlers.append(workflow_router)

            # Register exception handler
            app_config.exception_handlers[DatabaseRequiredError] = database_required_handler  # type: ignore[assignment]

        return app_config
