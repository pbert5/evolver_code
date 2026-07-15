"""HTTP proxy for the local eVOLVER supervisor service API."""

from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import Request
from urllib.request import urlopen

from .service_manager import ServiceManagerError


class SupervisorClientError(ServiceManagerError):
    pass


class SupervisorServiceManager(object):
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_services(self):
        return _run_json("GET", f"{self.base_url}/services").get(
            "services", []
        )

    def apply_action(self, service_id, action):
        data = _run_json(
            "POST",
            f"{self.base_url}/services/{service_id}/{action}",
        )
        return data.get("service", {})


def _run_json(method, url):
    request = Request(url, method=method)
    if method == "POST":
        request.add_header("Content-Type", "application/json")
        request.data = b"{}"
    try:
        with urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise SupervisorClientError(
            f"{method} {url} -> {exc.code}"
        ) from exc
    except URLError as exc:
        raise SupervisorClientError(str(exc)) from exc
