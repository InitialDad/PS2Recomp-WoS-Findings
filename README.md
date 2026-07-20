# PS2 Recompilation Findings — Way of the Samurai (SLUS-20407)

Verified reverse-engineering metadata and debugging methodology for PS2 static
recompilation, distilled from a long-running private port project. This repo
ships **findings, not game code** — no ISO, no extracted assets, no binary, no
translation units. Just the map, so the next person doesn't re-walk the dead ends.

## What's here

| Count | Data | File |
|------:|------|------|
| 67  | Verified EE memory addresses (player, script VM, inventory, camera, …) | [`data/addresses.json`](data/addresses.json) |
| 175 | Catalogued findings (92 `works`, 51 `investigated`, 19 `fails`, 13 `partial`) | [`data/findings.json`](data/findings.json) |
| 36  | Recorded **dead ends** — approaches proven not to work, with why | [`data/dead_ends.json`](data/dead_ends.json) |
| 104 | Cross-game engine patterns (shared-engine function hashes) | [`data/engine_patterns.json`](data/engine_patterns.json) |
| 189 | Script-VM opcode → handler mappings | [`data/opcode_handlers.json`](data/opcode_handlers.json) |
| 7   | Working mod recipes (address + format + safe-window) | [`data/mod_recipes.json`](data/mod_recipes.json) |

Game: **Way of the Samurai** (Spike / Acquire, 2003), serial `SLUS-20407`, NTSC-U.
Main data archive `VOLUME.DAT` (132 MB). Script VM uses C++ virtual dispatch, not
a jump table. Audio in `cdrom0:\SOUND\GZMVS.RBB`.

## Why this exists

Most recompilation and RE projects fail not for lack of tools but for lack of
**verification discipline** and **memory of what already failed**. Two things make
this dataset unusual:

1. **Ground-truth verification.** Every `works` finding was checked against the
   original PCSX2 runtime as ground truth (parallel memory scan / on-screen
   screenshot), never assumed from "the write stuck and it didn't crash."
2. **Dead ends are first-class.** The 36 recorded dead ends are the most valuable
   rows here — each one is hours you don't have to spend. Examples:
   - `MIPS:LE:32:R5900` is **not** a valid Ghidra processor ID — use
     `r5900:LE:32:default` (from the emotionengine-reloaded extension).
   - WoS pause-menu inventory values (yen, sword durability) are **not in EE RAM** —
     triangulated conclusively; stop searching RAM for them.
   - Boot instability came from **one systemic allocator cause**, not the many
     downstream hang sites (malloc / Deci2 / 0x8dcb00 / 0x152c78) — patching
     individual sites is a trap.

## How to use it

```bash
python - <<'PY'
import json
addrs = json.load(open("data/addresses.json", encoding="utf-8"))
dead  = json.load(open("data/dead_ends.json", encoding="utf-8"))
# BEFORE trying an approach, grep dead_ends for it:
for d in dead:
    if "texture" in (d["pattern"] + d["reason"]).lower():
        print("KNOWN DEAD END:", d["pattern"], "—", d["reason"])
PY
```

The schema is documented in [`SCHEMA.md`](SCHEMA.md). The bug taxonomy /
debugging playbook is in [`FINDINGS.md`](FINDINGS.md). To add findings for another
game, see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Scope: public vs. private

| Public (this repo) | Private (never shipped) |
|--------------------|-------------------------|
| Verified addresses + metadata | Game ISO / disc rip |
| Findings + dead ends | Raw EE memory dumps |
| Mod recipes (address + value) | Extracted assets & in-game strings (copyright) |
| Engine / opcode maps | The recompiled C++ translation units + runtime binary |
| Verification methodology | Internal build scripts with local paths |

Free-text fields in the export are scrubbed of local filesystem paths and the OS
username by [`tools/export_public.py`](tools/export_public.py).

## License

Data (`data/`, docs): [CC0 1.0](LICENSE) — public domain, use freely, attribution
appreciated but not required. This is metadata about a game, not the game.
