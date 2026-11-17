# Sorting items into the Eisenhower matrix

Every item gets two independent yes/no judgments, **urgent** and **important**, and those decide the quadrant:

|               | Urgent | Not urgent |
|---|---|---|
| **Important**     | **Do**: today, in the first blocks | **Schedule**: give it a focus block |
| **Not important** | **Delegate**: the user decides who or how | **Eliminate**: the user decides whether to drop it |

Judge urgent and important separately. The most common mistake is to call something important *because* it is urgent (a loud Slack ping) or urgent *because* it is important (a big strategy doc with no deadline).

## Urgent: time pressure on the user specifically

Mark it urgent when any of these is true:
- `due` is today, tomorrow, or past (count business days, so Friday → Monday is 1).
- It feeds a meeting **today**: prep, pre-read, or a question that has to be answered before the meeting.
- Someone is **blocked** on the user: phrases like "blocked", "waiting on you", "can't proceed", "need your sign-off to ship", or a ticket in a blocked status naming them.
- An unanswered invite for today or tomorrow.
- **Aging**: `awaiting_me` and `age_days` ≥ `config.aging_escalation_days` (default 3). People notice silence after a few days, so an ignored ask becomes urgent even if it never had a deadline. Say so in `urgent_reason` ("waiting 4 days").
- `times_shown` ≥ 3 and `last_quadrant` was `schedule`: it has slipped three plans in a row, so call it out.

These do not make an item urgent on their own: the message was sent recently, it contains the word "ASAP" with no actual consequence, or the channel is busy.

## Important: matters to the user's goals and relationships

1. **VIP rule (fixed):** if `vip` is true, the item is important. The user chose these people on purpose. Use the VIP's `why` from config in `important_reason` ("from Dana, your manager").
2. **Otherwise, use judgment.** Lean towards important when:
   - The user **owns** the outcome (assignee, thread starter, or owner of the feature or doc), not just an observer.
   - It moves a launch, roadmap decision, customer commitment, revenue, or exec-visible deliverable.
   - It's a decision only the user can make (approval, prioritization call, spec sign-off).
   - The cost of a bad or late answer is high: customer escalation, legal, security, an incident.

   Lean towards not important when it's an FYI, a broad-channel mention, a "thoughts?" on something the user doesn't own, a status ping answerable from a dashboard, or social chatter.

Write a short, concrete `important_reason` either way. The user will skim these, and a vague reason ("seems relevant") gives them nothing to check.

## Quadrant notes

- **Do: at most 6 items, every day.** A longer list stops being a plan: the user can't tell what to start with, and everything on it looks equally late. If more than 6 items qualify, rank them and keep the top 6:
  1. a hard deadline today (due by a time today, ships tonight, meeting prep for today)
  2. someone is blocked on the user right now
  3. a VIP ask due tomorrow
  4. aging or slipped items
  5. anything else urgent and important

  Two steps of the same thing may share one Do line (confirming Acme's P1, then prepping the Acme call). Separate tickets or asks never share a line, even when they're related (PROD-430 and PROD-431 stay two items), so every item stays visible and linkable. Move the rest to Schedule, keep their `urgent_reason`, and give them the earliest blocks after the Do items. The plan's header line says how many urgent items didn't fit in Do, so the trade-off is visible.
- **Schedule**: important work that deserves real focus time. This quadrant is where the user's leverage is, so give these items the good blocks.
- **Only the user can do it → never Delegate.** Some asks can't be handed to anyone else: their own interview scorecard or feedback, an approval or sign-off addressed to them, a review they were named on, a decision about their own team, a reply only they can give. Delegate would mean "nobody does it", so these items are always important (the user owns the outcome). Once they're urgent (due soon, someone is waiting, or aging), they qualify for **Do** (still subject to the 6-item cap); otherwise put them in **Schedule**. This rule only decides "not Delegate". It doesn't make anything more urgent, so write "only you can do this" only on items that would otherwise have looked delegable (like an interview scorecard), not as a general reason for important work the user already owns.
- **Delegate / Eliminate**: list them neutrally with their reasons. **Don't suggest who to delegate to or tell them to ignore something.** The user decides what happens to these. `next_action` for these items just restates the ask.

## `est_minutes`

Rough effort for the next action only (not the whole project): a Slack reply 5, an email 10, a review 30, a doc 60–90. Round to 5. These estimates decide which items fit into which blocks.

## `next_action`

The first concrete step, starting with a verb and naming the person: "Send Priya the Q3 churn cut", "Approve or comment on Legal's 3 PRD comments". Never "Look into this".
