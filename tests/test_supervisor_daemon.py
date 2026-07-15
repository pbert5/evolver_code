from evolver_integrated.service_manager import ServiceManager
from evolver_integrated.supervisor_daemon import DEFAULT_SUPERVISOR_PORT
from evolver_integrated.supervisor_daemon import create_app
from evolver_integrated.supervisor_daemon import parse_args


def test_supervisor_daemon_default_port():
    args = parse_args(["--no-autostart"])

    assert DEFAULT_SUPERVISOR_PORT == 18083
    assert args.port == 18083
    assert args.no_autostart is True


def test_supervisor_daemon_exposes_service_routes():
    app = create_app(ServiceManager([{"id": "svc"}]))

    routes = {(route.method, route.resource.canonical) for route in app.router.routes()}

    assert ("GET", "/health") in routes
    assert ("GET", "/services") in routes
    assert ("POST", "/services/{service_id}/{action}") in routes
