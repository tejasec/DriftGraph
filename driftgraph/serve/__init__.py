"""
Serving module for DriftGraph FastAPI backend.
"""

from driftgraph.serve.app import create_app, app

__all__ = ["create_app", "app"]
