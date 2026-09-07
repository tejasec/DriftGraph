"""
CLI entrypoint for the DriftGraph build pipeline.

Usage:
    python -m driftgraph.build [--notes ./data/notes]
"""

import argparse
import asyncio

from driftgraph.config import config
from driftgraph.main import build_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m driftgraph.build",
        description="Build the DriftGraph knowledge graph from a notes directory.",
    )
    parser.add_argument(
        "--notes",
        default=config.paths.notes_dir,
        help="Path to the markdown notes directory.",
    )
    args = parser.parse_args()
    asyncio.run(build_pipeline(args.notes))


if __name__ == "__main__":
    main()
