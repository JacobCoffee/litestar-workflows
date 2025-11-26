Document Review Workflow
========================

A complete document review system with submit-review-revise cycles,
parallel reviewers, approval/rejection handling, and persistence layer
integration.

This recipe demonstrates:

- Submit -> Review -> Revise iteration cycle
- Multiple reviewers in parallel
- Consolidating parallel review results
- Handling approval, rejection, and revision requests
- Full persistence with SQLAlchemy


Overview
--------

The workflow supports iterative document review with multiple reviewers:

.. code-block:: text

   [Submit] --> [Parallel Review] --> [Consolidate] --> [Decision Gateway]
                   |       |               |                   |
              [Reviewer 1][Reviewer 2]     |     +-- (approved) --> [Publish]
                                           |     |
                                           |     +-- (changes) --> [Author Revise] --+
                                           |     |                                   |
                                           |     +-- (rejected) --> [Notify Reject]  |
                                           |                                         |
                                           +<----------------------------------------+

**Review Outcomes:**

- **Approved**: All reviewers approve, document proceeds to publication
- **Changes Requested**: Any reviewer requests changes, author revises
- **Rejected**: Any reviewer rejects, document is declined


Complete Implementation
-----------------------

.. code-block:: python

   """Document review workflow with parallel reviewers and revision cycles.

   Save this file as ``document_review.py`` and run with:
       uv run python document_review.py
   """

   from __future__ import annotations

   from datetime import datetime, timedelta, timezone
   from typing import TYPE_CHECKING, Any

   from litestar import Litestar, get
   from litestar.di import Provide
   from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

   from litestar_workflows import (
       BaseMachineStep,
       BaseHumanStep,
       Edge,
       ExclusiveGateway,
       ParallelGroup,
       WorkflowContext,
       WorkflowDefinition,
       WorkflowPlugin,
       WorkflowPluginConfig,
       WorkflowRegistry,
   )
   from litestar_workflows.db import PersistentExecutionEngine

   if TYPE_CHECKING:
       pass


   # =============================================================================
   # Step Definitions
   # =============================================================================

   class SubmitDocument(BaseMachineStep):
       """Initialize document submission for review."""

       name = "submit_document"
       description = "Record document submission and initialize review"

       async def execute(self, context: WorkflowContext) -> dict[str, Any]:
           """Prepare document for review process."""
           context.set("submitted_at", datetime.now(timezone.utc).isoformat())
           context.set("status", "under_review")
           context.set("revision_count", context.get("revision_count", 0))
           context.set("review_history", context.get("review_history", []))

           # Validate required fields
           title = context.get("document_title")
           if not title:
               raise ValueError("Document title is required")

           document_url = context.get("document_url")
           if not document_url:
               raise ValueError("Document URL is required")

           return {
               "submitted": True,
               "title": title,
               "revision": context.get("revision_count", 0),
           }


   class TechnicalReview(BaseHumanStep):
       """Technical accuracy review."""

       name = "technical_review"
       title = "Technical Review Required"
       description = "Review document for technical accuracy"

       form_schema = {
           "type": "object",
           "title": "Technical Review",
           "properties": {
               "decision": {
                   "type": "string",
                   "title": "Review Decision",
                   "enum": ["approve", "request_changes", "reject"],
                   "enumNames": ["Approve", "Request Changes", "Reject"],
               },
               "technical_accuracy": {
                   "type": "integer",
                   "title": "Technical Accuracy (1-5)",
                   "minimum": 1,
                   "maximum": 5,
               },
               "completeness": {
                   "type": "integer",
                   "title": "Completeness (1-5)",
                   "minimum": 1,
                   "maximum": 5,
               },
               "feedback": {
                   "type": "string",
                   "title": "Feedback",
                   "format": "textarea",
                   "description": "Detailed feedback for the author",
               },
               "specific_issues": {
                   "type": "array",
                   "title": "Specific Issues",
                   "items": {
                       "type": "object",
                       "properties": {
                           "section": {"type": "string", "title": "Section"},
                           "issue": {"type": "string", "title": "Issue"},
                           "suggestion": {"type": "string", "title": "Suggestion"},
                       },
                   },
               },
           },
           "required": ["decision", "technical_accuracy", "completeness"],
       }

       async def get_description(self, context: WorkflowContext) -> str:
           """Provide document context for reviewer."""
           title = context.get("document_title", "Untitled")
           url = context.get("document_url", "")
           revision = context.get("revision_count", 0)
           author = context.get("author", "Unknown")

           return f"""
   **Document Review Request**

   - **Title:** {title}
   - **Author:** {author}
   - **Revision:** {revision}
   - **Document:** [{title}]({url})

   Please review for technical accuracy and completeness.
   """

       async def get_assignee_group(self, context: WorkflowContext) -> str | None:
           """Route to technical reviewers group."""
           return "technical-reviewers"

       async def get_due_date(self, context: WorkflowContext) -> datetime:
           """Technical review due in 3 business days."""
           return datetime.now(timezone.utc) + timedelta(days=3)


   class EditorialReview(BaseHumanStep):
       """Editorial and style review."""

       name = "editorial_review"
       title = "Editorial Review Required"
       description = "Review document for style and clarity"

       form_schema = {
           "type": "object",
           "title": "Editorial Review",
           "properties": {
               "decision": {
                   "type": "string",
                   "title": "Review Decision",
                   "enum": ["approve", "request_changes", "reject"],
                   "enumNames": ["Approve", "Request Changes", "Reject"],
               },
               "clarity": {
                   "type": "integer",
                   "title": "Clarity (1-5)",
                   "minimum": 1,
                   "maximum": 5,
               },
               "style_compliance": {
                   "type": "integer",
                   "title": "Style Guide Compliance (1-5)",
                   "minimum": 1,
                   "maximum": 5,
               },
               "grammar_issues": {
                   "type": "boolean",
                   "title": "Has Grammar Issues",
                   "default": False,
               },
               "feedback": {
                   "type": "string",
                   "title": "Editorial Feedback",
                   "format": "textarea",
               },
           },
           "required": ["decision", "clarity", "style_compliance"],
       }

       async def get_assignee_group(self, context: WorkflowContext) -> str | None:
           """Route to editorial team."""
           return "editorial-team"

       async def get_due_date(self, context: WorkflowContext) -> datetime:
           """Editorial review due in 2 business days."""
           return datetime.now(timezone.utc) + timedelta(days=2)


   class ConsolidateReviews(BaseMachineStep):
       """Consolidate results from parallel reviews."""

       name = "consolidate_reviews"
       description = "Aggregate review decisions and feedback"

       async def execute(self, context: WorkflowContext) -> dict[str, Any]:
           """Consolidate all review feedback into a single decision."""
           # Collect decisions from all reviewers
           tech_decision = context.get("technical_review_decision", "approve")
           edit_decision = context.get("editorial_review_decision", "approve")

           decisions = [tech_decision, edit_decision]

           # Determine consolidated outcome
           if "reject" in decisions:
               consolidated_decision = "rejected"
           elif "request_changes" in decisions:
               consolidated_decision = "changes_requested"
           else:
               consolidated_decision = "approved"

           context.set("consolidated_decision", consolidated_decision)

           # Compile all feedback
           all_feedback = []

           tech_feedback = context.get("technical_review_feedback")
           if tech_feedback:
               all_feedback.append({
                   "reviewer": "Technical",
                   "decision": tech_decision,
                   "feedback": tech_feedback,
                   "issues": context.get("technical_review_specific_issues", []),
               })

           edit_feedback = context.get("editorial_review_feedback")
           if edit_feedback:
               all_feedback.append({
                   "reviewer": "Editorial",
                   "decision": edit_decision,
                   "feedback": edit_feedback,
               })

           context.set("consolidated_feedback", all_feedback)

           # Record in review history
           review_history = context.get("review_history", [])
           review_history.append({
               "revision": context.get("revision_count", 0),
               "date": datetime.now(timezone.utc).isoformat(),
               "decision": consolidated_decision,
               "feedback": all_feedback,
           })
           context.set("review_history", review_history)

           return {
               "consolidated": True,
               "decision": consolidated_decision,
               "feedback_count": len(all_feedback),
           }


   class ReviewDecisionGateway(ExclusiveGateway):
       """Route based on consolidated review decision."""

       name = "review_decision"
       description = "Route based on review outcome"

       async def evaluate(self, context: WorkflowContext) -> str:
           """Determine next step based on review decision."""
           decision = context.get("consolidated_decision", "changes_requested")

           if decision == "approved":
               return "publish_document"
           elif decision == "rejected":
               return "notify_rejection"
           else:
               # Check revision limit
               revision_count = context.get("revision_count", 0)
               max_revisions = context.get("max_revisions", 3)

               if revision_count >= max_revisions:
                   return "notify_rejection"
               return "author_revision"


   class AuthorRevision(BaseHumanStep):
       """Author addresses reviewer feedback."""

       name = "author_revision"
       title = "Revisions Requested"
       description = "Address reviewer feedback and resubmit"

       form_schema = {
           "type": "object",
           "title": "Document Revision",
           "properties": {
               "revision_notes": {
                   "type": "string",
                   "title": "Revision Notes",
                   "format": "textarea",
                   "description": "Describe the changes you made to address feedback",
                   "minLength": 50,
               },
               "updated_url": {
                   "type": "string",
                   "title": "Updated Document URL",
                   "format": "uri",
                   "description": "URL to the revised document",
               },
               "addressed_issues": {
                   "type": "array",
                   "title": "Issues Addressed",
                   "items": {
                       "type": "object",
                       "properties": {
                           "issue": {"type": "string"},
                           "resolution": {"type": "string"},
                       },
                   },
               },
               "withdraw": {
                   "type": "boolean",
                   "title": "Withdraw Submission",
                   "description": "Check to withdraw this document from review",
                   "default": False,
               },
           },
           "required": ["revision_notes"],
       }

       async def get_description(self, context: WorkflowContext) -> str:
           """Show feedback to author."""
           title = context.get("document_title", "Untitled")
           revision = context.get("revision_count", 0)
           feedback = context.get("consolidated_feedback", [])

           feedback_text = ""
           for item in feedback:
               feedback_text += f"\n\n**{item['reviewer']} Review ({item['decision']})**\n{item['feedback']}"

           return f"""
   **Revision Requested for: {title}**

   Revision #{revision + 1}

   Please address the following feedback:
   {feedback_text}

   Submit your revised document or withdraw if you wish to cancel.
   """

       async def get_assignee(self, context: WorkflowContext) -> str | None:
           """Route back to the original author."""
           return context.get("author")


   class PrepareResubmission(BaseMachineStep):
       """Prepare document for re-review after revision."""

       name = "prepare_resubmission"
       description = "Update document state for re-review"

       async def execute(self, context: WorkflowContext) -> dict[str, Any]:
           """Prepare for next review round."""
           # Check if author withdrew
           if context.get("withdraw"):
               context.set("status", "withdrawn")
               return {"withdrawn": True}

           # Update revision count
           revision_count = context.get("revision_count", 0) + 1
           context.set("revision_count", revision_count)

           # Update document URL if provided
           updated_url = context.get("updated_url")
           if updated_url:
               context.set("document_url", updated_url)

           context.set("status", "resubmitted")
           context.set("resubmitted_at", datetime.now(timezone.utc).isoformat())

           return {
               "resubmitted": True,
               "revision": revision_count,
           }


   class PublishDocument(BaseMachineStep):
       """Publish approved document."""

       name = "publish_document"
       description = "Publish the approved document"

       async def execute(self, context: WorkflowContext) -> dict[str, Any]:
           """Finalize and publish document."""
           context.set("status", "published")
           context.set("published_at", datetime.now(timezone.utc).isoformat())

           # Calculate average scores
           tech_accuracy = context.get("technical_review_technical_accuracy", 0)
           tech_complete = context.get("technical_review_completeness", 0)
           edit_clarity = context.get("editorial_review_clarity", 0)
           edit_style = context.get("editorial_review_style_compliance", 0)

           scores = [s for s in [tech_accuracy, tech_complete, edit_clarity, edit_style] if s > 0]
           avg_score = sum(scores) / len(scores) if scores else 0

           context.set("quality_score", avg_score)

           # In a real app: publish to CMS, notify stakeholders
           return {
               "published": True,
               "title": context.get("document_title"),
               "quality_score": avg_score,
               "revisions": context.get("revision_count", 0),
           }


   class NotifyRejection(BaseMachineStep):
       """Notify author of document rejection."""

       name = "notify_rejection"
       description = "Handle document rejection"

       async def execute(self, context: WorkflowContext) -> dict[str, Any]:
           """Process rejection and notify author."""
           context.set("status", "rejected")
           context.set("rejected_at", datetime.now(timezone.utc).isoformat())

           # In a real app: send notification email
           return {
               "rejected": True,
               "reason": "Document did not meet quality standards after review",
               "feedback": context.get("consolidated_feedback"),
           }


   # =============================================================================
   # Workflow Definition
   # =============================================================================

   # Create parallel review group
   parallel_review = ParallelGroup(
       TechnicalReview(),
       EditorialReview(),
   )


   document_review_workflow = WorkflowDefinition(
       name="document_review",
       version="1.0.0",
       description="Document review with parallel reviewers and revision cycles",
       steps={
           "submit_document": SubmitDocument(),
           "parallel_review": parallel_review,
           "consolidate_reviews": ConsolidateReviews(),
           "review_decision": ReviewDecisionGateway(),
           "author_revision": AuthorRevision(),
           "prepare_resubmission": PrepareResubmission(),
           "publish_document": PublishDocument(),
           "notify_rejection": NotifyRejection(),
       },
       edges=[
           # Initial flow
           Edge("submit_document", "parallel_review"),
           Edge("parallel_review", "consolidate_reviews"),
           Edge("consolidate_reviews", "review_decision"),

           # Decision gateway routes
           Edge(
               "review_decision",
               "publish_document",
               condition="context.get('consolidated_decision') == 'approved'"
           ),
           Edge(
               "review_decision",
               "author_revision",
               condition="context.get('consolidated_decision') == 'changes_requested'"
           ),
           Edge(
               "review_decision",
               "notify_rejection",
               condition="context.get('consolidated_decision') == 'rejected'"
           ),

           # Revision cycle
           Edge("author_revision", "prepare_resubmission"),
           Edge(
               "prepare_resubmission",
               "parallel_review",
               condition="context.get('withdraw') != True"
           ),
           Edge(
               "prepare_resubmission",
               "notify_rejection",
               condition="context.get('withdraw') == True"
           ),
       ],
       initial_step="submit_document",
       terminal_steps={"publish_document", "notify_rejection"},
   )


   # =============================================================================
   # Application Setup
   # =============================================================================

   def create_app() -> Litestar:
       """Create the Litestar application with document review workflow."""
       db_engine = create_async_engine(
           "sqlite+aiosqlite:///documents.db",
           echo=False,
       )
       session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

       registry = WorkflowRegistry()
       registry.register_definition(document_review_workflow)

       async def provide_session() -> AsyncSession:
           async with session_factory() as session:
               yield session

       async def provide_engine(session: AsyncSession) -> PersistentExecutionEngine:
           return PersistentExecutionEngine(registry=registry, session=session)

       async def provide_registry() -> WorkflowRegistry:
           return registry

       @get("/health")
       async def health() -> dict[str, str]:
           return {"status": "healthy"}

       return Litestar(
           route_handlers=[health],
           plugins=[
               WorkflowPlugin(
                   config=WorkflowPluginConfig(
                       enable_api=True,
                       api_path_prefix="/api/workflows",
                   )
               ),
           ],
           dependencies={
               "session": Provide(provide_session),
               "workflow_engine": Provide(provide_engine),
               "workflow_registry": Provide(provide_registry),
           },
       )


   app = create_app()


   if __name__ == "__main__":
       import uvicorn
       uvicorn.run(app, host="0.0.0.0", port=8000)


Key Concepts
------------

Parallel Review Pattern
~~~~~~~~~~~~~~~~~~~~~~~

Multiple reviewers work simultaneously using ``ParallelGroup``:

.. code-block:: python

   from litestar_workflows import ParallelGroup

   parallel_review = ParallelGroup(
       TechnicalReview(),
       EditorialReview(),
   )

   # In workflow definition
   steps={"parallel_review": parallel_review}

All reviewers receive tasks at the same time. The workflow waits until
all complete before proceeding.


Consolidating Parallel Results
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After parallel steps complete, aggregate their outputs:

.. code-block:: python

   class ConsolidateReviews(BaseMachineStep):
       async def execute(self, context: WorkflowContext) -> dict:
           # Each parallel step stores results with a prefix
           tech_decision = context.get("technical_review_decision")
           edit_decision = context.get("editorial_review_decision")

           # Determine overall outcome
           if "reject" in [tech_decision, edit_decision]:
               context.set("consolidated_decision", "rejected")
           elif "request_changes" in [tech_decision, edit_decision]:
               context.set("consolidated_decision", "changes_requested")
           else:
               context.set("consolidated_decision", "approved")


Revision Cycle
~~~~~~~~~~~~~~

The workflow loops back for revisions using conditional edges:

.. code-block:: python

   edges = [
       # Author revision returns to review
       Edge("author_revision", "prepare_resubmission"),
       Edge(
           "prepare_resubmission",
           "parallel_review",  # Loop back
           condition="context.get('withdraw') != True"
       ),
   ]

Track revision count to prevent infinite loops:

.. code-block:: python

   revision_count = context.get("revision_count", 0)
   max_revisions = context.get("max_revisions", 3)

   if revision_count >= max_revisions:
       return "notify_rejection"


Customization Points
--------------------

**Add More Reviewers**
    Add steps to the ``ParallelGroup``

**Change Review Criteria**
    Modify the ``form_schema`` in review steps

**Adjust Revision Limits**
    Set ``max_revisions`` in the initial context

**Add Legal Review**
    Create a ``LegalReview`` step and add to parallel group


Usage Example
-------------

Start a document review via the API:

.. code-block:: bash

   curl -X POST http://localhost:8000/api/workflows/instances \
     -H "Content-Type: application/json" \
     -d '{
       "definition_name": "document_review",
       "input_data": {
         "document_title": "API Design Guidelines",
         "document_url": "https://docs.example.com/draft/api-guidelines",
         "author": "alice@example.com",
         "max_revisions": 3
       }
     }'

Complete a technical review:

.. code-block:: bash

   curl -X POST http://localhost:8000/api/workflows/tasks/{task_id}/complete \
     -H "Content-Type: application/json" \
     -d '{
       "output_data": {
         "decision": "request_changes",
         "technical_accuracy": 4,
         "completeness": 3,
         "feedback": "Good overall, but missing error handling section"
       },
       "completed_by": "reviewer@example.com"
     }'


Testing
-------

.. code-block:: python

   import pytest
   from litestar_workflows import WorkflowContext

   from document_review import ConsolidateReviews, ReviewDecisionGateway


   @pytest.mark.asyncio
   async def test_consolidate_all_approved():
       """All approvals should consolidate to approved."""
       context = WorkflowContext()
       context.set("technical_review_decision", "approve")
       context.set("editorial_review_decision", "approve")

       step = ConsolidateReviews()
       await step.execute(context)

       assert context.get("consolidated_decision") == "approved"


   @pytest.mark.asyncio
   async def test_consolidate_any_rejection():
       """Any rejection should consolidate to rejected."""
       context = WorkflowContext()
       context.set("technical_review_decision", "approve")
       context.set("editorial_review_decision", "reject")

       step = ConsolidateReviews()
       await step.execute(context)

       assert context.get("consolidated_decision") == "rejected"


   @pytest.mark.asyncio
   async def test_revision_limit():
       """Exceeding revision limit should trigger rejection."""
       context = WorkflowContext()
       context.set("consolidated_decision", "changes_requested")
       context.set("revision_count", 3)
       context.set("max_revisions", 3)

       gateway = ReviewDecisionGateway()
       result = await gateway.evaluate(context)

       assert result == "notify_rejection"


See Also
--------

- :doc:`/guides/parallel-execution` - Parallel step patterns
- :doc:`/guides/human-tasks` - Human task configuration
- :doc:`/guides/persistence` - Database persistence
- :doc:`integration-patterns` - External API integration
