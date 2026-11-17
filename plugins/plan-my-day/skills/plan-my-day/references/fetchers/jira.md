# Jira fetcher

Tools: the Atlassian / Jira MCP's JQL search and issue read tools (ToolSearch `jira jql`, `jira issue`). If you need the user's account id and it isn't in identities, use the "current user" tool.

## JQL queries (W = window start as `"yyyy-MM-dd HH:mm"`)

1. **Assigned and open**: `assignee = currentUser() AND statusCategory != Done ORDER BY updated DESC`. Include all of them, even ones not updated in the window, but only add stale ones (no update in the window) when they are due within 7 days or overdue.
2. **Mentioned in comments**: `text ~ "<account display name>" AND updated >= "W"`. Then read the comments and keep the issue only if a comment in the window actually @mentions the user.
3. **Reported by me, with new activity**: `reporter = currentUser() AND updated >= "W" AND statusCategory != Done`. Keep it if someone else commented or changed status in the window.
4. **Waiting on me to review**: if the instance uses a reviewer or approver field, `"Reviewer" = currentUser() AND statusCategory != Done`. Skip this query quietly if the field doesn't exist.

## Per item

- `source_id`: `jira:<ISSUE-KEY>`; `url`: the browse URL.
- `refs`: the issue key itself, plus the Aha! reference if the issue is integrated with Aha!. Put epic, parent and linked keys in `meta`, **not** in `refs`, because refs merge items into one, and sibling tickets under the same epic are separate work.
- `title`: who needs what, e.g. "QA blocked on PROD-88 until you confirm the acceptance criteria".
- `due`: the `duedate` field, or the sprint end date if the issue is in an active sprint and has no due date.
- `awaiting_me`: assigned and not Done, or the latest comment is from someone else and addresses the user.
- `resolved`: status category Done, or the user commented after the latest comment from someone else (for mention-only items).
- `meta`: `priority`, `status`, `type`, `sprint`, `epic`.
