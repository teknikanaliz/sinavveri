# -*- coding: utf-8 -*-
"""faq_ld.py — TrVeri ortak FAQ bileşeni: GÖRÜNÜR blok + eşleşen FAQPage JSON-LD.

NEDEN VAR (2026-08-19): GEO ölçümünde ağın en zayıf boyutu "Yapısal işaretleme"
(%37) ve en yaygın eksik "FAQPage şeması yok" (25 site). FAQPage, AI cevap
motorlarının (AI Overviews · ChatGPT · Perplexity · Claude) en verimli alıntı
yüzeyi: soru-cevap çiftleri kendi kendine yeten pasajlar olduğu için doğrudan
alıntılanabiliyor.

⚠ GOOGLE KURALI: JSON-LD'deki soru/cevap sayfada GÖRÜNÜR de olmalı. Görünmeyen
içeriği işaretlemek yapılandırılmış veri ihlalidir. Bu yüzden bu modül ikisini
BİRLİKTE üretir — ayrı ayrı kullanmayın.

KULLANIM
    from faq_ld import faq_block
    html, ld = faq_block([
        ("Nöbetçi eczane nasıl bulunur?", "İlinizi ve ilçenizi seçin; bugünün nöbetçi listesi …"),
        ("Nöbet saatleri kaçta başlar?", "Çoğu ilde 18:00'de başlar, ertesi sabah 09:00'da biter."),
    ])
    # html → sayfaya (ana veri bloğunun altına), ld → <script type="application/ld+json">

TASARIM NOTLARI
 · Cevaplar 40-60 kelimede doğrudan yanıt vermeli (AI alıntı optimumu 134-167 kelime/pasaj).
 · <details>/<summary> kullanılır: JS'siz açılır, mobil dostu, içerik ham HTML'de
   (AI botları JS render ETMEZ — SSR şart).
 · Soru <summary> İÇİNDE <h3> olarak sarılır. HTML spesifikasyonu summary içinde
   başlık içeriğine izin verir; görsel olarak hiçbir şey değişmez (CSS inline yapar).
   Sebep: soru artık GERÇEK bir başlık — AI cevap motorları pasajı başlıktan çıkarır,
   sadece <summary> olduğunda başlık hiyerarşisinde görünmüyordu (2026-08-20 ölçüldü:
   FAQ eklenen 10 sitede "soru biçimli başlık" sinyali 0 kalmıştı).
 · CSS sitenin tema değişkenlerini devralır (--border/--muted/--accent), fallback'li.
"""
import html as _html
import json as _json

__all__ = ["faq_block", "faq_html", "faq_jsonld", "FAQ_CSS"]

FAQ_CSS = """
.tv-faq{margin:26px 0}
.tv-faq h2{font-size:19px;margin:0 0 10px}
.tv-faq details{border:1px solid var(--border,#e2e8f0);border-radius:8px;margin:8px 0;background:var(--card,#fff)}
.tv-faq summary{cursor:pointer;padding:11px 14px;font-weight:600;font-size:14px;list-style:none}
.tv-faq summary h3{display:inline;font-size:inherit;font-weight:inherit;margin:0;line-height:inherit}
.tv-faq summary::-webkit-details-marker{display:none}
.tv-faq summary::after{content:'+';float:right;color:var(--muted,#64748b);font-weight:700}
.tv-faq details[open] summary::after{content:'−'}
.tv-faq .tv-faq-a{padding:0 14px 12px;font-size:13.5px;color:var(--muted,#475569);line-height:1.6}
"""


def _safe_script_json(js):
    r"""JSON'u <script> içine gömmeden ÖNCE HTML-ayrıştırıcıyı kandıracak dizileri kaçır.

    ⚠ NEDEN (güvenlik denetimi bulgusu, 2026-08-19): `<script>` içeriği HTML ayrıştırıcı
    tarafından ilk `</script>` dizisinde SONLANDIRILIR — JSON içinde geçse bile. Bir FAQ
    cevabı `</script><img onerror=...>` içerirse script bloğu kırılır ve XSS oluşur.

    Şu an bu modülün çağrıcıları FAQ metinlerini build script'lerinde ELLE yazıyor, yani
    sömürülebilir değil. Ama bu ORTAK bir bileşen: TrVeri sitelerinin verisi dışarıdan
    geliyor (EKAP ihale adları, doktor/şirket unvanları, KAP bildirimleri). Biri FAQ'yu
    DB'den üretirse saldırgan-kontrollü metin buraya akar. Kütüphane bunu ÇAĞRICIYA
    bırakmamalı — savunma burada, tek noktada.

    `<`, `>`, `&` → \uXXXX kaçışı: JSON ayrıştırıcı birebir aynı string'i üretir, ama
    HTML ayrıştırıcı artık hiçbir etiket sınırı görmez. U+2028/U+2029 (JS satır ayırıcı)
    da kaçırılır — bazı ayrıştırıcılarda string literali bozar.
    """
    return (js.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
              .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def _clean(s):
    """Şema ile görünür metnin BİREBİR aynı olması için tek noktadan normalize."""
    return " ".join(str(s).split())


def faq_html(pairs, title="Sıkça Sorulan Sorular", open_first=True):
    """Görünür FAQ bloğu. İlk soru açık gelir — ekran üstünde doğrudan cevap görünsün."""
    if not pairs:
        return ""
    items = ""
    for i, (q, a) in enumerate(pairs):
        op = " open" if (open_first and i == 0) else ""
        items += (f'<details{op}><summary><h3>{_html.escape(_clean(q))}</h3></summary>'
                  f'<div class="tv-faq-a">{_html.escape(_clean(a))}</div></details>')
    return f'<section class="tv-faq"><h2>{_html.escape(title)}</h2>{items}</section>'


def faq_jsonld(pairs, as_script=True, nonce=None):
    """FAQPage JSON-LD. Metin faq_html ile BİREBİR aynı (Google eşleşme şartı)."""
    if not pairs:
        return ""
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": _clean(q),
             "acceptedAnswer": {"@type": "Answer", "text": _clean(a)}}
            for q, a in pairs
        ],
    }
    js = _safe_script_json(_json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    if not as_script:
        return js
    n = f' nonce="{nonce}"' if nonce else ""
    return f'<script type="application/ld+json"{n}>{js}</script>'


def faq_block(pairs, title="Sıkça Sorulan Sorular", nonce=None, open_first=True):
    """(görünür_html, jsonld_script) — ikisini BİRLİKTE döndürür; ayrı kullanmayın."""
    return faq_html(pairs, title, open_first), faq_jsonld(pairs, True, nonce)
