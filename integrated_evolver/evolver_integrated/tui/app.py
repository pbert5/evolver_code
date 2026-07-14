"""eVOLVER TUI – LazyGit-style terminal interface for the control plane."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, RichLog

from .client import APIError, ControlAPIClient
from .panels import (
    ComponentsPanel,
    InventoryPanel,
    LivePanel,
    MainDisplay,
    StepsPanel,
    StatusPanel,
)
from .screens import ConfirmScreen, FuzzySearchScreen, NewExperimentScreen


class EvolverTUI(App):
    TITLE = "eVOLVER Control"
    CSS_PATH = Path(__file__).parent / "evolver.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("1", "focus_status", "Status", show=False),
        Binding("2", "focus_live", "Live", show=False),
        Binding("3", "focus_inventory", "Inventory", show=False),
        Binding("4", "focus_steps", "Steps", show=False),
        Binding("5", "focus_components", "Components", show=False),
    ]

    def __init__(self, api_url: str = "http://127.0.0.1:8082") -> None:
        super().__init__()
        self._client = ControlAPIClient(api_url)
        self._experiments: list[dict] = []
        self._selected_experiment: Optional[dict] = None

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
        await self._client.start()
        self._log("TUI started — polling control plane")
        self.set_interval(2.0, self._poll)
        await self._poll()

    async def on_unmount(self) -> None:
        await self._client.stop()

    # ── polling ───────────────────────────────────────────────────────────────

    async def _poll(self) -> None:
        await self._refresh_status()
        await self._refresh_experiments()
        await self._refresh_jobs()

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
        self._experiments = exps
        self.query_one(LivePanel).update_experiments(exps)
        if self._selected_experiment is not None:
            sel_id = self._selected_experiment.get("id")
            for exp in exps:
                if exp.get("id") == sel_id:
                    self._selected_experiment = exp
                    self.query_one(MainDisplay).show_experiment(exp)
                    break

    async def _refresh_jobs(self) -> None:
        try:
            jobs = await self._client.list_jobs()
        except APIError:
            jobs = []
        self.query_one(LivePanel).update_jobs(jobs)

    # ── live panel message handlers ───────────────────────────────────────────

    def on_live_panel_experiment_selected(
        self, message: LivePanel.ExperimentSelected
    ) -> None:
        self._selected_experiment = message.experiment
        self.query_one(MainDisplay).show_experiment(message.experiment)

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
            pass  # TODO: select the matching item

        self.push_screen(
            FuzzySearchScreen(message.items, message.context), on_result
        )

    # ── inventory panel message handlers ──────────────────────────────────────

    def on_inventory_panel_protocol_selected(
        self, message: InventoryPanel.ProtocolSelected
    ) -> None:
        proto = message.protocol
        self.query_one(StepsPanel).load_protocol(proto)
        self.query_one(ComponentsPanel).load_protocol(proto)
        self.query_one(MainDisplay).show_protocol(proto)

    def on_inventory_panel_fuzzy_search_requested(
        self, message: InventoryPanel.FuzzySearchRequested
    ) -> None:
        def on_result(selected: str | None) -> None:
            pass  # TODO: select the matching item

        self.push_screen(
            FuzzySearchScreen(message.items, message.context), on_result
        )

    # ── steps panel message handlers ──────────────────────────────────────────

    def on_steps_panel_step_selected(
        self, message: StepsPanel.StepSelected
    ) -> None:
        self.query_one(ComponentsPanel).load_step(
            message.step, message.step_idx
        )

    # ── focus actions (number keys) ───────────────────────────────────────────

    def action_focus_status(self) -> None:
        self.query_one("#status-panel").focus()

    def action_focus_live(self) -> None:
        self.query_one("#live-panel").focus()

    def action_focus_inventory(self) -> None:
        self.query_one("#inv-panel").focus()

    def action_focus_steps(self) -> None:
        self.query_one("#steps-panel").focus()

    def action_focus_components(self) -> None:
        self.query_one("#comp-panel").focus()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.query_one("#cmd-log", RichLog).write(f"[dim]{ts}[/dim]  {msg}")


def main() -> None:
    parser = argparse.ArgumentParser(description="eVOLVER terminal UI")
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8082",
        help="Control plane API base URL",
    )
    args = parser.parse_args()
    EvolverTUI(api_url=args.api_url).run()


if __name__ == "__main__":
    main()
