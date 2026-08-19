"""
review - report or resolve a review finding on a Story.

Answers the two-agent handoff: one agent designs/codes a Story, a second
agent reviews it and needs somewhere to write findings that the first agent
then reads and fixes. review.md is a sibling to tasks.md (same row-table
convention, see core/vocab.py REVIEW_ROW_COLUMNS/REVIEW_ROW_STATUSES) -
kept separate from tasks.md because a finding is feedback on work already
done, not work that was planned.

Two subcommands:
  report  - reviewer adds a new finding row (status: open)
  resolve - author marks a finding fixed/wontfix after addressing it
"""
import argparse
import datetime
import sys

from core.repo import AiDocsRepo
from core.vocab import REVIEW_SEVERITIES, is_valid_review_status
from plugins.base_plugin import BaseCommand

_HEADER = "# Review Findings\n\n| id | severity | status | summary | reported_by | updated |\n|----|----------|--------|---------|--------------|---------|\n"


class Command(BaseCommand):
    name = "review"
    description = "Report a review finding on a Story, or mark one resolved"

    def register_args(self, parser: argparse.ArgumentParser) -> None:
        sub = parser.add_subparsers(dest="review_action", required=True)

        report = sub.add_parser("report", help="Add a new finding to a Story's review.md")
        report.add_argument("--story", required=True, help="Story id the finding is against")
        report.add_argument("--summary", required=True, help="Short description of the finding")
        report.add_argument("--severity", default="medium", choices=sorted(REVIEW_SEVERITIES))
        report.add_argument("--reported-by", required=True, help="Reviewer identity, e.g. agent-2")

        resolve = sub.add_parser("resolve", help="Mark a finding fixed or wontfix")
        resolve.add_argument("id", help="Finding id, e.g. RVW-01")
        resolve.add_argument("--story", required=True, help="Story id the finding belongs to")
        resolve.add_argument("--status", required=True, choices=["fixed", "wontfix", "changes-requested"])

    def run(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        if args.review_action == "report":
            self._report(repo, args)
        elif args.review_action == "resolve":
            self._resolve(repo, args)

    def _report(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        story = repo.find(args.story)
        if story is None or story.type != "story":
            print(f"ERROR: '{args.story}' is not a known story")
            sys.exit(1)

        seq = repo.next_review_sequence(args.story)
        finding_id = f"RVW-{seq:02d}"
        review_md = story.path.parent / "review.md"

        if not review_md.exists():
            review_md.write_text(_HEADER, encoding="utf-8")

        row = f"| {finding_id} | {args.severity} | open | {args.summary} | {args.reported_by} | {datetime.date.today().isoformat()} |\n"
        with open(review_md, "a", encoding="utf-8") as f:
            f.write(row)

        print(f"Reported {finding_id} on {args.story} -> {review_md.relative_to(repo.root)}")

    def _resolve(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        if not is_valid_review_status(args.status):
            print(f"ERROR: invalid status '{args.status}'")
            sys.exit(1)

        rows = repo.review_rows(args.story)
        row = next((r for r in rows if r.id == args.id), None)
        if row is None:
            print(f"ERROR: finding '{args.id}' not found in {args.story}/review.md")
            sys.exit(1)

        story = repo.find(args.story)
        review_md = story.path.parent / "review.md"
        text = review_md.read_text(encoding="utf-8")
        lines = text.splitlines()
        out = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(f"| {row.id} |") or stripped.startswith(f"|{row.id}|"):
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                cells[2] = args.status
                cells[5] = datetime.date.today().isoformat()
                out.append("| " + " | ".join(cells) + " |")
            else:
                out.append(line)
        review_md.write_text("\n".join(out) + "\n", encoding="utf-8")

        print(f"{args.id} on {args.story} -> {args.status}")
