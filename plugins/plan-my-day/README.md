# Plan My Day

**A Claude Code agent that reads everything waiting for you across Slack, Jira, Confluence, Aha!, email and calendar, then hands you an Eisenhower-matrix plan for the day, with focus blocks that fit around your meetings.**

Every morning it:

1. **Fans out six fetcher agents in parallel**, one per tool, to collect what needs *you*: things you're assigned, @mentioned or tagged in, and replies on threads you started.
2. **Removes duplicates across tools.** The Jira ticket, the Slack thread about it and the email about it become one item with three links.
3. **Remembers yesterday.** Items are marked new or carried over. Anything you've ignored for 3+ days escalates, and answered items drop off.
4. **Sorts into an Eisenhower matrix:** 🔴 Do · 🟡 Schedule · 🔵 Delegate · ⚪ Eliminate. Your VIP list always counts as important; everything else is judged with a written reason.
5. **Proposes focus blocks** in the free gaps between your meetings and DMs you the plan on Slack. Reply "book 1 and 3" and those blocks go on your calendar. Nothing is ever booked without your OK.

```
Slack ─┐
Jira ──┤                    ┌─ merge + dedupe + memory (script)
Confl ─┼─▶ 6 fetcher agents ─┤
Aha! ──┤    (in parallel)    ├─ Eisenhower sort (orchestrator)
Email ─┤                    ├─ free-slot maths (script)
Cal ───┘                    └─▶ Slack DM  +  proposed [PMD] focus blocks
```

See a full example (on fictional data) in [`examples/sample-plan.md`](examples/sample-plan.md).

---

## Install

You need [Claude Code](https://claude.com/claude-code) and Python 3.9+.

```bash
/plugin marketplace add chandra-rameneni/ai-pm-agents
```
```bash
/plugin install plan-my-day@ai-pm-agents
```

### Try it with no setup (demo data)

```
plan my day demo
```
This runs the whole pipeline on a fictional PM's Tuesday ([`examples/demo-data`](examples/demo-data)). Nothing is read from or written to your accounts.

### Connect your tools

Plan My Day uses whatever connectors you already have in Claude, and works with any subset of them. Missing tools are skipped and listed as "not connected" in the plan.

| Source | Connector | What it fetches |
|---|---|---|
| Slack | Slack | @mentions, DMs, replies to your threads |
| Jira | Atlassian (Jira) | assigned and open, @mentions in comments, activity on tickets you reported |
| Confluence | Atlassian (Confluence) | @mentions, comments on your pages, inline tasks |
| Aha! | Aha! | assigned features and to-dos, comments, initiative mentions |
| Email | Gmail **or** Microsoft 365 (Outlook) | mail to you from people, replies to your threads, flagged |
| Calendar | Google Calendar **or** Outlook | today's meetings (for free time), prep needed, unanswered invites |

Connect them in Claude (Settings → Connectors) or add any MCP server that provides them. Claude Code picks up your claude.ai connectors automatically.

### First run

```
plan my day
```
The first run asks for your timezone, working hours, mail provider (`google` or `microsoft`) and your **VIPs** (people whose asks always count as important). It writes `~/.plan-my-day/config.json`. All options are in [`config.example.json`](skills/plan-my-day/config.example.json).

---

## Daily use

| Say | What happens |
|---|---|
| `plan my day` | full run, plan in chat + Slack DM, proposed focus blocks |
| `book 1 and 3` / `book all` | creates the proposed blocks as `[PMD] …` events, after checking they're still free |
| `plan my day demo` | fictional data, no side effects |

## Scheduling (weekday 8am)

[`scripts/run-daily.sh`](scripts/run-daily.sh) runs the agent headless, posts the Slack DM and **logs exact token usage and cost** for every run.

1. Clone this repo (the script and its helper need to be on disk).
2. Allow the tools the unattended run needs. The run uses `--permission-mode dontAsk`, so anything not listed is refused. List your connector servers by name (run `/mcp` in Claude Code to see them):
   ```bash
   export PMD_ALLOWED_TOOLS="Agent ToolSearch Read Write Edit Glob Grep Bash(python3:*) Bash(cp:*) Bash(mkdir:*) mcp__claude_ai_Slack mcp__claude_ai_Atlassian mcp__claude_ai_Gmail mcp__claude_ai_Google_Calendar"
   ```
3. Schedule it:
   - **macOS:** edit and load [`examples/schedule/com.plan-my-day.daily.plist`](examples/schedule/com.plan-my-day.daily.plist).
   - **Linux / cron:** `0 8 * * 1-5 PMD_ALLOWED_TOOLS="…" /path/to/ai-pm-agents/plugins/plan-my-day/scripts/run-daily.sh`

The scheduled run **never writes to your calendar**. It only proposes blocks; you book them later by saying "book 1 and 3" in Claude.

## What does it cost?

Every scheduled run appends its real usage (all models, orchestrator plus fetchers) to `~/.plan-my-day/usage.jsonl`. See the averages with:

```bash
python3 plugins/plan-my-day/skills/plan-my-day/scripts/pmd.py usage summary --markdown
```

| Metric | Value |
|---|---|
| Avg total tokens / run | _measured after a week of runs_ |
| Avg cost / run | _measured_ |
| Avg wall-clock / run | _measured_ |
| Avg items triaged / run | _measured_ |

Cost levers: `fetcher_model` (default `sonnet`, which does the bulk of the reading), `lookback_days`, and turning off sources you don't use.

## Privacy and safety

- **Read-only fetchers.** They search and read; they never send, comment, react, transition or RSVP.
- **The only writes:** one Slack DM to *yourself*, and calendar events titled `[PMD] …` that you explicitly approve. It never moves, declines or edits your other meetings.
- **Your data stays local.** Config, memory (`seen.json`) and logs live in `~/.plan-my-day/`, outside this repo. Message snippets are capped at 200 characters, and anything that looks like a secret is redacted.
- Data from your tools is processed by Claude under your existing Anthropic account terms, the same as any Claude Code session.

## How it decides (Eisenhower rules)

- **Urgent:** due today or tomorrow · feeds a meeting today · someone is blocked on you · an unanswered invite for the next day · you've left it 3+ days · it slipped through three plans in a row.
- **Important:** from a VIP (always) · otherwise the model judges ownership, launch, customer or exec impact, and decisions only you can make, and writes down its reason.
- **Do holds at most 6 items.** On a heavy day the rest move to the top of Schedule with their urgency kept, and the plan says how many didn't fit.
- **Things only you can do** (your interview feedback, your sign-offs) never land in Delegate.
- **Delegate / Eliminate** are listed with no advice. Those calls are yours.

Full rubric: [`skills/plan-my-day/references/eisenhower.md`](skills/plan-my-day/references/eisenhower.md).

## Layout

```
plugins/plan-my-day/
├── skills/plan-my-day/
│   ├── SKILL.md                 orchestrator
│   ├── references/fetchers/     one brief per tool + shared output contract
│   ├── references/eisenhower.md classification rubric
│   ├── references/output.md     Slack DM format
│   ├── scripts/pmd.py           merge, memory, free slots, usage log (stdlib Python)
│   ├── config.example.json
│   └── evals/                   test cases (run with `claude plugin eval`)
├── scripts/run-daily.sh         headless run + cost logging
└── examples/                    demo data, sample plan, launchd schedule
```

## License

MIT
