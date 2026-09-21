from __future__ import annotations

from .gateway import ToolGateway, ToolSpec
from ..models import AccessLevel


class MockEngineeringSystems:
    """Deterministic local signals for the first demo and evaluation fixtures."""

    def get_service_health(self, service: str) -> dict:
        return {"service": service, "status": "degraded", "http5xx_rate": 0.42, "db_connections_max": 100}

    def get_recent_deployments(self, service: str) -> list[dict]:
        return [{"id": "184", "service": service, "status": "completed", "commit": "abc123"}]

    def search_logs(self, service: str, query: str) -> list[dict]:
        return [{"service": service, "message": "HikariPool - Connection is not available, timeout"}]

    def query_metrics(self, service: str, metric: str) -> dict:
        return {"service": service, "metric": metric, "value": 100, "configured_max": 100}

    def inspect_git_commit(self, commit_sha: str) -> dict:
        return {"sha": commit_sha, "changed_files": ["src/checkout/CheckoutService.java"], "summary": "Extended transaction scope"}


def build_mock_gateway(systems: MockEngineeringSystems | None = None) -> ToolGateway:
    systems = systems or MockEngineeringSystems()
    gateway = ToolGateway()
    for name, handler in {
        "get_service_health": systems.get_service_health,
        "get_recent_deployments": systems.get_recent_deployments,
        "search_logs": systems.search_logs,
        "query_metrics": systems.query_metrics,
        "inspect_git_commit": systems.inspect_git_commit,
    }.items():
        gateway.register(ToolSpec(name, AccessLevel.READ, handler))
    gateway.register(ToolSpec("rollback_deployment", AccessLevel.APPROVAL_REQUIRED, lambda **_: {"status": "requested"}))
    return gateway
