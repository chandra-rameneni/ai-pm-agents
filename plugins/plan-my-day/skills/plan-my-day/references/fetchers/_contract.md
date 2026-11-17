# Fetcher contract (shared by every fetcher)

Your only job is to **find** items that need the user and write them down accurately. Don't prioritize, summarize the day, or post anything. The orchestrator does all of that.

## What counts as "needs the user"

Include an item when, within the window, at least one of these is true:
- **assignee**: it's assigned to them (ticket, feature, review request, action item).
- **mentioned**: they're @mentioned or tagged by name or handle.
- **reply_to_my_thread**: someone else replied in a thread, page, or email thread **they started**.
- **direct_message**: a 1:1 or small-group DM, or an email addressed to them in To (not CC) from a real person.
- **invitee**: a calendar invite they haven't answered, or a meeting today where they're organizer or presenter.
- **reviewer / approver**: they're asked to review or approve something.

Leave out: bot/automated notifications with nothing to do (CI, digests, newsletters), anything sent by the user themselves with no reply after it, and channels or senders on the ignore list.

## Resolved

Set `"resolved": true` when the user already handled it: they replied after the latest message, the ticket is Done/Closed, or the invite is answered. Still include resolved items, because the orchestrator uses them to clear old items from memory.

## Read-only

Use only search, list, and read tools. Never send, react, comment, edit, transition, or RSVP.

## Output

Write one JSON file to the path you were given, then reply with one line (`slack: 14 items` or `slack: ERROR <why>`).

```json
{
  "source": "slack",
  "status": "ok",
  "error": null,
  "window_start": "2026-11-10T08:00:00-08:00",
  "items": [
    {
      "source_id": "slack:C04ABCD:1731600000.123456",
      "url": "https://acme.slack.com/archives/C04ABCD/p1731600000123456",
      "title": "Priya asks for Q3 churn numbers before Thursday's QBR",
      "from": "Priya Shah",
      "from_id": "U02PRIYA",
      "from_email": null,
      "my_role": "mentioned",
      "last_activity": "2026-11-16T15:42:00-08:00",
      "due": "2026-11-19",
      "awaiting_me": true,
      "resolved": false,
      "snippet": "@you can you drop the Q3 churn cut in here before Thu? Exec review…",
      "refs": ["PROD-412"],
      "meta": {"channel": "#product-leads"}
    }
  ]
}
```

Field rules:
- `source_id`: stable and unique within the source (the same item gets the same id tomorrow). Prefix it with the source name.
- `title`: one line of ≤ 90 characters saying **who wants what**, in your own words. Not the subject line copied word for word.
- `due`: only if a date is actually stated or set (ticket due date, "by Thursday" → resolve it to a date). Otherwise `null`. Don't invent one.
- `awaiting_me`: true if the last move in the conversation is someone else's and it asks something of the user.
- `snippet`: ≤ 200 characters of the most relevant text. No secrets, tokens, or passwords even if they appear in the text. Replace them with `[redacted]`.
- `refs`: ticket keys (`ABC-123`), Aha! reference numbers (`PROD-I-45`, `APP-12`), or URLs of the **specific** work item this conversation is about. The orchestrator merges an item into whatever it refs, so list the thing being discussed, not every key that appears in a footer or the parent epic.
- If the source fails entirely (auth, rate limit), write `"status":"error"`, an `error` message, and `"items": []`.

Cap: if more than 60 items qualify, keep the 60 with the most recent `last_activity` and add `"truncated": true`.
