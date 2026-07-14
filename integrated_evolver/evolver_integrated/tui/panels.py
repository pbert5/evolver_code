"""Left-column panels and main display for the eVOLVER TUI."""
from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, ListItem, ListView, Static

_STATE_ICONS = {
    "created": "○",
    "running": "●",
    "paused": "⏸",
    "stopped": "✗",
    "failed": "✗",
}

_STATUS_DISPLAY = {
    "ok": ("green", "Idle"),
    "running": ("yellow", "Experiment in progress"),
    "disconnected": ("red", "Control plane unreachable"),
    "permission_needed": ("magenta", "Permission needed"),
    "calibration_needed": ("magenta", "Calibration needed"),
    "error": ("red", "Error"),
}


class StatusPanel(Widget):
    BORDER_TITLE = "[1] Status"

    def compose(self) -> ComposeResult:
        yield Static("Connecting...", id="status-text")
        yield Static("", id="status-hint")

    def update_status(self, status: str, detail: str = "") -> None:
        color, label = _STATUS_DISPLAY.get(status, ("white", status))
        self.query_one("#status-text", Static).update(
            f"[bold {color}]{label}[/bold {color}]"
        )
        needs_action = status not in ("ok", "disconnected")
        hint = detail or (
            "[dim]Press space to jump to relevant panel[/dim]"
            if needs_action
            else ""
        )
        self.query_one("#status-hint", Static).update(hint)


class ExperimentsPanel(Widget):
    BORDER_TITLE = "[2] Experiments"

    BINDINGS = [
        Binding("p", "pause_or_resume", "Pause/Resume"),
        Binding("c", "cancel_exp", "Cancel"),
        Binding("n", "new_exp", "New"),
        Binding("r", "run_exp", "Run"),
    ]

    class ExperimentSelected(Message):
        def __init__(self, experiment: dict) -> None:
            self.experiment = experiment
            super().__init__()

    class PauseRequested(Message):
        def __init__(self, experiment_id: str) -> None:
            self.experiment_id = experiment_id
            super().__init__()

    class ResumeRequested(Message):
        def __init__(self, experiment_id: str) -> None:
            self.experiment_id = experiment_id
            super().__init__()

    class StopRequested(Message):
        def __init__(self, experiment_id: str, experiment_name: str) -> None:
            self.experiment_id = experiment_id
            self.experiment_name = experiment_name
            super().__init__()

    class RunRequested(Message):
        def __init__(self, experiment_id: str) -> None:
            self.experiment_id = experiment_id
            super().__init__()

    class NewRequested(Message):
        pass

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._experiments: list[dict] = []

    def compose(self) -> ComposeResult:
        yield ListView(id="exp-list")

    def update_experiments(self, experiments: list[dict]) -> None:
        self._experiments = experiments
        lv = self.query_one("#exp-list", ListView)
        old_idx = lv.index if lv.index is not None else 0
        lv.clear()
        for exp in experiments:
            icon = _STATE_ICONS.get(exp.get("state", ""), "?")
            name = exp.get("name", "?")
            state = exp.get("state", "?")
            lv.append(ListItem(Label(f" {icon} {name}  [{state}]")))
        if experiments:
            lv.index = min(old_idx, len(experiments) - 1)

    def _focused_exp(self) -> Optional[dict]:
        idx = self.query_one("#exp-list", ListView).index
        if idx is not None and 0 <= idx < len(self._experiments):
            return self._experiments[idx]
        return None

    def on_list_view_highlighted(self, _event: ListView.Highlighted) -> None:
        exp = self._focused_exp()
        if exp:
            self.post_message(self.ExperimentSelected(exp))

    def action_pause_or_resume(self) -> None:
        exp = self._focused_exp()
        if not exp:
            return
        if exp.get("state") == "paused":
            self.post_message(self.ResumeRequested(exp["id"]))
        else:
            self.post_message(self.PauseRequested(exp["id"]))

    def action_cancel_exp(self) -> None:
        exp = self._focused_exp()
        if exp:
            self.post_message(
                self.StopRequested(exp["id"], exp.get("name", ""))
            )

    def action_run_exp(self) -> None:
        exp = self._focused_exp()
        if exp:
            self.post_message(self.RunRequested(exp["id"]))

    def action_new_exp(self) -> None:
        self.post_message(self.NewRequested())


class ProtocolsPanel(Widget):
    BORDER_TITLE = "[3] Protocol"

    def compose(self) -> ComposeResult:
        yield ListView(id="protocol-list")

    def update_protocol(self, protocol: dict) -> None:
        lv = self.query_one("#protocol-list", ListView)
        lv.clear()
        steps = protocol.get("steps", [])
        if not steps:
            lv.append(ListItem(Label("[dim]No steps defined[/dim]")))
            return
        current = protocol.get("current_step", -1)
        for i, step in enumerate(steps):
            if i < current:
                icon = "●"
            elif i == current:
                icon = "◌"
            else:
                icon = "○"
            label = (
                step.get("name", str(step))
                if isinstance(step, dict)
                else str(step)
            )
            lv.append(ListItem(Label(f" {icon} {i + 1}. {label}")))


class BioreactorsPanel(Widget):
    BORDER_TITLE = "[4] Bioreactors"

    class BioreactorSelected(Message):
        def __init__(self, device: dict) -> None:
            self.device = device
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._devices: list[dict] = []

    def compose(self) -> ComposeResult:
        yield ListView(id="bio-list")

    def on_mount(self) -> None:
        self._refresh_placeholder()

    def update_devices(self, devices: list[dict]) -> None:
        self._devices = devices
        lv = self.query_one("#bio-list", ListView)
        lv.clear()
        if not devices:
            self._refresh_placeholder()
            return
        for dev in devices:
            name = dev.get("name", dev.get("id", "?"))
            state = dev.get("state", "unknown")
            icon = "●" if state == "active" else "○"
            lv.append(ListItem(Label(f" {icon} {name}  [{state}]")))

    def _refresh_placeholder(self) -> None:
        lv = self.query_one("#bio-list", ListView)
        lv.clear()
        lv.append(ListItem(Label("[dim]No bioreactors connected[/dim]")))

    def on_list_view_highlighted(self, _event: ListView.Highlighted) -> None:
        idx = self.query_one("#bio-list", ListView).index
        if idx is not None and 0 <= idx < len(self._devices):
            self.post_message(self.BioreactorSelected(self._devices[idx]))


class ProcessesPanel(Widget):
    BORDER_TITLE = "[5] Processes"

    def compose(self) -> ComposeResult:
        yield ListView(id="proc-list")

    def on_mount(self) -> None:
        lv = self.query_one("#proc-list", ListView)
        lv.append(ListItem(Label("[dim]No active jobs[/dim]")))

    def update_jobs(self, jobs: list[dict]) -> None:
        lv = self.query_one("#proc-list", ListView)
        lv.clear()
        if not jobs:
            lv.append(ListItem(Label("[dim]No active jobs[/dim]")))
            return
        # order by importance: running > queued > pending > rest
        order = {"running": 0, "queued": 1, "pending": 2}
        jobs = sorted(jobs, key=lambda j: order.get(j.get("state", ""), 99))
        for job in jobs:
            state = job.get("state", "?")
            name = job.get("name", job.get("job_type", "?"))
            icon = "●" if state in ("running", "queued") else "○"
            lv.append(ListItem(Label(f" {icon} {name}  [{state}]")))


class MainDisplay(Widget):
    BORDER_TITLE = "[ Main ]"

    _WELCOME = (
        "[bold]eVOLVER Control[/bold]\n\n"
        "Select an item from the left panels to view details.\n\n"
        "[dim]1[/dim] Status   [dim]2[/dim] Experiments   "
        "[dim]3[/dim] Protocols  "
        "[dim]4[/dim] Bioreactors  "
        "[dim]5[/dim] Processes"
    )

    def compose(self) -> ComposeResult:
        yield Static(self._WELCOME, id="main-content")

    def show_experiment(self, experiment: dict) -> None:
        name = experiment.get("name", "?")
        state = experiment.get("state", "?")
        exp_id = experiment.get("id", "?")
        created_at = experiment.get("created_at", "?")
        protocol = experiment.get("protocol", "—")
        icon = _STATE_ICONS.get(state, "?")
        if state == "running":
            color = "yellow"
        elif state == "created":
            color = "green"
        else:
            color = "red"

        lines = [
            f"[bold]{name}[/bold]",
            "",
            f"  State:     {icon} [{color}]{state}[/{color}]",
            f"  ID:        [dim]{exp_id}[/dim]",
            f"  Protocol:  {protocol}",
            f"  Created:   {created_at}",
        ]
        self.query_one("#main-content", Static).update("\n".join(lines))

    def show_device(self, device: dict) -> None:
        name = device.get("name", device.get("id", "?"))
        state = device.get("state", "unknown")
        lines = [
            f"[bold]Bioreactor: {name}[/bold]",
            "",
            f"  State:  {state}",
        ]
        self.query_one("#main-content", Static).update("\n".join(lines))

    def show_welcome(self) -> None:
        self.query_one("#main-content", Static).update(self._WELCOME)
