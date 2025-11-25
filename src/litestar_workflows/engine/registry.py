"""Workflow registry for managing workflow definitions.

This module provides a registry for storing, retrieving, and managing
workflow definitions with support for versioning.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from litestar_workflows.core.definition import WorkflowDefinition
    from litestar_workflows.core.protocols import Workflow

__all__ = ["WorkflowRegistry"]


class WorkflowRegistry:
    """Registry for storing and retrieving workflow definitions.

    The registry maintains a mapping of workflow names to versions and their
    definitions, enabling workflow lookup and version management.

    Attributes:
        _definitions: Nested dict mapping name -> version -> WorkflowDefinition.
        _workflow_classes: Map of workflow names to their class definitions.
    """

    def __init__(self) -> None:
        """Initialize an empty workflow registry."""
        self._definitions: dict[str, dict[str, WorkflowDefinition]] = {}
        self._workflow_classes: dict[str, type[Workflow]] = {}

    def register(self, workflow_class: type[Workflow]) -> None:
        """Register a workflow class with the registry.

        Extracts the workflow definition from the class and stores it
        indexed by name and version.

        Args:
            workflow_class: The workflow class to register.

        Example:
            >>> registry = WorkflowRegistry()
            >>> registry.register(MyWorkflow)
        """
        definition = workflow_class.get_definition()

        # Initialize version dict if needed
        if definition.name not in self._definitions:
            self._definitions[definition.name] = {}

        # Store the definition
        self._definitions[definition.name][definition.version] = definition

        # Store the workflow class
        self._workflow_classes[definition.name] = workflow_class

    def get_definition(
        self,
        name: str,
        version: str | None = None,
    ) -> WorkflowDefinition:
        """Retrieve a workflow definition by name and optional version.

        Args:
            name: The workflow name.
            version: The workflow version. If None, returns the latest version.

        Returns:
            The WorkflowDefinition for the requested workflow.

        Raises:
            KeyError: If the workflow name or version is not found.

        Example:
            >>> definition = registry.get_definition("approval_workflow")
            >>> definition_v1 = registry.get_definition("approval_workflow", "1.0.0")
        """
        if name not in self._definitions:
            msg = f"Workflow '{name}' not found in registry"
            raise KeyError(msg)

        versions = self._definitions[name]

        if version is None:
            # Return the latest version (highest semantic version or last registered)
            version = max(versions.keys())

        if version not in versions:
            available = ", ".join(versions.keys())
            msg = f"Version '{version}' not found for workflow '{name}'. Available versions: {available}"
            raise KeyError(msg)

        return versions[version]

    def get_workflow_class(self, name: str) -> type[Workflow]:
        """Retrieve the workflow class by name.

        Args:
            name: The workflow name.

        Returns:
            The Workflow class.

        Raises:
            KeyError: If the workflow name is not found.

        Example:
            >>> WorkflowClass = registry.get_workflow_class("approval_workflow")
            >>> instance = await engine.start_workflow(WorkflowClass)
        """
        if name not in self._workflow_classes:
            msg = f"Workflow class '{name}' not found in registry"
            raise KeyError(msg)

        return self._workflow_classes[name]

    def list_definitions(self, active_only: bool = True) -> list[WorkflowDefinition]:
        """List all registered workflow definitions.

        Args:
            active_only: If True, only return the latest version of each workflow.
                If False, return all versions.

        Returns:
            List of WorkflowDefinition objects.

        Example:
            >>> all_workflows = registry.list_definitions()
            >>> all_versions = registry.list_definitions(active_only=False)
        """
        definitions = []

        for versions in self._definitions.values():
            if active_only:
                # Only include the latest version
                latest_version = max(versions.keys())
                definitions.append(versions[latest_version])
            else:
                # Include all versions
                definitions.extend(versions.values())

        return definitions

    def unregister(self, name: str, version: str | None = None) -> None:
        """Remove a workflow from the registry.

        Args:
            name: The workflow name.
            version: The specific version to remove. If None, removes all versions.

        Example:
            >>> registry.unregister("old_workflow")
            >>> registry.unregister("approval_workflow", "1.0.0")
        """
        if name not in self._definitions:
            return

        if version is None:
            # Remove all versions
            del self._definitions[name]
            if name in self._workflow_classes:
                del self._workflow_classes[name]
        else:
            # Remove specific version
            if version in self._definitions[name]:
                del self._definitions[name][version]

            # If no versions left, remove the workflow class too
            if not self._definitions[name]:
                del self._definitions[name]
                if name in self._workflow_classes:
                    del self._workflow_classes[name]

    def has_workflow(self, name: str, version: str | None = None) -> bool:
        """Check if a workflow exists in the registry.

        Args:
            name: The workflow name.
            version: Optional specific version to check.

        Returns:
            True if the workflow exists, False otherwise.

        Example:
            >>> if registry.has_workflow("approval_workflow"):
            ...     definition = registry.get_definition("approval_workflow")
        """
        if name not in self._definitions:
            return False

        if version is None:
            return True

        return version in self._definitions[name]

    def get_versions(self, name: str) -> list[str]:
        """Get all versions for a workflow.

        Args:
            name: The workflow name.

        Returns:
            List of version strings.

        Raises:
            KeyError: If the workflow name is not found.

        Example:
            >>> versions = registry.get_versions("approval_workflow")
            >>> print(versions)  # ['1.0.0', '1.1.0', '2.0.0']
        """
        if name not in self._definitions:
            msg = f"Workflow '{name}' not found in registry"
            raise KeyError(msg)

        return list(self._definitions[name].keys())
