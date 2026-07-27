# PS2 Recompilation Findings: Way of the Samurai (SLUS-20407)

Reverse-engineering findings and debugging methodology for PS2 static
recompilation, distilled from a long-running private port project. Each item is
labeled with its evidence tier so you can judge it. This repo
ships **findings, not game code**: no ISO, no extracted assets, no binary, no
translation units. Just the map, so the next person doesn't re-walk the dead ends.

## Project status (read first)

*Last verified: 2026-07-27.*

This is a **work in progress**, not a finished port. **No game is playable**, and
**no mod recipe is currently verified working.** This repo ships the *findings and
methodology*, not the game and not the port binary.

What is true today, measured rather than assumed:

- The toolchain builds. ~3,000 machine-translated C++ units; 2,820 translated
  functions covering 82.6% of the 1,198,208-byte `PT_LOAD`.
- **The early-boot hang is fixed.** The two blockers this repo previously led
  with, `heap-arena-overlap` and `deci2-tty-drain`, are both resolved. The
  runtime now reaches and sustains its main loop: **+2,803 frames** in the best
  drive, no bad dispatches, no bad allocations, vblank ticking.
- **The current blocker is rendering, not memory.** The screen is a flat clear
  colour. Texture uploads *do* reach VRAM (a 512x512 PSMT4HH transfer, a 256x128,
  and several 8x2 CLUT loads, all host-to-local), and 96 `TEX0` writes and 96
  `prim=6` sprite kicks occur. So the defect sits downstream of upload:
  rasterisation, sampling, or the draw target.
- The parallel-scan harness verifies the port against a live PCSX2 execution used
  as a reference implementation.

### Claims previously published here that were wrong

Recording these because a findings repo that only lists wins is not worth reading:

- *"The runtime hangs in early boot on a heap-corruption bug."* Withdrawn. It was
  true when first written; the underlying allocator cause was found and fixed.
- *"No texture uploads happen."* Wrong. It came from grepping logs for `TRXDIR`,
  a token that only ever appears as a `case` label and was never printed.
- *"Only 9,784 bytes of the image are untranslated code."* Withdrawn. The
  >92%-decode heuristic it rested on misclassifies: the ELF entry point, known
  code, scores only 54.7% over a 256-byte window.
- *"`0x21D808` is a gzmfs read that overwrites live code."* Wrong. That address
  decodes 0.0% as MIPS; it is data.

## What's here

| Count | Data | File |
|------:|------|------|
| 67  | Catalogued EE addresses, **17** carry in-band verification evidence (`on_screen`/`snapshot_diff`/`stated_verified`); most others are additionally cross-checked by the parallel-scan report | [`data/addresses.json`](data/addresses.json) |
| 202 | Findings (99 `works`, 68 `investigated`, 20 `fails`, 15 `partial`) | [`data/findings.json`](data/findings.json) |
| 32  | Recorded **dead ends**, approaches proven not to work, with why | [`data/dead_ends.json`](data/dead_ends.json) |
| 104 | **Shared SDK/middleware fingerprints**, Sony SDK + libc++ + libmpeg code confirmed byte-identical in one other title (`SLUS-20397`). *Not* game-engine code. | [`data/shared_sdk_fingerprints.json`](data/shared_sdk_fingerprints.json) |
| 189 | Script-VM opcode → handler mappings (statically derived, not runtime-verified) | [`data/opcode_handlers.json`](data/opcode_handlers.json) |
| 7   | Mod recipes, **none currently verified working**: 3 `needs_recheck`, 4 `contradicted` (write sticks in RAM but HUD never updates) | [`data/mod_recipes.json`](data/mod_recipes.json) |

Plus the **raw evidence** the above was drawn from:

| 10 | Port boot logs, oldest first, path-scrubbed and indexed by date, 46 MB raw published as 1.7 MB | [`logs/INDEX.md`](logs/INDEX.md) |

**Please read the logs adversarially.** The findings files say what we concluded;
the logs are what someone else can use to reach a *different* conclusion, spot a
pattern we missed, or catch us being wrong. That has already happened once, and
the log containing the misread is published deliberately, misleading part
included (see `Worked example 2` in [`FINDINGS.md`](FINDINGS.md)). If you see
something we didn't, an issue here is very welcome.

Game: **Way of the Samurai** (Spike / Acquire, 2003), serial `SLUS-20407`, NTSC-U.
Main data archive `VOLUME.DAT` (132 MB). Script VM uses C++ virtual dispatch, not
a jump table. Audio in `cdrom0:\SOUND\GZMVS.RBB`.

## Confidence legend

Every dataset is labeled so you can judge it yourself. Nothing here is asserted
beyond its evidence:

| Tier | Meaning |
|------|---------|
| `on_screen` | Confirmed by a visible in-game result. |
| `snapshot_diff` / parallel-scan `OK` | Matches a live PCSX2 reference execution byte-for-byte. |
| `stated_verified` | DB note claims verification; treat as strong-but-unaudited. |
| `catalogued` | Address/observation recorded; not independently verified in-band. |
| `static_vtable_walk` (opcodes) | Derived by static analysis; **not** confirmed at runtime. |
| `shared_sdk_or_middleware` | SDK/library code, not game-specific, near-zero discriminating power for "same engine". |

## Why this exists

Most recompilation and RE projects fail not for lack of tools but for lack of
**verification discipline** and **memory of what already failed**. Two things make
this dataset unusual:

1. **Reference-execution verification.** `works` findings were checked against a
   live PCSX2 execution used as a reference implementation (parallel memory scan /
   on-screen result), not assumed from "the write stuck and it didn't crash."
   (PCSX2 is an emulator, not literal ground truth, but it's a practical, stable
   reference for guest memory.)
2. **Dead ends are first-class.** The 32 recorded dead ends are the most valuable
   rows here; each one is hours you don't have to spend. Examples:
   - `MIPS:LE:32:R5900` is **not** a valid Ghidra processor ID, use
     `r5900:LE:32:default` (from the emotionengine-reloaded extension).
   - WoS pause-menu inventory values (yen, sword durability) are **not in EE RAM**, triangulated conclusively; stop searching RAM for them.
   - Boot instability came from **one systemic allocator cause**, not the many
     downstream hang sites (malloc / Deci2 / 0x8dcb00 / 0x152c78), patching
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
        print("KNOWN DEAD END:", d["pattern"], "::", d["reason"])
PY
```

The schema is documented in [`SCHEMA.md`](SCHEMA.md). The bug taxonomy /
debugging playbook is in [`FINDINGS.md`](FINDINGS.md). To add findings for another
game, see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Scope: public vs. private

| Public (this repo) | Private (never shipped) |
|--------------------|-------------------------|
| Port boot logs (path-scrubbed diagnostics) | Game ISO / disc rip |
| Verified addresses + metadata | Raw EE memory dumps |
| Findings + dead ends | Game dialogue / in-game text (copyright) |
| Mod recipes (address + value) | Extracted assets & in-game strings (copyright) |
| Engine / opcode maps | The recompiled C++ translation units + runtime binary |
| Verification methodology | Internal build scripts with local paths |

Free-text fields in the export are scrubbed of local filesystem paths and the OS
username by [`tools/export_public.py`](tools/export_public.py).

## License

Data (`data/`, docs): [CC0 1.0](LICENSE), public domain, use freely, attribution
appreciated but not required. This is metadata about a game, not the game.
