# PS2 Recomp / RE Debugging Playbook

A taxonomy of the bug classes and false trails encountered porting Way of the
Samurai (SLUS-20407). Each row is backed by real entries in
[`data/findings.json`](data/findings.json) and [`data/dead_ends.json`](data/dead_ends.json).
The goal is to let you recognize a bug class fast and skip the trap next to it.

## 1. Recompiler-correctness bugs

> **Status honesty:** these are *diagnosed* bug classes with *proposed* fix patterns.
> The WoS runtime still hangs in early boot as of this writing; the fixes below are
> the methodology and the current best hypotheses, not a solved boot. Treat the "fix
> pattern" column as "where to intervene," not "confirmed working."

| Bug class | Symptom | Detection | Fix pattern |
|-----------|---------|-----------|-------------|
| **Resume mis-entry** | Boot fails at a *different* address each run (malloc / Deci2 / 0x8dcb00 / 0x152c78) | Stuck PC + constant return-address + shrinking SP = a function pointer landing mid-prologue of a merged function | Prune dispatch/resume entries to the legitimate few; add a bounded recovery guard. **Do not** patch the individual downstream hang sites, they are downstream of one systemic cause. |
| **Free-list corruption** | Title-load spins forever inside the game's allocator on a corrupt free-list | Instrument allocator entry; watch fd/bk pointers go null / out-of-arena | Instrument/guard `fd` writes during allocator ops, this *detects* the corruption; it may not *fix* the upstream cause. The crash site is never the bug site. |
| **Merged-function inner entry** | Return to address 0 after a call | Trace call target vs. function boundaries from the linker map | Add the missing case + label for the inner address. |

## 2. HLE synchronization bugs

| Bug class | Symptom | Detection | Fix pattern |
|-----------|---------|-----------|-------------|
| **Completion-flag livelock** | Save-create hangs; menu spins | Game's manager polls a status flag your HLE never sets | Mirror the exact completion flag the game polls. (WoS: the routine at the "save" address is `sceMcMkdir`, not `sceMcFormat` as docs imply.) |
| **Poll-rate race** | Live daemon "wins" only ~35% of the time | Daemon polling > 1 Hz just interferes | Threshold-based intervention, ≤ 1 Hz; write only when the value leaves a safe window. |

## 3. Address-hunting false trails (the expensive ones)

| False trail | Reality | Lesson |
|-------------|---------|--------|
| Search EE RAM for HUD/pause-menu values (yen, sword durability) | **Not in EE RAM at all**, triangulated 5+ times, conclusive | RAM write-persistence ≠ HUD display binding. The field you can freeze is not always the field the HUD reads. |
| Snapshot-diff for player position / Y-velocity | Diff captured bone/skin/camera animation instead | Pausing mid-motion captures *every* changing field. Also: if the emulator is ignoring input (wrong pad bindings), the diff is pure background animation. |
| Treat `0x00C291F4` as yen | Yen is at `0x00C18A20`; `0x00C291F4` is a UI scratch cache | Resolve address conflicts by cross-checking value semantics, not first hit. |
| Assume pause menu reads a separate save struct | Pause menu reads **live** HP directly | "No update" symptom had a different cause. |

## 4. Tooling / environment traps

| Trap | Reality |
|------|---------|
| Ghidra processor `MIPS:LE:32:R5900` | Does not exist. Use `r5900:LE:32:default` (emotionengine-reloaded extension). Confirmed empirically, throws `InvalidInputException`. |
| Ghidra extension in user `~/.ghidra/.../Extensions/` for headless | `analyzeHeadless` doesn't load it reliably; symlink/place into the install-side dir. |
| Python `.py` postScripts in Ghidra 12.1.x headless | Bundled Jython removed; needs PyGhidra. |
| Loose-file texture mod on disk | PCSX2 reads from inside the mounted ISO; loose files do nothing, repack ISO or hook at runtime. |
| Save-state to test a texture/replacement | Save states cache GPU state and bypass disk replacements. |
| `DumpReplaceableTextures` during gameplay | Kill animations spawn 5-10 sprites; PCSX2 stalls writing them to disk → freeze. |
| Inject input via ViGEm/keyboard while a real controller holds XInput slot 0 | Backend hardcodes gamepad 0; synthetic input is ignored. Merge input sources / patch the pad backend. |

## 5. Asset / format reverse engineering

| Attempt | Result |
|---------|--------|
| Standard codecs (zlib/gzip/lz4/lzss/lz77) on `VOLUME.DAT type_0x14` | 43 blocks / 11.9 MB, **zero** decompressed. Likely Acquire-proprietary or encoded, not compressed. |
| Classify VOLUME.DAT blocks as VAGp/RIFF/SShd audio | Zero matches. Audio actually lives in `cdrom0:\SOUND\GZMVS.RBB`. |
| Trust a prior block-type taxonomy as ground truth | Many labels wrong (1F=microcode, 21=collision). Re-classify by sampling body content, not inherited labels. |
| Guess a texture by visual pattern-match | Almost always hits an effect/light sprite, not the asset you wanted. |
| Swap MDSP model pointer without the matching KMD+MTL+TEX bundle | Skeleton mismatch → T-pose. Slot size mismatch corrupts the archive index for every later character. |

## Worked example: the boot hang (SOLVED 2026-07-2x, kept for the method)

> **Outcome, added 2026-07-27:** this one is **fixed**. The runtime now sustains
> its main loop for **+2,803 frames** with no bad dispatches and no bad
> allocations. The write-up below is kept unchanged because the *method* is the
> transferable part, and because a playbook that quietly deletes its
> in-progress entries once they resolve teaches nothing about how the diagnosis
> actually went. See the next section for what the port is stuck on now.

Concrete, so the method above isn't abstract.

**Symptom.** The recompiled runtime executes thousands of ticks, then the EE main
thread freezes with a stable `pc=0x1d1050`, `ra=0x1d0c54`, `sp=0x1ff7c90` for 700+
ticks. DMA/GIF counters stop advancing. Looks like an I/O wait.

**Wrong first hypothesis** (recorded as a dead end): "the runtime fails to set some
GS/DMAC/INTC register the loop polls." False. The loop polls no fixed address.

**What the evidence shows.** `0x1d1050` is inside `FUN_001d0c10`, the game's dlmalloc
`malloc` core, specifically the smallbin best-fit scan:

```
0x1d104c  lw   $v0, 0x4($s0)      ; v0 = chunk->head (size+flags)
0x1d1050  and  $a2, $v0, $t4      ; <-- frozen PC (t4 = ~3 mask)
0x1d108c  lw   $s0, 0xC($s0)      ; s0 = s0->fd  (follow forward link)
0x1d1090  bnel $s0, $a1, 0x1d1050 ; loop until s0 == bin sentinel
```

The walk exits only when `$s0` reaches the bin sentinel `$a1`. From the RAM dump:
`u32(0x0000000C) == 0`, so the moment a chunk's `fd` link is corrupted to NULL,
`[$s0+0xC] = [0xC] = 0` → `$s0` stays 0 forever → infinite loop. The `malloc_state`
smallmap word (`0xe0020003`, claims bins {0,1,17,29,30,31} populated) is **desynced**
from the actual bins (only bin 6 populated), corrupt allocator metadata.

**Where the corruption likely originates.** Not the runtime's I/O emulation. The free
chunk's `fd` link was already corrupted before this `malloc` call. Leading suspect: a **recompilation-
correctness bug** in the allocator's 64-bit pointer stores (`free`/`unlink` do
`dsll32`/`dsrl32` juggling; one wrong width truncates a link). This is why "translated"
is not "correct": the translation runs and mostly works, and a single mis-widened store
1,000 functions away corrupts a heap link that hangs a scan much later.

**Method that found it, and that you can copy:**
1. Parallel-scan the port against a live PCSX2 dump → confirms *which* guest state is
   already correct (rules out most of memory).
2. Static-trace the frozen PC to a named function, identify the loop's exit condition.
3. Read the actual allocator metadata from the dump; prove the free-list is corrupt
   (smallmap↔bins desync) rather than the loop being a legitimate wait.
4. Fix at the function boundary (hook the allocator) *or* add a bounds guard as a
   diagnostic, but the guard **masks** the upstream corruption; note that honestly.

Status: diagnosed, fix proposed, **not yet confirmed working.** That's the true state.

## Worked example 2: the black screen, and a probe that could not answer its own question

*Added 2026-07-27. This is where the port is stuck now, and it is a better lesson
about instrumentation than about the GS.*

**Symptom.** The main loop runs, vblank ticks, 96 `TEX0` writes and 96 `prim=6`
(sprite) kicks occur per title screen, texture uploads reach VRAM, and the screen
is still a flat clear colour.

**The upload is a legitimate PS2 idiom, not a bug.** The game uploads the title
texture as `PSMCT32` (32-bit) at `bp=0x1A40` and then reads it as `PSMT8` (8-bit
CLUT) from the same `tbp0`. That looks wrong and isn't: `256*128*4 = 131072` bytes
is exactly `512*256` `PSMT8` indices. Uploading an 8-bit texture through a 32-bit
BITBLT for DMA throughput and letting the GS unswizzle on sample is standard.
**If you are writing a GS, you must make the two formats address the same physical
bytes**; you cannot treat the upload as malformed.

**The instrumentation trap.** A probe was added to answer "are we reading the
texture data at all?", and it printed:

```
[p4:clut] #1 psm=0x13 tbp0=0x1A40 tbw=8 (u=0 v=0) rawIndex=0x00 -> ... = 0x80000000
```

...with `rawIndex=0x00` on all 24 lines. That was written up as proof of a broken
`PSMT8`/`PSMCT32` swizzle. **It is not proof of anything.** The probe was

```c
static std::atomic<uint32_t> s_ci{0};
const uint32_t n = ++s_ci;
if (n <= 24) { /* print */ }
```

The first 24 samples of the run all landed at `u<=2, v<=1`, the extreme top-left
corner of the texture. **An empty image corner reads index 0 legitimately.** The
measurement is equally consistent with "the swizzle is broken" and "the corner of
the picture is blank", so it cannot distinguish them, and the conclusion drawn
from it was unsupported. Hand-walking the page math for both formats agrees:
`PSMCT32` at `bw=4` and `PSMT8` at `bw=8` both resolve to page 212, byte
`0x1A4000` - the addressing matches exactly where the claim said it diverged.

**The fix is to the probe, not (yet) to the swizzle.** Replace "first N samples"
with an aggregate over every sample: how many indices were non-zero, the actual
UV rectangle touched, and a histogram of index values. Non-zero indices anywhere
prove the data is reachable and exonerate the swizzle; all-zero across a wide UV
span is the real evidence the original claim needed.

**Transferable rule.** *A capped "first N" log is a sampling design, and an
unstated one.* If the first N events are correlated - and in a rasterizer they
always are, because you get the first N texels of the first primitive - then N
identical values is what you would see whether or not the bug exists. Before
believing a probe, ask what its output would look like if the hypothesis were
**false**. If the answer is "the same", the probe is not evidence.

## The one rule behind all of it

**Verify against a reference execution. Record every dead end.** A write that sticks
in RAM is not proof. A boot that doesn't crash is not proof. Only externally verified
behavior, an on-screen result, or a parallel scan matching a live PCSX2 run, is
proof. Everything else is a hypothesis, and every disproven hypothesis belongs in
`dead_ends.json` so nobody has to rediscover it.
