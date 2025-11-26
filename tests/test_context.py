"""Tests for WorkflowContext."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from litestar_workflows.core.context import WorkflowContext


@pytest.mark.unit
class TestWorkflowContext:
    """Tests for WorkflowContext class."""

    def test_context_creation(self) -> None:
        """Test creating a WorkflowContext instance."""
        from litestar_workflows.core.context import WorkflowContext

        workflow_id = uuid4()
        instance_id = uuid4()
        started_at = datetime.now(timezone.utc)

        context = WorkflowContext(
            workflow_id=workflow_id,
            instance_id=instance_id,
            data={"key": "value"},
            metadata={"created_by": "test_user"},
            current_step="initial",
            step_history=[],
            started_at=started_at,
        )

        assert context.workflow_id == workflow_id
        assert context.instance_id == instance_id
        assert context.data == {"key": "value"}
        assert context.metadata == {"created_by": "test_user"}
        assert context.current_step == "initial"
        assert context.step_history == []
        assert context.started_at == started_at
        assert context.user_id is None
        assert context.tenant_id is None

    def test_context_with_user_info(self) -> None:
        """Test WorkflowContext with user and tenant information."""
        from litestar_workflows.core.context import WorkflowContext

        context = WorkflowContext(
            workflow_id=uuid4(),
            instance_id=uuid4(),
            data={},
            metadata={},
            current_step="initial",
            step_history=[],
            started_at=datetime.now(timezone.utc),
            user_id="user123",
            tenant_id="tenant456",
        )

        assert context.user_id == "user123"
        assert context.tenant_id == "tenant456"

    def test_get_method(self, sample_context: WorkflowContext) -> None:
        """Test getting values from context data."""
        assert sample_context.get("test_key") == "test_value"
        assert sample_context.get("count") == 0
        assert sample_context.get("nonexistent") is None

    def test_get_method_with_default(self, sample_context: WorkflowContext) -> None:
        """Test get method with custom default value."""
        assert sample_context.get("nonexistent", "default") == "default"
        assert sample_context.get("test_key", "default") == "test_value"

    def test_set_method(self, sample_context: WorkflowContext) -> None:
        """Test setting values in context data."""
        sample_context.set("new_key", "new_value")
        assert sample_context.get("new_key") == "new_value"

        # Update existing value
        sample_context.set("count", 10)
        assert sample_context.get("count") == 10

    def test_set_overwrites_existing(self, sample_context: WorkflowContext) -> None:
        """Test that set method overwrites existing values."""
        original = sample_context.get("test_key")
        sample_context.set("test_key", "updated_value")
        assert sample_context.get("test_key") == "updated_value"
        assert sample_context.get("test_key") != original

    def test_with_step_creates_child_context(self, sample_context: WorkflowContext) -> None:
        """Test with_step creates a new context for step execution."""
        child_context = sample_context.with_step("next_step")

        # Child should have updated current_step
        assert child_context.current_step == "next_step"

        # Original should be unchanged
        assert sample_context.current_step == "initial_step"

        # Child should share same IDs
        assert child_context.workflow_id == sample_context.workflow_id
        assert child_context.instance_id == sample_context.instance_id

    def test_with_step_preserves_data(self, sample_context: WorkflowContext) -> None:
        """Test with_step preserves data and metadata."""
        child_context = sample_context.with_step("next_step")

        # Data should be preserved (or copied depending on implementation)
        assert child_context.get("test_key") == sample_context.get("test_key")
        assert child_context.get("count") == sample_context.get("count")

    def test_step_history_tracking(self) -> None:
        """Test that step_history is properly tracked."""
        from litestar_workflows.core.context import WorkflowContext
        from litestar_workflows.core.types import StepExecution, StepStatus

        now = datetime.now(timezone.utc)
        context = WorkflowContext(
            workflow_id=uuid4(),
            instance_id=uuid4(),
            data={},
            metadata={},
            current_step="step1",
            step_history=[],
            started_at=now,
        )

        # Add step execution to history
        execution = StepExecution(
            step_name="step1",
            status=str(StepStatus.SUCCEEDED),
            started_at=now,
            completed_at=now,
            result={"success": True},
        )

        context.step_history.append(execution)

        assert len(context.step_history) == 1
        assert context.step_history[0].step_name == "step1"
        assert context.step_history[0].status == str(StepStatus.SUCCEEDED)

    def test_metadata_immutability_pattern(self, sample_context: WorkflowContext) -> None:
        """Test that metadata follows immutability pattern."""
        # Metadata should be readable
        assert sample_context.metadata["created_by"] == "test_user"
        assert sample_context.metadata["environment"] == "test"

        # Attempting to modify should work (dict is mutable)
        # but best practice is to treat as immutable
        original_metadata = sample_context.metadata.copy()
        sample_context.metadata["new_field"] = "value"

        # Verify modification worked (implementation detail)
        assert "new_field" in sample_context.metadata

    def test_context_data_is_mutable(self, sample_context: WorkflowContext) -> None:
        """Test that context data is mutable and can be updated."""
        sample_context.data["dynamic_field"] = "dynamic_value"
        assert sample_context.get("dynamic_field") == "dynamic_value"

        # Update nested structures
        sample_context.set("nested", {"inner": "value"})
        assert sample_context.get("nested") == {"inner": "value"}

    def test_context_preserves_started_at(self, sample_context: WorkflowContext) -> None:
        """Test that started_at timestamp is preserved."""
        original_time = sample_context.started_at
        child_context = sample_context.with_step("next_step")

        assert child_context.started_at == original_time

    def test_multiple_step_transitions(self, sample_context: WorkflowContext) -> None:
        """Test multiple step transitions maintain context."""
        step1_context = sample_context.with_step("step1")
        step1_context.set("step1_data", "value1")

        step2_context = step1_context.with_step("step2")
        step2_context.set("step2_data", "value2")

        # Each context should have its current_step
        assert sample_context.current_step == "initial_step"
        assert step1_context.current_step == "step1"
        assert step2_context.current_step == "step2"

        # Later contexts should have data from earlier steps
        assert step2_context.get("step1_data") == "value1"
        assert step2_context.get("step2_data") == "value2"
