#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SinavVeri ⇄ Merkezî PostgreSQL (TrVeri DB, şema: sinav) — system-of-record katmanı.

Hibrit mimari: PG kaynak-doğruluk (system-of-record), site statik kalır.
  fetch_* → data/*.json → load(PG)  → export(PG → data/*.json) → build.py → deploy

- load():   data/*.json → sinav.* (transaction: truncate+insert; hata olursa rollback, eski veri durur)
- export(): sinav.* → data/*.json (build girdisi; PG kaynaktan tazelenir)

Bağlantı env ile (secret REPO'DA DEĞİL):
  SINAV_PG_DSN="postgresql://trveri:***@127.0.0.1:5432/trveri"   (tercih)
  ya da PG_HOST/PG_PORT/PG_DB/PG_USER/PG_PASSWORD
PG ulaşılamazsa sessizce atlanır → build mevcut data/*.json'dan sürer (fail-safe).
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SCHEMA = "sinav"

# (tablo, json dosyası, liste_mi)  — liste tipi: kayıt-başına satır; obje tipi: tek satır
DATASETS = [
    ("programlar", "programs_raw.json", True),
    ("tus", "osym_tus.json", True),
    ("dus", "osym_dus.json", True),
    ("dgs", "osym_dgs.json", True),
    ("kpss", "osym_kpss.json", True),
    ("liseler", "lgs_liseler.json", True),
    ("takvim", "takvim-2026.json", False),
    ("dgs_bolum", "dgs_bolum.json", False),
    ("tus_dallar", "tus_dallar.json", False),
    ("dus_dallar", "dus_dallar.json", False),
]
META_FILES = {"yokatlas": "yokatlas_meta.json", "osym": "osym_meta.json", "lgs": "lgs_meta.json"}


def connect():
    """psycopg2 bağlantısı; başarısızsa None (build engellenmez)."""
    try:
        import psycopg2
    except Exception as e:
        print(f"  [pg] psycopg2 yok, atlanıyor: {e}")
        return None
    try:
        dsn = os.environ.get("SINAV_PG_DSN")
        if dsn:
            return psycopg2.connect(dsn, connect_timeout=8)
        return psycopg2.connect(
            host=os.environ.get("PG_HOST", "127.0.0.1"),
            port=os.environ.get("PG_PORT", "5432"),
            dbname=os.environ.get("PG_DB", "trveri"),
            user=os.environ.get("PG_USER", "trveri"),
            password=os.environ.get("PG_PASSWORD", ""),
            connect_timeout=8,
        )
    except Exception as e:
        print(f"  [pg] bağlanılamadı, atlanıyor: {e}")
        return None


def _read(fn):
    p = DATA / fn
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def load(conn):
    """data/*.json → sinav.* (her tablo transaction içinde truncate+insert)."""
    from psycopg2.extras import execute_values
    cur = conn.cursor()
    for tbl, fn, is_list in DATASETS:
        d = _read(fn)
        if d is None:
            continue
        rows = d if is_list else [d]
        cur.execute(f"TRUNCATE {SCHEMA}.{tbl} RESTART IDENTITY")
        execute_values(
            cur, f"INSERT INTO {SCHEMA}.{tbl}(payload) VALUES %s",
            [(json.dumps(r, ensure_ascii=False),) for r in rows], template="(%s::jsonb)")
        print(f"  [pg load] {tbl}: {len(rows)}")
    for key, fn in META_FILES.items():
        m = _read(fn)
        if m is None:
            continue
        kayit = m.get("toplam_okul") or m.get("toplam") or m.get("kayit") or 0
        cur.execute(
            f"INSERT INTO {SCHEMA}.meta(dataset,payload,kayit,guncellendi) VALUES(%s,%s::jsonb,%s,now()) "
            f"ON CONFLICT(dataset) DO UPDATE SET payload=EXCLUDED.payload,kayit=EXCLUDED.kayit,guncellendi=now()",
            (key, json.dumps(m, ensure_ascii=False), kayit))
    conn.commit()
    print("  [pg load] commit ✓")


def export(conn):
    """sinav.* → data/*.json (build girdisi PG'den tazelenir)."""
    cur = conn.cursor()
    for tbl, fn, is_list in DATASETS:
        cur.execute(f"SELECT payload FROM {SCHEMA}.{tbl} ORDER BY id")
        rows = [r[0] for r in cur.fetchall()]
        if not rows:
            continue
        out = rows if is_list else rows[0]
        (DATA / fn).write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"  [pg export] {tbl} → {fn}: {len(rows) if is_list else 1}")
    for key, fn in META_FILES.items():
        cur.execute(f"SELECT payload FROM {SCHEMA}.meta WHERE dataset=%s", (key,))
        r = cur.fetchone()
        if r:
            (DATA / fn).write_text(json.dumps(r[0], ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "load"
    conn = connect()
    if conn is None:
        sys.exit(0)  # fail-safe: PG yoksa engelleme
    try:
        if cmd == "load":
            load(conn)
        elif cmd == "export":
            export(conn)
        elif cmd == "sync":  # load + export (round-trip)
            load(conn)
            export(conn)
        else:
            print(f"bilinmeyen komut: {cmd} (load|export|sync)")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
