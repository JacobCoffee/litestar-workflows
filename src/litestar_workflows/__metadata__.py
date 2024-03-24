"""Project Metadata based on it's``pyproject.toml``."""

from __future__ import annotations

import importlib.metadata

__all__ = ("__version__", "__project__")

__version__ = importlib.metadata.version("litestar-workflows")
"""Version of the project."""
__project__ = importlib.metadata.metadata("litestar-workflows")["Name"]
"""Name of the project."""
