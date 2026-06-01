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
        out.append({"kod": r["kod"], "kurum": kurum.strip(), "dal": dal.strip() or kurum.strip(),
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


# Çok-yıllık trend için resmî ÖSYM 'En Küçük ve En Büyük Puanlar' PDF'leri (sınav → {yıl: URL}).
# Geçmiş yıllar program/kadro KODU ile eşleştirilir (kod yıllar arası büyük oranda stabildir).
# TUS/DUS: aynı dönem (1. dönem) yıllar arası karşılaştırılır.
HIST_URLS = {
    "dgs": {
        2024: "https://dokuman.osym.gov.tr/pdfdokuman/2024/DGS/TERCIH/minmax27092024.pdf",
        2023: "https://dokuman.osym.gov.tr/pdfdokuman/2023/DGS/TERCIH/minmax11092023.pdf",
    },
    "tus": {
        2024: "https://dokuman.osym.gov.tr/pdfdokuman/2024/TUSDONEM-1/TERCIH/minmax_td03062024.pdf",
        2023: "https://dokuman.osym.gov.tr/pdfdokuman/2023/TUSDONEM1/TERCIH/minmax16062023.pdf",
    },
    "dus": {
        2024: "https://dokuman.osym.gov.tr/pdfdokuman/2024/DUSDONEM-1/TERCIH/minmax03072024.pdf",
        2023: "https://dokuman.osym.gov.tr/pdfdokuman/2023/DUSDONEM-1/TERCIH/minmaxd15082023.pdf",
    },
}


def _mkey(s):
    """İsim eşleştirme anahtarı: Türkçe i/I/ı/İ birleştir, küçült, sadece alfanümerik.
    (ÖSYM TUS/DUS program KODLARI yıllar arası YENİDEN ATANDIĞI için isimle eşleşilir.)"""
    s = (s or "").replace("İ", "i").replace("I", "i").replace("ı", "i").lower()
    return "".join(ch for ch in s if ch.isalnum())


def _tdkey(kurum, dal, tur):
    return _mkey(kurum) + "|" + _mkey(dal) + "|" + (tur or "")


def taban_map_kod(url):
    """{program_kodu: taban} — kodu STABİL dikeyler için (DGS: üniversite program kodları)."""
    return {r["kod"]: r["min"] for r in parse_rows(fetch_pdf_text(url)) if r["min"] is not None}


def taban_map_name(url):
    """{kurum|dal|tür: taban} — kodu yıllar arası DEĞİŞEN dikeyler için (TUS/DUS)."""
    m = {}
    for r in norm_tus_dus(parse_rows(fetch_pdf_text(url))):
        if r["tp"] is not None:
            m[_tdkey(r["kurum"], r["dal"], r["tur"])] = r["tp"]
    return m


def enrich_history(norm, exam):
    """Mevcut yıl satırlarını önceki yılların tabanıyla zenginleştir (tp24, tp23).
    DGS kodla (stabil), TUS/DUS isimle (kod yıllar arası değişir) eşleştirilir.
    Bir yıl çekilemezse o yıl atlanır (alan eklenmez); kötü veri build'i bozmaz."""
    by_name = exam in ("tus", "dus")
    keyf = (lambda r: _tdkey(r["kurum"], r["dal"], r["tur"])) if by_name else (lambda r: r["kod"])
    for year, url in HIST_URLS.get(exam, {}).items():
        key = "tp%s" % str(year)[2:]  # 2024→tp24, 2023→tp23
        try:
            m = taban_map_name(url) if by_name else taban_map_kod(url)
            hit = 0
            for r in norm:
                v = m.get(keyf(r))
                if v is not None:
                    r[key] = v
                    hit += 1
            print(f"    {exam.upper()} {year} geçmiş ({'isim' if by_name else 'kod'}): {len(m)} kayıt, {hit} eşleşme → {key}")
        except Exception as e:
            print(f"    {exam.upper()} {year} geçmiş HATA (atlandı): {e}")
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
        enrich_history(norm, exam)  # tp24/tp23 ekle (çok-yıllık trend)
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
