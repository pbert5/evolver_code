"""Modal screens for confirmation dialogs and generated forms."""
from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView, TextArea, Static


def sensor_sparkline(values: list[int], width: int = 36) -> str:
    """Render recent raw ADC readings without implying calibration."""
    samples = values[-width:]
    if not samples:
        return "·" * width
    low, high = min(samples), max(samples)
    if low == high:
        graph = "▅" * len(samples)
    else:
        glyphs = "▁▂▃▄▅▆▇█"
        graph = "".join(
            glyphs[(value - low) * (len(glyphs) - 1) // (high - low)]
            for value in samples
        )
    return graph.rjust(width, "·")


class HardwareMonitorScreen(ModalScreen[None]):
    """Read-only live raw-sensor monitor with safe serial cleanup."""

    BINDINGS = [
        Binding("escape", "dismiss_screen", "Close"),
        Binding("s", "safe_state", "Safe state"),
    ]
    DEFAULT_CSS = """
    HardwareMonitorScreen { align: center middle; }
    #hardware-monitor-dialog {
        width: 96; height: 24; border: round $accent;
        background: $surface; padding: 1 2;
    }
    #hardware-monitor-readings { height: 1fr; }
    #hardware-monitor-status { height: 3; }
    """
    HISTORY_LENGTH = 72

    def __init__(self, backend_factory: Any) -> None:
        super().__init__()
        self._backend_factory = backend_factory
        self._backend: Any = None
        self._history = {
            f"{kind}.{channel}": []
            for kind in ("thermistor", "photodiode")
            for channel in range(2)
        }
        self._error = "Connecting…"

    def compose(self) -> ComposeResult:
        with Vertical(id="hardware-monitor-dialog"):
            yield Label("Live Smart Sleeve Sensor Monitor — raw ADC, read-only")
            yield Label(
                "Reads hold commissioning safe mode; PID remains suspended. "
                "Esc closes safely; s sends safe state."
            )
            yield Static("Waiting for first sample…", id="hardware-monitor-readings")
            yield Static("", id="hardware-monitor-status")

    def on_mount(self) -> None:
        try:
            self._backend = self._backend_factory()
            self._backend.open()
            self._backend.safe_state()
            self._error = "LIVE — no outputs are commanded by this monitor"
            self._poll_sensors()
            self.set_interval(1.0, self._poll_sensors)
        except Exception as exc:
            self._error = (
                f"MONITOR ERROR: {exc}. Disconnect actuator power if safe "
                "state cannot be confirmed."
            )
            self._safe_close()
            self._render_monitor()

    def _poll_sensors(self) -> None:
        if self._backend is None:
            return
        try:
            for channel in range(2):
                self._append(
                    "thermistor", channel,
                    self._backend.read_thermistor(channel),
                )
                self._append(
                    "photodiode", channel,
                    self._backend.read_photodiode(channel),
                )
            self._error = (
                "LIVE — raw ADC values update every second; this is not "
                "calibration"
            )
        except Exception as exc:
            self._error = f"MONITOR ERROR: {exc}. Safe state is being requested."
            self._safe_close()
        self._render_monitor()

    def _append(self, kind: str, channel: int, value: int) -> None:
        history = self._history[f"{kind}.{channel}"]
        history.append(value)
        del history[:-self.HISTORY_LENGTH]

    def _render_monitor(self) -> None:
        lines = []
        for channel in range(2):
            for kind, label in (
                ("thermistor", "Thermistor"),
                ("photodiode", "Photodiode"),
            ):
                values = self._history[f"{kind}.{channel}"]
                current = "—" if not values else str(values[-1])
                trend = sensor_sparkline(values)
                lines.append(f"Sleeve {channel}  {label:<11} {current:>5}  {trend}")
        self.query_one(
            "#hardware-monitor-readings", Static
        ).update("\n".join(lines))
        self.query_one("#hardware-monitor-status", Static).update(self._error)

    def _safe_close(self) -> None:
        if self._backend is None:
            return
        try:
            self._backend.safe_state()
        except Exception:
            pass
        try:
            self._backend.close()
        finally:
            self._backend = None

    def action_safe_state(self) -> None:
        if self._backend is not None:
            try:
                self._backend.safe_state()
                self._error = (
                    "SAFE acknowledged; monitoring will resume on the next "
                    "read."
                )
            except Exception as exc:
                self._error = (
                    f"SAFE could not be confirmed: {exc}. Disconnect actuator "
                    "power."
                )
            self._render_monitor()

    def action_dismiss_screen(self) -> None:
        self.dismiss(None)

    def on_unmount(self) -> None:
        self._safe_close()


class HardwareCommissioningScreen(ModalScreen[None]):
    """A deliberately separate, safety-first hardware/commissioning mode.

    Widgets invoke the shared service; they never construct serial commands.
    """
    BINDINGS = [Binding("escape", "dismiss_screen", "Close")]
    DEFAULT_CSS = """
    HardwareCommissioningScreen { align: center middle; }
    #hardware-dialog {
        width: 82; height: 30; border: round $warning;
        background: $surface; padding: 1 2;
    }
    #hardware-actions { height: 3; }
    #hardware-status { height: 1fr; }
    """

    def __init__(self, tester_factory: Any) -> None:
        super().__init__()
        self._tester_factory = tester_factory

    def compose(self) -> ComposeResult:
        with Vertical(id="hardware-dialog"):
            yield Label("Commissioning / Hardware Test (dry-safe)")
            yield Label(
                "Physical actuation requires CLI confirmation. "
                "Emergency safe-state is always available."
            )
            with Grid(id="hardware-actions"):
                yield Button("Controller", id="hw-protocol")
                yield Button("Thermistors", id="hw-sensors")
                yield Button("OD electronics", id="hw-od")
                yield Button("Safe shutdown", variant="error", id="hw-safe")
            yield Static(
                "Choose a test. This mode uses the shared hardware service.",
                id="hardware-status",
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        from evolver_integrated.hardware.service import HardwareTester
        tester = HardwareTester(self._tester_factory())
        try:
            with tester.session():
                if event.button.id == "hw-protocol":
                    tester.protocol()
                elif event.button.id == "hw-sensors":
                    tester.sensor(0)
                    tester.sensor(1)
                elif event.button.id == "hw-od":
                    tester.od(0)
                    tester.od(1)
                else:
                    tester.safe_state()
            text = "\n".join(
                f"{item.status.value.upper()}: {item.id}"
                for item in tester.results
            )
            exchanges = "\n".join(
                f"TX {item.get('tx')} RX {item.get('rx')} "
                f"duration={item.get('duration_ms', '?')}ms"
                for item in tester.backend.debug_log
            )
            if exchanges:
                text += "\n" + exchanges
        except Exception as exc:
            text = f"Hardware error (outputs were asked to shut down): {exc}"
        self.query_one("#hardware-status", Static).update(text)

    def action_dismiss_screen(self) -> None:
        self.dismiss(None)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "untitled"


def _get_path(record: dict, path: str) -> Any:
    target: Any = record
    for part in path.split("."):
        if not isinstance(target, dict) or part not in target:
            return None
        target = target[part]
    return target


def _set_path(record: dict, path: str, value: Any) -> None:
    parts = path.split(".")
    target = record
    for part in parts[:-1]:
        child = target.get(part)
        if not isinstance(child, dict):
            child = {}
            target[part] = child
        target = child
    target[parts[-1]] = value


def record_from_template(
    template: dict,
    values: dict[str, str],
) -> dict:
    """Build a JSON object from a form template and raw field values."""
    record: dict = {}
    fields = template.get("fields", [])
    for field in fields:
        field_id = field["id"]
        raw = values.get(field_id, "").strip()
        if not raw and field.get("auto_id_from"):
            raw = _slug(values.get(field["auto_id_from"], ""))
        if field.get("required") and not raw:
            raise ValueError(f"{field['label']} is required")

        if field.get("kind") == "json":
            if raw:
                value = json.loads(raw)
            else:
                value = deepcopy(field.get("default"))
        else:
            value = raw

        if value not in ("", None):
            _set_path(record, field["path"], value)
    return record


class ExpandableTextArea(TextArea):
    """TextArea that grows while focused, capped by the terminal height."""

    COLLAPSED_HEIGHT = 8
    MIN_EXPANDED_HEIGHT = 8
    SHELL_MARGIN = 12

    def _watch_has_focus(self, focus: bool) -> None:
        super()._watch_has_focus(focus)
        self._refresh_dynamic_height()

    def _refresh_dynamic_height(self) -> None:
        text_lines = max(1, self.text.count("\n") + 1)
        if self.has_focus:
            shell_rows = getattr(self.app.size, "height", 32)
            max_height = max(
                self.MIN_EXPANDED_HEIGHT,
                shell_rows - self.SHELL_MARGIN,
            )
            target_height = min(
                max_height,
                max(self.MIN_EXPANDED_HEIGHT, text_lines + 1),
            )
        else:
            target_height = self.COLLAPSED_HEIGHT
        self.styles.height = target_height
        self.set_class(self.has_focus, "template-field-expanded")


class ConfirmScreen(ModalScreen[bool]):
    """Yes/no confirmation dialog."""

    BINDINGS = [
        Binding("escape", "dismiss_no", "No", show=True),
        Binding("y", "dismiss_yes", "Yes", show=True),
    ]

    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }
    #confirm-dialog {
        grid-size: 2;
        grid-rows: 1fr 3;
        grid-gutter: 1;
        height: 9;
        width: 54;
        border: round $warning;
        background: $surface;
        padding: 1 2;
    }
    #confirm-question {
        column-span: 2;
        content-align: center middle;
        height: 1fr;
    }
    """

    def __init__(self, question: str) -> None:
        super().__init__()
        self._question = question

    def compose(self) -> ComposeResult:
        with Grid(id="confirm-dialog"):
            yield Label(self._question, id="confirm-question")
            yield Button("Yes", variant="error", id="yes-btn")
            yield Button("No", variant="default", id="no-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes-btn")

    def action_dismiss_yes(self) -> None:
        self.dismiss(True)

    def action_dismiss_no(self) -> None:
        self.dismiss(False)


class NewExperimentScreen(ModalScreen[str | None]):
    """Prompt for a new experiment name."""

    BINDINGS = [
        Binding("escape", "dismiss_cancel", "Cancel", show=True),
    ]

    DEFAULT_CSS = """
    NewExperimentScreen {
        align: center middle;
    }
    #new-exp-dialog {
        grid-size: 2;
        grid-rows: auto auto 3;
        grid-gutter: 1;
        height: 13;
        width: 54;
        border: round $primary;
        background: $surface;
        padding: 1 2;
    }
    #new-exp-label {
        column-span: 2;
    }
    #name-input {
        column-span: 2;
    }
    """

    def compose(self) -> ComposeResult:
        with Grid(id="new-exp-dialog"):
            yield Label("New experiment name:", id="new-exp-label")
            yield Input(placeholder="my-experiment", id="name-input")
            yield Button("Create", variant="success", id="create-btn")
            yield Button("Cancel", variant="default", id="cancel-btn")

    def on_mount(self) -> None:
        self.query_one("#name-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create-btn":
            name = self.query_one("#name-input", Input).value.strip()
            self.dismiss(name or None)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        name = event.value.strip()
        self.dismiss(name or None)

    def action_dismiss_cancel(self) -> None:
        self.dismiss(None)


class TemplateFormScreen(ModalScreen[dict | None]):
    """Generate a JSON-object form from a template definition."""

    BINDINGS = [
        Binding("escape", "dismiss_cancel", "Cancel", show=True),
    ]

    DEFAULT_CSS = """
    TemplateFormScreen {
        align: center middle;
    }
    #template-form-dialog {
        width: 76;
        max-width: 90%;
        height: 90%;
        max-height: 36;
        border: round $primary;
        background: $surface;
        padding: 1 2;
    }
    #template-form-scroll {
        height: 1fr;
    }
    #template-form-title {
        text-style: bold;
        margin-bottom: 1;
    }
    .template-field-label {
        margin-top: 1;
    }
    .template-field {
        width: 1fr;
    }
    .template-json-field {
        width: 1fr;
        height: 8;
    }
    .template-field-expanded {
        border: tall $accent;
    }
    #template-form-error {
        color: $error;
        height: 1;
        margin-top: 1;
    }
    #template-form-actions {
        grid-size: 2;
        grid-gutter: 1;
        height: 3;
        margin-top: 1;
    }
    """

    def __init__(
        self,
        template: dict,
        initial_record: dict | None = None,
    ) -> None:
        super().__init__()
        self._template = template
        self._initial_record = initial_record or {}

    def compose(self) -> ComposeResult:
        with Vertical(id="template-form-dialog"):
            yield Label(
                self._template.get("title", "New JSON object"),
                id="template-form-title",
            )
            with VerticalScroll(id="template-form-scroll"):
                for field in self._template.get("fields", []):
                    yield Label(
                        field["label"],
                        classes="template-field-label",
                    )
                    field_id = f"template-field-{field['id']}"
                    initial_value = _get_path(
                        self._initial_record, field["path"]
                    )
                    if field.get("kind") == "json":
                        value = (
                            initial_value
                            if initial_value is not None
                            else field.get("default", [])
                        )
                        text = json.dumps(value, indent=2)
                        yield ExpandableTextArea(
                            text,
                            language="json",
                            id=field_id,
                            classes="template-field template-json-field",
                        )
                    else:
                        yield Input(
                            value=(
                                ""
                                if initial_value is None
                                else str(initial_value)
                            ),
                            placeholder=field.get("placeholder", ""),
                            id=field_id,
                            classes="template-field",
                        )
            yield Label("", id="template-form-error")
            with Grid(id="template-form-actions"):
                yield Button(
                    self._template.get("submit_label", "Create"),
                    variant="success",
                    id="template-submit",
                )
                yield Button("Cancel", variant="default", id="template-cancel")

    def on_mount(self) -> None:
        first = self.query(".template-field").first()
        if first is not None:
            first.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "template-cancel":
            self.dismiss(None)
            return
        self._submit()

    def _submit(self) -> None:
        values: dict[str, str] = {}
        for field in self._template.get("fields", []):
            widget_id = f"#template-field-{field['id']}"
            if field.get("kind") == "json":
                values[field["id"]] = self.query_one(widget_id, TextArea).text
            else:
                values[field["id"]] = self.query_one(widget_id, Input).value
        try:
            self.dismiss(record_from_template(self._template, values))
        except (json.JSONDecodeError, ValueError) as exc:
            self.query_one("#template-form-error", Label).update(str(exc))

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self._submit()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if isinstance(event.text_area, ExpandableTextArea):
            event.text_area._refresh_dynamic_height()

    def action_dismiss_cancel(self) -> None:
        self.dismiss(None)


class FuzzySearchScreen(ModalScreen[str | None]):
    """Live-filter search over a list of string items."""

    BINDINGS = [
        Binding("escape", "dismiss_cancel", "Cancel", show=True),
    ]

    DEFAULT_CSS = """
    FuzzySearchScreen {
        align: center middle;
    }
    #fuzzy-dialog {
        height: 20;
        width: 60;
        border: round $primary;
        background: $surface;
        padding: 1 2;
    }
    #fuzzy-input {
        width: 1fr;
        margin-bottom: 1;
    }
    #fuzzy-list {
        height: 1fr;
    }
    """

    def __init__(self, items: list, context: str = "") -> None:
        super().__init__()
        self._all_items: list[str] = [str(i) for i in items]
        self._context = context

    def compose(self) -> ComposeResult:
        with Vertical(id="fuzzy-dialog"):
            yield Label(
                f"Search{' — ' + self._context if self._context else ''}:",
                id="fuzzy-label",
            )
            yield Input(placeholder="type to filter...", id="fuzzy-input")
            yield ListView(id="fuzzy-list")

    def on_mount(self) -> None:
        self.query_one("#fuzzy-input", Input).focus()
        self._refresh_list(self._all_items)

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower()
        if query:
            filtered = [i for i in self._all_items if query in i.lower()]
        else:
            filtered = self._all_items
        self._refresh_list(filtered)

    def _refresh_list(self, items: list[str]) -> None:
        lv = self.query_one("#fuzzy-list", ListView)
        lv.clear()
        for item in items:
            lv.append(ListItem(Label(f" {item}")))
        if items:
            lv.index = 0

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        lv = self.query_one("#fuzzy-list", ListView)
        idx = lv.index
        query = self.query_one("#fuzzy-input", Input).value.lower()
        filtered = (
            [i for i in self._all_items if query in i.lower()]
            if query
            else self._all_items
        )
        if idx is not None and 0 <= idx < len(filtered):
            self.dismiss(filtered[idx])
        else:
            self.dismiss(None)

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        lv = self.query_one("#fuzzy-list", ListView)
        if lv.index is not None:
            self.on_list_view_selected(
                ListView.Selected(list_view=lv, item=None)  # type: ignore
            )
        else:
            self.dismiss(None)

    def action_dismiss_cancel(self) -> None:
        self.dismiss(None)
