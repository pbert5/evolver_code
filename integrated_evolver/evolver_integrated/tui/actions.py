"""JSON-backed action catalog helpers for the TUI."""
from __future__ import annotations

import json
from pathlib import Path


def load_action_catalog() -> dict:
    path = Path(__file__).parent / "actions.json"
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def actions_for_panel_tab(panel: str, tab: str) -> set[str]:
    catalog = load_action_catalog()
    panels = catalog.get("panels", {})
    panel_config = panels.get(panel, {}) if isinstance(panels, dict) else {}
    tabs = panel_config.get("tabs", {})
    tab_config = tabs.get(tab, {}) if isinstance(tabs, dict) else {}
    actions = tab_config.get("textual_actions", [])
    return {str(action) for action in actions}


def service_command(command_name: str, default: str) -> str:
    catalog = load_action_catalog()
    service = catalog.get("service_lifecycle", {})
    commands = service.get("commands", {}) if isinstance(service, dict) else {}
    command = commands.get(command_name, default)
    return str(command)


def service_managed_restricted_actions() -> set[str]:
    catalog = load_action_catalog()
    service = catalog.get("service_lifecycle", {})
    actions = (
        service.get("managed_only_textual_actions", [])
        if isinstance(service, dict)
        else []
    )
    return {str(action) for action in actions}


def key_help_lines() -> list[str]:
    catalog = load_action_catalog()
    entries = catalog.get("key_help", [])
    if not isinstance(entries, list):
        return []
    lines: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        key = entry.get("key")
        description = entry.get("description")
        if key and description:
            lines.append(f"{key} {description}")
    return lines
