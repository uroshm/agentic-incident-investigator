from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict
from urllib.parse import parse_qs, urlparse


SERVICE_NAME = "checkout-service"
SCENARIO_NAME = "db-pool-exhaustion"


class DatabasePoolExhaustedError(RuntimeError):
    """Real application exception raised when the simulated pool is exhausted."""


@dataclass
class SaaSState:
    started_at: float = field(default_factory=time.time)
    incident_enabled: bool = False
    requests_total: int = 0
    errors_total: int = 0
    db_connections_active: int = 4
    db_connections_max: int = 20
    long_running_queries: list[dict[str, object]] = field(default_factory=list)
    lock_waits: int = 0
    recent_logs: list[dict[str, object]] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def snapshot(self) -> Dict[str, object]:
        with self.lock:
            return {
                "service": SERVICE_NAME,
                "status": "degraded" if self.incident_enabled else "healthy",
                "incident": SCENARIO_NAME if self.incident_enabled else None,
                "requests_total": self.requests_total,
                "errors_total": self.errors_total,
                "db_connections_active": self.db_connections_active,
                "db_connections_max": self.db_connections_max,
                "http5xx_rate": round(self.errors_total / self.requests_total, 3)
                if self.requests_total
                else 0.0,
                "uptime_seconds": round(time.time() - self.started_at, 1),
            }

    def toggle_incident(self, enabled: bool) -> Dict[str, object]:
        with self.lock:
            self.incident_enabled = enabled
            self.db_connections_active = self.db_connections_max if enabled else 4
            self.long_running_queries = (
                [
                    {
                        "query": "UPDATE checkout_orders SET status = 'processing' WHERE id = 184",
                        "duration_seconds": 187,
                        "state": "active",
                        "transaction_age_seconds": 241,
                    }
                ]
                if enabled
                else []
            )
            self.lock_waits = 3 if enabled else 0
        logging.info(
            "incident_toggled incident=%s enabled=%s",
            SCENARIO_NAME,
            enabled,
            extra={
                "event": "incident_toggled",
                "incident": SCENARIO_NAME,
                "enabled": enabled,
            },
        )
        return self.snapshot()

    def simulate_request(self) -> None:
        with self.lock:
            self.requests_total += 1
            if self.incident_enabled:
                self.errors_total += 1
                self.recent_logs.append(
                    {
                        "level": "ERROR",
                        "message": "Database connection pool exhausted",
                        "error_type": "db_pool_exhaustion",
                    }
                )
                raise DatabasePoolExhaustedError("Database connection pool exhausted")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)
            ),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "message": record.getMessage(),
        }
        for key in ("event", "incident", "enabled", "error_type"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload)


class RequestHandler(BaseHTTPRequestHandler):
    state: SaaSState

    def log_message(self, format: str, *args: object) -> None:
        logging.info("http_request %s", format % args)

    def _send_json(
        self, payload: Dict[str, object], status: int = HTTPStatus.OK
    ) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        path = urlparse(self.path).path
        if path == "/health":
            snapshot = self.state.snapshot()
            self._send_json(snapshot, HTTPStatus.OK)
        elif path == "/admin/incidents":
            snapshot = self.state.snapshot()
            self._send_json(
                {
                    "incidents": [
                        {
                            "name": SCENARIO_NAME,
                            "enabled": snapshot["incident"] is not None,
                        }
                    ]
                }
            )
        elif path == "/metrics":
            self._send_metrics()
        elif path == "/diagnostics/logs":
            with self.state.lock:
                self._send_json({"logs": list(self.state.recent_logs)})
        elif path == "/diagnostics/database":
            with self.state.lock:
                self._send_json(
                    {
                        "service": SERVICE_NAME,
                        "active_connections": self.state.db_connections_active,
                        "max_connections": self.state.db_connections_max,
                        "long_running_queries": list(self.state.long_running_queries),
                        "lock_waits": self.state.lock_waits,
                    }
                )
        elif path == "/diagnostics/configuration":
            self._send_json(
                {
                    "service": SERVICE_NAME,
                    "database_pool_max": self.state.db_connections_max,
                    "transaction_timeout_seconds": 30,
                    "deployment_id": "184",
                }
            )
        elif path == "/diagnostics/kubernetes":
            self._send_json(
                {
                    "service": SERVICE_NAME,
                    "pod_status": "Running",
                    "restart_count": 0,
                    "events": [],
                }
            )
        elif path == "/diagnostics/deployments":
            self._send_json(
                {
                    "deployments": [
                        {
                            "id": "184",
                            "service": SERVICE_NAME,
                            "status": "completed",
                            "commit": "abc123",
                        }
                    ]
                }
            )
        elif path == "/diagnostics/source":
            self._send_json(
                {
                    "sha": parse_qs(urlparse(self.path).query).get("sha", ["abc123"])[
                        0
                    ],
                    "changed_files": ["src/checkout/CheckoutService.java"],
                    "summary": "Extended transaction scope",
                }
            )
        elif path == "/api/orders":
            self._handle_order()
        else:
            self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        path = urlparse(self.path).path
        prefix = "/admin/incidents/"
        if path.startswith(prefix) and path.endswith("/enable"):
            if path[len(prefix) : -len("/enable")].strip("/") != SCENARIO_NAME:
                self._send_json({"error": "unknown_incident"}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(self.state.toggle_incident(True))
        elif path.startswith(prefix) and path.endswith("/disable"):
            if path[len(prefix) : -len("/disable")].strip("/") != SCENARIO_NAME:
                self._send_json({"error": "unknown_incident"}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(self.state.toggle_incident(False))
        else:
            self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    def _handle_order(self) -> None:
        snapshot = self.state.snapshot()
        try:
            self.state.simulate_request()
        except DatabasePoolExhaustedError as exc:
            logging.exception(
                "order_request_failed",
                extra={"event": "request_failed", "error_type": "db_pool_exhaustion"},
            )
            self._send_json(
                {"error": "database_unavailable"}, HTTPStatus.INTERNAL_SERVER_ERROR
            )
            return
        self._send_json({"order_id": "order-123", "status": "accepted"})

    def _send_metrics(self) -> None:
        snapshot = self.state.snapshot()
        lines = [
            "# HELP http_requests_total Total HTTP requests handled by the mock service.",
            "# TYPE http_requests_total counter",
            f'http_requests_total{{service="{SERVICE_NAME}"}} {snapshot["requests_total"]}',
            "# HELP http_errors_total Total failed requests handled by the mock service.",
            "# TYPE http_errors_total counter",
            f'http_errors_total{{service="{SERVICE_NAME}"}} {snapshot["errors_total"]}',
            "# HELP db_connections_active Current active database connections.",
            "# TYPE db_connections_active gauge",
            f'db_connections_active{{service="{SERVICE_NAME}"}} {snapshot["db_connections_active"]}',
            "# HELP db_connections_max Configured database connection pool maximum.",
            "# TYPE db_connections_max gauge",
            f'db_connections_max{{service="{SERVICE_NAME}"}} {snapshot["db_connections_max"]}',
            "# HELP db_long_running_queries Current queries exceeding the long-running threshold.",
            "# TYPE db_long_running_queries gauge",
            f'db_long_running_queries{{service="{SERVICE_NAME}"}} {len(self.state.long_running_queries)}',
            "# HELP db_lock_waits Current database lock waits.",
            "# TYPE db_lock_waits gauge",
            f'db_lock_waits{{service="{SERVICE_NAME}"}} {self.state.lock_waits}',
            "# HELP incident_enabled Whether a simulated incident is active.",
            "# TYPE incident_enabled gauge",
            f'incident_enabled{{service="{SERVICE_NAME}",incident="{SCENARIO_NAME}"}} {1 if snapshot["incident"] else 0}',
        ]
        body = ("\n".join(lines) + "\n").encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def create_server(host: str = "127.0.0.1", port: int = 8080) -> ThreadingHTTPServer:
    state = SaaSState()
    RequestHandler.state = state
    server = ThreadingHTTPServer((host, port), RequestHandler)
    return server


def main() -> None:
    configure_logging()
    host = os.getenv("BUSINESS_SAAS_HOST", "127.0.0.1")
    port = int(os.getenv("BUSINESS_SAAS_PORT", "8080"))
    server = create_server(host, port)
    logging.info(
        "business_saas_started host=%s port=%s",
        host,
        port,
        extra={"event": "service_started"},
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("business_saas_stopping", extra={"event": "service_stopping"})
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
