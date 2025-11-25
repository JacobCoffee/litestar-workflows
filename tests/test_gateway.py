"""Tests for gateway steps (decision and branching)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from litestar_workflows.core.context import WorkflowContext


@pytest.mark.unit
@pytest.mark.asyncio
class TestExclusiveGateway:
    """Tests for ExclusiveGateway (XOR) routing."""

    async def test_exclusive_gateway_single_path(self, sample_context: WorkflowContext) -> None:
        """Test ExclusiveGateway selects single path."""
        from litestar_workflows.steps.gateway import ExclusiveGateway

        def condition(context: WorkflowContext) -> str:
            return "path_a" if context.get("value", 0) > 50 else "path_b"

        gateway = ExclusiveGateway(
            name="decision_gateway",
            condition=condition,
            description="Decision point",
        )

        # Test path_a selected
        sample_context.set("value", 75)
        result = await gateway.execute(sample_context)

        assert result == "path_a"

        # Test path_b selected
        sample_context.set("value", 25)
        result = await gateway.execute(sample_context)

        assert result == "path_b"

    async def test_exclusive_gateway_multiple_paths(self, sample_context: WorkflowContext) -> None:
        """Test ExclusiveGateway with multiple possible paths."""
        from litestar_workflows.steps.gateway import ExclusiveGateway

        def multi_condition(context: WorkflowContext) -> str:
            status = context.get("status", "pending")
            return {
                "approved": "approved_path",
                "rejected": "rejected_path",
                "pending": "review_path",
            }.get(status, "default_path")

        gateway = ExclusiveGateway(
            name="multi_gateway",
            condition=multi_condition,
            description="Multi-path gateway",
        )

        # Test each path
        for status, expected_path in [
            ("approved", "approved_path"),
            ("rejected", "rejected_path"),
            ("pending", "review_path"),
        ]:
            sample_context.set("status", status)
            result = await gateway.execute(sample_context)
            assert result == expected_path

    async def test_exclusive_gateway_conditional_expression(self, sample_context: WorkflowContext) -> None:
        """Test ExclusiveGateway with expression-based condition."""
        from litestar_workflows.steps.gateway import ExclusiveGateway

        def expression_condition(context: WorkflowContext) -> str:
            amount = context.get("amount", 0)
            if amount < 100:
                return "small"
            if amount < 1000:
                return "medium"
            return "large"

        gateway = ExclusiveGateway(
            name="amount_gateway",
            condition=expression_condition,
            description="Amount-based routing",
        )

        test_cases = [(50, "small"), (500, "medium"), (5000, "large")]

        for amount, expected_path in test_cases:
            sample_context.set("amount", amount)
            result = await gateway.execute(sample_context)
            assert result == expected_path

    async def test_exclusive_gateway_default_path(self, sample_context: WorkflowContext) -> None:
        """Test ExclusiveGateway with default/fallback path."""
        from litestar_workflows.steps.gateway import ExclusiveGateway

        def condition_with_default(context: WorkflowContext) -> str:
            value = context.get("category")
            if value in ["A", "B", "C"]:
                return value
            return "default"

        gateway = ExclusiveGateway(
            name="category_gateway",
            condition=condition_with_default,
            description="Category routing with default",
        )

        # Test known categories
        sample_context.set("category", "A")
        result = await gateway.execute(sample_context)
        assert result == "A"

        # Test unknown category
        sample_context.set("category", "UNKNOWN")
        result = await gateway.execute(sample_context)
        assert result == "default"


@pytest.mark.unit
@pytest.mark.asyncio
class TestParallelGateway:
    """Tests for ParallelGateway (AND) branching."""

    async def test_parallel_gateway_all_branches(self, sample_context: WorkflowContext) -> None:
        """Test ParallelGateway activates all branches."""
        from litestar_workflows.steps.gateway import ParallelGateway

        gateway = ParallelGateway(
            name="parallel_gateway",
            branches=["branch_a", "branch_b", "branch_c"],
            description="Parallel execution gateway",
        )

        result = await gateway.execute(sample_context)

        assert isinstance(result, list)
        assert set(result) == {"branch_a", "branch_b", "branch_c"}

    async def test_parallel_gateway_two_branches(self, sample_context: WorkflowContext) -> None:
        """Test ParallelGateway with two parallel branches."""
        from litestar_workflows.steps.gateway import ParallelGateway

        gateway = ParallelGateway(
            name="dual_gateway",
            branches=["process_a", "process_b"],
            description="Dual parallel branches",
        )

        result = await gateway.execute(sample_context)

        assert len(result) == 2
        assert "process_a" in result
        assert "process_b" in result

    async def test_parallel_gateway_with_conditions(self, sample_context: WorkflowContext) -> None:
        """Test ParallelGateway with conditional branch activation."""
        from litestar_workflows.steps.gateway import ParallelGateway

        # ParallelGateway doesn't support condition parameter in the actual API
        # It returns all branches unconditionally
        gateway = ParallelGateway(
            name="notification_gateway",
            branches=["email_branch", "sms_branch", "logging_branch"],
            description="Notification gateway",
        )

        result = await gateway.execute(sample_context)

        # All branches are returned
        assert len(result) == 3
        assert "email_branch" in result
        assert "sms_branch" in result
        assert "logging_branch" in result

    async def test_parallel_gateway_synchronization(self, sample_context: WorkflowContext) -> None:
        """Test ParallelGateway returns all branches."""
        from litestar_workflows.steps.gateway import ParallelGateway

        gateway = ParallelGateway(
            name="sync_gateway",
            branches=["branch_1", "branch_2", "branch_3"],
            description="Synchronization point",
        )

        result = await gateway.execute(sample_context)

        # All branches should be returned
        assert len(result) == 3
        assert set(result) == {"branch_1", "branch_2", "branch_3"}


@pytest.mark.unit
@pytest.mark.asyncio
class TestGatewayIntegration:
    """Integration tests for gateway workflows."""

    async def test_gateway_workflow_pattern(self, sample_context: WorkflowContext) -> None:
        """Test common gateway workflow pattern: fork-process-join."""
        from litestar_workflows.steps.gateway import ExclusiveGateway, ParallelGateway

        # Fork: Parallel gateway creates branches
        fork_gateway = ParallelGateway(
            name="fork",
            branches=["process_1", "process_2"],
            description="Fork into parallel processing",
        )

        fork_result = await fork_gateway.execute(sample_context)
        assert len(fork_result) == 2

        # Join: Exclusive gateway selects final path
        def join_condition(context: WorkflowContext) -> str:
            return "complete" if context.get("all_processed") else "retry"

        join_gateway = ExclusiveGateway(
            name="join",
            condition=join_condition,
            description="Join and decide",
        )

        sample_context.set("all_processed", True)
        join_result = await join_gateway.execute(sample_context)
        assert join_result == "complete"

    async def test_nested_gateway_pattern(self, sample_context: WorkflowContext) -> None:
        """Test nested gateway pattern (gateway within branches)."""
        from litestar_workflows.steps.gateway import ExclusiveGateway

        # First level gateway
        def level1_condition(context: WorkflowContext) -> str:
            return "premium" if context.get("is_premium") else "standard"

        level1_gateway = ExclusiveGateway(
            name="level1",
            condition=level1_condition,
            description="First level decision",
        )

        # Second level gateway (inside premium path)
        def level2_condition(context: WorkflowContext) -> str:
            return "vip" if context.get("is_vip") else "regular"

        level2_gateway = ExclusiveGateway(
            name="level2",
            condition=level2_condition,
            description="Second level decision",
        )

        # Test nested execution
        sample_context.set("is_premium", True)
        result1 = await level1_gateway.execute(sample_context)
        assert result1 == "premium"

        # If premium, check VIP status
        if result1 == "premium":
            sample_context.set("is_vip", True)
            result2 = await level2_gateway.execute(sample_context)
            assert result2 == "vip"
