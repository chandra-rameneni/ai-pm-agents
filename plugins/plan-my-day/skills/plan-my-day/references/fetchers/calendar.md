# Calendar fetcher (Google Calendar or Outlook Calendar)

Use the provider you were told: Google Calendar (ToolSearch `google calendar list events`) or Outlook / Microsoft 365 calendar (ToolSearch `outlook calendar events`). Read the user's **primary** calendar.

Besides the usual `items`, this fetcher also writes an `events` array: today's schedule, which the orchestrator uses to find free time.

## 1. `events`: today, from 00:00 to 23:59 in the user's timezone

For every event today:
```json
{"id": "…", "title": "Q3 QBR prep", "start": "2026-11-17T10:00:00-08:00", "end": "2026-11-17T10:30:00-08:00",
 "busy": true, "my_response": "accepted|tentative|needsAction|declined", "organizer_is_me": false,
 "attendee_count": 6, "url": "…", "needs_prep": true, "is_pmd_block": false}
```
- `busy`: false for events marked free/transparent, events the user declined, and all-day events that don't block time (OOO and holidays *do* block, so set busy to true).
- `needs_prep`: true when the user organizes or presents, the description has an agenda or doc link addressed to them, or the title says review/QBR/demo/interview/1:1 with a VIP.
- `is_pmd_block`: the title starts with `[PMD]` (a focus block booked from an earlier plan).

## 2. `items`: things on the calendar that need the user

- **Unanswered invites** (`needsAction`) for any date within the next 7 days → `my_role: invitee`, `due`: the event date.
- **Today's meetings that need prep** → one item each, `my_role: invitee`, `due`: today, title like "Prep for 2pm design review (you present)".
- **Changed or cancelled** meetings today, since the window start, that the user organizes → one item so they can follow up.
- `source_id`: `calendar:<event id>`; `refs`: doc, ticket, or Confluence links in the description.
- `resolved`: the invite has been answered (for invite items).

Don't include routine recurring meetings that need nothing (standups, 1:1s without an agenda) as items. They belong only in `events`.
