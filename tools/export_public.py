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
def dump(conn, sql, transform=None):
    conn.row_factory = sqlite3.Row
    out = []
    for r in conn.execute(sql):
        d = scrub_row(dict(r))
        if transform:
            d = transform(d)
        out.append(d)
    return out

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
        return d

    exports = {
        'game':            ("SELECT serial,name,region,notes FROM games", None),
        'addresses':       ("SELECT serial,label,address,fmt,category,notes,pointer_chain,code_refs "
                            "FROM km_addresses ORDER BY address", addr_tx),
        'findings':        ("SELECT serial,topic,outcome,details FROM km_findings ORDER BY ts", None),
        'dead_ends':       ("SELECT serial,pattern,reason FROM km_bad_paths ORDER BY added_ts", None),
        'mod_recipes':     ("SELECT serial,name,kind,status,payload,notes FROM km_mod_manifest ORDER BY name", None),
        'engine_patterns': ("SELECT * FROM km_engine_patterns", None),
        'opcode_handlers': ("SELECT * FROM km_opcode_handlers", None),
    }
    summary = {}
    for name, (sql, tx) in exports.items():
        try:
            rows = dump(conn, sql, tx)
        except sqlite3.OperationalError as e:
            print(f'skip {name}: {e}', file=sys.stderr); continue
        (out / f'{name}.json').write_text(
            json.dumps(rows, indent=2, ensure_ascii=False), encoding='utf-8')
        summary[name] = len(rows)
    print('exported:', json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
