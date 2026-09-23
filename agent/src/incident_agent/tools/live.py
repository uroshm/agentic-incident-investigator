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

    def get_database_diagnostics(self, service: str) -> dict[str, Any]:
        return self._get_json("/diagnostics/database")

    def get_configuration(self, service: str) -> dict[str, Any]:
        return self._get_json("/diagnostics/configuration")

    def get_pod_status(self, service: str) -> dict[str, Any]:
        return self._get_json("/diagnostics/kubernetes")

    def get_kubernetes_events(self, service: str) -> list[dict[str, Any]]:
        return self._get_json("/diagnostics/kubernetes")["events"]

    def inspect_git_commit(self, commit_sha: str) -> dict[str, Any]:
        return self._get_json(f"/diagnostics/source?{urlencode({'sha': commit_sha})}")


def build_live_gateway(base_url: str) -> ToolGateway:
    systems = LiveEngineeringSystems(base_url)
    gateway = ToolGateway()
    service_schema = {
        "type": "object",
        "properties": {"service": {"type": "string"}},
        "required": ["service"],
    }
    tools = [
        (
            "get_service_health",
            systems.get_service_health,
            "Get current service health and error rate.",
            service_schema,
        ),
        (
            "get_recent_deployments",
            systems.get_recent_deployments,
            "Get recent deployments and commit identifiers.",
            service_schema,
        ),
        (
            "search_logs",
            systems.search_logs,
            "Search recent service logs for a specific failure pattern.",
            {
                "type": "object",
                "properties": {
                    "service": {"type": "string"},
                    "query": {"type": "string"},
                },
                "required": ["service", "query"],
            },
        ),
        (
            "query_metrics",
            systems.query_metrics,
            "Read a named Prometheus-style service metric.",
            {
                "type": "object",
                "properties": {
                    "service": {"type": "string"},
                    "metric": {"type": "string"},
                },
                "required": ["service", "metric"],
            },
        ),
        (
            "get_database_diagnostics",
            systems.get_database_diagnostics,
            "Inspect pool saturation, long-running queries, and lock waits.",
            service_schema,
        ),
        (
            "get_configuration",
            systems.get_configuration,
            "Read runtime configuration relevant to the service.",
            service_schema,
        ),
        (
            "get_pod_status",
            systems.get_pod_status,
            "Read pod status and restart count.",
            service_schema,
        ),
        (
            "get_kubernetes_events",
            systems.get_kubernetes_events,
            "Read recent Kubernetes events for the service.",
            service_schema,
        ),
        (
            "inspect_git_commit",
            systems.inspect_git_commit,
            "Inspect files and summary for a deployment commit.",
            {
                "type": "object",
                "properties": {"commit_sha": {"type": "string"}},
                "required": ["commit_sha"],
            },
        ),
    ]
    for name, handler, description, input_schema in tools:
        gateway.register(
            ToolSpec(name, AccessLevel.READ, handler, description, input_schema)
        )
    return gateway
