"""
Shared pytest fixtures - builds a minimal Epic/Story tree under tmp_path so
each test gets an isolated repo instead of sharing tests/fixtures/ state.
"""
import argparse
from pathlib import Path

import pytest

from core.repo import AiDocsRepo


def write_story(
    root: Path,
    story_id: str = "STORY-01-test-story",
    status: str = "in-progress",
    stability: str | None = None,
    touches: list[str] | None = None,
) -> Path:
    epic_dir = root / "EPIC-T1-test-epic"
    story_dir = epic_dir / story_id
    story_dir.mkdir(parents=True, exist_ok=True)

    if not (epic_dir / "epic.md").exists():
        (epic_dir / "epic.md").write_text(
            "---\nid: EPIC-T1-test-epic\ntype: epic\nkind: work-item\nstatus: in-progress\n"
            "owner: Selva\nupdated: 2026-08-18\n---\n\n# Test Epic\n",
            encoding="utf-8",
        )

    fm = [
        "---",
        f"id: {story_id}",
        "type: story",
        "kind: work-item",
        f"status: {status}",
        "parent: EPIC-T1-test-epic",
        "owner: Selva",
        "updated: 2026-08-18",
        "scenario: feature",
    ]
    if stability is not None:
        fm.append(f"stability: {stability}")
    if touches:
        fm.append("touches:")
        fm += [f"  - {p}" for p in touches]
    fm += ["---", "", "# Test Story", ""]
    (story_dir / "story.md").write_text("\n".join(fm), encoding="utf-8")
    return story_dir


def write_tasks_md(story_dir: Path, rows: list[tuple[str, str, str, str, str, str]]) -> None:
    header = (
        "# Tasks\n\n| id | status | scenario | owner | updated | summary |\n"
        "|----|--------|----------|-------|---------|---------|\n"
    )
    body = "".join(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |\n" for r in rows)
    (story_dir / "tasks.md").write_text(header + body, encoding="utf-8")


def write_review_md(story_dir: Path, rows: list[tuple[str, str, str, str, str, str]]) -> None:
    header = "# Review Findings\n\n| id | severity | status | summary | reported_by | updated |\n|----|----------|--------|---------|--------------|---------|\n"
    body = "".join(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |\n" for r in rows)
    (story_dir / "review.md").write_text(header + body, encoding="utf-8")


@pytest.fixture
def repo(tmp_path) -> AiDocsRepo:
    return AiDocsRepo(tmp_path)


class _FakeProject:
    """Minimal stand-in for core.profile.Project - just the fields validate's
    stability gate reads. tmp_path is both the ai-docs root and (by default)
    the code_root for tests."""

    def __init__(self, code_root, test_file_globs=None, smoke_test_glob="*.smoke.spec.ts"):
        from core.vocab import DEFAULT_TEST_FILE_GLOBS
        self.code_root = code_root
        self.test_file_globs = test_file_globs or list(DEFAULT_TEST_FILE_GLOBS)
        self.smoke_test_glob = smoke_test_glob


@pytest.fixture
def repo_with_project(tmp_path):
    """A repo whose .project resolves code_root to tmp_path itself, so a
    Story's touches: like 'code/...' maps to tmp_path/code/..."""
    return AiDocsRepo(tmp_path, project=_FakeProject(code_root=tmp_path))


@pytest.fixture
def make_args():
    def _make(**kwargs) -> argparse.Namespace:
        return argparse.Namespace(**kwargs)
    return _make
