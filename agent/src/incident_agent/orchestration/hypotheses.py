from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..models import Recommendation


@dataclass(frozen=True)
class HypothesisResult:
    name: str
    root_cause: str
    score: int
    matched_signals: tuple[str, ...]
    recommendations: tuple[Recommendation, ...]


class HypothesisEngine:
    """Generate and rank explainable hypotheses from collected observations."""

    def evaluate(
        self, context: dict[str, Any]
    ) -> tuple[HypothesisResult, tuple[HypothesisResult, ...]]:
        candidates = (
            self._database_pool(context),
            self._kubernetes_crash_loop(context),
            self._configuration_failure(context),
            self._downstream_timeout(context),
        )
        ranked = tuple(sorted(candidates, key=lambda item: item.score, reverse=True))
        winner = ranked[0]
        return winner, ranked

    def _database_pool(self, context: dict[str, Any]) -> HypothesisResult:
        health = context["health"]
        database = context["database"]
        logs = context["logs"]
        configuration = context["configuration"]
        signals: list[str] = []
        score = 0
        if database["active_connections"] >= database["max_connections"]:
            score += 4
            signals.append("database connection pool is saturated")
        if database["long_running_queries"]:
            score += 3
            signals.append("long-running database query detected")
        if database["lock_waits"] > 0:
            score += 1
            signals.append(f"{database['lock_waits']} database lock wait(s)")
        if any("pool" in str(log).lower() for log in logs):
            score += 2
            signals.append("pool exhaustion error appears in logs")
        if health.get("status") == "degraded":
            score += 1
            signals.append("service health is degraded")

        deployment_id = context["deployment"].get("id", "unknown")
        max_duration = max(
            (
                query.get("duration_seconds", 0)
                for query in database["long_running_queries"]
            ),
            default=0,
        )
        recommendations = (
            Recommendation(
                f"Request rollback of deployment {deployment_id}",
                "The latest deployment is the strongest available change correlation.",
            ),
            Recommendation(
                "Investigate and shorten the transaction boundary",
                f"A database query has been running for {max_duration} seconds and is retaining connections.",
            ),
            Recommendation(
                "Add alerts for pool saturation, long-running queries, and lock waits",
                f"The configured pool maximum is {configuration['database_pool_max']} connections.",
            ),
        )
        return HypothesisResult(
            "database_pool_exhaustion",
            "Database connection pool exhaustion caused by long-lived transactions.",
            score,
            tuple(signals),
            recommendations,
        )

    def _kubernetes_crash_loop(self, context: dict[str, Any]) -> HypothesisResult:
        pod = context["pod"]
        signals: list[str] = []
        score = 0
        if pod.get("pod_status") != "Running":
            score += 5
            signals.append(f"pod status is {pod.get('pod_status')}")
        if pod.get("restart_count", 0) >= 3:
            score += 5
            signals.append(f"pod restarted {pod['restart_count']} times")
        return HypothesisResult(
            "kubernetes_crash_loop",
            "Service pod is unhealthy or repeatedly restarting.",
            score,
            tuple(signals),
            (
                Recommendation(
                    "Inspect container events and previous container logs",
                    "The pod is not stable.",
                    False,
                ),
            ),
        )

    def _configuration_failure(self, context: dict[str, Any]) -> HypothesisResult:
        health = context["health"]
        configuration = context["configuration"]
        database = context["database"]
        mismatch = database["max_connections"] != configuration["database_pool_max"]
        score = 3 if mismatch else 0
        signals = (
            ("runtime pool size differs from configured pool size",) if mismatch else ()
        )
        return HypothesisResult(
            "configuration_failure",
            "A runtime configuration mismatch is degrading the service.",
            score + (1 if health.get("status") == "degraded" and mismatch else 0),
            signals,
            (
                Recommendation(
                    "Compare deployed configuration with the expected configuration",
                    "Runtime and declared settings differ.",
                    False,
                ),
            ),
        )

    def _downstream_timeout(self, context: dict[str, Any]) -> HypothesisResult:
        logs = context["logs"]
        timeout_logs = [
            log
            for log in logs
            if "timeout" in str(log).lower() and "pool" not in str(log).lower()
        ]
        return HypothesisResult(
            "downstream_timeout",
            "A downstream dependency is timing out.",
            4 if timeout_logs else 0,
            ("downstream timeout appears in logs",) if timeout_logs else (),
            (
                Recommendation(
                    "Inspect downstream dependency health and latency",
                    "Timeouts are present in application logs.",
                    False,
                ),
            ),
        )
