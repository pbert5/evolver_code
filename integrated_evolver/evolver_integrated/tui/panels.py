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
    "running": "◉",
    "paused": "⏸",
    "stopped": "□",
    "failed": "✗",
    "unknown": "?",
}

_SERVICE_STATE_DISPLAY = {
    "running": ("green", "○"),
    "paused": ("yellow", "⏸"),
    "stopped": ("dim", "□"),
    "cancelled": ("red", "■"),
    "canceled": ("red", "■"),
    "failed": ("red", "✗"),
    "unknown": ("white", "?"),
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


def _item_key(item: dict, fallback: str = "") -> str:
    for key in ("id", "name"):
        value = item.get(key)
        if value:
            return str(value)
    return fallback


def _restore_list_index(
    list_view: ListView,
    items: list[dict],
    old_key: Optional[str],
    old_idx: Optional[int],
) -> None:
    if not items:
        list_view.index = None
        _mark_list_selection(list_view)
        return
    if old_key is None and old_idx is None:
        list_view.index = None
        _mark_list_selection(list_view)
        return
    idx = 0 if old_idx is None else min(old_idx, len(items) - 1)
    if old_key is not None:
        for candidate_idx, item in enumerate(items):
            if _item_key(item, str(candidate_idx)) == old_key:
                idx = candidate_idx
                break
    list_view.index = idx
    _mark_list_selection(list_view)


def _mark_list_selection(list_view: ListView) -> None:
    idx = list_view.index
    for child_idx, child in enumerate(list_view.children):
        if not isinstance(child, ListItem):
            continue
        child.set_class(child_idx == idx, "persistent-highlight")

# ── [1] Status ────────────────────────────────────────────────────────────────


class StatusPanel(Widget, can_focus=True):
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

    def focus_default(self) -> None:
        self.focus()


# ── [2] Live (tabs: Experiments | Evolver Units | Services) ───────────────────


class LivePanel(Widget):
    BORDER_TITLE = "[2] Live"

    _TABS = ["experiments", "evolvers", "services"]

    BINDINGS = [
        Binding("[", "prev_tab", "Prev tab", show=False),
        Binding("]", "next_tab", "Next tab", show=False),
        Binding("/", "fuzzy_search", "Search", show=True),
        Binding("a", "new_exp", "Add experiment"),
        Binding("e", "edit_item", "Edit"),
        Binding("delete", "delete_item", "Delete"),
        Binding("p", "pause_or_resume", "Pause/Resume"),
        Binding("c", "cancel_exp", "Cancel"),
        Binding("r", "run_or_restart", "Run/Restart"),
        Binding("s", "start_service", "Start", show=False),
        Binding("x", "stop_service", "Stop", show=False),
    ]

    class ExperimentSelected(Message):
        def __init__(self, experiment: dict) -> None:
            self.experiment = experiment
            super().__init__()

    class EvolverSelected(Message):
        def __init__(self, evolver: dict) -> None:
            self.evolver = evolver
            super().__init__()

    class ServiceSelected(Message):
        def __init__(self, service: dict) -> None:
            self.service = service
            super().__init__()

    class ScopeFocused(Message):
        def __init__(self, scope: str) -> None:
            self.scope = scope
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

    class ServiceActionRequested(Message):
        def __init__(self, service_id: str, action: str) -> None:
            self.service_id = service_id
            self.action = action
            super().__init__()

    class NewRequested(Message):
        pass

    class FuzzySearchRequested(Message):
        def __init__(self, items: list, context: str) -> None:
            self.items = items
            self.context = context
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._experiments: list[dict] = []
        self._devices: list[dict] = []
        self._services: list[dict] = []

    def compose(self) -> ComposeResult:
        with TabbedContent(id="live-tabs"):
            with TabPane("Experiments", id="experiments"):
                yield ListView(id="exp-list")
            with TabPane("Evolver Units", id="evolvers"):
                yield ListView(id="evolver-list")
            with TabPane("Services", id="services"):
                yield ListView(id="service-list")

    def on_mount(self) -> None:
        self.query_one("#evolver-list", ListView).append(
            ListItem(Label("[dim]No eVOLVER units connected[/dim]"))
        )
        self.query_one("#service-list", ListView).append(
            ListItem(Label("[dim]No configured services[/dim]"))
        )

    def focus_default(self) -> None:
        list_view = self.query_one(self._active_list_selector(), ListView)
        _mark_list_selection(list_view)
        list_view.focus()
        self._post_current_context()

    def _active_list_selector(self) -> str:
        return {
            "experiments": "#exp-list",
            "evolvers": "#evolver-list",
            "services": "#service-list",
        }.get(self._tc().active, "#exp-list")

    def _tc(self) -> TabbedContent:
        return self.query_one("#live-tabs", TabbedContent)

    def action_next_tab(self) -> None:
        self._switch_tab(1)

    def action_prev_tab(self) -> None:
        self._switch_tab(-1)

    def _switch_tab(self, delta: int) -> None:
        tc = self._tc()
        try:
            idx = self._TABS.index(tc.active)
        except ValueError:
            idx = 0
        tc.active = self._TABS[(idx + delta) % len(self._TABS)]
        self.call_after_refresh(self.focus_default)

    def on_tabbed_content_tab_activated(
        self, _event: TabbedContent.TabActivated
    ) -> None:
        self.call_after_refresh(self.focus_default)

    def action_fuzzy_search(self) -> None:
        tc = self._tc()
        if tc.active == "experiments":
            items = [_experiment_name(e) for e in self._experiments]
            self.post_message(self.FuzzySearchRequested(items, "experiments"))
        elif tc.active == "evolvers":
            items = [d.get("name", d.get("id", "?")) for d in self._devices]
            self.post_message(self.FuzzySearchRequested(items, "evolver units"))
        elif tc.active == "services":
            items = [s.get("name", s.get("id", "?")) for s in self._services]
            self.post_message(self.FuzzySearchRequested(items, "services"))

    def update_experiments(self, experiments: list[dict]) -> None:
        lv = self.query_one("#exp-list", ListView)
        old_idx = lv.index
        old_key = (
            _item_key(self._experiments[old_idx], str(old_idx))
            if old_idx is not None and 0 <= old_idx < len(self._experiments)
            else None
        )
        self._experiments = experiments
        lv.clear()
        for exp in experiments:
            icon = _STATE_ICONS.get(exp.get("state", ""), "?")
            name = _experiment_name(exp)
            state = exp.get("state", "?")
            lv.append(ListItem(Label(f" {icon} {name}  [{state}]")))
        _restore_list_index(lv, experiments, old_key, old_idx)

    def update_devices(self, devices: list[dict]) -> None:
        lv = self.query_one("#evolver-list", ListView)
        old_idx = lv.index
        old_key = (
            _item_key(self._devices[old_idx], str(old_idx))
            if old_idx is not None and 0 <= old_idx < len(self._devices)
            else None
        )
        self._devices = devices
        lv.clear()
        if not devices:
            lv.append(
                ListItem(Label("[dim]No eVOLVER units connected[/dim]"))
            )
            lv.index = None
            _mark_list_selection(lv)
            return
        for dev in devices:
            name = dev.get("name", dev.get("id", "?"))
            state = dev.get("state", "unknown")
            icon = "●" if state == "active" else "○"
            lv.append(ListItem(Label(f" {icon} {name}  [{state}]")))
        _restore_list_index(lv, devices, old_key, old_idx)

    def update_jobs(self, jobs: list[dict]) -> None:
        lv = self.query_one("#service-list", ListView)
        lv.clear()
        if not jobs:
            lv.append(ListItem(Label("[dim]No one-shot runs[/dim]")))
            lv.index = None
            _mark_list_selection(lv)
            return
        order = {"running": 0, "queued": 1, "pending": 2}
        for job in sorted(jobs, key=lambda j: order.get(j.get("state", ""), 9)):
            state = job.get("state", "?")
            name = job.get("name", job.get("job_type", "?"))
            icon = "●" if state in ("running", "queued") else "○"
            lv.append(ListItem(Label(f" {icon} {name}  [{state}]")))
        _restore_list_index(lv, jobs, None, lv.index)

    def update_services(self, services: list[dict]) -> None:
        if services == self._services:
            return
        lv = self.query_one("#service-list", ListView)
        old_idx = lv.index
        old_key = (
            _item_key(self._services[old_idx], str(old_idx))
            if old_idx is not None and 0 <= old_idx < len(self._services)
            else None
        )
        self._services = services
        lv.clear()
        if not services:
            lv.append(ListItem(Label("[dim]No configured services[/dim]")))
            lv.index = None
            _mark_list_selection(lv)
            return
        for service in services:
            state = service.get("state", "unknown")
            color, icon = _SERVICE_STATE_DISPLAY.get(
                state, _SERVICE_STATE_DISPLAY["unknown"]
            )
            name = service.get("name", service.get("id", "?"))
            category = service.get("category", "?")
            lv.append(
                ListItem(
                    Label(
                        f" [{color}]{icon}[/{color}] {name}"
                        f"  [{category}/{state}]"
                    )
                )
            )
        _restore_list_index(lv, services, old_key, old_idx)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        _mark_list_selection(event.list_view)
        self._post_current_context()

    def _post_current_context(self) -> None:
        tc = self._tc()
        if tc.active == "experiments":
            exp = self._focused_exp()
            if exp:
                self.post_message(self.ExperimentSelected(exp))
            else:
                self.post_message(self.ScopeFocused("live.experiments"))
        elif tc.active == "evolvers":
            evolver = self._focused_evolver()
            if evolver:
                self.post_message(self.EvolverSelected(evolver))
            else:
                self.post_message(self.ScopeFocused("live.evolvers"))
        elif tc.active == "services":
            service = self._focused_service()
            if service:
                self.post_message(self.ServiceSelected(service))
            else:
                self.post_message(self.ScopeFocused("live.services"))

    def _focused_exp(self) -> Optional[dict]:
        idx = self.query_one("#exp-list", ListView).index
        if idx is not None and 0 <= idx < len(self._experiments):
            return self._experiments[idx]
        return None

    def _focused_evolver(self) -> Optional[dict]:
        idx = self.query_one("#evolver-list", ListView).index
        if idx is not None and 0 <= idx < len(self._devices):
            return self._devices[idx]
        return None

    def action_pause_or_resume(self) -> None:
        if self._tc().active == "services":
            service = self._focused_service()
            if not service:
                return
            action = "resume" if service.get("state") == "paused" else "pause"
            self.post_message(
                self.ServiceActionRequested(service["id"], action)
            )
            return
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
                self.StopRequested(exp["id"], _experiment_name(exp))
            )

    def _focused_service(self) -> Optional[dict]:
        idx = self.query_one("#service-list", ListView).index
        if idx is not None and 0 <= idx < len(self._services):
            return self._services[idx]
        return None

    def action_run_or_restart(self) -> None:
        if self._tc().active == "services":
            service = self._focused_service()
            if service:
                self.post_message(
                    self.ServiceActionRequested(service["id"], "restart")
                )
            return
        exp = self._focused_exp()
        if exp:
            self.post_message(self.RunRequested(exp["id"]))

    def action_new_exp(self) -> None:
        self.post_message(self.NewRequested())

    def action_edit_item(self) -> None:
        self.post_message(self.ScopeFocused(f"edit.{self._tc().active}"))

    def action_delete_item(self) -> None:
        self.post_message(self.ScopeFocused(f"delete.{self._tc().active}"))

    def action_start_service(self) -> None:
        service = self._focused_service()
        if service:
            self.post_message(
                self.ServiceActionRequested(service["id"], "start")
            )

    def action_stop_service(self) -> None:
        service = self._focused_service()
        if service:
            self.post_message(
                self.ServiceActionRequested(service["id"], "stop")
            )


# ── [3] Inventory (tabs: Protocols | Materials | Devices) ─────────────────────


class InventoryPanel(Widget):
    BORDER_TITLE = "[3] Inventory"

    _TABS = ["protocols", "materials", "devices"]

    BINDINGS = [
        Binding("[", "prev_tab", "Prev tab", show=False),
        Binding("]", "next_tab", "Next tab", show=False),
        Binding("/", "fuzzy_search", "Search", show=True),
        Binding("space", "select_item", "Set active", show=True),
        Binding("a", "add_item", "Add"),
        Binding("e", "edit_item", "Edit"),
        Binding("delete", "delete_item", "Delete"),
        Binding("u", "auto_discover", "Discover", show=False),
    ]

    class ProtocolSelected(Message):
        def __init__(self, protocol: dict) -> None:
            self.protocol = protocol
            super().__init__()

    class MaterialSelected(Message):
        def __init__(self, material: dict) -> None:
            self.material = material
            super().__init__()

    class DeviceSelected(Message):
        def __init__(self, device: dict) -> None:
            self.device = device
            super().__init__()

    class ScopeFocused(Message):
        def __init__(self, scope: str) -> None:
            self.scope = scope
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

    def focus_default(self) -> None:
        list_view = self.query_one(self._active_list_selector(), ListView)
        _mark_list_selection(list_view)
        list_view.focus()
        self._post_current_context()

    def _active_list_selector(self) -> str:
        return {
            "protocols": "#proto-list",
            "materials": "#mat-list",
            "devices": "#dev-list",
        }.get(self._tc().active, "#proto-list")

    def _tc(self) -> TabbedContent:
        return self.query_one("#inv-tabs", TabbedContent)

    def action_next_tab(self) -> None:
        self._switch_tab(1)

    def action_prev_tab(self) -> None:
        self._switch_tab(-1)

    def _switch_tab(self, delta: int) -> None:
        tc = self._tc()
        try:
            idx = self._TABS.index(tc.active)
        except ValueError:
            idx = 0
        tc.active = self._TABS[(idx + delta) % len(self._TABS)]
        self.call_after_refresh(self.focus_default)

    def on_tabbed_content_tab_activated(
        self, _event: TabbedContent.TabActivated
    ) -> None:
        self.call_after_refresh(self.focus_default)

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
        elif tc.active == "devices":
            items = [d.get("name", "?") for d in self._hw_devices]
            self.post_message(self.FuzzySearchRequested(items, "devices"))

    def action_select_item(self) -> None:
        self._post_current_context(activate=True)

    def on_list_view_selected(self, _event: ListView.Selected) -> None:
        self.action_select_item()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        _mark_list_selection(event.list_view)
        self._post_current_context()

    def _post_current_context(self, activate: bool = False) -> None:
        tc = self._tc()
        if tc.active == "protocols":
            proto = self._focused_protocol()
            if proto:
                self.post_message(self.ProtocolSelected(proto))
            else:
                self.post_message(self.ScopeFocused("inventory.protocols"))
        elif tc.active == "materials":
            material = self._focused_material()
            if material:
                self.post_message(self.MaterialSelected(material))
            else:
                self.post_message(self.ScopeFocused("inventory.materials"))
        elif tc.active == "devices":
            device = self._focused_device()
            if device:
                self.post_message(self.DeviceSelected(device))
            else:
                self.post_message(self.ScopeFocused("inventory.devices"))

    def _focused_protocol(self) -> Optional[dict]:
        idx = self.query_one("#proto-list", ListView).index
        if idx is not None and 0 <= idx < len(self._protocols):
            return self._protocols[idx]
        return None

    def _focused_material(self) -> Optional[dict]:
        idx = self.query_one("#mat-list", ListView).index
        if idx is not None and 0 <= idx < len(self._materials):
            return self._materials[idx]
        return None

    def _focused_device(self) -> Optional[dict]:
        idx = self.query_one("#dev-list", ListView).index
        if idx is not None and 0 <= idx < len(self._hw_devices):
            return self._hw_devices[idx]
        return None

    def update_protocols(self, protocols: list[dict]) -> None:
        lv = self.query_one("#proto-list", ListView)
        old_idx = lv.index
        old_key = (
            _item_key(self._protocols[old_idx], str(old_idx))
            if old_idx is not None and 0 <= old_idx < len(self._protocols)
            else None
        )
        self._protocols = protocols
        lv.clear()
        if not protocols:
            lv.append(ListItem(Label("[dim]No protocols — create one first[/dim]")))
            lv.index = None
            _mark_list_selection(lv)
            return
        for proto in protocols:
            name = proto.get("name", "?")
            steps = len(proto.get("steps", []))
            lv.append(ListItem(Label(f" ○ {name}  [{steps} steps]")))
        _restore_list_index(lv, protocols, old_key, old_idx)

    def update_materials(self, materials: list[dict]) -> None:
        lv = self.query_one("#mat-list", ListView)
        old_idx = lv.index
        old_key = (
            _item_key(self._materials[old_idx], str(old_idx))
            if old_idx is not None and 0 <= old_idx < len(self._materials)
            else None
        )
        self._materials = materials
        lv.clear()
        if not materials:
            lv.append(ListItem(Label("[dim]No materials registered[/dim]")))
            lv.index = None
            _mark_list_selection(lv)
            return
        for mat in materials:
            name = mat.get("name", "?")
            mat_type = mat.get("type", "?")
            mat_id = mat.get("id", "")
            lv.append(ListItem(Label(f" · {name}  [{mat_type}]  {mat_id}")))
        _restore_list_index(lv, materials, old_key, old_idx)

    def update_hw_devices(self, devices: list[dict]) -> None:
        lv = self.query_one("#dev-list", ListView)
        old_idx = lv.index
        old_key = (
            _item_key(self._hw_devices[old_idx], str(old_idx))
            if old_idx is not None and 0 <= old_idx < len(self._hw_devices)
            else None
        )
        self._hw_devices = devices
        lv.clear()
        if not devices:
            lv.append(ListItem(Label("[dim]No devices configured[/dim]")))
            lv.index = None
            _mark_list_selection(lv)
            return
        for dev in devices:
            name = dev.get("name", "?")
            dev_type = dev.get("type", "?")
            role = dev.get("io_role", "")
            suffix = f"  [{role}]" if role else ""
            lv.append(ListItem(Label(f" · {name}  [{dev_type}]{suffix}")))
        _restore_list_index(lv, devices, old_key, old_idx)

    def action_add_item(self) -> None:
        self.post_message(self.ScopeFocused(f"add.{self._tc().active}"))

    def action_edit_item(self) -> None:
        self.post_message(self.ScopeFocused(f"edit.{self._tc().active}"))

    def action_delete_item(self) -> None:
        self.post_message(self.ScopeFocused(f"delete.{self._tc().active}"))

    def action_auto_discover(self) -> None:
        self.post_message(self.ScopeFocused("inventory.discover"))


# ── [4] Steps ─────────────────────────────────────────────────────────────────


class StepsPanel(Widget):
    BORDER_TITLE = "[4] Steps"

    BINDINGS = [
        Binding("/", "fuzzy_search", "Search", show=False),
    ]

    class StepSelected(Message):
        def __init__(self, protocol: Optional[dict], step: dict, step_idx: int) -> None:
            self.protocol = protocol
            self.step = step
            self.step_idx = step_idx
            super().__init__()

    class ScopeFocused(Message):
        def __init__(self, protocol: Optional[dict]) -> None:
            self.protocol = protocol
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._protocol: Optional[dict] = None
        self._steps: list[dict] = []
        self._protocol_name: str = ""
        self._current_step: int = -1

    def compose(self) -> ComposeResult:
        yield Static(
            "[dim]Select a protocol in [3] to view steps[/dim]",
            id="steps-header",
        )
        yield ListView(id="steps-list")

    def focus_default(self) -> None:
        list_view = self.query_one("#steps-list", ListView)
        _mark_list_selection(list_view)
        list_view.focus()
        idx = list_view.index
        if idx is not None and 0 <= idx < len(self._steps):
            self.post_message(self.StepSelected(self._protocol, self._steps[idx], idx))
        else:
            self.post_message(self.ScopeFocused(self._protocol))

    def load_protocol(
        self,
        protocol: dict,
        current_step: int = -1,
    ) -> None:
        self._protocol = protocol
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
        lv.index = None
        if not self._steps:
            lv.append(ListItem(Label("[dim]No steps defined[/dim]")))
            _mark_list_selection(lv)
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
        _mark_list_selection(lv)

    def on_list_view_highlighted(
        self, event: ListView.Highlighted
    ) -> None:
        _mark_list_selection(event.list_view)
        idx = self.query_one("#steps-list", ListView).index
        if idx is not None and 0 <= idx < len(self._steps):
            self.post_message(self.StepSelected(self._protocol, self._steps[idx], idx))

    def action_fuzzy_search(self) -> None:
        pass


# ── [5] Components ────────────────────────────────────────────────────────────


class ComponentsPanel(Widget):
    BORDER_TITLE = "[5] Components"

    class ComponentSelected(Message):
        def __init__(
            self,
            protocol: Optional[dict],
            step: Optional[dict],
            component: dict,
        ) -> None:
            self.protocol = protocol
            self.step = step
            self.component = component
            super().__init__()

    class ScopeFocused(Message):
        def __init__(self, protocol: Optional[dict], step: Optional[dict]) -> None:
            self.protocol = protocol
            self.step = step
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._protocol: Optional[dict] = None
        self._step: Optional[dict] = None
        self._step_idx: int = -1
        self._components: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Static(
            "[dim]Select a step in [4] to view components[/dim]",
            id="comp-header",
        )
        yield ListView(id="comp-list")

    def focus_default(self) -> None:
        list_view = self.query_one("#comp-list", ListView)
        _mark_list_selection(list_view)
        list_view.focus()
        idx = list_view.index
        if idx is not None and 0 <= idx < len(self._components):
            self.post_message(
                self.ComponentSelected(
                    self._protocol,
                    self._step,
                    self._components[idx],
                )
            )
        else:
            self.post_message(self.ScopeFocused(self._protocol, self._step))

    def load_protocol(self, protocol: dict) -> None:
        self._protocol = protocol
        self._step = None
        self._step_idx = -1
        self._components = []
        self.query_one("#comp-header", Static).update(
            "[dim]Select a step in [4][/dim]"
        )
        lv = self.query_one("#comp-list", ListView)
        lv.clear()
        lv.index = None
        _mark_list_selection(lv)

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
        lv.index = None
        components = (
            step.get("components", []) if isinstance(step, dict) else []
        )
        self._components = [c for c in components if isinstance(c, dict)]
        if not components:
            lv.append(
                ListItem(Label("[dim]No components defined for this step[/dim]"))
            )
            _mark_list_selection(lv)
            return
        for comp in components:
            name = comp.get("name", "?") if isinstance(comp, dict) else str(comp)
            comp_type = comp.get("type", "") if isinstance(comp, dict) else ""
            role = comp.get("io_role", "") if isinstance(comp, dict) else ""
            suffix = f"  [{role}]" if role else ""
            lv.append(ListItem(Label(f" · {name}  [{comp_type}]{suffix}")))
        _mark_list_selection(lv)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        _mark_list_selection(event.list_view)
        idx = event.list_view.index
        if idx is not None and 0 <= idx < len(self._components):
            self.post_message(
                self.ComponentSelected(
                    self._protocol,
                    self._step,
                    self._components[idx],
                )
            )


# ── [0] Main Display ──────────────────────────────────────────────────────────


class MainDisplay(Widget, can_focus=True):
    BORDER_TITLE = "[0] Context"

    _WELCOME = (
        "[bold]eVOLVER Control[/bold]\n\n"
        "Focus a numbered window to inspect its context.\n\n"
        "[dim]0[/dim] Context  "
        "[dim]1[/dim] Status  "
        "[dim]2[/dim] Live  "
        "[dim]3[/dim] Inventory  "
        "[dim]4[/dim] Steps  "
        "[dim]5[/dim] Components"
    )

    def compose(self) -> ComposeResult:
        yield Static(self._WELCOME, id="main-content")

    def focus_default(self) -> None:
        self.focus()

    def _update(self, lines: list[str]) -> None:
        self.query_one("#main-content", Static).update("\n".join(lines))

    def show_scope(self, scope: str) -> None:
        content = {
            "status": [
                "[bold][1] Status[/bold]",
                "",
                "System health and operator attention live here.",
                "Use this window to jump from a degraded condition to the relevant repair scope.",
            ],
            "live.experiments": [
                "[bold][2] Live / Experiments[/bold]",
                "",
                "Runtime experiment sessions appear here.",
                "No experiment is selected yet. Use up/down or click an experiment to inspect it.",
                "",
                "Suggested: a add experiment, / search, r run, p pause/resume, c cancel.",
            ],
            "live.evolvers": [
                "[bold][2] Live / Evolver Units[/bold]",
                "",
                "Connected or demo eVOLVER units appear here.",
                "Use this scope to inspect unit status, assignment, and available onboard devices.",
            ],
            "live.services": [
                "[bold][2] Live / Services[/bold]",
                "",
                "Supervisor-managed services appear here.",
                "Select a service to inspect lifecycle state and restart controls.",
            ],
            "inventory.protocols": [
                "[bold][3] Inventory / Protocols[/bold]",
                "",
                "Protocols define reusable experiment procedures for the current setup.",
                "Select a protocol to load its steps and component requirements.",
            ],
            "inventory.materials": [
                "[bold][3] Inventory / Materials[/bold]",
                "",
                "Materials describe organisms, media, reagents, samples, waste, and other lab inputs available to this eVOLVER setup.",
            ],
            "inventory.devices": [
                "[bold][3] Inventory / Devices[/bold]",
                "",
                "Devices describe pumps, sensors, vials, and I/O roles available to this eVOLVER setup.",
                "Use discover/import flows to populate hardware-backed entries.",
            ],
            "inventory.discover": [
                "[bold]Auto Discover[/bold]",
                "",
                "Future flow: scan attached eVOLVER hardware, choose detected units, import their config, or create demo units.",
            ],
        }
        if scope.startswith(("add.", "edit.", "delete.")):
            action, target = scope.split(".", 1)
            self._update([
                f"[bold]{action.title()} {target.title()}[/bold]",
                "",
                "This will open a form-driven popup in the next slice.",
                "Forms should preserve progress while moving through text fields, checkboxes, and multi-select choices.",
            ])
            return
        self._update(content.get(scope, ["[bold]Context[/bold]", "", scope]))

    def show_experiment(self, experiment: dict) -> None:
        name = _experiment_name(experiment)
        state = experiment.get("state", "?")
        exp_id = experiment.get("id", "?")
        created_at = experiment.get("created_at", "?")
        protocol = _experiment_protocol(experiment)
        runner = experiment.get("runner") or {}
        icon = _STATE_ICONS.get(state, "?")
        color = "yellow" if state == "running" else "green" if state == "created" else "red"
        lines = [
            f"[bold]Experiment: {name}[/bold]",
            "",
            f"  State:     {icon} [{color}]{state}[/{color}]",
            f"  ID:        [dim]{exp_id}[/dim]",
            f"  Protocol:  {protocol}",
            f"  Created:   {created_at}",
        ]
        if runner:
            lines.extend([
                "",
                "[bold]Runner[/bold]",
                f"  State: {runner.get('state', '-')}",
                f"  Dir:   {runner.get('experiment_dir', '-')}",
            ])
        self._update(lines)

    def show_evolver(self, evolver: dict) -> None:
        devices = evolver.get("devices", [])
        lines = [
            f"[bold]Evolver Unit: {evolver.get('name', evolver.get('id', '?'))}[/bold]",
            "",
            f"  ID:       [dim]{evolver.get('id', '?')}[/dim]",
            f"  State:    {evolver.get('state', 'unknown')}",
            f"  Role:     {evolver.get('role', '-')}",
            f"  Devices:  {len(devices)}",
        ]
        for device in devices[:6]:
            lines.append(
                f"    - {device.get('name', '?')} [{device.get('type', '?')}]"
            )
        self._update(lines)

    def show_service(self, service: dict) -> None:
        lines = [
            f"[bold]Service: {service.get('name', service.get('id', '?'))}[/bold]",
            "",
            f"  ID:        [dim]{service.get('id', '?')}[/dim]",
            f"  State:     {service.get('state', 'unknown')}",
            f"  Category:  {service.get('category', '-')}",
            f"  Restarts:  {service.get('restart_count', 0)}",
            f"  Last:      {service.get('last_action', '-')}",
        ]
        if service.get("description"):
            lines.extend(["", service["description"]])
        self._update(lines)

    def show_protocol(self, protocol: dict) -> None:
        name = protocol.get("name", "?")
        steps = protocol.get("steps", [])
        lines = [
            f"[bold]Protocol: {name}[/bold]",
            "",
            f"  ID:     [dim]{protocol.get('id', '-')}[/dim]",
            f"  Steps:  {len(steps)}",
        ]
        if protocol.get("description"):
            lines.extend(["", protocol["description"]])
        self._update(lines)

    def show_material(self, material: dict) -> None:
        self._update([
            f"[bold]Material: {material.get('name', '?')}[/bold]",
            "",
            f"  ID:    [dim]{material.get('id', '-')}[/dim]",
            f"  Type:  {material.get('type', '-')}",
            f"  Lot:   {material.get('lot', '-')}",
            "",
            material.get("description", "No description."),
        ])

    def show_device(self, device: dict) -> None:
        self._update([
            f"[bold]Device: {device.get('name', '?')}[/bold]",
            "",
            f"  ID:       [dim]{device.get('id', '-')}[/dim]",
            f"  Type:     {device.get('type', '-')}",
            f"  I/O role: {device.get('io_role', '-')}",
            f"  Unit:     {device.get('evolver_id', '-')}",
        ])

    def show_step(self, protocol: Optional[dict], step: dict, step_idx: int) -> None:
        lines: list[str] = []
        if protocol:
            lines.extend([
                f"[bold]Protocol: {protocol.get('name', '?')}[/bold]",
                f"  Steps: {len(protocol.get('steps', []))}",
                "",
            ])
        lines.extend([
            f"[bold]Step {step_idx + 1}: {step.get('name', '?')}[/bold]",
            "",
            step.get("description", "No step description."),
            "",
            f"Components: {len(step.get('components', []))}",
        ])
        self._update(lines)

    def show_component(self, protocol: Optional[dict], step: Optional[dict], component: dict) -> None:
        lines: list[str] = []
        if protocol:
            lines.extend([
                f"[bold]Protocol: {protocol.get('name', '?')}[/bold]",
                "",
            ])
        if step:
            lines.extend([
                f"[bold]Step: {step.get('name', '?')}[/bold]",
                "",
            ])
        lines.extend([
            f"[bold]Component: {component.get('name', '?')}[/bold]",
            "",
            f"  Type:     {component.get('type', '-')}",
            f"  I/O role: {component.get('io_role', '-')}",
            f"  Enabled:  {component.get('enabled', True)}",
        ])
        self._update(lines)

    def show_welcome(self) -> None:
        self._update([self._WELCOME])
