"""
stats - status statistics for the whole project, or drilled into one Epic.

`query` answers "list the items matching this one filter". `stats` answers
"what's the status spread" - a type x status matrix project-wide, the same
scoped to an Epic's Stories/Tasks, or counts grouped by owner / stability /
scenario. Read-only, prints to stdout, writes nothing.
"""
import argparse
import datetime
import json
import sys

from core.repo import AiDocsRepo
from core.version import __version__
from core.vocab import (
    REVIEW_SEVERITY_ORDER,
    STABILITY_ORDER,
    WORK_ITEM_STATUS_ORDER,
)
from plugins.base_plugin import BaseCommand

_WORK_ITEM_TYPE_ORDER = ("proposal", "epic", "story", "task", "adhoc")
_UNRESOLVED = ("open", "changes-requested")
_BY_FIELDS = ("owner", "stability", "scenario")


class Command(BaseCommand):
    name = "stats"
    description = "Status statistics - project-wide, per Epic (--epic), or grouped (--by owner|stability|scenario)"

    def register_args(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--epic", default=None, help="Drill into one Epic's Stories and Tasks")
        parser.add_argument("--by", default=None, choices=_BY_FIELDS, help="Group counts by this field instead of by type")
        parser.add_argument("--json", action="store_true", help="Emit the numbers as JSON instead of a table")

    def run(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        items = repo.all_files()
        work_items = [i for i in items if i.kind == "work-item"]

        if args.epic:
            payload = self._epic_payload(repo, items, args.epic)
            if payload is None:
                sys.exit(1)
        elif args.by:
            payload = self._grouped_payload(work_items, args.by)
        else:
            payload = self._project_payload(repo, work_items)

        project_name = getattr(getattr(repo, "project", None), "name", None) or repo.root.name
        payload = {"project": project_name, "generated": datetime.date.today().isoformat(), **payload}

        text = payload.pop("_text")
        if args.json:
            self._emit(json.dumps(payload, indent=2))
        else:
            self._emit(text)

    # -- payload builders ------------------------------------------------

    def _project_payload(self, repo: AiDocsRepo, work_items: list) -> dict:
        by_type: dict[str, dict] = {}
        present: set[str] = set()
        for t in _WORK_ITEM_TYPE_ORDER:
            group = [i for i in work_items if i.type == t]
            if not group:
                continue
            tally = _tally(i.status for i in group)
            by_type[t] = {"total": len(group), **tally}
            present.update(tally)

        # Tasks that live as tasks.md rows, not files - fold them into "task".
        row_statuses: list[str] = []
        for story in (i for i in work_items if i.type == "story"):
            row_statuses.extend(r.status for r in repo.task_rows(story.id))
        if row_statuses:
            row_tally = _tally(row_statuses)
            tgt = by_type.setdefault("task", {"total": 0})
            tgt["total"] += len(row_statuses)
            for k, v in row_tally.items():
                tgt[k] = tgt.get(k, 0) + v
            present.update(row_tally)

        cols = [s for s in WORK_ITEM_STATUS_ORDER if s in present]
        rows = [
            (t, by_type[t]["total"], [by_type[t].get(c, 0) for c in cols])
            for t in _WORK_ITEM_TYPE_ORDER if t in by_type
        ]

        stability = _stability_tally(i for i in work_items if i.type in ("epic", "story"))
        findings = _open_findings_tally(repo, work_items)

        text = _render_matrix("TYPE", cols, rows)
        text += "\n\nSTABILITY (epics + stories)   " + "   ".join(
            f"{k} {stability[k]}" for k in (*STABILITY_ORDER, "unset") if stability.get(k)
        )
        if any(findings.values()):
            text += "\n\nREVIEW FINDINGS (open)   " + "   ".join(
                f"{k} {findings[k]}" for k in REVIEW_SEVERITY_ORDER
            )

        return {"by_type": by_type, "stability": stability, "review_findings_open": findings, "_text": text}

    def _epic_payload(self, repo: AiDocsRepo, items: list, epic_id: str) -> dict | None:
        epic = repo.find(epic_id)
        if epic is None or epic.type != "epic":
            print(f"ERROR: '{epic_id}' is not a known epic")
            return None

        stories = sorted(
            (i for i in items if i.type == "story" and i.parent == epic_id),
            key=lambda s: s.id,
        )

        story_tally = _tally(s.status for s in stories)

        task_statuses: list[str] = []
        per_story_tasks: dict[str, tuple[int, int]] = {}
        for s in stories:
            file_tasks = [i for i in items if i.type == "task" and i.parent == s.id]
            row_tasks = repo.task_rows(s.id)
            statuses = [t.status for t in file_tasks] + [r.status for r in row_tasks]
            task_statuses.extend(statuses)
            done = sum(1 for st in statuses if st == "done")
            per_story_tasks[s.id] = (done, len(statuses))
        task_tally = _tally(task_statuses)

        story_cols = [s for s in WORK_ITEM_STATUS_ORDER if s in story_tally]
        task_cols = [s for s in WORK_ITEM_STATUS_ORDER if s in task_tally]

        lines = [
            f"{epic.id} - {epic.status}   (owner: {epic.owner or '-'}, stability: {epic.stability or 'unset'})",
            "",
            "  STORIES ({}){}".format(len(stories), _inline_counts(story_cols, story_tally)),
            "  TASKS  ({}){}".format(sum(t for _, t in per_story_tasks.values()), _inline_counts(task_cols, task_tally)),
        ]
        if stories:
            lines += ["", _story_table(stories, per_story_tasks)]

        return {
            "epic": {"id": epic.id, "status": epic.status, "stability": epic.stability},
            "stories": {"total": len(stories), **story_tally},
            "tasks": {"total": len(task_statuses), **task_tally},
            "_text": "\n".join(lines),
        }

    def _grouped_payload(self, work_items: list, field: str) -> dict:
        if field == "stability":
            work_items = [i for i in work_items if i.type in ("epic", "story")]

        def key_of(i) -> str:
            v = getattr(i, field, None)
            return v if v else ("unset" if field == "stability" else "unassigned" if field == "owner" else "none")

        groups: dict[str, list] = {}
        present: set[str] = set()
        for i in work_items:
            groups.setdefault(key_of(i), []).append(i)

        tallies = {k: _tally(i.status for i in v) for k, v in groups.items()}
        for t in tallies.values():
            present.update(t)
        cols = [s for s in WORK_ITEM_STATUS_ORDER if s in present]

        rows = [
            (k, len(groups[k]), [tallies[k].get(c, 0) for c in cols])
            for k in sorted(groups, key=lambda k: (-len(groups[k]), k))
        ]
        text = _render_matrix(field.upper(), cols, rows)
        return {"by": field, "groups": {k: {"total": len(groups[k]), **tallies[k]} for k in groups}, "_text": text}

    # -- output -------------------------------------------------------

    @staticmethod
    def _emit(text: str) -> None:
        # stdout may be a non-UTF-8 console codepage on Windows
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")


# -- module helpers ---------------------------------------------------

def _tally(statuses) -> dict[str, int]:
    out: dict[str, int] = {}
    for s in statuses:
        out[s] = out.get(s, 0) + 1
    return out


def _stability_tally(items) -> dict[str, int]:
    out = {k: 0 for k in (*STABILITY_ORDER, "unset")}
    for i in items:
        out[i.stability if i.stability in out else "unset"] += 1
    return out


def _open_findings_tally(repo: AiDocsRepo, work_items: list) -> dict[str, int]:
    out = {k: 0 for k in REVIEW_SEVERITY_ORDER}
    for story in (i for i in work_items if i.type == "story"):
        for r in repo.review_rows(story.id):
            if r.status in _UNRESOLVED and r.severity in out:
                out[r.severity] += 1
    return out


def _inline_counts(cols: list[str], tally: dict[str, int]) -> str:
    if not cols:
        return "   (none)"
    return "   " + "  ".join(f"{c} {tally.get(c, 0)}" for c in cols)


def _render_matrix(first_header: str, cols: list[str], rows: list[tuple[str, int, list[int]]]) -> str:
    headers = [first_header, "TOTAL", *cols]
    table = [headers] + [[name, str(total), *[str(n) if n else "-" for n in cells]] for name, total, cells in rows]
    widths = [max(len(r[c]) for r in table) for c in range(len(headers))]
    out = []
    for ri, row in enumerate(table):
        cells = [row[0].ljust(widths[0])] + [row[c].rjust(widths[c]) for c in range(1, len(headers))]
        out.append("  ".join(cells).rstrip())
        if ri == 0:
            out.append("  ".join("-" * widths[c] for c in range(len(headers))))
    return "\n".join(out)


def _story_table(stories: list, per_story_tasks: dict[str, tuple[int, int]]) -> str:
    table = [["Story", "Status", "Stability", "Tasks (done/total)"]]
    for s in stories:
        done, total = per_story_tasks.get(s.id, (0, 0))
        table.append([s.id, s.status, s.stability or "-", f"{done}/{total}"])
    widths = [max(len(r[c]) for r in table) for c in range(4)]
    out = []
    for ri, row in enumerate(table):
        out.append("  " + "  ".join(row[c].ljust(widths[c]) for c in range(4)).rstrip())
        if ri == 0:
            out.append("  " + "  ".join("-" * widths[c] for c in range(4)))
    return "\n".join(out)
