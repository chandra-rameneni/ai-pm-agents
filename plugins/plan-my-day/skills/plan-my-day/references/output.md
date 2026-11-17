# Plan format

The plan is read on a phone in Slack, so it has to scan in 30 seconds. Use Slack mrkdwn: `*bold*`, `<url|label>` links, `•` bullets. Don't use markdown tables or headings with `#`, because Slack doesn't render them. In chat, the same text is fine.

## Template

```
*Plan for <Weekday, Mon D>* · <N> things need you (<n_new> new, <n_carried> carried over)

*🔴 DO — today*
1. <next_action> — <from> · <source links> · ~<est> min
   _<urgent_reason>; <important_reason>_
…

*🟡 SCHEDULE — focus time*
• <next_action> — <from> · <links> · ~<est> min  _(<important_reason>)_
…

*🔵 DELEGATE — your call*
• <title> — <from> · <links>
…

*⚪ ELIMINATE? — your call*
• <title> — <from> · <links>
…

*🗓 Today*
09:30–10:00 Standup
10:00–11:30 *[proposed #1] Do: Priya churn cut + 2 quick replies*
11:30–12:00 Design review (you present) ← prep in block #1
…

*Proposed focus blocks:* #1 10:00–11:30 · #2 14:00–15:30 · #3 16:00–16:45
Reply "book 1 and 3" (or "book all") in Claude to put them on your calendar.

_Sources: Slack 14 · Jira 9 · Confluence 3 · Aha! 4 · Gmail 11 · Calendar 6 — 47 items triaged, 31 after merging duplicates. Not connected: none._
_Tokens (fetchers): 142k_
```

## Rules

- **Links:** one per source the item came from, labelled with the source name: `<url|Jira>` `<url|Slack>`. A merged item shows all its links. That's how the user sees the merge worked.
- **Order:** Do items in the order they should be tackled (blocking others → today's meeting → oldest wait). Schedule items by importance.
- Prefix carried-over items with `↩︎` and add the age when ≥ 2 days: `↩︎ (4d)`. New items get no marker, since new is the default.
- **Empty quadrant:** one line, `_nothing_`. If everything is empty, say so in one cheerful line and show the calendar anyway.
- **Not connected / failed sources:** always list them in the Sources line. Silence would read as "nothing there".
- Keep Delegate and Eliminate to titles only, with no advice. The user asked to make those calls themselves.
- Keep it under ~40 lines. If Schedule, Delegate, or Eliminate has more than 8 items, show 8 and then `…and N more (in plan.md)`.
- Times in the user's timezone, 24h or 12h following `config.time_format` (default 24h).
- In demo mode, put `_DEMO — sample data_` as the first line.
