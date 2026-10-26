"""
adopt - put a header on an existing file in place, no move (0.4.0).

For plan files written before the project used md-sdlc. The body is kept
as is; the header records adopted: <date>, which also exempts the file from
the short-layout rule that a file name starts with its id.
"""
import argparse
import sys
from pathlib import Path

from core.repo import AiDocsRepo, today_date
from core.vocab import TYPE_KIND, is_valid_status
from plugins.base_plugin import BaseCommand


class Command(BaseCommand):
    name = "adopt"
    description = "Add a header to an existing file in place, so the tool tracks it"

    def register_args(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("file", help="Path to the file (relative to here or absolute)")
        parser.add_argument("--type", required=True, choices=sorted(TYPE_KIND.keys()))
        parser.add_argument("--id", required=True, help="Id to give it")
        parser.add_argument("--parent", default=None)
        parser.add_argument("--status", default=None, help="Default: in-progress (work item) / current (artifact)")
        parser.add_argument("--title", default=None)

    def run(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        path = Path(args.file).resolve()
        if not path.is_file() or path.suffix != ".md":
            self._fail(f"'{args.file}' is not a .md file")
        try:
            path.relative_to(repo.root.resolve())
        except ValueError:
            self._fail(f"'{args.file}' is outside the project folder {repo.root}")
        if repo.find(args.id) is not None:
            self._fail(f"id '{args.id}' is already used by {repo.find(args.id).path.name}")
        if args.parent and repo.find(args.parent) is None:
            self._fail(f"parent '{args.parent}' not found")

        kind = TYPE_KIND[args.type]
        status = args.status or ("in-progress" if kind == "work-item" else "current")
        if not is_valid_status(args.type, status):
            self._fail(f"'{status}' is not a valid status for type '{args.type}'")

        meta = {"id": args.id, "type": args.type, "kind": kind, "status": status}
        if args.parent:
            meta["parent"] = args.parent
        if args.title:
            meta["title"] = args.title
        meta["updated"] = today_date()
        meta["adopted"] = today_date()
        try:
            repo.add_header(path, meta)
        except ValueError as exc:
            self._fail(str(exc))
        print(f"Adopted {path.name} as {args.id} ({args.type}, {status}) - file not moved")

    @staticmethod
    def _fail(message: str) -> None:
        print(f"ERROR: {message}")
        sys.exit(1)
