"""Exception handling for workflow web endpoints.

This module provides custom exceptions and exception handlers for the
workflow REST API, including database availability checks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar import Response
from litestar.status_codes import HTTP_501_NOT_IMPLEMENTED

if TYPE_CHECKING:  # pragma: no cover
    from litestar import Request

__all__ = [
    "DatabaseRequiredError",
    "database_required_handler",
    "provide_human_task_repository",
    "provide_workflow_instance_repository",
    "require_db",
]


class DatabaseRequiredError(Exception):
    """Raised when an endpoint requires database persistence but it's not available.

    This exception is raised when a user tries to access an endpoint that requires
    the [db] extra but it hasn't been installed.
    """

    def __init__(self, message: str | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Optional custom error message.
        """
        if message is None:  # pragma: no cover
            message = "This endpoint requires database persistence.\nInstall with: pip install litestar-workflows[db]"
        super().__init__(message)


def require_db() -> None:
    """Dependency that checks if database persistence is available.

    This function is used as a dependency in route handlers that require
    database functionality. It will raise DatabaseRequiredError if the
    required database components are not available.

    Raises:
        DatabaseRequiredError: If database components are not installed.

    Example:
        ```python
        from litestar import get
        from litestar.di import Provide


        @get(
            "/instances",
            dependencies={"_db_check": Provide(require_db)},
        )
        async def list_instances() -> list[dict]:
            # This endpoint requires database to be installed
            ...
        ```
    """
    try:
        from litestar_workflows.db import PersistentExecutionEngine  # noqa: F401
    except ImportError as e:  # pragma: no cover
        raise DatabaseRequiredError(
            "This endpoint requires database persistence.\nInstall with: pip install litestar-workflows[db]"
        ) from e


async def provide_workflow_instance_repository() -> Any:
    """Provide WorkflowInstanceRepository or raise error if DB not installed.

    This is used as a dependency provider for endpoints that require the
    workflow instance repository.

    Returns:
        WorkflowInstanceRepository instance.

    Raises:
        DatabaseRequiredError: If database components are not installed.
    """
    import importlib.util

    if importlib.util.find_spec("litestar_workflows.db") is None:  # pragma: no cover
        raise DatabaseRequiredError(
            "This endpoint requires database persistence.\nInstall with: pip install litestar-workflows[db]"
        )

    # DB module is available - raise error as we need proper session management
    # This will be replaced by actual repository instance in real setup
    raise DatabaseRequiredError(  # pragma: no cover
        "This endpoint requires database persistence.\nInstall with: pip install litestar-workflows[db]"
    )


async def provide_human_task_repository() -> Any:
    """Provide HumanTaskRepository or raise error if DB not installed.

    This is used as a dependency provider for endpoints that require the
    human task repository.

    Returns:
        HumanTaskRepository instance.

    Raises:
        DatabaseRequiredError: If database components are not installed.
    """
    import importlib.util

    if importlib.util.find_spec("litestar_workflows.db") is None:  # pragma: no cover
        raise DatabaseRequiredError(
            "This endpoint requires database persistence.\nInstall with: pip install litestar-workflows[db]"
        )

    # DB module is available - raise error as we need proper session management
    # This will be replaced by actual repository instance in real setup
    raise DatabaseRequiredError(  # pragma: no cover
        "This endpoint requires database persistence.\nInstall with: pip install litestar-workflows[db]"
    )


def database_required_handler(
    _request: Request,
    exc: DatabaseRequiredError,
) -> Response:
    """Exception handler for DatabaseRequiredError.

    Returns a 501 Not Implemented response with installation instructions.

    Args:
        request: The Litestar request object.
        exc: The DatabaseRequiredError exception.

    Returns:
        Response with error details and installation instructions.
    """
    return Response(
        content={
            "error": "database_required",
            "message": str(exc),
            "install": "pip install litestar-workflows[db]",
            "docs": "https://litestar-workflows.readthedocs.io/guides/persistence.html",
        },
        status_code=HTTP_501_NOT_IMPLEMENTED,
        media_type="application/json",
    )
