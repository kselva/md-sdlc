"""
item - add or change open-item rows in an epic/story tasks.md (0.4.0).

    item add PAY1-A "check retry on slow network" [--waits site] [--experiment]
    item set PAY1-A.3 done
    item set PAY1-A.3 --waits ""            (wait is over)
    item set PAY1-A.4 --verdict yes --result "kept the 2 s timeout"

Row ids are <parent>.<n>. The file's own columns are kept when writing back;
a column the table lacks (e.g. waits in a classic table) is an error, not
silently dropped.
"""
import argparse
import sys

from core.layout import next_row_id, row_parent_id
from core.repo import AiDocsRepo, today
from core.vocab import WORK_ITEM_STATUSES, is_valid_verdict
from plugins.base_plugin import BaseCommand


class Command(BaseCommand):
    name = "item"
    description = "Add or change open-item rows in an epic/story tasks.md"

    def register_args(self, parser: argparse.ArgumentParser) -> None:
        sub = parser.add_subparsers(dest="action", required=True)

        add = sub.add_parser("add", help="Add a row")
        add.add_argument("parent", help="Epic or story id that owns the tasks.md")
        add.add_argument("text", help="One-line summary")
        add.add_argument("--status", default="not-started")
        add.add_argument("--waits", default=None, help="Who or what the row waits on")
        add.add_argument("--experiment", action="store_true", help="A small experiment: adds verdict 'open'")

        upd = sub.add_parser("set", help="Change a row")
        upd.add_argument("row_id", help="Row id, e.g. PAY1-A.3")
        upd.add_argument("status", nargs="?", default=None)
        upd.add_argument("--waits", default=None, help="'' clears it")
        upd.add_argument("--verdict", default=None, help="open / yes / no / partly")
        upd.add_argument("--result", default=None, help="Appended to the summary as 'result: ...'")
        upd.add_argument("--parent", default=None, help="Owner id, when the row id is not <parent>.<n>")

    def run(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        if args.action == "add":
            self._add(repo, args)
        else:
            self._set(repo, args)

    @staticmethod
    def _fail(message: str) -> None:
        print(f"ERROR: {message}")
        sys.exit(1)

    def _owner(self, repo: AiDocsRepo, owner_id: str):
        owner = repo.find(owner_id)
        if owner is None:
            self._fail(f"'{owner_id}' not found")
        if not owner.is_folder_item:
            self._fail(f"'{owner_id}' is a single file - open items live in an epic/story folder's tasks.md")
        return owner

    def _check_status(self, status: str | None) -> None:
        if status is not None and status not in WORK_ITEM_STATUSES:
            self._fail(f"'{status}' is not a row status ({', '.join(sorted(WORK_ITEM_STATUSES))})")

    def _check_columns(self, columns: list[str], values: dict, path_hint: str) -> None:
        missing = [k for k, v in values.items() if v and k not in columns]
        if missing:
            self._fail(f"{path_hint} has no '{', '.join(missing)}' column - add it to the table header first")

    def _add(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        owner = self._owner(repo, args.parent)
        self._check_status(args.status)
        columns, rows = repo.raw_rows(owner)
        row = {
            "id": next_row_id(owner.id, [r["id"] for r in rows]),
            "status": args.status, "updated": today(), "summary": args.text.strip(),
        }
        extras = {"waits": args.waits or "", "verdict": "open" if args.experiment else ""}
        self._check_columns(columns, extras, f"{owner.id}/tasks.md")
        row.update({k: v for k, v in extras.items() if k in columns})
        repo.write_rows(owner, rows + [row], columns)
        repo.update_header(owner, {})
        print(f"Added {row['id']} to {owner.id}: {row['summary']}")

    def _set(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        owner_id = args.parent or row_parent_id(args.row_id)
        if owner_id is None:
            self._fail(f"cannot tell the owner of '{args.row_id}' - pass --parent")
        owner = self._owner(repo, owner_id)
        self._check_status(args.status)
        if args.verdict and not is_valid_verdict(args.verdict):
            self._fail(f"verdict must be open, yes, no or partly - got '{args.verdict}'")
        if all(v is None for v in (args.status, args.waits, args.verdict, args.result)):
            self._fail("nothing to change - give a status, --waits, --verdict or --result")

        columns, rows = repo.raw_rows(owner)
        row = next((r for r in rows if r["id"] == args.row_id), None)
        if row is None:
            self._fail(f"row '{args.row_id}' not found in {owner.id}/tasks.md")
        self._check_columns(columns, {"waits": args.waits, "verdict": args.verdict}, f"{owner.id}/tasks.md")

        if args.status is not None:
            row["status"] = args.status
        if args.waits is not None:
            row["waits"] = args.waits
        if args.verdict is not None:
            row["verdict"] = args.verdict
        if args.result:
            row["summary"] = f"{row.get('summary', '')} - result: {args.result.strip()}".strip(" -")
        row["updated"] = today()
        repo.write_rows(owner, rows, columns)
        repo.update_header(owner, {})
        print(f"Updated {args.row_id}: {row['status']}" + (f", waits {row['waits']}" if row.get("waits") else ""))
