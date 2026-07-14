"""Configured service lifecycle state for the integrated runtime."""

from __future__ import annotations

from pathlib import Path
import signal
import subprocess
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
    """Configured service registry with optional subprocess ownership."""

    def __init__(self, services: Iterable[dict], popen_factory=None):
        self._services = {}
        self._processes = {}
        self._popen_factory = popen_factory or subprocess.Popen
        for service in services:
            normalized = self._normalize_service(service)
            self._services[normalized["id"]] = normalized

    @classmethod
    def from_yaml(cls, path=None, popen_factory=None):
        path = path or default_service_catalog_path()
        with open(path) as handle:
            data = yaml.safe_load(handle) or {}
        services = data.get("services", [])
        if not isinstance(services, list):
            raise ServiceManagerError("services must be a list")
        return cls(services, popen_factory=popen_factory)

    def start_autostart_services(self):
        for service in list(self._services.values()):
            if service["autostart"]:
                self.apply_action(service["id"], "start")

    def list_services(self):
        for service_id in list(self._services):
            self._refresh_service_state(service_id)
        return [
            dict(service)
            for service in sorted(
                self._services.values(),
                key=lambda item: (item["category"], item["name"]),
            )
        ]

    def service_status(self, service_id):
        self._refresh_service_state(service_id)
        return dict(self._get_service(service_id))

    def apply_action(self, service_id, action):
        if action not in SERVICE_ACTIONS:
            raise InvalidServiceActionError("unsupported service action")
        service = self._get_service(service_id)
        if action == "start":
            self._start_service(service)
        elif action == "stop":
            self._stop_service(service)
        elif action == "pause":
            self._pause_service(service)
        elif action == "resume":
            self._resume_service(service)
        elif action == "restart":
            self._stop_service(service)
            self._start_service(service)
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
            "autostart": bool(service.get("autostart", False)),
        }

    def _start_service(self, service):
        process = self._processes.get(service["id"])
        if process is not None and process.poll() is None:
            service["state"] = SERVICE_RUNNING
            return
        command = service.get("command")
        if command:
            self._processes[service["id"]] = self._popen_factory(
                command,
                shell=True,
            )
        service["state"] = SERVICE_RUNNING

    def _stop_service(self, service):
        process = self._processes.pop(service["id"], None)
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        service["state"] = SERVICE_STOPPED

    def _pause_service(self, service):
        process = self._processes.get(service["id"])
        if process is not None and process.poll() is None:
            process.send_signal(signal.SIGSTOP)
        service["state"] = SERVICE_PAUSED

    def _resume_service(self, service):
        process = self._processes.get(service["id"])
        if process is not None and process.poll() is None:
            process.send_signal(signal.SIGCONT)
        service["state"] = SERVICE_RUNNING

    def _refresh_service_state(self, service_id):
        service = self._get_service(service_id)
        process = self._processes.get(service_id)
        if process is None:
            return
        returncode = process.poll()
        if returncode is None:
            return
        self._processes.pop(service_id, None)
        service["state"] = (
            SERVICE_STOPPED if returncode == 0 else SERVICE_FAILED
        )
