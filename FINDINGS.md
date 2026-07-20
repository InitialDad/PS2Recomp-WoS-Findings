# PS2 Recomp / RE Debugging Playbook

A taxonomy of the bug classes and false trails encountered porting Way of the
Samurai (SLUS-20407). Each row is backed by real entries in
[`data/findings.json`](data/findings.json) and [`data/dead_ends.json`](data/dead_ends.json).
The goal is to let you recognize a bug class fast and skip the trap next to it.

## 1. Recompiler-correctness bugs

> **Status honesty:** these are *diagnosed* bug classes with *proposed* fix patterns.
> The WoS runtime still hangs in early boot as of this writing — the fixes below are
> the methodology and the current best hypotheses, not a solved boot. Treat the "fix
> pattern" column as "where to intervene," not "confirmed working."

| Bug class | Symptom | Detection | Fix pattern |
|-----------|---------|-----------|-------------|
| **Resume mis-entry** | Boot fails at a *different* address each run (malloc / Deci2 / 0x8dcb00 / 0x152c78) | Stuck PC + constant return-address + shrinking SP = a function pointer landing mid-prologue of a merged function | Prune dispatch/resume entries to the legitimate few; add a bounded recovery guard. **Do not** patch the individual downstream hang sites — they are downstream of one systemic cause. |
| **Free-list corruption** | Title-load spins forever inside the game's allocator on a corrupt free-list | Instrument allocator entry; watch fd/bk pointers go null / out-of-arena | Add fd-corruption guards at the alloc/free sites; a corrupt earlier iteration can poison the list. The crash site is never the bug site. |
| **Merged-function inner entry** | Return to address 0 after a call | Trace call target vs. function boundaries from the linker map | Add the missing case + label for the inner address. |

## 2. HLE synchronization bugs

| Bug class | Symptom | Detection | Fix pattern |
|-----------|---------|-----------|-------------|
| **Completion-flag livelock** | Save-create hangs; menu spins | Game's manager polls a status flag your HLE never sets | Mirror the exact completion flag the game polls. (WoS: the routine at the "save" address is `sceMcMkdir`, not `sceMcFormat` as docs imply.) |
| **Poll-rate race** | Live daemon "wins" only ~35% of the time | Daemon polling > 1 Hz just interferes | Threshold-based intervention, ≤ 1 Hz; write only when the value leaves a safe window. |

## 3. Address-hunting false trails (the expensive ones)

| False trail | Reality | Lesson |
|-------------|---------|--------|
| Search EE RAM for HUD/pause-menu values (yen, sword durability) | **Not in EE RAM at all** — triangulated 5+ times, conclusive | RAM write-persistence ≠ HUD display binding. The field you can freeze is not always the field the HUD reads. |
| Snapshot-diff for player position / Y-velocity | Diff captured bone/skin/camera animation instead | Pausing mid-motion captures *every* changing field. Also: if the emulator is ignoring input (wrong pad bindings), the diff is pure background animation. |
| Treat `0x00C291F4` as yen | Yen is at `0x00C18A20`; `0x00C291F4` is a UI scratch cache | Resolve address conflicts by cross-checking value semantics, not first hit. |
| Assume pause menu reads a separate save struct | Pause menu reads **live** HP directly | "No update" symptom had a different cause. |

## 4. Tooling / environment traps

| Trap | Reality |
|------|---------|
| Ghidra processor `MIPS:LE:32:R5900` | Does not exist. Use `r5900:LE:32:default` (emotionengine-reloaded extension). Confirmed empirically — throws `InvalidInputException`. |
| Ghidra extension in user `~/.ghidra/.../Extensions/` for headless | `analyzeHeadless` doesn't load it reliably; symlink/place into the install-side dir. |
| Python `.py` postScripts in Ghidra 12.1.x headless | Bundled Jython removed; needs PyGhidra. |
| Loose-file texture mod on disk | PCSX2 reads from inside the mounted ISO; loose files do nothing — repack ISO or hook at runtime. |
| Save-state to test a texture/replacement | Save states cache GPU state and bypass disk replacements. |
| `DumpReplaceableTextures` during gameplay | Kill animations spawn 5–10 sprites; PCSX2 stalls writing them to disk → freeze. |
| Inject input via ViGEm/keyboard while a real controller holds XInput slot 0 | Backend hardcodes gamepad 0; synthetic input is ignored. Merge input sources / patch the pad backend. |

## 5. Asset / format reverse engineering

| Attempt | Result |
|---------|--------|
| Standard codecs (zlib/gzip/lz4/lzss/lz77) on `VOLUME.DAT type_0x14` | 43 blocks / 11.9 MB — **zero** decompressed. Likely Acquire-proprietary or encoded, not compressed. |
| Classify VOLUME.DAT blocks as VAGp/RIFF/SShd audio | Zero matches. Audio actually lives in `cdrom0:\SOUND\GZMVS.RBB`. |
| Trust a prior block-type taxonomy as ground truth | Many labels wrong (1F=microcode, 21=collision). Re-classify by sampling body content, not inherited labels. |
| Guess a texture by visual pattern-match | Almost always hits an effect/light sprite, not the asset you wanted. |
| Swap MDSP model pointer without the matching KMD+MTL+TEX bundle | Skeleton mismatch → T-pose. Slot size mismatch corrupts the archive index for every later character. |

## The one rule behind all of it

**Verify against ground truth, and record what failed.** A write that sticks in
RAM is not proof. A boot that doesn't crash is not proof. On-screen result or a
parallel scan against the original runtime is proof — everything else is a
hypothesis, and every dead hypothesis goes in `dead_ends.json` so it dies once.
