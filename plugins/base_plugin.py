"""
Base command contract.

Every plugin must inherit from BaseCommand and implement register_args + run.
Mirrors or-tools/azure-devops-tools/plugins/base_plugin.py, adapted to a
single `run` verb since these six commands don't share a natural
fetch/create shape the way ADO/Jira ticket plugins do.
"""
from abc import ABC, abstractmethod
import argparse

from core.repo import AiDocsRepo


class BaseCommand(ABC):
    """Abstract base for all ai-docs-tool command plugins."""

    name: str = ""
    description: str = ""

    @abstractmethod
    def register_args(self, parser: argparse.ArgumentParser) -> None:
        """Register all CLI arguments specific to this command."""

    @abstractmethod
    def run(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        """Execute the command against the resolved AiDocsRepo."""
