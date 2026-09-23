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

Other modes:

```bash
./scripts/start.sh --docker-ollama
./scripts/start.sh --rules
```

Services:

- SaaS: http://localhost:8080
- Investigator: http://localhost:8090
- Prometheus: http://localhost:9090
- PostgreSQL: localhost:5432

Flyway automatically applies [V1__initial_schema.sql](infra/flyway/sql/V1__initial_schema.sql).

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

The default mode uses an explainable deterministic baseline. To use a local
Ollama model on macOS, start Ollama on the host, pull a model, and start
Compose with:

```bash
ollama pull llama3.1:8b
INVESTIGATION_MODE=ollama docker compose up --build
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
LLM_BASE_URL=http://ollama:11434 INVESTIGATION_MODE=ollama \
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
