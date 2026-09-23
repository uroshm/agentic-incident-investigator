from __future__ import annotations

import json
import sys

from .models import Incident
from .orchestration.investigator import Investigator
from .tools.mock import build_mock_gateway


def main() -> int:
    description = (
        " ".join(sys.argv[1:]).strip()
        or "checkout-service is returning HTTP 500 errors"
    )
    gateway = build_mock_gateway()
    result = Investigator(gateway).investigate(
        Incident(description=description, service="checkout-service")
    )
    print(
        json.dumps(
            {"result": result.as_dict(), "audit": gateway.audit.events}, indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
