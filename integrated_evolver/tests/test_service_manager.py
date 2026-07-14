from evolver_integrated.service_manager import SERVICE_PAUSED
from evolver_integrated.service_manager import SERVICE_RUNNING
from evolver_integrated.service_manager import SERVICE_STOPPED
from evolver_integrated.service_manager import InvalidServiceActionError
from evolver_integrated.service_manager import ServiceManager
from evolver_integrated.service_manager import ServiceNotFoundError


def test_service_manager_loads_catalog_and_tracks_actions(tmp_path):
    catalog = tmp_path / "services.yaml"
    catalog.write_text(
        """
services:
  - id: control-plane
    name: Control Plane
    category: core
    supervisor_state: running
  - id: evolver-server
    name: eVOLVER Server
    category: managed
    command: nix run ../evolver#default
"""
    )

    manager = ServiceManager.from_yaml(str(catalog))

    services = manager.list_services()
    assert [service["id"] for service in services] == [
        "control-plane",
        "evolver-server",
    ]
    assert services[0]["state"] == SERVICE_RUNNING
    assert services[1]["state"] == SERVICE_STOPPED

    paused = manager.apply_action("evolver-server", "pause")
    assert paused["state"] == SERVICE_PAUSED

    restarted = manager.apply_action("evolver-server", "restart")
    assert restarted["state"] == SERVICE_RUNNING
    assert restarted["restart_count"] == 1
    assert restarted["last_action"] == "restart"


def test_service_manager_rejects_unknown_service_and_action():
    manager = ServiceManager([{"id": "svc"}])

    try:
        manager.apply_action("missing", "start")
    except ServiceNotFoundError:
        pass
    else:
        raise AssertionError("expected ServiceNotFoundError")

    try:
        manager.apply_action("svc", "explode")
    except InvalidServiceActionError:
        pass
    else:
        raise AssertionError("expected InvalidServiceActionError")
