#!/usr/bin/env python3
"""
Export a SANITIZED, public-safe subset of the Prometheus mods.db.

Ships ONLY reverse-engineering metadata (addresses, findings, dead-ends,
per-game mod recipes, engine/opcode maps). Never ships:
  - raw extracted game assets (km_assets)
  - raw extracted in-game strings / dialogue (km_ghidra_strings)  [copyright]
  - memory dumps, ISO, or any game binary data
Free-text fields are scrubbed of local filesystem paths and the OS username.

Usage:  python export_public.py --db ../../pcsx2_modder_wos/db/mods.db --out ../data
"""
import argparse, json, re, sqlite3, sys
from pathlib import Path

# --- scrubbers -------------------------------------------------------------
WIN_PATH = re.compile(r'[A-Za-z]:[\\/][^\s"\',]*')      # C:\Users\owner\...  or  C:/Users/...
UNIXHOME = re.compile(r'/(?:c|mnt/c)/Users/[^/\s"\']+', re.I)
USERNAME = re.compile(r'\bowner\b')                     # OS account name

def scrub(v):
    if not isinstance(v, str):
        return v
    v = WIN_PATH.sub('<path>', v)
    v = UNIXHOME.sub('<path>', v)
    v = USERNAME.sub('<user>', v)
    return v

def scrub_row(d):
    return {k: scrub(val) for k, val in d.items()}

def hexaddr(v):
    return f'0x{v:08X}' if isinstance(v, int) else v

# --- export ----------------------------------------------------------------
def dump(conn, sql, transform=None, dedup_on=None):
    conn.row_factory = sqlite3.Row
    out, seen = [], set()
    for r in conn.execute(sql):
        d = scrub_row(dict(r))
        if transform:
            d = transform(d)
        if dedup_on:
            key = tuple(d.get(k) for k in dedup_on)
            if key in seen:
                continue
            seen.add(key)
        out.append(d)
    return out

def addr_evidence(notes):
    """Derive an honest evidence tier from the in-band DB notes only.
    Many addresses are ADDITIONALLY validated by the parallel-scan report; this
    field reflects only what the row itself states."""
    n = (notes or '').lower()
    if any(k in n for k in ('screenshot', 'visible', 'pause menu', 'on-screen',
                            'on screen', 'confirmed live', 'counter confirmed')):
        return 'on_screen'
    if any(k in n for k in ('snapshot', 'parscan', 'parallel', 'triangulat')):
        return 'snapshot_diff'
    if any(k in n for k in ('verified', 'confirmed')):
        return 'stated_verified'
    return 'catalogued'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    conn = sqlite3.connect(a.db)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    def addr_tx(d):
        if 'address' in d:
            d['address'] = hexaddr(d['address'])
        d['evidence'] = addr_evidence(d.get('notes'))   # honest per-row tier
        return d

    def sdk_tx(d):
        # NOT engine code — Sony SDK / libc++ / libmpeg shared with other titles.
        # confidence=1.0 in the DB means "byte-identical match", NOT "significant":
        # SDK code matches across most PS2 games, so discriminating power is ~zero.
        if 'address' in d:
            d['address'] = hexaddr(d['address'])
        d['kind'] = 'shared_sdk_or_middleware'
        return d

    exports = {
        # (sql, transform, dedup_on)
        'game':                  ("SELECT serial,name,region,notes FROM games", None, None),
        'addresses':             ("SELECT serial,label,address,fmt,category,notes,pointer_chain,code_refs "
                                  "FROM km_addresses ORDER BY address", addr_tx, None),
        'findings':              ("SELECT serial,topic,outcome,details FROM km_findings ORDER BY ts", None, None),
        'dead_ends':             ("SELECT serial,pattern,reason FROM km_bad_paths ORDER BY added_ts",
                                  None, ('pattern', 'reason')),
        'mod_recipes':           ("SELECT serial,name,kind,status,payload,notes FROM km_mod_manifest ORDER BY name",
                                  None, None),
        'shared_sdk_fingerprints': ("SELECT pattern_key,game_serial,address,signature_hex,confidence,notes "
                                  "FROM km_engine_patterns", sdk_tx, None),
        'opcode_handlers':       ("SELECT opcode,handler_addr,mnemonic,arg_layout,evidence,notes "
                                  "FROM km_opcode_handlers", None, None),
    }
    summary = {}
    for name, (sql, tx, dd) in exports.items():
        try:
            rows = dump(conn, sql, tx, dedup_on=dd)
        except sqlite3.OperationalError as e:
            print(f'skip {name}: {e}', file=sys.stderr); continue
        (out / f'{name}.json').write_text(
            json.dumps(rows, indent=2, ensure_ascii=False), encoding='utf-8')
        summary[name] = len(rows)
    print('exported:', json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
