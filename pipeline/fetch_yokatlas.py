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

_TRLOW = {"I": "ı", "İ": "i", "Ş": "ş", "Ğ": "ğ", "Ü": "ü", "Ö": "ö", "Ç": "ç"}
_TRUP = {"i": "İ", "ı": "I", "ş": "Ş", "ğ": "Ğ", "ü": "Ü", "ö": "Ö", "ç": "Ç"}


def tr_title(s):
    """Türkçe-doğru başlık biçimi: İ→i, I→ı (Python .title() yanlış yapar:
    'ADIYAMAN'→'Adiyaman', 'İZMİR'→'İzmi̇r'). Kelime başı büyük, geri kalan Türkçe küçük."""
    s = (s or "").strip()
    if not s:
        return ""
    def lo(c):
        return _TRLOW.get(c, c.lower())
    def up(c):
        return _TRUP.get(c, c.upper())
    return " ".join((up(w[0]) + "".join(lo(c) for c in w[1:])) if w else w for w in s.split(" "))


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
        "il": tr_title(r.get("ilAdi")),
        "ilce": tr_title(r.get("ilceAdi")),
        "fak": (r.get("fymkAdi") or "").strip(),  # Fakülte/Yüksekokul/MYO — aynı-ad ayırt edici
        "t": {"DEVLET": "D", "VAKIF": "V", "VAKIF MYO": "V", "KKTC": "K", "YÖK": "Y",
              "YURTDISI KAMU": "Y", "YURTDISI VAKIF": "Y"}.get((r.get("universiteTuru") or "").strip(), "?"),
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
        # Program detay zenginliği (toplu API'den bedava):
        "kosul": (r.get("kosul") or "").strip(),                  # "21,22,23" koşul kodları
        "kadro": [_i(r, "prof"), _i(r, "doc"), _i(r, "dou"), _i(r, "arGor"), _i(r, "ogrGor")],  # Prof/Doçent/Dr.Öğr.Ü/Ar.Gör/Öğr.Gör
        "akr": (r.get("akreditasyon") or "").strip() or None,     # akreditasyon kurumu
        "sure": _i(r, "ogrenimSuresi"),                            # öğrenim süresi (yıl)
        "ucret": _i(r, "ucret"),                                   # vakıf ücreti (TL)
    }


def main():
    all_recs = []
    kosul_map = {}  # koşul kodu → açıklama (tüm programlardan dedup)
    pt_key = {"SAY": "say", "EA": "ea", "SÖZ": "soz", "DİL": "dil", "TYT": "tyt"}
    for birim, pt in SCOPES:
        print(f"  Çekiliyor: birimTuru={birim} puanTuru={pt}")
        recs = fetch_scope(birim, pt)
        for r in recs:
            for d in (r.get("kosulList") or []):
                for code, text in d.items():
                    if code and text:
                        kosul_map[str(code)] = text.strip()
        trimmed = [trim(r) for r in recs]
        (VERI / f"{pt_key[pt]}.json").write_text(
            json.dumps(trimmed, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        sz = (VERI / f"{pt_key[pt]}.json").stat().st_size
        print(f"  → {pt}: {len(trimmed)} kayıt, {sz//1024} KB")
        all_recs.extend(trimmed)
    (DATA / "programs_raw.json").write_text(
        json.dumps(all_recs, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\nTOPLAM: {len(all_recs)} program → data/programs_raw.json")
    (DATA / "kosul_map.json").write_text(
        json.dumps(kosul_map, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  koşul kodu açıklaması: {len(kosul_map)} → data/kosul_map.json")
    # meta
    meta = {"kaynak": "YÖK Atlas 2025 Tercih Kılavuzu", "url": URL,
            "yil": 2025, "toplam": len(all_recs)}
    (DATA / "yokatlas_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
