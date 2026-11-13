"""Dependencies injected into every node, so tests can swap them out."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import Settings
from .memory import Memory

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


@dataclass
class Deps:
    settings: Settings
    memory: Memory
