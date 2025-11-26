"""Shared test fixtures for litestar-workflows test suite."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest

if TYPE_CHECKING:
    from litestar_workflows.core.context import WorkflowContext
    from litestar_workflows.core.definition import WorkflowDefinition
    from litestar_workflows.core.models import WorkflowInstanceData
    from litestar_workflows.engine.local import LocalExecutionEngine
    from litestar_workflows.engine.registry import WorkflowRegistry
    from litestar_workflows.steps.base import BaseHumanStep, BaseMachineStep


@pytest.fixture
def sample_workflow_id() -> UUID:
    """Sample workflow ID for testing."""
    return uuid4()


@pytest.fixture
def sample_instance_id() -> UUID:
    """Sample instance ID for testing."""
    return uuid4()


@pytest.fixture
def sample_context(sample_workflow_id: UUID, sample_instance_id: UUID) -> WorkflowContext:
    """Create a sample workflow context for testing.

    Args:
        sample_workflow_id: Workflow identifier
        sample_instance_id: Instance identifier

    Returns:
        WorkflowContext instance
    """
    from litestar_workflows.core.context import WorkflowContext

    return WorkflowContext(
        workflow_id=sample_workflow_id,
        instance_id=sample_instance_id,
        data={"test_key": "test_value", "count": 0},
        metadata={"created_by": "test_user", "environment": "test"},
        current_step="initial_step",
        step_history=[],
        started_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_machine_step() -> BaseMachineStep:
    """Create a sample machine step for testing.

    Returns:
        BaseMachineStep instance
    """
    from litestar_workflows.steps.base import BaseMachineStep

    class TestMachineStep(BaseMachineStep):
        """Test machine step."""

        async def execute(self, context: WorkflowContext) -> dict[str, Any]:
            """Execute the step."""
            count = context.get("count", 0)
            context.set("count", count + 1)
            return {"executed": True, "count": count + 1}

    return TestMachineStep(name="test_machine_step", description="A test machine step")


@pytest.fixture
def sample_human_step() -> BaseHumanStep:
    """Create a sample human step for testing.

    Returns:
        BaseHumanStep instance
    """
    from litestar_workflows.steps.base import BaseHumanStep

    class TestHumanStep(BaseHumanStep):
        """Test human step."""

        async def execute(self, context: WorkflowContext) -> dict[str, Any]:
            """Execute the step."""
            approved = context.get("approved", False)
            return {"approved": approved}

    return TestHumanStep(
        name="test_human_step",
        title="Test Approval",
        description="A test human step",
        form_schema={
            "type": "object",
            "properties": {
                "approved": {"type": "boolean", "title": "Approve?"},
                "comments": {"type": "string", "title": "Comments"},
            },
            "required": ["approved"],
        },
    )


@pytest.fixture
def sample_workflow_definition(
    sample_machine_step: BaseMachineStep,
    sample_human_step: BaseHumanStep,
) -> WorkflowDefinition:
    """Create a sample workflow definition for testing.

    Args:
        sample_machine_step: Machine step fixture
        sample_human_step: Human step fixture

    Returns:
        WorkflowDefinition instance
    """
    from litestar_workflows.core.definition import Edge, WorkflowDefinition

    return WorkflowDefinition(
        name="test_workflow",
        version="1.0.0",
        description="A test workflow definition",
        steps={
            "start": sample_machine_step,
            "approval": sample_human_step,
        },
        edges=[
            Edge(source="start", target="approval"),
        ],
        initial_step="start",
        terminal_steps={"approval"},
    )


def make_workflow_class(definition: WorkflowDefinition) -> type:
    """Create a Workflow class from a WorkflowDefinition.

    This helper wraps a WorkflowDefinition in a class that conforms
    to the Workflow protocol for use with WorkflowRegistry.

    Args:
        definition: The workflow definition to wrap.

    Returns:
        A class that conforms to the Workflow protocol.
    """

    class _WorkflowClass:
        name = definition.name
        version = definition.version
        description = definition.description

        @classmethod
        def get_definition(cls) -> WorkflowDefinition:
            return definition

    return _WorkflowClass


@pytest.fixture
def sample_workflow_class(sample_workflow_definition: WorkflowDefinition) -> type:
    """Create a sample Workflow class for testing.

    Args:
        sample_workflow_definition: The workflow definition to wrap.

    Returns:
        A class conforming to Workflow protocol.
    """
    return make_workflow_class(sample_workflow_definition)


@pytest.fixture
def workflow_registry() -> WorkflowRegistry:
    """Create a workflow registry for testing.

    Returns:
        WorkflowRegistry instance
    """
    from litestar_workflows.engine.registry import WorkflowRegistry

    return WorkflowRegistry()


@pytest.fixture
def local_engine(workflow_registry: WorkflowRegistry) -> LocalExecutionEngine:
    """Create a local execution engine for testing.

    Args:
        workflow_registry: Workflow registry fixture

    Returns:
        LocalExecutionEngine instance
    """
    from litestar_workflows.engine.local import LocalExecutionEngine

    return LocalExecutionEngine(registry=workflow_registry)


class MockPersistence:
    """Mock persistence layer for testing."""

    def __init__(self) -> None:
        """Initialize mock persistence."""

        self.instances: dict[UUID, WorkflowInstanceData] = {}
        self.save_count = 0
        self.load_count = 0

    async def save_instance(self, instance: WorkflowInstanceData) -> None:
        """Save instance to mock storage."""
        self.instances[instance.id] = instance
        self.save_count += 1

    async def load_instance(self, instance_id: UUID) -> WorkflowInstanceData | None:
        """Load instance from mock storage."""
        self.load_count += 1
        return self.instances.get(instance_id)


class MockEventBus:
    """Mock event bus for testing."""

    def __init__(self) -> None:
        """Initialize mock event bus."""
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def emit(self, event_type: str, **kwargs: Any) -> None:
        """Emit an event."""
        self.events.append((event_type, kwargs))


@pytest.fixture
def mock_persistence() -> MockPersistence:
    """Create mock persistence layer.

    Returns:
        MockPersistence instance
    """
    return MockPersistence()


@pytest.fixture
def mock_event_bus() -> MockEventBus:
    """Create mock event bus.

    Returns:
        MockEventBus instance
    """
    return MockEventBus()


@pytest.fixture
def local_engine_with_persistence(
    workflow_registry: WorkflowRegistry, mock_persistence: MockPersistence
) -> LocalExecutionEngine:
    """Create a local execution engine with persistence.

    Args:
        workflow_registry: Workflow registry fixture
        mock_persistence: Mock persistence fixture

    Returns:
        LocalExecutionEngine instance with persistence
    """
    from litestar_workflows.engine.local import LocalExecutionEngine

    return LocalExecutionEngine(registry=workflow_registry, persistence=mock_persistence)


@pytest.fixture
def local_engine_with_event_bus(
    workflow_registry: WorkflowRegistry, mock_event_bus: MockEventBus
) -> LocalExecutionEngine:
    """Create a local execution engine with event bus.

    Args:
        workflow_registry: Workflow registry fixture
        mock_event_bus: Mock event bus fixture

    Returns:
        LocalExecutionEngine instance with event bus
    """
    from litestar_workflows.engine.local import LocalExecutionEngine

    return LocalExecutionEngine(registry=workflow_registry, event_bus=mock_event_bus)


@pytest.fixture
def local_engine_full(
    workflow_registry: WorkflowRegistry,
    mock_persistence: MockPersistence,
    mock_event_bus: MockEventBus,
) -> LocalExecutionEngine:
    """Create a local execution engine with all features.

    Args:
        workflow_registry: Workflow registry fixture
        mock_persistence: Mock persistence fixture
        mock_event_bus: Mock event bus fixture

    Returns:
        LocalExecutionEngine instance with persistence and event bus
    """
    from litestar_workflows.engine.local import LocalExecutionEngine

    return LocalExecutionEngine(registry=workflow_registry, persistence=mock_persistence, event_bus=mock_event_bus)


@pytest.fixture
def complex_workflow_definition() -> WorkflowDefinition:
    """Create a complex workflow with parallel and conditional paths.

    Returns:
        WorkflowDefinition with multiple branches
    """
    from litestar_workflows.core.definition import Edge, WorkflowDefinition
    from litestar_workflows.steps.base import BaseMachineStep

    class StartStep(BaseMachineStep):
        async def execute(self, context: WorkflowContext) -> dict[str, Any]:
            return {"started": True}

    class ProcessStep(BaseMachineStep):
        async def execute(self, context: WorkflowContext) -> dict[str, Any]:
            return {"processed": True}

    class ApprovalStep(BaseMachineStep):
        async def execute(self, context: WorkflowContext) -> dict[str, Any]:
            return {"approved": context.get("should_approve", True)}

    class PublishStep(BaseMachineStep):
        async def execute(self, context: WorkflowContext) -> dict[str, Any]:
            return {"published": True}

    class RejectStep(BaseMachineStep):
        async def execute(self, context: WorkflowContext) -> dict[str, Any]:
            return {"rejected": True}

    return WorkflowDefinition(
        name="complex_workflow",
        version="1.0.0",
        description="Complex workflow with branches",
        steps={
            "start": StartStep(name="start", description="Start step"),
            "process": ProcessStep(name="process", description="Process step"),
            "approval": ApprovalStep(name="approval", description="Approval step"),
            "publish": PublishStep(name="publish", description="Publish step"),
            "reject": RejectStep(name="reject", description="Reject step"),
        },
        edges=[
            Edge(source="start", target="process"),
            Edge(source="process", target="approval"),
            Edge(source="approval", target="publish", condition="approved"),
            Edge(source="approval", target="reject", condition="not approved"),
        ],
        initial_step="start",
        terminal_steps={"publish", "reject"},
    )


# Pytest configuration
def pytest_configure(config: Any) -> None:
    """Configure pytest with custom markers.

    Args:
        config: Pytest config object
    """
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Tests that take more than 1 second")
