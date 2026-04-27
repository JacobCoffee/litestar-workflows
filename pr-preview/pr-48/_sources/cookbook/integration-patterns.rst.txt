Integration Patterns
====================

Common patterns for integrating litestar-workflows with external services,
including API calls, error handling, retry strategies, event hooks, and
testing approaches.

This guide covers:

- Connecting to external APIs in workflow steps
- Error handling and retry strategies
- Event hooks for notifications and monitoring
- Testing workflows effectively


Connecting to External APIs
---------------------------

Steps often need to call external services. Here are patterns for doing
this reliably.


Basic HTTP Client Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``httpx`` for async HTTP calls:

.. code-block:: python

   """External API integration patterns."""

   from __future__ import annotations

   import httpx
   from typing import TYPE_CHECKING, Any

   from litestar_workflows import BaseMachineStep, WorkflowContext

   if TYPE_CHECKING:
       pass


   class FetchUserData(BaseMachineStep):
       """Fetch user data from external API."""

       name = "fetch_user"
       description = "Retrieve user information from user service"

       def __init__(self, api_base_url: str, api_key: str) -> None:
           super().__init__()
           self.api_base_url = api_base_url
           self.api_key = api_key

       async def execute(self, context: WorkflowContext) -> dict[str, Any]:
           """Fetch user data and store in context."""
           user_id = context.get("user_id")
           if not user_id:
               raise ValueError("user_id is required")

           async with httpx.AsyncClient() as client:
               response = await client.get(
                   f"{self.api_base_url}/users/{user_id}",
                   headers={"Authorization": f"Bearer {self.api_key}"},
                   timeout=30.0,
               )
               response.raise_for_status()
               user_data = response.json()

           context.set("user_data", user_data)
           context.set("user_email", user_data.get("email"))

           return {"fetched": True, "user_id": user_id}


Shared HTTP Client
~~~~~~~~~~~~~~~~~~

For better performance, share a client across steps:

.. code-block:: python

   from litestar_workflows import BaseMachineStep, WorkflowContext


   class APIStep(BaseMachineStep):
       """Base class for steps that call external APIs."""

       # Shared client instance (configure connection pooling)
       _client: httpx.AsyncClient | None = None

       @classmethod
       async def get_client(cls) -> httpx.AsyncClient:
           """Get or create shared HTTP client."""
           if cls._client is None:
               cls._client = httpx.AsyncClient(
                   timeout=30.0,
                   limits=httpx.Limits(max_keepalive_connections=10),
               )
           return cls._client

       @classmethod
       async def close_client(cls) -> None:
           """Close shared client (call on app shutdown)."""
           if cls._client is not None:
               await cls._client.aclose()
               cls._client = None


   class FetchOrderDetails(APIStep):
       """Fetch order from order service."""

       name = "fetch_order"

       async def execute(self, context: WorkflowContext) -> dict:
           client = await self.get_client()
           order_id = context.get("order_id")

           response = await client.get(f"https://orders.internal/api/orders/{order_id}")
           response.raise_for_status()

           context.set("order_details", response.json())
           return {"fetched": True}


Dependency Injection for Clients
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Inject API clients through Litestar's DI system:

.. code-block:: python

   from dataclasses import dataclass
   from litestar import Litestar
   from litestar.di import Provide


   @dataclass
   class PaymentClient:
       """Payment service client."""

       base_url: str
       api_key: str

       async def charge(self, amount: float, customer_id: str) -> dict:
           async with httpx.AsyncClient() as client:
               response = await client.post(
                   f"{self.base_url}/charges",
                   headers={"Authorization": f"Bearer {self.api_key}"},
                   json={"amount": amount, "customer_id": customer_id},
               )
               response.raise_for_status()
               return response.json()


   class ProcessPayment(BaseMachineStep):
       """Process payment using injected client."""

       name = "process_payment"

       def __init__(self, payment_client: PaymentClient) -> None:
           super().__init__()
           self.payment_client = payment_client

       async def execute(self, context: WorkflowContext) -> dict:
           result = await self.payment_client.charge(
               amount=context.get("amount"),
               customer_id=context.get("customer_id"),
           )
           context.set("payment_id", result["id"])
           return {"charged": True}


   # In app setup
   async def provide_payment_client() -> PaymentClient:
       return PaymentClient(
           base_url="https://payments.example.com",
           api_key=os.environ["PAYMENT_API_KEY"],
       )


   app = Litestar(
       dependencies={
           "payment_client": Provide(provide_payment_client),
       },
   )


Error Handling and Retry Strategies
-----------------------------------

External services fail. Handle failures gracefully.


Basic Error Handling
~~~~~~~~~~~~~~~~~~~~

Catch and classify errors:

.. code-block:: python

   import httpx
   from litestar_workflows import BaseMachineStep, WorkflowContext


   class ResilientAPICall(BaseMachineStep):
       """API call with error handling."""

       name = "resilient_api_call"

       async def execute(self, context: WorkflowContext) -> dict:
           try:
               async with httpx.AsyncClient() as client:
                   response = await client.get(
                       "https://api.example.com/data",
                       timeout=30.0,
                   )
                   response.raise_for_status()

                   context.set("api_data", response.json())
                   context.set("api_success", True)
                   return {"success": True}

           except httpx.TimeoutException:
               context.set("api_error", "timeout")
               context.set("api_success", False)
               # Don't re-raise - let workflow decide how to handle
               return {"success": False, "error": "timeout"}

           except httpx.HTTPStatusError as e:
               context.set("api_error", f"http_{e.response.status_code}")
               context.set("api_success", False)

               # Client errors (4xx) are not retryable
               if 400 <= e.response.status_code < 500:
                   context.set("retryable", False)
               else:
                   context.set("retryable", True)

               return {"success": False, "error": str(e)}

           except httpx.RequestError as e:
               context.set("api_error", "connection_error")
               context.set("api_success", False)
               context.set("retryable", True)
               return {"success": False, "error": str(e)}


Retry with Exponential Backoff
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Implement retry logic with backoff:

.. code-block:: python

   import asyncio
   import random
   from datetime import datetime, timezone


   class RetryableStep(BaseMachineStep):
       """Step with built-in retry capability."""

       max_retries: int = 3
       base_delay: float = 1.0
       max_delay: float = 60.0

       async def execute(self, context: WorkflowContext) -> dict:
           """Execute with retry logic."""
           retry_count = context.get(f"{self.name}_retry_count", 0)

           try:
               result = await self._do_work(context)
               context.set(f"{self.name}_retry_count", 0)  # Reset on success
               return result

           except Exception as e:
               if not self._is_retryable(e):
                   raise

               if retry_count >= self.max_retries:
                   context.set(f"{self.name}_final_error", str(e))
                   raise

               # Calculate backoff delay
               delay = min(
                   self.base_delay * (2 ** retry_count) + random.uniform(0, 1),
                   self.max_delay,
               )

               context.set(f"{self.name}_retry_count", retry_count + 1)
               context.set(f"{self.name}_next_retry", (datetime.now(timezone.utc)).isoformat())

               await asyncio.sleep(delay)

               # Recursive retry
               return await self.execute(context)

       async def _do_work(self, context: WorkflowContext) -> dict:
           """Override this method with actual work."""
           raise NotImplementedError

       def _is_retryable(self, error: Exception) -> bool:
           """Determine if error is retryable."""
           retryable_types = (
               httpx.TimeoutException,
               httpx.ConnectError,
               httpx.ReadTimeout,
           )
           if isinstance(error, retryable_types):
               return True

           if isinstance(error, httpx.HTTPStatusError):
               # Retry server errors (5xx), not client errors (4xx)
               return error.response.status_code >= 500

           return False


   class FetchWithRetry(RetryableStep):
       """Fetch data with automatic retry."""

       name = "fetch_with_retry"
       max_retries = 3

       async def _do_work(self, context: WorkflowContext) -> dict:
           async with httpx.AsyncClient() as client:
               response = await client.get("https://api.example.com/data")
               response.raise_for_status()
               context.set("data", response.json())
               return {"fetched": True}


Circuit Breaker Pattern
~~~~~~~~~~~~~~~~~~~~~~~

Prevent cascading failures with circuit breaker:

.. code-block:: python

   from dataclasses import dataclass, field
   from datetime import datetime, timezone
   from enum import StrEnum


   class CircuitState(StrEnum):
       CLOSED = "closed"      # Normal operation
       OPEN = "open"          # Failing, reject calls
       HALF_OPEN = "half_open"  # Testing if recovered


   @dataclass
   class CircuitBreaker:
       """Circuit breaker for external service calls."""

       failure_threshold: int = 5
       recovery_timeout: float = 60.0

       _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
       _failure_count: int = field(default=0, init=False)
       _last_failure_time: datetime | None = field(default=None, init=False)

       def can_execute(self) -> bool:
           """Check if call should proceed."""
           if self._state == CircuitState.CLOSED:
               return True

           if self._state == CircuitState.OPEN:
               # Check if recovery timeout has passed
               if self._last_failure_time:
                   elapsed = (datetime.now(timezone.utc) - self._last_failure_time).total_seconds()
                   if elapsed >= self.recovery_timeout:
                       self._state = CircuitState.HALF_OPEN
                       return True
               return False

           # HALF_OPEN - allow one test call
           return True

       def record_success(self) -> None:
           """Record successful call."""
           self._failure_count = 0
           self._state = CircuitState.CLOSED

       def record_failure(self) -> None:
           """Record failed call."""
           self._failure_count += 1
           self._last_failure_time = datetime.now(timezone.utc)

           if self._failure_count >= self.failure_threshold:
               self._state = CircuitState.OPEN


   # Usage in step
   class ProtectedAPICall(BaseMachineStep):
       """API call with circuit breaker protection."""

       name = "protected_call"
       _circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

       async def execute(self, context: WorkflowContext) -> dict:
           if not self._circuit_breaker.can_execute():
               context.set("circuit_open", True)
               return {"success": False, "error": "circuit_open"}

           try:
               async with httpx.AsyncClient() as client:
                   response = await client.get("https://api.example.com/data")
                   response.raise_for_status()

               self._circuit_breaker.record_success()
               context.set("data", response.json())
               return {"success": True}

           except Exception as e:
               self._circuit_breaker.record_failure()
               context.set("error", str(e))
               return {"success": False, "error": str(e)}


Event Hooks for Notifications
-----------------------------

Trigger actions at workflow lifecycle events.


Workflow Event Handlers
~~~~~~~~~~~~~~~~~~~~~~~

Subscribe to workflow events:

.. code-block:: python

   from litestar_workflows.core.events import (
       WorkflowEvent,
       WorkflowStartedEvent,
       WorkflowCompletedEvent,
       WorkflowFailedEvent,
       StepCompletedEvent,
       HumanTaskCreatedEvent,
   )


   class NotificationHandler:
       """Handle workflow events and send notifications."""

       def __init__(self, slack_webhook_url: str, email_service):
           self.slack_webhook_url = slack_webhook_url
           self.email_service = email_service

       async def handle_event(self, event: WorkflowEvent) -> None:
           """Route events to appropriate handlers."""
           if isinstance(event, WorkflowStartedEvent):
               await self._on_workflow_started(event)
           elif isinstance(event, WorkflowCompletedEvent):
               await self._on_workflow_completed(event)
           elif isinstance(event, WorkflowFailedEvent):
               await self._on_workflow_failed(event)
           elif isinstance(event, HumanTaskCreatedEvent):
               await self._on_task_created(event)

       async def _on_workflow_started(self, event: WorkflowStartedEvent) -> None:
           """Log workflow start."""
           # Send to monitoring system
           pass

       async def _on_workflow_completed(self, event: WorkflowCompletedEvent) -> None:
           """Notify on successful completion."""
           await self._send_slack(
               f"Workflow `{event.workflow_name}` completed successfully"
           )

       async def _on_workflow_failed(self, event: WorkflowFailedEvent) -> None:
           """Alert on workflow failure."""
           await self._send_slack(
               f"ALERT: Workflow `{event.workflow_name}` failed: {event.error}",
               urgent=True,
           )

       async def _on_task_created(self, event: HumanTaskCreatedEvent) -> None:
           """Notify assignee of new task."""
           await self.email_service.send(
               to=event.assignee,
               subject=f"New Task: {event.task_title}",
               body=f"You have a new task to complete: {event.task_title}",
           )

       async def _send_slack(self, message: str, urgent: bool = False) -> None:
           """Send Slack notification."""
           async with httpx.AsyncClient() as client:
               await client.post(
                   self.slack_webhook_url,
                   json={"text": message, "unfurl_links": False},
               )


Notification Steps
~~~~~~~~~~~~~~~~~~

Add notification steps directly in workflows:

.. code-block:: python

   class SendSlackNotification(BaseMachineStep):
       """Send notification to Slack channel."""

       name = "send_slack"
       description = "Send Slack notification"

       def __init__(self, webhook_url: str, channel: str = "#workflows") -> None:
           super().__init__()
           self.webhook_url = webhook_url
           self.channel = channel

       async def execute(self, context: WorkflowContext) -> dict:
           """Send notification with workflow context."""
           message = self._format_message(context)

           async with httpx.AsyncClient() as client:
               response = await client.post(
                   self.webhook_url,
                   json={
                       "channel": self.channel,
                       "text": message,
                       "blocks": self._build_blocks(context),
                   },
               )

           context.set("slack_sent", response.is_success)
           return {"sent": response.is_success}

       def _format_message(self, context: WorkflowContext) -> str:
           """Format notification message."""
           workflow_name = context.get("_workflow_name", "Unknown")
           status = context.get("status", "unknown")
           return f"Workflow {workflow_name}: {status}"

       def _build_blocks(self, context: WorkflowContext) -> list[dict]:
           """Build rich Slack blocks."""
           return [
               {
                   "type": "section",
                   "text": {
                       "type": "mrkdwn",
                       "text": f"*Workflow Update*\n{self._format_message(context)}",
                   },
               },
               {
                   "type": "context",
                   "elements": [
                       {"type": "mrkdwn", "text": f"Instance: {context.get('_instance_id')}"},
                   ],
               },
           ]


   class SendEmailNotification(BaseMachineStep):
       """Send email notification."""

       name = "send_email"

       def __init__(self, smtp_config: dict) -> None:
           super().__init__()
           self.smtp_config = smtp_config

       async def execute(self, context: WorkflowContext) -> dict:
           """Send email based on context."""
           recipient = context.get("notification_email")
           if not recipient:
               return {"sent": False, "reason": "no_recipient"}

           subject = context.get("email_subject", "Workflow Notification")
           body = context.get("email_body", "Your workflow has been updated.")

           # In real implementation, use aiosmtplib or similar
           # await send_email(recipient, subject, body)

           context.set("email_sent", True)
           return {"sent": True, "recipient": recipient}


Testing Workflows
-----------------

Effective testing strategies for workflow code.


Unit Testing Steps
~~~~~~~~~~~~~~~~~~

Test individual steps in isolation:

.. code-block:: python

   """Unit tests for workflow steps."""

   import pytest
   from unittest.mock import AsyncMock, patch

   from litestar_workflows import WorkflowContext
   from my_workflow import FetchUserData, ProcessPayment


   @pytest.mark.asyncio
   async def test_fetch_user_data_success():
       """Test successful user fetch."""
       context = WorkflowContext()
       context.set("user_id", "user-123")

       step = FetchUserData(
           api_base_url="https://api.example.com",
           api_key="test-key",
       )

       # Mock the HTTP call
       with patch("httpx.AsyncClient.get") as mock_get:
           mock_response = AsyncMock()
           mock_response.json.return_value = {
               "id": "user-123",
               "email": "test@example.com",
               "name": "Test User",
           }
           mock_response.raise_for_status = AsyncMock()
           mock_get.return_value = mock_response

           result = await step.execute(context)

       assert result["fetched"] is True
       assert context.get("user_email") == "test@example.com"


   @pytest.mark.asyncio
   async def test_fetch_user_data_missing_id():
       """Test error when user_id not provided."""
       context = WorkflowContext()  # No user_id set

       step = FetchUserData(
           api_base_url="https://api.example.com",
           api_key="test-key",
       )

       with pytest.raises(ValueError, match="user_id is required"):
           await step.execute(context)


   @pytest.mark.asyncio
   async def test_process_payment_calls_client():
       """Test payment processing calls client correctly."""
       context = WorkflowContext()
       context.set("amount", 100.00)
       context.set("customer_id", "cust-456")

       mock_client = AsyncMock()
       mock_client.charge.return_value = {"id": "charge-789"}

       step = ProcessPayment(payment_client=mock_client)
       result = await step.execute(context)

       mock_client.charge.assert_called_once_with(
           amount=100.00,
           customer_id="cust-456",
       )
       assert context.get("payment_id") == "charge-789"


Testing Workflow Definitions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Validate workflow structure:

.. code-block:: python

   import pytest
   from my_workflow import expense_approval_workflow


   def test_workflow_definition_valid():
       """Workflow definition should be valid."""
       # Validation happens on construction
       assert expense_approval_workflow is not None
       assert expense_approval_workflow.name == "expense_approval"


   def test_workflow_has_required_steps():
       """Workflow should have all required steps."""
       step_names = set(expense_approval_workflow.steps.keys())

       required_steps = {
           "submit_expense",
           "amount_router",
           "manager_approval",
           "process_approved",
       }

       assert required_steps.issubset(step_names)


   def test_workflow_has_valid_edges():
       """All edge targets should exist as steps."""
       step_names = set(expense_approval_workflow.steps.keys())

       for edge in expense_approval_workflow.edges:
           assert edge.source in step_names, f"Source {edge.source} not in steps"
           assert edge.target in step_names, f"Target {edge.target} not in steps"


   def test_workflow_initial_step_exists():
       """Initial step should be a valid step."""
       assert expense_approval_workflow.initial_step in expense_approval_workflow.steps


   def test_workflow_terminal_steps_exist():
       """All terminal steps should be valid steps."""
       for terminal in expense_approval_workflow.terminal_steps:
           assert terminal in expense_approval_workflow.steps


Integration Testing with Engine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Test complete workflow execution:

.. code-block:: python

   import pytest
   from litestar_workflows import LocalExecutionEngine, WorkflowRegistry

   from my_workflow import expense_approval_workflow


   @pytest.fixture
   def engine():
       """Create test execution engine."""
       registry = WorkflowRegistry()
       registry.register_definition(expense_approval_workflow)
       return LocalExecutionEngine(registry)


   @pytest.mark.asyncio
   async def test_small_expense_auto_approved(engine):
       """Expenses under threshold should auto-approve."""
       instance = await engine.start_workflow(
           "expense_approval",
           initial_data={
               "amount": 500,
               "requester": "alice@example.com",
               "description": "Office supplies",
           },
       )

       # Should complete immediately (auto-approved)
       assert instance.status.value == "completed"
       assert instance.context.get("approved") is True
       assert instance.context.get("approved_by") == "system"


   @pytest.mark.asyncio
   async def test_medium_expense_waits_for_approval(engine):
       """Medium expenses should wait for manager approval."""
       instance = await engine.start_workflow(
           "expense_approval",
           initial_data={
               "amount": 2500,
               "requester": "bob@example.com",
               "description": "Conference registration",
           },
       )

       # Should be waiting for human task
       assert instance.status.value == "waiting"
       assert instance.current_step == "manager_approval"


   @pytest.mark.asyncio
   async def test_complete_human_task(engine):
       """Test completing a human task continues workflow."""
       instance = await engine.start_workflow(
           "expense_approval",
           initial_data={
               "amount": 2500,
               "requester": "bob@example.com",
           },
       )

       # Complete the manager approval task
       await engine.complete_human_task(
           instance_id=instance.id,
           step_name="manager_approval",
           user_id="manager@example.com",
           data={
               "decision": "approve",
               "comments": "Looks good",
           },
       )

       # Refresh instance
       instance = await engine.get_instance(instance.id)

       # Should now be completed
       assert instance.status.value == "completed"
       assert instance.context.get("status") == "approved"


End-to-End API Testing
~~~~~~~~~~~~~~~~~~~~~~

Test via the REST API:

.. code-block:: python

   import pytest
   from litestar.testing import AsyncTestClient

   from my_app import app


   @pytest.fixture
   def client():
       return AsyncTestClient(app)


   @pytest.mark.asyncio
   async def test_start_workflow_api(client):
       """Test starting workflow via API."""
       response = await client.post(
           "/api/workflows/instances",
           json={
               "definition_name": "expense_approval",
               "input_data": {
                   "amount": 500,
                   "requester": "test@example.com",
               },
           },
       )

       assert response.status_code == 200
       data = response.json()
       assert "id" in data
       assert data["definition_name"] == "expense_approval"


   @pytest.mark.asyncio
   async def test_complete_task_api(client):
       """Test completing task via API."""
       # First start a workflow that creates a task
       start_response = await client.post(
           "/api/workflows/instances",
           json={
               "definition_name": "expense_approval",
               "input_data": {"amount": 5000, "requester": "test@example.com"},
           },
       )
       instance_id = start_response.json()["id"]

       # Get pending tasks
       tasks_response = await client.get(
           f"/api/workflows/tasks?status=pending"
       )
       tasks = tasks_response.json()
       task = next(t for t in tasks if t["instance_id"] == instance_id)

       # Complete the task
       complete_response = await client.post(
           f"/api/workflows/tasks/{task['id']}/complete",
           json={
               "output_data": {"decision": "approve"},
               "completed_by": "manager@example.com",
           },
       )

       assert complete_response.status_code == 200


Mocking External Services
~~~~~~~~~~~~~~~~~~~~~~~~~

Use pytest fixtures to mock external dependencies:

.. code-block:: python

   import pytest
   from unittest.mock import AsyncMock


   @pytest.fixture
   def mock_payment_client():
       """Mock payment client for testing."""
       client = AsyncMock()
       client.charge.return_value = {"id": "test-charge-123", "status": "succeeded"}
       client.refund.return_value = {"id": "test-refund-456", "status": "succeeded"}
       return client


   @pytest.fixture
   def mock_email_service():
       """Mock email service for testing."""
       service = AsyncMock()
       service.send.return_value = True
       return service


   @pytest.mark.asyncio
   async def test_payment_workflow(engine, mock_payment_client):
       """Test payment workflow with mocked client."""
       # Inject mock client
       engine.registry.get_step("process_payment").payment_client = mock_payment_client

       instance = await engine.start_workflow(
           "payment_workflow",
           initial_data={"amount": 100, "customer_id": "cust-123"},
       )

       # Verify mock was called correctly
       mock_payment_client.charge.assert_called_once_with(
           amount=100,
           customer_id="cust-123",
       )


Best Practices Summary
----------------------

**API Integration**

1. Use async HTTP clients (``httpx``)
2. Set appropriate timeouts
3. Share clients when possible for connection pooling
4. Use dependency injection for testability

**Error Handling**

1. Classify errors (retryable vs. non-retryable)
2. Implement exponential backoff for retries
3. Use circuit breakers for external services
4. Store error details in context for debugging

**Notifications**

1. Use event handlers for cross-cutting concerns
2. Add notification steps for workflow-specific alerts
3. Include context in notifications for debugging

**Testing**

1. Unit test steps in isolation
2. Validate workflow definitions statically
3. Integration test with engine
4. End-to-end test via API
5. Mock external services consistently


See Also
--------

- :doc:`/guides/persistence` - Database persistence for production
- :doc:`/guides/web-plugin` - REST API configuration
- :doc:`expense-approval` - Complete workflow example
- :doc:`document-review` - Parallel review patterns
