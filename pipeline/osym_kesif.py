#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ÖSYM 'En Küçük ve En Büyük Puanlar' (min-max) PDF'lerini OTOMATİK keşfeder.

NEDEN VAR (2026-08-19 kök-neden düzeltmesi)
-------------------------------------------
`fetch_osym.py` yıllarca URL'leri ELLE sabit yazıyordu. ÖSYM 2026 Temmuz'da URL
kalıbını değiştirdi ve artık **tahmin edilemez rastgele hash** kullanıyor:

    eski : /pdfdokuman/2025/KPSS/TERCIH1/minmaxlisans23072025.pdf
    yeni : /web/2026/7/kpss-20261-...-en-kucuk-ve-en-buyuk-puanlar-lsans-24q42vum.pdf
                                                                    ^^^^^^^^ tahmin edilemez

Ayrıca aşama dizini de değişti (2025 `TUSDONEM-1/TERCIH/` → 2026 `TUSDONEM-1/YERLESTIRME/SB/`).
Yani tarih/kalıp tahminiyle URL üretmek matematiksel olarak imkânsız hâle geldi —
duyuru sayfasından link çıkarmak ZORUNLU.

NASIL ÇALIŞIR
-------------
ÖSYM'nin sınav bazlı "Sayısal Bilgiler" menü sayfaları TEK statik HTML'de 2002'den
bugüne o sınavın TÜM min-max duyurularını listeler (yıl filtresi client-side JS).
Akış:  menü sayfası → yıl+başlık filtresiyle duyuru slug'ları → her duyuru sayfasından
       dokuman.osym.gov.tr PDF linkleri → ele/filtrele → HEAD ile 200+pdf doğrula.

KAYNAK SİCİLİ (data/osym_kaynaklar.json)
----------------------------------------
Keşfedilen URL'ler kalıcı bir sicile YAZILIR ve oradan okunur. Böylece:
  · ÖSYM sayfası geçici olarak erişilemezse en son bilinen iyi URL'ler kullanılır,
  · geçmiş yıllar birikir (çok-yıllık trend elle yazılmak zorunda kalmaz),
  · keşif hiçbir şey bulamazsa ESKİ veri korunur (sessiz gerileme olmaz).

Kullanım:
    python3 -m pipeline.osym_kesif                 # cari yılı keşfet + sicile işle
    python3 -m pipeline.osym_kesif --yil 2026      # belirli yıl
    python3 -m pipeline.osym_kesif --dry-run       # yalnız raporla, yazma
"""
import argparse
import json
import re
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SICIL = ROOT / "data" / "osym_kaynaklar.json"
BASE = "https://www.osym.gov.tr"
HDRS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Referer": "https://www.osym.gov.tr/",
}
TIMEOUT = 60
RETRY = 3

# Sınav → "Sayısal Bilgiler" menü sayfası id'leri (birden çok dönem ayrı sayfada).
SB_MENU = {
    "tus": [878, 896],      # 1. Dönem · 2. Dönem
    "dus": [1064, 1091],
    "dgs": [767],
    "kpss": [341],
}

# Duyuru slug'ı min-max/sayısal bilgi duyurusu mu?
DUY_RE = re.compile(r"(sayisal-bilgiler|en-kucuk|en-buyuk)", re.I)
# PDF gerçekten min-max tablosu mu? (özet sayısal-bilgi PDF'i, kılavuz, kontenjan tablosu HARİÇ)
PDF_OK = re.compile(r"(minmax|min-max|en-kucuk|en-buyuk)", re.I)
PDF_NO = re.compile(r"(yasakli|sayisalbil|sayisal-bilgiler|kilavuz|kontenjan|ktablo|konttablo)", re.I)
PDF_URL_RE = re.compile(r'https?://dokuman\.osym\.gov\.tr/[^\s"\'<>)]+\.pdf', re.I)

# KPSS düzeyi — URL/slug'dan. SIRA ÖNEMLİ: "onlisans" içinde "lisans" geçer,
# bu yüzden önce ön lisans ve ortaöğretim elenir.
# ⚠ ÖSYM slug'ları Türkçe harfleri düşürüyor: "lsans", "on-lsans", "ortaogretm".
# Bu yüzden 'i' harfleri OPSİYONEL. Sıra önemli: "onlisans" içinde "lisans" geçer.
_DUZEY_SIRA = [
    ("Önlisans", re.compile(r"(on[-_ ]?l[iı]?sans|[_-]onl(?![a-zçğıöşü])|minmaxonl)", re.I)),
    ("Ortaöğretim", re.compile(r"(orta[-_ ]?[oö][gğ]ret[iı]?m|[_-]ort(?![a-zçğıöşü])|minmaxort)", re.I)),
    ("Lisans", re.compile(r"(l[iı]?sans)", re.I)),
]
# Yerleştirmeyi yapan kurum (dönem etiketinin parantezi) — duyuru başlığından.
_KURUM_IPUCU = [
    ("Sağlık Bak.", re.compile(r"sa[gğ]l[iı]k\s*bakan|sb\d+d\d", re.I)),
    ("Çevre Bak.", re.compile(r"[cç]evre.*bakan|[cç]evre\s*[,ş]ehircilik", re.I)),
    ("Adalet Bak.", re.compile(r"adalet\s*bakan", re.I)),
    ("Millî Eğitim Bak.", re.compile(r"mill[iî]\s*e[gğ]it[iı]m", re.I)),
]


def get(url):
    """GET + retry. ÖSYM WAF'ı ilk istekte 403 verebiliyor; tarayıcı UA + Referer şart."""
    son = None
    for deneme in range(1, RETRY + 1):
        try:
            req = urllib.request.Request(url, headers=HDRS)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            son = e
            if deneme < RETRY:
                time.sleep(3 * deneme)
    raise RuntimeError(f"{url} çekilemedi ({RETRY} deneme): {son}")


def dogrula(url):
    """HEAD → (durum_kodu, content_type). 200 + application/pdf beklenir."""
    for deneme in range(1, RETRY + 1):
        try:
            req = urllib.request.Request(url, headers=HDRS, method="HEAD")
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, (r.headers.get("Content-Type") or "")
        except urllib.error.HTTPError as e:
            return e.code, ""
        except Exception:  # noqa: BLE001
            if deneme < RETRY:
                time.sleep(2 * deneme)
    return 0, ""


def _slug_yili(href):
    """Slug'ın İLK 4 haneli token'ı = duyurunun sınav yılı.

    ⚠️ TUZAK: ÖSYM'nin CMS göçü eski duyuru slug'larına zaman damgası ekliyor
    (`/2016tus-sonbahar-...-20260511143508616`). Naif `"2026" in slug` kontrolü bu
    2016 kaydını 2026 sanır. İLK token kuralı bunu engeller; `kpss-20261-...`
    gibi kalıpları da doğru yakalar."""
    m = re.search(r"\d{4}", href)
    return m.group(0) if m else None


def _duzey(metin):
    for ad, rx in _DUZEY_SIRA:
        if rx.search(metin):
            return ad
    return None


def _donem_etiketi(exam, yil, slug, baslik):
    """'2026/1 (Genel)' benzeri dönem etiketi üretir."""
    metin = (baslik or "") + " " + slug
    no = None
    # "kpss-20261-..." / "KPSS-2026/1" → yıla bitişik dönem numarası
    m = re.search(rf"{yil}\s*[/-]?\s*(\d)(?![\d])", slug) or re.search(rf"{yil}\s*[/-]\s*(\d)", baslik or "")
    if m:
        no = m.group(1)
    if not no:
        # "2026-tus-1-donem-...", "1. Dönem", "1.Donem" — ayırıcı serbest
        m = re.search(r"(\d)\s*[-_. ]*\s*d[oö]nem", metin, re.I)
        no = m.group(1) if m else None
    kurum = "Genel"
    for ad, rx in _KURUM_IPUCU:
        if rx.search((baslik or "") + " " + slug):
            kurum = ad
            break
    return f"{yil}/{no} ({kurum})" if no else f"{yil} ({kurum})"


_EK_RE = re.compile(r"(^|[/_-])ek[-_]?(yerlestirme|minmax)|[/_-]ek[/_-]", re.I)
_DAL_RE = re.compile(r"(dal[-_ ]?de[gğ]i[sş]|uzmanlik[-_ ]?dali[-_ ]?degisiklig)", re.I)


def _ek_mi(metin):
    return bool(_EK_RE.search(metin))


def _kayit_tipi(metin):
    """'ana' (asıl yerleştirme) · 'ek' (ek yerleştirme) · 'dal' (uzmanlık dalı değişikliği).
    Taban puanı YALNIZ 'ana' kayıttan alınır; diğerleri tabloyu bozar."""
    if _DAL_RE.search(metin):
        return "dal"
    if _ek_mi(metin):
        return "ek"
    return "ana"


def yeniden_siniflandir():
    """Sicildeki kayıtların duzey/donem/ek/tip alanlarını YENİDEN türetir — ÖSYM'ye
    tekrar gitmeden. Sınıflandırma kuralı düzeltildiğinde kullanılır."""
    sicil = sicil_oku()
    for exam, yillar in sicil.get("kaynaklar", {}).items():
        for yil, lst in yillar.items():
            for b in lst:
                metin = (b.get("duyuru") or "") + " " + b["url"]
                b["duzey"] = _duzey(b["url"]) or _duzey(b.get("duyuru") or "")
                b["donem"] = _donem_etiketi(exam, int(yil), b.get("duyuru") or "", b["url"])
                b["ek"] = _ek_mi(metin)
                b["tip"] = _kayit_tipi(metin)
    sicil_yaz(sicil)
    return sicil


def kesfet(exam, yil):
    """→ [{'url','duzey','donem','duyuru','ek'}] — sınav+yıl için min-max PDF'leri."""
    bulunan, gorulen = [], set()
    for mid in SB_MENU.get(exam, []):
        try:
            sayfa = get(f"{BASE}/SinavGrubu/Menu/{mid}")
        except Exception as e:  # noqa: BLE001
            print(f"    ! menü {mid} okunamadı: {e}")
            continue
        slugs = sorted({h for h in re.findall(r'href="(/[^"]+)"', sayfa)
                        if _slug_yili(h) == str(yil) and DUY_RE.search(h)})
        for s in slugs:
            try:
                d = get(BASE + s)
            except Exception:  # noqa: BLE001
                continue
            bm = re.search(r"<title>(.*?)</title>", d, re.S | re.I)
            baslik = re.sub(r"\s+", " ", bm.group(1)).strip() if bm else ""
            for pdf in sorted(set(PDF_URL_RE.findall(d))):
                if not PDF_OK.search(pdf) or PDF_NO.search(pdf) or pdf in gorulen:
                    continue
                gorulen.add(pdf)
                bulunan.append({
                    "url": pdf,
                    "duzey": _duzey(pdf) or _duzey(baslik),
                    "donem": _donem_etiketi(exam, yil, s, baslik + " " + pdf),
                    "duyuru": s,
                    # ek yerleştirme / dal değişikliği AYRI tutulur — ana yerleştirme
                    # tablosunu ezmemeli (taban puanı ana yerleştirmeden gelir).
                    "ek": _ek_mi(s + " " + pdf),
                    "tip": _kayit_tipi(s + " " + pdf),
                })
    return bulunan


def sicil_oku():
    if SICIL.exists():
        try:
            return json.loads(SICIL.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {"guncelleme": None, "kaynaklar": {}}


def sicil_yaz(sicil):
    sicil["guncelleme"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    SICIL.write_text(json.dumps(sicil, ensure_ascii=False, indent=1), encoding="utf-8")


def guncelle(yillar=None, dogrulama=True, dry_run=False):
    """Verilen yıllar için keşif yapar, DOĞRULANMIŞ URL'leri sicile işler.
    Sicil ADDITIVE'dir: keşif boş dönerse mevcut kayıtlar SİLİNMEZ."""
    bugun = date.today()
    yillar = yillar or [bugun.year]
    sicil = sicil_oku()
    kay = sicil.setdefault("kaynaklar", {})
    ozet = {}
    for exam in SB_MENU:
        for yil in yillar:
            print(f"  → {exam.upper()} {yil} keşfediliyor...", flush=True)
            try:
                bulunan = kesfet(exam, yil)
            except Exception as e:  # noqa: BLE001
                print(f"    ! keşif hatası: {e}")
                continue
            gecerli = []
            for b in bulunan:
                if dogrulama:
                    kod, ct = dogrula(b["url"])
                    if kod != 200 or "pdf" not in ct.lower():
                        print(f"    ✗ {kod} {b['url'].rsplit('/', 1)[-1]}")
                        continue
                gecerli.append(b)
            ozet[f"{exam}/{yil}"] = len(gecerli)
            print(f"    ✓ {len(gecerli)} doğrulanmış min-max PDF")
            if gecerli:
                kay.setdefault(exam, {})[str(yil)] = gecerli
    if not dry_run:
        sicil_yaz(sicil)
        print(f"\n  sicil → {SICIL.relative_to(ROOT)}")
    return ozet


def kaynaklar(exam, yil):
    """Sicilden (exam, yıl) min-max kayıtlarını döndürür — fetch_osym.py bunu kullanır."""
    return sicil_oku().get("kaynaklar", {}).get(exam, {}).get(str(yil), [])


def ana_kayitlar(exam, yil):
    """(exam, yıl) için YALNIZ ana yerleştirme kayıtları — ek/dal değişikliği hariç.
    TUS/DUS'ta birden çok dönem varsa 1. dönem öne alınır (site 1. dönemi gösteriyor)."""
    kay = [b for b in kaynaklar(exam, yil) if b.get("tip", "ana") == "ana"]
    if exam in ("tus", "dus"):
        d1 = [b for b in kay if "/1 " in (b.get("donem") or "") or "1. Dönem" in (b.get("duyuru") or "")]
        return d1 or kay
    return kay


def en_son_yil(exam, azami=None):
    """Sicilde o sınav için veri bulunan EN YENİ yıl. DGS gibi henüz yerleştirmesi
    yapılmamış sınavlarda otomatik olarak bir önceki yıla düşmeyi sağlar."""
    y = sicil_oku().get("kaynaklar", {}).get(exam, {})
    yillar = sorted((int(k) for k in y if str(k).isdigit()), reverse=True)
    if azami:
        yillar = [x for x in yillar if x <= azami]
    return yillar[0] if yillar else None


def main():
    ap = argparse.ArgumentParser(description="ÖSYM min-max PDF keşfi")
    ap.add_argument("--yil", type=int, action="append", help="keşfedilecek yıl (birden çok kez verilebilir)")
    ap.add_argument("--geriye", type=int, default=0, help="cari yıldan kaç yıl geriye de bakılsın")
    ap.add_argument("--dry-run", action="store_true", help="yalnız raporla, sicile yazma")
    ap.add_argument("--dogrulama-yok", action="store_true", help="HEAD doğrulamasını atla (hızlı)")
    a = ap.parse_args()
    yillar = a.yil or [date.today().year - k for k in range(a.geriye + 1)]
    print(f"ÖSYM min-max keşfi — yıllar: {sorted(yillar, reverse=True)}")
    ozet = guncelle(yillar, dogrulama=not a.dogrulama_yok, dry_run=a.dry_run)
    print("\n=== ÖZET ===")
    for k, v in sorted(ozet.items()):
        print(f"  {k}: {v} PDF")


if __name__ == "__main__":
    main()
