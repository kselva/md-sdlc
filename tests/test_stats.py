"""
stats - project-wide status matrix, per-Epic drill-down, grouped counts.
"""
import argparse
import json

import pytest

from conftest import write_review_md, write_story, write_tasks_md
from plugins.stats.plugin import Command as StatsCommand


def _args(epic=None, by=None, as_json=False):
    return argparse.Namespace(epic=epic, by=by, **{"json": as_json})


def _run(repo, capsys, **kw):
    try:
        StatsCommand().run(repo, _args(**kw))
        return capsys.readouterr().out, 0
    except SystemExit as exc:
        return capsys.readouterr().out, exc.code


def _seed(tmp_path):
    """Two epics, three stories with a spread of statuses, task rows, findings."""
    from pathlib import Path

    epic1 = tmp_path / "EPIC-01-checkout"
    epic2 = tmp_path / "EPIC-02-reporting"
    epic1.mkdir()
    epic2.mkdir()
    (epic1 / "epic.md").write_text(
        "---\nid: EPIC-01-checkout\ntype: epic\nkind: work-item\nstatus: in-progress\n"
        "stability: settled\nowner: Priya\nupdated: 2026-08-30\n---\n\n# Checkout\n",
        encoding="utf-8",
    )
    (epic2 / "epic.md").write_text(
        "---\nid: EPIC-02-reporting\ntype: epic\nkind: work-item\nstatus: not-started\n"
        "stability: exploring\nowner: Arjun\nupdated: 2026-08-30\n---\n\n# Reporting\n",
        encoding="utf-8",
    )

    def story(epic_dir, sid, status, stability, owner, parent):
        d = epic_dir / sid
        d.mkdir()
        (d / "story.md").write_text(
            f"---\nid: {sid}\ntype: story\nkind: work-item\nstatus: {status}\n"
            f"stability: {stability}\nparent: {parent}\nowner: {owner}\nupdated: 2026-08-30\n"
            f"scenario: feature\n---\n\n# {sid}\n",
            encoding="utf-8",
        )
        return d

    s1 = story(epic1, "STORY-01-payment", "done", "locked", "Priya", "EPIC-01-checkout")
    story(epic1, "STORY-02-ui", "in-review", "settled", "agent-a", "EPIC-01-checkout")
    story(epic2, "STORY-01-export", "blocked", "exploring", "Arjun", "EPIC-02-reporting")

    write_tasks_md(s1, [
        ("TASK-01", "done", "feature", "Priya", "2026-08-30", "schema"),
        ("TASK-02", "in-progress", "bug", "Priya", "2026-08-30", "edge case"),
    ])
    write_review_md(epic1 / "STORY-02-ui", [
        ("RVW-01", "high", "open", "Race", "agent-2", "2026-08-30"),
    ])
    write_review_md(epic2 / "STORY-01-export", [
        ("RVW-01", "critical", "open", "Double count", "agent-3", "2026-08-30"),
        ("RVW-02", "low", "fixed", "Nit", "agent-3", "2026-08-30"),
    ])


def test_project_wide_matrix(tmp_path, repo, capsys):
    _seed(tmp_path)

    out, code = _run(repo, capsys)

    assert code == 0
    assert "TYPE" in out and "TOTAL" in out
    # two epics, three stories, two task rows
    assert "epic" in out and "story" in out and "task" in out
    assert "STABILITY (epics + stories)" in out
    assert "exploring 2" in out and "settled 2" in out and "locked 1" in out
    assert "REVIEW FINDINGS (open)" in out
    assert "critical 1" in out and "high 1" in out


def test_epic_drilldown(tmp_path, repo, capsys):
    _seed(tmp_path)

    out, code = _run(repo, capsys, epic="EPIC-01-checkout")

    assert code == 0
    assert "EPIC-01-checkout - in-progress" in out
    assert "STORIES (2)" in out
    assert "TASKS  (2)" in out
    assert "STORY-01-payment" in out and "STORY-02-ui" in out
    assert "1/2" in out  # payment story: 1 of 2 task rows done


def test_epic_drilldown_unknown_epic_exits_1(tmp_path, repo, capsys):
    _seed(tmp_path)

    out, code = _run(repo, capsys, epic="EPIC-99-nope")

    assert code == 1
    assert "not a known epic" in out


def test_by_owner(tmp_path, repo, capsys):
    _seed(tmp_path)

    out, code = _run(repo, capsys, by="owner")

    assert code == 0
    assert "OWNER" in out
    assert "Priya" in out and "Arjun" in out and "agent-a" in out


def test_by_stability_excludes_tasks(tmp_path, repo, capsys):
    _seed(tmp_path)

    out, code = _run(repo, capsys, by="stability")

    assert code == 0
    assert "STABILITY" in out
    # rows are exploring/settled/locked only, tasks (no stability) not counted
    assert "exploring" in out and "settled" in out and "locked" in out


def test_json_output_shape(tmp_path, repo, capsys):
    _seed(tmp_path)

    out, code = _run(repo, capsys, as_json=True)

    assert code == 0
    data = json.loads(out)
    assert data["project"]
    assert data["by_type"]["story"]["total"] == 3
    assert data["stability"]["settled"] == 2
    assert data["review_findings_open"]["critical"] == 1
    assert "_text" not in data
