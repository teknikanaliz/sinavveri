#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sitemap .gz üretimi — nginx `gzip_static` için ÖN-SIKIŞTIRILMIŞ ikiz dosya.

KANONİK KAYNAK: servermimari/assets/sitemap_gz.py
Her site reposuna `faq_ld.py` / `meta_aciklama.py` gibi KOPYALANIR; kod tek noktada
değişir, kopyalar yenilenir.

── NEDEN VAR (2026-09-07 ölçümü) ─────────────────────────────────────────────────
nginx `gzip_static` kapalıyken 9,2 MB'lık bir sitemap her istekte SIFIRDAN
sıkıştırılıyordu (ekapveri/sitemap-1.xml: 9,2 MB → 0,65 MB, 14 kat). Tek nginx 22
siteye hizmet ettiği için bu CPU israfı yalnız o siteyi değil HEPSİNİ yavaşlatıyordu:
Googlebot yanıt süresi ekapveri'de ortalama 0,993 sn / p99 7,2 sn iken sitemap'i
küçük olan yakitveri'de 0,001 sn idi; dizinlenme oranı %0,01'e karşı %68,66.
Google'ın kendi dokümanı: "site yavaşlarsa tarama limiti düşer."
`gzip_static on` açıldı ve ölçüldü: ekapveri sitemap 1,99 sn → 0,17 sn (12 kat).

── ⚠ KRİTİK KURAL: .gz İLE .xml AYNI ANDA GÜNCELLENİR ────────────────────────────
nginx `gzip_static`, istemci gzip kabul ediyorsa `<ad>.xml.gz` dosyasını `.xml`in
İÇERİĞİNİ HİÇ OKUMADAN servis eder. Yani BAYAT bir `.gz` = arama motoruna YANLIŞ
İÇERİK sunmak (silinmiş URL'ler, eksik yeni sayfalar) demektir ve hiçbir yerde
hata olarak görünmez. Bu yüzden `.gz` üretimi **build'in kendisine** bağlanır:
sitemap yazan her kod yolu, yazdıktan hemen sonra bu modülü çağırır.
`.gz`yi elle üretmek KALICI ÇÖZÜM DEĞİLDİR — bir sonraki build .xml'i yeniler ve
elle üretilmiş .gz bayat kalır.

Kullanım (üretimin en sonunda, tek satır):

    from sitemap_gz import esitle          # ya da: from .sitemap_gz import esitle
    esitle(OUTPUT_DIR)                     # sitemap*.xml → sitemap*.xml.gz + yetim temizliği

Tek dosya için:

    from sitemap_gz import gz_yaz
    gz_yaz(OUTPUT_DIR / "sitemap-ilac.xml")
"""
from __future__ import annotations

import gzip
import os
from pathlib import Path

SEVIYE = 9          # en yüksek sıkıştırma: dosya bir kez üretilir, milyonlarca kez okunur
DESEN = "sitemap*.xml"


def _gercek(yol: Path) -> Path:
    """Symlink ise işaret ettiği GERÇEK dosyayı döndür.

    ⚠ Bazı sitelerde (NobetciEczaneVeri) sitemap'ler `shared/` altında durur ve
    release dizininde yalnız symlink vardır. Symlink'in üzerine düz dosya yazmak
    paylaşım düzenini bozar → hedefe yazılır, symlink olduğu gibi kalır.
    """
    return yol.resolve() if yol.is_symlink() else yol


def _sil(yol: Path) -> bool:
    """Dosyayı (symlink ise hedefiyle birlikte) sil. Silindi mi döndürür."""
    silindi = False
    try:
        if yol.is_symlink():
            hedef = yol.resolve()
            yol.unlink()
            silindi = True
            if hedef.exists():
                hedef.unlink()
        elif yol.exists():
            yol.unlink()
            silindi = True
    except OSError as e:
        print(f"  [sitemap-gz] {yol.name} silinemedi: {e}")
    return silindi


def gz_yaz(xml_yolu, seviye: int = SEVIYE) -> Path | None:
    """`<ad>.xml` → `<ad>.xml.gz` (atomik). Yazılan .gz yolunu döndürür.

    Atomik: geçici dosyaya yazılıp `os.replace` ile taşınır → yarım kalan bir
    build asla yarım .gz bırakmaz (nginx yarım .gz'yi bozuk içerik olarak sunardı).
    `mtime=0`: gzip başlığına zaman damgası yazılmaz → aynı XML her zaman aynı
    baytları üretir (gereksiz git commit'i / deploy farkı olmaz).
    """
    xml_yolu = Path(xml_yolu)
    if not xml_yolu.exists():           # symlink'i izler
        return None
    veri = xml_yolu.read_bytes()
    gz_yolu = xml_yolu.with_name(xml_yolu.name + ".gz")
    hedef = _gercek(gz_yolu)
    hedef.parent.mkdir(parents=True, exist_ok=True)
    gecici = hedef.with_name(f".{hedef.name}.tmp{os.getpid()}")
    try:
        gecici.write_bytes(gzip.compress(veri, seviye, mtime=0))
        os.replace(gecici, hedef)       # atomik: aynı dosya sistemi
    except OSError as e:
        print(f"  [sitemap-gz] {xml_yolu.name}: {e}")
        try:
            gecici.unlink(missing_ok=True)
        except OSError:
            pass
        return None
    return gz_yolu


def dogrula(xml_yolu) -> bool:
    """`.gz` açıldığında `.xml` ile BİREBİR aynı mı? (denetim/test için)"""
    xml_yolu = Path(xml_yolu)
    gz_yolu = xml_yolu.with_name(xml_yolu.name + ".gz")
    if not (xml_yolu.exists() and gz_yolu.exists()):
        return False
    try:
        return gzip.decompress(gz_yolu.read_bytes()) == xml_yolu.read_bytes()
    except (OSError, EOFError, gzip.BadGzipFile):
        return False


def esitle(dizin, desen: str = DESEN, sessiz: bool = False) -> tuple[int, int]:
    """Dizindeki TÜM sitemap'ler için .gz üret + YETİM .gz'leri sil.

    Dönüş: (üretilen_gz, silinen_yetim_gz).

    ⚠ Sitemap üretiminin EN SONUNDA çağrılır: o build'de yazılan her .xml için
    .gz yeniden üretilir (koşulsuz — "değişmedi" tahmini yapılmaz, çünkü yanlış
    tahminin bedeli arama motoruna yanlış içerik sunmaktır).
    ⚠ Yetim temizliği: artık üretilmeyen bir sitemap silindiğinde .gz'si de gider;
    aksi hâlde nginx var olmayan bir .xml için bayat .gz'yi 200 ile sunmaya devam eder.
    """
    dizin = Path(dizin)
    if not dizin.is_dir():
        return (0, 0)
    uretilen = 0
    for xml in sorted(dizin.glob(desen)):
        if xml.name.endswith(".gz"):
            continue
        if gz_yaz(xml) is not None:
            uretilen += 1
    silinen = 0
    for gz in sorted(dizin.glob(desen + ".gz")):
        if not gz.with_name(gz.name[:-3]).exists():
            if _sil(gz):
                silinen += 1
    if not sessiz and (uretilen or silinen):
        print(f"  [sitemap-gz] {uretilen} .gz üretildi"
              + (f" · {silinen} yetim .gz silindi" if silinen else "")
              + "  (nginx gzip_static)")
    return (uretilen, silinen)


if __name__ == "__main__":                       # elle: python3 sitemap_gz.py <dizin>
    import sys
    hedef_dizin = sys.argv[1] if len(sys.argv) > 1 else "."
    u, s = esitle(hedef_dizin)
    print(f"{hedef_dizin}: {u} .gz üretildi, {s} yetim silindi")
