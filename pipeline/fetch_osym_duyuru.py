#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ÖSYM duyuru listesi çekici — kaynak: https://www.osym.gov.tr/Duyurular/Index

NEDEN regex/stdlib: Sayfa sunucu-render HTML (JS gerekmez), robots.txt boş ve tüm
duyurular TEK sayfada (~322 kayıt) geliyor. Bu yüzden ne headless browser ne de
harici parser bağımlılığı gerekli; salt `urllib` + `re` yeterli ve kırılgan
bağımlılık eklemiyor.

Kalıp (2026-08 itibarıyla doğrulandı):
    <a class="duyuru-list-item" href="/slug" data-search-text="... 02.08.2026 ...">
        <div class="duyuru-list-date">
            <span class="duyuru-list-day">2</span>
            <span class="duyuru-list-my">Ağustos 2026</span>
        <div class="duyuru-list-body">
            <span class="duyuru-list-title">2026-ALES/2: ... Yayımlandı</span>

Çıktı: data/osym_duyurular.json
    {"guncelleme": ISO, "kaynak": "ÖSYM", "duyurular": [...]}

ARŞİV MANTIĞI (NEDEN): ÖSYM eski duyuruları listeden düşürüyor. Dosyanın üzerine
yazmak arşivi siler; bu yüzden mevcut kayıtlar `url` anahtarıyla BİRLEŞTİRİLİR —
yeni gelen eklenir, mevcut olan güncellenir, listeden düşen KORUNUR.

Kullanım:
    python3 -m pipeline.fetch_osym_duyuru [--limit N] [--dry-run]
"""
import argparse
import html as htmlmod
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "osym_duyurular.json"

BASE = "https://www.osym.gov.tr"
INDEX = BASE + "/Duyurular/Index"
# NEDEN gerçekçi UA: ÖSYM bazı bot UA'larını 403'lüyor; tarayıcı UA'sı ile 200 doğrulandı.
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
TIMEOUT = 25
RETRY = 3

# --- Türkçe ay adları -------------------------------------------------------
# NEDEN hem tam hem kısa ad: liste sayfası tam ad ("Ağustos") kullanıyor, ama
# ÖSYM metinlerinde kısaltma da geçebiliyor. Anahtarlar Türkçe-güvenli
# küçültme (_tr_lower) sonrası halleriyle tutulur.
AYLAR = {
    "ocak": 1, "oca": 1,
    "şubat": 2, "şub": 2, "subat": 2,
    "mart": 3, "mar": 3,
    "nisan": 4, "nis": 4,
    "mayıs": 5, "may": 5, "mayis": 5,
    "haziran": 6, "haz": 6,
    "temmuz": 7, "tem": 7,
    "ağustos": 8, "ağu": 8, "agustos": 8, "agu": 8,
    "eylül": 9, "eyl": 9, "eylul": 9,
    "ekim": 10, "eki": 10,
    "kasım": 11, "kas": 11, "kasim": 11,
    "aralık": 12, "ara": 12, "aralik": 12,
}


def _tr_lower(s: str) -> str:
    """Türkçe-güvenli küçültme.

    NEDEN: Python'un str.lower()'ı "I" → "i" ve "İ" → "i̇" (birleşik nokta)
    üretir. "AĞUSTOS".lower() sorunsuzdur ama "İSTANBUL"/"KILAVUZ" gibi
    metinlerde eşleşme bozulur. Önce İ→i, I→ı map'leyip sonra lower() çağırmak
    hem ay adlarını hem başlık kalıplarını güvenilir eşleştirir.
    """
    return s.replace("İ", "i").replace("I", "ı").lower()


# --- Sınav kodu tespiti -----------------------------------------------------
# NEDEN sıralı liste (dict değil): daha uzun/özel kod önce denenmeli.
# "e-YDS" içindeki "YDS" ve "YÖKDİL" içindeki "YDS" gibi tuzaklar var.
# "YDUS" içindeki "DUS" ise harf-lookbehind ile zaten elenir (Y bir harf).
SINAV_KODLARI = [
    # Bileşik/özel kodlar ÖNCE gelir: "MEB-AGS" içinde "AGS" de eşleşir, "AGS" listede
    # sonra olsa bile ilk-eşleşen-kazanır kuralı (sinav_bul) yüzünden MEB-AGS'i AGS'ye
    # indirgemesin diye MEB-AGS önce denenir. (2026-08-04, 103 kayıtta sınav="—" bulununca eklendi)
    ("MEB-AGS", r"meb-?ags"),
    ("MEB-EKYS", r"meb-?ekys"),
    ("e-YDS", r"e-?yds"),
    ("e-YDTS", r"e-?ydts"),
    ("e-TEP", r"e-?tep"),
    ("YÖKDİL", r"yökdil|yokdil"),
    ("YDUS", r"ydus"),
    ("DHBT", r"dhbt"),
    ("ALES", r"ales"),
    ("KPSS", r"kpss"),
    ("EKPSS", r"ekpss"),
    ("DGS", r"dgs"),
    ("TUS", r"tus"),
    ("DUS", r"dus"),
    ("YDS", r"yds"),
    ("MSÜ", r"msü|msu"),
    ("LGS", r"lgs"),
    ("STS", r"sts"),
    ("YKS", r"yks"),
    ("TYT", r"tyt"),
    ("AYT", r"ayt"),
    ("YDT", r"ydt"),
    ("AGS", r"ags"),
    ("ÖABT", r"öabt"),
    ("ÖZYES", r"özyes"),
    ("TR-YÖS", r"tr-?yös|tr-?yos"),
    ("HMGS", r"hmgs"),
    ("MBSTS", r"mbsts"),
    ("Kaymakamlık", r"kaymakamlık"),
    ("Adalet Bakanlığı Sınavları", r"adalet bakanlığı"),
    ("ÖSYM Uzman Yardımcılığı", r"uzman yardımcılığı"),
    ("GUY", r"guy"),
    ("BKUBTS", r"bkubts"),
    ("İSG", r"isg"),
    ("CBRY", r"cbry"),
    ("Sayıştay", r"sayıştay"),
    ("ÖSYM Sözleşmeli Bilişim Personeli", r"sözleşmeli bilişim personeli"),
]
# NEDEN özel sınır sınıfı: \b Türkçe harfleri (ı, ğ, ü…) kelime karakteri sayar
# ama emin olmak için sınırı açıkça "Türkçe dahil harf DEĞİL" diye tanımlıyoruz.
HARF = "A-Za-zÇĞİÖŞÜçğıöşü"
SINAV_RE = [
    (kod, re.compile(rf"(?<![{HARF}])(?:{pat})(?![{HARF}])"))
    for kod, pat in SINAV_KODLARI
]

# --- Duyuru tipi sınıflandırması --------------------------------------------
# NEDEN sıralı (ilk eşleşen kazanır): bir başlık birden çok kalıba uyabilir
# (ör. "Yerleştirme Sonuçları Açıklandı"). Sıra, göreve verilen listeyle birebir
# aynıdır; böylece sınıflandırma tahmin edilebilir kalır.
TIPLER = [
    ("sonuc_aciklandi", r"sonu[çc]lar[ıi]?\s+a[çc][ıi]kland[ıi]"),
    ("yerlestirme", r"yerle[şs]tirme\s+sonu[çc]lar[ıi]"),
    ("tercih", r"tercihlerin\s+al[ıi]nmas[ıi]|tercih\s+k[ıi]lavuzu"),
    ("kilavuz", r"k[ıi]lavuz|kontenjan"),
    ("basvuru", r"ba[şs]vuru"),
    ("giris_belgesi", r"s[ıi]nava\s+giri[şs]\s+belgeler[ıi]"),
    ("cevap_anahtari", r"cevap\s+anahtar[ıi]|soru\s+kitap[çc][ıi][ğg][ıi]"),
]
TIP_RE = [(ad, re.compile(pat)) for ad, pat in TIPLER]

# --- HTML kalıpları ---------------------------------------------------------
ITEM_RE = re.compile(
    r'<a\s+class="duyuru-list-item"\s+href="([^"]+)"(.*?)</a>',
    re.S | re.I,
)
DAY_RE = re.compile(r'<span class="duyuru-list-day">\s*(\d{1,2})\s*</span>', re.I)
MY_RE = re.compile(r'<span class="duyuru-list-my">\s*([^<]+?)\s*</span>', re.I)
TITLE_RE = re.compile(r'<span class="duyuru-list-title">\s*(.*?)\s*</span>', re.S | re.I)
SEARCHTEXT_RE = re.compile(r'data-search-text="([^"]*)"', re.I)
NUMERIC_DATE_RE = re.compile(r"\b(\d{2})\.(\d{2})\.(\d{4})\b")


def fetch(url: str) -> str:
    """Sayfayı çek: 3 deneme, artan bekleme (2s, 4s, 8s)."""
    son_hata = None
    for deneme in range(1, RETRY + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read().decode("utf-8", "ignore")
        except (urllib.error.URLError, OSError) as e:
            son_hata = e
            if deneme < RETRY:
                bekle = 2 ** deneme  # 2, 4 → artan bekleme
                print(f"  ! deneme {deneme}/{RETRY} başarısız ({e}); {bekle}s bekleniyor")
                time.sleep(bekle)
    raise RuntimeError(f"{url} çekilemedi ({RETRY} deneme): {son_hata}")


def temiz(s: str) -> str:
    """HTML etiketlerini/entity'lerini temizle, boşlukları tekle."""
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmlmod.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def tarih_iso(gun: str, ay_yil: str, fallback_text: str = "") -> str | None:
    """'2' + 'Ağustos 2026' → '2026-08-02'.

    NEDEN fallback: data-search-text içinde ayrıca 'DD.MM.YYYY' sayısal tarih var.
    Ay adı beklenmedik biçimde gelirse (yazım değişikliği, yeni kısaltma) sayısal
    tarihe düşerek veri kaybını önlüyoruz.
    """
    m = re.match(r"([^\s]+)\s+(\d{4})$", ay_yil.strip())
    if m:
        ay = AYLAR.get(_tr_lower(m.group(1)))
        if ay:
            try:
                return datetime(int(m.group(2)), ay, int(gun)).date().isoformat()
            except ValueError:
                pass  # geçersiz gün (ör. 31 Nisan) → fallback dene
    n = NUMERIC_DATE_RE.search(fallback_text)
    if n:
        try:
            return datetime(int(n.group(3)), int(n.group(2)), int(n.group(1))).date().isoformat()
        except ValueError:
            return None
    return None


def sinav_bul(baslik: str) -> str | None:
    """Başlıkta geçen sınav kodunu döndür; yoksa None."""
    low = _tr_lower(baslik)
    for kod, rx in SINAV_RE:
        if rx.search(low):
            return kod
    return None


def tip_bul(baslik: str) -> str:
    """Başlık kalıbından duyuru tipini belirle (ilk eşleşen kazanır)."""
    low = _tr_lower(baslik)
    for ad, rx in TIP_RE:
        if rx.search(low):
            return ad
    return "diger"


def parse(sayfa: str, limit: int | None = None) -> list[dict]:
    """HTML'den duyuru kayıtlarını çıkar."""
    kayitlar = []
    for href, govde in ITEM_RE.findall(sayfa):
        t = TITLE_RE.search(govde)
        if not t:
            continue
        baslik = temiz(t.group(1))
        if not baslik:
            continue
        st = SEARCHTEXT_RE.search(govde)
        search_text = htmlmod.unescape(st.group(1)) if st else ""
        d, my = DAY_RE.search(govde), MY_RE.search(govde)
        tarih = tarih_iso(
            d.group(1) if d else "",
            htmlmod.unescape(my.group(1)) if my else "",
            search_text,
        )
        slug = href.split("?")[0].strip("/")
        kayitlar.append({
            "tarih": tarih,
            "baslik": baslik,
            "url": href if href.startswith("http") else BASE + "/" + slug,
            "slug": slug,
            "sinav": sinav_bul(baslik),
            "tip": tip_bul(baslik),
        })
        if limit and len(kayitlar) >= limit:
            break
    return kayitlar


def mevcut_cikti() -> dict | None:
    """Diskteki mevcut çıktıyı ham haliyle döndür (yoksa/bozuksa None).
    birlestir()'den AYRI okur — o kendi kopyasını mutasyona uğrattığı için
    karşılaştırmada dokunulmamış bir referans gerekir."""
    if not OUT.exists():
        return None
    try:
        return json.loads(OUT.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def birlestir(yeni: list[dict]) -> tuple[list[dict], int, int, list[dict]]:
    """Mevcut arşivle birleştir (url anahtarı). → (liste, eklenen, guncellenen, yeni_kayitlar)
    yeni_kayitlar: bu koşuda GERÇEKTEN ilk kez görülen kayıtlar (push bildirimi tetiklemek için —
    "güncellenen" değil, arşivde hiç olmayan)."""
    mevcut: dict[str, dict] = {}
    if OUT.exists():
        try:
            eski = json.loads(OUT.read_text(encoding="utf-8"))
            for k in eski.get("duyurular", []):
                if k.get("url"):
                    mevcut[k["url"]] = k
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ! mevcut dosya okunamadı, sıfırdan yazılacak: {e}")

    eklenen = guncellenen = 0
    yeni_kayitlar = []
    for k in yeni:
        if k["url"] in mevcut:
            # NEDEN update(): eski kayıtta elle/başka scriptle eklenmiş ek alanlar
            # varsa korunur, yalnız bizim ürettiğimiz alanlar tazelenir.
            if mevcut[k["url"]] != {**mevcut[k["url"]], **k}:
                guncellenen += 1
            mevcut[k["url"]].update(k)
        else:
            mevcut[k["url"]] = k
            eklenen += 1
            yeni_kayitlar.append(k)

    # Tarihe göre yeniden sırala: yeni → eski. Tarihsizler en sona.
    # NEDEN ikincil anahtar slug: aynı tarihli kayıtlarda sıra deterministik kalsın
    # (idempotent çıktı → gereksiz git diff'i olmaz).
    liste = sorted(
        mevcut.values(),
        key=lambda k: (k.get("tarih") or "0000-00-00", k.get("slug") or ""),
        reverse=True,
    )
    return liste, eklenen, guncellenen, yeni_kayitlar


def push_bildir(yeni_kayitlar: list[dict]) -> None:
    """YENİ "sonuc_aciklandi" duyuruları için push-server'a bildir (server.js kendi içinde
    duyuru_url bazlı idempotent — aynı URL iki kez POST edilse bile ikinci bildirim atlanır).
    NEDEN try/except sarmalı: push-server ayakta değilse (bakım, yeniden başlatma) bu script
    YİNE DE veri dosyasını yazmalı — bildirim ikincil, veri birincil."""
    import os
    import urllib.error
    import urllib.request

    secret = os.environ.get("SINAVVERI_PUSH_SECRET", "")
    if not secret:
        return  # env yoksa (yerel geliştirme) sessizce atla
    sonuclar = [k for k in yeni_kayitlar if k.get("tip") == "sonuc_aciklandi" and k.get("sinav")]
    if not sonuclar:
        return
    for k in sonuclar:
        body = json.dumps({
            "secret": secret, "sinav": k["sinav"], "baslik": k["baslik"], "duyuru_url": k["url"],
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:3032/api/push/sonuc-aciklandi", data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                print(f"  🔔 push: {k['sinav']} — {json.loads(r.read())}")
        except (urllib.error.URLError, OSError) as e:
            print(f"  ! push-server'a ulaşılamadı ({k['sinav']}): {e}")


def main() -> None:
    ap = argparse.ArgumentParser(description="ÖSYM duyurularını çek → data/osym_duyurular.json")
    ap.add_argument("--limit", type=int, default=None, help="En fazla N duyuru işle")
    ap.add_argument("--dry-run", action="store_true", help="Dosyaya yazma, sadece raporla")
    a = ap.parse_args()

    print(f"→ {INDEX} çekiliyor...")
    sayfa = fetch(INDEX)
    yeni = parse(sayfa, a.limit)
    print(f"  {len(yeni)} duyuru ayrıştırıldı ({len(sayfa):,} bayt HTML)")

    tarihsiz = [k for k in yeni if not k["tarih"]]
    if tarihsiz:
        print(f"  ! {len(tarihsiz)} kayıtta tarih çözülemedi: {[k['slug'] for k in tarihsiz][:5]}")

    liste, eklenen, guncellenen, yeni_kayitlar = birlestir(yeni)

    # NEDEN içerik karşılaştırması (2026-09-01): bu iş 30 dakikada bir koşuyor. "guncelleme"
    # damgası her koşuda tazelenince dosya, duyuru listesi BİREBİR AYNIYKEN bile değişmiş
    # görünüyordu → git commit → push → GitHub Actions deploy. Günde 48 gereksiz deploy
    # (~1.400 Actions dk/ay) ücretsiz kotayı bitirdi ve 26-28 Ağustos'ta 11 sitenin
    # deploy'unu birden kilitledi. Damga artık YALNIZ liste gerçekten değişince ilerler;
    # sayfada zaten guncelleme[:10] (yalnız tarih) gösteriliyor, saat kullanılmıyor.
    eski = mevcut_cikti()
    degisti = eski is None or eski.get("duyurular") != liste

    if a.dry_run:
        print(f"[dry-run] yazılmadı — toplam {len(liste)}, yeni {eklenen}, güncellenen {guncellenen}")
    elif not degisti:
        print(f"= içerik aynı — {OUT} yazılmadı, gereksiz commit/deploy önlendi "
              f"(toplam {len(liste)} kayıt, damga {eski.get('guncelleme', '?')})")
    else:
        cikti = {
            "guncelleme": datetime.now().replace(microsecond=0).isoformat(),
            "kaynak": "ÖSYM",
            "duyurular": liste,
        }
        DATA.mkdir(exist_ok=True)
        OUT.write_text(json.dumps(cikti, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"✓ {OUT} → toplam {len(liste)} kayıt (yeni {eklenen}, güncellenen {guncellenen})")
        push_bildir(yeni_kayitlar)

    # Özet dağılımlar (rapor için)
    from collections import Counter
    print("  tip dağılımı :", dict(Counter(k["tip"] for k in liste).most_common()))
    print("  sınav dağılımı:", dict(Counter(k["sinav"] or "—" for k in liste).most_common()))


if __name__ == "__main__":
    main()
