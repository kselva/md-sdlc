"""
Overview (0.4.0) - the project status as plain data.

build_overview() returns a dict; render_markdown() turns it into the text
shown by `status` and written by `backlog` in short layout; `status --json`
dumps the same dict. A later UI reads this dict too - one copy of the rules.

Items under hist/ are left out (archived), but still resolve as links.
"""
import datetime

from core.version import __version__
from core.vocab import TERMINAL_STATUSES, WORK_ITEM_STATUS_ORDER

OPEN_STATUSES = {"in-progress", "in-review", "blocked"}
RECENT_LIMIT = 10
_PLAN_TYPES = ("epic", "story", "task", "adhoc", "experiment")


def _days_since(date_text: str | None, today: datetime.date) -> int | None:
    try:
        return (today - datetime.date.fromisoformat(str(date_text)[:10])).days
    except (TypeError, ValueError):
        return None


def _item_entry(item) -> dict:
    return {
        "id": item.id, "type": item.type, "status": item.status, "title": item.display_title,
        "parent": item.parent, "scenario": item.scenario, "next": item.next,
        "waits_on": item.waits_on, "deployed": item.deployed, "updated": item.updated,
        "path": item.path.as_posix(),
    }


def _row_entry(row, parent) -> dict:
    return {
        "id": row.id, "type": "row", "status": row.status, "title": row.summary,
        "parent": parent.id, "waits_on": row.waits, "verdict": row.verdict, "updated": row.updated,
    }


def build_overview(repo, today: datetime.date | None = None, scope_id: str | None = None) -> dict:
    today = today or datetime.date.today()
    project = repo.project
    decision_waits = getattr(project, "decision_waits", "owner")
    stale_days = getattr(project, "stale_days", 14)

    items = [i for i in repo.all_files() if i.kind == "work-item" and not repo.is_archived(i)]
    if scope_id is not None:
        items = _scope(items, scope_id)

    rows = []
    for item in items:
        if item.type in ("epic", "story"):
            rows += [_row_entry(r, item) for r in repo.task_rows(item.id)]
    open_rows = [r for r in rows if r["status"] not in TERMINAL_STATUSES]

    plan_items = [i for i in items if i.type in _PLAN_TYPES]
    counts = {s: 0 for s in WORK_ITEM_STATUS_ORDER}
    for i in plan_items:
        if i.status in counts:
            counts[i.status] += 1
    steps = [i for i in items if i.type == "story"]

    tracks = []
    for epic in sorted((i for i in items if i.type == "epic" and i.status != "parked"
                        and i.status not in TERMINAL_STATUSES), key=lambda e: e.id):
        epic_steps = [s for s in steps if s.parent == epic.id]
        step_ids = {epic.id} | {s.id for s in epic_steps}
        entry = _item_entry(epic)
        entry.update({
            "steps_done": sum(1 for s in epic_steps if s.status == "done"),
            "steps_total": len(epic_steps),
            "open_items": sum(1 for r in open_rows if r["parent"] in step_ids),
            "steps": [_item_entry(s) for s in sorted(epic_steps, key=lambda s: s.id)],
        })
        tracks.append(entry)

    live_items = [i for i in items if i.status not in TERMINAL_STATUSES and i.status != "parked"]
    waiting = [i for i in live_items if i.waits_on]
    waiting_rows = [r for r in open_rows if r["waits_on"]]

    stale = []
    for i in live_items:
        age = _days_since(i.updated, today)
        if i.status in OPEN_STATUSES and age is not None and age > stale_days:
            stale.append({**_item_entry(i), "days": age})

    dated = [_item_entry(i) for i in items] + rows
    recent = sorted((d for d in dated if d.get("updated")), key=lambda d: str(d["updated"]), reverse=True)

    experiments = [
        {**_item_entry(i), "question": i.question, "result": i.result, "verdict": i.verdict or "open"}
        for i in items if i.type == "experiment"
    ] + [r for r in rows if r.get("verdict")]

    return {
        "generated": today.isoformat(),
        "tool_version": __version__,
        "project": getattr(project, "name", None),
        "scope": scope_id,
        "summary": {
            "by_status": counts,
            "tracks_open": len(tracks),
            "steps_done": sum(1 for s in steps if s.status == "done"),
            "steps_total": len(steps),
            "rows_open": len(open_rows),
            "rows_done": sum(1 for r in rows if r["status"] == "done"),
            "ideas": sum(1 for i in items if i.type == "proposal" and i.status not in TERMINAL_STATUSES),
            "parked": sum(1 for i in items if i.status == "parked"),
        },
        "tracks": tracks,
        "on_site": sorted((_item_entry(i) for i in items if i.deployed),
                          key=lambda d: str(d["deployed"]), reverse=True),
        "waiting_check": [_item_entry(i) for i in live_items if i.status == "in-review"]
                         + [r for r in open_rows if r["status"] == "in-review"],
        "blocked": [_item_entry(i) for i in live_items if i.status == "blocked"]
                   + [r for r in open_rows if r["status"] == "blocked"],
        "decisions": [_item_entry(i) for i in waiting if i.waits_on == decision_waits]
                     + [r for r in waiting_rows if r["waits_on"] == decision_waits],
        "waiting_others": [_item_entry(i) for i in waiting if i.waits_on != decision_waits]
                          + [r for r in waiting_rows if r["waits_on"] != decision_waits],
        "experiments": experiments,
        "recent": recent[:RECENT_LIMIT],
        "stale": sorted(stale, key=lambda d: -d["days"]),
        "stale_days": stale_days,
        "ideas": [_item_entry(i) for i in items if i.type == "proposal" and i.status not in TERMINAL_STATUSES],
        "parked": [_item_entry(i) for i in items if i.status == "parked"],
        "rows": rows if scope_id is not None else [],
    }


def _scope(items: list, scope_id: str) -> list:
    """The item and everything under it."""
    keep = {scope_id}
    changed = True
    while changed:
        changed = False
        for i in items:
            if i.parent in keep and i.id not in keep:
                keep.add(i.id)
                changed = True
    return [i for i in items if i.id in keep]


# -- rendering --------------------------------------------------------------

def _cell(value) -> str:
    return "-" if value in (None, "") else str(value).replace("|", "\\|").replace("\n", " ")


def _table(headers: list[str], rows: list[list]) -> list[str]:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(_cell(c) for c in r) + " |" for r in rows]
    return out


def _section(title: str, headers: list[str], rows: list[list]) -> list[str]:
    if not rows:
        return [f"## {title}", "", "_none_", ""]
    return [f"## {title} ({len(rows)})", ""] + _table(headers, rows) + [""]


def render_markdown(ov: dict) -> str:
    s = ov["summary"]
    by = s["by_status"]
    head = f"# Status - {ov['project']}" if ov.get("project") else "# Status"
    if ov.get("scope"):
        head += f" - {ov['scope']}"
    lines = [
        head, "",
        f"_Generated {ov['generated']} by md_sdlc {ov['tool_version']} - do not hand-edit, run `status` or `backlog` to refresh._",
        "",
        f"**Done:** {by.get('done', 0)} items, steps {s['steps_done']}/{s['steps_total']}, open items done {s['rows_done']}  ",
        f"**Now:** {by.get('in-progress', 0)} in progress, {by.get('in-review', 0)} waiting for check, "
        f"{by.get('blocked', 0)} blocked, {s['rows_open']} open items  ",
        f"**Later:** {by.get('not-started', 0)} not started, {s['ideas']} ideas, {s['parked']} parked",
        "",
    ]
    lines += _section("Tracks", ["Track", "Title", "State", "Steps", "Open", "Next", "Waits on", "Updated"],
                      [[t["id"], t["title"], t["status"], f"{t['steps_done']}/{t['steps_total']}",
                        t["open_items"], t["next"], t["waits_on"], t["updated"]] for t in ov["tracks"]])
    lines += _section("On site", ["Item", "Title", "Deployed", "State"],
                      [[d["id"], d["title"], d["deployed"], d["status"]] for d in ov["on_site"]])
    simple = ["Id", "Title", "State", "Waits on", "Updated"]
    for key, title in (("waiting_check", "Waiting for check"), ("blocked", "Blocked"),
                       ("decisions", "Decisions for owner"), ("waiting_others", "Waiting on others")):
        lines += _section(title, simple, [[d["id"], d["title"], d["status"], d.get("waits_on"), d.get("updated")]
                                          for d in ov[key]])
    lines += _section("Experiments", ["Id", "Question / summary", "Verdict", "Result", "State"],
                      [[e["id"], e.get("question") or e["title"], e.get("verdict"), e.get("result"), e["status"]]
                       for e in ov["experiments"]])
    lines += _section("Recent", ["Id", "Title", "State", "Updated"],
                      [[d["id"], d["title"], d["status"], d["updated"]] for d in ov["recent"]])
    lines += _section(f"Not touched {ov['stale_days']} days", ["Id", "Title", "State", "Days"],
                      [[d["id"], d["title"], d["status"], d["days"]] for d in ov["stale"]])
    lines += _section("Ideas", ["Id", "Title", "State", "Updated"],
                      [[d["id"], d["title"], d["status"], d["updated"]] for d in ov["ideas"]])
    lines += _section("Parked", ["Id", "Title", "Updated"],
                      [[d["id"], d["title"], d["updated"]] for d in ov["parked"]])
    if ov.get("rows"):
        lines += _section("Rows", ["Id", "State", "Waits", "Verdict", "Updated", "Summary"],
                          [[r["id"], r["status"], r["waits_on"], r.get("verdict"), r["updated"], r["title"]]
                           for r in ov["rows"]])
    return "\n".join(lines).rstrip() + "\n"
