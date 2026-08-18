"""
backlog - regenerate the root Epic-level rollup, or a single Epic's
Story+Task rollup. Always fully overwritten - this is a generated
artifact, never a source file (design doc section 4.5).
"""
import argparse
import datetime

from core.repo import AiDocsRepo
from core.version import __version__
from plugins.base_plugin import BaseCommand


class Command(BaseCommand):
    name = "backlog"
    description = "Regenerate backlog.md (root Epic-level, or --epic for Story+Task level)"

    def register_args(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--epic", default=None, help="Regenerate this Epic's own backlog.md instead of root")

    def run(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        items = repo.all_files()
        if args.epic:
            self._write_epic_backlog(repo, items, args.epic)
        else:
            self._write_root_backlog(repo, items)

    def _write_root_backlog(self, repo: AiDocsRepo, items: list) -> None:
        epics = [i for i in items if i.type == "epic"]
        lines = [
            "# Backlog — Epic Overview",
            "",
            f"_Generated {datetime.date.today().isoformat()} by md_sdlc {__version__} — do not hand-edit, run `md_sdlc backlog` to refresh._",
            "",
            "| Epic | Status | Stories (done/total) | Owner |",
            "|---|---|---|---|",
        ]
        for epic in sorted(epics, key=lambda e: e.id):
            stories = [i for i in items if i.type == "story" and i.parent == epic.id]
            done = sum(1 for s in stories if s.status == "done")
            lines.append(f"| {epic.id} | {epic.status} | {done}/{len(stories)} | {epic.owner or '-'} |")

        out_path = repo.root / "backlog.md"
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Wrote {out_path.relative_to(repo.root)} ({len(epics)} epic(s))")

    def _write_epic_backlog(self, repo: AiDocsRepo, items: list, epic_id: str) -> None:
        epic = repo.find(epic_id)
        if epic is None or epic.type != "epic":
            print(f"ERROR: '{epic_id}' is not a known epic")
            return

        stories = sorted([i for i in items if i.type == "story" and i.parent == epic_id], key=lambda s: s.id)
        lines = [
            f"# Backlog — {epic_id}",
            "",
            f"_Generated {datetime.date.today().isoformat()} by md_sdlc {__version__} — do not hand-edit._",
            "",
            "## Stories",
            "",
            "| Story | Status | Owner | Tasks (done/total) |",
            "|---|---|---|---|",
        ]
        task_lines = ["", "## Tasks", "", "| Task | Story | Status | Owner |", "|---|---|---|---|"]

        for story in stories:
            file_tasks = [i for i in items if i.type == "task" and i.parent == story.id]
            row_tasks = repo.task_rows(story.id)
            total = len(file_tasks) + len(row_tasks)
            done = sum(1 for t in file_tasks if t.status == "done") + sum(1 for t in row_tasks if t.status == "done")
            lines.append(f"| {story.id} | {story.status} | {story.owner or '-'} | {done}/{total} |")

            for t in file_tasks:
                task_lines.append(f"| {t.id} | {story.id} | {t.status} | {t.owner or '-'} |")
            for r in row_tasks:
                task_lines.append(f"| {r.id} | {story.id} | {r.status} | {r.owner or '-'} |")

        lines.extend(task_lines)

        out_path = epic.path.parent / "backlog.md"
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Wrote {out_path.relative_to(repo.root)} ({len(stories)} stor(y/ies))")
