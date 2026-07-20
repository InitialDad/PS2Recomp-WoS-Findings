# PS2 Recompilation Findings — Way of the Samurai (SLUS-20407)

Reverse-engineering findings and debugging methodology for PS2 static
recompilation, distilled from a long-running private port project — each item
labeled with its evidence tier so you can judge it. This repo
ships **findings, not game code** — no ISO, no extracted assets, no binary, no
translation units. Just the map, so the next person doesn't re-walk the dead ends.

## Project status (read first)

This is a **work in progress**, not a finished port. What's true today: a full PS2
static-recompiler toolchain that builds, ~3,000 machine-translated C++ units, and a
working parallel-scan harness that verifies the port against a live PCSX2 execution
used as a reference implementation.
What's **not** done: the runtime currently hangs in early boot on a heap-corruption
bug (current leading hypothesis: a recompiler-correctness defect); **no** game is playable yet, and **no**
mod recipe is currently verified working. This repo ships the *findings and
methodology* from that work — not the game, not the port binary.

## What's here

| Count | Data | File |
|------:|------|------|
| 67  | Catalogued EE addresses — **17** carry in-band verification evidence (`on_screen`/`snapshot_diff`/`stated_verified`); most others are additionally cross-checked by the parallel-scan report | [`data/addresses.json`](data/addresses.json) |
| 176 | Findings (92 `works`, 52 `investigated`, 19 `fails`, 13 `partial`) | [`data/findings.json`](data/findings.json) |
| 32  | Recorded **dead ends** — approaches proven not to work, with why | [`data/dead_ends.json`](data/dead_ends.json) |
| 104 | **Shared SDK/middleware fingerprints** — Sony SDK + libc++ + libmpeg code confirmed byte-identical in one other title (`SLUS-20397`). *Not* game-engine code. | [`data/shared_sdk_fingerprints.json`](data/shared_sdk_fingerprints.json) |
| 189 | Script-VM opcode → handler mappings (statically derived, not runtime-verified) | [`data/opcode_handlers.json`](data/opcode_handlers.json) |
| 7   | Mod recipes — **none currently verified working**: 3 `needs_recheck`, 4 `contradicted` (write sticks in RAM but HUD never updates) | [`data/mod_recipes.json`](data/mod_recipes.json) |

Game: **Way of the Samurai** (Spike / Acquire, 2003), serial `SLUS-20407`, NTSC-U.
Main data archive `VOLUME.DAT` (132 MB). Script VM uses C++ virtual dispatch, not
a jump table. Audio in `cdrom0:\SOUND\GZMVS.RBB`.

## Confidence legend

Every dataset is labeled so you can judge it yourself — nothing here is asserted
beyond its evidence:

| Tier | Meaning |
|------|---------|
| `on_screen` | Confirmed by a visible in-game result. |
| `snapshot_diff` / parallel-scan `OK` | Matches a live PCSX2 reference execution byte-for-byte. |
| `stated_verified` | DB note claims verification; treat as strong-but-unaudited. |
| `catalogued` | Address/observation recorded; not independently verified in-band. |
| `static_vtable_walk` (opcodes) | Derived by static analysis; **not** confirmed at runtime. |
| `shared_sdk_or_middleware` | SDK/library code, not game-specific — near-zero discriminating power for "same engine". |

## Why this exists

Most recompilation and RE projects fail not for lack of tools but for lack of
**verification discipline** and **memory of what already failed**. Two things make
this dataset unusual:

1. **Reference-execution verification.** `works` findings were checked against a
   live PCSX2 execution used as a reference implementation (parallel memory scan /
   on-screen result), not assumed from "the write stuck and it didn't crash."
   (PCSX2 is an emulator, not literal ground truth — but it's a practical, stable
   reference for guest memory.)
2. **Dead ends are first-class.** The 32 recorded dead ends are the most valuable
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
