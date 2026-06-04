#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Üniversite künyesi (öğrenci/akademisyen/kuruluş/adres/iletişim) + logo.

İki kaynak birleştirilir:
  1) YÖK Atlas tercih-kılavuz API → (üniversiteAdı → universiteId) eşlemesi (logo + kimlik)
  2) Açık üniversite künye veri seti (kuruluş, tür, il, bölge, website, adres, telefon,
     rektör, akademik kadro kırılımı, öğrenci sayıları cinsiyet bazında).
Birincil/resmî kaynak YÖK İstatistik + YÖK Atlas'tır.

Çıktı:
  data/universiteler.json  → { norm(üniAdı): {id, slug, kurulus_yil, tur, il, bolge,
       website, telefon, eposta, adres, rektor, akademisyen, prof, doc, dr,
       ogrenci, ogr_e, ogr_k, lisans, onlisans, yukseklisans, doktora} }
  assets/logos/<universiteId>.png  → üniversite logoları (self-host)
"""
import csv
import io
import json
import os
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LOGODIR = ROOT / "assets" / "logos"
LOGODIR.mkdir(parents=True, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
API = "https://yokatlas.yok.gov.tr/api/tercih-kilavuz/search"
CSV_SRC = "https://raw.githubusercontent.com/MorphaxTheDeveloper/yokatlas-dataset-2025/main/universiteler.csv"
CSV_CACHE = DATA / "_universiteler_kaynak.csv"
LOGO_BASE = "https://www.universitetercih.com/static/universite-logolari/{}.png"  # YÖK kurum kodu = universiteId


def norm(s):
    s = (s or "").strip().lower().replace("i̇", "i")
    s = re.sub(r"\([^)]*\)", "", s)
    tr = {"ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c", "â": "a", "î": "i", "û": "u"}
    s = "".join(tr.get(c, c) for c in s)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


_TRLOW = {"I": "ı", "İ": "i", "Ş": "ş", "Ğ": "ğ", "Ü": "ü", "Ö": "ö", "Ç": "ç"}
_TRUP = {"i": "İ", "ı": "I", "ş": "Ş", "ğ": "Ğ", "ü": "Ü", "ö": "Ö", "ç": "Ç"}


def tr_title(s):
    """Türkçe-doğru başlık biçimi (Python .title() 'İNCİ'→'İnci̇' bozar)."""
    s = (s or "").strip().replace("̇", "")
    if not s:
        return ""
    out = []
    for w in s.split(" "):
        if not w:
            continue
        out.append(_TRUP.get(w[0], w[0].upper()) + "".join(_TRLOW.get(c, c.lower()) for c in w[1:]))
    return " ".join(out)


def clean_adres(s):
    s = (s or "").replace("\\n", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", s).strip()


def _i(x):
    try:
        v = int(float(x))
        return v if v else 0
    except (TypeError, ValueError):
        return 0


IDMAP_CACHE = DATA / "_uni_idmap.json"


def fetch_idmap():
    if IDMAP_CACHE.exists():
        return json.loads(IDMAP_CACHE.read_text(encoding="utf-8"))
    idmap = {}
    for pt, birim in [("SAY", 46), ("EA", 46), ("SÖZ", 46), ("DİL", 46), ("TYT", 47)]:
        body = json.dumps({"filters": {"birimTuruId": birim, "puanTuru": pt},
                           "page": 0, "size": 2000, "sortBy": "basariSirasi", "direction": "ASC"}).encode()
        req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json", "User-Agent": UA}, method="POST")
        for r in json.load(urllib.request.urlopen(req, timeout=90)).get("content", []):
            u = (r.get("universiteAdi") or "").strip()
            if u and r.get("universiteId"):
                idmap[norm(u)] = r["universiteId"]
    IDMAP_CACHE.write_text(json.dumps(idmap, ensure_ascii=False), encoding="utf-8")
    return idmap


def load_csv():
    if CSV_CACHE.exists():
        return CSV_CACHE.read_text(encoding="utf-8")
    req = urllib.request.Request(CSV_SRC, headers={"User-Agent": "sinavveri-bot/1.0"})
    txt = urllib.request.urlopen(req, timeout=120).read().decode("utf-8")
    CSV_CACHE.write_text(txt, encoding="utf-8")
    return txt


def proxy_opener():
    url = ""
    reg = Path("/home/tekni/VS/servermimari/.secrets/REGISTRY.env")
    if reg.exists():
        for ln in reg.read_text(encoding="utf-8").splitlines():
            if ln.startswith("EVOMI_PROXY_URL="):
                url = ln.split("=", 1)[1].strip().strip('"')
    if not url:
        return None
    return urllib.request.build_opener(urllib.request.ProxyHandler({"http": url, "https": url}))


def download_logos(ids):
    opener = proxy_opener()
    if not opener:
        print("  ! evomi proxy yok — logo indirme atlandı")
        return 0
    hdr = {"User-Agent": UA, "Accept": "image/avif,image/webp,image/png,*/*",
           "Referer": "https://www.universitetercih.com/",
           "sec-fetch-dest": "image", "sec-fetch-mode": "no-cors", "sec-fetch-site": "same-origin"}
    ok = 0
    for uid in ids:
        dest = LOGODIR / f"{uid}.png"
        if dest.exists() and dest.stat().st_size > 500:
            ok += 1
            continue
        try:
            req = urllib.request.Request(LOGO_BASE.format(uid), headers=hdr)
            data = opener.open(req, timeout=40).read()
            if len(data) > 500 and data[:8] == b"\x89PNG\r\n\x1a\n":
                dest.write_bytes(data)
                ok += 1
        except Exception:
            pass
    return ok


def main():
    print("  Üniversite ID eşlemesi çekiliyor (YÖK Atlas)…")
    idmap = fetch_idmap()
    print(f"    {len(idmap)} üniversite ID")

    rows = list(csv.DictReader(io.StringIO(load_csv())))
    out = {}
    for r in rows:
        key = norm(r["isim"])
        ak = sum(_i(r.get(k)) for k in ("profesor", "docent", "doktor", "ogretim", "arastirma"))
        kur = (r.get("kurulus") or "").strip()
        yil = ""
        m = re.search(r"(\d{4})", kur)
        if m:
            yil = m.group(1)
        out[key] = {
            "id": idmap.get(key),
            "slug": (r.get("slug") or "").strip(),
            "kurulus": yil,
            "tur": tr_title(r.get("tur")),
            "il": tr_title(r.get("il")),
            "bolge": tr_title(r.get("bolge")),
            "website": (r.get("website") or "").strip(),
            "telefon": (r.get("telefon") or "").strip(),
            "eposta": (r.get("eposta") or "").strip(),
            "adres": clean_adres(r.get("adres")),
            "rektor": tr_title(r.get("rektor")),
            "akademisyen": ak,
            "prof": _i(r.get("profesor")), "doc": _i(r.get("docent")), "dr": _i(r.get("doktor")),
            "ogrenci": _i(r.get("toplam")), "ogr_e": _i(r.get("toplamerkek")), "ogr_k": _i(r.get("toplamkadin")),
            "onlisans": _i(r.get("onlisanstoplam")), "lisans": _i(r.get("lisanstoplam")),
            "yukseklisans": _i(r.get("yukseklisanstoplam")), "doktora": _i(r.get("doktoratoplam")),
        }

    # Künyesi olmayan ama ID'si olan üniler için minimum kayıt (logo + kimlik dursun)
    for key, uid in idmap.items():
        out.setdefault(key, {"id": uid})
        out[key].setdefault("id", uid)

    (DATA / "universiteler.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    kunyeli = sum(1 for v in out.values() if v.get("ogrenci"))
    print(f"  → universiteler.json: {len(out)} üniversite ({kunyeli} künyeli)")

    ids = sorted(set(v["id"] for v in out.values() if v.get("id")))
    print(f"  Logolar indiriliyor ({len(ids)} adet, evomi proxy)…")
    n = download_logos(ids)
    print(f"  → assets/logos/: {n}/{len(ids)} logo hazır")


if __name__ == "__main__":
    main()
