"""Tests for the eVOLVER TUI package."""
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
    assert c.base_url == "http://localhost:8080"


def test_client_custom_url_strips_trailing_slash():
    from evolver_integrated.tui.client import ControlAPIClient
    c = ControlAPIClient("http://localhost:9999/")
    assert c.base_url == "http://localhost:9999"


def test_client_not_started_has_no_session():
    from evolver_integrated.tui.client import ControlAPIClient
    c = ControlAPIClient()
    assert c._session is None


# ── EvolverTUI construction ───────────────────────────────────────────────────


def test_evolver_tui_default_url():
    from evolver_integrated.tui.app import EvolverTUI
    app = EvolverTUI()
    assert app._client.base_url == "http://localhost:8080"


def test_evolver_tui_custom_url():
    from evolver_integrated.tui.app import EvolverTUI
    app = EvolverTUI(api_url="http://192.168.1.10:8080")
    assert "192.168.1.10" in app._client.base_url


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
