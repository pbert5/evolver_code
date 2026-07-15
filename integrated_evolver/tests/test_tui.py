"""Tests for the eVOLVER TUI package."""
import asyncio
import json
from pathlib import Path

import pytest

textual = pytest.importorskip(
    "textual", reason="textual not installed"
)


# ── import smoke tests ────────────────────────────────────────────────────────


def test_client_module_imports():
    from evolver_integrated.tui.client import APIError, ControlAPIClient
    assert issubclass(APIError, Exception)
    assert callable(ControlAPIClient)


def test_panels_module_imports():
    from evolver_integrated.tui.panels import (
        ComponentsPanel,
        InventoryPanel,
        LivePanel,
        MainDisplay,
        StepsPanel,
        StatusPanel,
        _SERVICE_STATE_DISPLAY,
        _STATE_ICONS,
        _STATUS_DISPLAY,
    )
    assert StatusPanel is not None
    assert LivePanel is not None
    assert InventoryPanel is not None
    assert StepsPanel is not None
    assert ComponentsPanel is not None
    assert MainDisplay is not None
    assert isinstance(_STATE_ICONS, dict)
    assert isinstance(_SERVICE_STATE_DISPLAY, dict)
    assert isinstance(_STATUS_DISPLAY, dict)


def test_screens_module_imports():
    from evolver_integrated.tui.screens import (
        ConfirmScreen,
        FuzzySearchScreen,
        NewExperimentScreen,
    )
    assert ConfirmScreen is not None
    assert NewExperimentScreen is not None
    assert FuzzySearchScreen is not None


def test_app_module_imports():
    from evolver_integrated.tui.app import EvolverTUI, main
    assert callable(main)
    assert EvolverTUI is not None


# ── state icon mapping ────────────────────────────────────────────────────────


def test_state_icons_cover_control_plane_states():
    from evolver_integrated.tui.panels import _STATE_ICONS
    from evolver_integrated.control_plane import (
        STATE_CREATED,
        STATE_FAILED,
        STATE_PAUSED,
        STATE_RUNNING,
        STATE_STOPPED,
    )
    for state in (
        STATE_CREATED,
        STATE_RUNNING,
        STATE_PAUSED,
        STATE_STOPPED,
        STATE_FAILED,
    ):
        assert state in _STATE_ICONS, f"Missing icon for state '{state}'"


def test_status_display_has_disconnected():
    from evolver_integrated.tui.panels import _STATUS_DISPLAY
    assert "disconnected" in _STATUS_DISPLAY
    color, label = _STATUS_DISPLAY["disconnected"]
    assert color and label


# ── APIError ──────────────────────────────────────────────────────────────────


def test_api_error_is_exception():
    from evolver_integrated.tui.client import APIError
    err = APIError("connection refused")
    assert str(err) == "connection refused"
    assert isinstance(err, Exception)


def test_api_error_wraps_cause():
    from evolver_integrated.tui.client import APIError
    cause = RuntimeError("original")
    err = APIError("wrapped")
    err.__cause__ = cause
    assert err.__cause__ is cause


# ── ControlAPIClient construction ─────────────────────────────────────────────


def test_client_default_url():
    from evolver_integrated.tui.client import ControlAPIClient
    c = ControlAPIClient()
    assert c.base_url == "http://127.0.0.1:18082"


def test_client_custom_url_strips_trailing_slash():
    from evolver_integrated.tui.client import ControlAPIClient
    c = ControlAPIClient("http://localhost:9999/")
    assert c.base_url == "http://localhost:9999"


def test_client_not_started_has_no_session():
    from evolver_integrated.tui.client import ControlAPIClient
    c = ControlAPIClient()
    assert c._session is None


def test_client_create_experiment_sends_valid_minimal_request(monkeypatch):
    from evolver_integrated.tui.client import ControlAPIClient

    calls = []

    async def fake_post(self, path, payload):
        calls.append((path, payload))
        return {"experiment": {"id": "exp-1"}}

    monkeypatch.setattr(ControlAPIClient, "_post", fake_post)

    result = asyncio.run(ControlAPIClient().create_experiment("trial"))

    assert result == {"experiment": {"id": "exp-1"}}
    assert calls == [
        (
            "/experiments",
            {
                "name": "trial",
                "machine_id": "machine-1",
                "vials": [0],
                "metadata": {"protocol": "default"},
            },
        )
    ]


def test_client_service_action_posts_to_service_route(monkeypatch):
    from evolver_integrated.tui.client import ControlAPIClient

    calls = []

    async def fake_post(self, path, payload):
        calls.append((path, payload))
        return {"service": {"id": "control-plane"}}

    monkeypatch.setattr(ControlAPIClient, "_post", fake_post)

    result = asyncio.run(
        ControlAPIClient().service_action("control-plane", "restart")
    )

    assert result == {"service": {"id": "control-plane"}}
    assert calls == [("/services/control-plane/restart", {})]


# ── EvolverTUI construction ───────────────────────────────────────────────────


def test_evolver_tui_default_url():
    from evolver_integrated.tui.app import EvolverTUI
    app = EvolverTUI()
    assert app._client.base_url == "http://127.0.0.1:18082"


def test_evolver_tui_custom_url():
    from evolver_integrated.tui.app import EvolverTUI
    app = EvolverTUI(api_url="http://192.168.1.10:8080")
    assert "192.168.1.10" in app._client.base_url


def test_evolver_tui_mounts_without_control_plane(monkeypatch):
    from evolver_integrated.tui.app import EvolverTUI

    async def noop_start(self):
        return None

    async def noop_stop(self):
        return None

    async def disconnected(self):
        from evolver_integrated.tui.client import APIError
        raise APIError("offline")

    async def empty_list(self):
        return []

    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.start",
        noop_start,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.stop",
        noop_stop,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.health",
        disconnected,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.list_experiments",
        empty_list,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.list_services",
        empty_list,
    )

    app = EvolverTUI()

    async def run_app():
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.query_one("#cmd-log") is not None

    asyncio.run(run_app())


def test_tui_architecture_uses_pages_before_windows():
    path = (
        Path(__file__).parents[1]
        / "evolver_integrated"
        / "tui"
        / "tui_architecture.json"
    )
    architecture = json.loads(path.read_text())

    assert architecture["version"] == 2
    assert isinstance(architecture["pages"], list)
    assert "windows" not in architecture

    page = architecture["pages"][0]
    assert page["id"] == "operational"
    window_ids = [window["id"] for window in page["windows"]]
    assert window_ids == [
        "context",
        "status",
        "live",
        "inventory",
        "steps",
        "components",
    ]


def test_tui_architecture_uses_focus_context_inheritance():
    path = (
        Path(__file__).parents[1]
        / "evolver_integrated"
        / "tui"
        / "tui_architecture.json"
    )
    architecture = json.loads(path.read_text())

    page = architecture["pages"][0]
    inventory = next(
        window for window in page["windows"] if window["id"] == "inventory"
    )
    steps = next(
        window for window in page["windows"] if window["id"] == "steps"
    )
    components = next(
        window for window in page["windows"] if window["id"] == "components"
    )
    protocols = next(
        tab for tab in inventory["tabs"] if tab["id"] == "protocols"
    )
    materials = next(
        tab for tab in inventory["tabs"] if tab["id"] == "materials"
    )
    steps_tab = steps["tabs"][0]
    components_tab = components["tabs"][0]
    live = next(
        window for window in page["windows"] if window["id"] == "live"
    )
    experiments = next(
        tab for tab in live["tabs"] if tab["id"] == "experiments"
    )
    evolver_units = next(
        tab for tab in live["tabs"] if tab["id"] == "evolver_units"
    )
    devices = next(
        tab for tab in inventory["tabs"] if tab["id"] == "devices"
    )

    assert protocols["context"]["focused_context"] == (
        "inventory.protocols.focused"
    )
    assert experiments["data"]["source"] == "json_store.experiments"
    assert evolver_units["data"]["source"] == "json_store.evolver_units"
    assert protocols["data"]["source"] == "json_store.protocols"
    assert materials["data"]["source"] == "json_store.materials"
    assert devices["data"]["source"] == "json_store.devices"
    assert steps["context"]["inherits_focus_from"] == (
        "inventory.protocols.focused"
    )
    assert steps["context"]["focused_context"] == "steps.focused"
    assert steps_tab["data"]["source"] == (
        "json_store.protocols.focused.steps"
    )
    assert components["context"]["inherits_focus_from"] == "steps.focused"
    assert components_tab["data"]["source"] == (
        "json_store.protocols.focused.steps.focused.components"
    )
    assert components_tab["data"]["references"] == [
        "json_store.materials",
        "json_store.devices",
    ]

    protocol_actions = [
        action["action"]
        for action in protocols["keybinds"]["available"]
    ]
    assert "activate" not in protocol_actions
    assert "can_activate_context" not in protocols.get("options", {})
    assert "can_activate_context" not in materials.get("options", {})

    assert "activation_model" not in architecture
    assert architecture["focus_model"]["ui_only"] is True


def test_tui_architecture_spells_out_tab_data_rows():
    path = (
        Path(__file__).parents[1]
        / "evolver_integrated"
        / "tui"
        / "tui_architecture.json"
    )
    architecture = json.loads(path.read_text())

    tabs = []
    for page in architecture["pages"]:
        for window in page["windows"]:
            tabs.extend(window.get("tabs", []))

    assert tabs
    for tab in tabs:
        assert tab["data"]["source"]
        assert tab["data"]["empty_state"]
        assert tab["data"]["rows"]
        for row in tab["data"]["rows"]:
            assert row["field"]
            assert row["display"]


def test_only_emphasized_rows_are_underlined():
    from evolver_integrated.tui.panels import _list_item

    item = _list_item("emphasized", emphasized=True)
    inactive = _list_item("inactive")
    css = (
        Path(__file__).parents[1]
        / "evolver_integrated"
        / "tui"
        / "evolver.tcss"
    ).read_text()

    assert item.has_class("state-emphasis-row")
    assert not inactive.has_class("state-emphasis-row")
    assert "ListView > ListItem.state-emphasis-row" in css
    assert "ListView > ListItem.persistent-highlight" in css
    assert (
        css.index("ListView > ListItem.state-emphasis-row")
        < css.index("text-style: underline;")
    )


def test_evolver_tui_number_keys_focus_left_panels_without_hiding(monkeypatch):
    from evolver_integrated.tui.app import EvolverTUI

    async def noop_start(self):
        return None

    async def noop_stop(self):
        return None

    async def empty_dict(self):
        return {"status": "ok"}

    async def empty_list(self):
        return []

    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.start",
        noop_start,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.stop",
        noop_stop,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.health",
        empty_dict,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.list_experiments",
        empty_list,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.list_services",
        empty_list,
    )

    app = EvolverTUI()

    async def run_app():
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.focused is not None
            assert app.focused.id == "exp-list"

            await pilot.press("3")
            assert app.query_one("#inv-panel").display is True
            assert app.query_one("#live-panel").display is True
            assert app.focused is not None
            assert app.focused.id == "proto-list"

            await pilot.press("]")
            assert app.focused is not None
            assert app.focused.id == "mat-list"
            await pilot.press("[")
            assert app.focused is not None
            assert app.focused.id == "proto-list"

            await pilot.press("2")
            assert app.focused is not None
            assert app.focused.id == "exp-list"
            await pilot.press("]")
            assert app.focused is not None
            assert app.focused.id == "evolver-list"
            await pilot.press("]")
            assert app.focused is not None
            assert app.focused.id == "service-list"

            await pilot.press("5")
            assert app.query_one("#comp-panel").display is True
            assert app.query_one("#inv-panel").display is True
            assert app.focused is not None
            assert app.focused.id == "comp-list"

            await pilot.press("1")
            assert app.focused is not None
            assert app.focused.id == "status-panel"

    asyncio.run(run_app())


def test_live_panel_keybindings_follow_active_tab(monkeypatch):
    from evolver_integrated.tui.app import EvolverTUI
    from evolver_integrated.tui.panels import LivePanel

    async def noop_start(self):
        return None

    async def noop_stop(self):
        return None

    async def empty_dict(self):
        return {"status": "ok"}

    async def empty_list(self):
        return []

    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.start",
        noop_start,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.stop",
        noop_stop,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.health",
        empty_dict,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.list_experiments",
        empty_list,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.list_services",
        empty_list,
    )

    app = EvolverTUI()

    async def run_app():
        async with app.run_test() as pilot:
            await pilot.pause()
            live = app.query_one(LivePanel)

            assert live.check_action("new_exp", ()) is True
            assert live.check_action("cancel_exp", ()) is True
            assert live.check_action("config_item", ()) is False

            await pilot.press("]")
            assert live.check_action("new_exp", ()) is False
            assert live.check_action("cancel_exp", ()) is False
            assert live.check_action("config_item", ()) is True
            assert live.check_action("run_or_restart", ()) is False

            await pilot.press("]")
            live.update_services([
                {
                    "id": "control-plane",
                    "name": "Control Plane",
                    "state": "running",
                    "category": "core",
                }
            ])
            await pilot.press("down")
            assert live.check_action("new_exp", ()) is False
            assert live.check_action("delete_item", ()) is False
            assert live.check_action("config_item", ()) is True
            assert live.check_action("run_or_restart", ()) is True
            assert live.check_action("pause_or_resume", ()) is True

    asyncio.run(run_app())


def test_live_panel_hides_restart_pause_for_unmanaged_service(monkeypatch):
    from evolver_integrated.tui.app import EvolverTUI
    from evolver_integrated.tui.panels import LivePanel

    async def noop_start(self):
        return None

    async def noop_stop(self):
        return None

    async def empty_dict(self):
        return {"status": "ok"}

    async def empty_list(self):
        return []

    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.start",
        noop_start,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.stop",
        noop_stop,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.health",
        empty_dict,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.list_experiments",
        empty_list,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.list_services",
        empty_list,
    )

    app = EvolverTUI()
    service_actions = []

    async def run_app():
        async with app.run_test() as pilot:
            await pilot.pause()
            live = app.query_one(LivePanel)
            live.update_services([
                {
                    "id": "tui",
                    "name": "TUI",
                    "state": "running",
                    "category": "unmanaged",
                }
            ])

            await pilot.press("]")
            await pilot.press("]")
            await pilot.press("down")
            assert live.check_action("run_or_restart", ()) is False
            assert live.check_action("pause_or_resume", ()) is False
            assert live.check_action("config_item", ()) is True

            def record_action(message):
                service_actions.append((message.service_id, message.action))

            monkeypatch.setattr(
                app,
                "on_live_panel_service_action_requested",
                record_action,
            )
            live.action_run_or_restart()
            live.action_pause_or_resume()
            assert service_actions == []

    asyncio.run(run_app())


def test_experiment_refresh_only_updates_live_experiments_context(monkeypatch):
    from evolver_integrated.tui.app import EvolverTUI
    from evolver_integrated.tui.panels import LivePanel, MainDisplay

    async def noop_start(self):
        return None

    async def noop_stop(self):
        return None

    async def empty_dict(self):
        return {"status": "ok"}

    async def empty_list(self):
        return []

    selected = {"id": "exp-1", "state": "running"}

    async def experiments(self):
        return [selected]

    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.start",
        noop_start,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.stop",
        noop_stop,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.health",
        empty_dict,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.list_services",
        empty_list,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.list_experiments",
        experiments,
    )

    rendered = []
    original_show_experiment = MainDisplay.show_experiment

    def record_show_experiment(self, experiment):
        rendered.append(experiment["id"])
        original_show_experiment(self, experiment)

    monkeypatch.setattr(MainDisplay, "show_experiment", record_show_experiment)

    app = EvolverTUI()

    async def run_app():
        async with app.run_test() as pilot:
            await pilot.pause()
            app._selected_experiment = dict(selected)
            live = app.query_one(LivePanel)

            await pilot.press("]")
            assert app.focused is not None
            assert app.focused.id == "evolver-list"
            await app._refresh_experiments()
            assert rendered == []

            await pilot.press("]")
            assert app.focused is not None
            assert app.focused.id == "service-list"
            await app._refresh_experiments()
            assert rendered == []

            await pilot.press("4")
            assert app.focused is not None
            assert app.focused.id == "steps-list"
            await app._refresh_experiments()
            assert rendered == []

            await pilot.press("5")
            assert app.focused is not None
            assert app.focused.id == "comp-list"
            await app._refresh_experiments()
            assert rendered == []

            await pilot.press("3")
            assert app.focused is not None
            assert app.focused.id == "proto-list"
            await app._refresh_experiments()
            assert rendered == []

            await pilot.press("escape")
            assert app.focused is not None
            assert app.focused.id == "inv-panel"
            await pilot.press("escape")
            assert app.focused is None
            await app._refresh_experiments()
            assert rendered == []

            app.set_focus(app.query_one("#exp-list"))
            live._tc().active = "services"
            assert app.focused is not None
            assert app.focused.id == "exp-list"
            await app._refresh_experiments()
            assert rendered == []

            live._tc().active = "experiments"
            live.focus_default()
            assert app.focused is not None
            assert app.focused.id == "exp-list"
            await app._refresh_experiments()
            assert rendered == ["exp-1"]

    asyncio.run(run_app())


def test_escape_clears_focus_without_clearing_highlight(monkeypatch):
    from evolver_integrated.tui.app import EvolverTUI

    async def noop_start(self):
        return None

    async def noop_stop(self):
        return None

    async def empty_dict(self):
        return {"status": "ok"}

    async def empty_list(self):
        return []

    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.start",
        noop_start,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.stop",
        noop_stop,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.health",
        empty_dict,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.list_experiments",
        empty_list,
    )
    monkeypatch.setattr(
        "evolver_integrated.tui.client.ControlAPIClient.list_services",
        empty_list,
    )

    app = EvolverTUI()

    async def run_app():
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("3")
            assert app.focused is not None
            assert app.focused.id == "proto-list"
            await pilot.press("down")

            list_view = app.query_one("#proto-list")
            selected = list_view.highlighted_child
            assert selected is not None
            assert selected.has_class("persistent-highlight")

            await pilot.press("escape")
            assert app.focused is not None
            assert app.focused.id == "inv-panel"
            assert selected.has_class("persistent-highlight")

            await pilot.press("escape")
            assert app.focused is None
            assert selected.has_class("persistent-highlight")

    asyncio.run(run_app())


def test_service_context_includes_keybind_hints(monkeypatch):
    from evolver_integrated.tui.panels import MainDisplay

    rendered = []

    def record_update(self, lines):
        rendered.extend(lines)

    monkeypatch.setattr(MainDisplay, "_update", record_update)

    display = MainDisplay()
    display.show_service({
        "id": "control-plane",
        "name": "Control Plane",
        "state": "running",
        "category": "core",
    })

    assert any(line.startswith("Suggested:") for line in rendered)
    assert any(line.startswith("Keybind hints:") for line in rendered)
    assert any("space config" in line for line in rendered)
    assert any("r restart" in line for line in rendered)


def test_unmanaged_service_context_omits_restart_pause(monkeypatch):
    from evolver_integrated.tui.panels import MainDisplay

    rendered = []

    def record_update(self, lines):
        rendered.extend(lines)

    monkeypatch.setattr(MainDisplay, "_update", record_update)

    display = MainDisplay()
    display.show_service({
        "id": "tui",
        "name": "TUI",
        "state": "running",
        "category": "unmanaged",
    })

    joined = "\n".join(rendered)
    assert "Keybind hints:" in joined
    assert "space config" in joined
    assert "r restart" not in joined
    assert "p pause/resume" not in joined


def test_live_panel_services_use_requested_status_symbols():
    from evolver_integrated.tui.panels import _SERVICE_STATE_DISPLAY

    assert _SERVICE_STATE_DISPLAY["running"] == ("green", "○")
    assert _SERVICE_STATE_DISPLAY["paused"] == ("yellow", "⏸")
    assert _SERVICE_STATE_DISPLAY["stopped"] == ("dim", "□")
    assert _SERVICE_STATE_DISPLAY["failed"] == ("red", "✗")


# ── FuzzySearchScreen filtering ───────────────────────────────────────────────


def test_fuzzy_search_screen_stores_items():
    from evolver_integrated.tui.screens import FuzzySearchScreen
    items = ["alpha", "beta", "gamma"]
    screen = FuzzySearchScreen(items, context="test")
    assert screen._all_items == items
    assert screen._context == "test"


def test_fuzzy_search_converts_items_to_str():
    from evolver_integrated.tui.screens import FuzzySearchScreen
    screen = FuzzySearchScreen([1, 2, 3])
    assert screen._all_items == ["1", "2", "3"]


def test_experiment_display_reads_control_plane_record_shape():
    from evolver_integrated.tui.panels import _experiment_name
    from evolver_integrated.tui.panels import _experiment_protocol

    experiment = {
        "id": "exp-1",
        "state": "created",
        "request": {
            "name": "trial",
            "metadata": {"protocol": "batch-growth"},
        },
    }

    assert _experiment_name(experiment) == "trial"
    assert _experiment_protocol(experiment) == "batch-growth"
