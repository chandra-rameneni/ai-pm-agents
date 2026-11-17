# Confluence fetcher

Tools: the Atlassian / Confluence MCP's CQL search, page read, and comment read tools (ToolSearch `confluence cql`, `confluence page comments`).

## Searches (W = window start date)

1. **Mentioned**: `mention = currentUser() AND lastmodified >= "W"`. Open each hit and confirm the mention is new in the window (in a comment or body edit).
2. **Comments on my pages**: `creator = currentUser() AND lastmodified >= "W"`. For each page, read the footer and inline comments and keep the page if someone else commented in the window.
3. **Assigned tasks**: if the tool supports inline tasks, get open tasks assigned to the user (`assignee = currentUser()` on tasks) that are due within 7 days or were created in the window.

## Per item

- `source_id`: `confluence:<page_id>` (for an inline task: `confluence:task:<task_id>`).
- `my_role`: `mentioned` | `reply_to_my_thread` (comments on their page) | `assignee` (tasks) | `reviewer` (if the page or comment asks them to review or approve).
- `title`: e.g. "Legal left 3 comments on your PRD 'Usage-based billing v2'".
- `resolved`: the user replied to the latest comment, or the task is complete.
- `refs`: ticket keys and Aha! references found in the page title and in the comments you read.
- `meta`: `space`, `page_title`, `comment_count_in_window`.
