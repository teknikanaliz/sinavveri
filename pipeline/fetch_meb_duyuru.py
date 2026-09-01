#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MEB (Millî Eğitim Bakanlığı) LGS duyuru listesi çekici — kaynak: ÖDSGM
(Ölçme, Değerlendirme ve Sınav Hizmetleri Genel Müdürlüğü) "Haberler" akışı
https://odsgm.meb.gov.tr/www/haberler/kategori/1

NEDEN ÖSYM'nin AKSİNE ÖDSGM: LGS, ÖSYM'nin değil MEB'in sınavıdır — MEB içinde
bunu hazırlayan/uygulayan/sonuçlandıran resmî birim ÖDSGM'dir. www.meb.gov.tr'nin
genel "Duyurular" sayfası (meb_duyuruindex.php, kategori=4) ARAŞTIRILDI — tüm-tarih
LGS araması sadece 1 eski (2023) kayıt döndürdü; yani bakanlığın genel duyuru panosu
LGS için pratikte BOŞ. Buna karşılık ÖDSGM'nin "Haberler" (kategori=1) akışı
2015'ten bugüne LGS'nin TÜM yaşam döngüsünü kapsıyor: kılavuz, başvuru, giriş
bilgileri, soru kitapçığı/cevap anahtarı, sonuç açıklanması, "tercih ve yerleştirme
kılavuzu", nakil sonuçları. 2026-08-04 itibarıyla 827 toplam ÖDSGM haberinden 105'i
LGS ile ilgili (bkz. LGS_RE — "lgs" veya "ortaöğretime geçiş" veya "...ortaöğretim
kurumlarına ilişkin merkezî sınav", LGS'nin resmî/tarihsel adları; "İlköğretim ve
Ortaöğretim Kurumları Bursluluk Sınavı" gibi alakasız ortaöğretim kayıtları bilinçli
olarak regex dışında kalır — doğrulandı, 34 böyle kayıt hiçbiri yanlış eşleşmedi).

www.meb.gov.tr'nin GENEL haber akışında (kategori boş, ~2400 kayıt) ayrıca birkaç
günü-gününe hatırlatma haberi de var (ör. "LGS TERCİH SÜRECİ BAŞLADI") ama bu akış
bilinçli olarak DIŞARIDA bırakıldı: (a) devasa oranda LGS'siz bakanlık haberiyle
gürültülü (binlerce sayfa gerektirir), (b) sunucu-taraflı arama parametresi (DataTables
"search[value]") HTTP 500 döndürüyor (muhtemelen backend bug — boş search çalışıyor,
dolu search'te tutarlı şekilde patlıyor; test edildi). ÖDSGM akışı tek başına
kılavuz+sonuç+tercih dönüm noktalarının hepsini zaten kapsadığından bu risk/karmaşıklığa
değmiyor.

NEDEN JSON/POST (regex/HTML parse değil): ÖDSGM sayfası DataTables sunucu-taraflı
("serverSide": true) JS ile /www/icerik_listele_ajax.php'ye POST ediyor ve TEMİZ JSON
döndürüyor ({"data":[{"BASLIK","ISLEMSAAT","LINK"}], "recordsTotal", ...}) — kırılgan
HTML regex yerine bu (resmî belgelenmemiş ama stabil) JSON API'yi doğrudan kullanmak
hem daha güvenilir hem daha az kod. robots.txt (odsgm.meb.gov.tr) yalnızca isimlendirilmiş
bot/SEO/AI-crawler UA'larını engelliyor (GPTBot, ClaudeBot, AhrefsBot, PerplexityBot vb.)
— genel/isimsiz UA için Disallow YOK; ÖSYM scraper'ıyla aynı gerçekçi Chrome UA kullanılır.

Kalıp (2026-08 itibarıyla doğrulandı):
    POST https://odsgm.meb.gov.tr/www/icerik_listele_ajax.php
    body: draw=1&columns[0][data]=ISLEMSAAT&columns[1][data]=BASLIK&
          columns[2][data]=SIRAID&order[0][column]=2&order[0][dir]=desc&
          start=<N>&length=100&kategori=1&dil=tr
    → {"data":[{"BASLIK":"...","ISLEMSAAT":"DD/MM/YYYY","LINK":"/www/.../icerik/N",
                "TARGET":""}, ...], "recordsTotal": 827, "recordsFiltered": 827}

Çıktı: data/meb_duyurular.json
    {"guncelleme": ISO, "kaynak": "MEB", "duyurular": [...]}
    (ÖSYM'nin data/osym_duyurular.json'ıyla AYNI kayıt şeması: tarih/baslik/url/slug/
    sinav/tip. build.py ikisini okuyup birleştirir — bu yüzden bu script ASLA
    osym_duyurular.json'a yazmaz, kendi ayrı dosyasına yazar.)

ARŞİV MANTIĞI (NEDEN): ÖDSGM sayfalama/sıralamayı değiştirebilir ya da eski haberi
listeden düşürebilir. Dosyanın üzerine yazmak arşivi siler; bu yüzden mevcut kayıtlar
`url` anahtarıyla BİRLEŞTİRİLİR — yeni gelen eklenir, mevcut güncellenir, listeden
düşen KORUNUR (ÖSYM scripti ile birebir aynı mantık).

Kullanım:
    python3 -m pipeline.fetch_meb_duyuru [--limit N] [--dry-run]
"""
import argparse
import html as htmlmod
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "meb_duyurular.json"

BASE = "https://odsgm.meb.gov.tr"
INDEX = BASE + "/www/haberler/kategori/1"  # yalnız Referer/dokümantasyon amaçlı
AJAX = BASE + "/www/icerik_listele_ajax.php"
KATEGORI = "1"  # ÖDSGM "Haberler" (kategori=2 "Duyurular" LGS için neredeyse boş — denendi)
# NEDEN gerçekçi UA: robots.txt yalnız isimlendirilmiş bot UA'larını engelliyor;
# tarayıcı UA'sı ile 200 doğrulandı (ÖSYM scraper'ıyla aynı yaklaşım).
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
TIMEOUT = 25
RETRY = 3
PAGE_SIZE = 100  # ÖDSGM lengthMenu'sündeki azami değer (10/25/50/100)
MAX_PAGES = 40   # güvenlik tavanı (40*100=4000 kayıt) — 2026-08 itibarıyla toplam 827


def _tr_lower(s: str) -> str:
    """Türkçe-güvenli küçültme (fetch_osym_duyuru.py ile birebir aynı NEDEN):
    Python'un str.lower()'ı "I"→"i" ve "İ"→"i̇" (birleşik nokta) üretir; bu da
    Türkçe metinde eşleşmeyi bozar. Önce İ→i, I→ı map'leyip sonra lower()."""
    return s.replace("İ", "i").replace("I", "ı").lower()


# --- LGS ile ilgili haberi tespit et ----------------------------------------
# NEDEN bu kalıplar: ÖDSGM haberlerinde LGS her zaman kısaltmayla anılmıyor —
# resmî/tarihsel adları da kullanılıyor: "Ortaöğretime Geçiş", "Ortaöğretim
# Kurumlarına Geçiş" (2015-2018 dönemi) ve "Sınavla Öğrenci Alacak Ortaöğretim
# Kurumlarına İlişkin Merkezî Sınav" (2019+ resmî uzun ad). Yalnız "ortaöğretim"
# aranırsa İOKBS (Bursluluk Sınavı) gibi alakasız kayıtlar da yakalanır — bu yüzden
# "geçiş" veya "ilişkin merkez" bağlamı ZORUNLU (34 İOKBS/diğer kaydıyla doğrulandı,
# hiçbiri yanlış eşleşmedi).
LGS_RE = re.compile(
    r"\blgs\b|liselere geçiş|ortaöğretime geçiş|ortaöğretim kurumlarına geçiş"
    r"|ortaöğretim kurumlarına ilişkin merkez"
)

# --- Duyuru tipi sınıflandırması --------------------------------------------
# NEDEN fetch_osym_duyuru.py'den ADAPTE (birebir kopya değil): MEB başlık kalıpları
# ÖSYM'den farklı. Sıra ÖSYM scriptiyle AYNI (ilk eşleşen kazanır, davranış
# tutarlılığı için): sonuc_aciklandi → yerlestirme → tercih → kilavuz → basvuru →
# giris_belgesi → cevap_anahtari → diger.
#   - giris_belgesi: MEB "SINAV GİRİŞ BİLGİLERİ ERİŞİME AÇILDI" der (ÖSYM'nin
#     "SINAVA GİRİŞ BELGELERİ" kalıbından farklı) → "giriş bilgileri/belgeleri" ikisi de.
#   - cevap_anahtari: MEB çoğunlukla ÇOĞUL kullanır ("SORU KİTAPÇIKLARI VE CEVAP
#     ANAHTARLARI") → ÖSYM'nin tekil-sonlu kalıbı ("kitapçığı") eşleşmez; kök
#     ("kitapç..", "anahtar..") yeterli, sonek serbest bırakıldı.
#   - yerlestirme: "nakil sonuçları" eklendi (MEB'e özgü "1./2. NAKİL SONUÇLARI").
#     NOT: sonuc_aciklandi ÖNCE kontrol edildiği için "... SONUÇLARI AÇIKLANDI"
#     kalıbına uyan yerleştirme/nakil başlıkları sonuc_aciklandi'ye düşer — ÖSYM
#     scriptiyle birebir aynı (kasıtlı) davranış; site genelinde tutarlılık.
TIPLER = [
    ("sonuc_aciklandi", r"sonu[çc]lar[ıi]?\s+a[çc][ıi]kland[ıi]"),
    ("yerlestirme", r"yerle[şs]tirme\s+sonu[çc]lar[ıi]|nakil\s+sonu[çc]lar[ıi]"),
    ("tercih", r"tercih\s+ve\s+yerle[şs]tirme\s+k[ıi]lavuzu|tercih\s+ve\s+yerle[şs]tirme\s+takvimi"
               r"|tercih\s+s[üu]reci|tercihlerin\s+al[ıi]nmas[ıi]"),
    ("kilavuz", r"k[ıi]lavuz|kontenjan"),
    ("basvuru", r"ba[şs]vuru"),
    ("giris_belgesi", r"giri[şs]\s+(bilgiler|belgeler)"),
    ("cevap_anahtari", r"cevap\s+anahtar|soru\s+kitap[çc][ıi]k"),
]
TIP_RE = [(ad, re.compile(pat)) for ad, pat in TIPLER]

DATE_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


def fetch_json(data: dict) -> dict:
    """ÖDSGM DataTables ajax'ına POST at: 3 deneme, artan bekleme (2s, 4s, 8s)."""
    body = urllib.parse.urlencode(data).encode()
    son_hata = None
    for deneme in range(1, RETRY + 1):
        try:
            req = urllib.request.Request(
                AJAX, data=body, method="POST",
                headers={
                    "User-Agent": UA,
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": INDEX,
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                },
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8", "ignore"))
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            son_hata = e
            if deneme < RETRY:
                bekle = 2 ** deneme  # 2, 4 → artan bekleme
                print(f"  ! deneme {deneme}/{RETRY} başarısız ({e}); {bekle}s bekleniyor")
                time.sleep(bekle)
    raise RuntimeError(f"{AJAX} çekilemedi ({RETRY} deneme): {son_hata}")


def temiz(s: str) -> str:
    """HTML entity'lerini çöz, boşlukları tekle (başlıklar zaten etiketsiz düz metin)."""
    return re.sub(r"\s+", " ", htmlmod.unescape(s)).strip()


def tarih_iso(dmy: str) -> str | None:
    """'DD/MM/YYYY' → 'YYYY-MM-DD'. ÖDSGM'nin ISLEMSAAT alanı hep bu biçimde."""
    m = DATE_RE.match(dmy.strip())
    if not m:
        return None
    gun, ay, yil = m.groups()
    try:
        return datetime(int(yil), int(ay), int(gun)).date().isoformat()
    except ValueError:
        return None


def tip_bul(baslik: str) -> str:
    """Başlık kalıbından duyuru tipini belirle (ilk eşleşen kazanır)."""
    low = _tr_lower(baslik)
    for ad, rx in TIP_RE:
        if rx.search(low):
            return ad
    return "diger"


def parse_sayfalar(limit: int | None = None) -> list[dict]:
    """ÖDSGM Haberler akışını sayfa sayfa çek, LGS ile ilgili olanları süz+sınıflandır.

    NEDEN limit erken-dur: --limit verildiğinde LGS eşleşen kayıt sayısı bu sınıra
    ulaşınca sayfalamayı durdurur (test/hızlı çalıştırma için gereksiz sayfa isteği
    atlanır). limit yoksa recordsTotal'a (veya MAX_PAGES güvenlik tavanına) kadar
    devam eder.
    """
    kayitlar: list[dict] = []
    start = 0
    toplam = None
    sayfa_no = 0
    while True:
        sayfa_no += 1
        if sayfa_no > MAX_PAGES:
            print(f"  ! MAX_PAGES ({MAX_PAGES}) aşıldı, durduruluyor")
            break
        data = {
            "draw": "1",
            "columns[0][data]": "ISLEMSAAT",
            "columns[1][data]": "BASLIK",
            "columns[2][data]": "SIRAID",
            "order[0][column]": "2",
            "order[0][dir]": "desc",
            "start": str(start),
            "length": str(PAGE_SIZE),
            "kategori": KATEGORI,
            "dil": "tr",
        }
        d = fetch_json(data)
        if toplam is None:
            toplam = int(d.get("recordsTotal", 0))
            print(f"  ÖDSGM Haberler toplam {toplam} kayıt (tümü, LGS harici dahil)")
        batch = d.get("data", [])
        if not batch:
            break
        for item in batch:
            baslik_ham = item.get("BASLIK") or ""
            if not LGS_RE.search(_tr_lower(baslik_ham)):
                continue
            baslik = temiz(baslik_ham)
            if not baslik:
                continue
            link = (item.get("LINK") or "").strip()
            if not link:
                continue
            url = urllib.parse.urljoin(BASE + "/", link)
            slug = urllib.parse.urlsplit(url).path.strip("/")
            kayitlar.append({
                "tarih": tarih_iso(item.get("ISLEMSAAT") or ""),
                "baslik": baslik,
                "url": url,
                "slug": slug,
                "sinav": "LGS",
                "tip": tip_bul(baslik),
            })
            if limit and len(kayitlar) >= limit:
                return kayitlar
        start += PAGE_SIZE
        if start >= toplam:
            break
        time.sleep(0.5)  # NEDEN: art arda 9+ POST isteği arasında nazik bekleme
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
    (fetch_osym_duyuru.birlestir ile birebir aynı mantık — bkz. o dosyadaki NEDEN yorumu.)"""
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
            if mevcut[k["url"]] != {**mevcut[k["url"]], **k}:
                guncellenen += 1
            mevcut[k["url"]].update(k)
        else:
            mevcut[k["url"]] = k
            eklenen += 1
            yeni_kayitlar.append(k)

    liste = sorted(
        mevcut.values(),
        key=lambda k: (k.get("tarih") or "0000-00-00", k.get("slug") or ""),
        reverse=True,
    )
    return liste, eklenen, guncellenen, yeni_kayitlar


def push_bildir(yeni_kayitlar: list[dict]) -> None:
    """YENİ "sonuc_aciklandi" duyuruları için push-server'a bildir — ÖSYM scriptiyle
    AYNI ortak endpoint/sözleşme (sinav alanı serbest metin, "LGS" de kabul eder).
    NEDEN try/except sarmalı: push-server ayakta değilse bu script YİNE DE veri
    dosyasını yazmalı — bildirim ikincil, veri birincil (fetch_osym_duyuru ile aynı)."""
    import os

    secret = os.environ.get("SINAVVERI_PUSH_SECRET", "")
    if not secret:
        return
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
    ap = argparse.ArgumentParser(description="MEB/ÖDSGM LGS duyurularını çek → data/meb_duyurular.json")
    ap.add_argument("--limit", type=int, default=None, help="En fazla N LGS duyurusu işle")
    ap.add_argument("--dry-run", action="store_true", help="Dosyaya yazma, sadece raporla")
    a = ap.parse_args()

    print(f"→ {AJAX} (kategori={KATEGORI}) çekiliyor...")
    yeni = parse_sayfalar(a.limit)
    print(f"  {len(yeni)} LGS duyurusu ayrıştırıldı")

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
            "kaynak": "MEB",
            "duyurular": liste,
        }
        DATA.mkdir(exist_ok=True)
        OUT.write_text(json.dumps(cikti, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"✓ {OUT} → toplam {len(liste)} kayıt (yeni {eklenen}, güncellenen {guncellenen})")
        push_bildir(yeni_kayitlar)

    from collections import Counter
    print("  tip dağılımı :", dict(Counter(k["tip"] for k in liste).most_common()))
    if liste:
        tarihler = [k["tarih"] for k in liste if k["tarih"]]
        if tarihler:
            print(f"  tarih aralığı: {min(tarihler)} .. {max(tarihler)}")


if __name__ == "__main__":
    main()
