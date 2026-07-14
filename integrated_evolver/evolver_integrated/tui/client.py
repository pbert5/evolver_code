"""HTTP client for the integrated eVOLVER control-plane API."""
from __future__ import annotations

import aiohttp


class APIError(Exception):
    pass


class ControlAPIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8082") -> None:
        self.base_url = base_url.rstrip("/")
        self._session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        self._session = aiohttp.ClientSession()

    async def stop(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def health(self) -> dict:
        return await self._get("/health")

    async def list_experiments(self) -> list:
        data = await self._get("/experiments")
        return data.get("experiments", [])

    async def create_experiment(
        self,
        name: str,
        protocol: str = "default",
        machine_id: str = "machine-1",
        vials: list[int] | None = None,
    ) -> dict:
        vials = [0] if vials is None else vials
        return await self._post(
            "/experiments",
            {
                "name": name,
                "machine_id": machine_id,
                "vials": vials,
                "metadata": {"protocol": protocol},
            },
        )

    async def start_experiment(self, exp_id: str) -> dict:
        return await self._post(f"/experiments/{exp_id}/start", {})

    async def pause_experiment(self, exp_id: str) -> dict:
        return await self._post(f"/experiments/{exp_id}/pause", {})

    async def resume_experiment(self, exp_id: str) -> dict:
        return await self._post(f"/experiments/{exp_id}/resume", {})

    async def stop_experiment(self, exp_id: str) -> dict:
        return await self._post(f"/experiments/{exp_id}/stop", {})

    async def list_jobs(self) -> list:
        data = await self._get("/jobs")
        return data.get("jobs", [])

    async def list_services(self) -> list:
        data = await self._get("/services")
        return data.get("services", [])

    async def service_action(self, service_id: str, action: str) -> dict:
        return await self._post(f"/services/{service_id}/{action}", {})

    async def _get(self, path: str) -> dict:
        assert self._session is not None, "client not started"
        try:
            async with self._session.get(f"{self.base_url}{path}") as r:
                if r.status >= 400:
                    raise APIError(f"GET {path} → {r.status}")
                return await r.json()
        except aiohttp.ClientError as exc:
            raise APIError(str(exc)) from exc

    async def _post(self, path: str, payload: dict) -> dict:
        assert self._session is not None, "client not started"
        try:
            async with self._session.post(
                f"{self.base_url}{path}", json=payload
            ) as r:
                if r.status >= 400:
                    raise APIError(f"POST {path} → {r.status}")
                return await r.json()
        except aiohttp.ClientError as exc:
            raise APIError(str(exc)) from exc
