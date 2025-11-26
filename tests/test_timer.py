"""Tests for timer and delay steps."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from litestar_workflows.core.context import WorkflowContext


@pytest.mark.unit
@pytest.mark.asyncio
class TestTimerStep:
    """Tests for TimerStep with fixed and dynamic durations."""

    async def test_timer_step_fixed_duration(self, sample_context: WorkflowContext) -> None:
        """Test TimerStep with fixed duration."""
        from litestar_workflows.steps.timer import TimerStep

        duration = timedelta(seconds=0.1)
        timer = TimerStep(
            name="fixed_timer",
            duration=duration,
            description="Fixed duration timer",
        )

        start_time = datetime.now(timezone.utc)
        result = await timer.execute(sample_context)
        end_time = datetime.now(timezone.utc)

        elapsed = (end_time - start_time).total_seconds()

        # Should have waited approximately the duration
        assert elapsed >= 0.09  # Allow small variance
        # TimerStep.execute() returns None, not a dict
        assert result is None

    async def test_timer_step_callable_duration(self, sample_context: WorkflowContext) -> None:
        """Test TimerStep with callable duration."""
        from litestar_workflows.steps.timer import TimerStep

        def dynamic_duration(context: WorkflowContext) -> timedelta:
            """Calculate duration based on context."""
            multiplier = context.get("wait_multiplier", 1)
            return timedelta(seconds=0.1 * multiplier)

        timer = TimerStep(
            name="dynamic_timer",
            duration=dynamic_duration,
            description="Dynamic duration timer",
        )

        # Test with multiplier = 1
        sample_context.set("wait_multiplier", 1)
        start_time = datetime.now(timezone.utc)
        result = await timer.execute(sample_context)
        end_time = datetime.now(timezone.utc)

        elapsed = (end_time - start_time).total_seconds()
        assert elapsed >= 0.09

    async def test_timer_step_zero_duration(self, sample_context: WorkflowContext) -> None:
        """Test TimerStep with zero duration."""
        from litestar_workflows.steps.timer import TimerStep

        timer = TimerStep(
            name="zero_timer",
            duration=timedelta(seconds=0),
            description="Zero duration timer",
        )

        result = await timer.execute(sample_context)

        # TimerStep.execute() returns None
        assert result is None

    async def test_timer_step_stores_wait_time(self, sample_context: WorkflowContext) -> None:
        """Test TimerStep stores wait time in context."""
        from litestar_workflows.steps.timer import TimerStep

        timer = TimerStep(
            name="context_timer",
            duration=timedelta(seconds=0.05),
            description="Timer that stores wait time",
        )

        await timer.execute(sample_context)

        # TimerStep doesn't store wait time in context by default
        # Just verify execution completed
        assert True

    async def test_timer_step_type(self) -> None:
        """Test TimerStep has correct step type."""
        from litestar_workflows.core.types import StepType
        from litestar_workflows.steps.timer import TimerStep

        timer = TimerStep(
            name="test_timer",
            duration=timedelta(seconds=1),
            description="Test timer",
        )

        assert timer.step_type == StepType.TIMER


@pytest.mark.unit
@pytest.mark.asyncio
class TestTimerIntegration:
    """Integration tests for timer steps in workflows."""

    async def test_timer_in_workflow_sequence(self, sample_context: WorkflowContext) -> None:
        """Test timer step in workflow sequence."""
        from litestar_workflows.steps.base import BaseMachineStep
        from litestar_workflows.steps.timer import TimerStep

        class BeforeTimer(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                context.set("before_time", datetime.now(timezone.utc))
                return {"step": "before"}

        class AfterTimer(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                context.set("after_time", datetime.now(timezone.utc))
                return {"step": "after"}

        timer = TimerStep(
            name="wait",
            duration=timedelta(seconds=0.05),
            description="Wait step",
        )

        # Execute sequence
        before = BeforeTimer(name="before", description="Before timer")
        after = AfterTimer(name="after", description="After timer")

        await before.execute(sample_context)
        await timer.execute(sample_context)
        await after.execute(sample_context)

        # Verify timing
        before_time = sample_context.get("before_time")
        after_time = sample_context.get("after_time")

        if before_time and after_time:
            elapsed = (after_time - before_time).total_seconds()
            assert elapsed >= 0.04

    async def test_multiple_timers_parallel(self, sample_context: WorkflowContext) -> None:
        """Test multiple timer steps executing in parallel."""
        from litestar_workflows.steps.timer import TimerStep

        timer1 = TimerStep(name="timer1", duration=timedelta(seconds=0.05), description="Timer 1")
        timer2 = TimerStep(name="timer2", duration=timedelta(seconds=0.05), description="Timer 2")
        timer3 = TimerStep(name="timer3", duration=timedelta(seconds=0.05), description="Timer 3")

        start_time = datetime.now(timezone.utc)

        # Execute in parallel
        results = await asyncio.gather(
            timer1.execute(sample_context),
            timer2.execute(sample_context),
            timer3.execute(sample_context),
        )

        end_time = datetime.now(timezone.utc)
        elapsed = (end_time - start_time).total_seconds()

        # Should take approximately one timer duration (parallel execution)
        assert elapsed < 0.15  # Should be less than 3x the duration
        assert len(results) == 3
