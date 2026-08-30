"""
handover - one-Story context pack (PROPOSAL-0.3.0 section 3.2).
"""
import argparse

import pytest

from conftest import write_review_md, write_story, write_tasks_md
from plugins.handover.plugin import Command as HandoverCommand


def _args(story_id, full=False, strict=False):
    return argparse.Namespace(story_id=story_id, full=full, strict=strict)


def _run(repo, story_id, capsys, **kw):
    try:
        HandoverCommand().run(repo, _args(story_id, **kw))
        return capsys.readouterr().out, 0
    except SystemExit as exc:
        return capsys.readouterr().out, exc.code


def test_pack_has_branch_story_touches_and_open_tasks(tmp_path, repo_with_project, capsys):
    story_dir = write_story(
        tmp_path, status="in-progress", stability="exploring",
        touches=["code/apps/api/src/salary/cycles/"],
    )
    write_tasks_md(story_dir, [
        ("TASK-01", "in-progress", "feature", "Selva", "2026-08-30", "Build the cycle calc"),
        ("TASK-02", "done", "feature", "Selva", "2026-08-30", "Scaffold module"),
    ])

    out, code = _run(repo_with_project, "STORY-01-test-story", capsys)

    assert code == 0
    assert "BRANCH: feat/STORY-01-test-story" in out
    assert "--- STORY ---" in out
    assert "stability: exploring" in out
    assert "code/apps/api/src/salary/cycles/" in out
    assert "TASK-01" in out
    assert "TASK-02" not in out  # done tasks are filtered out


def test_pack_excludes_sibling_stories(tmp_path, repo_with_project, capsys):
    write_story(tmp_path, story_id="STORY-01-mine", status="in-progress")
    write_story(tmp_path, story_id="STORY-02-other", status="in-progress")

    out, _ = _run(repo_with_project, "STORY-01-mine", capsys)

    assert "STORY-02-other" not in out


def test_ai_rules_inlined_when_present(tmp_path, repo_with_project, capsys):
    write_story(tmp_path, story_id="STORY-01-mine", status="in-progress")
    (tmp_path / "AI-RULES.md").write_text("# AI agent rules\n\nDO\n- Work only the Story.\n", encoding="utf-8")

    out, _ = _run(repo_with_project, "STORY-01-mine", capsys)

    assert "--- AI-RULES.md (project) ---" in out
    assert "Work only the Story." in out


def test_unknown_story_exits_1(tmp_path, repo_with_project, capsys):
    out, code = _run(repo_with_project, "STORY-99-nope", capsys)
    assert code == 1
    assert "not a known story" in out


def test_strict_refuses_when_validate_fails(tmp_path, repo_with_project, capsys):
    # invalid stability value -> validate error
    write_story(tmp_path, story_id="STORY-01-mine", status="in-progress", stability="bogus")

    out, code = _run(repo_with_project, "STORY-01-mine", capsys, strict=True)

    assert code == 1
    assert "refusing to build a handover pack" in out


def test_non_strict_emits_pack_with_warning_when_validate_fails(tmp_path, repo_with_project, capsys):
    write_story(tmp_path, story_id="STORY-01-mine", status="in-progress", stability="bogus")

    out, code = _run(repo_with_project, "STORY-01-mine", capsys, strict=False)

    assert code == 0
    assert "WARNING" in out
    assert "BRANCH: feat/STORY-01-mine" in out


def test_open_review_findings_included(tmp_path, repo_with_project, capsys):
    story_dir = write_story(tmp_path, story_id="STORY-01-mine", status="in-review")
    write_review_md(story_dir, [
        ("RVW-01", "high", "open", "Race in retry", "agent-2", "2026-08-30"),
        ("RVW-02", "low", "fixed", "Nit", "agent-2", "2026-08-30"),
    ])

    out, _ = _run(repo_with_project, "STORY-01-mine", capsys)

    assert "RVW-01" in out
    assert "RVW-02" not in out
