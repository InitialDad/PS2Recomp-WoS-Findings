# Data schema

All files are UTF-8 JSON arrays of flat objects. Addresses are hex strings
(`"0x00C18608"`). `serial` is the PS2 disc serial (`SLUS-20407`); `null` means
the row is game-agnostic (a general RE lesson).

## `addresses.json`
Verified EE (Emotion Engine) RAM addresses.

| field | type | meaning |
|-------|------|---------|
| `serial` | string | disc serial |
| `label` | string | human name, e.g. `hp_current` |
| `address` | hex string | EE RAM address |
| `fmt` | string | `float` \| `uint32` \| `uint16` \| `block` \| … |
| `category` | string | `player` \| `script_vm` \| `inventory` \| `camera` \| `npc_slot` \| … |
| `notes` | string | how verified, caveats, conflicts resolved |
| `pointer_chain` | string/null | pointer path if not static |
| `code_refs` | string/null | referencing function addresses |
| `evidence` | string | derived tier: `on_screen` \| `snapshot_diff` \| `stated_verified` \| `catalogued` (from in-band notes only; many are additionally validated by the parallel-scan report) |

## `findings.json`
Every meaningful observation, successes and failures alike.

| field | type | meaning |
|-------|------|---------|
| `serial` | string/null | disc serial |
| `topic` | string | short slug of what was examined |
| `outcome` | string | `works` \| `partial` \| `fails` \| `investigated` |
| `details` | string | full note; `works` requires ground-truth verification |

## `dead_ends.json`
Approaches proven not to work. **Read this before trying anything.**

| field | type | meaning |
|-------|------|---------|
| `serial` | string/null | disc serial (null = general) |
| `pattern` | string | the approach that failed |
| `reason` | string | why it failed / what to do instead |

## `mod_recipes.json`
Working runtime modifications.

| field | type | meaning |
|-------|------|---------|
| `serial` | string | disc serial |
| `name` | string | mod name, e.g. `infinite_hp` |
| `kind` | string | `memory` (live freeze) \| `pnach` (PCSX2 cheat) |
| `status` | string | `verified` \| `needs_recheck` |
| `payload` | JSON string | `{addr, fmt, target, safe_window}` etc. |
| `notes` | string | caveats |

`safe_window` matters: continuous writes freeze the game during kill animations
and cutscenes. Recipes use threshold-based intervention, only writing when the
value leaves a safe range.

## `shared_sdk_fingerprints.json`
Hashes of the first-N MIPS instructions of functions, matched against other
titles. **Important:** every row here is Sony SDK / C++ standard library /
libmpeg middleware — shared runtime code, **not** the game engine. A match
(all confirmed against `SLUS-20397`) proves both games linked the same SDK, which
is true of most PS2 games; it has near-zero power to identify a shared *game
engine*. The method (hash + cross-search) is a **test** for shared code, not a
claim of shared engine. `confidence` is byte-match confidence, not significance.

| field | type | meaning |
|-------|------|---------|
| `pattern_key` | string | `shared::<hash>` |
| `game_serial` | string | this game |
| `address` | hex string | address in this game |
| `signature_hex` | string | instruction-prefix hash |
| `confidence` | float | byte-match confidence (not significance) |
| `kind` | string | always `shared_sdk_or_middleware` |
| `notes` | string | which SDK/library + matching function in the other title |

## `opcode_handlers.json`
Script-VM opcode → handler-address mappings. WoS resolves handlers via C++
virtual dispatch (`lw t9, 0x20(a0)` → vtable, handler at `vt+0x8`), **not** a
contiguous jump table — the naive jump-table scan is a recorded dead end.
`evidence` is `static_vtable_walk`: **statically derived, not runtime-verified.**
