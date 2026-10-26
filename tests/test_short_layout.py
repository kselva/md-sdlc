"""
0.4.0 short layout - scenarios S1-S19 from
PROPOSAL-0.4.0-short-layout-status-and-experiments.md, each on a fresh
temporary project driven through the real commands.
"""
import argparse
import datetime
import importlib
import json
import time

import pytest

from core import frontmatter as fmparse
from core.overview import build_overview, render_markdown
from core.profile import init_marker, resolve_project
from core.repo import AiDocsRepo


def _cli(project_root):
    """Run a command the way sdlc_tool.py does: fresh project + repo each call."""
    def run(name: str, *argv: str) -> AiDocsRepo:
        project = resolve_project(project_root)
        repo = AiDocsRepo(project.root, project)
        command = importlib.import_module(f"plugins.{name}.plugin").Command()
        parser = argparse.ArgumentParser()
        command.register_args(parser)
        command.run(repo, parser.parse_args(list(argv)))
        return repo
    return run


@pytest.fixture
def proj(tmp_path):
    init_marker(tmp_path, "Demo", "DEMO", id_style="short", work_dir="plan")
    (tmp_path / "plan").mkdir()
    return tmp_path


@pytest.fixture
def cli(proj):
    return _cli(proj)


def _repo(proj) -> AiDocsRepo:
    project = resolve_project(proj)
    return AiDocsRepo(project.root, project)


def _overview(proj, scope=None, today=None) -> dict:
    return build_overview(_repo(proj), today=today, scope_id=scope)


def _validate(proj):
    command = importlib.import_module("plugins.validate.plugin").Command()
    return command.collect(_repo(proj))


def _track(proj):
    """PAY1 with steps A and B and three open items (S1 base)."""
    run = _cli(proj)
    run("new", "epic", "--title", "Checkout payments flow", "--code", "PAY1")
    run("new", "story", "--parent", "PAY1", "--title", "Card form", "--code", "A")
    run("new", "story", "--parent", "PAY1", "--title", "Retry logic", "--code", "B")
    run("item", "add", "PAY1-A", "postcode field")
    run("item", "add", "PAY1-A", "error text")
    run("item", "add", "PAY1-B", "timeout value")


def _ids(entries) -> list[str]:
    return [e["id"] for e in entries]


# -- S1-S6: tracks, checks, decisions, parked, stale ------------------------

def test_s1_new_track_steps_items(proj):
    _track(proj)
    ov = _overview(proj)
    track = ov["tracks"][0]
    assert track["id"] == "PAY1"
    assert (track["steps_done"], track["steps_total"], track["open_items"]) == (0, 2, 3)
    assert (proj / "plan/PAY1-checkout-payments-flow/PAY1-A-card-form/story.md").exists()
    assert (proj / "plan/PAY1-checkout-payments-flow/tasks.md").exists()
    assert _validate(proj) == ([], [])


def test_s2_step_in_review_waits_for_check(proj, cli):
    _track(proj)
    cli("set", "PAY1-A", "--status", "in-review", "--next", "field check")
    assert "PAY1-A" in _ids(_overview(proj)["waiting_check"])


def test_s3_row_waiting_on_site(proj, cli):
    _track(proj)
    cli("item", "set", "PAY1-A.1", "--waits", "site")
    ov = _overview(proj)
    assert "PAY1-A.1" in _ids(ov["waiting_others"])
    assert "PAY1-A.1" not in _ids(ov["decisions"])


def test_s4_decision_for_owner(proj, cli):
    _track(proj)
    cli("set", "PAY1-B", "--waits-on", "owner")
    cli("item", "set", "PAY1-A.2", "--waits", "owner")
    assert {"PAY1-B", "PAY1-A.2"} <= set(_ids(_overview(proj)["decisions"]))


def test_s5_parked_leaves_tracks(proj, cli):
    _track(proj)
    cli("set", "PAY1", "--status", "parked")
    ov = _overview(proj)
    assert ov["tracks"] == []
    assert _ids(ov["parked"]) == ["PAY1"]
    assert _validate(proj)[0] == []


def test_s6_not_touched(proj, cli):
    _track(proj)
    cli("set", "PAY1-A", "--status", "in-progress", "--next", "x")
    later = datetime.date.today() + datetime.timedelta(days=15)
    stale = _overview(proj, today=later)["stale"]
    assert _ids(stale) == ["PAY1-A"] and stale[0]["days"] == 15


# -- S7-S10: ideas, POC, experiments, adopt ----------------------------------

def test_s7_idea_promoted_keeps_fields(proj, cli):
    cli("new", "proposal", "--title", "Saved cards for returning users")
    idea_path = proj / "plan/ideas/IDEA-saved-cards-for.md"
    meta, body = fmparse.parse(idea_path)
    meta["source"] = "customer call"
    fmparse.write(idea_path, meta, body)

    cli("promote", "IDEA-saved-cards-for", "--to-epic", "--code", "PAY2")
    meta, _ = fmparse.parse(idea_path)
    assert meta["status"] == "done" and meta["promoted"] == "PAY2"
    assert meta["source"] == "customer call"  # W3
    epic = _repo(proj).find("PAY2")
    assert epic.originated_from == "IDEA-saved-cards-for"
    assert (epic.path.parent / "tasks.md").exists()


def test_s7_promote_needs_code(proj, cli):
    cli("new", "proposal", "--title", "Idea")
    with pytest.raises(SystemExit):
        cli("promote", "IDEA-idea", "--to-epic")


def test_s8_poc_track_with_experiments(proj, cli):
    cli("new", "epic", "--title", "Fraud check", "--code", "FRD1", "--scenario", "poc")
    cli("new", "experiment", "--parent", "FRD1", "--title", "Rule set A", "--question", "Does A catch 90%?")
    cli("new", "experiment", "--parent", "FRD1", "--title", "Rule set B", "--question", "Is B faster?")
    exps = _overview(proj)["experiments"]
    assert _ids(exps) == ["FRD1-E1", "FRD1-E2"]
    assert exps[0]["question"] == "Does A catch 90%?" and exps[0]["verdict"] == "open"
    assert (proj / "plan/FRD1-fraud-check/FRD1-E1-rule-set-a.md").exists()
    assert _validate(proj)[0] == []


def test_s9_result_keeps_header_order(proj, cli):
    cli("new", "experiment", "--title", "Cache size", "--question", "Is 64 MB enough?")
    path = proj / "plan/EXP-cache-size.md"
    before = list(fmparse.parse(path)[0].keys())
    cli("set", "EXP-cache-size", "--result", "64 MB hit 97%", "--verdict", "yes")
    meta, _ = fmparse.parse(path)
    assert list(meta.keys()) == before + ["result"]  # W2: no re-sort
    exp = _overview(proj)["experiments"][0]
    assert (exp["verdict"], exp["result"]) == ("yes", "64 MB hit 97%")
    assert "updated: " + datetime.date.today().isoformat() in path.read_text(encoding="utf-8")


def test_s10_adopt_in_place(proj, cli):
    old = proj / "plan/old-checkout-notes.md"
    old.write_text("# Old notes\n\nKeep this text.\n", encoding="utf-8")
    cli("adopt", str(old), "--type", "adhoc", "--id", "ADHOC-old-notes", "--status", "parked")
    meta, body = fmparse.parse(old)
    assert meta["id"] == "ADHOC-old-notes" and meta["adopted"]
    assert body.strip() == "# Old notes\n\nKeep this text."
    assert _validate(proj)[0] == []  # name rule skipped for adopted files


def test_s10_adopt_refuses_tracked_file(proj, cli):
    cli("new", "adhoc", "--title", "Thing")
    with pytest.raises(SystemExit):
        cli("adopt", str(proj / "plan/ADHOC-thing.md"), "--type", "adhoc", "--id", "ADHOC-other")


# -- S11-S14: validate rules, log --------------------------------------------

def test_s11_loose_file_is_error(proj):
    _track(proj)
    (proj / "plan/stray.md").write_text("# notes\n", encoding="utf-8")
    (proj / "plan/PAY1-checkout-payments-flow/PAY1-A-card-form/design-sketch.md").write_text("x", encoding="utf-8")
    errors, _ = _validate(proj)
    assert len(errors) == 1 and "stray.md" in errors[0] and "adopt" in errors[0]
    assert _repo(proj).attached_files(_repo(proj).find("PAY1-A")) == ["design-sketch.md"]


def test_s12_duplicate_bad_parent_bad_verdict(proj, cli):
    _track(proj)
    a = proj / "plan/PAY1-checkout-payments-flow/PAY1-A-card-form/story.md"
    copy = proj / "plan/PAY1-checkout-payments-flow/PAY1-A-copy/story.md"
    copy.parent.mkdir()
    copy.write_text(a.read_text(encoding="utf-8"), encoding="utf-8")
    cli("new", "experiment", "--title", "Bad one", "--question", "q")
    exp = proj / "plan/EXP-bad-one.md"
    meta, body = fmparse.parse(exp)
    meta.update({"verdict": "maybe", "parent": "NOPE"})
    fmparse.write(exp, meta, body)

    errors = " | ".join(_validate(proj)[0])
    assert "duplicate id 'PAY1-A'" in errors
    assert "parent 'NOPE' does not resolve" in errors
    assert "verdict 'maybe'" in errors


def test_s12_story_id_must_start_with_epic(proj):
    _track(proj)
    path = proj / "plan/PAY1-checkout-payments-flow/PAY1-B-retry-logic/story.md"
    meta, body = fmparse.parse(path)
    meta["id"] = "PAY9-B"
    fmparse.write(path, meta, body)
    errors = " | ".join(_validate(proj)[0])
    assert "must start with its epic id 'PAY1-'" in errors
    assert "must start with its id 'PAY9-B'" in errors


def test_s13_long_name_and_missing_next_warn(proj, cli):
    _track(proj)
    long_dir = proj / "plan/PAY1-checkout-payments-flow/PAY1-C-a-very-long-folder-name-that-goes-on-and-on"
    long_dir.mkdir()
    (long_dir / "story.md").write_text(
        "---\nid: PAY1-C\ntype: story\nkind: work-item\nstatus: not-started\nparent: PAY1\n---\n# C\n",
        encoding="utf-8")
    cli("set", "PAY1-A", "--status", "in-progress")
    errors, warnings = _validate(proj)
    assert errors == []
    text = " | ".join(warnings)
    assert "keep it under 40" in text and "in-progress story has no 'next:'" in text


def test_s14_log_newest_first(proj, cli):
    _track(proj)
    cli("log", "PAY1", "first note")
    cli("log", "PAY1", "second note")
    repo = _repo(proj)
    lines = repo.log_lines(repo.find("PAY1"))
    assert lines[0].endswith("second note") and lines[1].endswith("first note")
    assert repo.find("PAY1").updated == datetime.date.today().isoformat()


def test_s14_log_refuses_single_file(proj, cli):
    cli("new", "adhoc", "--title", "Thing")
    with pytest.raises(SystemExit):
        cli("log", "ADHOC-thing", "note")


# -- S15-S17: archive, hand-edited rows, json --------------------------------

def test_s15_archive_leaves_status_links_resolve(proj, cli):
    _track(proj)
    cli("new", "adhoc", "--title", "Follow up")
    adhoc = proj / "plan/ADHOC-follow-up.md"
    meta, body = fmparse.parse(adhoc)
    meta["related"] = "PAY1"
    fmparse.write(adhoc, meta, body)
    cli("set", "PAY1", "--status", "done")
    cli("archive", "PAY1")

    assert (proj / "hist/plan/PAY1-checkout-payments-flow/epic.md").exists()
    ov = _overview(proj)
    assert "PAY1" not in _ids(ov["recent"]) and ov["tracks"] == []
    assert _validate(proj)[0] == []


def test_s16_reordered_columns_and_escaped_pipe(proj, cli):
    _track(proj)
    tasks = proj / "plan/PAY1-checkout-payments-flow/PAY1-A-card-form/tasks.md"
    tasks.write_text(
        "# Open items\n\nIntro text.\n\n| summary | id | status | waits |\n|---|---|---|---|\n"
        "| a \\| b choice | PAY1-A.1 | in-progress | site |\n\nTrailing note.\n",
        encoding="utf-8")
    row = _repo(proj).task_rows("PAY1-A")[0]
    assert (row.id, row.status, row.waits, row.summary) == ("PAY1-A.1", "in-progress", "site", "a | b choice")

    cli("item", "add", "PAY1-A", "next one")
    text = tasks.read_text(encoding="utf-8")
    assert "Intro text." in text and "Trailing note." in text
    assert "| summary | id | status | waits |" in text  # own columns kept
    assert [r.id for r in _repo(proj).task_rows("PAY1-A")] == ["PAY1-A.1", "PAY1-A.2"]


def test_s16_missing_column_is_refused(proj, cli):
    _track(proj)
    tasks = proj / "plan/PAY1-checkout-payments-flow/PAY1-A-card-form/tasks.md"
    tasks.write_text("| id | status | summary |\n|---|---|---|\n| PAY1-A.1 | not-started | x |\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        cli("item", "set", "PAY1-A.1", "--waits", "site")


def test_s17_json_matches_text(proj, cli, capsysbinary):
    _track(proj)
    capsysbinary.readouterr()
    cli("status", "--json")
    data = json.loads(capsysbinary.readouterr().out.decode("utf-8"))
    cli("status")
    text = capsysbinary.readouterr().out.decode("utf-8")
    assert data["summary"]["rows_open"] == 3
    assert "3 open items" in text
    assert "| PAY1 | Checkout payments flow | not-started | 0/2 | 3 |" in text


# -- S18 is the existing suite; S19 performance ------------------------------

def test_s19_two_thousand_files_under_two_seconds(proj):
    root = proj / "plan"
    for e in range(40):
        epic_dir = root / f"E{e}-epic"
        epic_dir.mkdir()
        (epic_dir / "epic.md").write_text(
            f"---\nid: E{e}\ntype: epic\nkind: work-item\nstatus: in-progress\nnext: go\n"
            f"updated: 2026-10-01\n---\n# Epic {e}\n", encoding="utf-8")
        for s in range(49):
            story_dir = epic_dir / f"E{e}-{s}-story"
            story_dir.mkdir()
            (story_dir / "story.md").write_text(
                f"---\nid: E{e}-{s}\ntype: story\nkind: work-item\nstatus: not-started\nparent: E{e}\n"
                f"updated: 2026-10-01\n---\n# Story {s}\n", encoding="utf-8")
    _overview(proj)  # first read pays the OS / virus-scan cost of brand-new files
    start = time.perf_counter()
    ov = _overview(proj)
    render_markdown(ov)
    elapsed = time.perf_counter() - start
    assert ov["summary"]["steps_total"] == 40 * 49
    assert elapsed < 2.0, f"status took {elapsed:.2f}s"


# -- extra: experiment rows, deployed, classic untouched ---------------------

def test_experiment_row_with_verdict(proj, cli):
    _track(proj)
    cli("item", "add", "PAY1-B", "try 2 s timeout", "--experiment")
    cli("item", "set", "PAY1-B.2", "done", "--verdict", "partly", "--result", "fine on wifi only")
    exp = next(e for e in _overview(proj)["experiments"] if e["id"] == "PAY1-B.2")
    assert exp["verdict"] == "partly" and "result: fine on wifi only" in exp["title"]


def test_deployed_on_site_section(proj, cli):
    _track(proj)
    cli("set", "PAY1-A", "--deployed", "release-3 2026-10-20")
    cli("set", "PAY1-B", "--deployed", "release-4 2026-10-25")
    assert _ids(_overview(proj)["on_site"]) == ["PAY1-B", "PAY1-A"]
    cli("set", "PAY1-B", "--deployed", "")
    assert _ids(_overview(proj)["on_site"]) == ["PAY1-A"]


def test_new_task_refused_in_short_layout(proj, cli):
    _track(proj)
    with pytest.raises(SystemExit):
        cli("new", "task", "--parent", "PAY1-A", "--title", "x")


def test_story_number_when_no_code(proj, cli):
    _track(proj)
    cli("new", "story", "--parent", "PAY1", "--title", "Third")
    cli("new", "story", "--parent", "PAY1", "--title", "Fourth")
    ids = sorted(c.id for c in _repo(proj).children_of("PAY1") if c.type == "story")
    assert ids == ["PAY1-1", "PAY1-2", "PAY1-A", "PAY1-B"]


def test_bad_code_refused(proj, cli):
    with pytest.raises(SystemExit):
        cli("new", "epic", "--title", "x", "--code", "pay-1")
