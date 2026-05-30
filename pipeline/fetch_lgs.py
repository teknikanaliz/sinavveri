#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LGS il-bazlı lise taban puanları (2025) — kaynak: kazanabilirsin.com (MEB derlemesi).
Kullanıcı onayı ile üçüncü-taraf scrape. Her il sayfasının HTML tablosu parse edilir.
Sütun sırası varyasyonuna dayanıklı heuristik: taban≥100, yüzdelik<100 (ondalık), kontenjan tam sayı.
Çıktı: data/lgs_liseler.json
"""
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
INDEX = "https://kazanabilirsin.com/lise-taban-puanlari-ve-yuzdelik-dilimleri-lgs-meb"
UA = {"User-Agent": "Mozilla/5.0 (compatible; sinavveri/1.0)"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "ignore")


def clean_first(cell):
    """Hücrenin ilk satırını (2025 değeri) temizle."""
    part = re.split(r"<br\s*/?>", cell, flags=re.I)[0]
    part = re.sub(r"<[^>]+>", "", part)
    part = part.replace("&amp;", "&").replace("&nbsp;", " ")
    return part.strip()


def to_float(s):
    s = s.replace(".", "").replace(",", ".") if s.count(",") == 1 and "." in s else s.replace(",", ".")
    try:
        return round(float(s), 4)
    except ValueError:
        return None


def normalize_tur(t):
    t = t.lower()
    if "fen lisesi" in t:
        return "Fen Lisesi"
    if "sosyal bilimler" in t:
        return "Sosyal Bilimler Lisesi"
    if "imam hatip" in t or "i̇mam hatip" in t:
        return "Anadolu İmam Hatip Lisesi"
    if "teknik" in t or "meslek" in t:
        return "Mesleki ve Teknik Anadolu Lisesi"
    if "anadolu lisesi" in t:
        return "Anadolu Lisesi"
    if "güzel sanatlar" in t:
        return "Güzel Sanatlar Lisesi"
    if "spor lisesi" in t:
        return "Spor Lisesi"
    return "Diğer"


def _col_map(header_cells):
    """Başlık hücrelerinden sütun indekslerini çıkar (layout pageye göre değişir)."""
    idx = {}
    for i, c in enumerate(header_cells):
        t = re.sub(r"<[^>]+>", "", c).lower()
        if "okul adı" in t or ("okul" in t and "tür" not in t):
            idx.setdefault("okul", i)
        elif "tür" in t:
            idx.setdefault("tur", i)
        elif "yıl" in t:
            idx.setdefault("yil", i)
        elif "kont" in t:
            idx.setdefault("kont", i)
        elif "taban" in t:
            idx.setdefault("tp", i)
        elif "yüzdelik" in t or "yuzdelik" in t:
            idx.setdefault("yuz", i)
    return idx


def parse_il(html, il_fallback):
    m = re.search(r"<table.*?</table>", html, re.S | re.I)
    if not m:
        return []
    rows = re.split(r"<tr[^>]*>", m.group(0))[1:]
    if not rows:
        return []
    # ilk satır = başlık
    header = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", rows[0], re.S | re.I)
    cmap = _col_map(header)
    if "okul" not in cmap or "tp" not in cmap:
        cmap = {"okul": 0, "tur": 1, "yil": 2, "kont": 3, "tp": 4, "yuz": 5}  # bilinen varsayılan
    out = []
    for row in rows[1:]:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S | re.I)
        if len(cells) <= cmap["tp"]:
            continue
        vals = [clean_first(c) for c in cells]
        info = vals[cmap["okul"]]
        if "/" not in info:
            continue
        parts = [p.strip() for p in info.split("/")]
        if len(parts) < 2:
            continue
        il = parts[0]
        ilce = parts[1] if len(parts) >= 3 else ""
        okul = " / ".join(parts[2:]) if len(parts) >= 3 else parts[1]
        tur_raw = vals[cmap["tur"]] if "tur" in cmap and cmap["tur"] < len(vals) else ""
        tp = to_float(vals[cmap["tp"]]) if cmap["tp"] < len(vals) else None
        yuz = to_float(vals[cmap["yuz"]]) if "yuz" in cmap and cmap["yuz"] < len(vals) else None
        kont = None
        if "kont" in cmap and cmap["kont"] < len(vals):
            ks = re.sub(r"[^\d]", "", vals[cmap["kont"]])
            kont = int(ks) if ks else None
        if tp is None or tp < 50 or tp > 500:
            continue  # geçersiz/boş satır
        if yuz is not None and (yuz < 0 or yuz > 100):
            yuz = None
        out.append({
            "il": il, "ilce": ilce, "okul": okul,
            "tur": normalize_tur(tur_raw), "tur_ham": tur_raw,
            "kont": kont, "tp": tp, "yuz": yuz,
        })
    return out


def main():
    print("LGS lise verisi çekiliyor (kazanabilirsin.com / MEB)...")
    idx = get(INDEX)
    urls = sorted(set(re.findall(
        r"https://kazanabilirsin\.com/[a-z0-9-]+-liseleri(?:-[0-9]{4})?-taban-puanlari-yuzdelik-dilimleri-lgs-meb", idx)))
    print(f"  {len(urls)} il sayfası bulundu")
    all_schools = []
    il_count = {}
    for i, u in enumerate(urls, 1):
        try:
            html = get(u)
            recs = parse_il(html, u)
            for r in recs:
                all_schools.append(r)
            il = recs[0]["il"] if recs else u.split("/")[-1].split("-")[0]
            il_count[il] = len(recs)
            print(f"  [{i}/{len(urls)}] {il}: {len(recs)} okul")
        except Exception as e:
            print(f"  [{i}/{len(urls)}] HATA {u}: {e}")
        time.sleep(0.5)
    (DATA / "lgs_liseler.json").write_text(
        json.dumps(all_schools, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    meta = {"kaynak": "kazanabilirsin.com (MEB 2025 LGS yerleştirme derlemesi)",
            "yil": 2025, "toplam_okul": len(all_schools), "il_sayisi": len(il_count)}
    (DATA / "lgs_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nTOPLAM: {len(all_schools)} okul, {len(il_count)} il → data/lgs_liseler.json")


if __name__ == "__main__":
    main()
