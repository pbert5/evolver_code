"""eVOLVER TUI – LazyGit-style terminal interface for the control plane."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Log

from .client import APIError, ControlAPIClient
from .panels import (
    BioreactorsPanel,
    ExperimentsPanel,
    MainDisplay,
    ProcessesPanel,
    ProtocolsPanel,
    StatusPanel,
)
from .screens import ConfirmScreen, NewExperimentScreen


class EvolverTUI(App):
    TITLE = "eVOLVER Control"
    CSS_PATH = Path(__file__).parent / "evolver.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("1", "focus_status", "Status", show=False),
        Binding("2", "focus_experiments", "Experiments", show=False),
        Binding("3", "focus_protocols", "Protocols", show=False),
        Binding("4", "focus_bioreactors", "Bioreactors", show=False),
        Binding("5", "focus_processes", "Processes", show=False),
    ]

    def __init__(self, api_url: str = "http://localhost:8080") -> None:
        super().__init__()
        self._client = ControlAPIClient(api_url)
        self._experiments: list[dict] = []
        self._selected_experiment: Optional[dict] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-layout"):
            with Vertical(id="left-col"):
                yield StatusPanel(id="status-panel")
                yield ExperimentsPanel(id="experiments-panel")
                yield ProtocolsPanel(id="protocols-panel")
                yield BioreactorsPanel(id="bioreactors-panel")
                yield ProcessesPanel(id="processes-panel")
            with Vertical(id="right-col"):
                yield MainDisplay(id="main-display")
                yield Log(id="cmd-log", highlight=True, markup=True)
        yield Footer()

    async def on_mount(self) -> None:
        await self._client.start()
        self._log("TUI started — polling control plane")
        self.set_interval(2.0, self._poll)
        await self._poll()

    async def on_unmount(self) -> None:
        await self._client.stop()

    # --- Polling ---

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
        self.query_one(ExperimentsPanel).update_experiments(exps)
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
        self.query_one(ProcessesPanel).update_jobs(jobs)

    # --- Experiment panel message handlers ---

    def on_experiments_panel_experiment_selected(
        self, message: ExperimentsPanel.ExperimentSelected
    ) -> None:
        self._selected_experiment = message.experiment
        self.query_one(MainDisplay).show_experiment(message.experiment)
        protocol = message.experiment.get("protocol_steps", {})
        if isinstance(protocol, dict):
            self.query_one(ProtocolsPanel).update_protocol(protocol)

    async def on_experiments_panel_pause_requested(
        self, message: ExperimentsPanel.PauseRequested
    ) -> None:
        try:
            await self._client.pause_experiment(message.experiment_id)
            self._log(f"PAUSE {message.experiment_id[:8]}")
        except APIError as exc:
            self._log(f"[red]ERROR pause: {exc}[/red]")
        await self._refresh_experiments()

    async def on_experiments_panel_resume_requested(
        self, message: ExperimentsPanel.ResumeRequested
    ) -> None:
        try:
            await self._client.resume_experiment(message.experiment_id)
            self._log(f"RESUME {message.experiment_id[:8]}")
        except APIError as exc:
            self._log(f"[red]ERROR resume: {exc}[/red]")
        await self._refresh_experiments()

    def on_experiments_panel_stop_requested(
        self, message: ExperimentsPanel.StopRequested
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

    def on_experiments_panel_run_requested(
        self, message: ExperimentsPanel.RunRequested
    ) -> None:
        exp_id = message.experiment_id
        running = [e for e in self._experiments if e.get("state") == "running"]

        async def do_start() -> None:
            try:
                await self._client.start_experiment(exp_id)
                self._log(f"START {exp_id[:8]}")
            except APIError as exc:
                self._log(f"[red]ERROR start: {exc}[/red]")
            await self._refresh_experiments()

        if running:
            names = ", ".join(e.get("name", "?") for e in running)

            def on_confirm(confirmed: bool) -> None:
                if confirmed:
                    self.run_worker(do_start(), exclusive=True)

            msg = f"'{names}' is running. Start another?"
            self.push_screen(ConfirmScreen(msg), on_confirm)
        else:
            self.run_worker(do_start(), exclusive=True)

    def on_experiments_panel_new_requested(
        self, _message: ExperimentsPanel.NewRequested
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

    # --- Bioreactor panel message handlers ---

    def on_bioreactors_panel_bioreactor_selected(
        self, message: BioreactorsPanel.BioreactorSelected
    ) -> None:
        self.query_one(MainDisplay).show_device(message.device)

    # --- Focus actions (number keys) ---

    def action_focus_status(self) -> None:
        self.query_one("#status-panel").focus()

    def action_focus_experiments(self) -> None:
        self.query_one("#experiments-panel").focus()

    def action_focus_protocols(self) -> None:
        self.query_one("#protocols-panel").focus()

    def action_focus_bioreactors(self) -> None:
        self.query_one("#bioreactors-panel").focus()

    def action_focus_processes(self) -> None:
        self.query_one("#processes-panel").focus()

    # --- Helpers ---

    def _log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.query_one("#cmd-log", Log).write_line(f"[dim]{ts}[/dim]  {msg}")


def main() -> None:
    parser = argparse.ArgumentParser(description="eVOLVER terminal UI")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8080",
        help="Control plane API base URL (default: http://localhost:8080)",
    )
    args = parser.parse_args()
    EvolverTUI(api_url=args.api_url).run()


if __name__ == "__main__":
    main()
