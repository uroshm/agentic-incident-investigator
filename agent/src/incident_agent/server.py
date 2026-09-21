from __future__ import annotations

import json
import logging
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict

from .models import Incident
from .orchestration.investigator import Investigator
from .persistence import build_repository
from .tools.live import build_live_gateway


class AgentRequestHandler(BaseHTTPRequestHandler):
    investigator = Investigator(build_live_gateway(os.getenv("BUSINESS_SAAS_URL", "http://127.0.0.1:8080")))
    repository = build_repository(os.getenv("DATABASE_URL"))

    def log_message(self, format: str, *args: object) -> None:
        logging.info("http_request %s", format % args)

    def _send_json(self, payload: Dict[str, Any], status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path == "/health":
            self._send_json({"service": "incident-agent", "status": "healthy"})
        elif self.path == "/investigations":
            self._send_json({"investigations": self.repository.list_reports()})
        else:
            self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path != "/investigate":
            self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self._read_json()
            service = str(payload.get("service", "checkout-service"))
            description = str(payload.get("description", "Service is degraded"))
            incident = Incident(description=description, service=service)
            audit_start = len(self.investigator.gateway.audit.events)
            result = self.investigator.investigate(incident)
            report = result.as_dict()
            audit_events = self.investigator.gateway.audit.events[audit_start:]
            self.repository.save(incident, result, audit_events)
            print(json.dumps({"event": "investigation_report", "report": report}), flush=True)
            self._send_json(report, HTTPStatus.CREATED)
        except (TypeError, ValueError, KeyError) as exc:
            self._send_json({"error": "invalid_request", "detail": str(exc)}, HTTPStatus.BAD_REQUEST)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    host = os.getenv("INCIDENT_AGENT_HOST", "0.0.0.0")
    port = int(os.getenv("INCIDENT_AGENT_PORT", "8090"))
    server = ThreadingHTTPServer((host, port), AgentRequestHandler)
    logging.info("incident_agent_started host=%s port=%s", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("incident_agent_stopping")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
