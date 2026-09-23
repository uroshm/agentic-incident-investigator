from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from ..models import AccessLevel


class ToolDenied(PermissionError):
    """Raised when a caller attempts a tool outside its permission boundary."""


@dataclass(frozen=True)
class ToolSpec:
    name: str
    access: AccessLevel
    handler: Callable[..., Any]
    description: str = ""
    input_schema: dict[str, Any] | None = None


class AuditLog:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def record(self, event: str, **details: Any) -> None:
        self.events.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": event,
                **details,
            }
        )


class ToolGateway:
    """The server-side policy boundary around engineering-system tools."""

    def __init__(self, audit_log: AuditLog | None = None) -> None:
        self.audit = audit_log or AuditLog()
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"Tool already registered: {spec.name}")
        self._tools[spec.name] = spec

    def call(self, name: str, *, approval_granted: bool = False, **kwargs: Any) -> Any:
        spec = self._tools.get(name)
        if spec is None:
            self.audit.record("tool_call_denied", tool=name, reason="unknown_tool")
            raise ToolDenied(f"Unknown tool: {name}")
        if spec.access is AccessLevel.APPROVAL_REQUIRED and not approval_granted:
            self.audit.record("tool_call_denied", tool=name, reason="approval_required")
            raise ToolDenied(f"Approval required for tool: {name}")
        self.audit.record(
            "tool_call_started", tool=name, access=spec.access.value, arguments=kwargs
        )
        try:
            result = spec.handler(**kwargs)
        except Exception as exc:
            self.audit.record("tool_call_failed", tool=name, error=type(exc).__name__)
            raise
        self.audit.record("tool_call_succeeded", tool=name)
        return result

    @property
    def tools(self) -> tuple[ToolSpec, ...]:
        return tuple(self._tools.values())
