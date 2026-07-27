# Draft reply to ran-j on ran-j/PS2Recomp#172

Context: Raj asked two questions on 2026-07-20/25 and closed the issue as
`not_planned` on 2026-07-25 without a reply from us.

  > I love this game, do you think the hang is memory corruption? Can you attach the logs
  > Or even better can you share the infos on discord.

Discord (from the upstream README): https://discord.gg/JQ8mawxUEf

NOT POSTED. Review, edit, then post to the issue and/or Discord.

---

Sorry for the slow reply, and thanks for looking.

**Yes, it was memory corruption, and it's now fixed.** The answer to your
question turned out to be a single systemic allocator cause rather than the many
downstream hang sites it presented as (malloc / Deci2 / `0x8dcb00` / `0x152c78`).
Patching the individual sites was a trap; each fix just moved the freeze.

Where it stands today, measured rather than assumed:

- The runtime sustains its main loop, **+2,803 frames** in the best drive, no bad
  dispatches and no bad allocations, vblank ticking.
- The blocker is now **rendering, not memory**. The screen is a flat clear colour,
  but texture uploads do reach VRAM (a 512x512 PSMT4HH transfer, a 256x128, and
  several 8x2 CLUT loads, all host-to-local), and 96 `TEX0` writes and 96 `prim=6`
  sprite kicks occur per title screen. So the defect is downstream of upload:
  rasterisation, sampling, or the draw target.

One thing from this week that may be worth more to you than our address list,
because it is about PS2Recomp's GS rather than about this game:

Way of the Samurai uploads its title texture as `PSMCT32` at `bp=0x1A40` and then
samples it as `PSMT8` from the same `tbp0`. That is not malformed, it is the
standard idiom: `256*128*4 = 131072` bytes is exactly `512*256` PSMT8 indices, so
the game is pushing an 8-bit texture through a 32-bit BITBLT for DMA throughput
and expecting the GS to unswizzle on sample. Any GS implementation has to make
the two formats address the same physical bytes for that to work.

I want to be careful here, because I nearly reported this as a confirmed
PS2Recomp bug and it would have been wrong. Our probe printed `rawIndex=0x00`
and we read that as a broken swizzle, but the probe was capped at the first 24
samples and all 24 landed at `u<=2, v<=1`, the top-left corner, where index 0 is
perfectly legitimate. That measurement cannot tell a broken swizzle from a blank
corner. Hand-walking the page math for both formats, they agree: `PSMCT32` at
`bw=4` and `PSMT8` at `bw=8` both resolve to page 212, byte `0x1A4000`. So I have
**no** evidence of a swizzle defect in PS2Recomp right now, and I am re-running
with an aggregate probe (non-zero ratio, actual UV rectangle touched, index
histogram) before I claim anything either way. I will report back with numbers.

Happy to attach the boot logs and the `[p4:gs-trx]` / `[p4:clut]` traces, or to
bring it to Discord, whichever is easier for you.

On the original questions, still open whenever you have time, and no problem if
the answer is "not a priority":

1. Would per-game data be more useful as `config.toml` address bindings plus a
   `PS2_REGISTER_GAME_OVERRIDE` module, or as a separate reference repo?
2. Is there an existing schema for per-game function/address metadata I should
   match, rather than inventing a second incompatible one?
3. Any interest in a shared cross-game "dead ends" list in the main repo?

Findings repo, updated today with the current status and the corrections above:
https://github.com/InitialDad/PS2Recomp-WoS-Findings
