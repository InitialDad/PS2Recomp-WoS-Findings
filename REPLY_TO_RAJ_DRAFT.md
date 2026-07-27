# Draft reply to ran-j on ran-j/PS2Recomp#172

Context: Raj asked two questions on 2026-07-20/25 and closed the issue as
`not_planned` on 2026-07-25 without a reply from us.

  > I love this game, do you think the hang is memory corruption? Can you attach the logs
  > Or even better can you share the infos on discord.

Discord (from the upstream README): https://discord.gg/JQ8mawxUEf

NOT POSTED. Review, edit, then post to the issue and/or Discord.

---

Apologies for the slow reply, that was on me and I should have got back to you
much sooner. Thanks for taking the time to look, and for asking the right
question.

**Yes, it was memory corruption, and it's now fixed.** It turned out to be a
single systemic allocator cause rather than the many downstream hang sites it
presented as (malloc / Deci2 / `0x8dcb00` / `0x152c78`). Patching the individual
sites was a trap; each fix just moved the freeze somewhere else.

Where it stands today, measured rather than assumed:

- The runtime sustains its main loop, **+2,803 frames** in the best drive, no bad
  dispatches and no bad allocations, vblank ticking.
- The blocker is now **rendering, not memory**. The screen is a flat clear colour,
  but texture uploads do reach VRAM (a 512x512 PSMT4HH transfer, a 256x128, and
  several 8x2 CLUT loads, all host-to-local), and 96 `TEX0` writes and 96 `prim=6`
  sprite kicks occur per title screen. So the defect is downstream of upload:
  rasterisation, sampling, or the draw target.

Rather than mail you a pile of files, I've published the logs in the findings
repo so they're just there if they're ever useful to you or anyone else:
**https://github.com/InitialDad/PS2Recomp-WoS-Findings/blob/master/logs/INDEX.md**

Ten runs, oldest first, each with a note on what it shows, indexed by date. Local
paths are scrubbed and long runs of one tag are collapsed with an explicit
elision marker, so 46 MB of raw logs comes to about 1.7 MB. It includes the
reference signature of the old malloc freeze you asked about, and the current
`[p4:gs-trx]` / `[p4:gs-sprite]` / `[p4:clut]` GS traces.

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

That misread is written up in the repo as well, log included, since it's a better
lesson about instrumentation than about the GS.

Thanks again for building this, and happy to move to Discord if that's easier.
