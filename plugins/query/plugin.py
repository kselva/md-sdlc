"""
query - filtered counts and listings. Answers the "how many open/pending/
done", "MVP remaining", and staleness questions from the design doc without
needing to open every file (section 3, section 10.4 #3).
"""
import argparse
import datetime
import sys

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
        parser.add_argument("--story", default=None, help="Story id to scope --unresolved-reviews to (omit for a project-wide sweep)")
        parser.add_argument(
            "--unresolved-reviews", action="store_true",
            help="List open / changes-requested review.md findings - for one --story, or project-wide if --story is omitted",
        )
        parser.add_argument(
            "--active", action="store_true",
            help="List in-progress / in-review Stories with branch + touches globs (collision check)",
        )

    def run(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        if args.unresolved_reviews:
            self._unresolved_reviews(repo, args)
            return

        if args.active:
            self._active_stories(repo)
            return

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

    def _active_stories(self, repo: AiDocsRepo) -> None:
        """One line per in-progress / in-review Story: id | owner | branch |
        touches globs. Run before handing out a new Story to eyeball overlap
        (PROPOSAL-0.3.0 section 3.3)."""
        stories = [
            i for i in repo.all_files()
            if i.type == "story" and i.status in ("in-progress", "in-review")
        ]
        if not stories:
            print("No active stories (none in-progress or in-review).")
            return

        print(f"{len(stories)} active story(ies):\n")
        print("| ID | Owner | Branch | Touches |")
        print("|---|---|---|---|")
        for s in sorted(stories, key=lambda x: x.id):
            touches = "; ".join(s.touches) if s.touches else "-"
            print(f"| {s.id} | {s.owner or '-'} | feat/{s.id} | {touches} |")

    _UNRESOLVED = ("open", "changes-requested")

    def _unresolved_reviews(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        if args.story:
            self._unresolved_reviews_one(repo, args.story)
        else:
            self._unresolved_reviews_all(repo)

    def _unresolved_reviews_one(self, repo: AiDocsRepo, story_id: str) -> None:
        story = repo.find(story_id)
        if story is None or story.type != "story":
            print(f"ERROR: '{story_id}' is not a known story")
            sys.exit(1)

        rows = [r for r in repo.review_rows(story_id) if r.status in self._UNRESOLVED]

        if not rows:
            print(f"No unresolved review findings for {story_id}.")
            return

        print(f"{len(rows)} unresolved finding(s) on {story_id}:\n")
        print("| id | severity | status | summary | reported_by | updated |")
        print("|----|----------|--------|---------|--------------|---------|")
        for r in rows:
            print(f"| {r.id} | {r.severity or '-'} | {r.status} | {r.summary} | {r.reported_by or '-'} | {r.updated or '-'} |")

    def _unresolved_reviews_all(self, repo: AiDocsRepo) -> None:
        """Project-wide sweep: every Story's review.md, open / changes-requested
        findings only, one table with a story column."""
        stories = sorted(
            (i for i in repo.all_files() if i.type == "story"),
            key=lambda s: s.id,
        )
        hits: list[tuple[str, object]] = []
        for story in stories:
            for r in repo.review_rows(story.id):
                if r.status in self._UNRESOLVED:
                    hits.append((story.id, r))

        if not hits:
            print("No unresolved review findings in the project.")
            return

        n_stories = len({sid for sid, _ in hits})
        print(f"{len(hits)} unresolved finding(s) across {n_stories} story(ies):\n")
        print("| story | id | severity | status | summary | reported_by | updated |")
        print("|-------|----|----------|--------|---------|--------------|---------|")
        for sid, r in hits:
            print(
                f"| {sid} | {r.id} | {r.severity or '-'} | {r.status} | {r.summary} | "
                f"{r.reported_by or '-'} | {r.updated or '-'} |"
            )
