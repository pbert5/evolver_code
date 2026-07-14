"""Configured service lifecycle state for the integrated runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import yaml


SERVICE_RUNNING = "running"
SERVICE_STOPPED = "stopped"
SERVICE_PAUSED = "paused"
SERVICE_FAILED = "failed"
SERVICE_UNKNOWN = "unknown"

SERVICE_ACTIONS = {"start", "stop", "pause", "resume", "restart"}


class ServiceManagerError(Exception):
    pass


class ServiceNotFoundError(ServiceManagerError):
    pass


class InvalidServiceActionError(ServiceManagerError):
    pass


def default_service_catalog_path() -> str:
    return str(Path(__file__).with_name("service_catalog.yaml"))


class ServiceManager(object):
    """Small supervisor-shaped service registry.

    This tracks configured service state without owning subprocesses yet. The
    public shape is intentionally close to a future systemd/nix supervisor API.
    """

    def __init__(self, services: Iterable[dict]):
        self._services = {}
        for service in services:
            normalized = self._normalize_service(service)
            self._services[normalized["id"]] = normalized

    @classmethod
    def from_yaml(cls, path=None):
        path = path or default_service_catalog_path()
        with open(path) as handle:
            data = yaml.safe_load(handle) or {}
        services = data.get("services", [])
        if not isinstance(services, list):
            raise ServiceManagerError("services must be a list")
        return cls(services)

    def list_services(self):
        return [
            dict(service)
            for service in sorted(
                self._services.values(),
                key=lambda item: (item["category"], item["name"]),
            )
        ]

    def service_status(self, service_id):
        return dict(self._get_service(service_id))

    def apply_action(self, service_id, action):
        if action not in SERVICE_ACTIONS:
            raise InvalidServiceActionError("unsupported service action")
        service = self._get_service(service_id)
        if action == "start":
            service["state"] = SERVICE_RUNNING
        elif action == "stop":
            service["state"] = SERVICE_STOPPED
        elif action == "pause":
            service["state"] = SERVICE_PAUSED
        elif action == "resume":
            service["state"] = SERVICE_RUNNING
        elif action == "restart":
            service["state"] = SERVICE_RUNNING
            service["restart_count"] += 1
        service["last_action"] = action
        return dict(service)

    def _get_service(self, service_id):
        try:
            return self._services[service_id]
        except KeyError:
            raise ServiceNotFoundError("unknown service: " + str(service_id))

    def _normalize_service(self, service):
        if not isinstance(service, dict):
            raise ServiceManagerError("service entry must be a dictionary")
        service_id = service.get("id")
        if not service_id:
            raise ServiceManagerError("service id is required")
        category = service.get("category", "managed")
        state = service.get("supervisor_state", SERVICE_STOPPED)
        return {
            "id": str(service_id),
            "name": str(service.get("name", service_id)),
            "category": str(category),
            "command": str(service.get("command", "")),
            "description": str(service.get("description", "")),
            "state": str(state),
            "restart_count": int(service.get("restart_count", 0)),
            "last_action": service.get("last_action"),
        }
