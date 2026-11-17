# Email fetcher (Gmail or Outlook)

You were told the provider. Use that provider's mail tools: Gmail (ToolSearch `gmail search threads`) or Microsoft 365 / Outlook (ToolSearch `outlook mail search` or `microsoft 365 messages`).

## Searches

**Gmail** (query syntax; D = window start as `YYYY/MM/DD`):
1. Addressed to me by a person: `to:me after:D -category:promotions -category:social -category:updates -from:me`
2. Replies on threads I started: `from:me after:<D minus 7 days>`, then for each thread check whether a non-me message came after the user's last message within the window.
3. Starred or flagged and still unanswered: `is:starred after:<D minus 14 days>`.

**Outlook / Microsoft 365** (use whichever filters the tool supports):
1. Inbox messages received ≥ window start where the user is in **To** (not only CC), excluding `Other`/clutter, newsletters, and automatic replies.
2. Conversations where the user sent the first message and someone else replied in the window.
3. Flagged messages (`flagStatus = flagged`) not marked complete.

## Filtering

Drop: newsletters, marketing, receipts, calendar notifications (the calendar fetcher covers those), CI/alerting bots, and anything matching `ignore.email_senders`. Keep CC'd mail only when the body names the user or asks them something directly.

## Per item

- `source_id`: `email:<thread or conversation id>` (one item per thread).
- `my_role`: `direct_message` | `reply_to_my_thread` | `mentioned` (CC'd but named) | `reviewer` (asked to review or approve).
- `from_email`: the latest non-me sender's address (used for VIP matching).
- `resolved`: the user sent the last message in the thread.
- `due`: only when a date is stated ("by EOD Friday" → that Friday).
- `refs`: ticket keys and Jira/Confluence/Aha!/doc links in the latest message.
- Don't include full bodies, attachments, or signatures. The snippet is enough.
