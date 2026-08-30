"""
validate - 0.3.0 stability test gate and touches: overlap warning
(see CONVENTIONS.md §10, PROPOSAL-0.3.0 sections 3.1 / 3.3).
"""
from conftest import write_story
from plugins.validate.plugin import Command as ValidateCommand


def _run(repo, capsys):
    try:
        ValidateCommand().run(repo, None)
        return capsys.readouterr().out, 0
    except SystemExit as exc:
        return capsys.readouterr().out, exc.code


def _make_code_file(tmp_path, relpath: str) -> None:
    p = tmp_path / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("// fixture\n", encoding="utf-8")


# -- Rule 1: spec test file under an exploring Story's touches: -> ERROR ----

def test_exploring_story_with_spec_file_under_touches_errors(tmp_path, repo_with_project, capsys):
    write_story(
        tmp_path, status="in-progress", stability="exploring",
        touches=["code/apps/api/src/salary/cycles/"],
    )
    _make_code_file(tmp_path, "code/apps/api/src/salary/cycles/cycles.spec.ts")

    out, code = _run(repo_with_project, capsys)

    assert code == 1
    assert "spec/assertion test file exists under touches:" in out
    assert "cycles.spec.ts" in out


def test_exploring_story_with_only_smoke_test_passes(tmp_path, repo_with_project, capsys):
    write_story(
        tmp_path, status="in-progress", stability="exploring",
        touches=["code/apps/api/src/salary/cycles/"],
    )
    _make_code_file(tmp_path, "code/apps/api/src/salary/cycles/cycles.smoke.spec.ts")

    out, code = _run(repo_with_project, capsys)

    assert code == 0
    assert "OK" in out


def test_settled_story_with_spec_file_passes(tmp_path, repo_with_project, capsys):
    write_story(
        tmp_path, status="in-progress", stability="settled",
        touches=["code/apps/api/src/salary/cycles/"],
    )
    _make_code_file(tmp_path, "code/apps/api/src/salary/cycles/cycles.spec.ts")

    out, code = _run(repo_with_project, capsys)

    assert code == 0
    assert "OK" in out


def test_exploring_story_no_spec_file_passes(tmp_path, repo_with_project, capsys):
    write_story(
        tmp_path, status="in-progress", stability="exploring",
        touches=["code/apps/api/src/salary/cycles/"],
    )
    _make_code_file(tmp_path, "code/apps/api/src/salary/cycles/cycles.ts")

    out, code = _run(repo_with_project, capsys)

    assert code == 0
    assert "OK" in out


# -- Rule 3: exploring + status done -> WARNING (exit 0) -------------------

def test_exploring_story_marked_done_warns_not_errors(tmp_path, repo_with_project, capsys):
    write_story(tmp_path, status="done", stability="exploring")

    out, code = _run(repo_with_project, capsys)

    assert code == 0
    assert "WARN" in out
    assert "stability is 'exploring'" in out


# -- invalid stability value -> ERROR ------------------------------------

def test_invalid_stability_value_errors(tmp_path, repo_with_project, capsys):
    write_story(tmp_path, status="in-progress", stability="frozen-ish")

    out, code = _run(repo_with_project, capsys)

    assert code == 1
    assert "stability 'frozen-ish' not one of" in out


# -- touches: overlap between two active Stories -> WARNING --------------

def test_overlapping_touches_between_active_stories_warns(tmp_path, repo_with_project, capsys):
    write_story(
        tmp_path, story_id="STORY-01-calc", status="in-progress", stability="exploring",
        touches=["code/apps/api/src/salary/"],
    )
    write_story(
        tmp_path, story_id="STORY-02-picker", status="in-review", stability="exploring",
        touches=["code/apps/api/src/salary/cycles/boundary.ts"],
    )

    out, code = _run(repo_with_project, capsys)

    assert code == 0
    assert "touches: overlap" in out
    assert "STORY-01-calc" in out and "STORY-02-picker" in out


def test_non_overlapping_touches_no_warning(tmp_path, repo_with_project, capsys):
    write_story(
        tmp_path, story_id="STORY-01-calc", status="in-progress", stability="exploring",
        touches=["code/apps/api/src/salary/"],
    )
    write_story(
        tmp_path, story_id="STORY-02-picker", status="in-progress", stability="exploring",
        touches=["code/apps/web/src/features/employee-form/"],
    )

    out, code = _run(repo_with_project, capsys)

    assert code == 0
    assert "touches: overlap" not in out
