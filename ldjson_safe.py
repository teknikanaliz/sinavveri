# -*- coding: utf-8 -*-
r"""ldjson_safe.py — JSON-LD'yi <script> içine GÜVENLE gömmek için tek satırlık kaçış.

⚠ NEDEN (güvenlik denetimi, 2026-08-19): HTML ayrıştırıcı <script> içeriğini ilk
kapanış-etiketi dizisinde SONLANDIRIR — dizi JSON string'inin İÇİNDE geçse bile.
TrVeri sitelerinin JSON-LD'si DIŞARIDAN gelen metinler taşıyor (EKAP ihale adları,
doktor/hastane/şirket unvanları, KAP bildirim başlıkları, eczane adları). Bu
metinlerden biri kapanış etiketi içerirse script bloğu kırılır ve XSS oluşur.

json.dumps TEK BAŞINA YETMEZ: JSON standardı `<` `>` karakterlerini kaçırmaz.

KULLANIM
    from ldjson_safe import ld_json
    html = f'<script type="application/ld+json">{ld_json(veri)}</script>'
    # ya da elde hazır JSON string varsa:
    html = f'<script type="application/ld+json">{ld_escape(mevcut_json_str)}</script>'

GÜVENLİ ÇÜNKÜ: < > & karakterleri \uXXXX kaçışına çevrilir. JSON ayrıştırıcı
BİREBİR aynı string'i geri üretir (yani Google'ın gördüğü şema metni DEĞİŞMEZ),
ama HTML ayrıştırıcı artık hiçbir etiket sınırı göremez.
"""
import json as _json

__all__ = ["ld_escape", "ld_json", "ld_text"]

_MAP = (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"),
        (" ", "\\u2028"), (" ", "\\u2029"))


def ld_escape(js):
    """Hazır bir JSON string'ini <script> içine gömülebilir hale getirir."""
    if not js:
        return js
    for a, b in _MAP:
        js = js.replace(a, b)
    return js


def ld_json(obj, **kw):
    """json.dumps + kaçış (tek adım). ensure_ascii varsayılan False."""
    kw.setdefault("ensure_ascii", False)
    return ld_escape(_json.dumps(obj, **kw))


def ld_text(value):
    """ELLE YAZILMIŞ JSON literaline gömülecek bir METİN değeri güvenli hale getirir.

    Bazı üreticiler JSON-LD'yi json.dumps ile değil, f-string içinde ELLE yazıyor:
        <script type="application/ld+json">{{"name":"{ad}", ...}}</script>
    Burada `ad` dışarıdan geliyorsa iki ayrı kırılma olur: (1) içinde tırnak/ters bölü
    varsa JSON bozulur, (2) kapanış etiketi varsa <script> erken kapanır → XSS.

    ld_text() önce JSON string kaçışı uygular (tırnak/ters bölü/kontrol karakteri),
    sonra etiket kaçışı ekler. ÇEVRELEYEN TIRNAKLARI DÖNDÜRMEZ — literaldeki
    tırnakların arasına konur:  "name":"{ld_text(ad)}"
    """
    return ld_escape(_json.dumps("" if value is None else str(value))[1:-1])
