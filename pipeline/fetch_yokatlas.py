#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YÖK Atlas cari tercih kılavuzu gerçek verisini çeker.
Kaynak: POST https://yokatlas.yok.gov.tr/api/tercih-kilavuz/search
Çıktı: data/programs_raw.json (tüm kayıtlar, sadeleştirilmiş alanlar)
       data/veri/{say,ea,soz,dil,tyt}.json (istemci tarafı arama/tercih robotu için)

YIL SABİT YAZILMAZ (2026-08-19 kök-neden düzeltmesi): API yanıtının top-level `yil`
alanı kılavuz yılını verir; taban puanının (minPuan) hangi yerleştirmeye ait olduğu ise
KAYMA TESPİTİ ile bulunur — yeni minPuan1, bir önceki koşumun tp değerine eşitse veri
bir yıl kaymış demektir (yerleştirme sonuçları açıklandı). Böylece 2026→2027→… geçişleri
elle müdahale gerektirmez. Ayrıntı: `yil_tespit()`.

DAYANIKLILIK: post() retry+backoff yapar (10/17 Ağu 2026 koşumları tek TimeoutError ile
komple çökmüştü) ve TÜM scope'lar başarıyla çekilmeden HİÇBİR dosya yazılmaz (atomik).
"""
import json
import time
from datetime import datetime, timezone
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
TIMEOUT = 120          # tek istek zaman aşımı (sn) — 60 sn ÖSYM/YÖK yoğun saatlerde yetmiyordu
RETRY = 5              # istek başına deneme sayısı
BACKOFF = (3, 8, 20, 45)  # denemeler arası bekleme (sn)
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
    """POST + retry/backoff. NEDEN: YÖK Atlas API tek sayfada timeout verdiğinde eski
    kod tüm çekimi düşürüyordu → haftalık cron 2 hafta üst üste eski veriyle kaldı."""
    son_hata = None
    for deneme in range(1, RETRY + 1):
        try:
            req = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"),
                                         headers=HEADERS, method="POST")
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:          # noqa: BLE001 — timeout/SSL/5xx/JSON hepsi tekrar denenir
            son_hata = e
            if deneme < RETRY:
                bekle = BACKOFF[min(deneme - 1, len(BACKOFF) - 1)]
                print(f"    ! deneme {deneme}/{RETRY} başarısız ({type(e).__name__}: {e}) "
                      f"→ {bekle} sn sonra tekrar", flush=True)
                time.sleep(bekle)
    raise RuntimeError(f"YÖK Atlas isteği {RETRY} denemede başarısız: {son_hata}")


def fetch_scope(birim_turu, puan_turu):
    """→ (kayitlar, kilavuz_yili). API top-level `yil` = cari tercih kılavuzu yılı."""
    out, page, kil_yil = [], 0, None
    while True:
        body = {"filters": {"birimTuruId": birim_turu, "puanTuru": puan_turu},
                "page": page, "size": SIZE, "sortBy": "basariSirasi", "direction": "ASC"}
        d = post(body)
        if kil_yil is None:
            kil_yil = _i(d, "yil")
        content = d.get("content", [])
        out.extend(content)
        total = d.get("totalElements", 0)
        print(f"    {puan_turu} sayfa {page}: +{len(content)}  ({len(out)}/{total})")
        if d.get("last") or not content:
            break
        page += 1
        time.sleep(0.4)
    return out, kil_yil


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


def trim(r, tp_yili):
    """İstemciye gidecek kompakt kayıt + sunucu tarafı için 4 yıllık geçmiş.
    `tp_yili` = minPuan/basariSirasi/gkY alanlarının ait olduğu YERLEŞTİRME yılı
    (yil_tespit() ile bulunur — SABİT YAZILMAZ). Geçmiş suffix eşlemesi:
    1→tp_yili-1, 2→tp_yili-2, 3→tp_yili-3."""
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
        "yer": _i(r, "gkY"),  # genel kontenjandan yerleşen (tp_yili)
        "tp": _f(r, "minPuan"),
        "sira": _i(r, "basariSirasi"),
        # 4 yıllık geçmiş: [yıl, taban, sıra, yerleşen]
        "hist": [
            [tp_yili - 1, _f(r, "minPuan1"), _i(r, "basariSirasi1"), _i(r, "gk1")],
            [tp_yili - 2, _f(r, "minPuan2"), _i(r, "basariSirasi2"), _i(r, "gk2")],
            [tp_yili - 3, _f(r, "minPuan3"), _i(r, "basariSirasi3"), _i(r, "gk3")],
        ],
        # Program detay zenginliği (toplu API'den bedava):
        "kosul": (r.get("kosul") or "").strip(),                  # "21,22,23" koşul kodları
        "kadro": [_i(r, "prof"), _i(r, "doc"), _i(r, "dou"), _i(r, "arGor"), _i(r, "ogrGor")],  # Prof/Doçent/Dr.Öğr.Ü/Ar.Gör/Öğr.Gör
        "akr": (r.get("akreditasyon") or "").strip() or None,     # akreditasyon kurumu
        "sure": _i(r, "ogrenimSuresi"),                            # öğrenim süresi (yıl)
        "ucret": _i(r, "ucret"),                                   # vakıf ücreti (TL)
    }


def _duyuru_yerlesme_yili():
    """ÖSYM duyuru arşivinden (30 dk'da bir tazelenir) YKS YERLEŞTİRME sonucu açıklanmış
    EN SON yılı döndürür. yil_tespit() için bağımsız ikinci kanıt; bulunamazsa None."""
    f = DATA / "osym_duyurular.json"
    if not f.exists():
        return None
    try:
        kayitlar = json.loads(f.read_text(encoding="utf-8")).get("duyurular", [])
    except Exception:
        return None
    yillar = []
    for k in kayitlar:
        b = (k.get("baslik") or "")
        if k.get("sinav") != "YKS" or "Yerleştirme Sonuçları" not in b:
            continue
        if "Ek Yerleştirme" in b:          # ek yerleştirme taban puanlarını değiştirmez
            continue
        try:
            yillar.append(int((k.get("tarih") or "")[:4]))
        except ValueError:
            pass
    return max(yillar) if yillar else None


def yil_tespit(ham, kil_yil):
    """minPuan alanının hangi YERLEŞTİRME yılına ait olduğunu bulur — SABİT YAZILMAZ.

    Tercih kılavuzu Temmuz'da yayımlanır ama o yılın yerleştirmesi Ağustos'ta biter:
      · yerleştirmeden ÖNCE  → API'nin minPuan'ı bir ÖNCEKİ yılın sonucudur (kil_yil-1)
      · yerleştirmeden SONRA → minPuan cari yılın sonucudur (kil_yil) ve tüm geçmiş
        alanları bir slot kayar (eski minPuan → minPuan1).

    KANIT 1 (birincil, KAYMA TESPİTİ): bir önceki koşumun tp değerleri elimizde. Yeni
    minPuan1 çoğunlukla eski tp'ye eşitse veri bir yıl kaymıştır.
    KANIT 2 (çapraz doğrulama): ÖSYM duyuru arşivinde 'YKS: Yerleştirme Sonuçları
    Açıklandı' duyurusunun yılı.
    İkisi çelişirse UYARI basılır ve KANIT 1 esas alınır (ölçüme dayalı olan odur).
    """
    duy = _duyuru_yerlesme_yili()
    bekl = kil_yil if (duy is not None and duy >= kil_yil) else (kil_yil - 1 if duy is not None else None)

    onceki_tp = {}
    onceki_yil = None
    mf, pf = DATA / "yokatlas_meta.json", DATA / "programs_raw.json"
    if mf.exists() and pf.exists():
        try:
            m = json.loads(mf.read_text(encoding="utf-8"))
            onceki_yil = m.get("taban_yili") or m.get("yil")
            for r in json.loads(pf.read_text(encoding="utf-8")):
                if r.get("tp") is not None:
                    onceki_tp[r.get("k")] = r["tp"]
        except Exception as e:
            print(f"  ! önceki veri okunamadı ({e}) — kayma tespiti atlanıyor")

    tespit = None
    if onceki_tp and onceki_yil:
        ayni = kaydi = 0
        for r in ham:
            eski = onceki_tp.get(r.get("kilavuzKodu"))
            if eski is None:
                continue
            if _f(r, "minPuan") == eski:
                ayni += 1
            elif _f(r, "minPuan1") == eski:
                kaydi += 1
        toplam = ayni + kaydi
        if toplam >= 100:                      # anlamlı örneklem
            oran = kaydi / toplam
            if oran >= 0.80:
                tespit = onceki_yil + 1
                print(f"  ✓ KAYMA TESPİT EDİLDİ: {kaydi}/{toplam} (%{oran*100:.1f}) program bir yıl kaydı "
                      f"→ taban yılı {onceki_yil} → {tespit}")
            elif oran <= 0.20:
                tespit = onceki_yil
                print(f"  ✓ kayma yok: {ayni}/{toplam} (%{(1-oran)*100:.1f}) program aynı "
                      f"→ taban yılı {tespit} (değişmedi)")
            else:
                print(f"  ! kayma tespiti KARARSIZ (aynı={ayni}, kaydı={kaydi}) — duyuru kanıtına düşülüyor")
        else:
            print(f"  ! kayma tespiti için yetersiz eşleşme ({toplam}) — duyuru kanıtına düşülüyor")

    if tespit is None:
        tespit = bekl if bekl is not None else kil_yil - 1
        print(f"  → taban yılı duyuru/varsayılan kanıtından: {tespit}")
    elif bekl is not None and tespit != bekl:
        print(f"  ⚠ UYARI: kayma tespiti {tespit} diyor, ÖSYM duyurusu {bekl} diyor. "
              f"Ölçüme dayalı olan ({tespit}) kullanılıyor — kontrol edilmeli.")

    if tespit not in (kil_yil, kil_yil - 1):
        duzeltme = kil_yil if (bekl == kil_yil) else kil_yil - 1
        print(f"  ⚠ UYARI: taban yılı {tespit}, kılavuz yılı {kil_yil} ile tutarsız → {duzeltme} yapıldı")
        tespit = duzeltme
    return tespit


def main():
    pt_key = {"SAY": "say", "EA": "ea", "SÖZ": "soz", "DİL": "dil", "TYT": "tyt"}

    # 1) HEPSİNİ ÇEK — hiçbir dosya yazılmadan. NEDEN: eski kod her scope'u anında yazıyordu;
    #    3. scope'ta çökme veri/*.json'u yarısı yeni yarısı eski BOZUK durumda bırakıyordu.
    ham_scope = {}
    kil_yillar = []
    for birim, pt in SCOPES:
        print(f"  Çekiliyor: birimTuru={birim} puanTuru={pt}", flush=True)
        recs, ky = fetch_scope(birim, pt)
        if not recs:
            raise RuntimeError(f"{pt} scope'u BOŞ döndü — yazma iptal (eski veri korunur)")
        ham_scope[pt] = recs
        if ky:
            kil_yillar.append(ky)

    kil_yil = max(kil_yillar) if kil_yillar else datetime.now().year
    tum_ham = [r for recs in ham_scope.values() for r in recs]
    print(f"\n  Kılavuz yılı (API): {kil_yil} · toplam {len(tum_ham)} ham kayıt")
    tp_yili = yil_tespit(tum_ham, kil_yil)
    print(f"  → TABAN PUANI YILI: {tp_yili} · geçmiş sütunları: "
          f"{tp_yili-1}, {tp_yili-2}, {tp_yili-3}\n")

    # 2) DÖNÜŞTÜR
    all_recs = []
    kosul_map = {}
    cikti = {}
    for _, pt in SCOPES:
        recs = ham_scope[pt]
        for r in recs:
            for d in (r.get("kosulList") or []):
                for code, text in d.items():
                    if code and text:
                        kosul_map[str(code)] = text.strip()
        trimmed = [trim(r, tp_yili) for r in recs]
        cikti[pt_key[pt]] = trimmed
        all_recs.extend(trimmed)

    # 3) YAZ (hepsi başarılıysa)
    for ad, trimmed in cikti.items():
        f = VERI / f"{ad}.json"
        f.write_text(json.dumps(trimmed, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"  → {ad}: {len(trimmed)} kayıt, {f.stat().st_size//1024} KB")
    (DATA / "programs_raw.json").write_text(
        json.dumps(all_recs, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\nTOPLAM: {len(all_recs)} program → data/programs_raw.json")
    (DATA / "kosul_map.json").write_text(
        json.dumps(kosul_map, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  koşul kodu açıklaması: {len(kosul_map)} → data/kosul_map.json")

    meta = {
        "kaynak": f"YÖK Atlas {kil_yil} Tercih Kılavuzu",
        "url": URL,
        "yil": kil_yil,                                   # kılavuz (kontenjan) yılı
        "taban_yili": tp_yili,                            # taban puanı/sıra yerleştirme yılı
        "hist_yillari": [tp_yili - 1, tp_yili - 2, tp_yili - 3],
        "toplam": len(all_recs),
        "guncelleme": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }
    (DATA / "yokatlas_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  meta: kılavuz {kil_yil} · taban {tp_yili} → data/yokatlas_meta.json")


if __name__ == "__main__":
    main()
