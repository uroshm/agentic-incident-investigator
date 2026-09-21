# Initial architecture

The first milestone separates the investigation loop from the systems it
queries:

```text
CLI / API
   |
Investigator -> ToolGateway -> explicit tool adapters -> logs, metrics, git...
                    |
                 AuditLog
```

`ToolGateway` is the security boundary. Each tool has a named contract and an
access level. Read tools can run immediately; state-changing tools require an
explicit approval flag. Unknown tools and shell commands are rejected.

`Investigator` is intentionally deterministic in this bootstrap. It exercises
the full evidence and audit path with mock data, while leaving a clear seam for
a model-backed planner and live adapters.

## Next slices

1. Add schemas for time ranges and tool arguments.
2. Add a model interface and structured tool-call validation.
3. Add a FastAPI service for investigations and approval requests.
4. Add the Spring Boot demo service and PostgreSQL-backed fixtures.
5. Add React timeline and approval UI.
