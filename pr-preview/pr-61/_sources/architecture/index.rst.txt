Architecture Documentation
==========================

This section contains detailed architecture documents for litestar-workflows,
including design decisions, module structures, and implementation specifications.

.. toctree::
   :maxdepth: 2
   :caption: Architecture Documents

   phase3-web


Overview
--------

The litestar-workflows library is structured in layers:

.. code-block:: text

   +------------------------------------------------------------------+
   |                      User Application                              |
   +------------------------------------------------------------------+
   |                    litestar-workflows[web]                        |
   |  Controllers | DTOs | Guards | Graph Service | OpenAPI            |
   +------------------------------------------------------------------+
   |                     litestar-workflows[db]                        |
   |  SQLAlchemy Models | Repositories | Migrations | Persistent Engine|
   +------------------------------------------------------------------+
   |                       litestar-workflows                          |
   |  Core Protocols | Types | Context | Definition | Events           |
   |  Engine (Local) | Registry | Steps | Groups | Gateways            |
   +------------------------------------------------------------------+


Design Principles
-----------------

1. **Async-First**: All execution APIs are async, leveraging Litestar's foundation
2. **Protocol-Based**: Interfaces defined with Protocol for structural typing
3. **Plugin Architecture**: Core + optional extras (db, web, ui)
4. **Type-Safe**: Full typing throughout with strict mypy compatibility
5. **Litestar-Native**: Deep integration with DI, guards, middleware


Phase Documentation
-------------------

Each implementation phase has its own architecture document:

- **Phase 1**: Core Foundation (completed) - See PLAN.md
- **Phase 2**: Persistence Layer (completed) - See ``guides/persistence.rst``
- **Phase 3**: Web Plugin - :doc:`phase3-web`
- **Phase 4**: Decorator API - Coming soon
- **Phase 5**: UI Extra - Coming soon
- **Phase 6**: Distributed Execution - Coming soon
