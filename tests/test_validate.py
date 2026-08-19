"""
validate - Story status:done vs unresolved review.md findings (see conventions.md §5).
"""
import pytest

from conftest import write_review_md, write_story
from plugins.validate.plugin import Command as ValidateCommand


def _run_validate(repo, capsys):
    try:
        ValidateCommand().run(repo, None)
        return capsys.readouterr().out, 0
    except SystemExit as exc:
        return capsys.readouterr().out, exc.code


def test_done_story_with_open_finding_fails(tmp_path, repo, capsys):
    story_dir = write_story(tmp_path, status="done")
    write_review_md(story_dir, [("RVW-01", "high", "open", "Bug found", "agent-2", "2026-08-19")])

    out, code = _run_validate(repo, capsys)

    assert code == 1
    assert "unresolved finding 'RVW-01'" in out


def test_done_story_with_changes_requested_finding_fails(tmp_path, repo, capsys):
    story_dir = write_story(tmp_path, status="done")
    write_review_md(story_dir, [("RVW-01", "high", "changes-requested", "Bug found", "agent-2", "2026-08-19")])

    out, code = _run_validate(repo, capsys)

    assert code == 1
    assert "unresolved finding 'RVW-01'" in out


def test_done_story_with_only_resolved_findings_passes(tmp_path, repo, capsys):
    story_dir = write_story(tmp_path, status="done")
    write_review_md(story_dir, [
        ("RVW-01", "high", "fixed", "Bug found", "agent-2", "2026-08-19"),
        ("RVW-02", "low", "wontfix", "Style nit", "agent-2", "2026-08-19"),
    ])

    out, code = _run_validate(repo, capsys)

    assert code == 0
    assert "OK" in out


def test_in_review_story_with_open_finding_passes(tmp_path, repo, capsys):
    story_dir = write_story(tmp_path, status="in-review")
    write_review_md(story_dir, [("RVW-01", "high", "open", "Bug found", "agent-2", "2026-08-19")])

    out, code = _run_validate(repo, capsys)

    assert code == 0
    assert "OK" in out


def test_done_story_with_no_review_md_passes(tmp_path, repo, capsys):
    write_story(tmp_path, status="done")

    out, code = _run_validate(repo, capsys)

    assert code == 0
    assert "OK" in out
