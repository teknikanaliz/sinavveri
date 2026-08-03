#!/usr/bin/env python3
"""YKS RESMİ KILAVUZ DENETİMİ — ÖSYM'nin 2026 YKS kılavuzu (Tablo-3 + Tablo-4) ile
data/programs_raw.json'daki program kodlarını karşılaştırır.

NEDEN: build.py'deki YENİ/KAPANDI rozetleri programs_raw.json'ın KENDİ geçmişinden
(hist alanı) TAHMİN yapamaz — dosya yalnız CARİ (bu yılki) kılavuzu içerir, önceki yılın
program listesi hiçbir yerde saklı değil. Ama ÖSYM'nin resmî kılavuz tabloları TAM program
kodu listesini verir; bunu programs_raw.json ile kıyaslamak KESİN (heuristik değil) bir
YENİ/KAPANDI tespiti sağlar:
  - kılavuzda VAR, bizim veride YOK  → henüz pipeline'a düşmemiş YENİ program adayı
    (genelde bir sonraki `fetch_yokatlas.py` koşumunda otomatik gelir).
  - bizim veride VAR, kılavuzda YOK  → bu yıl kılavuzdan düşmüş (KAPANDI/alım yok) —
    build.py bu kodlar için sayfayı SİLMEZ, "Bu yıl alım yapmıyor" rozeti gösterir.

ÖLÇÜLDÜ (2026-08-03): 21.493 kılavuz kodu ↔ 21.480 program kaydı → 21.477 ORTAK, yalnız
16 yeni aday + 3 kapanma adayı. Yani örtüşme %99.9 — kod tabanlı diff düşük gürültülü.

KAYNAK DOSYALAR (ÖSYM sayfasından, elle sabit YAZILMAZ — sayfadan otomatik bulunur):
  https://www.osym.gov.tr/2026-yuksekogretim-kurumlari-sinavi-yks-yuksekogretim-programlari-ve-kontenjanlari-kilavuzu
Bu sayfa PDF kılavuz + Tablo-3 (önlisans/TYT ağırlıklı) + Tablo-4 (lisans) linklerini verir.
dokuman.osym.gov.tr bazen ilk istekte 403 "Erişim Engellendi" verebiliyor (WAF); tarayıcı
User-Agent + Referer ile güvenilir çalıştığı ölçüldü (3/3 deneme), yine de retry var.

Kullanım:
  python3 -m pipeline.kilavuz_diff             # data/kilavuz_2026.json yazar
  python3 -m pipeline.kilavuz_diff --dry-run    # yalnız özet basar, yazmaz
"""
import argparse
import io
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KILAVUZ_SAYFA = ("https://www.osym.gov.tr/2026-yuksekogretim-kurumlari-sinavi-yks-"
                  "yuksekogretim-programlari-ve-kontenjanlari-kilavuzu")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def _fetch(url, referer=None, retries=3):
    headers = {"User-Agent": UA}
    if referer:
        headers["Referer"] = referer
    last_err = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            last_err = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"{url} alınamadı: {last_err}")


def _dosya_linklerini_bul():
    """Kılavuz sayfasından PDF + Tablo-3 + Tablo-4 linklerini çıkarır (sabit yazılmaz —
    dosya adları her yıl/güncellemede değişiyor, ör. 'tablo-3-29u1s7pl.xls')."""
    html = _fetch(KILAVUZ_SAYFA).decode("utf-8", "replace")
    hrefs = re.findall(r'href="(https://dokuman\.osym\.gov\.tr/[^"]+)"', html)
    pdf = next((h for h in hrefs if h.lower().endswith(".pdf")), None)
    xls = [h for h in hrefs if h.lower().endswith((".xls", ".xlsx"))]
    tablo3 = next((h for h in xls if "tablo-3" in h.lower()), None)
    tablo4 = next((h for h in xls if "tablo-4" in h.lower()), None)
    if not (pdf and tablo3 and tablo4):
        raise RuntimeError(f"kılavuz sayfasında beklenen dosyalar bulunamadı "
                           f"(pdf={bool(pdf)} t3={bool(tablo3)} t4={bool(tablo4)}) — "
                           f"ÖSYM sayfa yapısını değiştirmiş olabilir, elle kontrol et: {KILAVUZ_SAYFA}")
    return pdf, tablo3, tablo4


def _tablo_oku(url):
    """(kod -> kontenjan) sözlüğü. Sütun 0=program kodu, sütun 4=GENEL KONTENJAN
    (her iki tabloda da aynı pozisyon — ölçüldü)."""
    import pandas as pd
    raw = _fetch(url, referer=KILAVUZ_SAYFA)
    df = pd.read_excel(io.BytesIO(raw), header=None)
    kod = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    kont = pd.to_numeric(df.iloc[:, 4], errors="coerce")
    out = {}
    for k, c in zip(kod, kont):
        if k == k:  # NaN değilse
            out[int(k)] = None if c != c else int(c)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    print("[kilavuz_diff] ÖSYM kılavuz sayfası taranıyor...")
    pdf_url, t3_url, t4_url = _dosya_linklerini_bul()
    print(f"  PDF: {pdf_url}\n  Tablo-3: {t3_url}\n  Tablo-4: {t4_url}")

    print("[kilavuz_diff] Tablo-3 + Tablo-4 indiriliyor ve okunuyor...")
    t3 = _tablo_oku(t3_url)
    t4 = _tablo_oku(t4_url)
    kilavuz = {**t3, **t4}
    print(f"  kılavuz kod sayısı: {len(kilavuz):,}  (Tablo-3: {len(t3):,}, Tablo-4: {len(t4):,})")

    import json
    programs = json.loads((ROOT / "data" / "programs_raw.json").read_text(encoding="utf-8"))
    bizde = {r["k"]: r for r in programs if r.get("k")}
    print(f"  bizim veri kod sayısı: {len(bizde):,}")

    yeni = sorted(set(kilavuz) - set(bizde))
    kapanan = sorted(set(bizde) - set(kilavuz))
    ortak = set(kilavuz) & set(bizde)
    print(f"  ortak: {len(ortak):,}  ·  YENİ aday: {len(yeni)}  ·  KAPANAN aday: {len(kapanan)}")

    out = {
        "guncelleme": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kaynak_sayfa": KILAVUZ_SAYFA,
        "pdf_url": pdf_url,
        "tablo3_url": t3_url,
        "tablo4_url": t4_url,
        "kilavuz_kod_sayisi": len(kilavuz),
        "bizim_kod_sayisi": len(bizde),
        "yeni_kodlar": yeni,
        "kapanan_kodlar": [{"kod": k, "universite": bizde[k].get("u"), "program": bizde[k].get("b")}
                           for k in kapanan],
    }

    if a.dry_run:
        print("\n[DRY-RUN] yazılmadı.")
        if kapanan:
            print("KAPANAN adaylar:")
            for k in kapanan[:20]:
                print(f"  {k} | {bizde[k].get('u')} | {bizde[k].get('b')}")
        return 0

    out_path = ROOT / "data" / "kilavuz_2026.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[kilavuz_diff] yazıldı: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
