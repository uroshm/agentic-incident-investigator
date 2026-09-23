# Agentic Incident Investigator

A local incident-response demo consisting of:

- a mock SaaS with a manually triggered database-pool failure
- a live investigator service that gathers evidence over HTTP
- PostgreSQL persistence initialized by Flyway
- Prometheus metrics
- Bruno requests for the REST API

## Run the repository

Requires Docker and Docker Compose.

```bash
./scripts/start.sh
```

By default, the script uses Ollama running on the host with the local
`llama3.1:8b` model. It verifies Ollama, pulls the model if needed, configures
the agent, and starts Compose.

Ollama can also run inside Docker:

```bash
./scripts/start.sh --docker-ollama
```

Services:

- SaaS: http://localhost:8080
- Investigator API: http://localhost:8090
- Frontend: http://localhost:3000
- Prometheus: http://localhost:9090
- PostgreSQL: localhost:5432

Flyway automatically applies the migrations in [infra/flyway/sql](infra/flyway/sql).

## Investigation console

Open http://localhost:3000/ to start and monitor investigations, browse persisted history, and review completed reports. The page polls active runs and displays final results when they complete.

The console is a React/Vite frontend bundled into the incident-agent image. For frontend development, run `npm install && npm run dev` from `frontend/`; Vite proxies API calls to the agent on port 8090.

Investigation monitoring endpoints:

- `POST /investigate/async` starts a background investigation and returns a run ID
- `GET /investigations/live` returns running, completed, and failed in-memory runs
- `GET /api/models` lists installed Ollama models and the approved download catalog
- `POST /api/models/pull` downloads an approved model through Ollama
- `GET /api/models/pull/{jobId}` reports model-download progress

The default downloadable models are `llama3.1:8b`, `qwen2.5:7b`, and `mistral:7b`. Override the catalog with `OLLAMA_ALLOWED_MODELS`, as a comma-separated list. Downloads go to the configured Ollama runtime and persist in its host installation or Docker volume.

## Trigger and investigate an incident

Enable the failure:

```bash
curl -X POST http://localhost:8080/admin/incidents/db-pool-exhaustion/enable
```

Trigger a real failing request:

```bash
curl -i http://localhost:8080/api/orders
```

Ask the investigator to inspect the live SaaS:

```bash
curl -X POST http://localhost:8090/investigate \
  -H 'Content-Type: application/json' \
  -d '{"service":"checkout-service","description":"HTTP 500 errors after deployment 184"}'
```

View persisted reports:

```bash
curl http://localhost:8090/investigations
```

For model-driven investigations, inspect the persisted model/tool trace with:

```bash
curl http://localhost:8090/investigations/1/trace
```

Disable the failure:

```bash
curl -X POST http://localhost:8080/admin/incidents/db-pool-exhaustion/disable
```

The incident agent always uses the local Ollama model. There is no deterministic
or rules-based production fallback. To use host Ollama directly:

```bash
ollama pull llama3.1:8b
LLM_BASE_URL=http://host.docker.internal:11434 docker compose up --build
```

The model is bounded to the registered read-only tools and its evidence must
cite successful tool calls. Automatic Prometheus alert delivery is not
implemented yet.

For a fully containerized model, start Ollama through the optional Compose
profile, pull the model into its persistent volume, then start the stack using
the `ollama` service as the model endpoint:

```bash
docker compose --profile ollama up -d ollama
docker compose --profile ollama exec ollama ollama pull llama3.1:8b
LLM_BASE_URL=http://ollama:11434 \
  docker compose --profile ollama up --build
```

## Bruno

Open the [bruno](bruno) directory as a Bruno collection and run the requests
in sequence.

## Tests

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
PYTHONPATH=agent/src python3 -m unittest discover -s agent/tests -v
```

## Formatting

Install the development tooling once:

```bash
make install-dev
```

Format the Python codebase or check it without making changes:

```bash
make format
make format-check
```

`make install-dev` also installs a pre-commit hook that runs Ruff's formatter on
staged Python files before every commit. If Ruff changes a file, stage the
change and commit again.

Stop the stack with `Ctrl-C` or:

```bash
docker compose down
```

Use `docker compose down -v` to also delete the PostgreSQL data volume.
