#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SinavVeri veri tazeleme orkestrasyonu — cron entry: `python3 -m pipeline.run`.

Akış: fetch_yokatlas → fetch_osym → fetch_lgs → build.py

FAIL-SAFE tasarım (kötü otomatik deploy'a karşı):
- Her fetch adımından önce çıktı dosyalarının snapshot'ı alınır.
- Fetch sonrası çıktı doğrulanır: kayıt sayısı mutlak eşiğin altındaysa VEYA
  eski sayının belirlenen oranından düşükse (kaynak format değişti / boş döndü)
  → o adımın ESKİ verisi geri yüklenir, adım FAILED işaretlenir.
- build.py her hâlükârda çalışır (geçerli/eski veriyle). build.py çökerse exit 1
  → cron zincirindeki git-auto-push TETİKLENMEZ (bozuk içerik push edilmez).

Kullanım:
  python3 -m pipeline.run              # tam: fetch + build
  python3 -m pipeline.run --build-only # sadece build (fetch atla — hızlı test/rebuild)
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# (script, [çıktı dosyaları (data/ göreli)], min_ratio_vs_old, min_abs)
STEPS = [
    ("fetch_yokatlas.py", ["programs_raw.json"], 0.70, 5000),
    ("fetch_osym.py", ["osym_tus.json", "osym_dus.json", "osym_dgs.json", "osym_kpss.json"], 0.50, 50),
    ("fetch_lgs.py", ["lgs_liseler.json"], 0.70, 1000),
]


def count(p: Path) -> int:
    """JSON kayıt sayısı; okunamazsa -1, yoksa 0."""
    if not p.exists():
        return 0
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return len(d) if isinstance(d, (list, dict)) else 0
    except Exception:
        return -1


def run_step(script, outs, min_ratio, min_abs) -> bool:
    files = [DATA / o for o in outs]
    old = {f: count(f) for f in files}
    baks = {}
    for f in files:
        if f.exists():
            b = f.with_name(f.name + ".bak")
            shutil.copy2(f, b)
            baks[f] = b

    print(f"\n=== {script} ===", flush=True)
    try:
        r = subprocess.run([sys.executable, str(ROOT / "pipeline" / script)], cwd=str(ROOT))
        ran_ok = (r.returncode == 0)
    except Exception as e:
        print(f"  ! {script} istisna: {e}")
        ran_ok = False

    valid = ran_ok
    for f in files:
        new = count(f)
        o = old.get(f, 0)
        if new < min_abs or (o > 0 and new < o * min_ratio):
            valid = False
            print(f"  ! DOĞRULAMA BAŞARISIZ {f.name}: yeni={new} eski={o} "
                  f"(min_abs={min_abs}, ratio≥{min_ratio})")
        else:
            print(f"  ✓ {f.name}: {new} kayıt (eski {o})")

    if not valid:
        for f, b in baks.items():
            shutil.copy2(b, f)
            print(f"  ↩ {f.name} ESKİ veriye geri yüklendi")

    for b in baks.values():
        b.unlink(missing_ok=True)
    return valid


def main():
    build_only = "--build-only" in sys.argv
    results = {}

    if not build_only:
        for script, outs, mr, ma in STEPS:
            results[script] = run_step(script, outs, mr, ma)
    else:
        print("[--build-only] fetch adımları atlandı")

    # PG system-of-record senkronu: data/*.json → PG → data/*.json (merkezî 'sinav' şeması).
    # Fail-safe: PG ulaşılamazsa pg.py exit 0 → build mevcut data/*.json'dan sürer.
    if not build_only:
        print("\n=== PG SYNC (system-of-record: sinav şeması) ===", flush=True)
        subprocess.run([sys.executable, "-m", "pipeline.pg", "sync"], cwd=str(ROOT))

    print("\n=== BUILD ===", flush=True)
    b = subprocess.run([sys.executable, str(ROOT / "build.py")], cwd=str(ROOT))

    print("\n=== ÖZET ===")
    for s, ok in results.items():
        print(f"  {'✓' if ok else '✗ (eski veri korundu)'} {s}")
    if b.returncode != 0:
        print("  ✗ build.py BAŞARISIZ → git-auto-push tetiklenmeyecek")
        sys.exit(1)
    print("  ✓ build.py OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
