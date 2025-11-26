"""Web plugin for litestar-workflows.

This module provides REST API controllers and HTML UI views for managing workflows
through HTTP endpoints. The REST API is automatically enabled when using
WorkflowPlugin with enable_api=True (the default).

The API includes controllers for workflow definitions, instances, and human tasks,
along with graph visualization utilities.

The UI views (optional, requires [ui] extra) provide:
- Dashboard with workflow statistics
- Workflow definition list and detail views
- Instance list and detail views with MermaidJS graphs
- Human task forms with JSON Schema rendering

Example:
    Basic usage with WorkflowPlugin (API enabled by default)::

        from litestar import Litestar
        from litestar_workflows import WorkflowPlugin, WorkflowPluginConfig

        app = Litestar(
            plugins=[
                WorkflowPlugin(
                    config=WorkflowPluginConfig(
                        enable_api=True,  # Default
                        api_path_prefix="/workflows",
                    )
                ),
            ],
        )

    With UI enabled (requires [ui] extra)::

        from litestar import Litestar
        from litestar_workflows import WorkflowPlugin, WorkflowPluginConfig
        from litestar_workflows.web.views import WorkflowUIController, get_template_config

        app = Litestar(
            plugins=[WorkflowPlugin(config=WorkflowPluginConfig())],
            route_handlers=[WorkflowUIController],
            template_config=get_template_config(),
        )

    With authentication guards::

        from litestar_workflows import WorkflowPluginConfig

        config = WorkflowPluginConfig(
            api_path_prefix="/api/v1/workflows",
            api_guards=[require_auth_guard],
        )

        app = Litestar(
            plugins=[WorkflowPlugin(config=config)],
        )

    Disable API endpoints::

        app = Litestar(
            plugins=[
                WorkflowPlugin(config=WorkflowPluginConfig(enable_api=False)),
            ],
        )
"""

from __future__ import annotations

from litestar_workflows.web.config import WorkflowWebConfig
from litestar_workflows.web.controllers import (
    HumanTaskController,
    WorkflowDefinitionController,
    WorkflowInstanceController,
)
from litestar_workflows.web.dto import (
    CompleteTaskDTO,
    GraphDTO,
    HumanTaskDTO,
    ReassignTaskDTO,
    StartWorkflowDTO,
    StepExecutionDTO,
    WorkflowDefinitionDTO,
    WorkflowInstanceDetailDTO,
    WorkflowInstanceDTO,
)
from litestar_workflows.web.exceptions import (
    DatabaseRequiredError,
    database_required_handler,
    require_db,
)
from litestar_workflows.web.graph import (
    generate_mermaid_graph,
    generate_mermaid_graph_with_state,
    parse_graph_to_dict,
)

__all__ = [
    "CompleteTaskDTO",
    "DatabaseRequiredError",
    "GraphDTO",
    "HumanTaskController",
    "HumanTaskDTO",
    "ReassignTaskDTO",
    "StartWorkflowDTO",
    "StepExecutionDTO",
    "WorkflowDefinitionController",
    "WorkflowDefinitionDTO",
    "WorkflowInstanceController",
    "WorkflowInstanceDTO",
    "WorkflowInstanceDetailDTO",
    "WorkflowWebConfig",
    "database_required_handler",
    "generate_mermaid_graph",
    "generate_mermaid_graph_with_state",
    "parse_graph_to_dict",
    "require_db",
]
