#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""data/takvim-2026.json tarih normalizasyonu.

SORUN: `sonuc` alanı biçimsiz karışık geliyor — "24 Mar 2026", "2026-07-22",
"13 Ağu 2026" ve "Haziran 2026 sonu" gibi MUĞLAK ifadeler bir arada. Bu haliyle
tarihe göre sıralama/karşılaştırma yapılamıyor.

ÇÖZÜM: Tüm tarih alanları ISO'ya (YYYY-MM-DD) çevrilir. Kesin tarihe
çevrilemeyenlerde VERİ KAYBEDİLMEZ:
    sonuc            → ISO tarih, kesinleşmemişse null
    sonuc_ham        → orijinal metin (HER ZAMAN korunur; geri dönüş garantisi)
    sonuc_kesin      → true = gerçek gün belli, false = tahmini/muğlak
    sonuc_tahmini_ay → "2026-06" (ay hassasiyeti varsa; yoksa alan eklenmez)

`basvuru` serbest metin olarak AYNEN KALIR (ör. "5 – 29 Oca 2026 (geç: 3 Şub)");
yanına makine-okunur `basvuru_bas` / `basvuru_bit` ISO alanları TÜRETİLİR.
NEDEN dokunmuyoruz: metin "geç başvuru" gibi ISO'ya sığmayan bilgi taşıyor ve
sitede olduğu gibi gösteriliyor.

IDEMPOTENT: İkinci çalıştırma aynı sonucu verir. NEDEN garantili: türetilmiş
alanlar her seferinde `sonuc_ham` / `basvuru` (orijinal kaynaklar) üzerinden
yeniden hesaplanır; bir önceki turun `sonuc` çıktısı girdi olarak kullanılmaz.

Kullanım:
    python3 -m pipeline.normalize_takvim            # --dry-run (varsayılan)
    python3 -m pipeline.normalize_takvim --apply    # yaz (önce .bak-<tarih> alır)
"""
import argparse
import json
import re
from datetime import date, datetime
from pathlib import Path

# NEDEN try/except: script hem `python3 -m pipeline.normalize_takvim` hem de
# `python3 pipeline/normalize_takvim.py` ile çalışabilsin. Ay tablosunu
# kopyalamak yerine tek kaynaktan (fetch_osym_duyuru) alıyoruz.
try:
    from .fetch_osym_duyuru import AYLAR, _tr_lower
except ImportError:  # doğrudan dosya olarak çalıştırıldığında
    from fetch_osym_duyuru import AYLAR, _tr_lower

ROOT = Path(__file__).resolve().parent.parent
HEDEF = ROOT / "data" / "takvim-2026.json"

# Türetilen alanlar — yeniden hesaplanmadan önce kayıttan çıkarılır (idempotentlik).
TURETILEN = ("sonuc_ham", "sonuc_kesin", "sonuc_tahmini_ay", "basvuru_bas", "basvuru_bit")

ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# "24 Mar 2026" / "4 Haziran 2026"  → gün + ay + yıl
GUN_AY_YIL = re.compile(r"^(\d{1,2})\s+([^\s\d]+)\s+(\d{4})$")
# "Haziran 2026 sonu" / "Haziran 2026" → yalnız ay + yıl (gün belirsiz)
AY_YIL = re.compile(r"^([^\s\d]+)\s+(\d{4})\b")
# Başvuru aralığı — parantezli ek ("(geç: 3 Şub)") temizlendikten sonra uygulanır.
ARALIK_FARKLI_AY = re.compile(
    r"(\d{1,2})\s+([^\s\d]+)\s*[–—-]\s*(\d{1,2})\s+([^\s\d]+)\s+(\d{4})"
)
ARALIK_AYNI_AY = re.compile(r"(\d{1,2})\s*[–—-]\s*(\d{1,2})\s+([^\s\d]+)\s+(\d{4})")


def _ay_no(ad: str) -> int | None:
    """'Ağu' / 'Ağustos' / 'AĞUSTOS' → 8. Türkçe-güvenli küçültme kullanır."""
    return AYLAR.get(_tr_lower(ad).strip("."))


def _iso(yil, ay, gun) -> str | None:
    """Geçerliyse ISO tarih döndür; 31 Nisan gibi geçersizlerde None."""
    try:
        return date(int(yil), int(ay), int(gun)).isoformat()
    except (ValueError, TypeError):
        return None


def coz_tarih(ham: str) -> tuple[str | None, bool, str | None]:
    """Serbest tarih metnini çöz → (iso, kesin_mi, tahmini_ay).

    kesin=True yalnızca GÜN düzeyinde tarih belliyse verilir.
    """
    s = (ham or "").strip()
    if not s:
        return None, False, None

    if ISO_RE.match(s):  # zaten ISO — dokunma
        return s, True, None

    m = GUN_AY_YIL.match(s)
    if m:
        ay = _ay_no(m.group(2))
        iso = _iso(m.group(3), ay, m.group(1)) if ay else None
        if iso:
            return iso, True, None

    # Gün yok, ay/yıl var → muğlak ("Haziran 2026 sonu"). Ay hassasiyetini sakla.
    m = AY_YIL.match(s)
    if m:
        ay = _ay_no(m.group(1))
        if ay:
            return None, False, f"{int(m.group(2)):04d}-{ay:02d}"

    return None, False, None  # hiç çözülemedi → ham metin yine de korunur


def coz_basvuru(metin: str) -> tuple[str | None, str | None]:
    """'5 – 29 Oca 2026 (geç: 3 Şub)' → ('2026-01-05', '2026-01-29').

    NEDEN önce parantez temizliği: '(geç: 3 Şub)' içindeki tarih normal aralıkla
    karışıp yanlış bitiş üretiyor. Parantezli ek her zaman ATILIR.
    """
    if not metin:
        return None, None
    s = re.sub(r"\([^)]*\)", " ", metin)  # parantezli ekleri at

    m = ARALIK_FARKLI_AY.search(s)  # "28 Oca – 5 Şub 2026" (ay değişiyor)
    if m:
        g1, a1, g2, a2, yil = m.groups()
        ay1, ay2 = _ay_no(a1), _ay_no(a2)
        if ay1 and ay2:
            # Yıl yalnız sonda yazılı; ay geriye sarıyorsa (Ara→Oca) başlangıç bir önceki yıl.
            yil1 = int(yil) - 1 if ay1 > ay2 else int(yil)
            return _iso(yil1, ay1, g1), _iso(yil, ay2, g2)

    m = ARALIK_AYNI_AY.search(s)  # "5 – 29 Oca 2026" (tek ay)
    if m:
        g1, g2, ad, yil = m.groups()
        ay = _ay_no(ad)
        if ay:
            return _iso(yil, ay, g1), _iso(yil, ay, g2)

    return None, None


def normalize(kayit: dict) -> dict:
    """Tek sınav kaydını normalize et; anahtar sırasını koruyarak yeni sözlük üret."""
    # Türetilmiş alanları at → her çalıştırmada sıfırdan hesapla (idempotentlik).
    ham_sonuc = kayit.get("sonuc_ham") if kayit.get("sonuc_ham") is not None else kayit.get("sonuc")
    temiz = {k: v for k, v in kayit.items() if k not in TURETILEN}

    yeni: dict = {}
    for k, v in temiz.items():
        if k == "sinav":
            # NEDEN aynı çözücü: şu an hepsi ISO ama kaynak elle güncellenirse
            # "20 Haz 2026" gelebilir; sessizce bozulmasın.
            iso, kesin, _ = coz_tarih(v)
            yeni[k] = iso if iso else v
            if not iso:
                print(f"  ! sinav tarihi çözülemedi: {kayit.get('ad')} → {v!r}")
        elif k == "sonuc":
            iso, kesin, tahmini_ay = coz_tarih(ham_sonuc or "")
            yeni["sonuc"] = iso
            yeni["sonuc_ham"] = ham_sonuc
            yeni["sonuc_kesin"] = kesin
            if tahmini_ay:
                yeni["sonuc_tahmini_ay"] = tahmini_ay
        elif k == "basvuru":
            yeni["basvuru"] = v  # DOKUNMA — serbest metin aynen kalır
            bas, bit = coz_basvuru(v)
            yeni["basvuru_bas"] = bas
            yeni["basvuru_bit"] = bit
        else:
            yeni[k] = v
    return yeni


def main() -> None:
    ap = argparse.ArgumentParser(description="takvim-2026.json tarih alanlarını ISO'ya normalize et")
    ap.add_argument("--apply", action="store_true", help="Dosyaya yaz (varsayılan: dry-run)")
    a = ap.parse_args()

    ham_bayt = HEDEF.read_bytes()
    veri = json.loads(ham_bayt.decode("utf-8"))
    veri["sinavlar"] = [normalize(k) for k in veri["sinavlar"]]

    # NEDEN aynı serileştirme ayarı: mevcut dosya separators=(',',':') + sondaki
    # newline yok. Aynısını üretiyoruz ki gereksiz git diff'i çıkmasın.
    yeni_bayt = json.dumps(veri, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    # Rapor tablosu
    print(f"{'SINAV':<34} {'SONUC (ISO)':<12} {'KESIN':<6} {'TAHMINI AY':<11} HAM")
    print("-" * 100)
    for s in veri["sinavlar"]:
        print(
            f"{s['ad'][:33]:<34} {str(s['sonuc'] or '—'):<12} "
            f"{str(s['sonuc_kesin']).lower():<6} {s.get('sonuc_tahmini_ay') or '—':<11} {s['sonuc_ham']}"
        )
    kesin = sum(1 for s in veri["sinavlar"] if s["sonuc_kesin"])
    bsv = sum(1 for s in veri["sinavlar"] if s.get("basvuru_bas") and s.get("basvuru_bit"))
    print("-" * 100)
    print(f"Toplam {len(veri['sinavlar'])} sınav · sonuc_kesin=true: {kesin} · "
          f"belirsiz: {len(veri['sinavlar']) - kesin} · başvuru aralığı türetilen: {bsv}")

    if yeni_bayt == ham_bayt:
        print("Değişiklik yok (idempotent) — yazılmadı.")
        return
    if not a.apply:
        print("[dry-run] Yazılmadı. Uygulamak için: --apply")
        return

    # NEDEN yedek: dosya elle de düzenleniyor; hatalı normalizasyon geri alınabilsin.
    yedek = HEDEF.with_name(HEDEF.name + ".bak-" + datetime.now().strftime("%Y-%m-%d"))
    yedek.write_bytes(ham_bayt)
    HEDEF.write_bytes(yeni_bayt)
    print(f"✓ Yazıldı: {HEDEF}\n  Yedek : {yedek}")


if __name__ == "__main__":
    main()
