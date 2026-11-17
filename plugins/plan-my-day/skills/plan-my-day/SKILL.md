---
name: plan-my-day
description: Plans the user's workday. It fans out one fetcher subagent per connected work tool (Slack, Jira, Confluence, Aha!, Gmail or Outlook, Google Calendar or Outlook Calendar) to collect everything that needs them, meaning items they are assigned, @mentioned or tagged in, or where someone replied to a thread they started. It then removes duplicates across tools, sorts the result into an Eisenhower matrix (Do / Schedule / Delegate / Eliminate), proposes focus blocks in their free calendar time, and DMs them the plan on Slack. Use this skill whenever the user says "plan my day", "what should I work on today", "triage my inbox/mentions", "what needs me", "morning plan", "Eisenhower matrix of my work", or asks to catch up across Slack/Jira/email after time away, even if they don't name the skill. Also use it when they answer a previous plan with "book my focus blocks", "book 1 and 3", or "put those blocks on my calendar".
---

# Plan My Day

You are the orchestrator. The fetchers find what needs the user. Your job is judgment: merge the fetcher results, decide what matters today, and turn it into a plan the user can act on in the first five minutes of their day.

The skill's own directory is called `<skill>` below; the helper script is `<skill>/scripts/pmd.py` (Python 3.9+, stdlib only). Run it with `python3`.

## Pick the mode first

| The user said… | Mode |
|---|---|
| "plan my day" or similar | **Live**: steps 1–8 |
| "plan my day **demo**" / "try plan-my-day with sample data" / gives a fixtures folder | **Demo**: same steps, but read items from fixtures instead of fetching, and never post or write anything (see *Demo mode*) |
| "book my focus blocks", "book 1 and 3", "yes, put those on my calendar" | **Book**: see *Booking focus blocks* |
| "set up plan my day" / no config exists yet | **Setup**: see *First-run setup*, then continue with Live |

The prompt may say it's a **scheduled run** (from `run-daily.sh`). Nobody is watching a scheduled run, so never ask questions: if something is missing, skip it and say so in the DM.

## Step 1: Config and run folder

```bash
python3 <skill>/scripts/pmd.py init
```
This prints JSON with `home` (default `~/.plan-my-day`, or `$PLAN_MY_DAY_HOME`), `config_path`, `config_exists`, a new `run_dir`, and `window_start`, which is now minus `lookback_days`. If `config_exists` is false, do *First-run setup*. Otherwise read the config. Keep `identities`, `vips`, `timezone`, and `working_hours` at hand for the later steps.

## Step 2: See which tools are connected

Connector tool names differ from person to person, so don't hardcode any. For each source enabled in `config.sources`, use ToolSearch with that source's keywords and see whether a matching tool exists:

- slack: `slack search messages`
- jira: `jira search issues jql`
- confluence: `confluence search cql`
- aha: `aha features ideas`
- email: `gmail search` or `outlook mail search` (based on `email_provider`)
- calendar: `google calendar events` or `outlook calendar events` (based on `calendar_provider`)

A source with no matching tools is **skipped**, not an error. Record it so the plan can say "Aha!: not connected". The user should see the gap and never confuse it with "nothing needs you in Aha!".

## Step 3: Fan out the fetchers in parallel

Start one subagent per available source, **all in the same message** so they run at the same time. Fetching is mechanical work, so use `config.fetcher_model` (default `sonnet`) as the subagent model to keep cost down. Give each one this prompt:

```
You are the <source> fetcher for Plan My Day.
Read and follow: <skill>/references/fetchers/<source>.md
Shared rules and output format: <skill>/references/fetchers/_contract.md
User identities: <identities JSON>     Timezone: <tz>
Window start (ISO): <window_start>     Today: <date>
Provider (email/calendar only): <google|microsoft>
Ignore list: <config.ignore for this source, if any>
Write your result to: <run_dir>/fetch/<source>.json
Reply with one line: item count, or the error.
```

Use calendar's `<source>` file `calendar.md` and email's `email.md`. If a fetcher fails or times out, carry on without it. `merge` reports any source that has no file.

Keep a running total of each subagent's `total_tokens` from its completion notice. The footer reports it (step 7).

## Step 4: Merge, remove duplicates, compare with past runs

```bash
python3 <skill>/scripts/pmd.py merge <run_dir>
```
This writes `<run_dir>/merged.json`:
- One item per real-world thing. A Jira ticket that's also in a Slack thread and an email becomes one item listing all three sources.
- Items whose every source is `resolved` (already answered or closed) are dropped.
- Each item has `status` (`new` | `carried_over`), `age_days`, `times_shown`, `last_quadrant`, and `vip` (true when the sender matched `config.vips`).
- Today's calendar is under `events`. The printed summary includes counts per source and any failed sources.

Read `merged.json` and use only it from here on. Don't go back to the raw fetch files.

## Step 5: Sort into quadrants

Read `<skill>/references/eisenhower.md` and classify every merged item. Write `<run_dir>/classified.json`:

```json
{"items": [{"id": "pmd-…", "quadrant": "do|schedule|delegate|eliminate",
            "urgent_reason": "…", "important_reason": "…", "est_minutes": 20,
            "next_action": "Reply to Priya with the Q3 numbers"}],
 "proposed_blocks": []}
```

Every item gets a quadrant. If you're unsure, write the reason in the item's reason fields. Don't drop it.

## Step 6: Propose focus blocks

```bash
python3 <skill>/scripts/pmd.py slots <run_dir>
```
This prints today's free gaps inside working hours (it subtracts busy meetings and lunch, and drops anything shorter than `min_block_minutes`). Fill `proposed_blocks` in `classified.json`:

- Put **Do** items first, in the earliest gaps. Group small ones (≤15 min each) into one "Inbox zero" block, and give big ones their own block.
- Put **Schedule** items into the later or longer gaps, at most `focus_block_minutes` per block.
- If a meeting today needs prep, put a short prep block before it when there's a gap.
- Leave at least one gap open. A day with every minute booked fails by noon.
- Number blocks from 1: `{"n":1,"start":"…","end":"…","title":"…","item_ids":["…"]}` with ISO times in the user's timezone.

These blocks are **proposals only**. Don't create calendar events in this step. The user books them (see *Booking focus blocks*).

## Step 7: Write and deliver the plan

Write the plan using the template in `<skill>/references/output.md` and save it to `<run_dir>/plan.md`. Then:

- **Live, interactive run:** show the plan in chat. If `deliver.slack_dm` is true, post it to the user's own Slack DM (`identities.slack_user_id`). They chose that as the delivery channel, so just do it. End by asking which focus blocks to book.
- **Scheduled run:** post the Slack DM only. Its last line tells them how to book blocks.
- **Demo:** do neither. The plan file is the deliverable.

Footer numbers: for an interactive run, give the summed fetcher tokens and label them "fetchers". You can't see your own token count, so don't make one up. For a scheduled run, `run-daily.sh` logs the exact total for the whole run. Leave that number out of the DM because it's logged after the run ends.

## Step 8: Save state

```bash
python3 <skill>/scripts/pmd.py save <run_dir>
```
This updates `seen.json` (new and carried-over tracking and aging) and `last_plan.json` (the proposed blocks, for booking), and appends one line to `runs.jsonl` with item counts. Skip this step in demo mode unless the demo uses its own `--home`.

## Booking focus blocks

1. `python3 <skill>/scripts/pmd.py last-plan` prints the latest proposed blocks and which are already booked.
2. Work out which blocks the user meant: all of them, "1 and 3", or "the morning ones". If it's ambiguous, ask once.
3. Check that each slot is still free by listing today's events. If a slot has filled up since the plan, say so and suggest the next free gap instead of double-booking.
4. Create each event on their calendar: title `[PMD] <block title>`, description listing the items with links, status busy, no attendees.
5. `python3 <skill>/scripts/pmd.py mark-booked <n> [<n>…] --event-id <id>…` records them so a re-run won't propose them again.

Only `[PMD]`-prefixed events are ever created or removed. Never move or decline the user's other meetings.

## First-run setup

Copy `<skill>/config.example.json` to the `config_path` from step 1, then ask the user, in one short message, for: name, timezone, working hours, email/calendar provider (google or microsoft), VIPs (name plus email or Slack ID, and why each matters), and preferred focus-block length. Find their Slack member ID and Atlassian account ID yourself with the connectors (look up the current user) instead of asking. Write the config, show it, and continue.

## Demo mode

The fixtures folder (default `<skill>/../../examples/demo-data`) holds fetcher outputs in the same format real fetchers write, plus `meta.json` with a fixed `today` and `now`.

Use a throwaway home so the demo never touches the user's real memory. If the prompt gives one, use it; otherwise use a fresh temp folder:
```bash
python3 <skill>/scripts/pmd.py --home <demo_home> init --now <meta.now>
cp <fixtures>/config.json <run_dir>/config.json        # if present
cp <fixtures>/seen.json   <demo_home>/state/seen.json  # if present: simulates earlier runs
# every other *.json except meta.json → <run_dir>/fetch/
```
Then run steps 4–6 with `--home <demo_home>` and `--now <meta.now>`, write `classified.json` and `plan.md` (step 7) into the run folder, and run step 8 with `--home <demo_home>`. If the prompt names an output folder, copy `plan.md`, `classified.json` and `merged.json` there too. Don't post to Slack or book anything, even when connectors are available.

## Why it works this way

- **Subagents per tool:** each tool's search is noisy and long. Keeping it out of your context leaves room for the part that needs judgment, and running them in parallel keeps the whole run to a few minutes.
- **Scripts for state and time maths:** merging, aging, and finding free gaps should give the same answer every day. Code does that reliably, and it saves tokens.
- **Propose, don't book:** the calendar is shared with colleagues who see it. The user approves what goes on it.
