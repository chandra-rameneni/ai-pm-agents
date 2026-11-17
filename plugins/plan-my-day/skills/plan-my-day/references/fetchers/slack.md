# Slack fetcher

Tools: whatever the connected Slack MCP offers for searching messages, reading threads, and looking up users. Find them with ToolSearch (`slack search`, `slack thread`, `slack user`).

## Searches (all limited to the window: `after:<window_start date - 1 day>`)

1. **Mentions**: search `<@SLACK_USER_ID>`, and also the user's display name if mentions in that workspace are plain text.
2. **DMs to the user**: search `to:me` or list DM conversations with activity in the window, skipping bots.
3. **Replies to threads they started**: search `from:<@SLACK_USER_ID>` for top-level messages in the window and also the 7 days before it (threads revive). For each one with `reply_count > 0`, read the thread and keep it if anyone other than the user posted after the user's last reply.
4. **User-group mentions**: if the user is in user groups such as `@pm-team`, include messages mentioning those groups only when the message clearly asks that group for something.

## Per item

- `source_id`: `slack:<channel_id>:<thread_ts or ts>`. Use the **thread** ts so replies to one thread become a single item.
- `my_role`: `mentioned` | `direct_message` | `reply_to_my_thread`.
- `resolved`: the user posted in that thread or DM after the latest message from someone else.
- `refs`: scan the thread text for ticket keys and Jira/Confluence/Aha!/Google Docs URLs.
- `meta.channel`: the channel name; `meta.reply_count`.

Skip messages from bots and app integrations unless a human @mentioned the user in them.
