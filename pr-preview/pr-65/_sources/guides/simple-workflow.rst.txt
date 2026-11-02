Building a Simple Workflow
==========================

This guide walks you through building a complete, production-ready workflow
from scratch. You'll create a document processing workflow that validates,
transforms, and stores documents.


Goal
----

Build a workflow that:

1. Validates uploaded document metadata
2. Processes the document content
3. Stores the result
4. Sends a notification

.. code-block:: text

   [Validate] --> [Process] --> [Store] --> [Notify]


Prerequisites
-------------

- litestar-workflows installed
- Basic understanding of async Python


Step 1: Define Your Steps
-------------------------

Create each step as a class that inherits from ``BaseMachineStep``:

.. code-block:: python

   # steps.py
   from litestar_workflows import BaseMachineStep, WorkflowContext


   class ValidateDocument(BaseMachineStep):
       """Validate document metadata and content."""

       name = "validate"
       description = "Validate document meets requirements"

       async def execute(self, context: WorkflowContext) -> None:
           # Get document data from context
           document = context.get("document", {})

           # Validate required fields
           errors = []
           if not document.get("title"):
               errors.append("Title is required")
           if not document.get("content"):
               errors.append("Content is required")
           if len(document.get("content", "")) < 10:
               errors.append("Content must be at least 10 characters")

           # Store validation results
           context.set("validation_errors", errors)
           context.set("is_valid", len(errors) == 0)

           # Fail if validation errors
           if errors:
               raise ValueError(f"Validation failed: {', '.join(errors)}")

       async def can_execute(self, context: WorkflowContext) -> bool:
           """Only run if document exists."""
           return context.get("document") is not None


   class ProcessDocument(BaseMachineStep):
       """Transform document content."""

       name = "process"
       description = "Process and transform document"

       async def execute(self, context: WorkflowContext) -> None:
           document = context.get("document", {})

           # Simulate processing
           processed_content = document["content"].upper()
           word_count = len(document["content"].split())

           # Store results
           context.set("processed_content", processed_content)
           context.set("word_count", word_count)
           context.set("processed_at", datetime.now().isoformat())


   class StoreDocument(BaseMachineStep):
       """Persist document to storage."""

       name = "store"
       description = "Save document to database"

       async def execute(self, context: WorkflowContext) -> None:
           document = context.get("document", {})
           processed_content = context.get("processed_content")

           # Simulate storage (replace with actual database call)
           document_id = f"doc-{uuid4().hex[:8]}"

           context.set("document_id", document_id)
           context.set("stored", True)


   class NotifyComplete(BaseMachineStep):
       """Send completion notification."""

       name = "notify"
       description = "Send notification on completion"

       async def execute(self, context: WorkflowContext) -> None:
           document_id = context.get("document_id")
           word_count = context.get("word_count")

           # Simulate notification (replace with actual service)
           notification = {
               "type": "document_processed",
               "document_id": document_id,
               "word_count": word_count,
               "message": f"Document {document_id} processed successfully",
           }

           context.set("notification", notification)
           context.set("notified", True)


Step 2: Create the Workflow Definition
--------------------------------------

Wire the steps together with edges:

.. code-block:: python

   # workflow.py
   from litestar_workflows import WorkflowDefinition, Edge
   from .steps import ValidateDocument, ProcessDocument, StoreDocument, NotifyComplete

   document_workflow = WorkflowDefinition(
       name="document_processing",
       version="1.0.0",
       description="Validate, process, store, and notify for documents",
       steps={
           "validate": ValidateDocument(),
           "process": ProcessDocument(),
           "store": StoreDocument(),
           "notify": NotifyComplete(),
       },
       edges=[
           Edge(source="validate", target="process"),
           Edge(source="process", target="store"),
           Edge(source="store", target="notify"),
       ],
       initial_step="validate",
       terminal_steps={"notify"},
   )


Step 3: Set Up the Engine
-------------------------

Create a registry and engine:

.. code-block:: python

   # engine_setup.py
   from litestar_workflows import WorkflowRegistry, LocalExecutionEngine
   from .workflow import document_workflow

   # Create and configure registry
   registry = WorkflowRegistry()
   registry.register_definition(document_workflow)

   # Create engine
   engine = LocalExecutionEngine(registry)


Step 4: Run the Workflow
------------------------

Start workflow instances:

.. code-block:: python

   # main.py
   import asyncio
   from .engine_setup import engine

   async def process_document(title: str, content: str) -> dict:
       """Start a document processing workflow."""

       instance = await engine.start_workflow(
           "document_processing",
           initial_data={
               "document": {
                   "title": title,
                   "content": content,
               }
           }
       )

       # Since all steps are machine steps, execution completes immediately
       return {
           "instance_id": str(instance.id),
           "document_id": instance.context.get("document_id"),
           "word_count": instance.context.get("word_count"),
           "status": instance.status.value,
       }


   async def main():
       result = await process_document(
           title="My Document",
           content="This is the content of my document that needs processing."
       )
       print(f"Result: {result}")


   if __name__ == "__main__":
       asyncio.run(main())


Step 5: Add Error Handling
--------------------------

Implement error handling in your steps:

.. code-block:: python

   class ProcessDocument(BaseMachineStep):
       name = "process"

       async def execute(self, context: WorkflowContext) -> None:
           try:
               document = context.get("document", {})
               processed_content = document["content"].upper()
               context.set("processed_content", processed_content)
           except Exception as e:
               context.set("processing_error", str(e))
               raise

       async def on_failure(self, context: WorkflowContext, error: Exception) -> None:
           """Handle processing failures."""
           # Log the error
           print(f"Processing failed: {error}")

           # Set failure state
           context.set("failed_at", "process")
           context.set("failure_reason", str(error))


Step 6: Integrate with Litestar
-------------------------------

Create an API endpoint to trigger workflows:

.. code-block:: python

   # app.py
   from litestar import Litestar, post
   from litestar.di import Provide
   from pydantic import BaseModel

   from .engine_setup import engine


   class DocumentRequest(BaseModel):
       title: str
       content: str


   class WorkflowResponse(BaseModel):
       instance_id: str
       document_id: str | None
       status: str


   @post("/documents/process")
   async def process_document(data: DocumentRequest) -> WorkflowResponse:
       """Process a document through the workflow."""

       instance = await engine.start_workflow(
           "document_processing",
           initial_data={
               "document": {
                   "title": data.title,
                   "content": data.content,
               }
           }
       )

       return WorkflowResponse(
           instance_id=str(instance.id),
           document_id=instance.context.get("document_id"),
           status=instance.status.value,
       )


   app = Litestar(route_handlers=[process_document])


Complete Example
----------------

Here's the complete working example:

.. code-block:: python

   """Complete document processing workflow."""

   import asyncio
   from datetime import datetime
   from uuid import uuid4

   from litestar_workflows import (
       WorkflowDefinition,
       Edge,
       BaseMachineStep,
       LocalExecutionEngine,
       WorkflowRegistry,
       WorkflowContext,
   )


   # Steps
   class ValidateDocument(BaseMachineStep):
       name = "validate"
       description = "Validate document"

       async def execute(self, context: WorkflowContext) -> None:
           document = context.get("document", {})
           if not document.get("title") or not document.get("content"):
               raise ValueError("Title and content required")
           context.set("is_valid", True)


   class ProcessDocument(BaseMachineStep):
       name = "process"
       description = "Process document"

       async def execute(self, context: WorkflowContext) -> None:
           document = context.get("document", {})
           context.set("processed_content", document["content"].upper())
           context.set("word_count", len(document["content"].split()))


   class StoreDocument(BaseMachineStep):
       name = "store"
       description = "Store document"

       async def execute(self, context: WorkflowContext) -> None:
           context.set("document_id", f"doc-{uuid4().hex[:8]}")
           context.set("stored", True)


   class NotifyComplete(BaseMachineStep):
       name = "notify"
       description = "Send notification"

       async def execute(self, context: WorkflowContext) -> None:
           context.set("notified", True)


   # Workflow definition
   document_workflow = WorkflowDefinition(
       name="document_processing",
       version="1.0.0",
       description="Document processing pipeline",
       steps={
           "validate": ValidateDocument(),
           "process": ProcessDocument(),
           "store": StoreDocument(),
           "notify": NotifyComplete(),
       },
       edges=[
           Edge("validate", "process"),
           Edge("process", "store"),
           Edge("store", "notify"),
       ],
       initial_step="validate",
       terminal_steps={"notify"},
   )

   # Setup
   registry = WorkflowRegistry()
   registry.register_definition(document_workflow)
   engine = LocalExecutionEngine(registry)


   async def main():
       instance = await engine.start_workflow(
           "document_processing",
           initial_data={
               "document": {
                   "title": "Test Document",
                   "content": "Hello world this is a test document.",
               }
           }
       )

       print(f"Status: {instance.status}")
       print(f"Document ID: {instance.context.get('document_id')}")
       print(f"Word count: {instance.context.get('word_count')}")


   if __name__ == "__main__":
       asyncio.run(main())


Next Steps
----------

- Add human approval: See :doc:`human-tasks`
- Run steps in parallel: See :doc:`parallel-execution`
- Add conditional logic: See :doc:`conditional-logic`
