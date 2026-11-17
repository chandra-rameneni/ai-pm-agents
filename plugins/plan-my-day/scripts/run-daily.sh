#!/usr/bin/env bash
# Plan My Day: unattended weekday run, with exact token and cost logging.
#
# Runs Claude Code headless, posts your plan to your Slack DM (never touches your
# calendar), and appends the run's real token usage and cost to
# ~/.plan-my-day/usage.jsonl. See the cost averages with:
#   python3 <repo>/plugins/plan-my-day/skills/plan-my-day/scripts/pmd.py usage summary
#
# Environment (all optional):
#   PLAN_MY_DAY_HOME     data dir (default ~/.plan-my-day)
#   PMD_ALLOWED_TOOLS    space-separated allow rules (see README, "Scheduling")
#   PMD_MAX_BUDGET_USD   hard spend cap per run (default 5)
#   PMD_MODEL            orchestrator model, e.g. opus or sonnet (default: your Claude Code default)
#   PMD_LOCAL_PLUGIN=1   load the plugin from this repo instead of the installed copy
#   PMD_WEEKENDS=1       also run on Saturday/Sunday

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(cd "$HERE/.." && pwd)"
PMD="$PLUGIN_DIR/skills/plan-my-day/scripts/pmd.py"
DATA="${PLAN_MY_DAY_HOME:-$HOME/.plan-my-day}"
mkdir -p "$DATA/logs"

if [[ "${PMD_WEEKENDS:-0}" != "1" && "$(date +%u)" -ge 6 ]]; then
  echo "weekend, skipping"; exit 0
fi

# Read-only connector tools and the Slack DM post need to be allowed for an
# unattended run. Add your connectors' server names, e.g. mcp__claude_ai_Slack.
DEFAULT_ALLOWED="Agent ToolSearch Read Write Edit Glob Grep Bash(python3:*) Bash(cp:*) Bash(mkdir:*)"
ALLOWED="${PMD_ALLOWED_TOOLS:-$DEFAULT_ALLOWED}"

PROMPT="Use the plan-my-day skill. This is a scheduled run: nobody is watching, so don't ask questions. Plan my day and post it to my Slack DM. Do not create any calendar events."

STAMP="$(date +%Y-%m-%d-%H%M)"
OUT="$DATA/logs/$STAMP.json"
ERR="$DATA/logs/$STAMP.err"

ARGS=(-p "$PROMPT" --output-format json --permission-mode dontAsk
      --max-budget-usd "${PMD_MAX_BUDGET_USD:-5}")
# shellcheck disable=SC2206
ARGS+=(--allowedTools $ALLOWED)
[[ -n "${PMD_MODEL:-}" ]] && ARGS+=(--model "$PMD_MODEL")
[[ "${PMD_LOCAL_PLUGIN:-0}" == "1" ]] && ARGS+=(--plugin-dir "$PLUGIN_DIR")

claude "${ARGS[@]}" >"$OUT" 2>"$ERR"
STATUS=$?

if [[ -s "$OUT" ]]; then
  python3 "$PMD" usage log <"$OUT"
else
  echo "claude produced no output (exit $STATUS); see $ERR" >&2
fi
exit $STATUS
