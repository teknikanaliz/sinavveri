#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YÖK Atlas (2025 tercih kılavuzu) gerçek verisini çeker.
Kaynak: POST https://yokatlas.yok.gov.tr/api/tercih-kilavuz/search
Çıktı: data/programs_raw.json (tüm kayıtlar, sadeleştirilmiş alanlar)
       data/veri/{say,ea,soz,dil,tyt}.json (istemci tarafı arama/tercih robotu için)
"""
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
VERI = DATA / "veri"
DATA.mkdir(exist_ok=True)
VERI.mkdir(exist_ok=True)

URL = "https://yokatlas.yok.gov.tr/api/tercih-kilavuz/search"
HEADERS = {"Content-Type": "application/json", "User-Agent": "sinavveri-bot/1.0 (+https://sinavveri.com)"}
SIZE = 2000
# Lisans (46): SAY/EA/SÖZ/DİL · Önlisans (47): TYT
SCOPES = [
    (46, "SAY"), (46, "EA"), (46, "SÖZ"), (46, "DİL"),
    (47, "TYT"),
]


def post(body):
    req = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"), headers=HEADERS, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_scope(birim_turu, puan_turu):
    out, page = [], 0
    while True:
        body = {"filters": {"birimTuruId": birim_turu, "puanTuru": puan_turu},
                "page": page, "size": SIZE, "sortBy": "basariSirasi", "direction": "ASC"}
        d = post(body)
        content = d.get("content", [])
        out.extend(content)
        total = d.get("totalElements", 0)
        print(f"    {puan_turu} sayfa {page}: +{len(content)}  ({len(out)}/{total})")
        if d.get("last") or not content:
            break
        page += 1
        time.sleep(0.4)
    return out


def _f(r, key):
    """Float al — API geçmiş alanları (minPuan1/2/3) STRING döner, cari float."""
    v = r.get(key)
    if v in (None, ""):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return round(f, 3) if f else None


def _i(r, key):
    v = r.get(key)
    if v in (None, ""):
        return None
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        return None
    return n or None


def trim(r):
    """İstemciye gidecek kompakt kayıt + sunucu tarafı için 4 yıllık geçmiş.
    Geçmiş eşlemesi (yokatlas-py): suffix 1→2024, 2→2023, 3→2022.
    yerleşen alanı: gkY (cari), gk1/gk2/gk3 (geçmiş)."""
    return {
        "k": r.get("kilavuzKodu"),
        "u": (r.get("universiteAdi") or "").strip(),
        "b": (r.get("birimAdi") or "").strip(),
        "g": (r.get("birimGrupAdi") or "").strip(),
        "il": (r.get("ilAdi") or "").strip().title(),
        "ilce": (r.get("ilceAdi") or "").strip().title(),
        "fak": (r.get("fymkAdi") or "").strip(),  # Fakülte/Yüksekokul/MYO — aynı-ad ayırt edici
        "t": {"DEVLET": "D", "VAKIF": "V", "KKTC": "K", "YÖK": "Y"}.get((r.get("universiteTuru") or "").strip(), "?"),
        "o": (r.get("ogrenimTuruAdi") or "").strip(),
        "dil": (r.get("ogrenimDiliAdi") or "").strip(),
        "bs": (r.get("bursOraniAdi") or "").strip(),
        "p": (r.get("puanTuru") or "").strip(),
        "kont": _i(r, "kontenjan"),
        "yer": _i(r, "gkY"),  # genel kontenjandan yerleşen (2025)
        "tp": _f(r, "minPuan"),
        "sira": _i(r, "basariSirasi"),
        # 4 yıllık geçmiş: [yıl, taban, sıra, yerleşen]
        "hist": [
            [2024, _f(r, "minPuan1"), _i(r, "basariSirasi1"), _i(r, "gk1")],
            [2023, _f(r, "minPuan2"), _i(r, "basariSirasi2"), _i(r, "gk2")],
            [2022, _f(r, "minPuan3"), _i(r, "basariSirasi3"), _i(r, "gk3")],
        ],
    }


def main():
    all_recs = []
    pt_key = {"SAY": "say", "EA": "ea", "SÖZ": "soz", "DİL": "dil", "TYT": "tyt"}
    for birim, pt in SCOPES:
        print(f"  Çekiliyor: birimTuru={birim} puanTuru={pt}")
        recs = fetch_scope(birim, pt)
        trimmed = [trim(r) for r in recs]
        (VERI / f"{pt_key[pt]}.json").write_text(
            json.dumps(trimmed, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        sz = (VERI / f"{pt_key[pt]}.json").stat().st_size
        print(f"  → {pt}: {len(trimmed)} kayıt, {sz//1024} KB")
        all_recs.extend(trimmed)
    (DATA / "programs_raw.json").write_text(
        json.dumps(all_recs, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\nTOPLAM: {len(all_recs)} program → data/programs_raw.json")
    # meta
    meta = {"kaynak": "YÖK Atlas 2025 Tercih Kılavuzu", "url": URL,
            "yil": 2025, "toplam": len(all_recs)}
    (DATA / "yokatlas_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
