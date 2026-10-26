"""
Project resolution - git-style marker discovery.

No central registry of project paths. Each project marks itself with a
.sdlc/config.yml inside its ai-docs/ folder (created by `init`). Resolution
walks up from the current working directory looking for that marker, the
same way `git` walks up looking for `.git/`. No plugin reads .sdlc/config.yml
directly - they all go through resolve_project().
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from core.vocab import DEFAULT_SMOKE_TEST_GLOB, DEFAULT_TEST_FILE_GLOBS, ID_STYLE_CLASSIC, ID_STYLE_SHORT
from core.version import __version__

logger = logging.getLogger(__name__)

MARKER_DIR = ".sdlc"
MARKER_CONFIG = "config.yml"


class NotInitializedError(Exception):
    """Raised when no .sdlc/config.yml is found walking up from cwd."""


@dataclass
class Project:
    root: Path            # the ai-docs/ folder itself
    project_prefix: str
    name: str
    marker_version: str | None = None  # tool version that ran `init`, if recorded
    # 0.3.0 - resolved from optional .sdlc/config.yml keys. code_root is the
    # tree that a Story's touches: globs resolve against (the code, not the
    # ai-docs/ folder); defaults to the directory that contains ai-docs/.
    code_root: Path | None = None
    test_file_globs: list[str] = field(default_factory=lambda: list(DEFAULT_TEST_FILE_GLOBS))
    smoke_test_glob: str = DEFAULT_SMOKE_TEST_GLOB
    # 0.4.0 - short layout (see CONVENTIONS "Short layout"). work_dir is where
    # new items are created and where loose files are an error; "" = root.
    id_style: str = ID_STYLE_CLASSIC
    work_dir: str = ""
    decision_waits: str = "owner"
    stale_days: int = 14

    @property
    def is_short(self) -> bool:
        return self.id_style == ID_STYLE_SHORT

    @property
    def work_path(self) -> Path:
        return self.root / self.work_dir if self.work_dir else self.root


def find_marker(start: Path | None = None) -> Path | None:
    """Walk up from start (default: cwd) looking for a .sdlc/ folder. Returns the folder containing it, or None."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / MARKER_DIR / MARKER_CONFIG).exists():
            return candidate
    return None


def resolve_project(start: Path | None = None) -> Project:
    """Find and load the nearest .sdlc/config.yml, or raise NotInitializedError."""
    root = find_marker(start)
    if root is None:
        raise NotInitializedError(
            "not initialized - no .sdlc/ found in this folder or any parent.\n"
            "  Run 'python sdlc_tool.py init' inside your project's ai-docs/ folder first."
        )

    config_path = root / MARKER_DIR / MARKER_CONFIG
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    marker_version = config.get("tool_version")
    if marker_version and marker_version != __version__:
        # stdout, not logger.warning (stderr) - PowerShell 5.1 wraps any stderr
        # output from a native exe into a NativeCommandError/ErrorRecord even at
        # exit code 0, which callers scripting against this CLI can misread as
        # a real failure.
        print(
            f"WARNING - project '{config.get('name', root.name)}' was initialized "
            f"with md_sdlc {marker_version}, running {__version__} - run 'validate' "
            f"after any tool upgrade to confirm nothing changed behavior"
        )

    code_root_cfg = config.get("code_root")
    if code_root_cfg:
        code_root = (root.parent / code_root_cfg).resolve()
    else:
        code_root = root.parent

    test_file_globs = config.get("test_file_globs") or list(DEFAULT_TEST_FILE_GLOBS)
    smoke_test_glob = config.get("smoke_test_glob") or DEFAULT_SMOKE_TEST_GLOB

    id_style = config.get("id_style") or ID_STYLE_CLASSIC
    if id_style not in (ID_STYLE_CLASSIC, ID_STYLE_SHORT):
        raise ValueError(f"{config_path}: id_style must be '{ID_STYLE_CLASSIC}' or '{ID_STYLE_SHORT}', got '{id_style}'")

    logger.debug("Resolved project at %s", root)
    return Project(
        root=root,
        project_prefix=config.get("project_prefix", root.name.upper()),
        name=config.get("name", root.name),
        marker_version=marker_version,
        code_root=code_root,
        test_file_globs=test_file_globs,
        smoke_test_glob=smoke_test_glob,
        id_style=id_style,
        work_dir=str(config.get("work_dir") or "").strip("/\\"),
        decision_waits=str(config.get("decision_waits") or "owner"),
        stale_days=int(config.get("stale_days") or 14),
    )


def init_marker(target: Path, name: str, project_prefix: str,
                id_style: str = ID_STYLE_CLASSIC, work_dir: str = "") -> Path:
    """Create .sdlc/config.yml under target. Raises FileExistsError if already initialized."""
    marker_dir = target / MARKER_DIR
    config_path = marker_dir / MARKER_CONFIG
    if config_path.exists():
        raise FileExistsError(f"already initialized: {config_path}")

    marker_dir.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        config = {"name": name, "project_prefix": project_prefix, "tool_version": __version__}
        if id_style != ID_STYLE_CLASSIC:
            config["id_style"] = id_style
        if work_dir:
            config["work_dir"] = work_dir
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
    return config_path
