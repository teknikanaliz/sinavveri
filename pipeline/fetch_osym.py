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


def _kurum_core(kurum):
    """Kurum adını çekirdeğe indir: parantez (şehir) at, 'T.C. Sağlık Bakanlığı' önekini at,
    virgül varsa son birimi al. 2025 'T.C. SB Adana Şehir Hast. (ADANA)' ↔ 2024 'Adana Şehir Hast.'"""
    s = re.sub(r"\([^)]*\)", " ", kurum or "")
    s = s.replace("T.C. Sağlık Bakanlığı", " ").replace("T.C.", " ")
    if "," in s:
        s = s.rsplit(",", 1)[-1]
    return _mkey(s)


def _corekey(kurum, dal, tur):
    return _kurum_core(kurum) + "|" + _mkey(dal) + "|" + (tur or "")


# ÖSYM kontenjan tablosu (kadro türü = ÜNİ/SBA/EAH/MSB/… kod ile). Aynı kurum+dal'da
# birden çok program ayrımı buradan gelir. Kod yıl-içinde UNIQUE → güvenli join.
CUR_YEAR = 2025
KONT_URLS = {
    "tus": {
        2025: "https://dokuman.osym.gov.tr/pdfdokuman/2025/TUSDONEM-1/TERCIH/konttablo_ts1d21052025.pdf",
        2024: "https://dokuman.osym.gov.tr/pdfdokuman/2024/TUSDONEM-1/TERCIH/okontenjan_20052024.pdf",
        2023: "https://dokuman.osym.gov.tr/pdfdokuman/2023/TUSDONEM1/TERCIH/kontenjanlar01062023.pdf",
    },
    "dus": {
        2025: "https://dokuman.osym.gov.tr/pdfdokuman/2025/DUSDONEM-1/TERCIH/konttablo25062025.pdf",
    },
}
VALID_KADRO = {"ÜNİ", "SBA", "EAH", "YBU", "KKTC", "MSB", "MAP", "BNDH", "ADL", "İÇB", "JAN", "DAP"}


def kadro_map(url):
    """{program_kodu: kadro_türü} — kontenjan tablosundan. Satır: 'kod T KADRO İL kurum dal …'.
    İl adını kadro sanmamak için ilk birkaç token içinde bilinen kadro kümesinden arar."""
    m = {}
    for ln in fetch_pdf_text(url).splitlines():
        t = ln.split()
        if t and re.fullmatch(r"\d{9,10}", t[0]):
            for tok in t[1:6]:
                if tok in VALID_KADRO:
                    m[t[0]] = tok
                    break
    return m


def taban_map_kod(url):
    """{program_kodu: taban} — kodu STABİL dikeyler için (DGS: üniversite program kodları)."""
    return {r["kod"]: r["min"] for r in parse_rows(fetch_pdf_text(url)) if r["min"] is not None}


def taban_maps_name(url):
    """(full, core) iki harita döndür. full: tam isim anahtarı. core: çekirdek kurum anahtarı —
    aynı çekirdeğe DÜŞEN birden çok FARKLI taban varsa o anahtar None (belirsiz → atlanır, yanlış eşleşme yok)."""
    full = {}
    core_seen = {}
    for r in norm_tus_dus(parse_rows(fetch_pdf_text(url))):
        if r["tp"] is None:
            continue
        full[_tdkey(r["kurum"], r["dal"], r["tur"])] = r["tp"]
        ck = _corekey(r["kurum"], r["dal"], r["tur"])
        if ck in core_seen:
            if core_seen[ck] != r["tp"]:
                core_seen[ck] = None  # belirsiz
        else:
            core_seen[ck] = r["tp"]
    return full, core_seen


def enrich_history(norm, exam):
    """Mevcut yıl satırlarını önceki yılların tabanıyla zenginleştir (tp24, tp23).
    DGS: kodla (üniversite kodları stabil). TUS/DUS: isim + KADRO TÜRÜ anahtarıyla — ÖSYM
    program kodları yıllar arası yeniden atandığından isimle, aynı kurum+dal'daki SBA/ÜNİ/EAH
    çoklu programlarını ayırmak için kadro türüyle eşleşir (her iki yılda da kont tablosu varsa).
    Belirsiz çekirdek eşleşmeler atlanır; kötü veri build'i bozmaz."""
    if exam == "dgs":
        for year, url in HIST_URLS.get(exam, {}).items():
            key = "tp%s" % str(year)[2:]
            try:
                m = taban_map_kod(url)
                hit = sum(1 for r in norm if _set_if(r, key, m.get(r["kod"])))
                print(f"    DGS {year} geçmiş (kod): {len(m)} kayıt, {hit} eşleşme → {key}")
            except Exception as e:
                print(f"    DGS {year} geçmiş HATA (atlandı): {e}")
        return norm

    # TUS/DUS — katmanlı: 1) isim+kadro (kesin) 2) çekirdek+kadro
    #   3) isim-only / 4) çekirdek-only — yalnız HER İKİ yılda da TEKİL ise (kadrosu değişmiş tek programlar).
    from collections import Counter
    placed = [r for r in norm if r["tp"] is not None]
    cnt_full25 = Counter(_tdkey(r["kurum"], r["dal"], r["tur"]) for r in placed)
    cnt_core25 = Counter(_corekey(r["kurum"], r["dal"], r["tur"]) for r in placed)
    for year, url in HIST_URLS.get(exam, {}).items():
        key = "tp%s" % str(year)[2:]
        use_kadro = CUR_YEAR in KONT_URLS.get(exam, {}) and year in KONT_URLS.get(exam, {})
        try:
            mm = norm_tus_dus(parse_rows(fetch_pdf_text(url)))
            kadY = kadro_map(KONT_URLS[exam][year]) if use_kadro else {}
            fk_kadro, ck_seen, fn_seen, cn_seen = {}, {}, {}, {}
            for r in mm:
                if r["tp"] is None:
                    continue
                fn = _tdkey(r["kurum"], r["dal"], r["tur"])
                cn = _corekey(r["kurum"], r["dal"], r["tur"])
                if use_kadro:
                    kd = kadY.get(r["kod"], "")
                    fk_kadro[fn + "|" + kd] = r["tp"]
                    _accum(ck_seen, cn + "|" + kd, r["tp"])
                _accum(fn_seen, fn, r["tp"])
                _accum(cn_seen, cn, r["tp"])
            hit = exact = fb = 0
            for r in norm:
                if r["tp"] is None:
                    continue
                fn = _tdkey(r["kurum"], r["dal"], r["tur"])
                cn = _corekey(r["kurum"], r["dal"], r["tur"])
                v = None
                if use_kadro:
                    kd = r.get("kadro", "")
                    v = fk_kadro.get(fn + "|" + kd)
                    if v is None:
                        v = ck_seen.get(cn + "|" + kd)
                    if v is not None:
                        exact += 1
                if v is None and cnt_full25[fn] == 1 and fn_seen.get(fn) is not None:
                    v = fn_seen[fn]; fb += 1
                elif v is None and cnt_core25[cn] == 1 and cn_seen.get(cn) is not None:
                    v = cn_seen[cn]; fb += 1
                if _set_if(r, key, v):
                    hit += 1
            print(f"    {exam.upper()} {year} geçmiş ({'isim+kadro' if use_kadro else 'isim'}): "
                  f"{hit} eşleşme ({exact} kadro + {fb} tekil-isim) → {key}")
        except Exception as e:
            print(f"    {exam.upper()} {year} geçmiş HATA (atlandı): {e}")
    return norm


def _accum(d, k, v):
    if k in d:
        if d[k] is not None and d[k] != v:
            d[k] = None
    else:
        d[k] = v


def _set_if(r, key, v):
    if v is not None:
        r[key] = v
        return True
    return False


# KPSS geçmiş (2024) — TÜR-duyarlı: postingler tek-seferlik olduğundan aynı TÜR yerleştirmeyle
# (Genel↔Genel, Sağlık Bak.↔Sağlık Bak.) kurum+il+kadro+düzey isim anahtarıyla eşleşir.
_KB = "https://dokuman.osym.gov.tr/pdfdokuman/2024/KPSS/"
KPSS_HIST = {
    "Genel": [
        (_KB + "TERCIH1/minmaxlisans29072024.pdf", "Lisans"),
        (_KB + "TERCIH1/minmaxonl29072024.pdf", "Önlisans"),
        (_KB + "TERCIH1/minmaxort29072024.pdf", "Ortaöğretim"),
        (_KB + "TERCIH2/minmaxlisans03012025.pdf", "Lisans"),
        (_KB + "TERCIH2/minmaxonl03012025.pdf", "Önlisans"),
        (_KB + "TERCIH2/minmaxort03012025.pdf", "Ortaöğretim"),
    ],
    "Sağlık Bak.": [
        (_KB + "TERCIH5/minmax_lisansdt04032024.pdf", "Lisans"),
        (_KB + "TERCIH5/minmax_onlisansdt04032024.pdf", "Önlisans"),
        (_KB + "TERCIH5/minmax_ortaogretimdt04032024.pdf", "Ortaöğretim"),
    ],
}


def _kpss_key(r):
    return _mkey(r["kurum"]) + "|" + _mkey(r.get("il", "")) + "|" + _mkey(r["kadro"]) + "|" + (r["duzey"] or "")


def enrich_kpss_history(kpss):
    """2025 KPSS satırlarına tp24 ekle (aynı tür 2024 yerleştirmesiyle isim eşleşmesi)."""
    maps = {}
    for typ, urls in KPSS_HIST.items():
        m = {}
        for url, duz in urls:
            try:
                for r in norm_kpss(parse_rows(fetch_pdf_text(url)), duz, "2024"):
                    if r["tp"] is not None:
                        m[_kpss_key(r)] = r["tp"]
            except Exception as e:
                print(f"    KPSS 2024 {typ} HATA: {url.split('/')[-1]} {e}")
        maps[typ] = m
        print(f"    KPSS 2024 {typ}: {len(m)} kadro")
    hit = 0
    for r in kpss:
        m = re.search(r"\(([^)]+)\)", r.get("donem", ""))
        mp = maps.get(m.group(1) if m else "")
        if mp:
            v = mp.get(_kpss_key(r))
            if v is not None:
                r["tp24"] = v
                hit += 1
    print(f"    KPSS tp24 eşleşme: {hit}/{len(kpss)} (%{100*hit//len(kpss) if kpss else 0})")
    return kpss


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
        if exam in ("tus", "dus") and CUR_YEAR in KONT_URLS.get(exam, {}):
            try:
                kad = kadro_map(KONT_URLS[exam][CUR_YEAR])
                for r in norm:
                    r["kadro"] = kad.get(r["kod"], "")
                print(f"    {exam.upper()} kadro türü: {sum(1 for r in norm if r.get('kadro'))}/{len(norm)} eşleşti")
            except Exception as e:
                print(f"    {exam.upper()} kadro HATA (atlandı): {e}")
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
    enrich_kpss_history(kpss)  # tp24 (tür-duyarlı 2024 eşleşmesi)
    (DATA / "osym_kpss.json").write_text(
        json.dumps(kpss, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  KPSS toplam: {len(kpss)} kadro → osym_kpss.json")
    (DATA / "osym_meta.json").write_text(json.dumps(
        {"kaynak": "ÖSYM 2025 'En Küçük ve En Büyük Puanlar' (resmî, dokuman.osym.gov.tr)", "yil": 2025},
        ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
