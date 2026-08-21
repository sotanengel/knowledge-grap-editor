"""Command line entry point.

``ontoforge serve`` is what the container runs (§12.1). It binds to loopback by
default; exposing the instance to a LAN is a deliberate act, and one that should
be paired with ``ONTOFORGE_AUTH_TOKEN`` (§13).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from ontoforge import __version__
from ontoforge.config import Settings, load_settings

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ontoforge", description="OntoForge")
    parser.add_argument("--version", action="version", version=__version__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    serve = subcommands.add_parser("serve", help="run the API and the web UI")
    serve.add_argument("--host", default=DEFAULT_HOST, help="interface to bind (default loopback)")
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.add_argument("--reload", action="store_true", help="reload on source changes")

    subcommands.add_parser("info", help="print the resolved configuration")
    subcommands.add_parser(
        "mcp-stdio", help="run the read-only MCP server over stdio for a local AI client"
    )

    load = subcommands.add_parser("load-vocab", help="load bundled vocabularies into the store")
    load.add_argument("names", nargs="*", help="vocabulary names (default: the usual set)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)

    if arguments.command == "info":
        settings = load_settings()
        for field in Settings.model_fields:
            value = "<set>" if field == "auth_token" and settings.auth_token else None
            print(f"{field}: {value or getattr(settings, field)}")
        return 0

    if arguments.command == "mcp-stdio":
        from ontoforge.mcp.server import run_stdio

        run_stdio(load_settings())
        return 0

    if arguments.command == "load-vocab":
        from ontoforge.runtime import Runtime
        from ontoforge.vocab import loader

        with Runtime.create(load_settings()) as runtime:
            names = arguments.names or list(loader.DEFAULT_VOCABULARIES)
            for name, count in loader.load(runtime.store, names).items():
                print(f"{name}: {count} triples")
        return 0

    import uvicorn

    uvicorn.run(
        "ontoforge.api.app:create_app",
        factory=True,
        host=arguments.host,
        port=arguments.port,
        reload=arguments.reload,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
