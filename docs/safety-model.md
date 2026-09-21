# Safety model

- Tools are allow-listed and explicitly registered.
- Tool permissions are enforced by the gateway, independently of model output.
- The initial investigator only calls read-only tools.
- Recommendations are data, not executed actions.
- Rollback is registered as approval-required and cannot run without an
  explicit approval flag.
- Every call produces an audit event, including denied and failed calls.
- No arbitrary shell, filesystem, or network tool is exposed to the agent.
