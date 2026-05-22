from __future__ import annotations

from abc import ABC, abstractmethod


class Command(ABC):
    @abstractmethod
    def execute(self) -> int:
        """Run the command. Return an exit code (0 = success)."""
