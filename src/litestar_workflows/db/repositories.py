"""Repository implementations for workflow persistence.

This module provides async repositories for CRUD operations on workflow
models using advanced-alchemy's repository pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from advanced_alchemy.filters import LimitOffset, OrderBy
from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from sqlalchemy import and_, or_, select

from litestar_workflows.core.types import StepStatus, WorkflowStatus
from litestar_workflows.db.models import (
    HumanTaskModel,
    StepExecutionModel,
    WorkflowDefinitionModel,
    WorkflowInstanceModel,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "HumanTaskRepository",
    "StepExecutionRepository",
    "WorkflowDefinitionRepository",
    "WorkflowInstanceRepository",
]


class WorkflowDefinitionRepository(SQLAlchemyAsyncRepository[WorkflowDefinitionModel]):
    """Repository for workflow definition CRUD operations.

    Provides methods for managing workflow definitions including
    version management and activation status.
    """

    model_type = WorkflowDefinitionModel

    async def get_by_name(
        self,
        name: str,
        version: str | None = None,
        *,
        active_only: bool = True,
    ) -> WorkflowDefinitionModel | None:
        """Get a workflow definition by name and optional version.

        Args:
            name: The workflow name.
            version: Optional specific version. If None, returns the latest active version.
            active_only: If True, only return active definitions.

        Returns:
            The workflow definition or None if not found.
        """
        conditions = [WorkflowDefinitionModel.name == name]

        if version:
            conditions.append(WorkflowDefinitionModel.version == version)

        if active_only:
            conditions.append(WorkflowDefinitionModel.is_active == True)  # noqa: E712

        stmt = (
            select(WorkflowDefinitionModel)
            .where(and_(*conditions))
            .order_by(WorkflowDefinitionModel.created_at.desc())
            .limit(1)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_version(self, name: str) -> WorkflowDefinitionModel | None:
        """Get the latest active version of a workflow definition.

        Args:
            name: The workflow name.

        Returns:
            The latest active workflow definition or None.
        """
        return await self.get_by_name(name, active_only=True)

    async def list_active(self) -> Sequence[WorkflowDefinitionModel]:
        """List all active workflow definitions.

        Returns:
            List of active workflow definitions.
        """
        stmt = (
            select(WorkflowDefinitionModel)
            .where(WorkflowDefinitionModel.is_active == True)  # noqa: E712
            .order_by(WorkflowDefinitionModel.name, WorkflowDefinitionModel.version.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def deactivate_version(self, name: str, version: str) -> bool:
        """Deactivate a specific workflow version.

        Args:
            name: The workflow name.
            version: The version to deactivate.

        Returns:
            True if a definition was deactivated.
        """
        definition = await self.get_by_name(name, version, active_only=False)
        if definition:
            definition.is_active = False
            await self.session.flush()
            return True
        return False


class WorkflowInstanceRepository(SQLAlchemyAsyncRepository[WorkflowInstanceModel]):
    """Repository for workflow instance CRUD operations.

    Provides methods for querying and managing workflow instances
    including filtering by status, user, and workflow name.
    """

    model_type = WorkflowInstanceModel

    async def find_by_workflow(
        self,
        workflow_name: str,
        status: WorkflowStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[Sequence[WorkflowInstanceModel], int]:
        """Find instances by workflow name with optional status filter.

        Args:
            workflow_name: The workflow name to filter by.
            status: Optional status filter.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            Tuple of (instances, total_count).
        """
        conditions = [WorkflowInstanceModel.workflow_name == workflow_name]

        if status:
            conditions.append(WorkflowInstanceModel.status == status)

        return await self.list_and_count(
            *conditions,
            LimitOffset(limit=limit, offset=offset),
            OrderBy(field_name="created_at", sort_order="desc"),
        )

    async def find_by_user(
        self,
        user_id: str,
        status: WorkflowStatus | None = None,
    ) -> Sequence[WorkflowInstanceModel]:
        """Find instances created by a specific user.

        Args:
            user_id: The user ID to filter by.
            status: Optional status filter.

        Returns:
            List of workflow instances.
        """
        conditions = [WorkflowInstanceModel.created_by == user_id]

        if status:
            conditions.append(WorkflowInstanceModel.status == status)

        stmt = select(WorkflowInstanceModel).where(and_(*conditions)).order_by(WorkflowInstanceModel.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_by_tenant(
        self,
        tenant_id: str,
        status: WorkflowStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[Sequence[WorkflowInstanceModel], int]:
        """Find instances by tenant ID.

        Args:
            tenant_id: The tenant ID to filter by.
            status: Optional status filter.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            Tuple of (instances, total_count).
        """
        conditions = [WorkflowInstanceModel.tenant_id == tenant_id]

        if status:
            conditions.append(WorkflowInstanceModel.status == status)

        return await self.list_and_count(
            *conditions,
            LimitOffset(limit=limit, offset=offset),
            OrderBy(field_name="created_at", sort_order="desc"),
        )

    async def find_running(self) -> Sequence[WorkflowInstanceModel]:
        """Find all running or waiting workflow instances.

        Returns:
            List of active workflow instances.
        """
        stmt = (
            select(WorkflowInstanceModel)
            .where(
                WorkflowInstanceModel.status.in_(
                    [
                        WorkflowStatus.RUNNING,
                        WorkflowStatus.WAITING,
                    ]
                )
            )
            .order_by(WorkflowInstanceModel.started_at)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_status(
        self,
        instance_id: UUID,
        status: WorkflowStatus,
        *,
        current_step: str | None = None,
        error: str | None = None,
    ) -> WorkflowInstanceModel | None:
        """Update the status of a workflow instance.

        Args:
            instance_id: The instance ID.
            status: The new status.
            current_step: Optional current step name.
            error: Optional error message.

        Returns:
            The updated instance or None if not found.
        """
        instance = await self.get(instance_id)
        if instance:
            instance.status = status
            if current_step is not None:
                instance.current_step = current_step
            if error is not None:
                instance.error = error
            await self.session.flush()
        return instance


class StepExecutionRepository(SQLAlchemyAsyncRepository[StepExecutionModel]):
    """Repository for step execution record CRUD operations."""

    model_type = StepExecutionModel

    async def find_by_instance(
        self,
        instance_id: UUID,
    ) -> Sequence[StepExecutionModel]:
        """Find all step executions for an instance.

        Args:
            instance_id: The workflow instance ID.

        Returns:
            List of step executions ordered by start time.
        """
        stmt = (
            select(StepExecutionModel)
            .where(StepExecutionModel.instance_id == instance_id)
            .order_by(StepExecutionModel.started_at)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_by_step_name(
        self,
        instance_id: UUID,
        step_name: str,
    ) -> StepExecutionModel | None:
        """Find the execution record for a specific step.

        Args:
            instance_id: The workflow instance ID.
            step_name: The step name.

        Returns:
            The step execution or None.
        """
        stmt = (
            select(StepExecutionModel)
            .where(
                and_(
                    StepExecutionModel.instance_id == instance_id,
                    StepExecutionModel.step_name == step_name,
                )
            )
            .order_by(StepExecutionModel.started_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_failed(
        self,
        instance_id: UUID | None = None,
    ) -> Sequence[StepExecutionModel]:
        """Find failed step executions.

        Args:
            instance_id: Optional instance ID filter.

        Returns:
            List of failed step executions.
        """
        conditions = [StepExecutionModel.status == StepStatus.FAILED]

        if instance_id:
            conditions.append(StepExecutionModel.instance_id == instance_id)

        stmt = select(StepExecutionModel).where(and_(*conditions)).order_by(StepExecutionModel.completed_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()


class HumanTaskRepository(SQLAlchemyAsyncRepository[HumanTaskModel]):
    """Repository for human task CRUD operations.

    Provides methods for querying pending human tasks by assignee,
    group, and due date.
    """

    model_type = HumanTaskModel

    async def find_pending(
        self,
        assignee_id: str | None = None,
        assignee_group: str | None = None,
    ) -> Sequence[HumanTaskModel]:
        """Find pending human tasks.

        Args:
            assignee_id: Optional assignee ID filter.
            assignee_group: Optional group filter.

        Returns:
            List of pending human tasks.
        """
        conditions = [HumanTaskModel.status == "pending"]

        if assignee_id:
            # Include tasks assigned to user or unassigned
            conditions.append(
                or_(
                    HumanTaskModel.assignee_id == assignee_id,
                    HumanTaskModel.assignee_id.is_(None),
                )
            )

        if assignee_group:
            conditions.append(
                or_(
                    HumanTaskModel.assignee_group == assignee_group,
                    HumanTaskModel.assignee_group.is_(None),
                )
            )

        stmt = (
            select(HumanTaskModel)
            .where(and_(*conditions))
            .order_by(HumanTaskModel.due_at.asc().nullslast(), HumanTaskModel.created_at)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_by_instance(
        self,
        instance_id: UUID,
    ) -> Sequence[HumanTaskModel]:
        """Find all human tasks for an instance.

        Args:
            instance_id: The workflow instance ID.

        Returns:
            List of human tasks.
        """
        stmt = (
            select(HumanTaskModel).where(HumanTaskModel.instance_id == instance_id).order_by(HumanTaskModel.created_at)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_overdue(self) -> Sequence[HumanTaskModel]:
        """Find overdue pending human tasks.

        Returns:
            List of overdue human tasks.
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        stmt = (
            select(HumanTaskModel)
            .where(
                and_(
                    HumanTaskModel.status == "pending",
                    HumanTaskModel.due_at.isnot(None),
                    HumanTaskModel.due_at < now,
                )
            )
            .order_by(HumanTaskModel.due_at)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def complete_task(
        self,
        task_id: UUID,
        completed_by: str,
    ) -> HumanTaskModel | None:
        """Mark a human task as completed.

        Args:
            task_id: The task ID.
            completed_by: User ID who completed the task.

        Returns:
            The updated task or None if not found.
        """
        from datetime import datetime, timezone

        task = await self.get(task_id)
        if task and task.status == "pending":
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)
            task.completed_by = completed_by
            await self.session.flush()
        return task

    async def cancel_task(self, task_id: UUID) -> HumanTaskModel | None:
        """Cancel a pending human task.

        Args:
            task_id: The task ID.

        Returns:
            The updated task or None if not found.
        """
        task = await self.get(task_id)
        if task and task.status == "pending":
            task.status = "canceled"
            await self.session.flush()
        return task
