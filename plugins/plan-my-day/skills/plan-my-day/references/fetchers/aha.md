# Aha! fetcher

Tools: the Aha! MCP connector (ToolSearch `aha feature`, `aha idea`, `aha comment`, `aha todo`). Tool names and capabilities differ between Aha! connectors, so use whatever the connected one offers for the searches below and skip the ones it can't do.

## What to collect (updated in the window unless stated)

1. **Features / epics / requirements assigned to the user** that are not shipped: include all that are due or have a release date within 14 days, plus any updated in the window.
2. **To-dos** assigned to the user that are not complete, regardless of update date.
3. **Comments mentioning the user**, or comments on records the user created or owns that were posted by someone else in the window.
4. **Ideas** in a portal the user owns that got new votes or comments in the window. Group them into one item per idea category, not one per idea, so this doesn't flood the plan.
5. **Approvals** requested from the user (initiative or feature approvals), if the connector exposes them.

## Per item

- `source_id`: `aha:<reference_num>` (e.g. `aha:PROD-123`, `aha:PROD-I-45`, `aha:todo:<id>`).
- `refs`: the reference number itself, plus any **Jira key it's integrated with**. Aha! features are often linked to Jira issues, and that link is how the orchestrator merges them.
- `due`: the to-do due date, the feature due date, or the release date if it's closer.
- `my_role`: `assignee` | `mentioned` | `reply_to_my_thread` | `reviewer`.
- `meta`: `record_type`, `workflow_status`, `release`, `initiative`.
