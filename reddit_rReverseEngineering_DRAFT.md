# Draft — r/ReverseEngineering post

> Delete this header before posting. Flair: "Reverse Engineering" / project share.
> Keep it technical; the hook is the surprising diagnosis, not "I made a repo."

---

**Title:** Static-recompiling a PS2 game: the boot hung at a different address every run — all one systemic bug. Findings + methodology (CC0)

---

I've been static-recompiling *Way of the Samurai* (PS2, SLUS-20407) to native — MIPS
R5900 → C++, the ran-j/PS2Recomp approach. The toolchain builds and ~3,000 functions
are machine-translated, but it's **not playable** — it hangs in early boot. I'm sharing
the findings and the verification method, not a finished port, because the *method* is
the part other people keep asking for.

**The bug that taught me the most:** boot failed at a *different* guest address every
run — `malloc`, `Deci2`, `0x8dcb00`, `0x152c78`. The tempting move is to patch each hang
site. That's a trap: they're all downstream of **one** systemic cause. The frozen PC
eventually resolved to the game's dlmalloc smallbin scan, spinning because a free
chunk's `fd` link had been corrupted to NULL (`u32(0xC)==0` makes NULL a permanent fixed
point), and the allocator smallmap was desynced from the actual bins. Root suspect: a
recompilation-correctness bug in a 64-bit pointer store (`dsll32`/`dsrl32` width) in
`free`/`unlink`, corrupting a heap link that only bites a scan much later. "Translated"
is not "correct."

**How I know which memory is right:** a parallel-scan harness that dumps the port's
guest RAM and diffs it page-by-page and address-by-address against a live PCSX2 dump as
ground truth. On the last run, the majority of ~70 known addresses matched byte-for-byte;
that's what lets me *rule out* most of memory and localize a bug instead of guessing.

I catalogued the whole thing, including the failures:
- 67 EE addresses, each tagged with an evidence tier (on-screen / snapshot-diff / catalogued)
- 176 findings, **32 recorded dead ends with the reason each failed**
- 189 script-VM opcode→handler mappings (the VM uses C++ virtual dispatch, not a jump table)
- HLE contracts, a debugging playbook, the export tooling

Repo (data as JSON + playbook, CC0, no game code/assets):
https://github.com/InitialDad/PS2Recomp-WoS-Findings

Two things I'd genuinely like eyes on:
1. The `dsll32`/`dsrl32` mis-widening theory for the corrupted `fd` link — anyone who's
   debugged R5900 64-bit store recompilation, does this match what you've seen?
2. A `VOLUME.DAT` block type (`type_0x14`, 43 blocks / ~12 MB) that fails every standard
   codec (zlib/lz4/lzss/…). Proprietary encoding, or am I missing something obvious?

I'm new to this community and mostly want the findings to save someone else the dead
ends — and to get corrected where I'm wrong.
