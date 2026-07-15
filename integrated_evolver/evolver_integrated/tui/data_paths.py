"""Paths for TUI JSON data stored in the project data tree."""
from __future__ import annotations

from pathlib import Path


def tui_data_dir() -> Path:
    return (
        Path(__file__).parents[2]
        / "data"
        / "integrated system"
        / "objects"
        / "software"
        / "tui"
    )


def tui_data_path(filename: str) -> Path:
    return tui_data_dir() / filename


def integrated_object_path(filename: str) -> Path:
    return (
        Path(__file__).parents[2]
        / "data"
        / "integrated system"
        / "objects"
        / filename
    )
