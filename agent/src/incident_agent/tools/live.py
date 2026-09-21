from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from .gateway import ToolGateway, ToolSpec
from ..models import AccessLevel


class LiveEngineeringSystems:
    """HTTP adapter for the running mock SaaS diagnostic endpoints."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def _get_json(self, path: str) -> dict[str, Any]:
        with urlopen(f"{self.base_url}{path}", timeout=3) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_service_health(self, service: str) -> dict[str, Any]:
        return self._get_json("/health")

    def get_recent_deployments(self, service: str) -> list[dict[str, Any]]:
        return self._get_json("/diagnostics/deployments")["deployments"]

    def search_logs(self, service: str, query: str) -> list[dict[str, Any]]:
        logs = self._get_json("/diagnostics/logs")["logs"]
        return [log for log in logs if query.lower() in str(log).lower()]

    def query_metrics(self, service: str, metric: str) -> dict[str, Any]:
        with urlopen(f"{self.base_url}/metrics", timeout=3) as response:
            body = response.read().decode("utf-8")
        values: dict[str, float] = {}
        for line in body.splitlines():
            if line.startswith(metric + "{"):
                values[metric] = float(line.rsplit(" ", 1)[1])
        return {"service": service, "metric": metric, "value": values.get(metric, 0.0)}

    def inspect_git_commit(self, commit_sha: str) -> dict[str, Any]:
        return self._get_json(f"/diagnostics/source?{urlencode({'sha': commit_sha})}")


def build_live_gateway(base_url: str) -> ToolGateway:
    systems = LiveEngineeringSystems(base_url)
    gateway = ToolGateway()
    for name, handler in {
        "get_service_health": systems.get_service_health,
        "get_recent_deployments": systems.get_recent_deployments,
        "search_logs": systems.search_logs,
        "query_metrics": systems.query_metrics,
        "inspect_git_commit": systems.inspect_git_commit,
    }.items():
        gateway.register(ToolSpec(name, AccessLevel.READ, handler))
    return gateway
