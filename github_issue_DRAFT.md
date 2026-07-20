# Draft — GitHub issue for ran-j/PS2Recomp

> Post at: https://github.com/ran-j/PS2Recomp/issues/new
> Title: **Community findings database — Way of the Samurai (SLUS-20407): 67 verified addresses, 36 recorded dead ends**
> Delete this header block before posting. Fill in <YOUR-REPO-URL>.

---

Hi — I've been doing deep verification work on **Way of the Samurai (SLUS-20407)**
using a parallel-scan methodology that treats the original PCSX2 runtime as ground
truth. I'd like to contribute the findings back in whatever form is most useful to
the project.

What I have, all as sanitized metadata (no game code, no ISO, no assets):

- **67 verified EE addresses** (player state, script VM, inventory, camera, NPC slots)
- **175 findings** — 92 confirmed-working, plus the failures
- **36 recorded dead ends** with the reason each failed (e.g. the WoS script VM uses
  C++ virtual dispatch, not a jump table; the pause-menu inventory values are not in
  EE RAM at all)
- **189 script-VM opcode → handler mappings**
- **104 shared-engine function patterns** (useful for other Acquire/Spike titles)

Repo: <YOUR-REPO-URL> (data as JSON + a debugging playbook + schema docs, CC0).

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
