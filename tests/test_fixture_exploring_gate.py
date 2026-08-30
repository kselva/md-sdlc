"""
Locks in the 0.3.0 stability ERROR against a real on-disk fixture tree
(tests/fixtures/exploring_gate/) resolved the same way the CLI resolves a
project - so a regression in config-key reading or code_root resolution is
caught, not just the in-memory rule logic.
"""
from pathlib import Path

from core.profile import resolve_project
from core.repo import AiDocsRepo
from plugins.validate.plugin import Command as ValidateCommand

_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "exploring_gate"
_AIDOCS = _FIXTURE_ROOT / "ai-docs"


def test_exploring_story_with_spec_file_is_an_error(capsys):
    project = resolve_project(_AIDOCS)
    repo = AiDocsRepo(project.root, project)

    try:
        ValidateCommand().run(repo, None)
        code = 0
    except SystemExit as exc:
        code = exc.code

    out = capsys.readouterr().out
    assert code == 1
    assert "STORY-01-cycles" in out
    assert "cycles.spec.ts" in out
    assert "smoke test only" in out


def test_code_root_resolves_to_project_dir():
    project = resolve_project(_AIDOCS)
    # config.yml `code_root: "."` -> the folder that contains ai-docs/,
    # i.e. the fixture project root where code/ lives.
    assert project.code_root == _FIXTURE_ROOT.resolve()
