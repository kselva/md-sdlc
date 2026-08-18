"""
query - filtered counts and listings. Answers the "how many open/pending/
done", "MVP remaining", and staleness questions from the design doc without
needing to open every file (section 3, section 10.4 #3).
"""
import argparse
import datetime

from core.repo import AiDocsRepo
from plugins.base_plugin import BaseCommand


class Command(BaseCommand):
    name = "query"
    description = "Filter and count work-items by type/status/owner/scenario/staleness"

    def register_args(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--type", default=None)
        parser.add_argument("--status", default=None)
        parser.add_argument("--owner", default=None)
        parser.add_argument("--scenario", default=None)
        parser.add_argument("--stale-days", type=int, default=None, help="Only items not updated in N+ days")
        parser.add_argument("--mvp-remaining", action="store_true", help="Shorthand: type=epic, mvp=true, status!=done")

    def run(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        items = repo.all_files()

        if args.mvp_remaining:
            items = [i for i in items if i.type == "epic" and i.mvp and i.status != "done"]
        else:
            if args.type:
                items = [i for i in items if i.type == args.type]
            if args.status:
                items = [i for i in items if i.status == args.status]
            if args.owner:
                items = [i for i in items if i.owner == args.owner]
            if args.scenario:
                items = [i for i in items if i.scenario == args.scenario]
            if args.stale_days is not None:
                cutoff = datetime.date.today() - datetime.timedelta(days=args.stale_days)
                items = [i for i in items if i.updated and self._parse_date(i.updated) and self._parse_date(i.updated) <= cutoff]

        if not items:
            print("No matching items.")
            return

        print(f"{len(items)} matching item(s):\n")
        print("| ID | Type | Status | Owner | Updated |")
        print("|---|---|---|---|---|")
        for i in sorted(items, key=lambda x: x.id):
            print(f"| {i.id} | {i.type} | {i.status} | {i.owner or '-'} | {i.updated or '-'} |")

    @staticmethod
    def _parse_date(value: str):
        try:
            return datetime.date.fromisoformat(value)
        except (ValueError, TypeError):
            return None
