"""
query --unresolved-reviews --story <id> (see conventions.md §5).
"""
import argparse

import pytest

from conftest import write_review_md, write_story
from plugins.query.plugin import Command as QueryCommand


def _args(**overrides):
    defaults = dict(
        type=None, status=None, owner=None, scenario=None, stale_days=None,
        mvp_remaining=False, story=None, unresolved_reviews=False, active=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_unresolved_reviews_lists_open_and_changes_requested(tmp_path, repo, capsys):
    write_story(tmp_path)
    write_review_md(tmp_path / "EPIC-T1-test-epic" / "STORY-01-test-story", [
        ("RVW-01", "high", "open", "Bug A", "agent-2", "2026-08-19"),
        ("RVW-02", "medium", "changes-requested", "Bug B", "agent-2", "2026-08-19"),
        ("RVW-03", "low", "fixed", "Bug C", "agent-2", "2026-08-19"),
    ])

    QueryCommand().run(repo, _args(unresolved_reviews=True, story="STORY-01-test-story"))

    out = capsys.readouterr().out
    assert "RVW-01" in out
    assert "RVW-02" in out
    assert "RVW-03" not in out
    assert "2 unresolved finding(s)" in out


def test_unresolved_reviews_none_left(tmp_path, repo, capsys):
    write_story(tmp_path)
    write_review_md(tmp_path / "EPIC-T1-test-epic" / "STORY-01-test-story", [
        ("RVW-01", "high", "fixed", "Bug A", "agent-2", "2026-08-19"),
    ])

    QueryCommand().run(repo, _args(unresolved_reviews=True, story="STORY-01-test-story"))

    out = capsys.readouterr().out
    assert "No unresolved review findings" in out


def test_unresolved_reviews_requires_story(repo, capsys):
    with pytest.raises(SystemExit) as exc_info:
        QueryCommand().run(repo, _args(unresolved_reviews=True, story=None))

    assert exc_info.value.code == 1
    assert "requires --story" in capsys.readouterr().out


def test_unresolved_reviews_unknown_story(repo, capsys):
    with pytest.raises(SystemExit) as exc_info:
        QueryCommand().run(repo, _args(unresolved_reviews=True, story="STORY-99-nope"))

    assert exc_info.value.code == 1
    assert "not a known story" in capsys.readouterr().out


# -- 0.3.0 --active view ------------------------------------------------

def test_active_lists_in_progress_stories_with_branch_and_touches(tmp_path, repo, capsys):
    write_story(
        tmp_path, story_id="STORY-01-calc", status="in-progress",
        touches=["code/apps/api/src/salary/"],
    )
    write_story(tmp_path, story_id="STORY-02-done", status="done")

    QueryCommand().run(repo, _args(active=True))

    out = capsys.readouterr().out
    assert "STORY-01-calc" in out
    assert "feat/STORY-01-calc" in out
    assert "code/apps/api/src/salary/" in out
    assert "STORY-02-done" not in out


def test_active_none(tmp_path, repo, capsys):
    write_story(tmp_path, story_id="STORY-01-done", status="done")

    QueryCommand().run(repo, _args(active=True))

    assert "No active stories" in capsys.readouterr().out
