#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VERİ BEKÇİSİ — sitenin verisi kaynağın gerisinde mi, GÜNLÜK kontrol eder.

NEDEN VAR (2026-08-19)
----------------------
2026-YKS yerleştirme sonuçları 18 Ağustos'ta açıklandı; site 19 Ağustos'ta hâlâ 2025
taban puanlarını gösteriyordu. Üç ayrı sessiz arıza üst üste gelmişti:
  1. `fetch_yokatlas` iki hafta üst üste TimeoutError ile çöktü (retry yoktu) → fail-safe
     eski veriyi geri yükledi ve kimse görmedi.
  2. `fetch_lgs` cari yılı SABİT "2025" okuyordu → kaynak 2026'ya geçtiği hâlde yok saydı.
  3. `fetch_osym` URL'leri elle sabitti → ÖSYM kalıbı değişince yeni yıl hiç gelmedi.
Üçünün ortak yanı: **hata vermeden geride kalmak.** Haftalık cron'un bir sonraki koşumunu
beklemek de 7 güne kadar gecikme demekti. Bu bekçi her gün kaynağa bakar; site geride
kalmışsa Telegram'dan haber verir ve (izin verilirse) tazelemeyi KENDİSİ tetikler.

Kontroller
----------
  YKS  : YÖK Atlas API'sinin cari kılavuz yılı + minPuan kayması ↔ yokatlas_meta.taban_yili
  ÖSYM : osym_kesif keşfi ile cari yıl min-max PDF'i var mı ↔ osym_meta.yillar[exam]
  LGS  : kaynakta görülen en büyük yıl ↔ lgs_meta.yil
  Duyuru: osym_duyurular.json bayat mı (>3 saat güncellenmemiş)

Kullanım:
    python3 -m pipeline.veri_bekcisi            # kontrol + Telegram bildirimi
    python3 -m pipeline.veri_bekcisi --tazele   # geride ise pipeline.run'ı da çalıştır
    python3 -m pipeline.veri_bekcisi --sessiz   # Telegram gönderme (yalnız stdout)
Çıkış kodu: 0 = güncel · 1 = geride (izleme bunu yakalar)
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import osym_kesif as kesif

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REGISTRY = Path("/home/tekni/VS/servermimari/.secrets/REGISTRY.env")


def _meta(ad):
    f = DATA / ad
    try:
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    except Exception:  # noqa: BLE001
        return {}


# ───────────────────────────── kontroller ─────────────────────────────
def kontrol_yks():
    """YÖK Atlas'ta cari kılavuz yılı ve taban puanı kayması ↔ bizim taban_yili."""
    body = {"filters": {"birimTuruId": 46, "puanTuru": "SAY"}, "page": 0, "size": 50,
            "sortBy": "basariSirasi", "direction": "ASC"}
    req = urllib.request.Request(
        "https://yokatlas.yok.gov.tr/api/tercih-kilavuz/search",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "sinavveri-bekci/1.0"},
        method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.loads(r.read().decode("utf-8"))

    meta = _meta("yokatlas_meta.json")
    bizim = int(meta.get("taban_yili") or meta.get("yil") or 0)
    kaynak_kilavuz = int(d.get("yil") or 0)

    # Kayma tespiti: kaynaktaki minPuan1 bizim tp'ye eşitse veri bir yıl ilerlemiş demektir.
    try:
        mevcut = {r["k"]: r["tp"] for r in json.loads((DATA / "programs_raw.json").read_text(encoding="utf-8"))
                  if r.get("tp") is not None}
    except Exception:  # noqa: BLE001
        mevcut = {}
    kaydi = ayni = 0
    for r in d.get("content", []):
        eski = mevcut.get(r.get("kilavuzKodu"))
        if eski is None:
            continue
        def f(k):
            v = r.get(k)
            try:
                return round(float(v), 3) if v not in (None, "") else None
            except (TypeError, ValueError):
                return None
        if f("minPuan") == eski:
            ayni += 1
        elif f("minPuan1") == eski:
            kaydi += 1
    geride = (kaydi + ayni) >= 10 and kaydi > ayni
    return {
        "ad": "YKS (YÖK Atlas)", "bizim": bizim, "kaynak": bizim + 1 if geride else bizim,
        "geride": geride,
        "not": (f"kaynakta {kaydi}/{kaydi+ayni} program bir yıl ilerlemiş — YENİ YERLEŞTİRME VAR"
                if geride else f"kılavuz {kaynak_kilavuz}, taban {bizim} · güncel"),
    }


def kontrol_osym(kesif_yap=True):
    """ÖSYM'de cari yıl min-max PDF'i yayımlanmış mı ↔ osym_meta.yillar."""
    bu_yil = date.today().year
    if kesif_yap:
        try:
            kesif.guncelle([bu_yil], dogrulama=True)
        except Exception as e:  # noqa: BLE001
            print(f"  ! ÖSYM keşfi başarısız: {e}")
    meta = _meta("osym_meta.json")
    yillar = meta.get("yillar") or {}
    sonuc = []
    for exam in ("tus", "dus", "dgs", "kpss"):
        bizim = int(yillar.get(exam) or meta.get("yil") or 0)
        kaynak = kesif.en_son_yil(exam, azami=bu_yil) or bizim
        sonuc.append({
            "ad": f"{exam.upper()} (ÖSYM)", "bizim": bizim, "kaynak": kaynak,
            "geride": kaynak > bizim,
            "not": ("ÖSYM yeni yerleştirme min-max tablosunu yayımladı"
                    if kaynak > bizim else "güncel (yeni yerleştirme yok)"),
        })
    return sonuc


def kontrol_lgs():
    """LGS kaynağında görülen en büyük yıl ↔ lgs_meta.yil."""
    from .fetch_lgs import INDEX, get, parse_il  # noqa: PLC0415
    meta = _meta("lgs_meta.json")
    bizim = int(meta.get("yil") or 0)
    try:
        idx = get(INDEX)
        urls = sorted(set(re.findall(
            r"https://[a-z0-9.]+/[a-z0-9-]+-liseleri(?:-[0-9]{4})?-taban-puanlari-yuzdelik-dilimleri-lgs-meb",
            idx)))
        kaynak = 0
        for u in urls[:2]:                       # örneklem yeter (tüm iller aynı yıl setinde)
            for r in parse_il(get(u), u):
                kaynak = max(kaynak, int(r.get("yil") or 0))
        kaynak = kaynak or bizim
    except Exception as e:  # noqa: BLE001
        return {"ad": "LGS (MEB)", "bizim": bizim, "kaynak": bizim, "geride": False,
                "not": f"kontrol edilemedi: {e}"}
    return {"ad": "LGS (MEB)", "bizim": bizim, "kaynak": kaynak, "geride": kaynak > bizim,
            "not": "MEB yeni yerleştirme verisini yayımladı" if kaynak > bizim else "güncel"}


def kontrol_duyuru():
    """Duyuru arşivi bayat mı? (30 dk'da bir tazelenmeli — 3 saat sınırı toleranslı.)"""
    d = _meta("osym_duyurular.json")
    ham = d.get("guncelleme")
    try:
        t = datetime.fromisoformat(ham)
        if t.tzinfo is None:
            # Damga sunucunun YEREL saatiyle yazılıyor (UTC değil) — UTC varsaymak
            # negatif yaş üretiyordu.
            t = t.astimezone() if hasattr(t, "astimezone") else t
            t = t.replace(tzinfo=datetime.now().astimezone().tzinfo)
        yas = datetime.now(timezone.utc).astimezone() - t
    except Exception:  # noqa: BLE001
        return {"ad": "ÖSYM duyuruları", "bizim": "?", "kaynak": "?", "geride": True,
                "not": "guncelleme damgası okunamadı"}
    bayat = yas > timedelta(hours=3)
    return {"ad": "ÖSYM duyuruları", "bizim": ham, "kaynak": "≤3 sa", "geride": bayat,
            "not": f"{int(yas.total_seconds()//60)} dk önce güncellendi" + (" — BAYAT" if bayat else "")}


# ───────────────────────────── bildirim ─────────────────────────────
def _registry(anahtar):
    if not REGISTRY.exists():
        return None
    for satir in REGISTRY.read_text(encoding="utf-8", errors="replace").splitlines():
        satir = satir.strip()
        if satir.startswith(anahtar + "="):
            return satir.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def telegram(metin):
    tok = os.environ.get("TG_CLAUDE_BOT_TOKEN") or _registry("TG_CLAUDE_BOT_TOKEN") or _registry("TG_BOT_TOKEN")
    chat = os.environ.get("TG_CLAUDE_CHAT_ID") or _registry("TG_CLAUDE_CHAT_ID") or _registry("TG_CHAT_ID")
    if not (tok and chat):
        print("  ! Telegram anahtarı bulunamadı — bildirim atlandı")
        return False
    veri = urllib.parse.urlencode({"chat_id": chat, "text": metin,
                                   "parse_mode": "HTML", "disable_web_page_preview": "true"}).encode()
    try:
        with urllib.request.urlopen(
                urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage", data=veri),
                timeout=20) as r:
            return r.status == 200
    except Exception as e:  # noqa: BLE001
        print(f"  ! Telegram gönderilemedi: {e}")
        return False


def main():
    ap = argparse.ArgumentParser(description="SinavVeri veri güncellik bekçisi")
    ap.add_argument("--tazele", action="store_true", help="geride ise pipeline.run'ı çalıştır")
    ap.add_argument("--sessiz", action="store_true", help="Telegram bildirimi gönderme")
    ap.add_argument("--kesif-yok", action="store_true", help="ÖSYM keşfini atla (hızlı)")
    a = ap.parse_args()

    print(f"SinavVeri veri bekçisi — {date.today().isoformat()}")
    kontroller = []
    for ad, fn in (("YKS", lambda: [kontrol_yks()]),
                   ("ÖSYM", lambda: kontrol_osym(kesif_yap=not a.kesif_yok)),
                   ("LGS", lambda: [kontrol_lgs()]),
                   ("Duyuru", lambda: [kontrol_duyuru()])):
        try:
            kontroller.extend(fn())
        except Exception as e:  # noqa: BLE001
            kontroller.append({"ad": ad, "bizim": "?", "kaynak": "?", "geride": True,
                               "not": f"kontrol HATASI: {e}"})

    print("\n{:<20} {:<12} {:<12} {}".format("KONTROL", "BİZDE", "KAYNAKTA", "DURUM"))
    for k in kontroller:
        isaret = "⚠ GERİDE" if k["geride"] else "✓"
        print("{:<20} {:<12} {:<12} {} — {}".format(k["ad"], str(k["bizim"]), str(k["kaynak"]), isaret, k["not"]))

    geride = [k for k in kontroller if k["geride"]]
    if not geride:
        print("\n✓ Tüm veri setleri güncel.")
        return 0

    satirlar = "\n".join(f"• <b>{k['ad']}</b>: bizde {k['bizim']} · kaynakta {k['kaynak']} — {k['not']}"
                         for k in geride)
    msg = (f"⚠️ <b>SinavVeri — veri geride kaldı</b>\n\n{satirlar}\n\n"
           f"https://sinavveri.com")
    if a.tazele:
        print("\n→ pipeline.run tetikleniyor (--tazele)...")
        r = subprocess.run([sys.executable, "-m", "pipeline.run"], cwd=str(ROOT))
        msg += f"\n\nOtomatik tazeleme çalıştırıldı (çıkış kodu {r.returncode})."
    if not a.sessiz:
        telegram(msg)
    return 1


if __name__ == "__main__":
    sys.exit(main())
