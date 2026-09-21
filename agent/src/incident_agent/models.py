from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class AccessLevel(str, Enum):
    READ = "READ"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"


@dataclass(frozen=True)
class Incident:
    description: str
    service: str
    started_at: datetime | None = None


@dataclass(frozen=True)
class Evidence:
    source: str
    finding: str
    tool: str
    collected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class Recommendation:
    action: str
    reason: str
    requires_approval: bool = True


@dataclass(frozen=True)
class InvestigationResult:
    incident: Incident
    root_cause: str
    confidence: float
    evidence: tuple[Evidence, ...]
    recommendations: tuple[Recommendation, ...]

    def as_dict(self) -> dict:
        return {
            "incident": self.incident.description,
            "service": self.incident.service,
            "rootCause": self.root_cause,
            "confidence": self.confidence,
            "evidence": [{"source": e.source, "finding": e.finding, "tool": e.tool} for e in self.evidence],
            "recommendedActions": [r.action for r in self.recommendations],
        }
