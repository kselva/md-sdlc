"""
Plugin registry.

In dev mode (running as .py), auto-discovers command plugins by walking
plugins/ subdirectories on disk - adding a new plugin folder is the entire
integration step, no changes needed here or in sdlc_tool.py.

When frozen into a single-file .exe (PyInstaller), there is no real
plugins/ directory to walk at runtime and importlib.import_module calls
are invisible to PyInstaller's static analysis, so the plugin set falls
back to a fixed list that must be kept in sync with plugins/*/plugin.py.
Both paths load through the same Command contract either way.
"""
import importlib
import logging
import sys
from pathlib import Path

from plugins.base_plugin import BaseCommand

logger = logging.getLogger(__name__)

# Kept in sync with plugins/*/plugin.py AND md_sdlc.spec's hiddenimports list -
# used only when frozen (see module docstring). Adding a plugin needs BOTH
# updated, or the exe silently drops the command while `python sdlc_tool.py`
# still works fine - this bit twice during development, hence the note.
_FROZEN_PLUGIN_MODULES = [
    "plugins.init.plugin",
    "plugins.validate.plugin",
    "plugins.backlog.plugin",
    "plugins.query.plugin",
    "plugins.new.plugin",
    "plugins.promote.plugin",
    "plugins.archive.plugin",
    "plugins.conventions.plugin",
    "plugins.review.plugin",
]


def _load_module(module_name: str, registry: dict[str, BaseCommand]) -> None:
    try:
        module = importlib.import_module(module_name)
        command_class = getattr(module, "Command", None)
        if command_class is None or not issubclass(command_class, BaseCommand):
            logger.warning("No valid Command class found in %s", module_name)
            return
        instance = command_class()
        if not instance.name:
            logger.warning("Command in %s has no name set, skipping", module_name)
            return
        registry[instance.name] = instance
        logger.debug("Loaded command: %s", instance.name)
    except Exception as exc:
        logger.error("Failed to load command %s: %s", module_name, exc)


def load_plugins() -> dict[str, BaseCommand]:
    registry: dict[str, BaseCommand] = {}

    if getattr(sys, "frozen", False):
        for module_name in _FROZEN_PLUGIN_MODULES:
            _load_module(module_name, registry)
        return registry

    plugins_dir = Path(__file__).parent
    for entry in sorted(plugins_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        if not (entry / "plugin.py").exists():
            continue
        _load_module(f"plugins.{entry.name}.plugin", registry)

    return registry
