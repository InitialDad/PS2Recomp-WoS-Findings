# Draft — GitHub issue for ran-j/PS2Recomp

> Post at: https://github.com/ran-j/PS2Recomp/issues/new
> Title: **Community findings database — Way of the Samurai (SLUS-20407): 67 catalogued addresses, 32 recorded dead ends, parallel-scan verification**
> Delete this header block before posting. Repo URL is filled in below.

---

Hi — I've been doing deep verification work on **Way of the Samurai (SLUS-20407)**
using a parallel-scan methodology that uses a live PCSX2 execution as a reference
implementation for guest-memory verification. I'd like to contribute the findings
back in whatever form is most useful to the project.

What I have, all as sanitized metadata (no game code, no ISO, no assets):

- **67 catalogued EE addresses**, each labeled with an evidence tier; most are
  cross-checked against a live PCSX2 dump (the port matches that reference byte-for-byte
  on the majority of known addresses)
- **176 findings** — 92 confirmed-working, plus the failures
- **32 recorded dead ends** with the reason each failed (e.g. the WoS script VM uses
  C++ virtual dispatch, not a jump table; the pause-menu inventory values are not in
  EE RAM at all)
- **189 script-VM opcode → handler mappings** (statically derived)
- **104 shared SDK/middleware fingerprints** (Sony SDK / libc++ / libmpeg, confirmed
  identical in one other title — useful for skipping re-analysis of SDK code, *not*
  an engine map)

Honest status: the toolchain builds and ~3,000 functions are machine-translated, but
the runtime still hangs in early boot (a heap-corruption bug, likely a
recompiler-correctness defect) — nothing playable yet. Sharing the verified findings
and methodology, not claiming a finished port.

Repo: https://github.com/InitialDad/PS2Recomp-WoS-Findings (data as JSON + a debugging playbook + schema docs, CC0).

My goal isn't to get this exact repo adopted — I'd rather contribute the verified data
in whatever format is most useful to PS2Recomp, and avoid creating another incompatible
metadata format if one already exists.

A couple of questions on how you'd prefer to receive this:

1. Would per-game data be more useful as **`config.toml` address bindings**
   (`handler@0xADDRESS`) plus a `PS2_REGISTER_GAME_OVERRIDE` module for the HLE
   contracts, or as a separate reference repo (like mine) that PS2Recomp links to?
2. Is there an existing schema for per-game function/address metadata I should match?
   If not, I'm happy to propose one — the JSON schema I'm using is documented and
   game-agnostic.
3. The "dead ends" list (approaches that provably don't work) has saved me a lot of
   time. Is there interest in a shared, cross-game version of that in the main repo?

Happy to adapt the format to whatever fits your pipeline. Thanks for building this.
