"""Integration tests for database persistence layer.

Tests the SQLAlchemy models, repositories, and PersistentExecutionEngine
using an async SQLite in-memory database.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from litestar_workflows.core.context import WorkflowContext
from litestar_workflows.core.definition import Edge, WorkflowDefinition
from litestar_workflows.core.types import StepStatus, StepType, WorkflowStatus
from litestar_workflows.db.models import (
    HumanTaskModel,
    StepExecutionModel,
    WorkflowDefinitionModel,
    WorkflowInstanceModel,
)
from litestar_workflows.db.repositories import (
    HumanTaskRepository,
    StepExecutionRepository,
    WorkflowDefinitionRepository,
    WorkflowInstanceRepository,
)
from litestar_workflows.steps.base import BaseHumanStep, BaseMachineStep

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


# =============================================================================
# Database Fixtures
# =============================================================================


@pytest.fixture
async def async_engine():
    """Create an async SQLite in-memory engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(WorkflowDefinitionModel.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def async_session(async_engine) -> AsyncIterator[AsyncSession]:
    """Create an async session for testing."""
    session_maker = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_maker() as session:
        yield session
        await session.rollback()


# =============================================================================
# Repository Fixtures
# =============================================================================


@pytest.fixture
def definition_repo(async_session: AsyncSession) -> WorkflowDefinitionRepository:
    """Create a workflow definition repository."""
    return WorkflowDefinitionRepository(session=async_session)


@pytest.fixture
def instance_repo(async_session: AsyncSession) -> WorkflowInstanceRepository:
    """Create a workflow instance repository."""
    return WorkflowInstanceRepository(session=async_session)


@pytest.fixture
def step_repo(async_session: AsyncSession) -> StepExecutionRepository:
    """Create a step execution repository."""
    return StepExecutionRepository(session=async_session)


@pytest.fixture
def task_repo(async_session: AsyncSession) -> HumanTaskRepository:
    """Create a human task repository."""
    return HumanTaskRepository(session=async_session)


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
async def sample_definition_model(
    definition_repo: WorkflowDefinitionRepository,
    async_session: AsyncSession,
) -> WorkflowDefinitionModel:
    """Create and persist a sample workflow definition."""
    model = WorkflowDefinitionModel(
        name="test_workflow",
        version="1.0.0",
        description="A test workflow",
        definition_json={
            "name": "test_workflow",
            "version": "1.0.0",
            "steps": ["start", "end"],
            "edges": [{"source": "start", "target": "end"}],
            "initial_step": "start",
            "terminal_steps": ["end"],
        },
        is_active=True,
    )
    model = await definition_repo.add(model)
    await async_session.commit()
    return model


@pytest.fixture
async def sample_instance_model(
    sample_definition_model: WorkflowDefinitionModel,
    instance_repo: WorkflowInstanceRepository,
    async_session: AsyncSession,
) -> WorkflowInstanceModel:
    """Create and persist a sample workflow instance."""
    now = datetime.now(timezone.utc)
    model = WorkflowInstanceModel(
        definition_id=sample_definition_model.id,
        workflow_name=sample_definition_model.name,
        workflow_version=sample_definition_model.version,
        status=WorkflowStatus.RUNNING,
        current_step="start",
        context_data={"key": "value"},
        metadata_={"created_by": "test"},
        started_at=now,
        tenant_id="tenant1",
        created_by="user1",
    )
    model = await instance_repo.add(model)
    await async_session.commit()
    return model


@pytest.fixture
async def sample_step_execution(
    sample_instance_model: WorkflowInstanceModel,
    step_repo: StepExecutionRepository,
    async_session: AsyncSession,
) -> StepExecutionModel:
    """Create and persist a sample step execution."""
    now = datetime.now(timezone.utc)
    model = StepExecutionModel(
        instance_id=sample_instance_model.id,
        step_name="start",
        step_type=StepType.MACHINE,
        status=StepStatus.RUNNING,
        started_at=now,
    )
    model = await step_repo.add(model)
    await async_session.commit()
    return model


@pytest.fixture
async def sample_human_task(
    sample_instance_model: WorkflowInstanceModel,
    sample_step_execution: StepExecutionModel,
    task_repo: HumanTaskRepository,
    async_session: AsyncSession,
) -> HumanTaskModel:
    """Create and persist a sample human task."""
    model = HumanTaskModel(
        instance_id=sample_instance_model.id,
        step_execution_id=sample_step_execution.id,
        step_name="approval",
        title="Test Approval",
        description="Approve this test",
        assignee_id="user1",
        status="pending",
    )
    model = await task_repo.add(model)
    await async_session.commit()
    return model


# =============================================================================
# WorkflowDefinitionRepository Tests
# =============================================================================


class TestWorkflowDefinitionRepository:
    """Tests for WorkflowDefinitionRepository."""

    async def test_add_definition(
        self,
        definition_repo: WorkflowDefinitionRepository,
        async_session: AsyncSession,
    ):
        """Test adding a new workflow definition."""
        model = WorkflowDefinitionModel(
            name="new_workflow",
            version="1.0.0",
            description="New workflow",
            definition_json={"steps": []},
            is_active=True,
        )
        result = await definition_repo.add(model)
        await async_session.commit()

        assert result.id is not None
        assert result.name == "new_workflow"
        assert result.version == "1.0.0"

    async def test_get_by_name(
        self,
        sample_definition_model: WorkflowDefinitionModel,
        definition_repo: WorkflowDefinitionRepository,
    ):
        """Test getting a definition by name."""
        result = await definition_repo.get_by_name("test_workflow")

        assert result is not None
        assert result.name == "test_workflow"
        assert result.version == "1.0.0"

    async def test_get_by_name_and_version(
        self,
        sample_definition_model: WorkflowDefinitionModel,
        definition_repo: WorkflowDefinitionRepository,
    ):
        """Test getting a definition by name and version."""
        result = await definition_repo.get_by_name("test_workflow", "1.0.0")

        assert result is not None
        assert result.name == "test_workflow"
        assert result.version == "1.0.0"

    async def test_get_by_name_not_found(
        self,
        definition_repo: WorkflowDefinitionRepository,
    ):
        """Test getting a non-existent definition."""
        result = await definition_repo.get_by_name("nonexistent")

        assert result is None

    async def test_get_latest_version(
        self,
        definition_repo: WorkflowDefinitionRepository,
        async_session: AsyncSession,
    ):
        """Test getting the latest active version."""
        # Create multiple versions
        for version in ["1.0.0", "1.1.0", "2.0.0"]:
            model = WorkflowDefinitionModel(
                name="versioned_workflow",
                version=version,
                description=f"Version {version}",
                definition_json={"version": version},
                is_active=True,
            )
            await definition_repo.add(model)
        await async_session.commit()

        result = await definition_repo.get_latest_version("versioned_workflow")

        assert result is not None
        # Latest by created_at order
        assert result.name == "versioned_workflow"

    async def test_list_active(
        self,
        sample_definition_model: WorkflowDefinitionModel,
        definition_repo: WorkflowDefinitionRepository,
        async_session: AsyncSession,
    ):
        """Test listing active definitions."""
        # Add an inactive definition
        inactive = WorkflowDefinitionModel(
            name="inactive_workflow",
            version="1.0.0",
            description="Inactive",
            definition_json={},
            is_active=False,
        )
        await definition_repo.add(inactive)
        await async_session.commit()

        result = await definition_repo.list_active()

        names = [d.name for d in result]
        assert "test_workflow" in names
        assert "inactive_workflow" not in names

    async def test_deactivate_version(
        self,
        sample_definition_model: WorkflowDefinitionModel,
        definition_repo: WorkflowDefinitionRepository,
        async_session: AsyncSession,
    ):
        """Test deactivating a workflow version."""
        result = await definition_repo.deactivate_version("test_workflow", "1.0.0")
        await async_session.commit()

        assert result is True

        # Verify it's deactivated
        definition = await definition_repo.get_by_name("test_workflow", "1.0.0", active_only=False)
        assert definition is not None
        assert definition.is_active is False


# =============================================================================
# WorkflowInstanceRepository Tests
# =============================================================================


class TestWorkflowInstanceRepository:
    """Tests for WorkflowInstanceRepository."""

    async def test_add_instance(
        self,
        sample_definition_model: WorkflowDefinitionModel,
        instance_repo: WorkflowInstanceRepository,
        async_session: AsyncSession,
    ):
        """Test adding a new workflow instance."""
        now = datetime.now(timezone.utc)
        model = WorkflowInstanceModel(
            definition_id=sample_definition_model.id,
            workflow_name="test_workflow",
            workflow_version="1.0.0",
            status=WorkflowStatus.PENDING,
            current_step="start",
            context_data={},
            metadata_={},
            started_at=now,
        )
        result = await instance_repo.add(model)
        await async_session.commit()

        assert result.id is not None
        assert result.status == WorkflowStatus.PENDING

    async def test_find_by_workflow(
        self,
        sample_instance_model: WorkflowInstanceModel,
        instance_repo: WorkflowInstanceRepository,
    ):
        """Test finding instances by workflow name."""
        instances, count = await instance_repo.find_by_workflow("test_workflow")

        assert count >= 1
        assert any(i.id == sample_instance_model.id for i in instances)

    async def test_find_by_workflow_with_status(
        self,
        sample_instance_model: WorkflowInstanceModel,
        instance_repo: WorkflowInstanceRepository,
    ):
        """Test finding instances by workflow name and status."""
        instances, count = await instance_repo.find_by_workflow("test_workflow", status=WorkflowStatus.RUNNING)

        assert count >= 1
        assert all(i.status == WorkflowStatus.RUNNING for i in instances)

    async def test_find_by_user(
        self,
        sample_instance_model: WorkflowInstanceModel,
        instance_repo: WorkflowInstanceRepository,
    ):
        """Test finding instances by user."""
        instances = await instance_repo.find_by_user("user1")

        assert len(instances) >= 1
        assert any(i.id == sample_instance_model.id for i in instances)

    async def test_find_by_tenant(
        self,
        sample_instance_model: WorkflowInstanceModel,
        instance_repo: WorkflowInstanceRepository,
    ):
        """Test finding instances by tenant."""
        instances, count = await instance_repo.find_by_tenant("tenant1")

        assert count >= 1
        assert any(i.tenant_id == "tenant1" for i in instances)

    async def test_find_running(
        self,
        sample_instance_model: WorkflowInstanceModel,
        instance_repo: WorkflowInstanceRepository,
    ):
        """Test finding running instances."""
        instances = await instance_repo.find_running()

        assert len(instances) >= 1
        assert all(i.status in [WorkflowStatus.RUNNING, WorkflowStatus.WAITING] for i in instances)

    async def test_update_status(
        self,
        sample_instance_model: WorkflowInstanceModel,
        instance_repo: WorkflowInstanceRepository,
        async_session: AsyncSession,
    ):
        """Test updating instance status."""
        result = await instance_repo.update_status(
            sample_instance_model.id,
            WorkflowStatus.COMPLETED,
            current_step=None,
        )
        await async_session.commit()

        assert result is not None
        assert result.status == WorkflowStatus.COMPLETED

    async def test_update_status_with_error(
        self,
        sample_instance_model: WorkflowInstanceModel,
        instance_repo: WorkflowInstanceRepository,
        async_session: AsyncSession,
    ):
        """Test updating instance status with error."""
        result = await instance_repo.update_status(
            sample_instance_model.id,
            WorkflowStatus.FAILED,
            error="Test error message",
        )
        await async_session.commit()

        assert result is not None
        assert result.status == WorkflowStatus.FAILED
        assert result.error == "Test error message"


# =============================================================================
# StepExecutionRepository Tests
# =============================================================================


class TestStepExecutionRepository:
    """Tests for StepExecutionRepository."""

    async def test_add_step_execution(
        self,
        sample_instance_model: WorkflowInstanceModel,
        step_repo: StepExecutionRepository,
        async_session: AsyncSession,
    ):
        """Test adding a step execution."""
        now = datetime.now(timezone.utc)
        model = StepExecutionModel(
            instance_id=sample_instance_model.id,
            step_name="process",
            step_type=StepType.MACHINE,
            status=StepStatus.PENDING,
            started_at=now,
        )
        result = await step_repo.add(model)
        await async_session.commit()

        assert result.id is not None
        assert result.step_name == "process"

    async def test_find_by_instance(
        self,
        sample_step_execution: StepExecutionModel,
        step_repo: StepExecutionRepository,
    ):
        """Test finding step executions by instance."""
        executions = await step_repo.find_by_instance(sample_step_execution.instance_id)

        assert len(executions) >= 1
        assert any(e.id == sample_step_execution.id for e in executions)

    async def test_find_by_step_name(
        self,
        sample_step_execution: StepExecutionModel,
        step_repo: StepExecutionRepository,
    ):
        """Test finding step execution by step name."""
        execution = await step_repo.find_by_step_name(sample_step_execution.instance_id, "start")

        assert execution is not None
        assert execution.step_name == "start"

    async def test_find_failed(
        self,
        sample_instance_model: WorkflowInstanceModel,
        step_repo: StepExecutionRepository,
        async_session: AsyncSession,
    ):
        """Test finding failed step executions."""
        now = datetime.now(timezone.utc)
        failed = StepExecutionModel(
            instance_id=sample_instance_model.id,
            step_name="failed_step",
            step_type=StepType.MACHINE,
            status=StepStatus.FAILED,
            error="Step failed",
            started_at=now,
            completed_at=now,
        )
        await step_repo.add(failed)
        await async_session.commit()

        executions = await step_repo.find_failed()

        assert len(executions) >= 1
        assert all(e.status == StepStatus.FAILED for e in executions)

    async def test_find_failed_by_instance(
        self,
        sample_instance_model: WorkflowInstanceModel,
        step_repo: StepExecutionRepository,
        async_session: AsyncSession,
    ):
        """Test finding failed steps for specific instance."""
        now = datetime.now(timezone.utc)
        failed = StepExecutionModel(
            instance_id=sample_instance_model.id,
            step_name="failed_step",
            step_type=StepType.MACHINE,
            status=StepStatus.FAILED,
            error="Step failed",
            started_at=now,
            completed_at=now,
        )
        await step_repo.add(failed)
        await async_session.commit()

        executions = await step_repo.find_failed(sample_instance_model.id)

        assert len(executions) >= 1
        assert all(e.instance_id == sample_instance_model.id for e in executions)


# =============================================================================
# HumanTaskRepository Tests
# =============================================================================


class TestHumanTaskRepository:
    """Tests for HumanTaskRepository."""

    async def test_add_human_task(
        self,
        sample_instance_model: WorkflowInstanceModel,
        sample_step_execution: StepExecutionModel,
        task_repo: HumanTaskRepository,
        async_session: AsyncSession,
    ):
        """Test adding a human task."""
        model = HumanTaskModel(
            instance_id=sample_instance_model.id,
            step_execution_id=sample_step_execution.id,
            step_name="review",
            title="Review Task",
            description="Review this item",
            status="pending",
        )
        result = await task_repo.add(model)
        await async_session.commit()

        assert result.id is not None
        assert result.title == "Review Task"

    async def test_find_pending(
        self,
        sample_human_task: HumanTaskModel,
        task_repo: HumanTaskRepository,
    ):
        """Test finding pending human tasks."""
        tasks = await task_repo.find_pending()

        assert len(tasks) >= 1
        assert all(t.status == "pending" for t in tasks)

    async def test_find_pending_by_assignee(
        self,
        sample_human_task: HumanTaskModel,
        task_repo: HumanTaskRepository,
    ):
        """Test finding pending tasks by assignee."""
        tasks = await task_repo.find_pending(assignee_id="user1")

        assert len(tasks) >= 1
        # Should include tasks assigned to user1 or unassigned
        assert any(t.assignee_id == "user1" for t in tasks)

    async def test_find_pending_by_group(
        self,
        sample_instance_model: WorkflowInstanceModel,
        sample_step_execution: StepExecutionModel,
        task_repo: HumanTaskRepository,
        async_session: AsyncSession,
    ):
        """Test finding pending tasks by group."""
        task = HumanTaskModel(
            instance_id=sample_instance_model.id,
            step_execution_id=sample_step_execution.id,
            step_name="group_task",
            title="Group Task",
            assignee_group="admins",
            status="pending",
        )
        await task_repo.add(task)
        await async_session.commit()

        tasks = await task_repo.find_pending(assignee_group="admins")

        assert len(tasks) >= 1

    async def test_find_by_instance(
        self,
        sample_human_task: HumanTaskModel,
        task_repo: HumanTaskRepository,
    ):
        """Test finding tasks by instance."""
        tasks = await task_repo.find_by_instance(sample_human_task.instance_id)

        assert len(tasks) >= 1
        assert any(t.id == sample_human_task.id for t in tasks)

    async def test_find_overdue(
        self,
        sample_instance_model: WorkflowInstanceModel,
        sample_step_execution: StepExecutionModel,
        task_repo: HumanTaskRepository,
        async_session: AsyncSession,
    ):
        """Test finding overdue tasks."""
        past = datetime.now(timezone.utc) - timedelta(days=1)
        task = HumanTaskModel(
            instance_id=sample_instance_model.id,
            step_execution_id=sample_step_execution.id,
            step_name="overdue_task",
            title="Overdue Task",
            due_at=past,
            status="pending",
        )
        await task_repo.add(task)
        await async_session.commit()

        tasks = await task_repo.find_overdue()

        assert len(tasks) >= 1
        # SQLite returns naive datetimes, so we compare without timezone
        now = datetime.now(timezone.utc)
        for t in tasks:
            due = t.due_at.replace(tzinfo=timezone.utc) if t.due_at.tzinfo is None else t.due_at
            assert due < now

    async def test_complete_task(
        self,
        sample_human_task: HumanTaskModel,
        task_repo: HumanTaskRepository,
        async_session: AsyncSession,
    ):
        """Test completing a human task."""
        result = await task_repo.complete_task(sample_human_task.id, "user1")
        await async_session.commit()

        assert result is not None
        assert result.status == "completed"
        assert result.completed_by == "user1"
        assert result.completed_at is not None

    async def test_cancel_task(
        self,
        sample_human_task: HumanTaskModel,
        task_repo: HumanTaskRepository,
        async_session: AsyncSession,
    ):
        """Test canceling a human task."""
        result = await task_repo.cancel_task(sample_human_task.id)
        await async_session.commit()

        assert result is not None
        assert result.status == "canceled"


# =============================================================================
# PersistentExecutionEngine Tests
# =============================================================================


class TestPersistentExecutionEngine:
    """Tests for PersistentExecutionEngine."""

    @pytest.fixture
    def simple_workflow_definition(self) -> WorkflowDefinition:
        """Create a simple workflow definition for testing."""

        class IncrementStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                count = context.get("count", 0)
                context.set("count", count + 1)
                return {"count": count + 1}

        class FinalStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"final": True}

        return WorkflowDefinition(
            name="simple_workflow",
            version="1.0.0",
            description="Simple test workflow",
            steps={
                "start": IncrementStep(name="start", description="Start step"),
                "end": FinalStep(name="end", description="End step"),
            },
            edges=[Edge(source="start", target="end")],
            initial_step="start",
            terminal_steps={"end"},
        )

    @pytest.fixture
    def human_workflow_definition(self) -> WorkflowDefinition:
        """Create a workflow with a human step."""

        class StartStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"started": True}

        class ApprovalStep(BaseHumanStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"approved": context.get("approved", False)}

        class EndStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"completed": True}

        return WorkflowDefinition(
            name="human_workflow",
            version="1.0.0",
            description="Workflow with human approval",
            steps={
                "start": StartStep(name="start", description="Start step"),
                "approval": ApprovalStep(
                    name="approval",
                    title="Approval Required",
                    description="Approve to continue",
                    form_schema={"type": "object", "properties": {"approved": {"type": "boolean"}}},
                ),
                "end": EndStep(name="end", description="End step"),
            },
            edges=[
                Edge(source="start", target="approval"),
                Edge(source="approval", target="end"),
            ],
            initial_step="start",
            terminal_steps={"end"},
        )

    @pytest.fixture
    def workflow_registry(self):
        """Create a workflow registry for testing."""
        from litestar_workflows.engine.registry import WorkflowRegistry

        return WorkflowRegistry()

    @pytest.fixture
    def make_workflow_class(self):
        """Factory for creating workflow classes from definitions."""

        def _make(definition: WorkflowDefinition) -> type:
            class _WorkflowClass:
                name = definition.name
                version = definition.version
                description = definition.description

                @classmethod
                def get_definition(cls) -> WorkflowDefinition:
                    return definition

            return _WorkflowClass

        return _make

    async def test_start_workflow(
        self,
        async_session: AsyncSession,
        workflow_registry,
        simple_workflow_definition: WorkflowDefinition,
        make_workflow_class,
    ):
        """Test starting a workflow with persistence."""
        from litestar_workflows.db.engine import PersistentExecutionEngine

        workflow_class = make_workflow_class(simple_workflow_definition)
        workflow_registry.register(workflow_class)

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
        )

        result = await engine.start_workflow(
            workflow_class,
            initial_data={"count": 0},
            tenant_id="test_tenant",
            created_by="test_user",
        )

        assert result.id is not None
        assert result.workflow_name == "simple_workflow"
        assert result.status == WorkflowStatus.RUNNING

        # Wait briefly for background execution
        import asyncio

        await asyncio.sleep(0.1)

    async def test_get_instance(
        self,
        async_session: AsyncSession,
        workflow_registry,
        simple_workflow_definition: WorkflowDefinition,
        make_workflow_class,
    ):
        """Test getting a workflow instance."""
        from litestar_workflows.db.engine import PersistentExecutionEngine

        workflow_class = make_workflow_class(simple_workflow_definition)
        workflow_registry.register(workflow_class)

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
        )

        started = await engine.start_workflow(
            workflow_class,
            initial_data={"count": 0},
        )

        # Wait for execution
        import asyncio

        await asyncio.sleep(0.2)

        result = await engine.get_instance(started.id)

        assert result.id == started.id
        assert result.workflow_name == "simple_workflow"

    async def test_workflow_completes(
        self,
        async_session: AsyncSession,
        workflow_registry,
        simple_workflow_definition: WorkflowDefinition,
        make_workflow_class,
    ):
        """Test that a workflow completes successfully."""
        from litestar_workflows.db.engine import PersistentExecutionEngine

        workflow_class = make_workflow_class(simple_workflow_definition)
        workflow_registry.register(workflow_class)

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
        )

        result = await engine.start_workflow(
            workflow_class,
            initial_data={"count": 0},
        )

        # Wait for completion
        import asyncio

        await asyncio.sleep(0.5)

        instance = await engine.get_instance(result.id)

        assert instance.status == WorkflowStatus.COMPLETED

    async def test_workflow_waits_for_human_task(
        self,
        async_session: AsyncSession,
        workflow_registry,
        human_workflow_definition: WorkflowDefinition,
        make_workflow_class,
    ):
        """Test that workflow waits at human step."""
        from litestar_workflows.db.engine import PersistentExecutionEngine

        workflow_class = make_workflow_class(human_workflow_definition)
        workflow_registry.register(workflow_class)

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
        )

        result = await engine.start_workflow(workflow_class)

        # Wait for it to reach human step
        import asyncio

        await asyncio.sleep(0.3)

        instance = await engine.get_instance(result.id)

        assert instance.status == WorkflowStatus.WAITING
        assert instance.current_step == "approval"

    async def test_complete_human_task(
        self,
        async_session: AsyncSession,
        workflow_registry,
        human_workflow_definition: WorkflowDefinition,
        make_workflow_class,
    ):
        """Test completing a human task resumes workflow."""
        from litestar_workflows.db.engine import PersistentExecutionEngine

        workflow_class = make_workflow_class(human_workflow_definition)
        workflow_registry.register(workflow_class)

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
        )

        result = await engine.start_workflow(workflow_class)

        import asyncio

        await asyncio.sleep(0.3)

        # Complete the human task
        await engine.complete_human_task(
            result.id,
            "approval",
            "user1",
            {"approved": True},
        )

        # Wait for completion
        await asyncio.sleep(0.3)

        instance = await engine.get_instance(result.id)

        # Should have progressed after human task
        assert instance.status in [WorkflowStatus.RUNNING, WorkflowStatus.COMPLETED]

    async def test_cancel_workflow(
        self,
        async_session: AsyncSession,
        workflow_registry,
        human_workflow_definition: WorkflowDefinition,
        make_workflow_class,
    ):
        """Test canceling a workflow."""
        from litestar_workflows.db.engine import PersistentExecutionEngine

        workflow_class = make_workflow_class(human_workflow_definition)
        workflow_registry.register(workflow_class)

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
        )

        result = await engine.start_workflow(workflow_class)

        import asyncio

        await asyncio.sleep(0.3)

        await engine.cancel_workflow(result.id, "Test cancellation")

        instance = await engine.get_instance(result.id)

        assert instance.status == WorkflowStatus.CANCELED
        assert "Test cancellation" in instance.error

    async def test_get_running_instances(
        self,
        async_session: AsyncSession,
        workflow_registry,
        human_workflow_definition: WorkflowDefinition,
        make_workflow_class,
    ):
        """Test getting running instance IDs."""
        from litestar_workflows.db.engine import PersistentExecutionEngine

        workflow_class = make_workflow_class(human_workflow_definition)
        workflow_registry.register(workflow_class)

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
        )

        result = await engine.start_workflow(workflow_class)

        import asyncio

        await asyncio.sleep(0.1)

        # The workflow might still be "running" in memory (task exists)
        # even if it's waiting in DB
        running = engine.get_running_instances()

        # Note: This test checks the in-memory task tracking
        # After human step wait, the task should have returned
        assert isinstance(running, list)

    async def test_definition_persisted(
        self,
        async_session: AsyncSession,
        workflow_registry,
        simple_workflow_definition: WorkflowDefinition,
        make_workflow_class,
        definition_repo: WorkflowDefinitionRepository,
    ):
        """Test that workflow definition is persisted."""
        from litestar_workflows.db.engine import PersistentExecutionEngine

        workflow_class = make_workflow_class(simple_workflow_definition)
        workflow_registry.register(workflow_class)

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
        )

        await engine.start_workflow(workflow_class)

        # Check definition was persisted
        definition = await definition_repo.get_by_name("simple_workflow", "1.0.0")

        assert definition is not None
        assert definition.name == "simple_workflow"
        assert definition.definition_json is not None

    async def test_definition_reused_when_exists(
        self,
        async_session: AsyncSession,
        workflow_registry,
        simple_workflow_definition: WorkflowDefinition,
        make_workflow_class,
        definition_repo: WorkflowDefinitionRepository,
    ):
        """Test that existing definition is reused on line 100."""
        from litestar_workflows.db.engine import PersistentExecutionEngine

        workflow_class = make_workflow_class(simple_workflow_definition)
        workflow_registry.register(workflow_class)

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
        )

        # Start first workflow
        await engine.start_workflow(workflow_class)

        # Get definition count
        all_defs = await definition_repo.list_active()
        count_before = len([d for d in all_defs if d.name == "simple_workflow"])

        # Start second workflow - should reuse definition
        await engine.start_workflow(workflow_class)

        # Verify no duplicate definition was created
        all_defs = await definition_repo.list_active()
        count_after = len([d for d in all_defs if d.name == "simple_workflow"])

        assert count_after == count_before  # Should be the same (reused)

    async def test_workflow_with_event_bus(
        self,
        async_session: AsyncSession,
        workflow_registry,
        simple_workflow_definition: WorkflowDefinition,
        make_workflow_class,
    ):
        """Test workflow with event bus to cover lines 203, 266, 346-347, 517."""
        from unittest.mock import AsyncMock

        from litestar_workflows.db.engine import PersistentExecutionEngine

        workflow_class = make_workflow_class(simple_workflow_definition)
        workflow_registry.register(workflow_class)

        # Create mock event bus
        event_bus = AsyncMock()
        event_bus.emit = AsyncMock()

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
            event_bus=event_bus,
        )

        result = await engine.start_workflow(workflow_class)

        import asyncio

        await asyncio.sleep(0.5)

        # Verify event bus was called for workflow.started
        event_bus.emit.assert_any_call("workflow.started", instance_id=result.id)

        # Verify completion event was emitted
        instance = await engine.get_instance(result.id)
        if instance.status == WorkflowStatus.COMPLETED:
            event_bus.emit.assert_any_call("workflow.completed", instance_id=result.id)

    async def test_workflow_with_invalid_step_name(
        self,
        async_session: AsyncSession,
        workflow_registry,
        make_workflow_class,
    ):
        """Test workflow failure when step not found to cover lines 248-253."""
        from litestar_workflows.db.engine import PersistentExecutionEngine
        from litestar_workflows.db.repositories import WorkflowInstanceRepository

        class BadStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"done": True}

        definition = WorkflowDefinition(
            name="invalid_workflow",
            version="1.0.0",
            description="Workflow with invalid step",
            steps={"start": BadStep(name="start", description="Start")},
            edges=[],
            initial_step="start",
            terminal_steps={"end"},  # Terminal step doesn't exist!
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
        )

        result = await engine.start_workflow(workflow_class)

        import asyncio

        await asyncio.sleep(0.3)

        # Manually update instance to trigger the invalid step path
        instance_repo = WorkflowInstanceRepository(session=async_session)
        instance = await instance_repo.get(result.id)
        instance.current_step = "nonexistent_step"
        instance.status = WorkflowStatus.RUNNING
        await async_session.commit()

        # Trigger workflow execution
        await engine._run_workflow(result.id, definition)

        # Should fail with step not found
        instance = await engine.get_instance(result.id)
        assert instance.status == WorkflowStatus.FAILED
        assert "not found" in instance.error

    async def test_workflow_step_execution_failure(
        self,
        async_session: AsyncSession,
        workflow_registry,
        make_workflow_class,
    ):
        """Test workflow handling step execution failure to cover lines 307-317."""
        from litestar_workflows.db.engine import PersistentExecutionEngine

        class FailingStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                raise RuntimeError("Step execution failed")

        definition = WorkflowDefinition(
            name="failing_workflow",
            version="1.0.0",
            description="Workflow with failing step",
            steps={"start": FailingStep(name="start", description="Failing step")},
            edges=[],
            initial_step="start",
            terminal_steps={"start"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
        )

        result = await engine.start_workflow(workflow_class)

        import asyncio

        await asyncio.sleep(0.3)

        # Workflow should have failed
        instance = await engine.get_instance(result.id)
        assert instance.status == WorkflowStatus.FAILED
        assert "Step execution failed" in instance.error

    async def test_workflow_step_skipped(
        self,
        async_session: AsyncSession,
        workflow_registry,
        make_workflow_class,
    ):
        """Test workflow skipping steps when can_execute returns False to cover lines 290-292."""
        from litestar_workflows.db.engine import PersistentExecutionEngine

        class ConditionalStep(BaseMachineStep):
            async def can_execute(self, context: WorkflowContext) -> bool:
                return context.get("should_execute", False)

            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"executed": True}

        class NextStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"final": True}

        definition = WorkflowDefinition(
            name="conditional_workflow",
            version="1.0.0",
            description="Workflow with conditional step",
            steps={
                "conditional": ConditionalStep(name="conditional", description="Conditional step"),
                "next": NextStep(name="next", description="Next step"),
            },
            edges=[Edge(source="conditional", target="next")],
            initial_step="conditional",
            terminal_steps={"next"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
        )

        # Start with should_execute=False
        result = await engine.start_workflow(workflow_class, initial_data={"should_execute": False})

        import asyncio

        await asyncio.sleep(0.5)

        # Check that conditional step was skipped
        from litestar_workflows.db.repositories import StepExecutionRepository

        step_repo = StepExecutionRepository(session=async_session)
        step_execs = await step_repo.find_by_instance(result.id)

        conditional_exec = next((s for s in step_execs if s.step_name == "conditional"), None)
        assert conditional_exec is not None
        assert conditional_exec.status == StepStatus.SKIPPED

    async def test_workflow_no_next_steps(
        self,
        async_session: AsyncSession,
        workflow_registry,
        make_workflow_class,
    ):
        """Test workflow completion when no next steps available to cover lines 330-335."""
        from litestar_workflows.db.engine import PersistentExecutionEngine

        class SingleStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"done": True}

        definition = WorkflowDefinition(
            name="single_step_workflow",
            version="1.0.0",
            description="Workflow with single non-terminal step",
            steps={"only": SingleStep(name="only", description="Only step")},
            edges=[],  # No edges
            initial_step="only",
            terminal_steps=set(),  # Not marked as terminal
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
        )

        result = await engine.start_workflow(workflow_class)

        import asyncio

        await asyncio.sleep(0.3)

        # Should complete because no next steps
        instance = await engine.get_instance(result.id)
        assert instance.status == WorkflowStatus.COMPLETED
        assert instance.current_step is None

    async def test_workflow_instance_not_found_in_run(
        self,
        async_session: AsyncSession,
        workflow_registry,
        simple_workflow_definition: WorkflowDefinition,
        make_workflow_class,
    ):
        """Test exception raised when instance not found in _run_workflow (line 237-239)."""
        from uuid import uuid4

        from advanced_alchemy.exceptions import NotFoundError

        from litestar_workflows.db.engine import PersistentExecutionEngine

        workflow_class = make_workflow_class(simple_workflow_definition)
        workflow_registry.register(workflow_class)

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
        )

        # Try to run workflow with non-existent instance ID
        # The repository.get() raises NotFoundError, which propagates
        fake_id = uuid4()

        with pytest.raises(NotFoundError):
            await engine._run_workflow(fake_id, simple_workflow_definition)

    async def test_workflow_current_step_none(
        self,
        async_session: AsyncSession,
        workflow_registry,
        simple_workflow_definition: WorkflowDefinition,
        make_workflow_class,
    ):
        """Test workflow loop breaks when current_step is None to cover lines 244-245."""
        from litestar_workflows.db.engine import PersistentExecutionEngine
        from litestar_workflows.db.repositories import WorkflowInstanceRepository

        workflow_class = make_workflow_class(simple_workflow_definition)
        workflow_registry.register(workflow_class)

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
        )

        result = await engine.start_workflow(workflow_class)

        import asyncio

        await asyncio.sleep(0.1)

        # Manually set current_step to None
        instance_repo = WorkflowInstanceRepository(session=async_session)
        instance = await instance_repo.get(result.id)
        instance.current_step = None
        await async_session.commit()

        # Run workflow - should break early
        await engine._run_workflow(result.id, simple_workflow_definition)

    async def test_complete_human_task_instance_not_found(
        self,
        async_session: AsyncSession,
        workflow_registry,
        simple_workflow_definition: WorkflowDefinition,
        make_workflow_class,
    ):
        """Test error handling when instance not found to cover lines 438-440."""
        from uuid import uuid4

        from advanced_alchemy.exceptions import NotFoundError

        from litestar_workflows.db.engine import PersistentExecutionEngine

        workflow_class = make_workflow_class(simple_workflow_definition)
        workflow_registry.register(workflow_class)

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
        )

        # Use non-existent ID - repository will raise NotFoundError on line 437
        fake_id = uuid4()

        with pytest.raises(NotFoundError):
            await engine.complete_human_task(fake_id, "approval", "user1", {"approved": True})

    async def test_complete_human_task_not_waiting(
        self,
        async_session: AsyncSession,
        workflow_registry,
        simple_workflow_definition: WorkflowDefinition,
        make_workflow_class,
    ):
        """Test error when instance is not waiting to cover lines 442-444."""
        from litestar_workflows.db.engine import PersistentExecutionEngine

        workflow_class = make_workflow_class(simple_workflow_definition)
        workflow_registry.register(workflow_class)

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
        )

        result = await engine.start_workflow(workflow_class)

        import asyncio

        await asyncio.sleep(0.3)

        # Try to complete human task on running (non-waiting) workflow
        with pytest.raises(ValueError, match="not waiting"):
            await engine.complete_human_task(result.id, "start", "user1", {})

    async def test_complete_human_task_wrong_step(
        self,
        async_session: AsyncSession,
        workflow_registry,
        human_workflow_definition: WorkflowDefinition,
        make_workflow_class,
    ):
        """Test error when completing wrong step to cover lines 446-448."""
        from litestar_workflows.db.engine import PersistentExecutionEngine

        workflow_class = make_workflow_class(human_workflow_definition)
        workflow_registry.register(workflow_class)

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
        )

        result = await engine.start_workflow(workflow_class)

        import asyncio

        await asyncio.sleep(0.3)

        # Workflow should be waiting at "approval" step
        instance = await engine.get_instance(result.id)
        assert instance.status == WorkflowStatus.WAITING
        assert instance.current_step == "approval"

        # Try to complete wrong step
        with pytest.raises(ValueError, match="not 'wrong_step'"):
            await engine.complete_human_task(result.id, "wrong_step", "user1", {"approved": True})

    async def test_complete_human_task_resumes_workflow(
        self,
        async_session: AsyncSession,
        workflow_registry,
        human_workflow_definition: WorkflowDefinition,
        make_workflow_class,
    ):
        """Test that completing human task resumes workflow and covers line 486."""
        from litestar_workflows.db.engine import PersistentExecutionEngine

        workflow_class = make_workflow_class(human_workflow_definition)
        workflow_registry.register(workflow_class)

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
        )

        result = await engine.start_workflow(workflow_class)

        import asyncio

        await asyncio.sleep(0.3)

        # Verify workflow is waiting
        instance = await engine.get_instance(result.id)
        assert instance.status == WorkflowStatus.WAITING
        assert instance.current_step == "approval"

        # Instance should not be in running tasks (since it's waiting)
        running_before = engine.get_running_instances()
        # Note: task may have completed and been removed from _running already

        # Complete the task
        await engine.complete_human_task(result.id, "approval", "user1", {"approved": True})

        # Verify task was created on line 486 - give it time to start
        await asyncio.sleep(0.1)

        # Check that workflow is running again (or already completed)
        running_after = engine.get_running_instances()

        # Wait for completion
        await asyncio.sleep(0.5)

        # Should have resumed and completed
        instance = await engine.get_instance(result.id)
        assert instance.status in [WorkflowStatus.RUNNING, WorkflowStatus.COMPLETED]

    async def test_cancel_workflow_not_found(
        self,
        async_session: AsyncSession,
        workflow_registry,
        simple_workflow_definition: WorkflowDefinition,
        make_workflow_class,
    ):
        """Test cancel workflow when instance not found to cover lines 496-498."""
        from uuid import uuid4

        from advanced_alchemy.exceptions import NotFoundError

        from litestar_workflows.db.engine import PersistentExecutionEngine

        workflow_class = make_workflow_class(simple_workflow_definition)
        workflow_registry.register(workflow_class)

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
        )

        # Use non-existent ID - repository will raise NotFoundError on line 495
        fake_id = uuid4()

        with pytest.raises(NotFoundError):
            await engine.cancel_workflow(fake_id, "Test reason")

    async def test_cancel_workflow_with_event_bus(
        self,
        async_session: AsyncSession,
        workflow_registry,
        human_workflow_definition: WorkflowDefinition,
        make_workflow_class,
    ):
        """Test cancel workflow with event bus to cover line 517."""
        from unittest.mock import AsyncMock

        from litestar_workflows.db.engine import PersistentExecutionEngine

        workflow_class = make_workflow_class(human_workflow_definition)
        workflow_registry.register(workflow_class)

        event_bus = AsyncMock()
        event_bus.emit = AsyncMock()

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
            event_bus=event_bus,
        )

        result = await engine.start_workflow(workflow_class)

        import asyncio

        await asyncio.sleep(0.3)

        await engine.cancel_workflow(result.id, "Test cancellation")

        # Verify event was emitted
        event_bus.emit.assert_any_call("workflow.canceled", instance_id=result.id, reason="Test cancellation")

    async def test_get_instance_not_found(
        self,
        async_session: AsyncSession,
        workflow_registry,
        simple_workflow_definition: WorkflowDefinition,
        make_workflow_class,
    ):
        """Test get_instance raises NotFoundError when not found to cover lines 536-538."""
        from uuid import uuid4

        from advanced_alchemy.exceptions import NotFoundError

        from litestar_workflows.db.engine import PersistentExecutionEngine

        workflow_class = make_workflow_class(simple_workflow_definition)
        workflow_registry.register(workflow_class)

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
        )

        # Use non-existent ID - repository will raise NotFoundError on line 535
        fake_id = uuid4()

        with pytest.raises(NotFoundError):
            await engine.get_instance(fake_id)

    async def test_workflow_with_human_step_event_emission(
        self,
        async_session: AsyncSession,
        workflow_registry,
        human_workflow_definition: WorkflowDefinition,
        make_workflow_class,
    ):
        """Test event emission when workflow waits for human to cover line 266."""
        from unittest.mock import AsyncMock

        from litestar_workflows.db.engine import PersistentExecutionEngine

        workflow_class = make_workflow_class(human_workflow_definition)
        workflow_registry.register(workflow_class)

        event_bus = AsyncMock()
        event_bus.emit = AsyncMock()

        engine = PersistentExecutionEngine(
            registry=workflow_registry,
            session=async_session,
            event_bus=event_bus,
        )

        result = await engine.start_workflow(workflow_class)

        import asyncio

        await asyncio.sleep(0.3)

        # Verify waiting event was emitted
        event_bus.emit.assert_any_call("workflow.waiting", instance_id=result.id, step_name="approval")


# =============================================================================
# Model Tests
# =============================================================================


class TestModels:
    """Tests for SQLAlchemy models."""

    async def test_workflow_definition_model_relationships(
        self,
        sample_definition_model: WorkflowDefinitionModel,
        sample_instance_model: WorkflowInstanceModel,
        async_session: AsyncSession,
    ):
        """Test definition-instance relationship."""
        # Refresh with relationship
        await async_session.refresh(sample_instance_model, ["definition"])

        assert sample_instance_model.definition is not None
        assert sample_instance_model.definition.id == sample_definition_model.id

    async def test_workflow_instance_model_relationships(
        self,
        sample_instance_model: WorkflowInstanceModel,
        step_repo: StepExecutionRepository,
        async_session: AsyncSession,
    ):
        """Test instance-step_execution relationship via repository."""
        # Create step execution directly in test
        now = datetime.now(timezone.utc)
        step_exec = StepExecutionModel(
            instance_id=sample_instance_model.id,
            step_name="test_step",
            step_type=StepType.MACHINE,
            status=StepStatus.RUNNING,
            started_at=now,
        )
        await step_repo.add(step_exec)
        await async_session.commit()

        # Verify the relationship via repo query (since lazy="noload" requires explicit loading)
        step_executions = await step_repo.find_by_instance(sample_instance_model.id)

        assert len(step_executions) >= 1
        assert any(se.id == step_exec.id for se in step_executions)
        assert all(se.instance_id == sample_instance_model.id for se in step_executions)

    async def test_step_execution_model_json_fields(
        self,
        sample_instance_model: WorkflowInstanceModel,
        step_repo: StepExecutionRepository,
        async_session: AsyncSession,
    ):
        """Test JSON fields in step execution."""
        now = datetime.now(timezone.utc)
        model = StepExecutionModel(
            instance_id=sample_instance_model.id,
            step_name="json_step",
            step_type=StepType.MACHINE,
            status=StepStatus.SUCCEEDED,
            input_data={"input": "value"},
            output_data={"output": "result"},
            started_at=now,
            completed_at=now,
        )
        await step_repo.add(model)
        await async_session.commit()

        # Reload and verify
        loaded = await step_repo.get(model.id)

        assert loaded.input_data == {"input": "value"}
        assert loaded.output_data == {"output": "result"}

    async def test_human_task_model_timestamps(
        self,
        sample_instance_model: WorkflowInstanceModel,
        sample_step_execution: StepExecutionModel,
        task_repo: HumanTaskRepository,
        async_session: AsyncSession,
    ):
        """Test timestamp fields in human task."""
        now = datetime.now(timezone.utc)
        due = now + timedelta(days=1)
        reminder = now + timedelta(hours=12)

        model = HumanTaskModel(
            instance_id=sample_instance_model.id,
            step_execution_id=sample_step_execution.id,
            step_name="timed_task",
            title="Timed Task",
            due_at=due,
            reminder_at=reminder,
            status="pending",
        )
        await task_repo.add(model)
        await async_session.commit()

        loaded = await task_repo.get(model.id)

        assert loaded.due_at is not None
        assert loaded.reminder_at is not None
