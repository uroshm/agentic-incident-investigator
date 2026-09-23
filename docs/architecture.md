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

The running incident agent uses the local Ollama-backed planner. The mock SaaS
remains the target system for the demo, but diagnosis and recommendations come
from the model's tool-calling investigation loop rather than a deterministic
hypothesis table.

## Next slices

1. Add schemas for time ranges and tool arguments.
2. Add a model interface and structured tool-call validation.
3. Add a FastAPI service for investigations and approval requests.
4. Add the Spring Boot demo service and PostgreSQL-backed fixtures.
5. Add React timeline and approval UI.
