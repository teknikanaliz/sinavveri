#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ÖSYM resmî 'En Küçük ve En Büyük Puanlar' PDF'lerinden taban/tavan puan verisi.
Kaynak: dokuman.osym.gov.tr (resmî). PDF → pdftotext -layout → satır parse (sağdan: kont,yer,boş,min,max).
Çıktı: data/osym_<exam>.json (ham) + sınav bazında normalize alanlar.
"""
import json
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
HDRS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://www.osym.gov.tr/",
    "Accept": "application/pdf,*/*",
}
B = "https://dokuman.osym.gov.tr/pdfdokuman/2025/"

SOURCES = {
    "tus": [B + "TUSDONEM-1/TERCIH/minmax03062025.pdf"],
    "dus": [B + "DUSDONEM-1/TERCIH/minmax_ds1d04072025.pdf"],
    "dgs": [B + "DGS/TERCIH/minmax_dgd08092025.pdf"],
    "kpss": [
        (B + "KPSS/TERCIH1/minmaxlisans23072025.pdf", "Lisans", "2025/1 (Genel)"),
        (B + "KPSS/TERCIH1/minmaxonl23072025.pdf", "Önlisans", "2025/1 (Genel)"),
        (B + "KPSS/TERCIH1/minmaxort23072025.pdf", "Ortaöğretim", "2025/1 (Genel)"),
        (B + "KPSS/TERCIH2/minmaxlisans07012026.pdf", "Lisans", "2025/2 (Genel)"),
        (B + "KPSS/TERCIH2/minmaxonl07012026.pdf", "Önlisans", "2025/2 (Genel)"),
        (B + "KPSS/TERCIH2/minmaxort07012025.pdf", "Ortaöğretim", "2025/2 (Genel)"),
        (B + "KPSS/TERCIH3/minmax_lisans20012025.pdf", "Lisans", "2025/3 (Çevre Bak.)"),
        (B + "KPSS/TERCIH3/minmax_onlisans20012025.pdf", "Önlisans", "2025/3 (Çevre Bak.)"),
        (B + "KPSS/TERCIH3/minmax_ort20012025.pdf", "Ortaöğretim", "2025/3 (Çevre Bak.)"),
        (B + "KPSS/TERCIH4/minmaxlisans_sb4d14052025.pdf", "Lisans", "2025/4 (Sağlık Bak.)"),
        (B + "KPSS/TERCIH4/minmaxonlisans_sb4d14052025.pdf", "Önlisans", "2025/4 (Sağlık Bak.)"),
        (B + "KPSS/TERCIH4/minmaxortaogretim_sb4d14052025.pdf", "Ortaöğretim", "2025/4 (Sağlık Bak.)"),
        (B + "KPSS/TERCIH5/minmax_lisanssb5d14052025.pdf", "Lisans", "2025/5 (Sağlık Bak.)"),
    ],
}


def fetch_pdf_text(url):
    req = urllib.request.Request(url, headers=HDRS)
    data = urllib.request.urlopen(req, timeout=90).read()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(data)
        path = f.name
    out = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True)
    return out.stdout


def num(x):
    if x == "--":
        return None
    if re.fullmatch(r"[\d.]+,\d+", x):
        return round(float(x.replace(".", "").replace(",", ".")), 3)
    if re.fullmatch(r"\d+", x):
        return float(x)
    return "X"


def parse_rows(txt):
    rows = []
    for line in txt.splitlines():
        t = line.split()
        if len(t) < 6 or not re.fullmatch(r"\d{6,10}", t[0]):
            continue
        vmn, vmx = num(t[-2]), num(t[-1])
        if vmn == "X" or vmx == "X":
            continue
        try:
            bos, yer, kont = int(t[-3]), int(t[-4]), int(t[-5])
        except (ValueError, IndexError):
            continue
        rows.append({"kod": t[0], "ad": " ".join(t[1:-5]), "kont": kont, "yer": yer,
                     "min": vmn, "max": vmx})
    return rows


KONT_TUR = ("Genel", "Yabancı Uyruklu", "Yabancı")


def norm_tus_dus(rows):
    out = []
    for r in rows:
        ad = r["ad"]
        tur = "Genel"
        for k in KONT_TUR:
            if ad.endswith(" " + k):
                tur = k
                ad = ad[: -len(k) - 1].strip()
                break
        kurum, dal = (ad.rsplit("/", 1) + [""])[:2] if "/" in ad else (ad, "")
        out.append({"kurum": kurum.strip(), "dal": dal.strip() or kurum.strip(),
                    "tur": tur, "kont": r["kont"], "yer": r["yer"], "tp": r["min"], "tavan": r["max"]})
    return out


def norm_dgs(rows):
    out = []
    for r in rows:
        ad = r["ad"]
        # "Üniversite ... Fakültesi / BÖLÜM (puan türü)" — son '/' bölüm
        uni, bol = (ad.rsplit("/", 1) + [""])[:2] if "/" in ad else (ad, "")
        out.append({"kod": r["kod"], "uni": uni.strip(), "bolum": bol.strip() or uni.strip(),
                    "kont": r["kont"], "yer": r["yer"], "tp": r["min"], "tavan": r["max"]})
    return out


# DGS çok-yıllık trend için resmî ÖSYM 'En Küçük ve En Büyük Puanlar' PDF'leri (yıl → URL).
# Geçmiş yıllar program KODU ile eşleştirilir (kod yıllar arası büyük oranda stabildir).
DGS_HIST_URLS = {
    2024: "https://dokuman.osym.gov.tr/pdfdokuman/2024/DGS/TERCIH/minmax27092024.pdf",
    2023: "https://dokuman.osym.gov.tr/pdfdokuman/2023/DGS/TERCIH/minmax11092023.pdf",
}


def dgs_taban_map(url):
    """Bir yılın DGS PDF'inden {program_kodu: taban_puan} haritası."""
    m = {}
    for r in parse_rows(fetch_pdf_text(url)):
        if r["min"] is not None:
            m[r["kod"]] = r["min"]
    return m


def enrich_dgs_history(norm):
    """2025 DGS satırlarını önceki yılların tabanıyla zenginleştir (tp24, tp23).
    Bir yıl çekilemezse o yıl atlanır (alan eklenmez); kötü veri build'i bozmaz."""
    for year, url in DGS_HIST_URLS.items():
        key = "tp%s" % str(year)[2:]  # 2024→tp24, 2023→tp23
        try:
            m = dgs_taban_map(url)
            hit = 0
            for r in norm:
                v = m.get(r["kod"])
                if v is not None:
                    r[key] = v
                    hit += 1
            print(f"    DGS {year} geçmiş: {len(m)} kayıt, {hit} eşleşme → {key}")
        except Exception as e:
            print(f"    DGS {year} geçmiş HATA (atlandı): {e}")
    return norm


def norm_kpss(rows, duzey, donem):
    out = []
    for r in rows:
        ad = r["ad"]
        parts = [p.strip() for p in ad.split("/")]
        kurum = parts[0] if parts else ad
        il = ""
        kadro = ""
        if len(parts) >= 2:
            il = parts[-2].strip()
            tail = parts[-1].strip()  # "TAŞRA HEMŞİRE" / "MERKEZ AVUKAT"
            m = re.match(r"^(TAŞRA|MERKEZ|YURTDIŞI)\s+(.*)$", tail)
            kadro = m.group(2).strip() if m else tail
        out.append({"kurum": kurum, "il": il.title(), "kadro": kadro, "duzey": duzey, "donem": donem,
                    "kont": r["kont"], "yer": r["yer"], "tp": r["min"], "tavan": r["max"]})
    return out


def main():
    # TUS
    for exam in ("tus", "dus", "dgs"):
        url = SOURCES[exam][0]
        print(f"  {exam.upper()}: {url.split('/')[-1]}")
        rows = parse_rows(fetch_pdf_text(url))
        norm = norm_tus_dus(rows) if exam in ("tus", "dus") else norm_dgs(rows)
        if exam == "dgs":
            enrich_dgs_history(norm)  # tp24/tp23 ekle (çok-yıllık trend)
        withp = [x for x in norm if x["tp"]]
        (DATA / f"osym_{exam}.json").write_text(
            json.dumps(norm, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"    {len(norm)} satır, {len(withp)} puanlı → osym_{exam}.json")

    # KPSS (çok dosya birleşik)
    kpss = []
    for url, duzey, donem in SOURCES["kpss"]:
        print(f"  KPSS {donem} {duzey}: {url.split('/')[-1]}")
        try:
            rows = parse_rows(fetch_pdf_text(url))
            kpss.extend(norm_kpss(rows, duzey, donem))
            print(f"    +{len(rows)}")
        except Exception as e:
            print(f"    HATA: {e}")
    (DATA / "osym_kpss.json").write_text(
        json.dumps(kpss, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  KPSS toplam: {len(kpss)} kadro → osym_kpss.json")
    (DATA / "osym_meta.json").write_text(json.dumps(
        {"kaynak": "ÖSYM 2025 'En Küçük ve En Büyük Puanlar' (resmî, dokuman.osym.gov.tr)", "yil": 2025},
        ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
