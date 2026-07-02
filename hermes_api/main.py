"""Console entry point for the Hermes Agent FastAPI server."""

from __future__ import annotations

import argparse

import uvicorn


def build_parser() -> argparse.ArgumentParser:
    """Build the ``hermes-api`` command-line parser."""

    parser = argparse.ArgumentParser(description="Run the Hermes Agent FastAPI server")
    parser.add_argument(
        "--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", default=8000, type=int, help="Bind port (default: 8000)"
    )
    parser.add_argument(
        "--reload", action="store_true", help="Enable Uvicorn reload for development"
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Run the Hermes API with Uvicorn."""

    args = build_parser().parse_args(argv)
    uvicorn.run(
        "hermes_api.app:app", host=args.host, port=args.port, reload=args.reload
    )
