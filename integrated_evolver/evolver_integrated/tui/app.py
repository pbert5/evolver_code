"""eVOLVER TUI – LazyGit-style terminal interface for the control plane."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.widgets import Footer, Header, RichLog

from .actions import key_help_lines
from .client import APIError, ControlAPIClient
from .data_paths import integrated_object_path, tui_data_path
from .demo_projection import project_integrated_system_for_tui
from .panels import (
    ComponentsPanel,
    InventoryPanel,
    LivePanel,
    MainDisplay,
    StepsPanel,
    StatusPanel,
)
from .screens import (
    ConfirmScreen,
    FuzzySearchScreen,
    NewExperimentScreen,
    TemplateFormScreen,
)


class EvolverTUI(App):
    TITLE = "eVOLVER Control"
    CSS_PATH = Path(__file__).parent / "evolver.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("?", "key_help", "Keys", priority=True),
        Binding("0", "focus_main", "Context", show=False, priority=True),
        Binding("1", "focus_status", "Status", show=False, priority=True),
        Binding("2", "focus_live", "Live", show=False, priority=True),
        Binding(
            "3",
            "focus_inventory",
            "Inventory",
            show=False,
            priority=True,
        ),
        Binding("4", "focus_steps", "Steps", show=False, priority=True),
        Binding(
            "5",
            "focus_components",
            "Components",
            show=False,
            priority=True,
        ),
        Binding("escape", "clear_focus", "Clear focus", show=False),
        Binding("d", "load_demo_data", "Demo", show=False),
    ]

    def __init__(
        self,
        api_url: str = "http://127.0.0.1:18082",
        demo: bool = False,
    ) -> None:
        super().__init__()
        self._client = ControlAPIClient(api_url)
        self._experiments: list[dict] = []
        self._selected_experiment: Optional[dict] = None
        self._demo_enabled = demo
        self._demo_data: dict = {}
        self._form_templates = self._load_form_templates()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-layout"):
            with Vertical(id="left-col"):
                yield StatusPanel(id="status-panel")
                yield LivePanel(id="live-panel")
                yield InventoryPanel(id="inv-panel")
                yield StepsPanel(id="steps-panel")
                yield ComponentsPanel(id="comp-panel")
            with Vertical(id="right-col"):
                yield MainDisplay(id="main-display")
                yield RichLog(id="cmd-log", highlight=True, markup=True)
        yield Footer()

    async def on_mount(self) -> None:
        if self._demo_enabled:
            self._load_demo_fixture()
        await self._client.start()
        self._log("TUI started — polling control plane")
        self.set_interval(2.0, self._poll)
        await self._poll()
        if self._demo_enabled:
            self._apply_demo_static_data()
        self.call_after_refresh(self._show_left_panel, "#live-panel")

    async def on_unmount(self) -> None:
        await self._client.stop()

    async def _poll(self) -> None:
        await self._refresh_status()
        await self._refresh_experiments()
        await self._refresh_services()

    async def _refresh_status(self) -> None:
        try:
            data = await self._client.health()
            status = data.get("status", "unknown")
        except APIError:
            status = "disconnected"
        self.query_one(StatusPanel).update_status(status)

    async def _refresh_experiments(self) -> None:
        try:
            exps = await self._client.list_experiments()
        except APIError:
            exps = []
        if self._demo_enabled and not exps:
            exps = list(self._demo_data.get("experiments", []))
        self._experiments = exps
        self.query_one(LivePanel).update_experiments(exps)
        if self._selected_experiment is not None:
            sel_id = self._selected_experiment.get("id")
            for exp in exps:
                if exp.get("id") == sel_id:
                    self._selected_experiment = exp
                    if self._live_experiments_has_focus():
                        main = self._main_display()
                        if main is not None:
                            main.show_experiment(exp)
                    break

    async def _refresh_services(self) -> None:
        try:
            services = await self._client.list_services()
        except APIError:
            services = []
        if self._demo_enabled and not services:
            services = list(self._demo_data.get("services", []))
        self.query_one(LivePanel).update_services(services)

    def on_live_panel_experiment_selected(
        self, message: LivePanel.ExperimentSelected
    ) -> None:
        self._selected_experiment = message.experiment
        main = self._main_display()
        if main is not None:
            main.show_experiment(message.experiment)

    def on_live_panel_evolver_selected(
        self, message: LivePanel.EvolverSelected
    ) -> None:
        main = self._main_display()
        if main is not None:
            main.show_evolver(message.evolver)

    def on_live_panel_service_selected(
        self, message: LivePanel.ServiceSelected
    ) -> None:
        main = self._main_display()
        if main is not None:
            main.show_service(message.service)

    def on_live_panel_scope_focused(
        self, message: LivePanel.ScopeFocused
    ) -> None:
        main = self._main_display()
        if main is not None:
            main.show_scope(message.scope)

    async def on_live_panel_pause_requested(
        self, message: LivePanel.PauseRequested
    ) -> None:
        try:
            await self._client.pause_experiment(message.experiment_id)
            self._log(f"PAUSE {message.experiment_id[:8]}")
        except APIError as exc:
            self._log(f"[red]ERROR pause: {exc}[/red]")
        await self._refresh_experiments()

    async def on_live_panel_resume_requested(
        self, message: LivePanel.ResumeRequested
    ) -> None:
        try:
            await self._client.resume_experiment(message.experiment_id)
            self._log(f"RESUME {message.experiment_id[:8]}")
        except APIError as exc:
            self._log(f"[red]ERROR resume: {exc}[/red]")
        await self._refresh_experiments()

    def on_live_panel_stop_requested(
        self, message: LivePanel.StopRequested
    ) -> None:
        exp_id = message.experiment_id
        exp_name = message.experiment_name

        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                self.run_worker(self._do_stop(exp_id), exclusive=True)

        self.push_screen(
            ConfirmScreen(f"Cancel experiment '{exp_name}'?"), on_confirm
        )

    async def _do_stop(self, exp_id: str) -> None:
        try:
            await self._client.stop_experiment(exp_id)
            self._log(f"STOP {exp_id[:8]}")
        except APIError as exc:
            self._log(f"[red]ERROR stop: {exc}[/red]")
        await self._refresh_experiments()

    def on_live_panel_run_requested(
        self, message: LivePanel.RunRequested
    ) -> None:
        exp_id = message.experiment_id
        running = [
            e for e in self._experiments if e.get("state") == "running"
        ]

        async def do_start() -> None:
            try:
                await self._client.start_experiment(exp_id)
                self._log(f"START {exp_id[:8]}")
            except APIError as exc:
                self._log(f"[red]ERROR start: {exc}[/red]")
            await self._refresh_experiments()

        if running:
            names = ", ".join(e.get("name", "?") for e in running)
            msg = f"'{names}' is running. Start another?"

            def on_confirm(confirmed: bool) -> None:
                if confirmed:
                    self.run_worker(do_start(), exclusive=True)

            self.push_screen(ConfirmScreen(msg), on_confirm)
        else:
            self.run_worker(do_start(), exclusive=True)

    async def on_live_panel_service_action_requested(
        self, message: LivePanel.ServiceActionRequested
    ) -> None:
        try:
            await self._client.service_action(
                message.service_id, message.action
            )
            self._log(
                f"{message.action.upper()} service {message.service_id}"
            )
        except APIError as exc:
            self._log(f"[red]ERROR service: {exc}[/red]")
        await self._refresh_services()

    def on_live_panel_service_config_requested(
        self, message: LivePanel.ServiceConfigRequested
    ) -> None:
        service = message.service
        items = self._service_config_items(service)
        if not items:
            self.query_one(MainDisplay).show_scope("service.no_config")
            return
        title = f"{service.get('name', service.get('id', '?'))} config"
        self.push_screen(FuzzySearchScreen(items, title))

    def _service_config_items(self, service: dict) -> list[str]:
        items: list[str] = []
        for key in (
            "id",
            "name",
            "state",
            "category",
            "description",
            "command",
            "supervisor_state",
            "restart_count",
            "last_action",
        ):
            value = service.get(key)
            if value not in (None, "", [], {}):
                items.append(f"{key}: {value}")

        for key in ("config", "environment", "ports", "volumes"):
            value = service.get(key)
            if isinstance(value, dict):
                items.extend(
                    f"{key}.{entry_key}: {entry_value}"
                    for entry_key, entry_value in sorted(value.items())
                )
            elif isinstance(value, list):
                items.extend(f"{key}: {entry}" for entry in value)
            elif value not in (None, ""):
                items.append(f"{key}: {value}")

        return items

    def on_live_panel_new_requested(
        self, _message: LivePanel.NewRequested
    ) -> None:
        async def on_result(name: str | None) -> None:
            if name:
                try:
                    await self._client.create_experiment(name)
                    self._log(f"CREATE {name}")
                except APIError as exc:
                    self._log(f"[red]ERROR create: {exc}[/red]")
                await self._refresh_experiments()

        self.push_screen(NewExperimentScreen(), on_result)

    def on_live_panel_fuzzy_search_requested(
        self, message: LivePanel.FuzzySearchRequested
    ) -> None:
        def on_result(selected: str | None) -> None:
            pass

        self.push_screen(
            FuzzySearchScreen(message.items, message.context), on_result
        )

    def on_inventory_panel_protocol_selected(
        self, message: InventoryPanel.ProtocolSelected
    ) -> None:
        proto = message.protocol
        self.query_one(StepsPanel).load_protocol(proto)
        self.query_one(ComponentsPanel).load_protocol(proto)
        self.query_one(MainDisplay).show_protocol(proto)

    def on_inventory_panel_material_selected(
        self, message: InventoryPanel.MaterialSelected
    ) -> None:
        self.query_one(MainDisplay).show_material(message.material)

    def on_inventory_panel_device_selected(
        self, message: InventoryPanel.DeviceSelected
    ) -> None:
        self.query_one(MainDisplay).show_device(message.device)

    def on_inventory_panel_scope_focused(
        self, message: InventoryPanel.ScopeFocused
    ) -> None:
        self.query_one(MainDisplay).show_scope(message.scope)

    def on_inventory_panel_create_requested(
        self, message: InventoryPanel.CreateRequested
    ) -> None:
        template_key = {
            "protocols": "protocol",
            "materials": "material",
        }.get(message.scope)
        if template_key is None:
            self.query_one(MainDisplay).show_scope(f"add.{message.scope}")
            return
        template = self._form_templates.get(template_key)
        if not template:
            self._log(f"[red]ERROR missing template: {template_key}[/red]")
            return

        def on_result(record: dict | None) -> None:
            if not record:
                return
            inventory = self.query_one(InventoryPanel)
            if template_key == "protocol":
                inventory.add_protocol(record)
                self.query_one(StepsPanel).load_protocol(record)
                self.query_one(ComponentsPanel).load_protocol(record)
                self.query_one(MainDisplay).show_protocol(record)
            elif template_key == "material":
                inventory.add_material(record)
                self.query_one(MainDisplay).show_material(record)
            self._log(f"CREATE {template_key} {record.get('id', '?')}")

        self.push_screen(TemplateFormScreen(template), on_result)

    def on_inventory_panel_edit_requested(
        self, message: InventoryPanel.EditRequested
    ) -> None:
        template_key = {
            "protocols": "protocol",
            "materials": "material",
        }.get(message.scope)
        if template_key is None:
            self.query_one(MainDisplay).show_scope(f"edit.{message.scope}")
            return
        template = self._form_template_for_edit(template_key)
        if not template:
            self._log(f"[red]ERROR missing template: {template_key}[/red]")
            return

        def on_result(record: dict | None) -> None:
            if not record:
                return
            inventory = self.query_one(InventoryPanel)
            if template_key == "protocol":
                inventory.replace_protocol(message.item_idx, record)
                self.query_one(StepsPanel).load_protocol(record)
                self.query_one(ComponentsPanel).load_protocol(record)
                self.query_one(MainDisplay).show_protocol(record)
            elif template_key == "material":
                inventory.replace_material(message.item_idx, record)
                self.query_one(MainDisplay).show_material(record)
            self._log(f"EDIT {template_key} {record.get('id', '?')}")

        self.push_screen(
            TemplateFormScreen(template, message.item), on_result
        )

    def on_inventory_panel_fuzzy_search_requested(
        self, message: InventoryPanel.FuzzySearchRequested
    ) -> None:
        def on_result(selected: str | None) -> None:
            pass

        self.push_screen(
            FuzzySearchScreen(message.items, message.context), on_result
        )

    def on_steps_panel_step_selected(
        self, message: StepsPanel.StepSelected
    ) -> None:
        self.query_one(ComponentsPanel).load_step(
            message.step, message.step_idx
        )
        self.query_one(MainDisplay).show_step(
            message.protocol,
            message.step,
            message.step_idx,
        )

    def on_steps_panel_scope_focused(
        self, message: StepsPanel.ScopeFocused
    ) -> None:
        if message.protocol:
            self.query_one(MainDisplay).show_protocol(message.protocol)
        else:
            self.query_one(MainDisplay).show_scope("steps")

    def on_steps_panel_create_requested(
        self, message: StepsPanel.CreateRequested
    ) -> None:
        if not message.protocol:
            self.query_one(MainDisplay).show_scope("add.steps")
            return
        template = self._form_templates.get("step")
        if not template:
            self._log("[red]ERROR missing template: step[/red]")
            return

        def on_result(record: dict | None) -> None:
            if not record:
                return
            steps = self.query_one(StepsPanel)
            steps.add_step(record)
            self.query_one(ComponentsPanel).load_step(
                record, len(message.protocol.get("steps", [])) - 1
            )
            self.query_one(MainDisplay).show_step(
                message.protocol,
                record,
                len(message.protocol.get("steps", [])) - 1,
            )
            self._log(f"CREATE step {record.get('name', '?')}")

        self.push_screen(TemplateFormScreen(template), on_result)

    def on_steps_panel_edit_requested(
        self, message: StepsPanel.EditRequested
    ) -> None:
        template = self._form_template_for_edit("step")
        if not template:
            self._log("[red]ERROR missing template: step[/red]")
            return

        def on_result(record: dict | None) -> None:
            if not record:
                return
            steps = self.query_one(StepsPanel)
            steps.replace_step(message.step_idx, record)
            self.query_one(ComponentsPanel).load_step(
                record, message.step_idx
            )
            self.query_one(MainDisplay).show_step(
                message.protocol,
                record,
                message.step_idx,
            )
            self._log(f"EDIT step {record.get('name', '?')}")

        self.push_screen(TemplateFormScreen(template, message.step), on_result)

    def on_components_panel_component_selected(
        self, message: ComponentsPanel.ComponentSelected
    ) -> None:
        self.query_one(MainDisplay).show_component(
            message.protocol,
            message.step,
            message.component,
        )

    def on_components_panel_scope_focused(
        self, message: ComponentsPanel.ScopeFocused
    ) -> None:
        if message.step:
            self.query_one(MainDisplay).show_step(
                message.protocol,
                message.step,
                0,
            )
        elif message.protocol:
            self.query_one(MainDisplay).show_protocol(message.protocol)
        else:
            self.query_one(MainDisplay).show_scope("components")

    def _live_experiments_has_focus(self) -> bool:
        if self.focused is None or self.focused.id != "exp-list":
            return False
        try:
            return self.query_one(LivePanel)._tc().active == "experiments"
        except Exception:
            return False

    def _main_display(self) -> Optional[MainDisplay]:
        try:
            return self.query_one(MainDisplay)
        except NoMatches:
            return None

    def action_focus_main(self) -> None:
        self.query_one(MainDisplay).focus_default()

    def action_focus_status(self) -> None:
        self.query_one(MainDisplay).show_scope("status")
        self._show_left_panel("#status-panel")

    def action_focus_live(self) -> None:
        self._show_left_panel("#live-panel")

    def action_focus_inventory(self) -> None:
        self._show_left_panel("#inv-panel")

    def action_focus_steps(self) -> None:
        self._show_left_panel("#steps-panel")

    def action_focus_components(self) -> None:
        self._show_left_panel("#comp-panel")

    def action_clear_focus(self) -> None:
        if self._focus_containing_window():
            return
        self.set_focus(None)

    def _focus_containing_window(self) -> bool:
        focused = self.focused
        if focused is None:
            return False
        window_ids = {
            "status-panel",
            "live-panel",
            "inv-panel",
            "steps-panel",
            "comp-panel",
            "main-display",
        }
        for ancestor in focused.ancestors:
            if ancestor.id in window_ids and getattr(
                ancestor, "can_focus", False
            ):
                self.set_focus(ancestor)
                return True
        return False

    def action_key_help(self) -> None:
        self.push_screen(
            FuzzySearchScreen(self._available_key_help(), "keybindings")
        )

    def action_load_demo_data(self) -> None:
        self._demo_enabled = True
        self._load_demo_fixture()
        self._apply_demo_static_data()
        self.query_one(LivePanel).update_experiments(
            list(self._demo_data.get("experiments", []))
        )
        self.query_one(LivePanel).update_services(
            list(self._demo_data.get("services", []))
        )
        self._log("Demo data loaded")

    def _load_demo_fixture(self) -> None:
        if self._demo_data:
            return
        path = integrated_object_path("demo_integrated_system.json")
        try:
            system = json.loads(path.read_text())
            self._demo_data = project_integrated_system_for_tui(system)
        except OSError as exc:
            self._demo_data = {}
            self._log(f"[red]ERROR demo data: {exc}[/red]")

    def _load_form_templates(self) -> dict:
        path = tui_data_path("form_templates.json")
        try:
            return json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return {}

    def _form_template_for_edit(self, template_key: str) -> dict:
        template = self._form_templates.get(template_key)
        if not template:
            return {}
        edit_template = deepcopy(template)
        edit_template["title"] = template.get("title", "Edit").replace(
            "New ", "Edit ", 1
        )
        submit = template.get("submit_label", "Save")
        edit_template["submit_label"] = (
            submit.replace("Create ", "Save ", 1)
            if submit.startswith("Create ")
            else "Save"
        )
        return edit_template

    def _apply_demo_static_data(self) -> None:
        if not self._demo_data:
            return
        live = self.query_one(LivePanel)
        inventory = self.query_one(InventoryPanel)
        live.update_devices(list(self._demo_data.get("evolver_units", [])))
        inventory.update_protocols(list(self._demo_data.get("protocols", [])))
        inventory.update_materials(list(self._demo_data.get("materials", [])))
        inventory.update_hw_devices(list(self._demo_data.get("devices", [])))

    def _available_key_help(self) -> list[str]:
        return key_help_lines()

    def _log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.query_one("#cmd-log", RichLog).write(f"[dim]{ts}[/dim]  {msg}")

    def _show_left_panel(self, selector: str) -> None:
        selectors = [
            "#status-panel",
            "#live-panel",
            "#inv-panel",
            "#steps-panel",
            "#comp-panel",
        ]
        for panel_selector in selectors:
            panel = self.query_one(panel_selector)
            panel.display = True
        panel = self.query_one(selector)
        focus_default = getattr(panel, "focus_default", None)
        if callable(focus_default):
            focus_default()
        elif getattr(panel, "can_focus", False):
            panel.focus()


def main() -> None:
    parser = argparse.ArgumentParser(description="eVOLVER terminal UI")
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:18082",
        help="Control plane API base URL",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Load demo experiments, evolvers, inventory, and services.",
    )
    args = parser.parse_args()
    EvolverTUI(api_url=args.api_url, demo=args.demo).run()


if __name__ == "__main__":
    main()
