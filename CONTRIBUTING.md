# Contributing findings

This repo is a shared map. Additions welcome for **any** PS2 title, not just
Way of the Samurai.

## What belongs here
- Verified EE addresses (say how you verified).
- Findings — including things that **didn't** work. Failures are the point.
- Dead ends: an approach + why it failed + what to do instead.
- Per-game recompiler notes: HLE contracts, opcode maps, shared SDK/middleware
  fingerprints. (Label SDK/library matches honestly — they are not "engine" evidence.)

## What does NOT belong here
- Game code, ISOs, extracted assets, raw memory dumps, copyrighted in-game text.
- Anything that only makes sense with the game binary in hand.

## Evidence tiers
Tag each finding with how strongly it's verified:

| Tier | Meaning |
|------|---------|
| `works` | Confirmed against a reference execution (on-screen result or parallel scan vs. a live PCSX2 run). |
| `partial` | Works with caveats / only in some states. |
| `investigated` | Understood but not acted on. |
| `fails` | Tried, did not work — record it and, if it should never be retried, add a `dead_ends` row. |

Never delete a finding, even a wrong one — supersede it with a new row that
references it. History is the value.

## How to add
1. Append objects to the relevant `data/*.json` file, matching the schema in
   [`SCHEMA.md`](SCHEMA.md). Use hex strings for addresses. Set `serial` to the
   disc serial, or `null` for a general lesson.
2. If you maintain your own knowledge DB, `tools/export_public.py` shows the
   sanitizing export pattern (scrubs local paths + usernames). Adapt the SQL to
   your schema.
3. Open a PR. Keep one logical finding per object; keep `details` concise but
   specific (addresses, opcodes, exact error strings).
