#!/usr/bin/env python3
"""
Export a curated, sanitized set of port boot logs for the public repo.

Why publish logs at all: the findings files say what we concluded. The logs are
the raw evidence someone else can read to reach a *different* conclusion, spot a
pattern we missed, or catch us being wrong. That has already happened once
internally, so it is worth making easy.

What this does:

  * Curates. 156 raw logs / 526 MB is not a contribution, it is a dump. Only the
    runs that carry the diagnostic story ship, each with a note on what it shows.
  * Scrubs local paths. `C:/Users/<name>/...` becomes `<path>`. Note the port
    also prints a legitimate `owner=0x...` diagnostic field, so the username is
    NOT blanket-replaced - only path-shaped text is rewritten, or that field
    would be corrupted.
  * Trims runaway repetition. A single run can emit ~9,500 identical-tag lines.
    Consecutive runs of the same tag keep their first and last KEEP lines and
    collapse the middle into an explicit elision marker, so the shape of the run
    is preserved and the size is not.
  * Compresses, and writes INDEX.md ordered by date.

Usage:
    python export_logs.py --src C:/Users/<you>/wos_recomp --out ../logs
"""
import argparse
import datetime as dt
import gzip
import os
import re
import shutil

# Curated set: filename -> what this run is evidence for.
# Ordered oldest-first in the index by the file's own mtime, not by this dict.
MANIFEST = {
    "boot_p6p_interactive.log":
        "Early interactive drive. Main loop alive, 249 vblanks. Baseline for "
        "'the CPU side runs' before rendering was the focus.",
    "boot_p6r_interactive.log":
        "Longer interactive drive, 527 vblanks. Confirms the loop sustains "
        "rather than limping.",
    "boot_p7i.log":
        "THE SOLVED BOOT HANG. 1,060 samples of the EE thread frozen at "
        "pc=0x1d1050, inside the game's dlmalloc smallbin best-fit scan. This "
        "is the corrupted-free-list hang described in FINDINGS.md, now fixed. "
        "Kept as the reference signature of that failure mode.",
    "boot_p7g.log":
        "Post-allocator-work drive, 337 vblanks.",
    "boot_p7j.log":
        "Longest clean drive in this set, 719 vblanks, no allocator freeze.",
    "boot_p7j2.log.err":
        "First run carrying [p4:gs-trx] GS transfer tracing. Shows texture "
        "uploads genuinely reaching VRAM, which retired the earlier and wrong "
        "'no texture uploads happen' claim.",
    "boot_menu.log.err":
        "Menu-path drive, 143 vblanks.",
    "boot_trap_003849.log.err":
        "Sprite-kick tracing comes online: 51 [p4:gs-sprite] records with "
        "FRAME/SCISSOR/TEST/TEX0 and vertex coords per kick.",
    "boot_trap_105751.log.err":
        "510 sprite kicks with full per-kick GS state. Primary evidence that "
        "the draws are issued and the defect is downstream of upload.",
    "boot_trap_111754.log.err":
        "THE MISLEADING ONE. 8 [p4:gs-trx] uploads, 511 [p4:gs-sprite] kicks, "
        "and the 24 [p4:clut] samples that were MISREAD as proof of a "
        "PSMT8/PSMCT32 swizzle bug. Read those 24 lines with FINDINGS.md "
        "'Worked example 2' open: every one lands at u<=2, v<=1, so index 0 is "
        "legitimate and the probe could not answer its own question. Published "
        "deliberately, including the misleading part. Disproved by the next log.",
    "boot_clutprobe.log.err":
        "THE ANSWER. Same scene, probe rewritten to aggregate over every sample "
        "instead of printing the first 24. For the title texture "
        "(psm=0x13 tbp0=0x1A40): at 1,000 samples the region reached is still "
        "v=[0..1] at 0.00% non-zero (which is how the old probe fooled us), but "
        "by 500,000 samples it is u=[0..480] v=[0..255], 35.21% non-zero, with "
        "all 256 distinct index values present. The PSMT8 read WORKS and the "
        "swizzle is exonerated. The black screen is caused by something else.",
}

WIN_PATH = re.compile(r"[A-Za-z]:[\\/][^\s\"',;)\]]*")
UNIX_HOME = re.compile(r"/(?:c|mnt/c)/Users/[^/\s\"']+", re.I)
TAG = re.compile(r"^\s*(\[[A-Za-z0-9:_.-]+\])")

# Budget per tag ACROSS THE WHOLE FILE, not per consecutive run. These logs
# interleave tags heavily, so a consecutive-run collapse barely fires: it took
# one 171k-line file to 125k, which is not a readable file. A global budget takes
# the same file to a few thousand lines.
HEAD, TAIL = 60, 60

# Tags that carry the actual evidence are never budgeted away, whatever the count.
ALWAYS_KEEP = {
    "[p4:clut]",        # the CLUT/index probe - the whole GS argument rests on it
    "[p4:gs-trx]",      # GS uploads reaching VRAM
    "[p4:gs-sprite]",   # per-kick FRAME/SCISSOR/TEST/TEX0 + vertex coords
    "[p4:malloc]",      # allocator diagnostics from the solved boot hang
}
# NOT here: [gzmfs]. It looks like a low-volume "file opened" tag and is one in
# most runs, but boot_menu emits 26,543 of them, which alone pushed that file
# past GitHub's ~1 MB in-browser preview limit. Budgeted like anything else.


def scrub(line):
    line = WIN_PATH.sub("<path>", line)
    return UNIX_HOME.sub("<path>", line)


def trim(lines):
    """Budget each tag across the whole file: keep the first HEAD and last TAIL
    occurrences, elide the middle once, and prepend a census so the reader knows
    exactly what was dropped. Line order is preserved."""
    idx = {}
    for i, line in enumerate(lines):
        m = TAG.match(line)
        idx.setdefault(m.group(1) if m else "(untagged)", []).append(i)

    drop, elide_at = set(), {}
    for tag, positions in idx.items():
        if tag in ALWAYS_KEEP or len(positions) <= HEAD + TAIL:
            continue
        middle = positions[HEAD:-TAIL]
        drop.update(middle)
        elide_at[middle[0]] = (tag, len(middle))

    header = [
        "# ---------------------------------------------------------------\n",
        "# Trimmed for publication by tools/export_logs.py.\n",
        "# Per-tag census of the ORIGINAL file (kept / total):\n",
    ]
    for tag, positions in sorted(idx.items(), key=lambda kv: -len(kv[1])):
        total = len(positions)
        kept = total if (tag in ALWAYS_KEEP or total <= HEAD + TAIL) else HEAD + TAIL
        mark = "  <- all kept (evidence)" if tag in ALWAYS_KEEP and total > HEAD + TAIL else ""
        header.append(f"#   {tag:22s} {kept:>7,} / {total:>7,}{mark}\n")
    header.append("# Nothing is silently removed; every elision is marked inline.\n")
    header.append("# ---------------------------------------------------------------\n\n")

    out = list(header)
    for i, line in enumerate(lines):
        if i in elide_at:
            tag, n = elide_at[i]
            out.append(f"        ... [{n:,} more {tag} lines elided by "
                       f"export_logs.py] ...\n")
        if i not in drop:
            out.append(line)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"))
    ap.add_argument("--no-trim", action="store_true")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    rows = []
    for name, note in MANIFEST.items():
        src = os.path.join(a.src, name)
        if not os.path.exists(src):
            print(f"  MISSING {name}")
            continue
        raw = os.path.getsize(src)
        with open(src, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
        n_in = len(lines)
        lines = [scrub(l) for l in lines]
        if not a.no_trim:
            lines = trim(lines)
        # Plain text, deliberately. gzip halves the size and removes the whole
        # point: GitHub cannot preview a .gz, and Windows will not open one
        # without extra software, so a curious reader has to download a binary
        # blob and decompress it before seeing a single line. These files exist
        # to be skimmed by strangers.
        dst = os.path.join(a.out, name)
        with open(dst, "w", encoding="utf-8", newline="\n") as fh:
            fh.writelines(lines)
        rows.append({
            "name": name, "note": note,
            "when": dt.datetime.fromtimestamp(os.path.getmtime(src)),
            "raw": raw, "out": os.path.getsize(dst),
            "lines_in": n_in, "lines_out": len(lines),
        })
        print(f"  {name:34s} {raw/1048576:7.2f} MB -> {os.path.getsize(dst)/1024:8.1f} KB"
              f"  ({n_in:,} -> {len(lines):,} lines)")

    rows.sort(key=lambda r: r["when"])
    idx = [
        "# Port boot logs",
        "",
        "Raw evidence from the Way of the Samurai (`SLUS-20407`) static-recompilation",
        "port, oldest first. These are the logs the conclusions in",
        "[`FINDINGS.md`](../FINDINGS.md) were drawn from, published so that someone",
        "else can read them and reach a different conclusion, spot a pattern we",
        "missed, or catch us being wrong.",
        "",
        "**Please do read them adversarially.** One of the logs here (`boot_trap_111754`)",
        "contains a probe output we misread as proof of a GS swizzle bug; the write-up",
        "of how that went wrong is in FINDINGS.md, 'Worked example 2'. If you spot",
        "something similar, an issue on this repo is very welcome.",
        "",
        "## What was done to these files",
        "",
        "- **Local paths scrubbed** to `<path>`. The port also emits a genuine",
        "  `owner=0x...` diagnostic field, so the username is not blanket-replaced;",
        "  only path-shaped text is rewritten. Nothing else is altered.",
        "- **Long runs of one tag collapsed.** A run can emit ~9,500 consecutive",
        "  identical-tag lines. The first and last few of each run are kept and the",
        "  middle is replaced with an explicit",
        "  `... [N more [tag] lines elided by export_logs.py] ...` marker, so no",
        "  elision is silent. Regenerate untrimmed with `--no-trim`.",
        "- **Left as plain text on purpose.** gzip would halve the size and",
        "  destroy the point: GitHub cannot preview a `.gz`, and Windows will not",
        "  open one without extra software. Click any file below and read it.",
        "",
        "No game code, assets, dialogue or memory dumps are included; these are the",
        "port's own diagnostic traces.",
        "",
        "| Date | Log | Size | Lines | What it shows |",
        "|------|-----|-----:|------:|---------------|",
    ]
    for r in rows:
        idx.append(
            f"| {r['when']:%Y-%m-%d %H:%M} | [`{r['name']}`]({r['name']}) | "
            f"{r['out']/1024:.0f} KB | {r['lines_out']:,} | {r['note']} |")
    idx += [
        "",
        f"*{len(rows)} logs, "
        f"{sum(r['raw'] for r in rows)/1048576:.0f} MB raw -> "
        f"{sum(r['out'] for r in rows)/1048576:.1f} MB published. "
        f"Generated by [`tools/export_logs.py`](../tools/export_logs.py).*",
        "",
    ]
    with open(os.path.join(a.out, "INDEX.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(idx))
    print(f"\nwrote {os.path.join(a.out, 'INDEX.md')} ({len(rows)} logs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
