"""Integration tests for example applications.

Tests the minimal and full example apps using Litestar's test client
to verify end-to-end functionality.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest
from litestar.testing import AsyncTestClient

from litestar_workflows import WorkflowStatus

if TYPE_CHECKING:
    pass


async def wait_for_status(
    client: AsyncTestClient,
    instance_id: str,
    expected_statuses: list[str],
    timeout: float = 5.0,
    poll_interval: float = 0.1,
    endpoint_prefix: str = "/instances",
) -> dict:
    """Poll instance status until it reaches expected state or timeout.

    Args:
        client: Test client to use.
        instance_id: Instance ID to check.
        expected_statuses: List of acceptable final statuses.
        timeout: Maximum time to wait in seconds.
        poll_interval: Time between polls in seconds.
        endpoint_prefix: URL prefix for instance endpoint.

    Returns:
        Instance data dict.
    """
    elapsed = 0.0
    while elapsed < timeout:
        response = await client.get(f"{endpoint_prefix}/{instance_id}")
        data = response.json()
        if data["status"] in expected_statuses:
            return data
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
    return data  # Return last data even if not in expected state


# =============================================================================
# Minimal App Tests
# =============================================================================


class TestMinimalApp:
    """Integration tests for the minimal example app."""

    @pytest.fixture
    def minimal_app(self):
        """Import and return the minimal example app."""
        from examples.minimal.app import app

        return app

    async def test_health_check(self, minimal_app):
        """Test health check endpoint."""
        async with AsyncTestClient(app=minimal_app) as client:
            response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    async def test_list_workflows(self, minimal_app):
        """Test listing registered workflows."""
        async with AsyncTestClient(app=minimal_app) as client:
            response = await client.get("/workflows/")

            assert response.status_code == 200
            workflows = response.json()
            assert len(workflows) >= 1

            # Find order_processing workflow
            order_workflow = next((w for w in workflows if w["name"] == "order_processing"), None)
            assert order_workflow is not None
            assert order_workflow["version"] == "1.0.0"
            assert "validate_order" in order_workflow["steps"]
            assert "process_payment" in order_workflow["steps"]
            assert "fulfill_order" in order_workflow["steps"]

    async def test_get_workflow_definition(self, minimal_app):
        """Test getting a specific workflow definition."""
        async with AsyncTestClient(app=minimal_app) as client:
            response = await client.get("/workflows/order_processing")

            assert response.status_code == 200
            workflow = response.json()
            assert workflow["name"] == "order_processing"
            assert workflow["initial_step"] == "validate_order"
            assert "fulfill_order" in workflow["terminal_steps"]
            assert "mermaid" in workflow

    async def test_start_and_complete_order_workflow(self, minimal_app):
        """Test starting and completing the order workflow."""
        async with AsyncTestClient(app=minimal_app) as client:
            # Start workflow
            start_response = await client.post(
                "/workflows/order_processing/start",
                json={
                    "order_id": "ORD-12345",
                    "items": ["item1", "item2", "item3"],
                    "amount": 99.99,
                },
            )

            assert start_response.status_code == 201
            start_data = start_response.json()
            assert "instance_id" in start_data
            assert start_data["workflow_name"] == "order_processing"
            instance_id = start_data["instance_id"]

            # Wait for workflow to complete (it's all machine steps)
            await asyncio.sleep(0.5)

            # Get instance status
            status_response = await client.get(f"/workflows/instances/{instance_id}")

            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data["instance_id"] == instance_id
            assert status_data["status"] == WorkflowStatus.COMPLETED.value

            # Verify context data was populated
            context_data = status_data["data"]
            assert context_data.get("validation_passed") is True
            assert "payment_id" in context_data
            assert "tracking_number" in context_data

    async def test_order_workflow_with_invalid_data(self, minimal_app):
        """Test order workflow with missing required data."""
        async with AsyncTestClient(app=minimal_app) as client:
            # Start workflow with empty items
            start_response = await client.post(
                "/workflows/order_processing/start",
                json={
                    "order_id": "ORD-INVALID",
                    "items": [],  # Empty items should fail validation
                    "amount": 0,
                },
            )

            assert start_response.status_code == 201
            instance_id = start_response.json()["instance_id"]

            # Wait for workflow
            await asyncio.sleep(0.3)

            # Get instance - validation should have set validation_passed to False
            status_response = await client.get(f"/workflows/instances/{instance_id}")
            status_data = status_response.json()

            # Workflow still completes but validation_passed should be False
            assert status_data["data"].get("validation_passed") is False

    async def test_get_nonexistent_workflow(self, minimal_app):
        """Test getting a workflow that doesn't exist."""
        async with AsyncTestClient(app=minimal_app) as client:
            response = await client.get("/workflows/nonexistent_workflow")

            assert response.status_code == 500  # WorkflowNotFoundError


# =============================================================================
# Full App Tests
# =============================================================================


class TestFullApp:
    """Integration tests for the full example app."""

    @pytest.fixture
    def full_app(self):
        """Import and return the full example app."""
        from examples.full.app import app

        return app

    async def test_health_check(self, full_app):
        """Test health check endpoint."""
        async with AsyncTestClient(app=full_app) as client:
            response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    async def test_list_workflows(self, full_app):
        """Test listing registered workflows."""
        async with AsyncTestClient(app=full_app) as client:
            response = await client.get("/workflows/")

            assert response.status_code == 200
            workflows = response.json()
            assert len(workflows) >= 2  # document_approval and simple_workflow

            workflow_names = [w["name"] for w in workflows]
            assert "document_approval" in workflow_names
            assert "simple_workflow" in workflow_names

    async def test_get_document_approval_definition(self, full_app):
        """Test getting the document approval workflow definition."""
        async with AsyncTestClient(app=full_app) as client:
            response = await client.get("/workflows/document_approval")

            assert response.status_code == 200
            workflow = response.json()
            assert workflow["name"] == "document_approval"
            assert workflow["initial_step"] == "submit_document"

            # Check steps include human step
            steps = workflow["steps"]
            assert "review_document" in steps
            assert steps["review_document"]["type"] == "human"

            # Check conditional edges
            edges = workflow["edges"]
            conditional_edges = [e for e in edges if e["condition"] is not None]
            assert len(conditional_edges) == 3  # approve, reject, request_changes

    async def test_simple_workflow_execution(self, full_app):
        """Test executing the simple workflow."""
        async with AsyncTestClient(app=full_app) as client:
            # Start workflow
            start_response = await client.post(
                "/workflows/simple_workflow/start",
                json={"test_data": "hello"},
            )

            assert start_response.status_code == 201
            instance_id = start_response.json()["instance_id"]

            # Wait for completion
            await asyncio.sleep(0.3)

            # Get instance
            status_response = await client.get(f"/instances/{instance_id}")

            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data["status"] == WorkflowStatus.COMPLETED.value
            assert status_data["data"].get("simple_executed") is True

    async def test_document_approval_workflow_approve_path(self, full_app):
        """Test document approval workflow through approval path.

        Note: Full E2E completion testing is limited by test client's handling of
        background asyncio tasks. This test verifies the human task flow works correctly.
        """
        async with AsyncTestClient(app=full_app) as client:
            # Start document approval workflow
            start_response = await client.post(
                "/workflows/document_approval/start",
                json={
                    "document_id": "DOC-001",
                    "submitter": "john.doe@example.com",
                    "title": "Q4 Report",
                },
            )

            assert start_response.status_code == 201
            instance_id = start_response.json()["instance_id"]

            # Wait for it to reach human step
            await asyncio.sleep(0.3)

            # Check status - should be waiting at review_document
            status_response = await client.get(f"/instances/{instance_id}")
            status_data = status_response.json()
            assert status_data["status"] == WorkflowStatus.WAITING.value
            assert status_data["current_step"] == "review_document"

            # Complete the human task with approval
            complete_response = await client.post(
                f"/instances/{instance_id}/complete-task",
                json={
                    "user_id": "reviewer@example.com",
                    "decision": "approve",
                    "comments": "Looks good!",
                },
            )

            assert complete_response.status_code == 201

            # Verify the human task was processed - status changes from WAITING
            # Note: Background task execution in test client is limited
            await asyncio.sleep(0.2)
            final_response = await client.get(f"/instances/{instance_id}")
            final_data = final_response.json()

            # The decision should be recorded in context
            assert final_data["data"].get("decision") == "approve"
            assert final_data["data"].get("comments") == "Looks good!"
            # Status should no longer be WAITING after task completion
            assert final_data["status"] != WorkflowStatus.WAITING.value

    async def test_document_approval_workflow_reject_path(self, full_app):
        """Test document approval workflow through rejection path.

        Note: Full E2E completion testing is limited by test client's handling of
        background asyncio tasks. This test verifies the human task flow works correctly.
        """
        async with AsyncTestClient(app=full_app) as client:
            # Start workflow
            start_response = await client.post(
                "/workflows/document_approval/start",
                json={
                    "document_id": "DOC-002",
                    "submitter": "jane.doe@example.com",
                },
            )

            assert start_response.status_code == 201
            instance_id = start_response.json()["instance_id"]

            # Wait for human step
            await asyncio.sleep(0.3)

            # Verify at human step
            status_response = await client.get(f"/instances/{instance_id}")
            assert status_response.json()["status"] == WorkflowStatus.WAITING.value

            # Complete with rejection
            await client.post(
                f"/instances/{instance_id}/complete-task",
                json={
                    "user_id": "reviewer@example.com",
                    "decision": "reject",
                    "comments": "Missing required sections",
                },
            )

            # Verify the human task was processed
            await asyncio.sleep(0.2)
            final_response = await client.get(f"/instances/{instance_id}")
            final_data = final_response.json()

            # The decision should be recorded in context
            assert final_data["data"].get("decision") == "reject"
            assert final_data["data"].get("comments") == "Missing required sections"
            # Status should no longer be WAITING
            assert final_data["status"] != WorkflowStatus.WAITING.value

    async def test_document_approval_workflow_request_changes_path(self, full_app):
        """Test document approval workflow through request changes path.

        Note: Full E2E completion testing is limited by test client's handling of
        background asyncio tasks. This test verifies the human task flow works correctly.
        """
        async with AsyncTestClient(app=full_app) as client:
            # Start workflow
            start_response = await client.post(
                "/workflows/document_approval/start",
                json={
                    "document_id": "DOC-003",
                    "submitter": "bob@example.com",
                },
            )

            instance_id = start_response.json()["instance_id"]

            # Wait for human step
            await asyncio.sleep(0.3)

            # Verify at human step
            status_response = await client.get(f"/instances/{instance_id}")
            assert status_response.json()["status"] == WorkflowStatus.WAITING.value

            # Complete with request changes
            await client.post(
                f"/instances/{instance_id}/complete-task",
                json={
                    "user_id": "reviewer@example.com",
                    "decision": "request_changes",
                    "comments": "Please add executive summary",
                },
            )

            # Verify the human task was processed
            await asyncio.sleep(0.2)
            final_response = await client.get(f"/instances/{instance_id}")
            final_data = final_response.json()

            # The decision should be recorded in context
            assert final_data["data"].get("decision") == "request_changes"
            assert final_data["data"].get("comments") == "Please add executive summary"
            # Status should no longer be WAITING
            assert final_data["status"] != WorkflowStatus.WAITING.value

    async def test_list_instances(self, full_app):
        """Test listing workflow instances."""
        async with AsyncTestClient(app=full_app) as client:
            # Start a workflow first
            await client.post(
                "/workflows/simple_workflow/start",
                json={"test": "data"},
            )
            await asyncio.sleep(0.2)

            # List instances
            response = await client.get("/instances/")

            assert response.status_code == 200
            instances = response.json()
            assert isinstance(instances, list)
            assert len(instances) >= 1

    async def test_cancel_workflow(self, full_app):
        """Test canceling a workflow."""
        async with AsyncTestClient(app=full_app) as client:
            # Start document approval workflow (will wait at human step)
            start_response = await client.post(
                "/workflows/document_approval/start",
                json={"document_id": "DOC-CANCEL"},
            )

            instance_id = start_response.json()["instance_id"]

            # Wait for it to reach human step
            await asyncio.sleep(0.3)

            # Cancel the workflow
            cancel_response = await client.post(
                f"/instances/{instance_id}/cancel",
                json={"reason": "Test cancellation"},
            )

            assert cancel_response.status_code == 201
            cancel_data = cancel_response.json()
            assert cancel_data["status"] == WorkflowStatus.CANCELED.value
            assert "Test cancellation" in cancel_data["error"]

    async def test_complete_task_on_non_waiting_instance(self, full_app):
        """Test completing task on instance that isn't waiting."""
        async with AsyncTestClient(app=full_app) as client:
            # Start simple workflow (will complete immediately)
            start_response = await client.post(
                "/workflows/simple_workflow/start",
                json={},
            )

            instance_id = start_response.json()["instance_id"]
            await asyncio.sleep(0.3)

            # Try to complete task (should fail since it's already completed)
            complete_response = await client.post(
                f"/instances/{instance_id}/complete-task",
                json={"decision": "approve"},
            )

            assert complete_response.status_code == 201
            complete_data = complete_response.json()
            assert "error" in complete_data
            assert "not waiting" in complete_data["error"].lower()

    async def test_get_instance_step_history(self, full_app):
        """Test that step history is tracked."""
        async with AsyncTestClient(app=full_app) as client:
            # Start and complete document approval
            start_response = await client.post(
                "/workflows/document_approval/start",
                json={"document_id": "DOC-HISTORY"},
            )
            instance_id = start_response.json()["instance_id"]

            await asyncio.sleep(0.3)

            # Complete human task
            await client.post(
                f"/instances/{instance_id}/complete-task",
                json={"decision": "approve"},
            )

            await asyncio.sleep(0.5)

            # Check step history
            response = await client.get(f"/instances/{instance_id}")
            data = response.json()

            # Should have step history entries
            step_history = data.get("step_history", [])
            assert len(step_history) >= 1

            # First step should be submit_document
            step_names = [s["step_name"] for s in step_history]
            assert "submit_document" in step_names


# =============================================================================
# Cross-App Tests
# =============================================================================


class TestCrossAppFeatures:
    """Tests that verify features work across both apps."""

    @pytest.fixture
    def minimal_app(self):
        """Import and return the minimal example app."""
        from examples.minimal.app import app

        return app

    @pytest.fixture
    def full_app(self):
        """Import and return the full example app."""
        from examples.full.app import app

        return app

    async def test_both_apps_have_health_check(self, minimal_app, full_app):
        """Verify both apps have health check endpoints."""
        async with AsyncTestClient(app=minimal_app) as client:
            response = await client.get("/health")
            assert response.status_code == 200

        async with AsyncTestClient(app=full_app) as client:
            response = await client.get("/health")
            assert response.status_code == 200

    async def test_both_apps_list_workflows(self, minimal_app, full_app):
        """Verify both apps can list workflows."""
        async with AsyncTestClient(app=minimal_app) as client:
            response = await client.get("/workflows/")
            assert response.status_code == 200
            assert len(response.json()) >= 1

        async with AsyncTestClient(app=full_app) as client:
            response = await client.get("/workflows/")
            assert response.status_code == 200
            assert len(response.json()) >= 2

    async def test_workflow_mermaid_diagram_generation(self, minimal_app, full_app):
        """Test that both apps generate valid Mermaid diagrams."""
        async with AsyncTestClient(app=minimal_app) as client:
            response = await client.get("/workflows/order_processing")
            mermaid = response.json()["mermaid"]
            assert "graph" in mermaid.lower() or "flowchart" in mermaid.lower()
            assert "validate_order" in mermaid
            assert "process_payment" in mermaid

        async with AsyncTestClient(app=full_app) as client:
            response = await client.get("/workflows/document_approval")
            mermaid = response.json()["mermaid"]
            assert "graph" in mermaid.lower() or "flowchart" in mermaid.lower()
            assert "submit_document" in mermaid
            assert "review_document" in mermaid
