from __future__ import annotations

import json
import sys

from .models import Incident
from .llm import OllamaClient
from .orchestration.model_investigator import ModelInvestigator
from .tools.live import build_live_gateway


def main() -> int:
    description = (
        " ".join(sys.argv[1:]).strip()
        or "checkout-service is returning HTTP 500 errors"
    )
    gateway = build_live_gateway("http://127.0.0.1:8080")
    result = ModelInvestigator(
        gateway,
        OllamaClient("http://127.0.0.1:11434", "llama3.1:8b"),
    ).investigate(Incident(description=description, service="checkout-service"))
    print(
        json.dumps(
            {"result": result.as_dict(), "audit": gateway.audit.events}, indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
