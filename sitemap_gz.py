# -*- coding: utf-8 -*-
"""sitemap_gz — sitemap `.xml` ve `.xml.gz` dosyalarını TEK ÇAĞRIDA yazan kanonik yardımcı.

KANONİK KAYNAK: /home/tekni/VS/servermimari/assets/sitemap_gz.py
Her site reposuna `faq_ld.py` / `meta_aciklama.py` / `lastmod.py` gibi KOPYALANIR
(sitemap'i üreten modülün yanına).

═══════════════════════════════════════════════════════════════════════════════
NEDEN VAR — 7 Eylül 2026 ölçümü
═══════════════════════════════════════════════════════════════════════════════
nginx'te `gzip_static` KAPALIYDI: her sitemap isteğinde dosya SIFIRDAN sıkıştırılıyordu.
ekapveri/sitemap-1.xml = 9,2 MB ham → 0,65 MB gzip (14 kat). Tek nginx 22 siteye
hizmet ettiği için bu CPU israfı YALNIZ o siteyi değil HEPSİNİ yavaşlatıyordu.

Googlebot yanıt süresi (16 günlük GSC ölçümü):
    ekapveri  ort 0,993 sn · p99 7,2 sn   → dizinlenme %0,01
    kapveri   ort 0,700 sn · p99 10,0 sn
    yakitveri ort 0,001 sn · p99 0,000 sn → dizinlenme %68,66
Google'ın kendi dokümanı: site yavaşlarsa tarama limiti (crawl rate) DÜŞER.

Ana oturumda `gzip_static on` açıldı ve ölçüldü: ekapveri sitemap 1,99 sn → 0,17 sn
(12 kat). Ama `.gz` dosyaları O AN ELLE üretilmişti.

═══════════════════════════════════════════════════════════════════════════════
⚠️ BU MODÜLÜN VAR OLMA SEBEBİ: BAYAT .gz = YANLIŞ İÇERİK
═══════════════════════════════════════════════════════════════════════════════
`gzip_static on` iken nginx `<ad>.xml` istendiğinde YANINDAKİ `<ad>.xml.gz` dosyasını
OLDUĞU GİBİ gönderir. **Tazelik KONTROL ETMEZ** — mtime karşılaştırması yoktur.
Yani `.xml` yeniden üretilip `.gz` eski kalırsa Google'a AYLARCA ESKİ SITEMAP servis
edilir ve bunu hiçbir hata mesajı haber vermez.

BU YÜZDEN: `.gz` her zaman `.xml` ile AYNI ANDA, AYNI KOD YOLUNDA üretilir.
Elle `gzip` çalıştırmak, ayrı bir cron'a bırakmak, "deploy sonrası hallederiz" demek
— hepsi bu hatayı geri getirir. Sitemap yazan her yer bu modülü çağırır.

═══════════════════════════════════════════════════════════════════════════════
GARANTİLER
═══════════════════════════════════════════════════════════════════════════════
 G1. `.xml` ve `.gz` tek çağrıda yazılır; ikisi ayrı kod yoluna DÜŞEMEZ.
 G2. `.gz` üretimi hata verirse eski `.gz` SİLİNİR (yarım/bayat dosya bırakılmaz).
     nginx o an `.gz` bulamaz → içeriği kendisi sıkıştırır: YAVAŞ ama DOĞRU.
     "Yanlış içerik" ile "yavaş" eşit ağırlıkta değildir; her zaman yavaşı seçeriz.
 G3. Yazım ATOMİK (`tmp` + `os.replace`) — yarım dosya servis edilmez.
 G4. SYMLINK GÜVENLİ: TrVeri deploy'unda `current/sitemap.xml` çoğu sitede
     `shared/sitemap.xml`e symlink'tir. Doğrudan `os.replace(tmp, yol)` symlink'i
     GERÇEK DOSYAYA ÇEVİRİR ve paylaşılan dosya bağını koparır. Bu yüzden önce
     `os.path.realpath()` ile hedef çözülür, değişim gerçek dosya üzerinde yapılır.
 G5. `.gz` yolu VERİLEN yola göre türetilir (`<verilen>.gz`), çözülmüş yola göre
     DEĞİL. Çünkü nginx `.gz`yi URI'den türettiği dosya yolunun yanında arar
     (`current/sitemap.xml.gz`), symlink hedefinin yanında değil.
 G6. `mtime=0` — aynı XML her zaman BAYT BAYT aynı `.gz` üretir. Sitemap'i git'te
     tutan repolarda (ör. SuKesintisiVeri) içerik değişmediyse sahte diff çıkmaz.

═══════════════════════════════════════════════════════════════════════════════
KULLANIM
═══════════════════════════════════════════════════════════════════════════════
    from sitemap_gz import yaz, yetim_temizle       # veya: from .sitemap_gz import ...

    bilgi = yaz(ROOT / "sitemap.xml", xml_metni)
    # {'xml': 274844, 'gz': 9563, 'oran': 28.7, 'gz_yol': '.../sitemap.xml.gz'}

    # Sitemap INDEX kullanan sitelerde, artık üretilmeyen alt sitemap'lerin
    # `.gz` artıklarını temizle (yetim `.gz` = nginx'in servis ettiği ölü içerik):
    yetim_temizle(ROOT)

    # XML'i BAŞKA bir kod yolu yazıyorsa (ör. `W()`/`write()` yardımcıları, harici
    # üretici) tüm dizini tek çağrıda eşitle — `.xml`e DOKUNMADAN `.gz`leri tazeler
    # + yetimleri siler. Sitemap üretiminin EN SONUNDA çağrılır:
    from sitemap_gz import esitle
    esitle(ROOT)                                   # → (üretilen_gz, silinen_yetim)
"""
from __future__ import annotations

import gzip
import io
import os
from pathlib import Path

__all__ = ["yaz", "gz_yaz", "gz_tazele", "esitle", "dogrula", "yetim_temizle", "GZ_SEVIYE"]

# 9 = en yüksek sıkıştırma. Sitemap günde 1-2 kez üretilir, binlerce kez okunur →
# üretimde bir kerelik CPU maliyeti, her istekte kazanılan bant genişliğine değer.
GZ_SEVIYE = 9


def _gercek(yol: Path) -> Path:
    """Symlink'i çöz (G4). Dosya yoksa `realpath` yolu aynen döndürür."""
    return Path(os.path.realpath(str(yol)))


def _atomik_yaz(yol: Path, veri: bytes) -> int:
    """`veri`yi `yol`a atomik yaz (G3) — symlink hedefini koruyarak (G4)."""
    hedef = _gercek(yol)
    hedef.parent.mkdir(parents=True, exist_ok=True)
    gecici = hedef.with_name(hedef.name + ".tmp")
    try:
        with open(gecici, "wb") as f:
            f.write(veri)
            f.flush()
            os.fsync(f.fileno())
        os.replace(gecici, hedef)          # aynı dizin → atomik rename
    except BaseException:
        try:
            gecici.unlink()
        except OSError:
            pass
        raise
    return len(veri)


def _sikistir(veri: bytes, seviye: int = GZ_SEVIYE) -> bytes:
    """Deterministik gzip: mtime=0, dosya adı gömülmez (G6)."""
    tampon = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", compresslevel=seviye,
                       fileobj=tampon, mtime=0) as g:
        g.write(veri)
    return tampon.getvalue()


def _gz_yolu(xml_yol: Path) -> Path:
    """`<verilen>.gz` — çözülmüş yola göre DEĞİL (G5)."""
    return xml_yol.with_name(xml_yol.name + ".gz")


def _gz_sil(gz_yol: Path) -> None:
    """`.gz`yi kaldır. Symlink ise HEM link HEM hedef gider (bayat kalmasın)."""
    for aday in (_gercek(gz_yol), gz_yol):
        try:
            aday.unlink()
        except (OSError, FileNotFoundError):
            pass


def yaz(xml_yol, xml_metin: str, seviye: int = GZ_SEVIYE) -> dict:
    """Sitemap'i `.xml` + `.xml.gz` olarak birlikte yaz.

    ⚠ `.gz` HER ZAMAN `.xml` ile aynı anda güncellenir; bayat `.gz` nginx tarafından
      (gzip_static) tazelik kontrolü YAPILMADAN servis edilir → yanlış içerik.

    Dönüş: {'xml': bayt, 'gz': bayt, 'oran': %, 'gz_yol': str|None}
    """
    xml_yol = Path(xml_yol)
    veri = xml_metin.encode("utf-8")
    xml_bayt = _atomik_yaz(xml_yol, veri)

    gz_yol = _gz_yolu(xml_yol)
    try:
        gz_bayt = _atomik_yaz(gz_yol, _sikistir(veri, seviye))
    except Exception:
        # G2 — .gz üretilemediyse eskisini BIRAKMA. nginx .gz bulamayınca içeriği
        # kendisi sıkıştırır: yavaş ama DOĞRU. Bayat .gz sessizce yanlış içerik verir.
        _gz_sil(gz_yol)
        return {"xml": xml_bayt, "gz": 0, "oran": 0.0, "gz_yol": None}

    return {
        "xml": xml_bayt,
        "gz": gz_bayt,
        "oran": round(100.0 * gz_bayt / xml_bayt, 1) if xml_bayt else 0.0,
        "gz_yol": str(gz_yol),
    }


def gz_yaz(xml_yol, seviye: int = GZ_SEVIYE) -> dict:
    """XML metni elde değil, dosya zaten diskteyse: `.gz`yi diskteki `.xml`den üret.

    `yaz()` tercih edilir (tek çağrı, tek kod yolu). Bu, XML'i başka bir katmanın
    (ör. shutil.copy ile taşınan staging dosyası) yazdığı durumlar içindir.
    """
    xml_yol = Path(xml_yol)
    gercek = _gercek(xml_yol)
    if not gercek.exists():
        _gz_sil(_gz_yolu(xml_yol))      # XML yoksa .gz de kalmamalı (yetim)
        return {"xml": 0, "gz": 0, "oran": 0.0, "gz_yol": None}
    return yaz(xml_yol, gercek.read_text(encoding="utf-8"), seviye)


def yetim_temizle(dizin, desen: str = "sitemap*.xml.gz") -> list[str]:
    """`.xml` karşılığı KALMAMIŞ `.gz` dosyalarını sil.

    Sitemap kümesi değişince (ör. index modunda alt sitemap sayısı azalınca) eski
    `.gz` dosyası dizinde kalırsa nginx onu servis etmeye devam eder — kaldırılmış
    bir sitemap sonsuza kadar canlı görünür. Dönüş: silinen dosya yolları.
    """
    dizin = Path(dizin)
    silinen: list[str] = []
    if not dizin.is_dir():
        return silinen
    for gz in sorted(dizin.glob(desen)):
        xml = gz.with_name(gz.name[:-3])          # ".gz" ekini at
        if _gercek(xml).exists():
            continue
        _gz_sil(gz)
        silinen.append(str(gz))
    return silinen


# ═══════════════════════════════════════════════════════════════════════════════
# DİZİN EŞİTLEME — XML'i BAŞKA bir kod yolu yazdığında
# ═══════════════════════════════════════════════════════════════════════════════
# ⚠ Tercih SIRASI: `yaz()` > `esitle()`. `yaz()` tek çağrıda ikisini birden yazar
# (G1) ve iki dosyanın ayrışması İMKÂNSIZ olur. `esitle()` ise sitemap'i kendi
# yardımcısıyla yazan (DoktorVeri `W()`, HastaneVeri `write()`, çok dilli döngüler)
# üreticiler için: TÜM dizini tarar, her `.xml`in `.gz`sini tazeler, yetimleri siler.
# Çağrı yeri KRİTİK — sitemap yazımının HEMEN ARDINDAN, aynı fonksiyonun içinde.

def gz_tazele(xml_yol, seviye: int = GZ_SEVIYE) -> dict:
    """Diskteki `.xml`den `.gz` üret — `.xml` dosyasına DOKUNMADAN.

    `gz_yaz()`ten farkı: XML'i yeniden YAZMAZ. Bu bilinçli bir tercihtir —
    içeriği aynı olan bir sitemap'i yeniden yazmak `mtime`ı ilerletir, nginx'in
    `Last-Modified`/304 koşullu istek katmanı (trveri-304-kosullu-istek.conf) o
    dosyayı "değişmiş" sayar ve Google 9 MB'lık sitemap'i boşuna yeniden indirir.
    """
    xml_yol = Path(xml_yol)
    gercek = _gercek(xml_yol)
    gz_yol = _gz_yolu(xml_yol)
    if not gercek.exists():
        _gz_sil(gz_yol)                       # XML yoksa .gz de kalmamalı (yetim)
        return {"xml": 0, "gz": 0, "oran": 0.0, "gz_yol": None}
    veri = gercek.read_bytes()
    try:
        gz_bayt = _atomik_yaz(gz_yol, _sikistir(veri, seviye))
    except Exception:
        _gz_sil(gz_yol)                       # G2 — bayat/yarım .gz BIRAKILMAZ
        return {"xml": len(veri), "gz": 0, "oran": 0.0, "gz_yol": None}
    return {"xml": len(veri), "gz": gz_bayt,
            "oran": round(100.0 * gz_bayt / len(veri), 1) if veri else 0.0,
            "gz_yol": str(gz_yol)}


def dogrula(xml_yol) -> bool:
    """`.gz` açıldığında `.xml` ile BİREBİR aynı mı? (denetim/test kapısı)"""
    xml_yol = Path(xml_yol)
    gz_yol = _gz_yolu(xml_yol)
    try:
        return gzip.decompress(_gercek(gz_yol).read_bytes()) == _gercek(xml_yol).read_bytes()
    except (OSError, EOFError, gzip.BadGzipFile):
        return False


def esitle(dizin, desen: str = "sitemap*.xml", sessiz: bool = False) -> tuple[int, int]:
    """Dizindeki TÜM sitemap'ler için `.gz` tazele + YETİM `.gz`leri sil.

    Dönüş: (üretilen_gz, silinen_yetim_gz).

    ⚠ KOŞULSUZ tazeler — "değişmemiştir" tahmini YAPILMAZ. Yanlış tahminin bedeli
      arama motoruna aylarca yanlış sitemap servis etmektir; yeniden sıkıştırmanın
      bedeli ise build'de birkaç saniyedir. İkisi eşit ağırlıkta değildir.
    """
    dizin = Path(dizin)
    if not dizin.is_dir():
        return (0, 0)
    uretilen = 0
    for xml in sorted(dizin.glob(desen)):
        if xml.name.endswith(".gz"):
            continue
        if gz_tazele(xml)["gz_yol"]:
            uretilen += 1
    silinen = len(yetim_temizle(dizin))
    if not sessiz and (uretilen or silinen):
        print(f"  [sitemap-gz] {uretilen} .gz tazelendi"
              + (f" · {silinen} yetim .gz silindi" if silinen else "")
              + "  (nginx gzip_static)")
    return (uretilen, silinen)
