"""
CLI entrypoint for the DriftGraph FastAPI server.

Usage:
    python -m driftgraph.serve [--host 0.0.0.0] [--port 8000]
"""

import argparse
import uvicorn

from driftgraph.config import config


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m driftgraph.serve",
        description="Start the DriftGraph FastAPI web server and UI.",
    )
    parser.add_argument("--host", default=config.server.host, help="Host address.")
    parser.add_argument("--port", type=int, default=config.server.port, help="Port.")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload.")
    args = parser.parse_args()

    uvicorn.run(
        "driftgraph.serve.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
