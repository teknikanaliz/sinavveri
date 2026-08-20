#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""meta_aciklama.py — KANONİK meta açıklama üreticisi (TÜM SİTELER, HER SAYFA).

GLOBAL KURAL (2026-08-20, kullanıcı talimatı): üretilen HER sayfanın
`<meta name="description">` değeri **en az 150, en çok 165 karakter** olacak.
Tek bir yerde tanımlıdır; her sitenin generator'ı bunu çağırır — böylece
"bu sitede kısa kalmış" sorunuyla bir daha tek tek uğraşılmaz.

NEDEN 150-165:
  • <150 → Bing Webmaster açıkça "Meta descriptions on many pages are too short"
    uyarısı veriyor; Google/Bing kısa açıklamayı KULLANMAYIP kendi snippet'ini
    üretiyor → SERP'te ne yazacağını biz belirlemiyoruz (tıklama kaybı).
  • >165 → masaüstü SERP'te kesiliyor (~920px ≈ 155-165 karakter); sonu "..."
    olarak görünüyor, cümle yarım kalıyor.
  • AI cevap motorları (GEO) sayfa özetini description'dan da besliyor; kısa
    açıklama = zayıf alıntı sinyali.

KULLANIM (iki biçim):

  1) Parça parça kur (tercih edilen — uydurma yok, sayfanın kendi verisi):
       from meta_aciklama import kur
       desc = kur(["Ankara Çankaya nöbetçi eczaneleri",
                   "20 Ağustos 2026 gece nöbeti",
                   "adres, telefon ve yol tarifi"],
                  dolgu=["Liste her gün 18:00'de güncellenir.",
                         "En yakın eczaneyi haritadan görebilirsiniz."])

  2) Mevcut metni sınıra çek:
       from meta_aciklama import duzelt
       desc = duzelt(mevcut_metin, dolgu=["..."])

  3) Denetle (test/CI):
       from meta_aciklama import dogrula
       assert dogrula(desc)[0], dogrula(desc)[1]

⚠ DOLGU METNİ UYDURMA DEĞİLDİR: `dolgu` sayfanın GERÇEKTEN sunduğu şeyi anlatan
  sabit cümlelerdir (ne var, ne sıklıkla güncellenir, kaynağı ne). Olmayan bir
  rakam/olgu EKLEME — meta yanlışsa Google onu kullanmaz, güven de kaybedilir.
"""
from __future__ import annotations

import html as _html
import re

MIN = 150
MAX = 165

# ⚠ CJK İSTİSNASI: Google/Bing snippet'i KARAKTERE değil PİKSEL genişliğine göre keser
# (masaüstünde ~920px). Çince/Japonca/Korece karakterler Latin harfin ~2 katı genişlikte
# olduğundan 150 karakterlik Çince meta SERP'te iki katı yer kaplar ve kesilir. Bu
# dillerde eşdeğer hedef ~70-80 karakterdir. 150 kuralını CJK'ya uygulamak, düzeltmek
# istediğimiz sorunun aynısını (kesik snippet) ters yönden üretirdi.
CJK_MIN = 70
CJK_MAX = 80
CJK_DILLER = ("zh", "ja", "ko")


def sinirlar(dil: str = "tr") -> tuple:
    """(min, max) — dile göre karakter sınırı. Tek nokta: eşik başka yerde yazılmaz."""
    return (CJK_MIN, CJK_MAX) if (dil or "tr").split("-")[0].lower() in CJK_DILLER else (MIN, MAX)

# Hiç dolgu verilmediğinde kullanılan son çare — site-nötr, iddiasız.
# ⚠ MERDİVEN: dolgu cümleleri UZUNDAN KISAYA sıralı ve aralarındaki uzunluk farkı
# 15 karakterden küçük tutulur. Neden: hedef pencere 15 karakter geniş (150-165);
# elde yalnız uzun cümle varsa taban 146 karakterken cümle yarıda kesilir ve SERP'te
# "…Bildirimin tam…" gibi yarım biten meta görünür. Kısa basamaklar bunu önler.
#
# ⚠ ÇOK DİLLİ: dolgu sayfanın DİLİNDE olmalı. Türkçe dolgu İngilizce/Almanca sayfaya
# yapıştırılırsa arama motoru meta'yı sayfa diliyle uyumsuz görür ve KULLANMAZ —
# kısa meta'yı düzeltirken snippet'i büsbütün kaybederdik.
DOLGU_DILE_GORE = {
    # ⚠ Basamaklar birbirini TEKRAR ETMEMELİ: aç gözlü arama iki cümleyi yan yana
    # koyabiliyor ("…bu sayfada yer alıyor. Ayrıntılı bilgi bu sayfada yer alıyor.")
    # ve SERP'te bariz doldurma gibi görünüyordu.
    "tr": (
        "Güncel veriler, ayrıntılı tablo ve açıklamalar bu sayfada yer alıyor.",
        "Bilgiler resmî kaynaklardan derlenir, düzenli olarak güncellenir.",
        "Kaynak ve güncelleme bilgisi sayfanın altında.",
        "Veriler resmî kaynaklardan derlenir.",
        "Liste düzenli güncellenir.",
        "Düzenli güncellenir.",
    ),
    "en": (
        "Up-to-date figures, detailed tables and explanations are on this page.",
        "Data is compiled from official sources and updated regularly.",
        "Source and update notes are at the bottom.",
        "Data comes from official sources.",
        "The list is updated regularly.",
        "Updated regularly.",
    ),
    "de": (
        "Aktuelle Daten, detaillierte Tabellen und Erläuterungen auf dieser Seite.",
        "Die Angaben stammen aus amtlichen Quellen und werden regelmäßig aktualisiert.",
        "Die Angaben stammen aus amtlichen Quellen.",
        "Ausführliche Informationen auf dieser Seite.",
        "Details auf dieser Seite.",
        "Mehr dazu hier.",
    ),
    "fr": (
        "Données à jour, tableaux détaillés et explications sur cette page.",
        "Les informations proviennent de sources officielles, mises à jour régulièrement.",
        "Les informations proviennent de sources officielles.",
        "Informations détaillées sur cette page.",
        "Détails sur cette page.",
        "Voir les détails ici.",
    ),
    "es": (
        "Datos actualizados, tablas detalladas y explicaciones en esta página.",
        "La información procede de fuentes oficiales y se actualiza periódicamente.",
        "La información procede de fuentes oficiales.",
        "Información detallada en esta página.",
        "Detalles en esta página.",
        "Ver detalles aquí.",
    ),
    "ru": (
        "Актуальные данные, подробные таблицы и пояснения на этой странице.",
        "Информация собрана из официальных источников и регулярно обновляется.",
        "Информация собрана из официальных источников.",
        "Подробная информация на этой странице.",
        "Подробности на этой странице.",
        "Подробности здесь.",
    ),
    "ar": (
        "بيانات محدثة وجداول تفصيلية وشروحات كاملة متوفرة في هذه الصفحة.",
        "المعلومات مجمعة من مصادر رسمية ويتم تحديثها بانتظام.",
        "المعلومات مجمعة من مصادر رسمية.",
        "معلومات تفصيلية في هذه الصفحة.",
        "التفاصيل في هذه الصفحة.",
        "التفاصيل هنا.",
    ),
    "zh": (
        "本页提供最新数据、详细表格与完整说明，可直接查询与比较。",
        "信息来自官方渠道，并定期更新维护。",
        "信息来自官方渠道，定期更新。",
        "本页提供详细信息。",
        "详情见本页。",
        "详情如下。",
    ),
    "pl": (
        "Aktualne dane, szczegółowe tabele i wyjaśnienia znajdziesz na tej stronie.",
        "Informacje pochodzą ze źródeł urzędowych i są regularnie aktualizowane.",
        "Informacje pochodzą ze źródeł urzędowych.",
        "Szczegółowe informacje na tej stronie.",
        "Szczegóły na tej stronie.",
        "Szczegóły poniżej.",
    ),
    "fa": (
        "داده‌های به‌روز، جدول‌های تفصیلی و توضیحات کامل در این صفحه آمده است.",
        "اطلاعات از منابع رسمی گردآوری و به‌طور منظم به‌روزرسانی می‌شود.",
        "اطلاعات از منابع رسمی گردآوری می‌شود.",
        "اطلاعات تفصیلی در این صفحه است.",
        "جزئیات در این صفحه.",
        "جزئیات اینجاست.",
    ),
    "ko": (
        "최신 데이터와 상세 표, 설명을 이 페이지에서 확인할 수 있습니다.",
        "정보는 공식 출처에서 수집되며 정기적으로 갱신됩니다.",
        "정보는 공식 출처에서 수집됩니다.",
        "자세한 내용은 이 페이지에 있습니다.",
        "자세한 내용은 아래에.",
        "상세 정보 참조.",
    ),
    "ja": (
        "最新のデータ、詳細な表と解説をこのページで確認できます。",
        "情報は公式資料に基づき、定期的に更新されます。",
        "情報は公式資料に基づきます。",
        "詳細はこのページに記載。",
        "詳細は本ページに。",
        "詳細はこちら。",
    ),
}
VARSAYILAN_DOLGU = DOLGU_DILE_GORE["tr"]


def _kirp(metin: str, dil: str = "tr") -> str:
    """MAX'ı aşan metni KELİME SINIRINDA keser; sonuç HER ZAMAN <= MAX kalır.

    ⚠ Ekleme yapan "…" karakteri de uzunluğa dahildir (2026-08-20'de 2.000
    gerçek bildirimle ölçüldü: pencere MAX+1 alınınca 112 sayfa 166 karaktere
    taşıyordu). Bu yüzden pencere MAX, sonuç ayrıca MAX'a kırpılır.
    """
    alt, ust = sinirlar(dil)
    if len(metin) <= ust:
        return metin
    pencere = metin[:ust]
    bosluk = pencere.rfind(" ")
    # CJK'da kelime arası boşluk yoktur → doğrudan karakter sınırında kesilir.
    aday = (pencere[:bosluk] if bosluk >= alt else metin[:ust - 1]).rstrip(" ,;:.、，。") + "…"
    return aday[:ust]


def _cumle(x: str) -> str:
    x = " ".join(str(x).split()).strip()
    if x and not x.endswith((".", "!", "?", "…", "。", "！", "？", "、")):
        x += "."
    return x


def _en_iyi(metin: str, adaylar: list, dil: str = "tr") -> str | None:
    """Aralığa (150-165) KESİLMEDEN oturan dolgu birleşimini bulur.

    Önce tek cümle, sonra ikili birleşim denenir; oturanlar arasından EN UZUN
    olan seçilir (aynı yeri en çok bilgiyle doldur). Hiçbiri oturmazsa None.
    """
    alt, ust = sinirlar(dil)
    ara = "" if (dil or "tr").split("-")[0].lower() in CJK_DILLER else " "
    tek = [m for m in ((metin + ara + c).strip() for c in adaylar) if alt <= len(m) <= ust]
    if tek:
        return max(tek, key=len)
    ikili = []
    for i, a in enumerate(adaylar):
        for j, b in enumerate(adaylar):
            if i == j:
                continue
            m = (metin + ara + a + ara + b).strip()
            if alt <= len(m) <= ust:
                ikili.append(m)
    return max(ikili, key=len) if ikili else None


def kur(parcalar, dolgu=None, dil: str = "tr") -> str:
    """`parcalar` (öncelik sırasıyla bilgi kırıntıları) → 150-165 karakter meta.

    Parçalar noktayla birleştirilir. MIN'e ulaşılmadıysa dolgu cümleleri eklenir.

    ⚠ DOLGU SEÇİMİ AKILLIDIR: önce aralığa KESİLMEDEN oturan bir birleşim aranır
    (cümle yarıda kalmasın diye). Yalnızca hiçbir birleşim oturmazsa aç gözlü
    eklenip kelime sınırında kesilir. Amaç: "…Bildirimin tam…" gibi yarım biten
    meta üretmemek — SERP'te yarım cümle güven kaybettirir.
    """
    parcalar = [str(p).strip().rstrip(".。") for p in (parcalar or []) if p and str(p).strip()]
    alt, _ust = sinirlar(dil)
    cjk = (dil or "tr").split("-")[0].lower() in CJK_DILLER
    if not parcalar:
        metin = ""
    elif cjk:                                  # CJK'da cümle ayracı 。 ve boşluk yok
        metin = "".join(p + "。" for p in parcalar)
    else:
        metin = " ".join((". ".join(parcalar) + ".").split())
    if len(metin) >= alt:
        return _kirp(metin, dil)

    varsayilan = DOLGU_DILE_GORE.get((dil or "tr").split("-")[0].lower(), VARSAYILAN_DOLGU)
    adaylar = [_cumle(c) for c in (list(dolgu or ()) + list(varsayilan)) if str(c).strip()]
    oturan = _en_iyi(metin, adaylar, dil)
    if oturan:
        return oturan

    for cumle in adaylar:                      # son çare: aç gözlü + kelime sınırında kes
        if len(metin) >= alt:
            break
        metin = (metin + ("" if cjk else " ") + cumle).strip()
    return _kirp(metin, dil)


def duzelt(metin: str, dolgu=None, dil: str = "tr") -> str:
    """Hazır bir meta metnini 150-165 aralığına çeker (tek noktada uygulanacak biçim)."""
    return kur([metin], dolgu=dolgu, dil=dil)


def dogrula(metin: str, dil: str = "tr"):
    """(uygun_mu, mesaj) — denetim/CI için. HTML entity'leri çözülmüş metin ver."""
    alt, ust = sinirlar(dil)
    n = len(metin or "")
    if n < alt:
        return False, f"meta açıklama {n} karakter — asgari {alt} (GLOBAL KURAL, dil={dil})"
    if n > ust:
        return False, f"meta açıklama {n} karakter — azami {ust} (SERP'te kesilir, dil={dil})"
    return True, f"{n} karakter ✓"


# ── Üretilmiş HTML üzerinde son-kontrol ───────────────────────────────────
_META_RE = re.compile(
    r'(<meta\s[^>]*?name\s*=\s*["\']?description["\']?[^>]*?content\s*=\s*")([^"]*)(")',
    re.I)
_META_RE2 = re.compile(
    r'(<meta\s[^>]*?content\s*=\s*")([^"]*)("[^>]*?name\s*=\s*["\']?description["\']?)',
    re.I)
_LANG_RE = re.compile(r'<html[^>]*?\slang\s*=\s*["\']?([A-Za-z-]+)', re.I)


def html_duzelt(sayfa: str, dil: str | None = None, dolgu=None) -> str:
    """Üretilmiş HTML'deki meta description'ı kurala çeker (SON KONTROL kapısı).

    NE ZAMAN KULLANILIR: sitede tek bir <head> üreticisi yoksa ve meta onlarca
    şablon/blok içinde dağılmışsa. Sayfayı diske yazan tek fonksiyona bir satır
    eklemek, her şablonu tek tek düzeltmekten hem daha kısa hem daha kalıcıdır —
    yeni şablon eklendiğinde de kural kendiliğinden uygulanır.

    ⚠ Entity güvenli: içerik önce çözülür (uzunluk GERÇEK karakterle ölçülsün),
    düzeltilir, sonra yeniden kaçışlanır. Çözmeden ölçmek "Türkiye&#39;nin"i
    13 karakter fazla sayardı.
    """
    if not sayfa:
        return sayfa
    if dil is None:
        m = _LANG_RE.search(sayfa)
        dil = m.group(1) if m else "tr"

    def _yenile(m):
        ic = _html.unescape(m.group(2))
        return m.group(1) + _html.escape(kur([ic], dolgu=dolgu, dil=dil), quote=True) + m.group(3)

    yeni, n = _META_RE.subn(_yenile, sayfa, count=1)
    if n == 0:                                   # content= önce, name= sonra yazılmış olabilir
        yeni = _META_RE2.sub(
            lambda m: m.group(1) + _html.escape(kur([_html.unescape(m.group(2))],
                                                    dolgu=dolgu, dil=dil), quote=True) + m.group(3),
            sayfa, count=1)
    return yeni
