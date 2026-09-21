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
docker compose up --build
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

Disable the failure:

```bash
curl -X POST http://localhost:8080/admin/incidents/db-pool-exhaustion/disable
```

The investigation currently uses deterministic reasoning over live health,
metrics, logs, deployment metadata, and source-change metadata. Automatic
Prometheus alert delivery and a local LLM are not implemented yet.

## Bruno

Open the [bruno](bruno) directory as a Bruno collection and run the requests
in sequence.

## Tests

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
PYTHONPATH=agent/src python3 -m unittest discover -s agent/tests -v
```

Stop the stack with `Ctrl-C` or:

```bash
docker compose down
```

Use `docker compose down -v` to also delete the PostgreSQL data volume.
