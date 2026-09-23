from __future__ import annotations

from .gateway import ToolGateway, ToolSpec
from ..models import AccessLevel


class MockEngineeringSystems:
    """Deterministic local signals for the first demo and evaluation fixtures."""

    def get_service_health(self, service: str) -> dict:
        return {
            "service": service,
            "status": "degraded",
            "http5xx_rate": 0.42,
            "db_connections_max": 100,
        }

    def get_recent_deployments(self, service: str) -> list[dict]:
        return [
            {"id": "184", "service": service, "status": "completed", "commit": "abc123"}
        ]

    def search_logs(self, service: str, query: str) -> list[dict]:
        return [
            {
                "service": service,
                "message": "HikariPool - Connection is not available, timeout",
            }
        ]

    def query_metrics(self, service: str, metric: str) -> dict:
        return {
            "service": service,
            "metric": metric,
            "value": 100,
            "configured_max": 100,
        }

    def get_database_diagnostics(self, service: str) -> dict:
        return {
            "service": service,
            "active_connections": 100,
            "max_connections": 100,
            "long_running_queries": [
                {"query": "UPDATE orders", "duration_seconds": 187}
            ],
            "lock_waits": 3,
        }

    def get_configuration(self, service: str) -> dict:
        return {
            "service": service,
            "database_pool_max": 100,
            "transaction_timeout_seconds": 30,
            "deployment_id": "184",
        }

    def get_pod_status(self, service: str) -> dict:
        return {
            "service": service,
            "pod_status": "Running",
            "restart_count": 0,
            "events": [],
        }

    def get_kubernetes_events(self, service: str) -> list[dict]:
        return []

    def inspect_git_commit(self, commit_sha: str) -> dict:
        return {
            "sha": commit_sha,
            "changed_files": ["src/checkout/CheckoutService.java"],
            "summary": "Extended transaction scope",
        }


def build_mock_gateway(systems: MockEngineeringSystems | None = None) -> ToolGateway:
    systems = systems or MockEngineeringSystems()
    gateway = ToolGateway()
    for name, handler in {
        "get_service_health": systems.get_service_health,
        "get_recent_deployments": systems.get_recent_deployments,
        "search_logs": systems.search_logs,
        "query_metrics": systems.query_metrics,
        "get_database_diagnostics": systems.get_database_diagnostics,
        "get_configuration": systems.get_configuration,
        "get_pod_status": systems.get_pod_status,
        "get_kubernetes_events": systems.get_kubernetes_events,
        "inspect_git_commit": systems.inspect_git_commit,
    }.items():
        gateway.register(ToolSpec(name, AccessLevel.READ, handler))
    gateway.register(
        ToolSpec(
            "rollback_deployment",
            AccessLevel.APPROVAL_REQUIRED,
            lambda **_: {"status": "requested"},
        )
    )
    return gateway
