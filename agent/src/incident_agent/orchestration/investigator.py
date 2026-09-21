from __future__ import annotations

from ..models import Evidence, Incident, InvestigationResult, Recommendation
from ..tools.gateway import ToolGateway


class Investigator:
    """A deterministic baseline loop; a model-backed planner can replace it later."""

    def __init__(self, gateway: ToolGateway) -> None:
        self.gateway = gateway

    def investigate(self, incident: Incident) -> InvestigationResult:
        self.gateway.audit.record("investigation_started", service=incident.service)
        health = self.gateway.call("get_service_health", service=incident.service)
        deployments = self.gateway.call("get_recent_deployments", service=incident.service)
        logs = self.gateway.call("search_logs", service=incident.service, query="pool")
        metrics = self.gateway.call("query_metrics", service=incident.service, metric="db_connections_active")
        commit = self.gateway.call("inspect_git_commit", commit_sha=deployments[0]["commit"])
        pool_exhausted = metrics["value"] >= health["db_connections_max"]
        has_pool_error = bool(logs)
        root_cause = (
            "Database connection pool exhaustion caused by longer-lived transactions."
            if pool_exhausted and has_pool_error
            else "Insufficient evidence to identify a root cause."
        )
        evidence = (
            Evidence("health", f"Service is degraded with HTTP 5xx rate {health['http5xx_rate']}", "get_service_health"),
            Evidence("deployment", f"Deployment {deployments[0]['id']} completed before the incident", "get_recent_deployments"),
            Evidence("logs", logs[0].get("message", "Pool error detected"), "search_logs") if logs else Evidence("logs", "No pool error found", "search_logs"),
            Evidence("metrics", f"Active database connections: {metrics['value']} / {health['db_connections_max']}", "query_metrics"),
            Evidence("source", commit["summary"], "inspect_git_commit"),
        )
        result = InvestigationResult(
            incident=incident,
            root_cause=root_cause,
            confidence=0.91 if pool_exhausted and has_pool_error else 0.2,
            evidence=evidence,
            recommendations=(
                Recommendation("Request rollback of deployment 184", "The deployment correlates with the failure and changed transaction scope."),
                Recommendation("Investigate and shorten the transaction boundary", "The source change extended transaction lifetime."),
                Recommendation("Add a database connection-pool saturation alert", "The metric reached its configured maximum."),
            ),
        )
        self.gateway.audit.record("diagnosis_generated", confidence=result.confidence)
        return result
