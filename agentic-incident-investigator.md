# Agentic Incident Investigator

## Repository

`agentic-incident-investigator`

## Project Goal

Build a production-style AI agent that investigates software incidents by correlating application logs, metrics, deployment history, source-code changes, runbooks, Kubernetes/container events, and service health data.

The agent should gather evidence, form and test hypotheses, identify a likely root cause, and recommend remediation.

The system should be designed like something a real engineering organization could safely use, not as a toy chatbot.

> AI agents become valuable when they are embedded inside a well-designed engineering harness with scoped tools, strong observability, approval boundaries, evaluations, and auditability.

---

## Why This Project Exists

Production incident investigation often requires engineers to manually correlate information across several systems:

- deployment history
- source repositories
- logs
- metrics
- runbooks
- container orchestration
- configuration
- issue trackers

The goal is to demonstrate how an AI agent can perform that investigative loop while remaining constrained, observable, and safe.

The agent should not have unrestricted shell access. It should interact with engineering systems through explicitly defined tools.

---

## Example User Request

```text
Investigate why checkout-api is returning HTTP 500 errors after deployment #184.
```

The agent might:

1. Check current service health.
2. Find recent deployments.
3. Correlate the incident start time with a deployment.
4. Query application logs.
5. Query infrastructure/application metrics.
6. Inspect files changed in the relevant commit.
7. Search runbooks for matching failure patterns.
8. Inspect Kubernetes/container events.
9. Form a root-cause hypothesis.
10. Gather additional evidence to test that hypothesis.
11. Produce a diagnosis with supporting evidence.
12. Recommend remediation.
13. Require human approval before any write/destructive action.

Example output:

```text
Incident
--------
checkout-api returning HTTP 500 errors.

Likely Root Cause
-----------------
Database connection pool exhaustion introduced after deployment #184.

Evidence
--------
- HTTP 500 rate increased at 14:12.
- Deployment #184 completed at 14:09.
- Logs contain repeated HikariPool connection timeout errors.
- Active DB connections reached the configured maximum.
- Commit abc123 changed transaction handling in CheckoutService.

Recommended Remediation
-----------------------
1. Roll back deployment #184.
2. Investigate transaction lifetime introduced by commit abc123.
3. Add connection-pool saturation alerts.
4. Add an integration test reproducing the failure.

Confidence
----------
High
```

---

# Portfolio Objectives

## 1. Production Software Engineering

- Spring Boot
- PostgreSQL
- REST APIs
- React/TypeScript
- Docker
- cloud deployment
- CI/CD
- configuration management

## 2. Production Operations

- structured logging
- metrics
- deployment history
- Kubernetes/container diagnostics
- incident response
- rollback strategy
- runbooks
- service health checks

## 3. Agentic AI Engineering

- tool calling
- MCP or equivalent tool interfaces
- context management
- multi-step investigation
- state management
- hypothesis testing
- structured outputs
- model/provider abstraction

## 4. Safe Agent Harness Engineering

- least-privilege tools
- read-only defaults
- approval gates
- audit logging
- deterministic tool contracts
- retries/timeouts
- validation
- evaluation suites
- protection against unsafe actions

---

# High-Level Architecture

```text
                    ┌───────────────────────┐
                    │       User / UI       │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Incident Agent      │
                    │                       │
                    │ investigate           │
                    │ hypothesize           │
                    │ gather evidence       │
                    │ recommend             │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │     Tool Gateway      │
                    │                       │
                    │ auth                  │
                    │ validation            │
                    │ permissions           │
                    │ audit logging         │
                    │ approval handling     │
                    └───────────┬───────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
     Logs/Metrics          Git/Deployments        Kubernetes
          │                     │                     │
          └─────────────────────┼─────────────────────┘
                                │
                                ▼
                         Runbooks / Docs
```

---

# Suggested Demo Application

Build a small production-style SaaS environment around several services.

```text
React Frontend
      |
      v
API Gateway
      |
      +-------------------+
      |                   |
      v                   v
checkout-service     orders-service
      |                   |
      +---------+---------+
                |
                v
            PostgreSQL
```

Optional components:

- Redis
- background worker
- message queue
- mock third-party payment API
- authentication service

The application does not need to be large. Its purpose is to provide realistic operational signals for the agent to investigate.

---

# Recommended Technology Stack

## Application

Backend:
- Java 21+
- Spring Boot 3
- Spring Data JPA
- PostgreSQL
- Gradle

Frontend:
- React
- TypeScript
- Vite

Infrastructure:
- Docker Compose for local development
- Kubernetes or lightweight local Kubernetes for advanced scenarios
- optionally AWS for hosted demo

Observability:
- structured JSON logs
- Prometheus-compatible metrics
- Grafana optional
- OpenTelemetry optional

Agent:
- Python or Java
- OpenAI-compatible model interface
- tool-calling API
- optional MCP server/tool gateway

The agent implementation language is less important than the architecture.

---

# Tool Model

The agent must not receive arbitrary shell access.

Expose explicit tools instead.

## Read-Only Tools

```text
get_service_health(service)
search_logs(service, query, start_time, end_time)
query_metrics(service, metric, start_time, end_time)
get_recent_deployments(service)
get_deployment_details(deployment_id)
inspect_git_commit(commit_sha)
get_changed_files(commit_sha)
read_source_file(path, revision)
search_runbooks(query)
get_kubernetes_events(service)
get_pod_status(service)
get_configuration(service)
```

## Write Tools

These should require approval.

```text
create_github_issue(...)
create_incident_note(...)
draft_rollback_plan(...)
request_rollback(...)
restart_service(...)
rollback_deployment(...)
```

Do not allow destructive actions automatically.

---

# Permission Model

```text
search_logs              READ
query_metrics            READ
inspect_git_commit       READ
search_runbooks          READ
get_kubernetes_events    READ

create_github_issue      APPROVAL_REQUIRED
restart_service          APPROVAL_REQUIRED
rollback_deployment      APPROVAL_REQUIRED
```

The tool gateway should reject unauthorized operations independently of model behavior.

The LLM should never be the security boundary.

---

# Agent Investigation Loop

```text
Incident received
      |
      v
Collect initial evidence
      |
      v
Form hypothesis
      |
      v
Identify missing evidence
      |
      v
Call tools
      |
      v
Evaluate hypothesis
      |
      +------ insufficient evidence ------+
      |                                   |
      v                                   |
Refine hypothesis <-----------------------+
      |
      v
Produce diagnosis
      |
      v
Recommend remediation
      |
      v
Request approval for actions
```

The agent should distinguish facts, observations, hypotheses, conclusions, and recommendations.

---

# Structured Investigation Result

```json
{
  "incident": "checkout-api HTTP 500 errors",
  "rootCause": "Database connection pool exhaustion",
  "confidence": 0.91,
  "evidence": [
    {
      "source": "logs",
      "finding": "Repeated HikariPool timeout errors"
    },
    {
      "source": "metrics",
      "finding": "Active DB connections reached configured maximum"
    },
    {
      "source": "deployment",
      "finding": "Error spike began three minutes after deployment #184"
    }
  ],
  "recommendedActions": [
    "Roll back deployment #184",
    "Investigate transaction lifetime",
    "Add pool saturation alert"
  ]
}
```

---

# Safety Requirements

Required:

- read-only tools by default
- scoped credentials
- explicit schemas for every tool
- server-side parameter validation
- no arbitrary command execution
- timeouts
- rate limits
- audit logs
- approval for state-changing operations
- tool-call history
- model response logging where appropriate
- secrets never inserted directly into model prompts

Approval example:

```text
Agent recommendation:
Rollback checkout-service deployment #184.

Reason:
Deployment correlates with the incident and introduced transaction changes.

Impact:
Service will return to deployment #183.

Approval required.

[Approve]
[Reject]
```

---

# Audit Trail

Every investigation should produce an audit trail.

```text
14:21:03 investigation_started
14:21:05 get_recent_deployments checkout-api
14:21:06 deployment_184 identified
14:21:10 search_logs HikariPool
14:21:13 query_metrics db_connections
14:21:17 inspect_git_commit abc123
14:21:22 hypothesis_created db_pool_exhaustion
14:21:28 hypothesis_validated
14:21:30 diagnosis_generated
```

This should be visible in the demo UI.

---

# Incident Evaluation Suite

Create known failure scenarios with expected diagnoses.

```text
01-db-pool-exhaustion
02-invalid-jwt-secret
03-n-plus-one-query
04-downstream-api-timeout
05-invalid-environment-variable
06-failed-database-migration
07-memory-leak
08-kubernetes-crashloop
09-redis-unavailable
10-api-rate-limit
11-disk-space-exhaustion
12-expired-certificate
13-missing-secret
14-message-queue-backlog
15-thread-pool-exhaustion
16-third-party-auth-failure
17-bad-feature-flag
18-cache-stampede
19-dns-resolution-failure
20-database-lock-contention
```

Each scenario should contain:

```text
scenario metadata
expected root cause
allowed supporting evidence
forbidden/unsafe actions
expected confidence range
```

---

# Evaluation Metrics

Track:

```text
Root-cause diagnosis accuracy
Evidence quality
Evidence citation accuracy
False-positive rate
Tool-call efficiency
Mean investigation duration
Unsafe action attempts
Approval bypass attempts
Token usage
Cost per investigation
```

Example:

```text
Scenarios evaluated:          20
Correct diagnosis:            17
Diagnosis accuracy:           85%
Evidence citation accuracy:   95%
Unsafe action attempts:        0
Median investigation time:    42 sec
```

Do not fabricate metrics in the README. Only publish measured results.

---

# Example Incident Design

## DB Pool Exhaustion

Cause:

```text
A deployment introduces an unnecessarily long transaction.
```

Signals:

```text
Hikari timeout logs
increasing DB connection count
HTTP 500 increase
deployment immediately before incident
relevant transaction code change
```

Expected diagnosis:

```text
Database connection pool exhaustion caused by longer-lived transactions.
```

Expected remediation:

```text
rollback deployment
fix transaction boundary
add connection-pool alert
add regression test
```

---

# User Interface

A simple operational dashboard is enough.

```text
Incident Investigation

[ Describe the incident...                     ]

[ Investigate ]

------------------------------------------------

Incident
checkout-service HTTP 500 errors

Status
Investigation complete

Likely Root Cause
Database connection pool exhaustion

Confidence
91%

Evidence
✓ Deployment #184 occurred before error spike
✓ Hikari timeout errors detected
✓ DB connection pool reached maximum
✓ Commit abc123 modified transaction handling

Recommended Actions
1. Roll back deployment #184
2. Fix transaction boundary
3. Add saturation alert

[Create Issue]
[Draft Rollback]
[Request Rollback Approval]
```

Also show an investigation timeline with individual tool calls and findings. This makes the agent's process observable without exposing hidden chain-of-thought.

---

# MCP

MCP can be used as the tool integration layer.

Potential MCP servers:

```text
github-mcp
observability-mcp
kubernetes-mcp
deployment-mcp
runbook-mcp
```

Do not force MCP everywhere.

The architectural principle matters more:

> Agents interact with systems through structured, controlled tools.

MCP is one implementation mechanism.

---

# Harness Engineering

The model alone is not the system.

The harness consists of:

```text
model
+
context
+
tools
+
permissions
+
state
+
validation
+
retry behavior
+
evaluations
+
approval workflow
+
auditability
```

Document these design choices.

---

# Context Engineering

Avoid dumping all available information into the context window.

Retrieve information progressively:

```text
1. Incident metadata
2. Current service health
3. Recent deployment
4. Relevant logs
5. Relevant metrics
6. Changed files
7. Relevant runbook sections
```

Only fetch additional context when required by a hypothesis.

---

# Model Abstraction

Avoid coupling the project tightly to one LLM provider.

Create an interface such as:

```text
AgentModel
  investigate(...)
  summarize(...)
  selectTool(...)
```

Implement provider adapters separately.

Possible providers:

- OpenAI
- Anthropic
- local/open models later

Provider independence is useful but should not distract from the core project.

---

# Repository Structure

```text
agentic-incident-investigator/

README.md

docs/
  architecture.md
  safety-model.md
  evaluations.md
  demo.md

backend/
  src/
  build.gradle

frontend/
  src/
  package.json

agent/
  src/
    agent/
    tools/
    models/
    orchestration/
    approvals/
    audit/

mcp/
  github/
  observability/
  kubernetes/
  deployments/

scenarios/
  01-db-pool-exhaustion/
  02-invalid-jwt-secret/
  03-n-plus-one-query/
  ...

evals/
  runner/
  datasets/
  reports/

infra/
  docker/
  kubernetes/
  terraform/

scripts/
```

Adjust if a cleaner architecture emerges.

---

# Development Milestones

## Milestone 1 — Demo Application

Build a small service environment with:

- Spring Boot
- PostgreSQL
- React UI
- health endpoint
- structured logging
- metrics
- Docker Compose

Goal: have a real system that can fail in controlled ways.

## Milestone 2 — Incident Data APIs

Implement programmatic access to:

- logs
- metrics
- deployments
- source changes
- runbooks
- service health

Initially these can use local/mock implementations.

## Milestone 3 — Agent MVP

Agent can:

- accept an incident
- call read-only tools
- gather evidence
- generate a diagnosis
- recommend remediation

No write operations yet.

## Milestone 4 — Hypothesis Loop

Add explicit iterative investigation:

- generate candidate hypotheses
- identify missing evidence
- gather evidence
- reject weak hypotheses
- stop when sufficiently confident

## Milestone 5 — Approval System

Add write operations such as:

- creating an issue
- drafting a rollback
- requesting a rollback

All state-changing operations require approval.

## Milestone 6 — Incident Scenarios

Implement at least five real failure scenarios first:

1. DB pool exhaustion
2. invalid JWT configuration
3. downstream timeout
4. failed migration
5. Kubernetes crash loop

Then expand toward 20.

## Milestone 7 — Evaluation Harness

Run the agent against known incidents.

Generate a report containing:

- accuracy
- evidence quality
- tool usage
- unsafe actions
- duration
- model cost

## Milestone 8 — Portfolio UI

Create a polished demonstration experience.

A visitor should be able to understand the project in less than three minutes.

---

# README Strategy

The public README should read like a technical case study.

Suggested opening:

```text
# Agentic Incident Investigator

Production incidents require engineers to correlate deployments, logs,
metrics, source changes, configuration, and runbooks.

This project explores how an AI agent can perform that investigation
through scoped engineering tools while remaining observable, testable,
and safe.

The agent is read-only by default. State-changing operations require
human approval and every tool call is recorded in an audit trail.
```

Then include:

1. problem
2. architecture diagram
3. three-minute demo
4. example investigation
5. safety architecture
6. evaluation methodology
7. measured results
8. local setup
9. technical design docs

---

# Portfolio Demo Flow

The final demo should be approximately three minutes.

1. Show a healthy application.
2. Deploy or trigger an incident.
3. Ask the agent: `Investigate why checkout-service is failing.`
4. Show the investigation timeline.
5. Show the diagnosis.
6. Show supporting evidence.
7. Click `Request Rollback`.
8. The system stops and requests human approval.

That approval moment is important. It demonstrates that the project is designed for real systems rather than as a toy autonomous agent.

---

# ULT Labs Portfolio Positioning

Portfolio title:

```text
ULT Labs — Agentic Incident Investigator
```

Possible description:

> A production-style AI incident-response agent that investigates failures across logs, deployments, metrics, source code, Kubernetes, and engineering documentation. The system uses scoped tools, evidence-based diagnosis, automated evaluations, audit trails, and human approval for production actions.

The message should be:

> ULT Labs can build production software and modern AI systems without treating the LLM as magic.

---

# What Not to Build

Avoid spending substantial time on:

- generic chat UI
- complicated multi-agent role-playing
- autonomous production access
- an elaborate custom agent framework
- dozens of unnecessary microservices
- fancy infrastructure before the investigation loop works
- artificial MCP servers with no useful purpose

The primary deliverable is:

> A credible demonstration that an AI agent can investigate a realistic production incident safely and measurably.

---

# Stretch Goals

After the core project works:

## GitHub Integration

Inspect commits, pull requests, changed files, and deployment-associated revisions.

## Kubernetes Integration

Read events, pod status, restart counts, resource limits, and container logs.

## Observability Integration

Integrate with Grafana, Prometheus, OpenTelemetry, or a Splunk-style API.

## Issue Tracker

Create GitHub issues, Linear tickets, or Jira tickets with human approval.

## Incident Memory

Store previous incidents and remediation outcomes.

Support queries such as:

```text
Have we seen this failure before?
```

## Multiple Agents

Only after the single-agent architecture works well.

Potential specialization:

```text
Coordinator
    |
    +-- Observability Investigator
    +-- Source Code Investigator
    +-- Infrastructure Investigator
```

Compare this against the single-agent baseline using evaluations.

Do not assume multi-agent architecture is better. Measure it.

---

# First Implementation Target

Do not attempt the entire vision immediately.

Build this vertical slice first:

```text
Spring Boot checkout-service
        |
        v
PostgreSQL

Failure:
DB connection pool exhaustion

Available agent tools:
- service health
- logs
- deployment history
- DB metrics
- source diff
- runbook search

Agent output:
- diagnosis
- evidence
- confidence
- remediation

Evaluation:
Does the agent correctly identify DB pool exhaustion?
```

Once this works end-to-end, add the next incident.

---

# Definition of Done

The project is portfolio-ready when:

- a real application is running
- at least 5 incident scenarios are reproducible
- the agent investigates using structured tools
- evidence is visible
- the agent produces structured diagnoses
- destructive actions require approval
- investigations have audit trails
- an evaluation harness measures performance
- the README explains the architecture clearly
- a short demo video can show the entire workflow

A larger scenario suite can be added afterward.

---

# Guiding Principle

Do not optimize for showing that an LLM can call tools.

Optimize for showing that a senior engineer understands how to build a trustworthy system around an LLM.

That distinction is the point of the project.
