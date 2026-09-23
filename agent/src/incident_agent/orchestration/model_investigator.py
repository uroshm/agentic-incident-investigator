from __future__ import annotations

import json
import copy
from typing import Any

from ..llm import OllamaClient
from ..models import Evidence, Incident, InvestigationResult, Recommendation
from ..tools.gateway import ToolGateway


SYSTEM_PROMPT = """You are an incident investigator operating inside a controlled engineering harness.
Investigate using read-only tools. Do not guess when evidence is missing.
Progressively gather evidence, compare at least two plausible hypotheses, and stop when the evidence is sufficient.
Before returning a diagnosis, call at least three different read-only tools and cite their observed results. Prefer health, deployment, logs, metrics, database, configuration, and runtime evidence over a single signal.
Do not call the same tool repeatedly. Each tool has a small call budget; use its previous result instead of polling it again.
Return only JSON with this shape:
{
  "rootCause": "...",
  "confidence": 0.0,
  "evidence": [{"tool": "tool_name", "finding": "specific observed fact"}],
  "recommendedActions": [{"action": "...", "reason": "...", "requiresApproval": true}]
}
Every evidence item must cite a tool you actually called. Recommendations must be safe and concrete.
"""


class ModelInvestigator:
    """A bounded tool-calling investigation loop driven by a local model."""

    def __init__(
        self,
        gateway: ToolGateway,
        model: OllamaClient,
        max_iterations: int = 6,
        max_tool_attempts: int = 2,
        minimum_evidence_sources: int = 3,
    ) -> None:
        self.gateway = gateway
        self.model = model
        self.max_iterations = max_iterations
        self.max_tool_attempts = max_tool_attempts
        self.minimum_evidence_sources = minimum_evidence_sources

    def investigate(self, incident: Incident) -> InvestigationResult:
        self.gateway.audit.record(
            "investigation_started", service=incident.service, mode="local_model"
        )
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {"service": incident.service, "incident": incident.description}
                ),
            },
        ]
        tool_attempts: dict[str, int] = {}
        trace: list[dict[str, Any]] = []

        for iteration in range(self.max_iterations):
            self.gateway.audit.record(
                "model_iteration_started", iteration=iteration + 1
            )
            trace.append(
                {
                    "turn": iteration + 1,
                    "direction": "model_request",
                    "messages": copy.deepcopy(messages),
                }
            )
            response = self.model.chat(messages, self.gateway)
            message = response.get("message", {})
            trace.append(
                {
                    "turn": iteration + 1,
                    "direction": "model_response",
                    "message": message,
                }
            )
            tool_calls = message.get("tool_calls", [])
            if not tool_calls:
                content = message.get("content", "")
                try:
                    result = self._parse_result(incident, content, trace)
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    self.gateway.audit.record(
                        "model_output_invalid",
                        error=type(exc).__name__,
                        detail=str(exc),
                        content=content,
                    )
                    messages.extend(
                        [
                            {"role": "assistant", "content": content},
                            {
                                "role": "user",
                                "content": "Your previous response was invalid: "
                                f"{exc}. Return valid JSON with rootCause, confidence, evidence, "
                                "and recommendedActions. Do not finish until evidence cites tools you called.",
                            },
                        ]
                    )
                    continue
                self.gateway.audit.record(
                    "diagnosis_generated",
                    confidence=result.confidence,
                    mode="local_model",
                )
                return result

            messages.append(message)
            for tool_call in tool_calls:
                function = tool_call.get("function", {})
                name = function.get("name")
                arguments = function.get("arguments", {})
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                attempts = tool_attempts.get(name, 0)
                if attempts >= self.max_tool_attempts:
                    self.gateway.audit.record("model_tool_budget_exhausted", tool=name)
                    tool_result = {
                        "error": "tool_call_budget_exhausted",
                        "tool": name,
                        "instruction": "Use the previous result and investigate with a different tool.",
                    }
                else:
                    tool_attempts[name] = attempts + 1
                    try:
                        tool_result = self.gateway.call(name, **arguments)
                    except Exception as exc:
                        self.gateway.audit.record(
                            "model_tool_error",
                            tool=name,
                            error=type(exc).__name__,
                            detail=str(exc),
                        )
                        tool_result = {
                            "error": "tool_call_failed",
                            "tool": name,
                            "detail": str(exc),
                            "instruction": "Correct the arguments and retry once, or choose another read-only tool.",
                        }
                trace.append(
                    {
                        "turn": iteration + 1,
                        "direction": "tool_result",
                        "tool": name,
                        "result": tool_result,
                    }
                )
                messages.append(
                    {
                        "role": "tool",
                        "content": json.dumps(tool_result),
                    }
                )

        messages.append(
            {
                "role": "user",
                "content": "The investigation tool budget is exhausted. Stop calling tools and return the final JSON diagnosis now using only the evidence already collected.",
            }
        )
        final_response = self.model.chat(messages, self.gateway, include_tools=False)
        final_message = final_response.get("message", {})
        trace.append(
            {
                "turn": self.max_iterations + 1,
                "direction": "model_request",
                "messages": copy.deepcopy(messages),
            }
        )
        trace.append(
            {
                "turn": self.max_iterations + 1,
                "direction": "model_response",
                "message": final_message,
            }
        )
        result = self._parse_result(incident, final_message.get("content", ""), trace)
        self.gateway.audit.record(
            "diagnosis_generated",
            confidence=result.confidence,
            mode="local_model",
            forced_finalization=True,
        )
        return result

    def _parse_result(
        self, incident: Incident, content: str, trace: list[dict[str, Any]]
    ) -> InvestigationResult:
        payload = json.loads(content.strip().strip("`").replace("json\n", "", 1))
        root_cause = str(
            payload.get("rootCause")
            or payload.get("root_cause")
            or payload.get("diagnosis")
        )
        if root_cause == "None":
            raise ValueError("Missing rootCause")
        confidence = float(payload.get("confidence", payload.get("confidence_score")))
        if not 0 <= confidence <= 1:
            raise ValueError("Model confidence must be between 0 and 1")
        called_tools = {
            event.get("tool")
            for event in self.gateway.audit.events
            if event.get("event") == "tool_call_succeeded"
        }
        evidence = tuple(
            Evidence(str(item["tool"]), str(item["finding"]), str(item["tool"]))
            for item in payload.get("evidence", payload.get("supportingEvidence", []))
            if item.get("tool") in called_tools and item.get("finding")
        )
        if not evidence:
            raise ValueError(
                "Model returned no evidence citations for successful tool calls"
            )
        distinct_sources = {item.tool for item in evidence}
        if len(distinct_sources) < self.minimum_evidence_sources:
            raise ValueError(
                f"Model cited {len(distinct_sources)} evidence source(s); "
                f"at least {self.minimum_evidence_sources} are required"
            )
        recommendations = tuple(
            Recommendation(
                str(item["action"]),
                str(item.get("reason", "Model recommendation")),
                bool(item.get("requiresApproval", True)),
            )
            for item in payload.get(
                "recommendedActions", payload.get("recommendations", [])
            )
            if item.get("action")
        )
        return InvestigationResult(
            incident, root_cause, confidence, evidence, recommendations, tuple(trace)
        )
