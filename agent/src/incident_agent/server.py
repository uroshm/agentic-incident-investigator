from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict

from .models import Incident
from .llm import OllamaClient
from .orchestration.model_investigator import ModelInvestigator
from .persistence import build_repository
from .tools.live import build_live_gateway


def build_investigator() -> ModelInvestigator:
    gateway = build_live_gateway(
        os.getenv("BUSINESS_SAAS_URL", "http://127.0.0.1:8080")
    )
    return ModelInvestigator(
        gateway,
        OllamaClient(
            os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434"),
            os.getenv("LLM_MODEL", "llama3.1:8b"),
        ),
    )


class AgentRequestHandler(BaseHTTPRequestHandler):
    investigator = build_investigator()
    repository = build_repository(os.getenv("DATABASE_URL"))
    active_investigations: dict[str, dict[str, Any]] = {}
    active_lock = threading.Lock()
    investigation_lock = threading.Lock()
    model_jobs: dict[str, dict[str, Any]] = {}
    model_jobs_lock = threading.Lock()

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

    @staticmethod
    def _allowed_models() -> list[str]:
        configured = os.getenv(
            "OLLAMA_ALLOWED_MODELS", "llama3.1:8b,qwen2.5:7b,mistral:7b"
        )
        return [model.strip() for model in configured.split(",") if model.strip()]

    @classmethod
    def _pull_model(cls, job_id: str, model: str) -> None:
        try:
            client = OllamaClient(
                os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434"),
                model,
                timeout_seconds=30,
            )

            def update(event: dict[str, Any]) -> None:
                with cls.model_jobs_lock:
                    cls.model_jobs[job_id].update(
                        {
                            "status": event.get("status", "downloading"),
                            "digest": event.get("digest"),
                            "completed": event.get("completed"),
                            "total": event.get("total"),
                        }
                    )

            client.pull_model(model, update)
            with cls.model_jobs_lock:
                cls.model_jobs[job_id].update(
                    {"status": "completed", "completed": 1, "total": 1}
                )
        except Exception as exc:
            logging.exception("model_pull_failed model=%s", model)
            with cls.model_jobs_lock:
                cls.model_jobs[job_id].update({"status": "failed", "error": str(exc)})

    @classmethod
    def _execute_investigation(cls, payload: Dict[str, Any]) -> dict[str, Any]:
        service = str(payload.get("service", "checkout-service"))
        description = str(payload.get("description", "Service is degraded"))
        incident = Incident(description=description, service=service)
        model_name = str(payload.get("model") or os.getenv("LLM_MODEL", "llama3.1:8b"))
        investigator = cls.investigator
        if model_name != investigator.model.model:
            investigator = ModelInvestigator(
                investigator.gateway,
                OllamaClient(
                    os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434"), model_name
                ),
                max_iterations=investigator.max_iterations,
                max_tool_attempts=investigator.max_tool_attempts,
                minimum_evidence_sources=investigator.minimum_evidence_sources,
            )
        # The gateway audit stream is shared by the singleton investigator. Serialize
        # runs so each persisted trace belongs to exactly one investigation.
        with cls.investigation_lock:
            audit_start = len(cls.investigator.gateway.audit.events)
            result = investigator.investigate(incident)
            report = result.as_dict()
            audit_events = cls.investigator.gateway.audit.events[audit_start:]
            investigation_id = cls.repository.save(incident, result, audit_events)
            report["investigationId"] = investigation_id
            report["model"] = model_name
        print(
            json.dumps({"event": "investigation_report", "report": report}), flush=True
        )
        return report

    @classmethod
    def _run_async_investigation(cls, run_id: str, payload: Dict[str, Any]) -> None:
        try:
            report = cls._execute_investigation(payload)
            with cls.active_lock:
                cls.active_investigations[run_id].update(
                    {
                        "status": "COMPLETED",
                        "completedAt": datetime.now(timezone.utc).isoformat(),
                        "result": report,
                    }
                )
        except (
            Exception
        ) as exc:  # report failures to the UI instead of losing the worker
            logging.exception("investigation_failed run_id=%s", run_id)
            with cls.active_lock:
                cls.active_investigations[run_id].update(
                    {
                        "status": "FAILED",
                        "completedAt": datetime.now(timezone.utc).isoformat(),
                        "error": str(exc),
                    }
                )

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        path = self.path.split("?", 1)[0]
        if path == "/health":
            self._send_json(
                {
                    "service": "incident-agent",
                    "status": "healthy",
                    "mode": type(self.investigator).__name__,
                }
            )
        elif path == "/investigations":
            self._send_json({"investigations": self.repository.list_reports()})
        elif path == "/investigations/live":
            with self.active_lock:
                self._send_json(
                    {"investigations": list(self.active_investigations.values())}
                )
        elif path == "/api/models":
            default_model = os.getenv("LLM_MODEL", "llama3.1:8b")
            try:
                models = OllamaClient(
                    os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434"), default_model
                ).list_models()
                self._send_json(
                    {
                        "models": models,
                        "available": self._allowed_models(),
                        "default": default_model,
                    }
                )
            except Exception as exc:
                self._send_json(
                    {
                        "models": [],
                        "available": self._allowed_models(),
                        "default": default_model,
                        "error": str(exc),
                    }
                )
        elif path.startswith("/api/models/pull/"):
            job_id = path.rsplit("/", 1)[-1]
            with self.model_jobs_lock:
                job = self.model_jobs.get(job_id)
            self._send_json(
                job or {"error": "pull_job_not_found"},
                HTTPStatus.OK if job else HTTPStatus.NOT_FOUND,
            )
        elif path.startswith("/investigations/") and path.endswith("/trace"):
            try:
                investigation_id = int(self.path.split("/")[2])
            except (IndexError, ValueError):
                self._send_json(
                    {"error": "invalid_investigation_id"}, HTTPStatus.BAD_REQUEST
                )
                return
            self._send_json(
                {
                    "investigationId": investigation_id,
                    "trace": self.repository.get_trace(investigation_id),
                }
            )
        elif path.startswith("/investigations/"):
            try:
                investigation_id = int(path.split("/")[2])
            except (IndexError, ValueError):
                self._send_json(
                    {"error": "invalid_investigation_id"}, HTTPStatus.BAD_REQUEST
                )
                return
            report = self.repository.get_report(investigation_id)
            if report is None:
                self._send_json(
                    {"error": "investigation_not_found"}, HTTPStatus.NOT_FOUND
                )
                return
            self._send_json({"investigation": report})
        else:
            self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        path = self.path.split("?", 1)[0]
        try:
            payload = self._read_json()
            if path == "/api/models/pull":
                model = str(payload.get("model", "")).strip()
                if model not in self._allowed_models():
                    raise ValueError("model is not in OLLAMA_ALLOWED_MODELS")
                default_model = os.getenv("LLM_MODEL", "llama3.1:8b")
                installed = OllamaClient(
                    os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434"), default_model
                ).list_models()
                if model in installed:
                    self._send_json(
                        {
                            "status": "completed",
                            "model": model,
                            "message": "Model is already installed",
                        }
                    )
                    return
                job_id = uuid.uuid4().hex
                with self.model_jobs_lock:
                    self.model_jobs[job_id] = {
                        "id": job_id,
                        "model": model,
                        "status": "queued",
                        "completed": 0,
                        "total": None,
                    }
                threading.Thread(
                    target=self._pull_model, args=(job_id, model), daemon=True
                ).start()
                self._send_json(self.model_jobs[job_id], HTTPStatus.ACCEPTED)
                return
        except (
            TypeError,
            ValueError,
            KeyError,
            RuntimeError,
            json.JSONDecodeError,
        ) as exc:
            self._send_json(
                {"error": "invalid_request", "detail": str(exc)}, HTTPStatus.BAD_REQUEST
            )
            return

        if path == "/investigate/async":
            run_id = uuid.uuid4().hex
            now = datetime.now(timezone.utc).isoformat()
            with self.active_lock:
                self.active_investigations[run_id] = {
                    "id": run_id,
                    "status": "RUNNING",
                    "service": str(payload.get("service", "checkout-service")),
                    "incident": str(payload.get("description", "Service is degraded")),
                    "model": str(
                        payload.get("model") or os.getenv("LLM_MODEL", "llama3.1:8b")
                    ),
                    "startedAt": now,
                }
            threading.Thread(
                target=self._run_async_investigation,
                args=(run_id, payload),
                daemon=True,
            ).start()
            self._send_json(self.active_investigations[run_id], HTTPStatus.ACCEPTED)
            return

        if path != "/investigate":
            self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            report = self._execute_investigation(payload)
            self._send_json(report, HTTPStatus.CREATED)
        except (
            TypeError,
            ValueError,
            KeyError,
            RuntimeError,
            json.JSONDecodeError,
        ) as exc:
            self._send_json(
                {"error": "invalid_request", "detail": str(exc)}, HTTPStatus.BAD_REQUEST
            )


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
