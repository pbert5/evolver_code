"""Standalone local supervisor for integrated eVOLVER services."""

from __future__ import absolute_import

import argparse
import os

from aiohttp import web

from .service_manager import ServiceManager
from .service_manager import ServiceManagerError
from .service_manager import default_service_catalog_path


DEFAULT_SUPERVISOR_HOST = "127.0.0.1"
DEFAULT_SUPERVISOR_PORT = 18083


try:
    SERVICE_MANAGER_KEY = web.AppKey("service_manager", object)
except AttributeError:
    SERVICE_MANAGER_KEY = "service_manager"


def create_app(service_manager):
    app = web.Application()
    app[SERVICE_MANAGER_KEY] = service_manager
    app.router.add_get("/health", _health)
    app.router.add_get("/services", _list_services)
    app.router.add_post("/services/{service_id}/{action}", _service_action)
    return app


async def _health(_request):
    return web.json_response({"ok": True, "service": "evolver-supervisord"})


async def _list_services(request):
    service_manager = request.app[SERVICE_MANAGER_KEY]
    return web.json_response({"services": service_manager.list_services()})


async def _service_action(request):
    service_manager = request.app[SERVICE_MANAGER_KEY]
    try:
        service = service_manager.apply_action(
            request.match_info["service_id"],
            request.match_info["action"],
        )
        return web.json_response({"service": service})
    except ServiceManagerError as exc:
        return web.json_response({"error": str(exc)}, status=400)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Run the local eVOLVER supervisor.",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get(
            "EVOLVER_SUPERVISOR_HOST",
            DEFAULT_SUPERVISOR_HOST,
        ),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(
            os.environ.get("EVOLVER_SUPERVISOR_PORT", DEFAULT_SUPERVISOR_PORT)
        ),
    )
    parser.add_argument(
        "--services-config",
        default=os.environ.get(
            "EVOLVER_SERVICES_CONFIG",
            default_service_catalog_path(),
        ),
    )
    parser.add_argument(
        "--no-autostart",
        action="store_true",
        help="Load service catalog without starting autostart services.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    service_manager = ServiceManager.from_yaml(args.services_config)
    if not args.no_autostart:
        service_manager.start_autostart_services()
    app = create_app(service_manager)
    web.run_app(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
