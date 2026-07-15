from evolver_integrated.service_manager import SERVICE_PAUSED
from evolver_integrated.service_manager import SERVICE_RUNNING
from evolver_integrated.service_manager import SERVICE_STOPPED
from evolver_integrated.service_manager import InvalidServiceActionError
from evolver_integrated.service_manager import ServiceManager
from evolver_integrated.service_manager import ServiceNotFoundError


class FakeProcess(object):
    def __init__(self):
        self.returncode = None
        self.signals = []
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.returncode

    def send_signal(self, signal_number):
        self.signals.append(signal_number)

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, timeout=None):
        if self.returncode is None:
            self.returncode = 0
        return self.returncode


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
    command: nix run path:deprecated/evolver#default
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


def test_service_manager_can_own_service_process_lifecycle():
    created = []

    def popen_factory(command, **kwargs):
        process = FakeProcess()
        created.append((command, kwargs, process))
        return process

    manager = ServiceManager(
        [{"id": "svc", "command": "python -m service"}],
        popen_factory=popen_factory,
    )

    started = manager.apply_action("svc", "start")
    assert started["state"] == SERVICE_RUNNING
    assert created[0][0] == "python -m service"
    assert created[0][1]["shell"] is True

    paused = manager.apply_action("svc", "pause")
    assert paused["state"] == SERVICE_PAUSED
    assert created[0][2].signals

    resumed = manager.apply_action("svc", "resume")
    assert resumed["state"] == SERVICE_RUNNING

    stopped = manager.apply_action("svc", "stop")
    assert stopped["state"] == SERVICE_STOPPED
    assert created[0][2].terminated is True
