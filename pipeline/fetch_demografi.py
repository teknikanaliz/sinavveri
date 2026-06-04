#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yerleşen demografisi (cinsiyet + öğrenim durumu) — YÖK Atlas arşiv verisi.

YÖK Atlas 2024'te React'e geçerken program-bazı demografik dağılımları yayından
kaldırdı. Bu veri yalnızca migrasyon-öncesi arşivlerde yaşıyor. Burada, silinen
YÖK Atlas demografisini sistematik toplamış açık veri setinden (yerleşenlerin
yıllara göre cinsiyet ve öğrenim durumu) yararlanılıyor; birincil/resmî kaynak
YÖK Atlas'tır (yayınlanan içerikte yalnızca "YÖK Atlas" gösterilir).

Çıktı: data/demografi.json  →  { kilavuzKodu: {"y":2023,"k":kiz,"e":erkek,
        "ls":liseli, "mz":mezun, "ub":uni_iken, "um":uni_mezunu, "hist":{yıl:{...}}} }

Eşleme: (üniversite, birimGrupAdi, puanTürü) anahtarıyla; arşiv programı varyant
adlarını (İngilizce/Burslu) tek grup adı altında topladığından çoklu satır toplanır.
"""
import csv
import io
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# Silinen YÖK Atlas demografisini toplamış açık veri seti (ham CSV)
SRC = "https://raw.githubusercontent.com/MorphaxTheDeveloper/yokatlas-dataset-2025/main/tum_bolumler.csv"
CACHE = DATA / "_demografi_kaynak.csv"  # ham önbellek (gitignore'da)

TMAP = {"SAYISAL": "SAY", "EŞİT AĞIRLIK": "EA", "SÖZEL": "SÖZ", "DİL": "DİL", "TYT": "TYT"}
YEARS = [2023, 2022, 2021]  # en güncelden geriye (YÖK Atlas'ın son yayınladığı yıllar)


def norm(s):
    s = (s or "").strip().lower().replace("i̇", "i")
    s = re.sub(r"\([^)]*\)", "", s)  # parantez içi (şehir eki, dil/burs eki) at
    tr = {"ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c", "â": "a", "î": "i", "û": "u"}
    s = "".join(tr.get(c, c) for c in s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def fnum(x):
    x = (x or "").strip()
    try:
        v = float(x)
        return int(round(v)) if v and v > 0 else None
    except (TypeError, ValueError):
        return None


def load_source():
    if CACHE.exists():
        return CACHE.read_text(encoding="utf-8")
    print("  Kaynak CSV indiriliyor…")
    req = urllib.request.Request(SRC, headers={"User-Agent": "sinavveri-bot/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        txt = r.read().decode("utf-8")
    CACHE.write_text(txt, encoding="utf-8")
    return txt


def build_index(csv_text):
    """(uni, grup, puan) → yıllara göre toplanmış demografi."""
    idx = {}
    cols = {y: {"k": f"kiz{y}", "e": f"erkek{y}", "ls": f"liseli{y}",
                "mz": f"mezun{y}", "ub": f"universiteli{y}", "um": f"unimezunu{y}"} for y in YEARS}
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    for r in rows:
        key = (norm(r.get("universite")), norm(r.get("isim")), TMAP.get(r.get("tur"), r.get("tur")))
        bucket = idx.setdefault(key, {y: {} for y in YEARS})
        for y in YEARS:
            for short, col in cols[y].items():
                v = fnum(r.get(col))
                if v:
                    bucket[y][short] = bucket[y].get(short, 0) + v
    return idx


def main():
    csv_text = load_source()
    idx = build_index(csv_text)
    print(f"  Arşiv demografi agregat anahtarı: {len(idx)}")

    programs = json.loads((DATA / "programs_raw.json").read_text(encoding="utf-8"))
    out = {}
    matched = 0
    for p in programs:
        key = (norm(p.get("u")), norm(p.get("g") or p.get("b")), p.get("p"))
        bucket = idx.get(key)
        if not bucket:
            continue
        # En güncel dolu yılı seç
        rec = None
        for y in YEARS:
            d = bucket.get(y) or {}
            if d.get("k") or d.get("e"):
                rec = {"y": y, **d}
                break
        if not rec:
            continue
        # Önceki yıllar (cinsiyet trendi için)
        hist = {}
        for y in YEARS:
            d = bucket.get(y) or {}
            if (d.get("k") or d.get("e")) and y != rec["y"]:
                hist[str(y)] = {"k": d.get("k", 0), "e": d.get("e", 0)}
        if hist:
            rec["hist"] = hist
        out[p["k"]] = rec
        matched += 1

    (DATA / "demografi.json").write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    sz = (DATA / "demografi.json").stat().st_size
    print(f"  → demografi.json: {matched}/{len(programs)} program eşleşti "
          f"(%{100*matched//len(programs)}), {sz//1024} KB")
    meta = {"kaynak": "YÖK Atlas (arşiv — yerleşen demografisi)", "yil_araligi": "2021-2023",
            "eslesen": matched, "alanlar": "cinsiyet (kız/erkek), öğrenim durumu "
            "(lise son sınıf / önceki yıl mezunu / üniversite öğrencisi iken / üniversite mezunu)"}
    (DATA / "demografi_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
