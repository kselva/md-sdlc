"""
status - one screen with the whole project status (0.4.0).

Reads core.overview: what is done, in progress, waiting for check or for a
decision, on site, stuck, and what is next (ideas, parked). With an id it
shows that item, everything under it and its open items.
"""
import argparse
import json
import sys

from core.overview import build_overview, render_markdown
from core.repo import AiDocsRepo
from plugins.base_plugin import BaseCommand


class Command(BaseCommand):
    name = "status"
    description = "Show the project status on one screen (or one item with --json for tools)"

    def register_args(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("id", nargs="?", default=None, help="Limit to this item and everything under it")
        parser.add_argument("--json", action="store_true", help="Emit the status as JSON")

    def run(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        if args.id and repo.find(args.id) is None:
            print(f"ERROR: '{args.id}' not found")
            sys.exit(1)
        overview = build_overview(repo, scope_id=args.id)
        text = json.dumps(overview, indent=2, default=str) if args.json else render_markdown(overview)
        # stdout may be a non-UTF-8 console codepage on Windows
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
