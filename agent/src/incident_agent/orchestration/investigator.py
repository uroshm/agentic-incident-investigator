from __future__ import annotations

from ..models import Evidence, Incident, InvestigationResult, Recommendation
from ..tools.gateway import ToolGateway
from .hypotheses import HypothesisEngine


class Investigator:
    """A deterministic baseline loop; a model-backed planner can replace it later."""

    def __init__(self, gateway: ToolGateway) -> None:
        self.gateway = gateway
        self.hypotheses = HypothesisEngine()

    def investigate(self, incident: Incident) -> InvestigationResult:
        self.gateway.audit.record("investigation_started", service=incident.service)
        health = self.gateway.call("get_service_health", service=incident.service)
        deployments = self.gateway.call(
            "get_recent_deployments", service=incident.service
        )
        logs = self.gateway.call("search_logs", service=incident.service, query="pool")
        metrics = self.gateway.call(
            "query_metrics", service=incident.service, metric="db_connections_active"
        )
        database = self.gateway.call(
            "get_database_diagnostics", service=incident.service
        )
        configuration = self.gateway.call("get_configuration", service=incident.service)
        pod = self.gateway.call("get_pod_status", service=incident.service)
        kubernetes_events = self.gateway.call(
            "get_kubernetes_events", service=incident.service
        )
        deployment = (
            deployments[0] if deployments else {"id": "unknown", "commit": "unknown"}
        )
        commit = self.gateway.call(
            "inspect_git_commit", commit_sha=deployment["commit"]
        )
        context = {
            "health": health,
            "database": database,
            "logs": logs,
            "configuration": configuration,
            "pod": pod,
            "deployment": deployment,
        }
        winner, ranked = self.hypotheses.evaluate(context)
        self.gateway.audit.record(
            "hypotheses_ranked",
            candidates=[
                {
                    "name": item.name,
                    "score": item.score,
                    "signals": item.matched_signals,
                }
                for item in ranked
            ],
        )
        confidence = min(0.98, 0.25 + winner.score / 12) if winner.score else 0.2
        self.gateway.audit.record(
            "hypothesis_selected" if winner.score else "hypothesis_unresolved",
            hypothesis=winner.name,
            confidence=confidence,
        )
        long_running_queries = database["long_running_queries"]
        evidence = (
            Evidence(
                "health",
                f"Service is degraded with HTTP 5xx rate {health['http5xx_rate']}",
                "get_service_health",
            ),
            Evidence(
                "deployment",
                f"Deployment {deployment['id']} completed before the incident",
                "get_recent_deployments",
            ),
            Evidence(
                "logs", logs[0].get("message", "Pool error detected"), "search_logs"
            )
            if logs
            else Evidence("logs", "No pool error found", "search_logs"),
            Evidence(
                "metrics",
                f"Active database connections: {metrics['value']} / {configuration['database_pool_max']}",
                "query_metrics",
            ),
            Evidence(
                "database",
                f"{len(long_running_queries)} long-running query(s), {database['lock_waits']} lock wait(s)",
                "get_database_diagnostics",
            ),
            Evidence(
                "runtime",
                f"Pod status {pod['pod_status']} with {pod['restart_count']} restart(s)",
                "get_pod_status",
            ),
            Evidence(
                "kubernetes",
                f"{len(kubernetes_events)} Kubernetes event(s) found",
                "get_kubernetes_events",
            ),
            Evidence("source", commit["summary"], "inspect_git_commit"),
        )
        recommendations = (
            winner.recommendations
            if winner.score
            else (
                Recommendation(
                    "Collect additional read-only evidence",
                    "The current signals do not support a high-confidence diagnosis.",
                    False,
                ),
            )
        )
        result = InvestigationResult(
            incident=incident,
            root_cause=winner.root_cause
            if winner.score
            else "Insufficient evidence to identify a root cause.",
            confidence=confidence,
            evidence=evidence,
            recommendations=recommendations,
        )
        self.gateway.audit.record("diagnosis_generated", confidence=result.confidence)
        return result
