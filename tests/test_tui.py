"""Tests for the eVOLVER TUI package."""
import asyncio
import json
from pathlib import Path

import pytest
import yaml

textual = pytest.importorskip(
    "textual", reason="textual not installed"
)


def _tui_data_path(filename):
    from evolver_integrated.tui.data_paths import tui_data_path

    return tui_data_path(filename)


def _integrated_object_path(filename):
    from evolver_integrated.tui.data_paths import integrated_object_path

    return integrated_object_path(filename)


def _demo_system():
    return json.loads(
        _integrated_object_path("demo_integrated_system.json").read_text()
    )


def _projected_demo_data():
    from evolver_integrated.tui.demo_projection import (
        project_integrated_system_for_tui,
    )

    return project_integrated_system_for_tui(_demo_system())


def _schema_bundle():
    schema_root = Path(__file__).parents[1] / "data" / "integrated system"
    paths = [
        schema_root / "integrated_evolver_schema.linkml.yml",
        *sorted((schema_root / "schemas").glob("*.yaml")),
    ]
    bundle = {"classes": {}, "enums": {}}
    for path in paths:
        schema = yaml.safe_load(path.read_text())
        bundle["classes"].update(schema.get("classes", {}))
        bundle["enums"].update(schema.get("enums", {}))
    return bundle


def _class_attributes(bundle, class_name):
    cls = bundle["classes"][class_name]
    attrs = {}
    parent = cls.get("is_a")
    if parent:
        attrs.update(_class_attributes(bundle, parent))
    attrs.update(cls.get("attributes", {}))
    return attrs


def _validate_schema_object(bundle, class_name, record, path):
    attrs = _class_attributes(bundle, class_name)
    unknown = sorted(set(record) - set(attrs))
    assert not unknown, f"{path} has unknown schema fields: {unknown}"

    for attr_name, attr_schema in attrs.items():
        attr_schema = attr_schema or {}
        attr_path = f"{path}.{attr_name}"
        if attr_schema.get("required"):
            assert attr_name in record, f"{attr_path} is required"
        if attr_name not in record:
            continue
        value = record[attr_name]
        range_name = attr_schema.get("range")
        if range_name in bundle["enums"]:
            allowed = set(
                bundle["enums"][range_name]["permissible_values"]
            )
            values = value if attr_schema.get("multivalued") else [value]
            for candidate in values:
                assert candidate in allowed, (
                    f"{attr_path}={candidate!r} is not in {range_name}"
                )
        elif (
            range_name in bundle["classes"]
            and attr_schema.get("inlined_as_list")
        ):
            for idx, item in enumerate(value):
                _validate_schema_object(
                    bundle, range_name, item, f"{attr_path}[{idx}]"
                )
        elif range_name in bundle["classes"] and attr_schema.get("inlined"):
            _validate_schema_object(bundle, range_name, value, attr_path)


def _stub_tui_client(monkeypatch):
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
        TemplateFormScreen,
        record_from_template,
    )
    assert ConfirmScreen is not None
    assert NewExperimentScreen is not None
    assert FuzzySearchScreen is not None
    assert TemplateFormScreen is not None
    assert callable(record_from_template)


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
    path = _tui_data_path("tui_architecture.json")
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
    path = _tui_data_path("tui_architecture.json")
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
    path = _tui_data_path("tui_architecture.json")
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


def test_tui_actions_json_drives_live_action_catalog():
    from evolver_integrated.tui.actions import (
        actions_for_panel_tab,
        key_help_lines,
        service_command,
        service_managed_restricted_actions,
    )
    from evolver_integrated.tui.panels import LivePanel

    path = _tui_data_path("actions.json")
    actions = json.loads(path.read_text())

    assert actions["version"] == 1
    assert "run_or_restart" in actions_for_panel_tab("live", "services")
    assert "config_item" not in actions_for_panel_tab(
        "live", "experiments"
    )
    assert service_command("restart", "fallback") == "restart"
    assert service_managed_restricted_actions() == {
        "pause_or_resume",
        "run_or_restart",
    }
    assert any(line.startswith("enter ") for line in key_help_lines())
    assert LivePanel._TAB_ACTIONS["services"] == actions_for_panel_tab(
        "live", "services"
    )


def test_form_templates_create_material_and_protocol_records():
    from evolver_integrated.tui.screens import record_from_template

    path = _tui_data_path("form_templates.json")
    templates = json.loads(path.read_text())

    material = record_from_template(
        templates["material"],
        {
            "name": "LB medium",
            "type": "growth_medium",
            "lot": "demo",
            "description": "Broth",
        },
    )
    assert material == {
        "id": "lb-medium",
        "name": "LB medium",
        "type": "growth_medium",
        "lot": "demo",
        "description": "Broth",
    }

    protocol = record_from_template(
        templates["protocol"],
        {
            "name": "Batch Growth",
            "description": "Simple growth run",
            "steps": json.dumps([
                {
                    "name": "grow",
                    "components": [
                        {
                            "name": "media pump",
                            "type": "pump",
                            "enabled": True,
                        }
                    ],
                }
            ]),
        },
    )
    assert protocol["id"] == "batch-growth"
    assert protocol["steps"][0]["name"] == "grow"
    assert protocol["steps"][0]["components"][0]["enabled"] is True

    step = record_from_template(
        templates["step"],
        {
            "name": "sample",
            "description": "Collect sample",
            "components": json.dumps([]),
        },
    )
    assert step == {
        "name": "sample",
        "description": "Collect sample",
        "components": [],
    }


def test_demo_integrated_system_matches_owned_schema():
    system = _demo_system()
    bundle = _schema_bundle()

    _validate_schema_object(
        bundle,
        "IntegratedEvolverSystem",
        system,
        "demo_integrated_system",
    )


def test_demo_data_contains_core_experiment_protocol_objects():
    demo_data = _projected_demo_data()

    protocols = {
        protocol["protocol_type"]: protocol
        for protocol in demo_data["protocols"]
    }

    assert set(protocols) == {
        "growth_curve",
        "chemostat",
        "turbidostat",
    }
    assert protocols["growth_curve"]["algorithm"]["input_parameters"] == [
        "optical_density",
        "temperature",
        "stir_rate",
    ]
    assert "dilution_rate" in protocols["chemostat"]["algorithm"][
        "input_parameters"
    ]
    assert any(
        equation["name"] == "pump_period_seconds"
        for equation in protocols["chemostat"]["algorithm"]["equations"]
    )
    assert any(
        equation["name"] == "dilution_time_seconds"
        for equation in protocols["turbidostat"]["algorithm"]["equations"]
    )

    for protocol in protocols.values():
        assert protocol["steps"]
        assert "algorithm_type" in protocol["algorithm"]
        for step in protocol["steps"]:
            assert step["components"]


def test_demo_data_marks_material_placeholders_as_run_blocking():
    demo_data = _projected_demo_data()

    materials = {material["id"]: material for material in demo_data["materials"]}
    placeholder_ids = {
        material_id
        for material_id, material in materials.items()
        if material.get("placeholder")
    }

    assert placeholder_ids == {
        "mat-placeholder-growth-media",
        "mat-placeholder-limiting-media",
        "mat-placeholder-starting-culture",
        "sample-placeholder-starting-culture",
    }
    for material_id in placeholder_ids:
        material = materials[material_id]
        assert material["run_blocking"] is True
        assert material["required_fields"]

    growth_curve = next(
        protocol
        for protocol in demo_data["protocols"]
        if protocol["protocol_type"] == "growth_curve"
    )
    assert set(growth_curve["run_blocking_placeholders"]) == {
        "mat-placeholder-growth-media",
        "mat-placeholder-starting-culture",
    }
    assert demo_data["experiments"][0]["run_readiness"] == {
        "can_run": False,
        "blocking_placeholder_ids": [
            "mat-placeholder-growth-media",
            "mat-placeholder-starting-culture",
            "sample-placeholder-starting-culture",
        ],
        "unresolved_required_fields": [
            "growth_medium",
            "supply_volume",
            "organism",
            "strain_name",
            "density",
        ],
    }


def test_demo_data_models_virtual_min_evolver_components():
    demo_data = _projected_demo_data()

    mini = demo_data["evolver_units"][0]
    devices = demo_data["devices"]
    pumps = [device for device in devices if device["type"] == "pump"]
    sleeves = [
        device for device in devices if device["type"] == "smart_sleeve"
    ]

    assert mini["unit_type"] == "min_evolver"
    assert mini["command_interface"] == "stubbed_virtual_evolver"
    assert len(sleeves) == 2
    assert len(pumps) == 6
    assert {pump["action_stub"] for pump in pumps} == {
        "virtual_evolver.run_pump"
    }
    assert all(
        device["evolver_id"] == "virtual-mini-evolver-1"
        for device in devices
    )


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


def test_inventory_add_uses_template_form(monkeypatch):
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
    pushed_titles = []

    def fake_push_screen(screen, callback=None, *args, **kwargs):
        pushed_titles.append(screen._template["title"])
        if callback is not None:
            callback({
                "id": "mat-test",
                "name": "Test material",
                "type": "reagent",
            })

    monkeypatch.setattr(app, "push_screen", fake_push_screen)

    async def run_app():
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("3")
            await pilot.press("]")
            assert app.focused is not None
            assert app.focused.id == "mat-list"

            await pilot.press("a")
            await pilot.pause()

            assert pushed_titles == ["New Material"]
            material_list = app.query_one("#mat-list")
            assert len(material_list.children) == 1

    asyncio.run(run_app())


def test_inventory_protocol_edit_uses_template_form(monkeypatch):
    from evolver_integrated.tui.app import EvolverTUI
    from evolver_integrated.tui.panels import InventoryPanel

    _stub_tui_client(monkeypatch)

    app = EvolverTUI()
    pushed = []

    def fake_push_screen(screen, callback=None, *args, **kwargs):
        pushed.append((screen._template["title"], screen._initial_record))
        if callback is not None:
            callback({
                "id": "batch-growth",
                "name": "Batch Growth Edited",
                "description": "Edited",
                "steps": [],
            })

    monkeypatch.setattr(app, "push_screen", fake_push_screen)

    async def run_app():
        async with app.run_test() as pilot:
            await pilot.pause()
            inventory = app.query_one(InventoryPanel)
            inventory.update_protocols([
                {
                    "id": "batch-growth",
                    "name": "Batch Growth",
                    "description": "Simple run",
                    "steps": [],
                }
            ])

            await pilot.press("3")
            assert app.focused is not None
            assert app.focused.id == "proto-list"

            await pilot.press("e")
            await pilot.pause()

            assert pushed == [
                (
                    "Edit Protocol",
                    {
                        "id": "batch-growth",
                        "name": "Batch Growth",
                        "description": "Simple run",
                        "steps": [],
                    },
                )
            ]
            assert inventory._protocols[0]["name"] == "Batch Growth Edited"

    asyncio.run(run_app())


def test_steps_add_and_edit_use_template_forms(monkeypatch):
    from evolver_integrated.tui.app import EvolverTUI
    from evolver_integrated.tui.panels import StepsPanel

    _stub_tui_client(monkeypatch)

    app = EvolverTUI()
    pushed_titles = []

    def fake_push_screen(screen, callback=None, *args, **kwargs):
        pushed_titles.append(screen._template["title"])
        if callback is None:
            return
        if screen._template["title"] == "New Step":
            callback({
                "name": "sample",
                "description": "Take a sample",
                "components": [],
            })
        else:
            callback({
                "name": "grow edited",
                "description": "Grow culture longer",
                "components": [],
            })

    monkeypatch.setattr(app, "push_screen", fake_push_screen)

    async def run_app():
        async with app.run_test() as pilot:
            await pilot.pause()
            protocol = {
                "id": "batch-growth",
                "name": "Batch Growth",
                "steps": [
                    {
                        "name": "grow",
                        "description": "Grow culture",
                        "components": [],
                    }
                ],
            }
            steps = app.query_one(StepsPanel)
            steps.load_protocol(protocol)

            await pilot.press("4")
            assert app.focused is not None
            assert app.focused.id == "steps-list"

            await pilot.press("a")
            await pilot.pause()
            assert protocol["steps"][1]["name"] == "sample"

            steps.query_one("#steps-list").index = 0
            await pilot.press("e")
            await pilot.pause()

            assert pushed_titles == ["New Step", "Edit Step"]
            assert protocol["steps"][0]["name"] == "grow edited"

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


def test_live_services_footer_updates_when_switching_tabs(monkeypatch):
    from textual.widgets import Footer

    from evolver_integrated.tui.app import EvolverTUI
    from evolver_integrated.tui.panels import LivePanel

    _stub_tui_client(monkeypatch)

    app = EvolverTUI()

    async def run_app():
        async with app.run_test() as pilot:
            await pilot.pause()
            live = app.query_one(LivePanel)
            live.update_services([
                {
                    "id": "control-plane",
                    "name": "Control Plane",
                    "state": "running",
                    "category": "core",
                }
            ])

            await pilot.press("]")
            await pilot.press("]")
            await pilot.pause()

            assert app.focused is not None
            assert app.focused.id == "service-list"
            assert app.query_one("#service-list").index == 0

            footer_actions = {
                getattr(child, "action", None)
                for child in app.query_one(Footer).children
            }
            assert "config_item" in footer_actions
            assert "run_or_restart" in footer_actions
            assert "pause_or_resume" in footer_actions

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


def test_experiment_refresh_only_updates_current_live_experiments_context(monkeypatch):
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
    monkeypatch.setattr(EvolverTUI, "set_interval", lambda *args, **kwargs: None)

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
            live = app.query_one(LivePanel)
            rendered.clear()

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
            await pilot.pause()
            rendered.clear()
            selected["state"] = "paused"
            await app._refresh_experiments()
            await pilot.pause()
            assert rendered
            assert set(rendered) == {"exp-1"}
            assert live._experiments == [selected]

    asyncio.run(run_app())


def test_refresh_does_not_create_competing_context_writes(monkeypatch):
    from evolver_integrated.tui.app import EvolverTUI
    from evolver_integrated.tui.panels import MainDisplay

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
    monkeypatch.setattr(EvolverTUI, "set_interval", lambda *args, **kwargs: None)

    context_writes = []
    original_update = MainDisplay._update

    def record_update(self, lines):
        context_writes.append(lines[0] if lines else "")
        original_update(self, lines)

    monkeypatch.setattr(MainDisplay, "_update", record_update)

    app = EvolverTUI()

    async def run_app():
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.focused is not None
            assert app.focused.id == "exp-list"

            await pilot.press("3")
            await pilot.pause()
            assert app.focused is not None
            assert app.focused.id == "proto-list"

            context_writes.clear()
            await app._refresh_experiments()
            await pilot.pause()

            assert context_writes == []

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
