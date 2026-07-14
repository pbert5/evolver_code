"""Left-column panels and main display for the eVOLVER TUI."""
from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, ListItem, ListView, Static
from textual.widgets import TabbedContent, TabPane

# ── shared constants ──────────────────────────────────────────────────────────

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

# Material type tags (drawn from lab submission metadata vocabulary)
MATERIAL_TYPES = [
    "organism",
    "growth_medium",
    "carbon_source",
    "nitrogen_source",
    "reagent",
    "starting_inoculum",
    "waste",
    "sample",
]


def _experiment_request(experiment: dict) -> dict:
    request = experiment.get("request", {})
    return request if isinstance(request, dict) else {}


def _experiment_name(experiment: dict) -> str:
    return experiment.get("name") or _experiment_request(experiment).get(
        "name", "?"
    )


def _experiment_protocol(experiment: dict) -> str:
    request = _experiment_request(experiment)
    metadata = request.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    return experiment.get("protocol") or metadata.get("protocol", "-")

# ── [1] Status ────────────────────────────────────────────────────────────────


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
            "[dim]space → jump to relevant panel[/dim]"
            if needs_action
            else ""
        )
        self.query_one("#status-hint", Static).update(hint)


# ── [2] Live (tabs: Experiments | Evolver Units | Processes) ──────────────────


class LivePanel(Widget):
    BORDER_TITLE = "[2] Live"

    _TABS = ["experiments", "evolvers", "processes"]

    BINDINGS = [
        Binding("[", "prev_tab", "Prev tab", show=False),
        Binding("]", "next_tab", "Next tab", show=False),
        Binding("/", "fuzzy_search", "Search", show=True),
        # Experiment actions (active when Experiments tab visible)
        Binding("p", "pause_or_resume", "Pause/Resume"),
        Binding("c", "cancel_exp", "Cancel"),
        Binding("n", "new_exp", "New"),
        Binding("r", "run_exp", "Run"),
    ]

    # ── messages ──────────────────────────────────────────────────────────────

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
        def __init__(
            self, experiment_id: str, experiment_name: str
        ) -> None:
            self.experiment_id = experiment_id
            self.experiment_name = experiment_name
            super().__init__()

    class RunRequested(Message):
        def __init__(self, experiment_id: str) -> None:
            self.experiment_id = experiment_id
            super().__init__()

    class NewRequested(Message):
        pass

    class FuzzySearchRequested(Message):
        def __init__(self, items: list, context: str) -> None:
            self.items = items
            self.context = context
            super().__init__()

    # ── compose ───────────────────────────────────────────────────────────────

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._experiments: list[dict] = []
        self._devices: list[dict] = []

    def compose(self) -> ComposeResult:
        with TabbedContent(id="live-tabs"):
            with TabPane("Experiments", id="experiments"):
                yield ListView(id="exp-list")
            with TabPane("Evolver Units", id="evolvers"):
                yield ListView(id="evolver-list")
            with TabPane("Processes", id="processes"):
                yield ListView(id="proc-list")

    def on_mount(self) -> None:
        self.query_one("#evolver-list", ListView).append(
            ListItem(Label("[dim]No eVOLVER units connected[/dim]"))
        )
        self.query_one("#proc-list", ListView).append(
            ListItem(Label("[dim]No active processes[/dim]"))
        )

    # ── tab navigation ────────────────────────────────────────────────────────

    def _tc(self) -> TabbedContent:
        return self.query_one("#live-tabs", TabbedContent)

    def action_next_tab(self) -> None:
        tc = self._tc()
        try:
            idx = self._TABS.index(tc.active)
        except ValueError:
            idx = 0
        tc.active = self._TABS[(idx + 1) % len(self._TABS)]

    def action_prev_tab(self) -> None:
        tc = self._tc()
        try:
            idx = self._TABS.index(tc.active)
        except ValueError:
            idx = 0
        tc.active = self._TABS[(idx - 1) % len(self._TABS)]

    def action_fuzzy_search(self) -> None:
        tc = self._tc()
        if tc.active == "experiments":
            items = [e.get("name", "?") for e in self._experiments]
            self.post_message(self.FuzzySearchRequested(items, "experiments"))

    # ── experiment list ───────────────────────────────────────────────────────

    def update_experiments(self, experiments: list[dict]) -> None:
        self._experiments = experiments
        lv = self.query_one("#exp-list", ListView)
        old_idx = lv.index if lv.index is not None else 0
        lv.clear()
        for exp in experiments:
            icon = _STATE_ICONS.get(exp.get("state", ""), "?")
            name = _experiment_name(exp)
            state = exp.get("state", "?")
            lv.append(ListItem(Label(f" {icon} {name}  [{state}]")))
        if experiments:
            lv.index = min(old_idx, len(experiments) - 1)

    def update_devices(self, devices: list[dict]) -> None:
        self._devices = devices
        lv = self.query_one("#evolver-list", ListView)
        lv.clear()
        if not devices:
            lv.append(
                ListItem(Label("[dim]No eVOLVER units connected[/dim]"))
            )
            return
        for dev in devices:
            name = dev.get("name", dev.get("id", "?"))
            state = dev.get("state", "unknown")
            icon = "●" if state == "active" else "○"
            lv.append(ListItem(Label(f" {icon} {name}  [{state}]")))

    def update_jobs(self, jobs: list[dict]) -> None:
        lv = self.query_one("#proc-list", ListView)
        lv.clear()
        if not jobs:
            lv.append(ListItem(Label("[dim]No active processes[/dim]")))
            return
        order = {"running": 0, "queued": 1, "pending": 2}
        for job in sorted(jobs, key=lambda j: order.get(j.get("state", ""), 9)):
            state = job.get("state", "?")
            name = job.get("name", job.get("job_type", "?"))
            icon = "●" if state in ("running", "queued") else "○"
            lv.append(ListItem(Label(f" {icon} {name}  [{state}]")))

    # ── selection events ──────────────────────────────────────────────────────

    def on_list_view_highlighted(self, _event: ListView.Highlighted) -> None:
        tc = self._tc()
        if tc.active != "experiments":
            return
        exp = self._focused_exp()
        if exp:
            self.post_message(self.ExperimentSelected(exp))

    # ── experiment actions ────────────────────────────────────────────────────

    def _focused_exp(self) -> Optional[dict]:
        idx = self.query_one("#exp-list", ListView).index
        if idx is not None and 0 <= idx < len(self._experiments):
            return self._experiments[idx]
        return None

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


# ── [3] Inventory (tabs: Protocols | Materials | Devices) ─────────────────────


class InventoryPanel(Widget):
    BORDER_TITLE = "[3] Inventory"

    _TABS = ["protocols", "materials", "devices"]

    BINDINGS = [
        Binding("[", "prev_tab", "Prev tab", show=False),
        Binding("]", "next_tab", "Next tab", show=False),
        Binding("/", "fuzzy_search", "Search", show=True),
        Binding("space", "select_item", "Select", show=True),
    ]

    class ProtocolSelected(Message):
        def __init__(self, protocol: dict) -> None:
            self.protocol = protocol
            super().__init__()

    class FuzzySearchRequested(Message):
        def __init__(self, items: list, context: str) -> None:
            self.items = items
            self.context = context
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._protocols: list[dict] = []
        self._materials: list[dict] = []
        self._hw_devices: list[dict] = []

    def compose(self) -> ComposeResult:
        with TabbedContent(id="inv-tabs"):
            with TabPane("Protocols", id="protocols"):
                yield ListView(id="proto-list")
            with TabPane("Materials", id="materials"):
                yield ListView(id="mat-list")
            with TabPane("Devices", id="devices"):
                yield ListView(id="dev-list")

    def on_mount(self) -> None:
        for list_id, msg in [
            ("#proto-list", "No protocols — create one first"),
            ("#mat-list", "No materials registered"),
            ("#dev-list", "No devices configured"),
        ]:
            self.query_one(list_id, ListView).append(
                ListItem(Label(f"[dim]{msg}[/dim]"))
            )

    # ── tab navigation ────────────────────────────────────────────────────────

    def _tc(self) -> TabbedContent:
        return self.query_one("#inv-tabs", TabbedContent)

    def action_next_tab(self) -> None:
        tc = self._tc()
        try:
            idx = self._TABS.index(tc.active)
        except ValueError:
            idx = 0
        tc.active = self._TABS[(idx + 1) % len(self._TABS)]

    def action_prev_tab(self) -> None:
        tc = self._tc()
        try:
            idx = self._TABS.index(tc.active)
        except ValueError:
            idx = 0
        tc.active = self._TABS[(idx - 1) % len(self._TABS)]

    def action_fuzzy_search(self) -> None:
        tc = self._tc()
        if tc.active == "protocols":
            items = [p.get("name", "?") for p in self._protocols]
            self.post_message(
                self.FuzzySearchRequested(items, "protocols")
            )
        elif tc.active == "materials":
            items = [m.get("name", "?") for m in self._materials]
            self.post_message(
                self.FuzzySearchRequested(items, "materials")
            )

    # ── select (space/enter) loads protocol context into W4/W5 ───────────────

    def action_select_item(self) -> None:
        tc = self._tc()
        if tc.active == "protocols":
            proto = self._focused_protocol()
            if proto:
                self.post_message(self.ProtocolSelected(proto))

    def on_list_view_selected(self, _event: ListView.Selected) -> None:
        self.action_select_item()

    def _focused_protocol(self) -> Optional[dict]:
        idx = self.query_one("#proto-list", ListView).index
        if idx is not None and 0 <= idx < len(self._protocols):
            return self._protocols[idx]
        return None

    # ── data refresh ──────────────────────────────────────────────────────────

    def update_protocols(self, protocols: list[dict]) -> None:
        self._protocols = protocols
        lv = self.query_one("#proto-list", ListView)
        old_idx = lv.index if lv.index is not None else 0
        lv.clear()
        if not protocols:
            lv.append(ListItem(Label("[dim]No protocols — create one first[/dim]")))
            return
        for proto in protocols:
            name = proto.get("name", "?")
            steps = len(proto.get("steps", []))
            lv.append(ListItem(Label(f" ○ {name}  [{steps} steps]")))
        lv.index = min(old_idx, len(protocols) - 1)

    def update_materials(self, materials: list[dict]) -> None:
        self._materials = materials
        lv = self.query_one("#mat-list", ListView)
        lv.clear()
        if not materials:
            lv.append(ListItem(Label("[dim]No materials registered[/dim]")))
            return
        for mat in materials:
            name = mat.get("name", "?")
            mat_type = mat.get("type", "?")
            mat_id = mat.get("id", "")
            lv.append(ListItem(Label(f" · {name}  [{mat_type}]  {mat_id}")))

    def update_hw_devices(self, devices: list[dict]) -> None:
        self._hw_devices = devices
        lv = self.query_one("#dev-list", ListView)
        lv.clear()
        if not devices:
            lv.append(ListItem(Label("[dim]No devices configured[/dim]")))
            return
        for dev in devices:
            name = dev.get("name", "?")
            dev_type = dev.get("type", "?")
            role = dev.get("io_role", "")
            suffix = f"  [{role}]" if role else ""
            lv.append(ListItem(Label(f" · {name}  [{dev_type}]{suffix}")))


# ── [4] Steps ─────────────────────────────────────────────────────────────────


class StepsPanel(Widget):
    BORDER_TITLE = "[4] Steps"

    BINDINGS = [
        Binding("/", "fuzzy_search", "Search", show=False),
    ]

    class StepSelected(Message):
        def __init__(self, step: dict, step_idx: int) -> None:
            self.step = step
            self.step_idx = step_idx
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._steps: list[dict] = []
        self._protocol_name: str = ""
        self._current_step: int = -1

    def compose(self) -> ComposeResult:
        yield Static(
            "[dim]Select a protocol in [3] to view steps[/dim]",
            id="steps-header",
        )
        yield ListView(id="steps-list")

    def load_protocol(
        self,
        protocol: dict,
        current_step: int = -1,
    ) -> None:
        self._protocol_name = protocol.get("name", "?")
        self._steps = protocol.get("steps", [])
        self._current_step = current_step
        self.BORDER_TITLE = f"[4] Steps — {self._protocol_name}"
        self.query_one("#steps-header", Static).update(
            f"[bold]{self._protocol_name}[/bold]  "
            f"[dim]{len(self._steps)} steps[/dim]"
        )
        lv = self.query_one("#steps-list", ListView)
        lv.clear()
        if not self._steps:
            lv.append(ListItem(Label("[dim]No steps defined[/dim]")))
            return
        for i, step in enumerate(self._steps):
            if i < current_step:
                icon = "●"
            elif i == current_step:
                icon = "◌"
            else:
                icon = "○"
            label = (
                step.get("name", str(step))
                if isinstance(step, dict)
                else str(step)
            )
            lv.append(ListItem(Label(f" {icon} {i + 1}. {label}")))

    def on_list_view_highlighted(
        self, _event: ListView.Highlighted
    ) -> None:
        idx = self.query_one("#steps-list", ListView).index
        if idx is not None and 0 <= idx < len(self._steps):
            self.post_message(self.StepSelected(self._steps[idx], idx))

    def action_fuzzy_search(self) -> None:
        pass


# ── [5] Components ────────────────────────────────────────────────────────────


class ComponentsPanel(Widget):
    BORDER_TITLE = "[5] Components"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._protocol: Optional[dict] = None
        self._step: Optional[dict] = None
        self._step_idx: int = -1

    def compose(self) -> ComposeResult:
        yield Static(
            "[dim]Select a step in [4] to view components[/dim]",
            id="comp-header",
        )
        yield ListView(id="comp-list")

    def load_protocol(self, protocol: dict) -> None:
        self._protocol = protocol
        self._step = None
        self._step_idx = -1
        self.query_one("#comp-header", Static).update(
            "[dim]Select a step in [4][/dim]"
        )
        self.query_one("#comp-list", ListView).clear()

    def load_step(self, step: dict, step_idx: int) -> None:
        self._step = step
        self._step_idx = step_idx
        step_name = (
            step.get("name", f"Step {step_idx + 1}")
            if isinstance(step, dict)
            else str(step)
        )
        self.query_one("#comp-header", Static).update(
            f"[bold]{step_name}[/bold]  [dim]components[/dim]"
        )
        lv = self.query_one("#comp-list", ListView)
        lv.clear()
        components = (
            step.get("components", []) if isinstance(step, dict) else []
        )
        if not components:
            lv.append(
                ListItem(Label("[dim]No components defined for this step[/dim]"))
            )
            return
        for comp in components:
            name = comp.get("name", "?") if isinstance(comp, dict) else str(comp)
            comp_type = comp.get("type", "") if isinstance(comp, dict) else ""
            role = comp.get("io_role", "") if isinstance(comp, dict) else ""
            suffix = f"  [{role}]" if role else ""
            lv.append(ListItem(Label(f" · {name}  [{comp_type}]{suffix}")))


# ── [0] Main Display ──────────────────────────────────────────────────────────


class MainDisplay(Widget):
    BORDER_TITLE = "[ Main ]"

    _WELCOME = (
        "[bold]eVOLVER Control[/bold]\n\n"
        "Select an item from the left panels.\n\n"
        "[dim]1[/dim] Status  "
        "[dim]2[/dim] Live  "
        "[dim]3[/dim] Inventory  "
        "[dim]4[/dim] Steps  "
        "[dim]5[/dim] Components"
    )

    def compose(self) -> ComposeResult:
        yield Static(self._WELCOME, id="main-content")

    def show_experiment(self, experiment: dict) -> None:
        name = _experiment_name(experiment)
        state = experiment.get("state", "?")
        exp_id = experiment.get("id", "?")
        created_at = experiment.get("created_at", "?")
        protocol = _experiment_protocol(experiment)
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

    def show_protocol(self, protocol: dict) -> None:
        name = protocol.get("name", "?")
        steps = protocol.get("steps", [])
        lines = [
            f"[bold]Protocol: {name}[/bold]",
            "",
            f"  Steps:  {len(steps)}",
        ]
        self.query_one("#main-content", Static).update("\n".join(lines))

    def show_welcome(self) -> None:
        self.query_one("#main-content", Static).update(self._WELCOME)
