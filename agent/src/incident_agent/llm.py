from __future__ import annotations

import json
from typing import Any, Callable
from urllib.request import Request, urlopen

from .tools.gateway import ToolGateway


class OllamaClient:
    """Small local Ollama client using its native chat/tool-call API."""

    def __init__(self, base_url: str, model: str, timeout_seconds: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def chat(
        self,
        messages: list[dict[str, Any]],
        gateway: ToolGateway,
        include_tools: bool = True,
    ) -> dict[str, Any]:
        tools = (
            [
                {
                    "type": "function",
                    "function": {
                        "name": spec.name,
                        "description": spec.description,
                        "parameters": spec.input_schema
                        or {"type": "object", "properties": {}},
                    },
                }
                for spec in gateway.tools
            ]
            if include_tools
            else []
        )
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "stream": False,
        }
        if not include_tools:
            payload["format"] = "json"
        request = Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def list_models(self) -> list[str]:
        """Return models currently installed in this Ollama instance."""
        request = Request(f"{self.base_url}/api/tags", method="GET")
        with urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return [
            str(item["name"]) for item in payload.get("models", []) if item.get("name")
        ]

    def pull_model(
        self, model: str, on_update: Callable[[dict[str, Any]], None]
    ) -> None:
        """Pull a model from Ollama and report each native progress event."""
        request = Request(
            f"{self.base_url}/api/pull",
            data=json.dumps({"name": model, "stream": True}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=None) as response:
            for line in response:
                if line.strip():
                    on_update(json.loads(line.decode("utf-8")))
