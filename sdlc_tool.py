"""
SDLC Tool - CLI entry point.

Discovers all command plugins and dispatches to them. Adding a new plugin
requires no changes to this file.

Project targeting is git-style: run from inside (or under) a project's
ai-docs/ folder and the tool walks up looking for .sdlc/config.yml. Run
`init` first inside a new project's ai-docs/ folder.

Usage:
    python sdlc_tool.py init --name "My Project" --prefix MP
    python sdlc_tool.py validate
    python sdlc_tool.py backlog [--epic EPIC-xx]
    python sdlc_tool.py query --type task --status in-progress
    python sdlc_tool.py new task --parent STORY-01-xxx --title "..."
    python sdlc_tool.py promote TASK-ROW-07 --to-file
    python sdlc_tool.py archive EPIC-01-checkout-redesign
"""
import argparse
import logging
import sys

from core.profile import NotInitializedError, resolve_project
from core.repo import AiDocsRepo
from core.version import __version__
from plugins import load_plugins

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

_NO_PROJECT_REQUIRED = {"init", "conventions"}


def build_parser(commands: dict) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="md_sdlc",
        description="SDLC tracking CLI for ai-docs. Supports: " + ", ".join(commands.keys()),
    )
    parser.add_argument("--version", action="version", version=f"md_sdlc {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, command in commands.items():
        cmd_parser = sub.add_parser(name, help=command.description)
        command.register_args(cmd_parser)

    return parser


def main() -> None:
    commands = load_plugins()

    if not commands:
        logger.error("No commands found. Check plugins/ directory.")
        sys.exit(1)

    parser = build_parser(commands)
    args = parser.parse_args()

    command = commands.get(args.command)
    if command is None:
        parser.print_help()
        sys.exit(1)

    if args.command in _NO_PROJECT_REQUIRED:
        command.run(None, args)
        return

    try:
        project = resolve_project()
    except NotInitializedError as exc:
        logger.error(str(exc))
        sys.exit(1)

    repo = AiDocsRepo(project.root, project)
    command.run(repo, args)


if __name__ == "__main__":
    main()
