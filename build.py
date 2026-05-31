#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SınavVeri.com statik site jeneratörü.
Tüm sayfaları assets/style.css + ortak şablonla üretir.
Inline <script>'lar nonce="__NONCE__" taşır (nginx sub_filter ile per-request nonce).
Inline event handler (onclick/onload) YOK — addEventListener kullanılır (CSP strict-dynamic)."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
SITE = "https://sinavveri.com"
ASSET_VER = "20260530b"

NAV = [
    ("/index.html", "Ana Sayfa"),
    ("/taban-puanlari.html", "Taban Puanları"),
    ("/tercih-robotu.html", "Tercih Robotu"),
    ("/puan-hesaplama.html", "Puan Hesaplama"),
    ("/takvim.html", "Takvim"),
    ("/rehberler.html", "Rehberler"),
]


def jsonld(title, desc, slug, extra=None):
    url = SITE + "/" + (slug if slug != "index.html" else "")
    graph = [
        {"@type": "Organization", "@id": SITE + "/#organization", "name": "SınavVeri.com",
         "url": SITE, "memberOf": {"@type": "Organization", "name": "Türkiye Veri Platformu", "url": "https://trveri.com/"}},
        {"@type": "WebPage", "name": title, "description": desc, "url": url, "inLanguage": "tr",
         "isPartOf": {"@type": "WebSite", "name": "SınavVeri.com", "url": SITE},
         "publisher": {"@id": SITE + "/#organization"}},
    ]
    if extra:
        graph.extend(extra)
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=2)


def base(slug, title, desc, body, *, extra_head="", extra_ld=None):
    canonical = SITE + "/" + (slug if slug != "index.html" else "")
    nav_parts = []
    for href, label in NAV:
        cls = ' class="active"' if href.lstrip("/") == slug else ''
        nav_parts.append('<a href="' + href + '"' + cls + '>' + label + '</a>')
    nav_html = "\n".join(nav_parts)
    ld = jsonld(title, desc, slug, extra_ld)
    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📝</text></svg>">
<meta name="theme-color" content="#0f172a" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0a0d14" media="(prefers-color-scheme: dark)">
<meta property="og:type" content="website">
<meta property="og:site_name" content="SınavVeri.com">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{SITE}/assets/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="tr_TR">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{SITE}/assets/og.png">
<script nonce="__NONCE__" type="application/ld+json">{ld}</script>
<script nonce="__NONCE__">
  (function(){{ try {{ if (localStorage.getItem('sinavveri-theme') === 'dark') document.documentElement.setAttribute('data-theme','dark'); }} catch(e){{}} }})();
</script>
<link rel="stylesheet" href="/assets/style.css?v={ASSET_VER}">
<link rel="manifest" href="/manifest.json">
{extra_head}
</head>
<body>
<header>
  <div class="header-inner">
    <a href="/index.html" class="logo">Sınav<span class="logo-veri">Veri</span></a>
    <div class="header-right">
      <nav>{nav_html}</nav>
      <button type="button" class="theme-toggle" id="themeToggle" aria-label="Tema değiştir" title="Açık/Koyu tema"><span class="toggle-icon">🌙</span><span class="toggle-text">Koyu Tema</span></button>
    </div>
  </div>
</header>
<main>
{body}
</main>
<footer>
  <div class="footer-inner">
    <span>© 2026 SınavVeri.com · <a href="https://www.trveri.com" target="_blank" rel="noopener noreferrer">Türkiye Veri Platformu</a> ürünüdür.</span>
    <span class="fi-grow"></span>
    <span>Kaynak: <a href="https://www.osym.gov.tr" target="_blank" rel="noopener noreferrer">ÖSYM</a> · <a href="https://www.meb.gov.tr" target="_blank" rel="noopener noreferrer">MEB</a></span>
    <span>Resmî kaynak değildir; bilgi amaçlıdır.</span>
  </div>
</footer>
<script nonce="__NONCE__">
  (function(){{
    var btn=document.getElementById('themeToggle'); if(!btn) return;
    var root=document.documentElement, ic=btn.querySelector('.toggle-icon'), tx=btn.querySelector('.toggle-text');
    function lab(){{ var d=root.getAttribute('data-theme')==='dark'; if(ic)ic.textContent=d?'☀️':'🌙'; if(tx)tx.textContent=d?'Açık Tema':'Koyu Tema'; }}
    lab();
    btn.addEventListener('click',function(){{
      var n=root.getAttribute('data-theme')==='dark'?'light':'dark';
      if(n==='dark')root.setAttribute('data-theme','dark'); else root.removeAttribute('data-theme');
      try{{localStorage.setItem('sinavveri-theme',n);}}catch(e){{}} lab();
    }});
  }})();
</script>
<script nonce="__NONCE__">if('serviceWorker' in navigator){{navigator.serviceWorker.register('/sw.js').catch(function(){{}});}}</script>
</body>
</html>"""


def write(slug, html):
    p = ROOT / slug
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    print(f"  [+] {slug}  ({len(html)//1024} KB)")


# ───────────────────────── SLUG & VERİ YARDIMCILARI ─────────────────────────
_TR = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosucgiosu")


def slugify(s):
    s = (s or "").translate(_TR).lower()
    out = []
    for ch in s:
        if ch.isalnum():
            out.append(ch)
        elif ch in " -_/":
            out.append("-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "x"


PT_LABEL = {"SAY": "Sayısal", "EA": "Eşit Ağırlık", "SÖZ": "Sözel", "DİL": "Dil", "TYT": "TYT (Önlisans)"}
TUR_FULL = {"D": "Devlet", "V": "Vakıf", "K": "KKTC", "Y": "Diğer", "?": "—"}


def load_programs():
    return json.loads((ROOT / "data" / "programs_raw.json").read_text(encoding="utf-8"))


def fmt_puan(v):
    if not v:
        return "—"
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_sira(v):
    if not v:
        return "—"
    return f"{int(v):,}".replace(",", ".")


def hist_taban(r, year):
    for h in r.get("hist", []):
        if h[0] == year:
            return h[1]
    return None


def doluluk_html(r):
    k, y = r.get("kont"), r.get("yer")
    if not k or y is None:
        return "—"
    p = round(y / k * 100)
    cls = "tag-lgs" if p >= 100 else ("tag-kpss" if p >= 70 else "tag-other")
    return f'<span class="tag {cls}">%{p}</span>'


def median(vals):
    vals = sorted(v for v in vals if v)
    if not vals:
        return None
    n = len(vals)
    return vals[n // 2] if n % 2 else round((vals[n // 2 - 1] + vals[n // 2]) / 2, 2)


PLOTLY_CDN = '<script nonce="__NONCE__" src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>'


def trend_chart(group_recs, divid):
    """Grup için 2022-2025 medyan + en yüksek taban trend grafiği (Plotly)."""
    years = [2022, 2023, 2024, 2025]
    med, mx = [], []
    for yr in years:
        if yr == 2025:
            vals = [r.get("tp") for r in group_recs if r.get("tp")]
        else:
            vals = [hist_taban(r, yr) for r in group_recs]
            vals = [v for v in vals if v]
        med.append(median(vals))
        mx.append(max(vals) if vals else None)
    if sum(1 for m in med if m) < 2:
        return ""  # yeterli geçmiş yok
    data = [
        {"x": years, "y": med, "name": "Medyan taban", "mode": "lines+markers",
         "line": {"color": "#b45309", "width": 3}, "connectgaps": True},
        {"x": years, "y": mx, "name": "En yüksek taban", "mode": "lines+markers",
         "line": {"color": "#1e3a8a", "width": 2, "dash": "dot"}, "connectgaps": True},
    ]
    layout = {
        "margin": {"l": 48, "r": 16, "t": 10, "b": 36}, "height": 300,
        "xaxis": {"tickvals": years, "tickformat": "d", "gridcolor": "rgba(128,128,128,.15)"},
        "yaxis": {"title": {"text": "Taban Puanı"}, "gridcolor": "rgba(128,128,128,.15)"},
        "legend": {"orientation": "h", "y": -0.18, "x": 0}, "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)", "font": {"family": "Segoe UI, Arial, sans-serif", "size": 12},
        "hovermode": "x unified",
    }
    cfg = {"displayModeBar": False, "responsive": True}
    return (f'<div class="chart-card"><h3>Yıllara Göre Taban Puanı Trendi (2022–2025)</h3>'
            f'<div id="{divid}" style="width:100%"></div></div>'
            f'<script nonce="__NONCE__">Plotly.newPlot("{divid}",'
            + json.dumps(data) + "," + json.dumps(layout) + "," + json.dumps(cfg) + ");</script>")


# ───────────────────────── TAKVİM VERİSİ ─────────────────────────
CAL = json.loads((ROOT / "data" / "takvim-2026.json").read_text(encoding="utf-8"))
TUR_LABEL = {"yks": ("YKS", "tag-yks"), "lgs": ("LGS", "tag-lgs"), "kpss": ("KPSS", "tag-kpss"), "other": ("Diğer", "tag-other")}
AY_TR = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def fmt_date(iso):
    try:
        y, m, d = iso.split("-")
        return f"{int(d)} {AY_TR[int(m)]} {y}"
    except Exception:
        return iso


# ───────────────────────── ANA SAYFA ─────────────────────────
def page_index():
    # Yaklaşan sınavlar (spotlight) — istemci tarafında bugüne göre filtrelenir (her gün otomatik doğru)
    def exam_href(s):
        n, tur = s["ad"], s.get("tur")
        if tur == "yks":
            return "/yks.html"
        if tur == "lgs":
            return "/lgs.html"
        if tur == "kpss":
            return "/kpss.html"
        if "DGS" in n:
            return "/dgs.html"
        if "ALES" in n:
            return "/ales.html"
        return "/takvim.html"

    dated = [{"ad": s["ad"], "iso": s["sinav"], "tarih": fmt_date(s["sinav"]), "href": exam_href(s)}
             for s in CAL["sinavlar"] if s["sinav"].count("-") == 2]
    dated_json = json.dumps(dated, ensure_ascii=False)

    exams = [
        ("yks.html", "🎓", "YKS", "Yükseköğretim Kurumları Sınavı", "TYT + AYT ile üniversiteye giriş. ~2 milyon aday.", "20-21 Haziran 2026"),
        ("lgs.html", "🏫", "LGS", "Liselere Geçiş Sınavı", "8. sınıf merkezi sınavı ile liseye yerleşme.", "14 Haziran 2026"),
        ("kpss.html", "🏛️", "KPSS", "Kamu Personel Seçme Sınavı", "Kamu kadrolarına atanma için temel sınav.", "6 Eylül 2026"),
        ("dgs.html", "📈", "DGS", "Dikey Geçiş Sınavı", "Önlisanstan lisansa geçiş sınavı.", "19 Temmuz 2026"),
        ("ales.html", "📚", "ALES", "Akademik Personel ve Lisansüstü Eğitimi Giriş Sınavı", "Yüksek lisans, doktora ve akademik kadro.", "10 Mayıs 2026"),
        ("takvim.html", "🗓️", "Tüm Takvim", "2026 Sınav Takvimi", "YKS, LGS, KPSS, DGS, ALES, TUS, YDS ve daha fazlası.", "19 sınav"),
    ]
    cards = ""
    for href, icon, t, full, desc, meta in exams:
        cards += f"""<a class="exam-card" href="{href}">
  <div class="ec-top"><span class="ec-icon">{icon}</span><div><div class="ec-title">{t}</div><div class="ec-full">{full}</div></div></div>
  <div class="ec-desc">{desc}</div>
  <div class="ec-meta"><span><b>2026:</b> {meta}</span><span>İncele →</span></div>
</a>"""

    tools = [
        ("taban-puanlari.html", "📊", "Taban Puanları Merkezi", "Üniversite · LGS · TUS"),
        ("universite-taban-puanlari.html", "🎓", "Üniversite Taban Puanları", "21.602 program · YÖK Atlas"),
        ("lise-taban-puanlari.html", "🏫", "LGS Lise Taban Puanları", "81 il · 3.000+ lise"),
        ("tus-taban-puanlari.html", "🩺", "TUS Taban Puanları", "40 uzmanlık dalı · 2025"),
        ("tercih-robotu.html", "🎯", "Tercih Robotu", "Sıralamana göre bölüm bul"),
        ("takvim.html", "🗓️", "Sınav Takvimi 2026", "Tüm tarihler tek sayfada"),
    ]
    tool_html = ""
    for href, icon, t, sub in tools:
        tool_html += f"""<a class="tool-btn" href="{href}"><span class="tb-icon">{icon}</span><span class="tb-text"><b>{t}</b><span>{sub}</span></span></a>"""

    body = f"""
<div class="hero">
  <h1>Türkiye Sınav Verileri Tek Çatıda</h1>
  <p>2025 üniversite taban puanları, tercih robotu, puan hesaplama araçları ve güncel sınav takvimi. Sade, hızlı ve reklamsız bilgi.</p>
  <div class="hero-badges"><span>📊 21.602 Program</span><span>🎯 Tercih Robotu</span><span>🧮 Puan Hesaplama</span><span>📅 2026 Takvimi</span></div>
</div>

<div class="spotlight" id="spotlight"></div>

<div class="section">
  <h2>Sınavlar</h2>
  <div class="section-sub">Her sınav için format, puan hesaplama ve rehber bilgileri.</div>
  <div class="card-grid">
{cards}
  </div>
</div>

<div class="section">
  <h2>Hızlı Araçlar</h2>
  <div class="section-sub">Net ve puanını saniyeler içinde hesapla.</div>
  <div class="tool-row">
{tool_html}
  </div>
</div>

<div class="info-box">
  <h3>SınavVeri Nedir?</h3>
  SınavVeri, Türkiye'deki merkezi sınavlara hazırlanan öğrenciler ve adaylar için sade bir bilgi platformudur.
  ÖSYM ve MEB'in açıkladığı resmî sınav takvimi, sınav formatları ve puan hesaplama mantığı bir araya getirilir.
  Hesaplama araçları <strong>net hesabını birebir</strong> verir; puan tahminleri ise ÖSYM standart puan sistemi nedeniyle yaklaşıktır.
</div>

<script nonce="__NONCE__">
(function(){{
  var EXAMS={dated_json};
  var today=new Date(); today.setHours(0,0,0,0);
  function days(iso){{var p=iso.split('-');var d=new Date(+p[0],+p[1]-1,+p[2]);return Math.round((d-today)/86400000);}}
  var up=EXAMS.filter(function(e){{return days(e.iso)>=0;}}).sort(function(a,b){{return a.iso<b.iso?-1:1;}}).slice(0,4);
  var box=document.getElementById('spotlight');
  if(!box) return;
  if(!up.length){{box.style.display='none';return;}}
  up.forEach(function(e){{
    var diff=days(e.iso);
    var a=document.createElement('a');
    a.className='spot-card'; a.href=e.href;
    a.innerHTML='<div class="sc-label">Yaklaşan Sınav</div>'+
      '<div class="sc-exam">'+e.ad+'</div>'+
      '<div class="sc-date">'+e.tarih+'</div>'+
      '<div class="sc-days">'+(diff===0?'Bugün!':(diff+' gün kaldı'))+'</div>';
    box.appendChild(a);
  }});
}})();
</script>
"""
    desc = "Türkiye sınav verileri platformu: YKS, LGS, KPSS, DGS, ALES için 2026 sınav takvimi, puan hesaplama araçları ve sınav rehberleri."
    return base("index.html", "SınavVeri.com — Türkiye Sınav Verileri Platformu", desc, body)


# ───────────────────────── TAKVİM ─────────────────────────
def page_takvim():
    rows = ""
    for s in CAL["sinavlar"]:
        lbl, cls = TUR_LABEL.get(s["tur"], TUR_LABEL["other"])
        sinav = fmt_date(s["sinav"]) if s["sinav"].count("-") == 2 else s["sinav"]
        rows += f"""<tr>
  <td><span class="tag {cls}">{lbl}</span></td>
  <td><strong>{s['ad']}</strong>{('<br><small class="soon">'+s['not']+'</small>') if s['not'] else ''}</td>
  <td>{s['basvuru']}</td>
  <td><strong>{sinav}</strong></td>
  <td>{s['sonuc']}</td>
</tr>"""
    body = f"""
<div class="crumb"><a href="index.html">Ana Sayfa</a> / Sınav Takvimi</div>
<div class="page-title"><h1>2026 Sınav Takvimi</h1><span class="sub">ÖSYM ve MEB resmî takvimine göre · Güncelleme: {fmt_date(CAL['guncelleme'])}</span></div>
<div class="data-table-wrap">
<table class="data-table">
<thead><tr><th>Tür</th><th>Sınav</th><th>Başvuru</th><th>Sınav Tarihi</th><th>Sonuç</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
</div>
<div class="notice"><b>Not:</b> Tarihler ÖSYM'nin 14.11.2025 tarihli 2026 Yılı Sınav Takvimi ve MEB LGS duyurusuna dayanır.
Başvuru ve sonuç tarihleri ÖSYM tarafından güncellenebilir; kesin bilgi için <a href="https://www.osym.gov.tr" target="_blank" rel="noopener">osym.gov.tr</a> takip edilmelidir.</div>
"""
    ev = [{"@type": "Event", "name": s["ad"], "startDate": s["sinav"],
           "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
           "location": {"@type": "Country", "name": "Türkiye"}}
          for s in CAL["sinavlar"] if s["sinav"].count("-") == 2]
    return base("takvim.html", "2026 Sınav Takvimi — YKS, LGS, KPSS, DGS, ALES | SınavVeri",
                "2026 ÖSYM ve MEB sınav takvimi: YKS (TYT/AYT), LGS, KPSS, DGS, ALES, TUS, YDS başvuru, sınav ve sonuç tarihleri.",
                body, extra_ld=ev)


# ───────────────────────── HESAPLAMA SAYFALARI ─────────────────────────
def calc_subj_rows(subjects):
    head = '<div class="subj-head"><span>Ders</span><span>Doğru</span><span>Yanlış</span><span>Net</span></div>'
    rows = ""
    for key, name, count in subjects:
        rows += f"""<div class="subj-row" data-key="{key}" data-max="{count}">
  <div class="sr-name">{name} <small>/{count}</small></div>
  <input type="number" min="0" max="{count}" inputmode="numeric" class="in-d" placeholder="0">
  <input type="number" min="0" max="{count}" inputmode="numeric" class="in-y" placeholder="0">
  <div class="sr-net" data-net>0</div>
</div>"""
    return head + rows


def page_yks_calc():
    tyt = [("turkce", "Türkçe", 40), ("sosyal", "Sosyal Bilimler", 20), ("mat", "Temel Matematik", 40), ("fen", "Fen Bilimleri", 20)]
    ayt = [("edeb", "Edebiyat-Sosyal Bilimler-1", 40), ("sos2", "Sosyal Bilimler-2", 40), ("amat", "Matematik", 40), ("afen", "Fen Bilimleri", 40)]
    body = f"""
<div class="crumb"><a href="index.html">Ana Sayfa</a> / <a href="yks.html">YKS</a> / Puan Hesaplama</div>
<div class="page-title"><h1>YKS Puan Hesaplama (TYT + AYT)</h1><span class="sub">2026 · Yanlış cevap doğruyu götürür: <b>4 yanlış = 1 doğru</b></span></div>
<div class="calc-wrap">
  <div>
    <div class="calc-card">
      <h2>TYT — Temel Yeterlilik Testi</h2>
      <div class="calc-hint">120 soru · Tüm adaylar girer</div>
      <div class="calc-block" id="tyt">{calc_subj_rows(tyt)}</div>
    </div>
    <div style="height:16px"></div>
    <div class="calc-card">
      <h2>AYT — Alan Yeterlilik Testi</h2>
      <div class="calc-hint">160 soru · Tercih edilen puan türüne göre ilgili testler</div>
      <div class="calc-block" id="ayt">{calc_subj_rows(ayt)}</div>
      <div class="calc-block" style="margin-bottom:0">
        <h3>Diploma / OBP</h3>
        <div class="subj-row" style="grid-template-columns:1fr 120px">
          <div class="sr-name">Diploma Notu <small>(50-100)</small></div>
          <input type="number" min="50" max="100" step="0.01" inputmode="decimal" id="diploma" placeholder="örn. 85.40">
        </div>
      </div>
      <div class="calc-actions">
        <button type="button" class="btn btn-primary" id="calcBtn">Hesapla</button>
        <button type="button" class="btn btn-ghost" id="resetBtn">Temizle</button>
      </div>
    </div>
  </div>
  <div class="result-card">
    <h3>Sonuç</h3>
    <div class="res-net"><div class="rn-label">Toplam Net</div><div class="rn-value" id="rTotal">0,00</div></div>
    <ul class="res-list">
      <li><span>TYT Net</span><b id="rTyt">0,00</b></li>
      <li><span>AYT Net</span><b id="rAyt">0,00</b></li>
      <li><span>OBP (Diploma × 5)</span><b id="rObp">—</b></li>
    </ul>
    <div class="res-est"><div class="re-label">Yaklaşık TYT Ham Puanı</div><div class="re-value" id="rTytPuan">—</div></div>
  </div>
</div>
<div class="notice"><b>Önemli:</b> Net hesabı <b>kesindir</b>. Puan tahmini ÖSYM'nin her yıl sınava göre belirlediği
<b>standart puan</b> sistemi (ortalama/standart sapma) nedeniyle <b>yaklaşıktır</b> ve gerçek sonuçtan farklı olabilir.
AYT yerleştirme puanı (Sayısal/Eşit Ağırlık/Sözel/Dil) puan türüne göre değişir; kesin puan ÖSYM sonuç belgenizde yer alır.</div>
<div class="info-box"><h3>YKS net nasıl hesaplanır?</h3>
Her test için: <strong>Net = Doğru − (Yanlış ÷ 4)</strong>. TYT ve AYT'de 4 yanlış 1 doğruyu götürür.
Yerleştirme puanına OBP (Okul Başarı Puanı = Diploma Notu × 5) en fazla 60 puana kadar katkı sağlar (OBP × 0,12).</div>
{calc_js_yks()}
"""
    return base("yks-puan-hesaplama.html", "YKS Puan Hesaplama 2026 (TYT + AYT Net) | SınavVeri",
                "2026 YKS puan ve net hesaplama: TYT ve AYT doğru-yanlış gir, dersbazlı net ve toplam netini anında öğren. 4 yanlış 1 doğru.",
                body)


def calc_js_yks():
    return """<script nonce="__NONCE__">
(function(){
  var TR=function(n){return n.toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2});};
  function netOf(row,penalty){
    var d=parseFloat(row.querySelector('.in-d').value)||0;
    var y=parseFloat(row.querySelector('.in-y').value)||0;
    var max=parseFloat(row.getAttribute('data-max'))||0;
    d=Math.max(0,Math.min(d,max)); y=Math.max(0,Math.min(y,max));
    if(d+y>max){y=Math.max(0,max-d);}
    var net=d-(y/penalty); if(net<0)net=0;
    row.querySelector('[data-net]').textContent=TR(net);
    return net;
  }
  function sum(sel){var t=0;document.querySelectorAll(sel+' .subj-row').forEach(function(r){t+=netOf(r,4);});return t;}
  function calc(){
    var tyt=sum('#tyt'), ayt=sum('#ayt');
    document.getElementById('rTyt').textContent=TR(tyt);
    document.getElementById('rAyt').textContent=TR(ayt);
    document.getElementById('rTotal').textContent=TR(tyt+ayt);
    var dip=parseFloat(document.getElementById('diploma').value);
    document.getElementById('rObp').textContent=(dip&&dip>=50&&dip<=100)?TR(dip*5):'—';
    // Yaklaşık TYT ham puanı: 100 taban + net*3.33 (kaba tahmin)
    document.getElementById('rTytPuan').textContent=Math.round(100+tyt*3.33)+' (±)';
  }
  document.getElementById('calcBtn').addEventListener('click',calc);
  document.querySelectorAll('#tyt input,#ayt input,#diploma').forEach(function(i){i.addEventListener('input',calc);});
  document.getElementById('resetBtn').addEventListener('click',function(){
    document.querySelectorAll('input').forEach(function(i){i.value='';});
    document.querySelectorAll('[data-net]').forEach(function(n){n.textContent='0,00';});
    ['rTyt','rAyt','rTotal'].forEach(function(id){document.getElementById(id).textContent='0,00';});
    document.getElementById('rObp').textContent='—'; document.getElementById('rTytPuan').textContent='—';
  });
})();
</script>"""


def page_lgs_calc():
    subj = [("turkce", "Türkçe", 20, 4), ("inkilap", "T.C. İnkılap Tarihi", 10, 1), ("din", "Din Kültürü", 10, 1),
            ("ydil", "Yabancı Dil (İng.)", 10, 1), ("mat", "Matematik", 20, 4), ("fen", "Fen Bilimleri", 20, 4)]
    rows = '<div class="subj-head"><span>Ders</span><span>Doğru</span><span>Yanlış</span><span>Net</span></div>'
    for key, name, count, kat in subj:
        rows += f"""<div class="subj-row" data-key="{key}" data-max="{count}" data-kat="{kat}">
  <div class="sr-name">{name} <small>/{count} · ×{kat}</small></div>
  <input type="number" min="0" max="{count}" inputmode="numeric" class="in-d" placeholder="0">
  <input type="number" min="0" max="{count}" inputmode="numeric" class="in-y" placeholder="0">
  <div class="sr-net" data-net>0</div>
</div>"""
    body = f"""
<div class="crumb"><a href="index.html">Ana Sayfa</a> / <a href="lgs.html">LGS</a> / Puan Hesaplama</div>
<div class="page-title"><h1>LGS Puan Hesaplama</h1><span class="sub">2026 · Yanlış cevap doğruyu götürür: <b>3 yanlış = 1 doğru</b></span></div>
<div class="calc-wrap">
  <div class="calc-card">
    <h2>LGS — Tüm Dersler</h2>
    <div class="calc-hint">90 soru · Sözel (50) + Sayısal (40) · Katsayılar: Türkçe/Mat/Fen ×4, diğerleri ×1</div>
    <div class="calc-block" id="lgs">{rows}</div>
    <div class="calc-actions">
      <button type="button" class="btn btn-primary" id="calcBtn">Hesapla</button>
      <button type="button" class="btn btn-ghost" id="resetBtn">Temizle</button>
    </div>
  </div>
  <div class="result-card">
    <h3>Sonuç</h3>
    <div class="res-net"><div class="rn-label">Toplam Net</div><div class="rn-value" id="rTotal">0,00</div></div>
    <ul class="res-list">
      <li><span>Ağırlıklı Net</span><b id="rWeighted">0,00</b></li>
      <li><span>Maksimum Ağırlıklı</span><b>270,00</b></li>
    </ul>
    <div class="res-est"><div class="re-label">Yaklaşık LGS Puanı (100-500)</div><div class="re-value" id="rPuan">—</div></div>
  </div>
</div>
<div class="notice"><b>Önemli:</b> Net hesabı <b>kesindir</b>. LGS puanı MEB tarafından <b>standart puan</b> yöntemiyle (her dersin
ülke ortalaması/standart sapması) hesaplanır; buradaki puan ağırlıklı nete dayalı <b>yaklaşık</b> bir tahmindir.
Kesin puan ve yüzdelik dilim MEB sonuç belgenizde yer alır.</div>
<div class="info-box"><h3>LGS net nasıl hesaplanır?</h3>
Her ders için: <strong>Net = Doğru − (Yanlış ÷ 3)</strong>. LGS'de 3 yanlış 1 doğruyu götürür.
Türkçe, Matematik ve Fen Bilimleri 4 katsayıyla; İnkılap Tarihi, Din Kültürü ve Yabancı Dil 1 katsayıyla değerlendirilir.</div>
<script nonce="__NONCE__">
(function(){{
  var TR=function(n){{return n.toLocaleString('tr-TR',{{minimumFractionDigits:2,maximumFractionDigits:2}});}};
  function calc(){{
    var total=0,weighted=0;
    document.querySelectorAll('#lgs .subj-row').forEach(function(r){{
      var d=parseFloat(r.querySelector('.in-d').value)||0, y=parseFloat(r.querySelector('.in-y').value)||0;
      var max=+r.getAttribute('data-max'), kat=+r.getAttribute('data-kat');
      d=Math.max(0,Math.min(d,max)); y=Math.max(0,Math.min(y,max)); if(d+y>max)y=Math.max(0,max-d);
      var net=d-(y/3); if(net<0)net=0;
      r.querySelector('[data-net]').textContent=TR(net);
      total+=net; weighted+=net*kat;
    }});
    document.getElementById('rTotal').textContent=TR(total);
    document.getElementById('rWeighted').textContent=TR(weighted);
    document.getElementById('rPuan').textContent=Math.round(100+(weighted/270)*400)+' (±)';
  }}
  document.getElementById('calcBtn').addEventListener('click',calc);
  document.querySelectorAll('#lgs input').forEach(function(i){{i.addEventListener('input',calc);}});
  document.getElementById('resetBtn').addEventListener('click',function(){{
    document.querySelectorAll('#lgs input').forEach(function(i){{i.value='';}});
    document.querySelectorAll('[data-net]').forEach(function(n){{n.textContent='0,00';}});
    document.getElementById('rTotal').textContent='0,00'; document.getElementById('rWeighted').textContent='0,00';
    document.getElementById('rPuan').textContent='—';
  }});
}})();
</script>
"""
    return base("lgs-puan-hesaplama.html", "LGS Puan Hesaplama 2026 (Net ve Ağırlıklı Puan) | SınavVeri",
                "2026 LGS puan ve net hesaplama: doğru-yanlış gir, dersbazlı net, ağırlıklı net ve yaklaşık LGS puanını öğren. 3 yanlış 1 doğru.",
                body)


def page_kpss_calc():
    gy = [("turkce", "Türkçe", 30), ("mat", "Matematik-Geometri", 30)]
    gk = [("tarih", "Tarih", 27), ("cog", "Coğrafya", 18), ("vat", "Vatandaşlık", 9), ("guncel", "Güncel Bilgiler", 6)]
    body = f"""
<div class="crumb"><a href="index.html">Ana Sayfa</a> / <a href="kpss.html">KPSS</a> / Puan Hesaplama</div>
<div class="page-title"><h1>KPSS Puan Hesaplama (Lisans GY-GK)</h1><span class="sub">2026 · Yanlış cevap doğruyu götürür: <b>4 yanlış = 1 doğru</b></span></div>
<div class="calc-wrap">
  <div>
    <div class="calc-card">
      <h2>Genel Yetenek (GY)</h2>
      <div class="calc-hint">60 soru</div>
      <div class="calc-block" id="gy">{calc_subj_rows(gy)}</div>
    </div>
    <div style="height:16px"></div>
    <div class="calc-card">
      <h2>Genel Kültür (GK)</h2>
      <div class="calc-hint">60 soru</div>
      <div class="calc-block" id="gk">{calc_subj_rows(gk)}</div>
      <div class="calc-actions">
        <button type="button" class="btn btn-primary" id="calcBtn">Hesapla</button>
        <button type="button" class="btn btn-ghost" id="resetBtn">Temizle</button>
      </div>
    </div>
  </div>
  <div class="result-card">
    <h3>Sonuç</h3>
    <div class="res-net"><div class="rn-label">Toplam Net (120)</div><div class="rn-value" id="rTotal">0,00</div></div>
    <ul class="res-list">
      <li><span>GY Net</span><b id="rGy">0,00</b></li>
      <li><span>GK Net</span><b id="rGk">0,00</b></li>
      <li><span>Doğru Oranı</span><b id="rPct">—</b></li>
    </ul>
    <div class="res-est"><div class="re-label">Yaklaşık KPSS P (GY-GK)</div><div class="re-value" id="rPuan">—</div></div>
  </div>
</div>
<div class="notice"><b>Önemli:</b> Net hesabı <b>kesindir</b>. KPSS puanı (P1/P2/P3 vb.) ÖSYM'nin <b>standart puan</b>
yöntemiyle hesaplanır ve net→puan dönüşümü her sınavda değişir; buradaki "yaklaşık KPSS P" net oranına dayalı
kaba bir göstergedir, atama puanı olarak kullanılamaz. Kesin puan ÖSYM sonuç belgenizdedir.</div>
<div class="info-box"><h3>KPSS net nasıl hesaplanır?</h3>
Her test için: <strong>Net = Doğru − (Yanlış ÷ 4)</strong>. KPSS Lisans GY-GK oturumunda 120 soru bulunur:
GY (Türkçe 30, Matematik 30) + GK (Tarih 27, Coğrafya 18, Vatandaşlık 9, Güncel 6).
Alan bilgisi (ÖABT vb.) ayrı oturumdur.</div>
<script nonce="__NONCE__">
(function(){{
  var TR=function(n){{return n.toLocaleString('tr-TR',{{minimumFractionDigits:2,maximumFractionDigits:2}});}};
  function netOf(r){{
    var d=parseFloat(r.querySelector('.in-d').value)||0, y=parseFloat(r.querySelector('.in-y').value)||0;
    var max=+r.getAttribute('data-max'); d=Math.max(0,Math.min(d,max)); y=Math.max(0,Math.min(y,max)); if(d+y>max)y=Math.max(0,max-d);
    var net=d-(y/4); if(net<0)net=0; r.querySelector('[data-net]').textContent=TR(net); return net;
  }}
  function sum(sel){{var t=0;document.querySelectorAll(sel+' .subj-row').forEach(function(r){{t+=netOf(r);}});return t;}}
  function calc(){{
    var gy=sum('#gy'), gk=sum('#gk'), tot=gy+gk;
    document.getElementById('rGy').textContent=TR(gy);
    document.getElementById('rGk').textContent=TR(gk);
    document.getElementById('rTotal').textContent=TR(tot);
    document.getElementById('rPct').textContent=(tot/120*100).toFixed(1)+'%';
    // Kaba gösterge: KPSS P yaklaşık 50 taban + (net/120)*50  → ~50-100 aralığı
    document.getElementById('rPuan').textContent=(50+(tot/120)*50).toFixed(1)+' (±)';
  }}
  document.getElementById('calcBtn').addEventListener('click',calc);
  document.querySelectorAll('#gy input,#gk input').forEach(function(i){{i.addEventListener('input',calc);}});
  document.getElementById('resetBtn').addEventListener('click',function(){{
    document.querySelectorAll('input').forEach(function(i){{i.value='';}});
    document.querySelectorAll('[data-net]').forEach(function(n){{n.textContent='0,00';}});
    ['rGy','rGk','rTotal'].forEach(function(id){{document.getElementById(id).textContent='0,00';}});
    document.getElementById('rPct').textContent='—'; document.getElementById('rPuan').textContent='—';
  }});
}})();
</script>
"""
    return base("kpss-puan-hesaplama.html", "KPSS Puan Hesaplama 2026 (Lisans GY-GK Net) | SınavVeri",
                "2026 KPSS Lisans puan ve net hesaplama: Genel Yetenek ve Genel Kültür doğru-yanlış gir, net ve doğru oranını öğren. 4 yanlış 1 doğru.",
                body)


# ───────────────────────── REHBER SAYFALARI ─────────────────────────
def guide(slug, exam, title_full, icon, calc_slug, intro, sections, has_calc=True):
    sec_html = ""
    for h, paras in sections:
        sec_html += f"<h2>{h}</h2>"
        for p in paras:
            if isinstance(p, tuple):
                if p[0] == "ul":
                    sec_html += "<ul>" + "".join(f"<li>{x}</li>" for x in p[1]) + "</ul>"
                elif p[0] == "ol":
                    sec_html += "<ol>" + "".join(f"<li>{x}</li>" for x in p[1]) + "</ol>"
            else:
                sec_html += f"<p>{p}</p>"
    calc_btn = (f'<a class="tool-btn" href="{calc_slug}" style="max-width:340px;margin:18px 0"><span class="tb-icon">🧮</span>'
                f'<span class="tb-text"><b>{exam} Puan Hesaplama</b><span>Net ve puanını hesapla</span></span></a>') if has_calc else ""
    body = f"""
<div class="crumb"><a href="index.html">Ana Sayfa</a> / {exam}</div>
<div class="hero" style="padding:30px 28px">
  <h1>{icon} {exam} — {title_full}</h1>
  <p>{intro}</p>
</div>
{calc_btn}
<div class="prose">
{sec_html}
</div>
<div class="notice" style="max-width:880px"><b>Bilgi:</b> Bu sayfa bilgilendirme amaçlıdır. Başvuru koşulları ve güncel kurallar için
resmî kaynak <a href="https://www.osym.gov.tr" target="_blank" rel="noopener">ÖSYM</a>/<a href="https://www.meb.gov.tr" target="_blank" rel="noopener">MEB</a> esas alınmalıdır.</div>
"""
    return base(slug, f"{exam} Nedir? {title_full} Rehberi 2026 | SınavVeri",
                intro[:155], body)


def page_yks():
    return guide("yks.html", "YKS", "Yükseköğretim Kurumları Sınavı", "🎓", "yks-puan-hesaplama.html",
        "YKS, Türkiye'de üniversiteye girişin tek yoludur. TYT ve AYT olmak üzere iki temel oturumdan oluşur; 2026'da TYT 20 Haziran, AYT 21 Haziran'da yapılacaktır.",
        [
            ("YKS Nedir?", [
                "Yükseköğretim Kurumları Sınavı (YKS), lisans ve önlisans programlarına yerleşmek isteyen adayların girdiği merkezi sınavdır. ÖSYM tarafından yılda bir kez düzenlenir.",
                "Sınav iki ana oturumdan oluşur: <strong>TYT</strong> (Temel Yeterlilik Testi) ve <strong>AYT</strong> (Alan Yeterlilik Testi). Yabancı dil bölümleri için ayrıca <strong>YDT</strong> uygulanır.",
            ]),
            ("Oturumlar ve Soru Dağılımı", [
                "<strong>TYT (120 soru, 165 dk):</strong>",
                ("ul", ["Türkçe — 40 soru", "Sosyal Bilimler — 20 soru (Tarih, Coğrafya, Felsefe, Din Kültürü)",
                        "Temel Matematik — 40 soru", "Fen Bilimleri — 20 soru (Fizik, Kimya, Biyoloji)"]),
                "<strong>AYT (160 soru, 180 dk):</strong>",
                ("ul", ["Türk Dili ve Edebiyatı – Sosyal Bilimler-1 — 40 soru", "Sosyal Bilimler-2 — 40 soru",
                        "Matematik — 40 soru", "Fen Bilimleri — 40 soru"]),
            ]),
            ("Puan Türleri", [
                "AYT'de tercih edeceğiniz alana göre puan türü oluşur:",
                ("ul", ["<strong>SAY</strong> (Sayısal) — Matematik + Fen ağırlıklı (mühendislik, tıp, fen)",
                        "<strong>EA</strong> (Eşit Ağırlık) — Matematik + Edebiyat/Sosyal (hukuk, işletme, psikoloji)",
                        "<strong>SÖZ</strong> (Sözel) — Edebiyat + Sosyal Bilimler (öğretmenlik, tarih, hukuk)",
                        "<strong>DİL</strong> — Yabancı Dil Testi (mütercim tercümanlık, dil öğretmenlikleri)"]),
            ]),
            ("Net ve Puan Hesaplama", [
                "Her testte <strong>Net = Doğru − (Yanlış ÷ 4)</strong> formülü uygulanır. TYT ve AYT'de 4 yanlış 1 doğruyu götürür.",
                "Yerleştirme puanına <strong>OBP</strong> (Okul Başarı Puanı = Diploma Notu × 5) en fazla 60 puana kadar (OBP × 0,12) katkı sağlar.",
                "Detaylı hesaplama için <a href='yks-puan-hesaplama.html'>YKS Puan Hesaplama</a> aracını kullanabilirsiniz.",
            ]),
            ("2026 YKS Tarihleri", [
                ("ul", ["Başvuru: 6 Şubat – 2 Mart 2026", "TYT: 20 Haziran 2026", "AYT & YDT: 21 Haziran 2026", "Sonuç: 22 Temmuz 2026"]),
            ]),
        ])


def page_lgs():
    return guide("lgs.html", "LGS", "Liselere Geçiş Sınavı", "🏫", "lgs-puan-hesaplama.html",
        "LGS, 8. sınıf öğrencilerinin fen lisesi, sosyal bilimler lisesi ve nitelikli Anadolu liselerine yerleşmek için girdiği merkezi sınavdır. 2026'da 14 Haziran'da yapılacaktır.",
        [
            ("LGS Nedir?", [
                "Liselere Geçiş Sınavı (LGS), MEB tarafından düzenlenen ve merkezi yerleştirmeyle öğrenci alan liselere giriş için uygulanan sınavdır. Katılım zorunlu değildir; isteyen öğrenci girer.",
                "Sınav tek oturumda, iki bölüm halinde yapılır: <strong>Sözel</strong> ve <strong>Sayısal</strong>.",
            ]),
            ("Soru Dağılımı", [
                "<strong>Sözel Bölüm (50 soru):</strong>",
                ("ul", ["Türkçe — 20", "T.C. İnkılap Tarihi ve Atatürkçülük — 10", "Din Kültürü ve Ahlak Bilgisi — 10", "Yabancı Dil — 10"]),
                "<strong>Sayısal Bölüm (40 soru):</strong>",
                ("ul", ["Matematik — 20", "Fen Bilimleri — 20"]),
            ]),
            ("Puan ve Katsayılar", [
                "Net hesabı: <strong>Net = Doğru − (Yanlış ÷ 3)</strong>. LGS'de 3 yanlış 1 doğruyu götürür.",
                "Ders katsayıları: Türkçe, Matematik ve Fen Bilimleri <strong>×4</strong>; İnkılap Tarihi, Din Kültürü ve Yabancı Dil <strong>×1</strong>.",
                "LGS puanı 100–500 arasında, standart puan yöntemiyle hesaplanır. Tahmini için <a href='lgs-puan-hesaplama.html'>LGS Puan Hesaplama</a> aracını kullanın.",
            ]),
            ("2026 LGS Tarihi", [
                ("ul", ["Sınav: 14 Haziran 2026", "Sonuç: Temmuz 2026 (MEB tarafından açıklanır)"]),
            ]),
        ])


def page_kpss():
    return guide("kpss.html", "KPSS", "Kamu Personel Seçme Sınavı", "🏛️", "kpss-puan-hesaplama.html",
        "KPSS, kamu kurumlarında memur ve personel olarak çalışmak isteyen adayların girdiği merkezi sınavdır. Lisans, ön lisans ve ortaöğretim düzeyinde ayrı yapılır.",
        [
            ("KPSS Nedir?", [
                "Kamu Personel Seçme Sınavı (KPSS), kamu kurum ve kuruluşlarına atanacak personelin belirlenmesinde kullanılan ÖSYM sınavıdır. Eğitim düzeyine göre üç ayrı sınav yapılır: Lisans, Ön Lisans, Ortaöğretim.",
            ]),
            ("Lisans Soru Dağılımı (GY-GK)", [
                "<strong>Genel Yetenek (60 soru):</strong>",
                ("ul", ["Türkçe — 30", "Matematik-Geometri — 30"]),
                "<strong>Genel Kültür (60 soru):</strong>",
                ("ul", ["Tarih — 27", "Türkiye Coğrafyası — 18", "Temel Yurttaşlık Bilgisi — 9", "Güncel Bilgiler — 6"]),
                "Öğretmen adayları ayrıca <strong>Eğitim Bilimleri</strong> ve alanlarına göre <strong>ÖABT</strong> oturumlarına girer.",
            ]),
            ("Puan ve Atama", [
                "Net hesabı: <strong>Net = Doğru − (Yanlış ÷ 4)</strong>.",
                "Sonuçtan P1, P2, P3 gibi farklı puan türleri üretilir; atamalarda kullanılan puan türü kadroya göre değişir. Net hesabı için <a href='kpss-puan-hesaplama.html'>KPSS Puan Hesaplama</a> aracını kullanın.",
            ]),
            ("2026 KPSS Tarihleri", [
                ("ul", ["Lisans GY-GK: 6 Eylül 2026", "Lisans ÖABT: 12-13 Eylül 2026", "Ön Lisans: 4 Ekim 2026", "Ortaöğretim: 25 Ekim 2026"]),
            ]),
        ])


def page_dgs():
    return guide("dgs.html", "DGS", "Dikey Geçiş Sınavı", "📈", "",
        "DGS, ön lisans (2 yıllık) mezunlarının veya son sınıf öğrencilerinin lisans (4 yıllık) programlarına dikey geçiş yapabilmesi için girdiği sınavdır. 2026'da 19 Temmuz'da yapılacaktır.",
        [
            ("DGS Nedir?", [
                "Dikey Geçiş Sınavı (DGS), meslek yüksekokulu ve açıköğretim ön lisans programlarından mezun olanların, alanlarıyla ilişkili lisans programlarına geçişini sağlayan ÖSYM sınavıdır.",
            ]),
            ("Sınav Formatı", [
                "DGS tek oturumda yapılır ve iki testten oluşur:",
                ("ul", ["Sayısal — 60 soru", "Sözel — 60 soru"]),
                "Adayın sayısal ve sözel netlerinden, tercih edilen programın puan türüne göre (SAY/SÖZ/EA) ağırlıklı puan hesaplanır. Net hesabında 4 yanlış 1 doğruyu götürür.",
            ]),
            ("Kimler Girebilir?", [
                "Ön lisans programlarından mezun olanlar ve son sınıf öğrencileri başvurabilir. Yerleşilebilecek lisans programları, mezun olunan ön lisans alanına göre ÖSYM kılavuzunda belirtilir.",
            ]),
            ("2026 DGS Tarihleri", [
                ("ul", ["Başvuru: 15 Mayıs – 2 Haziran 2026", "Sınav: 19 Temmuz 2026", "Sonuç: 13 Ağustos 2026"]),
            ]),
        ], has_calc=False)


def page_ales():
    return guide("ales.html", "ALES", "Akademik Personel ve Lisansüstü Eğitimi Giriş Sınavı", "📚", "",
        "ALES, yüksek lisans ve doktora programlarına başvuru ile akademik kadrolara (araştırma görevlisi, öğretim görevlisi) atanma için girilen sınavdır. Yılda üç kez yapılır.",
        [
            ("ALES Nedir?", [
                "Akademik Personel ve Lisansüstü Eğitimi Giriş Sınavı (ALES), lisansüstü eğitime başvuruda ve akademik personel alımında kullanılan ÖSYM sınavıdır. Sonuçlar 5 yıl geçerlidir.",
            ]),
            ("Sınav Formatı", [
                "ALES, sayısal ve sözel bölümlerden oluşur:",
                ("ul", ["Sayısal-1 ve Sayısal-2 — 50 soru", "Sözel-1 ve Sözel-2 — 50 soru"]),
                "Sayısal ve Sözel netlerden adayın puan türüne göre (Sayısal / Sözel / Eşit Ağırlık) ağırlıklı puan üretilir. 4 yanlış 1 doğruyu götürür.",
            ]),
            ("Geçerlilik ve Kullanım", [
                ("ul", ["Yüksek lisans / doktora başvuruları", "Araştırma görevlisi ve öğretim görevlisi kadroları",
                        "Sonuçlar açıklandığı tarihten itibaren 5 yıl geçerlidir"]),
            ]),
            ("2026 ALES Tarihleri", [
                ("ul", ["ALES/1: 10 Mayıs 2026", "ALES/2: 26 Temmuz 2026", "ALES/3: 29 Kasım 2026"]),
            ]),
        ], has_calc=False)


# ───────────────────────── HATA SAYFALARI ─────────────────────────
def page_error(code, msg):
    body = f"""
<div style="text-align:center;padding:60px 20px">
  <div style="font-size:72px">📝</div>
  <h1 style="font-size:48px;color:var(--accent);margin:10px 0">{code}</h1>
  <p style="font-size:16px;color:var(--fg-muted);margin-bottom:24px">{msg}</p>
  <a class="btn btn-primary" href="/index.html" style="text-decoration:none;display:inline-block">Ana Sayfaya Dön</a>
</div>"""
    return base("index.html", f"{code} — SınavVeri.com", msg, body)


# ───────────────────────── DESTEK DOSYALARI ─────────────────────────
def write_support(pages=None):
    if pages is None:
        pages = ["index.html", "takvim.html"]

    def meta(p):
        if p == "index.html":
            return "daily", "1.0"
        if p in ("taban-puanlari.html", "tercih-robotu.html", "takvim.html", "lise-taban-puanlari.html"):
            return "daily", "0.9"
        if p.startswith(("bolum/", "universite/", "lise/")):
            return "monthly", "0.6"
        return "weekly", "0.7"

    rows = []
    for p in pages:
        cf, pr = meta(p)
        loc = SITE + "/" + ("" if p == "index.html" else p)
        rows.append(f"  <url><loc>{loc}</loc><changefreq>{cf}</changefreq><priority>{pr}</priority></url>")
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(rows) + "\n</urlset>\n"
    (ROOT / "sitemap.xml").write_text(sitemap, encoding="utf-8")

    manifest = {
        "name": "SınavVeri.com", "short_name": "SınavVeri",
        "description": "Türkiye Sınav Verileri Platformu — takvim, puan hesaplama, rehberler",
        "start_url": "/", "display": "standalone", "background_color": "#0f172a", "theme_color": "#0f172a",
        "icons": [{"src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📝</text></svg>", "sizes": "any", "type": "image/svg+xml"}],
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    sw = """const CACHE='sinavveri-v1';
const ASSETS=['/','/index.html','/takvim.html','/assets/style.css'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  e.respondWith(fetch(e.request).then(r=>{const cp=r.clone();caches.open(CACHE).then(c=>c.put(e.request,cp));return r;}).catch(()=>caches.match(e.request)));
});
"""
    (ROOT / "sw.js").write_text(sw, encoding="utf-8")

    robots = """User-agent: *
Allow: /

User-agent: Google-Extended
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: OAI-SearchBot
Allow: /
User-agent: ChatGPT-User
Allow: /

User-agent: GPTBot
Disallow: /
User-agent: ClaudeBot
Disallow: /
User-agent: CCBot
Disallow: /
User-agent: Bytespider
Disallow: /

Sitemap: https://sinavveri.com/sitemap.xml
"""
    (ROOT / "robots.txt").write_text(robots, encoding="utf-8")

    llms = """# SınavVeri.com
> Türkiye sınav verileri platformu — YKS, LGS, KPSS, DGS, ALES

## Hakkında
SınavVeri, TrVeri ailesi bünyesinde Türkiye'deki merkezi sınavlar için takvim, puan hesaplama ve rehber sunan bir bilgi platformudur.

## İçerik
- Taban puanları merkezi (tüm sınavlar): /taban-puanlari.html
- Üniversite taban puanları 2025 (YÖK Atlas, 21.602 program): /universite-taban-puanlari.html
- LGS lise taban puanları 2025 (81 il, 3000+ lise): /lise-taban-puanlari.html
- TUS taban puanları 2025 (40 uzmanlık dalı): /tus-taban-puanlari.html
- DUS taban puanları 2025 (8 diş hekimliği uzmanlık dalı): /dus-taban-puanlari.html
- DGS taban puanları 2025 (7000+ üniversite programı, ÖSYM): /dgs-taban-puanlari.html
- KPSS atama taban puanları 2025 (kadro bazında, ÖSYM): /kpss-atama-taban-puanlari.html
- Tercih robotu (sıralamaya göre program): /tercih-robotu.html
- Bölümlere göre taban puanları: /bolumler.html
- Üniversitelere göre taban puanları: /universiteler.html
- 2026 sınav takvimi (ÖSYM + MEB): /takvim.html
- Puan hesaplama (YKS/LGS/KPSS/DGS/ALES): /puan-hesaplama.html
- Sınav rehberleri: /rehberler.html

## İletişim
- Web: https://sinavveri.com
- Ana platform: https://trveri.com
"""
    (ROOT / "llms.txt").write_text(llms, encoding="utf-8")
    # NOT: e77c...txt Cloudflare doğrulama marker'ı SUNUCUDA yönetilir; burada üretilmez.
    print("  [+] sitemap.xml, manifest.json, sw.js, robots.txt, llms.txt")


# ───────────────────────── LEAN VERİ (istemci) ─────────────────────────
# Kompakt dizi: [kod,üni,program,grup,il,tür,öğrenim,dil,burs,kontenjan,taban,sıra,yerleşen]
def write_veri(programs):
    veri = ROOT / "veri"
    veri.mkdir(exist_ok=True)
    buckets = {"SAY": [], "EA": [], "SÖZ": [], "DİL": [], "TYT": []}
    fname = {"SAY": "say", "EA": "ea", "SÖZ": "soz", "DİL": "dil", "TYT": "tyt"}
    for r in programs:
        pt = r.get("p")
        if pt not in buckets:
            continue
        buckets[pt].append([r.get("k"), r.get("u"), r.get("b"), r.get("g"), r.get("il"),
                             r.get("t"), r.get("o"), r.get("dil"), r.get("bs"),
                             r.get("kont"), r.get("tp"), r.get("sira"), r.get("yer")])
    for pt, rows in buckets.items():
        rows.sort(key=lambda x: (x[11] is None, x[11] or 0))
        path = veri / f"{fname[pt]}.json"
        path.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"  [veri] {fname[pt]}.json  {len(rows)} kayıt, {path.stat().st_size//1024} KB")


# ───────────────────────── TABAN PUANLARI (interaktif arama) ─────────────────────────
SEARCH_JS = r"""<script nonce="__NONCE__">
(function(){
  var IDX={k:0,u:1,b:2,g:3,il:4,t:5,o:6,dil:7,bs:8,kont:9,tp:10,sira:11,yer:12};
  var TUR={D:'Devlet',V:'Vakıf',K:'KKTC',Y:'Diğer','?':'—'};
  function doluluk(r){var k=r[IDX.kont],y=r[IDX.yer];if(!k||y==null)return '—';var p=Math.round(y/k*100);var c=p>=100?'tag-lgs':(p>=70?'tag-kpss':'tag-other');return '<span class="tag '+c+'">%'+p+'</span>';}
  var data=[], shown=0, PAGE=50, cache={};
  var nf=function(n){return n==null?'—':n.toLocaleString('tr-TR');};
  var pf=function(n){return n==null?'—':n.toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2});};
  function el(id){return document.getElementById(id);}
  function load(pt){
    if(cache[pt]){data=cache[pt];afterLoad();return;}
    el('status').textContent='Veriler yükleniyor…';
    fetch('/veri/'+pt+'.json').then(function(r){return r.json();}).then(function(j){
      cache[pt]=j; data=j; afterLoad();
    }).catch(function(){el('status').textContent='Veri yüklenemedi. Lütfen tekrar deneyin.';});
  }
  function fillIl(){
    var set={}; data.forEach(function(r){if(r[IDX.il])set[r[IDX.il]]=1;});
    var ils=Object.keys(set).sort(function(a,b){return a.localeCompare(b,'tr');});
    var sel=el('fIl'); sel.innerHTML='<option value="">Tüm iller</option>';
    ils.forEach(function(i){var o=document.createElement('option');o.value=i;o.textContent=i;sel.appendChild(o);});
  }
  function afterLoad(){fillIl();render();}
  function filtered(){
    var q=(el('fQ').value||'').toLocaleLowerCase('tr').trim();
    var il=el('fIl').value, tur=el('fTur').value, dual=el('fDevlet')?null:null;
    var bursOnly=el('fBurs')&&el('fBurs').checked;
    var out=data.filter(function(r){
      if(il&&r[IDX.il]!==il)return false;
      if(tur&&r[IDX.t]!==tur)return false;
      if(bursOnly&&!/Burslu/i.test(r[IDX.bs]||''))return false;
      if(q){
        var hay=((r[IDX.b]||'')+' '+(r[IDX.u]||'')+' '+(r[IDX.g]||'')).toLocaleLowerCase('tr');
        if(hay.indexOf(q)<0)return false;
      }
      return true;
    });
    return out;
  }
  function render(reset){
    if(reset!==false)shown=0;
    var rows=filtered();
    el('status').textContent=rows.length.toLocaleString('tr-TR')+' program bulundu';
    shown=Math.min(shown+PAGE,rows.length); if(shown===0&&rows.length)shown=Math.min(PAGE,rows.length);
    var tb=el('tbody'); tb.innerHTML='';
    rows.slice(0,shown||PAGE).forEach(function(r){
      var tr=document.createElement('tr');
      tr.innerHTML='<td><strong>'+(r[IDX.b]||'')+'</strong><br><small>'+(r[IDX.u]||'')+'</small></td>'+
        '<td>'+(r[IDX.il]||'—')+'</td>'+
        '<td><span class="tag tag-other">'+(TUR[r[IDX.t]]||'—')+'</span></td>'+
        '<td>'+nf(r[IDX.kont])+'</td>'+
        '<td><strong>'+pf(r[IDX.tp])+'</strong></td>'+
        '<td>'+nf(r[IDX.sira])+'</td>'+
        '<td>'+doluluk(r)+'</td>';
      tb.appendChild(tr);
    });
    el('moreWrap').style.display = (shown<rows.length)?'block':'none';
    el('moreInfo').textContent=shown+' / '+rows.length.toLocaleString('tr-TR');
  }
  ['fQ','fIl','fTur'].forEach(function(id){var e=el(id);if(e)e.addEventListener('input',function(){render(true);});});
  if(el('fBurs'))el('fBurs').addEventListener('change',function(){render(true);});
  el('ptSel').addEventListener('change',function(){load(this.value);});
  el('moreBtn').addEventListener('click',function(){render(false);});
  load(el('ptSel').value);
})();
</script>"""


def page_taban_index():
    body = """
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / <a href="/taban-puanlari.html">Taban Puanları</a> / Üniversite</div>
<div class="page-title"><h1>Üniversite Taban Puanları 2025</h1><span class="sub">YÖK Atlas 2025 yerleştirme verisi · 21.602 program · Gerçek taban puanı ve başarı sırası</span></div>

<div class="calc-card" style="margin-bottom:18px">
  <div class="subj-head" style="grid-template-columns:1fr;border:none;padding:0;margin-bottom:10px"><span>Filtrele</span></div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px">
    <select id="ptSel" class="btn btn-ghost" style="text-align:left">
      <option value="say">Sayısal (SAY)</option>
      <option value="ea">Eşit Ağırlık (EA)</option>
      <option value="soz">Sözel (SÖZ)</option>
      <option value="dil">Dil (DİL)</option>
      <option value="tyt">TYT (Önlisans)</option>
    </select>
    <input id="fQ" type="text" placeholder="Program / üniversite ara…" style="padding:9px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:13px">
    <select id="fIl" class="btn btn-ghost" style="text-align:left"><option value="">Tüm iller</option></select>
    <select id="fTur" class="btn btn-ghost" style="text-align:left">
      <option value="">Tüm türler</option><option value="D">Devlet</option><option value="V">Vakıf</option><option value="K">KKTC</option>
    </select>
    <label style="display:flex;align-items:center;gap:6px;font-size:13px;color:var(--fg-muted)"><input type="checkbox" id="fBurs"> Sadece burslu</label>
  </div>
  <div id="status" style="margin-top:12px;font-size:13px;color:var(--accent);font-weight:700">Yükleniyor…</div>
</div>

<div class="data-table-wrap">
<table class="data-table">
<thead><tr><th>Program / Üniversite</th><th>İl</th><th>Tür</th><th>Kont.</th><th>Taban Puan</th><th>Başarı Sırası</th><th>Doluluk</th></tr></thead>
<tbody id="tbody"></tbody>
</table>
</div>
<div id="moreWrap" style="text-align:center;margin-top:16px;display:none">
  <button type="button" class="btn btn-primary" id="moreBtn">Daha fazla göster</button>
  <div id="moreInfo" style="font-size:12px;color:var(--fg-faded);margin-top:6px"></div>
</div>

<div class="notice"><b>Kaynak:</b> YÖK Atlas 2025 Tercih Kılavuzu (en güncel tamamlanmış yerleştirme). Taban puanı ve başarı sırası
o programa <b>en son yerleşen</b> adayın verisidir. Yerleşen olmayan programlarda değer boştur (—).
2026 taban puanları, yerleştirme sonrası (Ağustos 2026) güncellenecektir.</div>
""" + SEARCH_JS
    return base("universite-taban-puanlari.html", "Üniversite Taban Puanları 2025 — YÖK Atlas Verisi | SınavVeri",
                "2025 üniversite taban puanları ve başarı sıralamaları. 21.602 lisans ve önlisans programını puan türü, il ve üniversite türüne göre filtrele. YÖK Atlas verisi.",
                body)


# ───────────────────────── TERCİH ROBOTU ─────────────────────────
ROBOT_JS = r"""<script nonce="__NONCE__">
(function(){
  var IDX={k:0,u:1,b:2,g:3,il:4,t:5,o:6,dil:7,bs:8,kont:9,tp:10,sira:11};
  var TUR={D:'Devlet',V:'Vakıf',K:'KKTC',Y:'Diğer','?':'—'};
  var data=[],cache={};
  var nf=function(n){return n==null?'—':n.toLocaleString('tr-TR');};
  var pf=function(n){return n==null?'—':n.toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2});};
  function el(id){return document.getElementById(id);}
  function load(pt,cb){
    if(cache[pt]){data=cache[pt];cb();return;}
    el('rstatus').textContent='Veriler yükleniyor…';
    fetch('/veri/'+pt+'.json').then(function(r){return r.json();}).then(function(j){cache[pt]=j;data=j;cb();})
      .catch(function(){el('rstatus').textContent='Veri yüklenemedi.';});
  }
  function run(){
    var pt=el('rPt').value;
    load(pt,function(){
      var sira=parseInt((el('rSira').value||'').replace(/\D/g,''),10);
      if(!sira||sira<1){el('rstatus').textContent='Lütfen geçerli bir başarı sıranızı girin.';el('rbody').innerHTML='';return;}
      var il=el('rIl').value, tur=el('rTur').value;
      // Ulaşılabilir: programın taban sırası >= adayın sırası (aday daha iyi/eşit)
      var reach=data.filter(function(r){
        if(r[IDX.sira]==null)return false;
        if(il&&r[IDX.il]!==il)return false;
        if(tur&&r[IDX.t]!==tur)return false;
        return r[IDX.sira]>=sira;
      });
      reach.sort(function(a,b){return a[IDX.sira]-b[IDX.sira];}); // en iyi (en zor) ulaşılabilir önce
      el('rstatus').innerHTML='<b>'+reach.length.toLocaleString('tr-TR')+'</b> programa yerleşebilirsin (sıran: '+sira.toLocaleString('tr-TR')+')';
      var tb=el('rbody'); tb.innerHTML='';
      reach.slice(0,200).forEach(function(r){
        var margin=r[IDX.sira]-sira;
        var safe = margin>sira*0.25 ? '<span class="tag tag-lgs">Rahat</span>' : (margin>sira*0.05 ? '<span class="tag tag-kpss">Olası</span>' : '<span class="tag tag-other">Sınırda</span>');
        var tr=document.createElement('tr');
        tr.innerHTML='<td><strong>'+(r[IDX.b]||'')+'</strong><br><small>'+(r[IDX.u]||'')+'</small></td>'+
          '<td>'+(r[IDX.il]||'—')+'</td>'+'<td>'+(TUR[r[IDX.t]]||'—')+'</td>'+
          '<td><strong>'+pf(r[IDX.tp])+'</strong></td>'+'<td>'+nf(r[IDX.sira])+'</td>'+'<td>'+safe+'</td>';
        tb.appendChild(tr);
      });
      el('rhint').style.display = reach.length>200 ? 'block':'none';
      el('rhint').textContent='İlk 200 program gösteriliyor. Daha hassas sonuç için il/tür filtresi kullanın.';
    });
  }
  el('rBtn').addEventListener('click',run);
  el('rSira').addEventListener('keydown',function(e){if(e.key==='Enter')run();});
})();
</script>"""


def page_tercih_robotu():
    body = """
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / Tercih Robotu</div>
<div class="page-title"><h1>YKS Tercih Robotu 2025</h1><span class="sub">Başarı sıranı gir, yerleşebileceğin programları gör · YÖK Atlas 2025 verisi</span></div>

<div class="calc-card" style="margin-bottom:18px">
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;align-items:end">
    <div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">Puan Türü</label>
      <select id="rPt" class="btn btn-ghost" style="text-align:left;width:100%;margin-top:4px">
        <option value="say">Sayısal (SAY)</option><option value="ea">Eşit Ağırlık (EA)</option>
        <option value="soz">Sözel (SÖZ)</option><option value="dil">Dil (DİL)</option><option value="tyt">TYT (Önlisans)</option>
      </select></div>
    <div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">Başarı Sıran</label>
      <input id="rSira" type="text" inputmode="numeric" placeholder="örn. 45000" style="width:100%;margin-top:4px;padding:9px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:14px"></div>
    <div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">İl (ops.)</label>
      <select id="rIl" class="btn btn-ghost" style="text-align:left;width:100%;margin-top:4px"><option value="">Tüm iller</option></select></div>
    <div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">Tür (ops.)</label>
      <select id="rTur" class="btn btn-ghost" style="text-align:left;width:100%;margin-top:4px"><option value="">Hepsi</option><option value="D">Devlet</option><option value="V">Vakıf</option><option value="K">KKTC</option></select></div>
    <button type="button" class="btn btn-primary" id="rBtn">Programları Göster</button>
  </div>
  <div id="rstatus" style="margin-top:14px;font-size:14px;color:var(--accent);font-weight:700"></div>
</div>

<div class="data-table-wrap">
<table class="data-table">
<thead><tr><th>Program / Üniversite</th><th>İl</th><th>Tür</th><th>Taban Puan</th><th>Başarı Sırası</th><th>Şans</th></tr></thead>
<tbody id="rbody"></tbody>
</table>
</div>
<div id="rhint" style="display:none;font-size:12px;color:var(--fg-faded);margin-top:10px;text-align:center"></div>

<div class="notice"><b>Nasıl çalışır?</b> Başarı sıran, bir programın 2025 taban başarı sırasından <b>daha iyi (küçük)</b> veya eşitse
o programa yerleşebilirsin. "Şans" sütunu güvenlik payını gösterir: <b>Rahat</b> (geniş pay), <b>Olası</b>, <b>Sınırda</b>.
Bu bir tahmindir; 2026 taban puanları kontenjan ve tercih yoğunluğuna göre değişir. Resmî tercih için
<a href="https://www.osym.gov.tr" target="_blank" rel="noopener">ÖSYM</a> kılavuzu esastır.</div>
""" + ROBOT_JS
    # rIl doldurma — robot da fillIl benzeri ister; basitçe SEARCH veri yüklenince doldurulmuyor.
    fill = r"""<script nonce="__NONCE__">
(function(){
  var sel=document.getElementById('rIl'),ptSel=document.getElementById('rPt');
  function fill(){fetch('/veri/'+ptSel.value+'.json').then(function(r){return r.json();}).then(function(j){
    var set={};j.forEach(function(r){if(r[4])set[r[4]]=1;});
    var ils=Object.keys(set).sort(function(a,b){return a.localeCompare(b,'tr');});
    var cur=sel.value; sel.innerHTML='<option value="">Tüm iller</option>';
    ils.forEach(function(i){var o=document.createElement('option');o.value=i;o.textContent=i;if(i===cur)o.selected=true;sel.appendChild(o);});
  }).catch(function(){});}
  ptSel.addEventListener('change',fill); fill();
})();
</script>"""
    body += fill
    return base("tercih-robotu.html", "YKS Tercih Robotu 2025 — Sıralamana Göre Bölüm Bul | SınavVeri",
                "Başarı sıranı gir, 2025 YÖK Atlas verisiyle yerleşebileceğin üniversite programlarını anında gör. Ücretsiz YKS tercih robotu.",
                body)


# ───────────────────────── BÖLÜM (program grubu) SAYFALARI ─────────────────────────
def gen_bolum_pages(programs):
    from collections import defaultdict
    groups = defaultdict(list)
    for r in programs:
        if r.get("g"):
            groups[r["g"]].append(r)
    slugmap = {}
    for g in groups:
        s = slugify(g)
        # çakışma önleme
        base_s = s; i = 2
        while s in slugmap and slugmap[s] != g:
            s = f"{base_s}-{i}"; i += 1
        slugmap[s] = g
    g_by_slug = {s: g for s, g in slugmap.items()}

    for s, g in g_by_slug.items():
        recs = sorted(groups[g], key=lambda r: (r.get("sira") is None, r.get("sira") or 0))
        with_p = [r for r in recs if r.get("tp")]
        rows = ""
        for r in recs:
            rows += ("<tr><td><strong>" + (r.get("u") or "") + "</strong></td>"
                     "<td>" + (r.get("b") or "") + "</td>"
                     "<td>" + (r.get("il") or "—") + "</td>"
                     "<td>" + TUR_FULL.get(r.get("t"), "—") + "</td>"
                     "<td>" + fmt_sira(r.get("kont")) + "</td>"
                     "<td>" + doluluk_html(r) + "</td>"
                     "<td><strong>" + fmt_puan(r.get("tp")) + "</strong></td>"
                     "<td>" + fmt_puan(hist_taban(r, 2024)) + "</td>"
                     "<td>" + fmt_puan(hist_taban(r, 2023)) + "</td>"
                     "<td>" + fmt_sira(r.get("sira")) + "</td></tr>")
        tabans = [r["tp"] for r in with_p]
        en_yuksek = max(tabans) if tabans else None
        en_dusuk = min(tabans) if tabans else None
        pts = sorted(set(r.get("p") for r in recs if r.get("p")))
        summary = (f"<strong>{g}</strong> bölümü 2025'te <strong>{len(recs)}</strong> programda açıldı"
                   + (f", taban puanları <strong>{fmt_puan(en_dusuk)}</strong> – <strong>{fmt_puan(en_yuksek)}</strong> aralığında." if tabans else "."))
        chart = trend_chart(recs, "trend_" + s.replace("-", "_")[:40])
        head = PLOTLY_CDN if chart else ""
        body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / <a href="/bolumler.html">Bölümler</a> / {g}</div>
<div class="page-title"><h1>{g} Taban Puanları 2025</h1><span class="sub">YÖK Atlas 2025 · {len(recs)} program · Puan türü: {', '.join(pts)}</span></div>
<div class="info-box">{summary} Aşağıdaki tablo başarı sırasına göre sıralıdır (en düşük sıra = en yüksek puan).</div>
{chart}
<div class="data-table-wrap">
<table class="data-table">
<thead><tr><th>Üniversite</th><th>Program</th><th>İl</th><th>Tür</th><th>Kont.</th><th>Doluluk</th><th>Taban 2025</th><th>Taban 2024</th><th>Taban 2023</th><th>Sıra 2025</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</div>
<div class="notice"><b>Kaynak:</b> YÖK Atlas 2025 Tercih Kılavuzu (geçmiş: 2024/2023). Boş (—) değerler o yıl yerleşen/veri olmadığını gösterir.
Doluluk = yerleşen ÷ kontenjan. Daha fazlası: <a href="/taban-puanlari.html">tüm taban puanları</a> · <a href="/tercih-robotu.html">tercih robotu</a> · <a href="/doluluk.html">doluluk analizi</a>.</div>
"""
        html = base(f"bolum/{s}.html", f"{g} Taban Puanları 2025 ve Başarı Sıralaması | SınavVeri",
                    f"{g} bölümü 2025 taban puanları, son 4 yıl trendi, doluluk oranları ve başarı sıralaması. {len(recs)} üniversite programı YÖK Atlas verisiyle.",
                    body, extra_head=head)
        write(f"bolum/{s}.html", html)
    return g_by_slug


# ───────────────────────── ÜNİVERSİTE SAYFALARI ─────────────────────────
def gen_universite_pages(programs):
    from collections import defaultdict
    unis = defaultdict(list)
    for r in programs:
        if r.get("u"):
            unis[r["u"]].append(r)
    slugmap = {}
    for u in unis:
        s = slugify(u); base_s = s; i = 2
        while s in slugmap and slugmap[s] != u:
            s = f"{base_s}-{i}"; i += 1
        slugmap[s] = u
    u_by_slug = {s: u for s, u in slugmap.items()}
    for s, u in u_by_slug.items():
        recs = sorted(unis[u], key=lambda r: (r.get("sira") is None, r.get("sira") or 0))
        il = next((r.get("il") for r in recs if r.get("il")), "")
        tur = next((TUR_FULL.get(r.get("t")) for r in recs if r.get("t")), "")
        rows = ""
        for r in recs:
            rows += ("<tr><td><strong>" + (r.get("b") or "") + "</strong></td>"
                     "<td>" + (r.get("g") or "—") + "</td>"
                     "<td>" + PT_LABEL.get(r.get("p"), r.get("p") or "—") + "</td>"
                     "<td>" + fmt_sira(r.get("kont")) + "</td>"
                     "<td>" + doluluk_html(r) + "</td>"
                     "<td><strong>" + fmt_puan(r.get("tp")) + "</strong></td>"
                     "<td>" + fmt_puan(hist_taban(r, 2024)) + "</td>"
                     "<td>" + fmt_sira(r.get("sira")) + "</td></tr>")
        body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / <a href="/universiteler.html">Üniversiteler</a> / {u}</div>
<div class="page-title"><h1>{u} Taban Puanları 2025</h1><span class="sub">{il} · {tur} · {len(recs)} program · YÖK Atlas 2025</span></div>
<div class="data-table-wrap">
<table class="data-table">
<thead><tr><th>Program</th><th>Bölüm Grubu</th><th>Puan Türü</th><th>Kont.</th><th>Doluluk</th><th>Taban 2025</th><th>Taban 2024</th><th>Başarı Sırası</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</div>
<div class="notice"><b>Kaynak:</b> YÖK Atlas 2025 (geçmiş: 2024). Doluluk = yerleşen ÷ kontenjan. Başarı sırasına göre sıralı.
<a href="/taban-puanlari.html">Tüm taban puanları</a> · <a href="/tercih-robotu.html">tercih robotu</a> · <a href="/doluluk.html">doluluk analizi</a>.</div>
"""
        html = base(f"universite/{s}.html", f"{u} Taban Puanları 2025 — Tüm Bölümler | SınavVeri",
                    f"{u} 2025 taban puanları ve başarı sıralamaları. {len(recs)} programın taban puanı, kontenjan ve sıralaması YÖK Atlas verisiyle.",
                    body)
        write(f"universite/{s}.html", html)
    return u_by_slug


# ───────────────────────── INDEX SAYFALARI (bölüm/üni listesi) ─────────────────────────
def page_bolumler(g_by_slug, programs):
    from collections import Counter
    cnt = Counter(r["g"] for r in programs if r.get("g"))
    items = sorted(g_by_slug.items(), key=lambda kv: kv[1].lower())
    cards = ""
    for s, g in items:
        cards += f'<a class="tool-btn" href="/bolum/{s}.html"><span class="tb-icon">📘</span><span class="tb-text"><b>{g}</b><span>{cnt.get(g,0)} program</span></span></a>'
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / Bölümler</div>
<div class="page-title"><h1>Bölümlere Göre Taban Puanları</h1><span class="sub">{len(items)} bölüm grubu · YÖK Atlas 2025</span></div>
<input id="bSearch" type="text" placeholder="Bölüm ara… (örn. tıp, hukuk, bilgisayar)" style="width:100%;max-width:480px;padding:10px 12px;border:1px solid var(--border);border-radius:9px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:14px;margin-bottom:18px">
<div class="tool-row" id="bList">
{cards}
</div>
<script nonce="__NONCE__">
(function(){{
  var q=document.getElementById('bSearch'),list=document.getElementById('bList');
  var items=Array.prototype.slice.call(list.children);
  q.addEventListener('input',function(){{
    var v=this.value.toLocaleLowerCase('tr').trim();
    items.forEach(function(a){{a.style.display = a.textContent.toLocaleLowerCase('tr').indexOf(v)>=0?'':'none';}});
  }});
}})();
</script>
"""
    return base("bolumler.html", "Bölümlere Göre Üniversite Taban Puanları 2025 | SınavVeri",
                "Tüm üniversite bölümlerinin 2025 taban puanları. Tıp, hukuk, mühendislik, psikoloji ve 600+ bölüm grubu YÖK Atlas verisiyle.",
                body)


def page_universiteler(u_by_slug, programs):
    from collections import Counter
    cnt = Counter(r["u"] for r in programs if r.get("u"))
    ilmap = {}
    for r in programs:
        if r.get("u") and r.get("il") and r["u"] not in ilmap:
            ilmap[r["u"]] = r["il"]
    items = sorted(u_by_slug.items(), key=lambda kv: kv[1].lower())
    cards = ""
    for s, u in items:
        cards += f'<a class="tool-btn" href="/universite/{s}.html"><span class="tb-icon">🏛️</span><span class="tb-text"><b>{u}</b><span>{ilmap.get(u,"")} · {cnt.get(u,0)} program</span></span></a>'
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / Üniversiteler</div>
<div class="page-title"><h1>Üniversitelere Göre Taban Puanları</h1><span class="sub">{len(items)} üniversite · YÖK Atlas 2025</span></div>
<input id="uSearch" type="text" placeholder="Üniversite ara… (örn. boğaziçi, ege, itü)" style="width:100%;max-width:480px;padding:10px 12px;border:1px solid var(--border);border-radius:9px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:14px;margin-bottom:18px">
<div class="tool-row" id="uList">
{cards}
</div>
<script nonce="__NONCE__">
(function(){{
  var q=document.getElementById('uSearch'),list=document.getElementById('uList');
  var items=Array.prototype.slice.call(list.children);
  q.addEventListener('input',function(){{
    var v=this.value.toLocaleLowerCase('tr').trim();
    items.forEach(function(a){{a.style.display = a.textContent.toLocaleLowerCase('tr').indexOf(v)>=0?'':'none';}});
  }});
}})();
</script>
"""
    return base("universiteler.html", "Üniversitelere Göre Taban Puanları 2025 | SınavVeri",
                "Tüm üniversitelerin 2025 taban puanları ve bölümleri. 227 devlet ve vakıf üniversitesi YÖK Atlas verisiyle.",
                body)


# ───────────────────────── LGS LİSE TABAN PUANLARI ─────────────────────────
LISE_TUR_CODE = {"Fen Lisesi": "F", "Sosyal Bilimler Lisesi": "S", "Anadolu Lisesi": "A",
                 "Anadolu İmam Hatip Lisesi": "I", "Mesleki ve Teknik Anadolu Lisesi": "M",
                 "Güzel Sanatlar Lisesi": "G", "Spor Lisesi": "P", "Diğer": "D"}
LISE_TUR_NAME = {v: k for k, v in LISE_TUR_CODE.items()}


def load_lgs():
    p = ROOT / "data" / "lgs_liseler.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def write_lgs_veri(lgs):
    # [il, ilce, okul, türKodu, kontenjan, taban, yüzdelik]
    rows = [[r["il"], r["ilce"], r["okul"], LISE_TUR_CODE.get(r["tur"], "D"),
             r["kont"], r["tp"], r["yuz"]] for r in lgs]
    rows.sort(key=lambda x: (x[5] is None, -(x[5] or 0)))
    (ROOT / "veri").mkdir(exist_ok=True)
    path = ROOT / "veri" / "liseler.json"
    path.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  [veri] liseler.json  {len(rows)} okul, {path.stat().st_size//1024} KB")


LISE_SEARCH_JS = r"""<script nonce="__NONCE__">
(function(){
  var TUR={F:'Fen Lisesi',S:'Sosyal Bilimler L.',A:'Anadolu Lisesi',I:'Anadolu İmam Hatip L.',M:'Mesleki ve Teknik',G:'Güzel Sanatlar L.',P:'Spor Lisesi',D:'Diğer'};
  var data=[],shown=0,PAGE=50;
  var nf=function(n){return n==null?'—':n.toLocaleString('tr-TR');};
  var pf=function(n){return n==null?'—':n.toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2});};
  function el(id){return document.getElementById(id);}
  fetch('/veri/liseler.json').then(function(r){return r.json();}).then(function(j){data=j;fillIl();render();})
    .catch(function(){el('status').textContent='Veri yüklenemedi.';});
  function fillIl(){
    var set={};data.forEach(function(r){if(r[0])set[r[0]]=1;});
    var ils=Object.keys(set).sort(function(a,b){return a.localeCompare(b,'tr');});
    var sel=el('fIl');ils.forEach(function(i){var o=document.createElement('option');o.value=i;o.textContent=i;sel.appendChild(o);});
  }
  function filtered(){
    var q=(el('fQ').value||'').toLocaleLowerCase('tr').trim(),il=el('fIl').value,tur=el('fTur').value;
    return data.filter(function(r){
      if(il&&r[0]!==il)return false;
      if(tur&&r[3]!==tur)return false;
      if(q){var hay=((r[2]||'')+' '+(r[1]||'')+' '+(r[0]||'')).toLocaleLowerCase('tr');if(hay.indexOf(q)<0)return false;}
      return true;
    });
  }
  function render(reset){
    if(reset!==false)shown=0;
    var rows=filtered();
    el('status').textContent=rows.length.toLocaleString('tr-TR')+' lise bulundu';
    shown=Math.min(shown+PAGE,rows.length);if(shown===0&&rows.length)shown=Math.min(PAGE,rows.length);
    var tb=el('tbody');tb.innerHTML='';
    rows.slice(0,shown||PAGE).forEach(function(r){
      var tr=document.createElement('tr');
      tr.innerHTML='<td><strong>'+(r[2]||'')+'</strong></td><td>'+(r[0]||'')+(r[1]?' / '+r[1]:'')+'</td>'+
        '<td><span class="tag tag-other">'+(TUR[r[3]]||'—')+'</span></td>'+
        '<td>'+nf(r[4])+'</td><td><strong>'+pf(r[5])+'</strong></td><td>'+(r[6]==null?'—':'%'+pf(r[6]))+'</td>';
      tb.appendChild(tr);
    });
    el('moreWrap').style.display=(shown<rows.length)?'block':'none';
    el('moreInfo').textContent=shown+' / '+rows.length.toLocaleString('tr-TR');
  }
  ['fQ','fIl','fTur'].forEach(function(id){el(id).addEventListener('input',function(){render(true);});});
  el('moreBtn').addEventListener('click',function(){render(false);});
})();
</script>"""


def page_lise_taban_index(lgs, il_slugs):
    il_links = ""
    for sl, il in sorted(il_slugs.items(), key=lambda kv: kv[1].lower()):
        il_links += f'<a href="/lise/{sl}.html" style="display:inline-block;margin:2px 4px;font-size:13px">{il}</a>'
    body = """
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / LGS Lise Taban Puanları</div>
<div class="page-title"><h1>LGS Lise Taban Puanları 2025</h1><span class="sub">81 il · 3.000+ sınavla öğrenci alan lise · Taban puanı ve yüzdelik dilim</span></div>
<div class="calc-card" style="margin-bottom:18px">
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px">
    <input id="fQ" type="text" placeholder="Lise / ilçe ara…" style="padding:9px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:13px">
    <select id="fIl" class="btn btn-ghost" style="text-align:left"><option value="">Tüm iller</option></select>
    <select id="fTur" class="btn btn-ghost" style="text-align:left">
      <option value="">Tüm türler</option><option value="F">Fen Lisesi</option><option value="S">Sosyal Bilimler</option>
      <option value="A">Anadolu Lisesi</option><option value="I">Anadolu İmam Hatip</option><option value="M">Mesleki ve Teknik</option>
    </select>
  </div>
  <div id="status" style="margin-top:12px;font-size:13px;color:var(--accent);font-weight:700">Yükleniyor…</div>
</div>
<div class="data-table-wrap">
<table class="data-table">
<thead><tr><th>Lise</th><th>İl / İlçe</th><th>Tür</th><th>Kont.</th><th>Taban Puan</th><th>Yüzdelik</th></tr></thead>
<tbody id="tbody"></tbody>
</table>
</div>
<div id="moreWrap" style="text-align:center;margin-top:16px;display:none">
  <button type="button" class="btn btn-primary" id="moreBtn">Daha fazla göster</button>
  <div id="moreInfo" style="font-size:12px;color:var(--fg-faded);margin-top:6px"></div>
</div>
<div class="notice"><b>Kaynak:</b> MEB 2025 LGS merkezi yerleştirme verileri. Taban puanı ve yüzdelik dilim,
o liseye <b>en son yerleşen</b> öğrencinin değeridir. Yalnızca <b>sınavla öğrenci alan</b> liseler listelenir.
Resmî kayıt için <a href="https://www.meb.gov.tr" target="_blank" rel="noopener">MEB</a>/e-Okul esastır.</div>
<div class="section" style="margin-top:24px"><h2>İllere Göre Lise Taban Puanları</h2>
<div class="section-sub">İl sayfasında o ilin tüm liseleri taban puanına göre sıralı.</div>
<div style="line-height:2">""" + il_links + """</div></div>
""" + LISE_SEARCH_JS
    return base("lise-taban-puanlari.html", "LGS Lise Taban Puanları 2025 — İl İl Tüm Liseler | SınavVeri",
                "2025 LGS lise taban puanları ve yüzdelik dilimleri. 81 ilde 3000+ Fen, Anadolu, İmam Hatip ve Meslek lisesi. İl ve türe göre filtrele.",
                body)


def gen_lise_il_pages(lgs):
    from collections import defaultdict
    by_il = defaultdict(list)
    for r in lgs:
        by_il[r["il"]].append(r)
    slugs = {}
    for il in by_il:
        slugs[slugify(il)] = il
    for sl, il in slugs.items():
        recs = sorted(by_il[il], key=lambda r: (r.get("tp") is None, -(r.get("tp") or 0)))
        rows = ""
        for r in recs:
            yuz = ("%" + fmt_puan(r["yuz"])) if r.get("yuz") is not None else "—"
            rows += ("<tr><td><strong>" + (r.get("okul") or "") + "</strong></td>"
                     "<td>" + (r.get("ilce") or "—") + "</td>"
                     "<td>" + (r.get("tur") or "—") + "</td>"
                     "<td>" + fmt_sira(r.get("kont")) + "</td>"
                     "<td><strong>" + fmt_puan(r.get("tp")) + "</strong></td>"
                     "<td>" + yuz + "</td></tr>")
        tabans = [r["tp"] for r in recs if r.get("tp")]
        fen = [r for r in recs if r["tur"] == "Fen Lisesi"]
        summary = (f"<strong>{il}</strong> ilinde 2025 LGS ile öğrenci alan <strong>{len(recs)}</strong> lise listelenmiştir"
                   + (f"; taban puanları <strong>{fmt_puan(min(tabans))}</strong> – <strong>{fmt_puan(max(tabans))}</strong> aralığında." if tabans else "."))
        body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / <a href="/lise-taban-puanlari.html">LGS Liseler</a> / {il}</div>
<div class="page-title"><h1>{il} Liseleri Taban Puanları 2025 (LGS)</h1><span class="sub">{len(recs)} sınavla öğrenci alan lise · MEB 2025 · taban puanı + yüzdelik dilim</span></div>
<div class="info-box">{summary} Tablo taban puanına göre sıralıdır (yüksek puan = daha yüksek başarı).</div>
<div class="data-table-wrap">
<table class="data-table">
<thead><tr><th>Lise</th><th>İlçe</th><th>Tür</th><th>Kont.</th><th>Taban Puan</th><th>Yüzdelik</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</div>
<div class="notice"><b>Kaynak:</b> MEB 2025 LGS merkezi yerleştirme verileri. Yalnızca sınavla öğrenci alan liseler.
Tüm Türkiye: <a href="/lise-taban-puanlari.html">LGS lise taban puanları</a> · <a href="/lgs-puan-hesaplama.html">LGS puan hesaplama</a>.</div>
"""
        html = base(f"lise/{sl}.html", f"{il} Liseleri Taban Puanları 2025 LGS — Yüzdelik Dilim | SınavVeri",
                    f"{il} 2025 LGS lise taban puanları ve yüzdelik dilimleri. {len(recs)} sınavla öğrenci alan Fen, Anadolu, İmam Hatip ve Meslek lisesi. MEB verisi.",
                    body)
        write(f"lise/{sl}.html", html)
    return slugs


# ───────────────────────── TABAN PUANLARI HUB ─────────────────────────
def page_taban_hub():
    live = [
        ("/universite-taban-puanlari.html", "🎓", "Üniversite Taban Puanları", "YKS · 21.602 lisans/önlisans programı · YÖK Atlas 2025"),
        ("/lise-taban-puanlari.html", "🏫", "LGS Lise Taban Puanları", "81 il · 3.000+ sınavla öğrenci alan lise · MEB 2025"),
        ("/tus-taban-puanlari.html", "🩺", "TUS Taban Puanları", "Tıpta uzmanlık · kurum × dal · ÖSYM resmî 2025"),
        ("/dus-taban-puanlari.html", "🦷", "DUS Taban Puanları", "Diş hekimliği uzmanlık · kurum × dal · ÖSYM resmî 2025"),
        ("/dgs-taban-puanlari.html", "📈", "DGS Taban Puanları", "Dikey geçiş · 7.000+ üniversite programı · ÖSYM resmî 2025"),
        ("/kpss-atama-taban-puanlari.html", "🏛️", "KPSS Atama Taban Puanları", "Kadro bazında atama puanları · ÖSYM resmî 2025"),
        ("/bolumler.html", "📘", "Bölümlere Göre", "600+ bölüm grubu taban puanı"),
        ("/universiteler.html", "🏫", "Üniversitelere Göre", "227 üniversite"),
        ("/doluluk.html", "📊", "Doluluk Analizi", "Kontenjan & doluluk oranları 2025"),
    ]
    cards = "".join(
        f'<a class="exam-card" href="{h}"><div class="ec-top"><span class="ec-icon">{i}</span>'
        f'<div><div class="ec-title">{t}</div></div></div><div class="ec-desc">{d}</div>'
        f'<div class="ec-meta"><span>Görüntüle →</span></div></a>' for h, i, t, d in live)
    roadmap = ["KPSS atama — diğer yerleştirme dönemleri (2025/2, /3, /4 ...) eklenmesi",
               "YDUS (Yan Dal Uzmanlık) taban puanları",
               "Çok yıllık taban puan trendi (2022-2025)"]
    rm = "".join(f"<li>{x}</li>" for x in roadmap)
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / Taban Puanları</div>
<div class="page-title"><h1>Taban Puanları Merkezi</h1><span class="sub">Türkiye'deki tüm merkezi sınavların güncel taban puanları tek çatıda · 2025 verileri</span></div>
<div class="section">
  <div class="card-grid">{cards}</div>
</div>
<div class="info-box"><h3>Hangi taban puanları var?</h3>
<strong>Üniversite (YKS)</strong>, <strong>LGS Lise</strong>, <strong>TUS</strong>, <strong>DUS</strong>, <strong>DGS</strong> ve <strong>KPSS atama</strong> taban puanları gerçek resmî verilerle yayında.
Kaynaklar: YÖK Atlas (üniversite), MEB (LGS), <strong>ÖSYM resmî 'En Küçük ve En Büyük Puanlar' yayını</strong> (TUS/DUS/DGS/KPSS).</div>
<div class="section">
  <h2>Yakında Eklenecekler</h2>
  <div class="section-sub">Planlanan taban puanı veri setleri:</div>
  <ul style="margin-left:20px;color:var(--fg-muted);line-height:1.9">{rm}</ul>
</div>
"""
    return base("taban-puanlari.html", "Taban Puanları 2025 — Üniversite, LGS, TUS, DUS, DGS, KPSS | SınavVeri",
                "2025 taban puanları merkezi: üniversite (YKS), LGS lise, TUS, DUS, DGS ve KPSS atama taban puanları ve başarı sıralamaları tek çatıda.",
                body)


# ───────────────────────── ÖSYM RESMİ TABAN PUANLARI (TUS/DUS/DGS/KPSS) ─────────────────────────
# Kaynak: ÖSYM 'En Küçük ve En Büyük Puanlar' resmî PDF'leri (dokuman.osym.gov.tr).
GENERIC_SEARCH_JS = r"""<script nonce="__NONCE__">
(function(){
  var CFG=__CFG__;
  var data=[],shown=0,PAGE=50;
  function el(id){return document.getElementById(id);}
  var nf=function(n){return n==null?'—':Number(n).toLocaleString('tr-TR');};
  var pf=function(n){return n==null?'—':Number(n).toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2});};
  el('status').textContent='Veriler yükleniyor…';
  fetch(CFG.file).then(function(r){return r.json();}).then(function(j){data=j;initFilters();render();})
    .catch(function(){el('status').textContent='Veri yüklenemedi.';});
  function initFilters(){
    CFG.filters.forEach(function(f){
      var set={};data.forEach(function(r){if(r[f[0]])set[r[f[0]]]=1;});
      var vals=Object.keys(set).sort(function(a,b){return a.localeCompare(b,'tr');});
      var sel=el('fil'+f[1]);if(!sel)return;
      vals.forEach(function(v){var o=document.createElement('option');o.value=v;o.textContent=v;sel.appendChild(o);});
    });
  }
  function filtered(){
    var q=(el('fQ').value||'').toLocaleLowerCase('tr').trim();
    return data.filter(function(r){
      for(var k=0;k<CFG.filters.length;k++){var f=CFG.filters[k];var s=el('fil'+f[1]);if(s&&s.value&&String(r[f[0]])!==s.value)return false;}
      if(q){var hay='';CFG.search.forEach(function(i){hay+=' '+(r[i]||'');});if(hay.toLocaleLowerCase('tr').indexOf(q)<0)return false;}
      return true;
    });
  }
  function render(reset){
    if(reset!==false)shown=0;
    var rows=filtered();
    el('status').textContent=rows.length.toLocaleString('tr-TR')+' sonuç bulundu';
    shown=Math.min(shown+PAGE,rows.length);if(shown===0&&rows.length)shown=Math.min(PAGE,rows.length);
    var tb=el('tbody');tb.innerHTML='';
    rows.slice(0,shown||PAGE).forEach(function(r){
      var html='';
      CFG.cols.forEach(function(c){
        var v=r[c[0]],cell;
        if(c[1]==='p')cell='<strong>'+pf(v)+'</strong>';
        else if(c[1]==='pv')cell=pf(v);
        else if(c[1]==='n')cell=nf(v);
        else if(c[1]==='b')cell='<strong>'+(v==null?'—':v)+'</strong>';
        else cell=(v==null?'—':v);
        html+='<td>'+cell+'</td>';
      });
      var tr=document.createElement('tr');tr.innerHTML=html;tb.appendChild(tr);
    });
    el('moreWrap').style.display=(shown<rows.length)?'block':'none';
    el('moreInfo').textContent=shown+' / '+rows.length.toLocaleString('tr-TR');
  }
  el('fQ').addEventListener('input',function(){render(true);});
  CFG.filters.forEach(function(f){var s=el('fil'+f[1]);if(s)s.addEventListener('change',function(){render(true);});});
  el('moreBtn').addEventListener('click',function(){render(false);});
})();
</script>"""


def minmax_page(slug, title, desc, h1, sub, file, cols, filters, search_idx, intro, kaynak, ph="Ara…"):
    """Generic ÖSYM taban puanı interaktif arama sayfası.
    cols: [(dataIdx, label, kind)] kind: b=kalın metin, t=metin, n=tamsayı, p=taban(kalın), pv=tavan
    filters: [(dataIdx, label)] → dropdown
    """
    thead = "".join(f"<th>{c[1]}</th>" for c in cols)
    fhtml = (f'<input id="fQ" type="text" placeholder="{ph}" style="padding:9px 10px;border:1px solid var(--border);'
             'border-radius:8px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:13px">')
    for n, (idx, label) in enumerate(filters):
        fhtml += f'<select id="fil{n}" class="btn btn-ghost" style="text-align:left"><option value="">{label} (tümü)</option></select>'
    cfg = {"file": file, "cols": [[c[0], c[2]] for c in cols],
           "filters": [[idx, n] for n, (idx, label) in enumerate(filters)], "search": search_idx}
    js = GENERIC_SEARCH_JS.replace("__CFG__", json.dumps(cfg, ensure_ascii=False))
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / <a href="/taban-puanlari.html">Taban Puanları</a> / {h1}</div>
<div class="page-title"><h1>{h1}</h1><span class="sub">{sub}</span></div>
<div class="info-box">{intro}</div>
<div class="calc-card" style="margin-bottom:18px">
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px">{fhtml}</div>
  <div id="status" style="margin-top:12px;font-size:13px;color:var(--accent);font-weight:700">Yükleniyor…</div>
</div>
<div class="data-table-wrap">
<table class="data-table"><thead><tr>{thead}</tr></thead><tbody id="tbody"></tbody></table>
</div>
<div id="moreWrap" style="text-align:center;margin-top:16px;display:none">
  <button type="button" class="btn btn-primary" id="moreBtn">Daha fazla göster</button>
  <div id="moreInfo" style="font-size:12px;color:var(--fg-faded);margin-top:6px"></div>
</div>
<div class="notice"><b>Kaynak:</b> {kaynak} Taban = o programa/kadroya yerleşen <b>en düşük</b>, tavan = <b>en yüksek</b> puan.
Yerleşen olmayan satırlarda değer boştur (—). Resmî bilgi için <a href="https://www.osym.gov.tr" target="_blank" rel="noopener">ÖSYM</a> esastır.</div>
{js}
"""
    return base(slug, title, desc, body)


OSYM_KAYNAK = "ÖSYM 2025 'En Küçük ve En Büyük Puanlar' resmî yayını (dokuman.osym.gov.tr)."


def _load_osym(name):
    p = ROOT / "data" / f"osym_{name}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _osym_trend(r):
    """Çok-yıllık taban trendi: 2025 vs en yakın önceki yıl (2024, yoksa 2023).
    '↑ +X,XX' / '↓ -X,XX' / '→ 0' / '' (geçmiş yoksa)."""
    cur = r["tp"]
    prev = r.get("tp24") if r.get("tp24") is not None else r.get("tp23")
    if cur is None or prev is None:
        return ""
    diff = round(cur - prev, 2)
    if diff > 0.005:
        return "↑ +%s" % ("%.2f" % diff).replace(".", ",")
    if diff < -0.005:
        return "↓ %s" % ("%.2f" % diff).replace(".", ",")
    return "→ 0"


def write_osym_veri():
    """Resmî ÖSYM verisinden istemci JSON'ları üret. Döndürür: mevcut sınavların sayıları."""
    veri = ROOT / "veri"
    veri.mkdir(exist_ok=True)
    counts = {}

    def dump(name, rows):
        path = veri / f"{name}.json"
        path.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        counts[name] = len(rows)
        print(f"  [veri] {name}.json  {len(rows)} satır, {path.stat().st_size // 1024} KB")

    # TUS/DUS: [kurum, dal, tur, kont, tp(2025), tavan, tp24, tp23, trend] — çok-yıllık
    for ex in ("tus", "dus"):
        d = _load_osym(ex)
        if not d:
            continue
        rows = [[r["kurum"], r["dal"], r["tur"], r["kont"], r["tp"], r["tavan"],
                 r.get("tp24"), r.get("tp23"), _osym_trend(r)] for r in d]
        rows.sort(key=lambda x: (x[4] is None, -(x[4] or 0)))
        dump(ex, rows)
    # DGS: [uni, bolum, kont, tp(2025), tavan, tp24, tp23, trend] — çok-yıllık
    d = _load_osym("dgs")
    if d:
        rows = [[r["uni"], r["bolum"], r["kont"], r["tp"], r["tavan"],
                 r.get("tp24"), r.get("tp23"), _osym_trend(r)] for r in d]
        rows.sort(key=lambda x: (x[3] is None, -(x[3] or 0)))
        dump("dgs", rows)
    # KPSS: [kurum, kadro, il, duzey, donem, kont, tp, tavan]
    d = _load_osym("kpss")
    if d:
        rows = [[r["kurum"], r["kadro"], r["il"], r["duzey"], r.get("donem", ""), r["kont"], r["tp"], r["tavan"]] for r in d]
        rows.sort(key=lambda x: (x[6] is None, -(x[6] or 0)))
        dump("kpss", rows)
    return counts


def page_tus():
    if not (ROOT / "veri" / "tus.json").exists():
        return None
    return minmax_page(
        "tus-taban-puanlari.html", "TUS Taban Puanları 2023-2025 — Kurum ve Uzmanlık Dalı | SınavVeri",
        "TUS taban ve tavan puanları (2025/1) + 2024 ve 2023 karşılaştırması, her hastane/üniversite ve uzmanlık dalı için. ÖSYM resmî, 3 yıllık trend. Kardiyoloji, radyoloji, genel cerrahi ve tüm branşlar.",
        "TUS Taban Puanları (3 Yıllık Trend)", "Tıpta Uzmanlık · kurum × uzmanlık dalı · ÖSYM resmî 1. dönem 2023→2025",
        "/veri/tus.json",
        [(1, "Uzmanlık Dalı", "b"), (0, "Kurum", "t"), (3, "Kont.", "n"),
         (4, "2025 Taban", "p"), (6, "2024", "pv"), (7, "2023", "pv"), (8, "Trend", "t"), (5, "Tavan", "pv")],
        [(1, "Uzmanlık Dalı"), (2, "Kontenjan Türü")], [0, 1],
        "TUS'ta her kurum ve uzmanlık dalı için ÖSYM'nin açıkladığı en düşük (taban) ve en yüksek (tavan) puanlar, "
        "<b>son 3 yılın (2023-2024-2025, 1. dönem) karşılaştırmasıyla</b>. Trend sütunu 2025 tabanının bir önceki yıla göre değişimini gösterir. "
        "Dal veya kurum/şehir arayın, uzmanlık dalına göre filtreleyin.",
        "ÖSYM 2023, 2024 ve 2025 TUS 1. Dönem 'En Küçük ve En Büyük Puanlar' resmî yayınları (dokuman.osym.gov.tr).",
        ph="Dal / kurum / şehir ara…")


def page_dus():
    if not (ROOT / "veri" / "dus.json").exists():
        return None
    return minmax_page(
        "dus-taban-puanlari.html", "DUS Taban Puanları 2023-2025 — Kurum ve Uzmanlık Dalı | SınavVeri",
        "DUS taban ve tavan puanları (2025/1) + 2024 ve 2023 karşılaştırması, her diş hekimliği fakültesi ve uzmanlık dalı için. ÖSYM resmî, 3 yıllık trend.",
        "DUS Taban Puanları (3 Yıllık Trend)", "Diş Hekimliği Uzmanlık · kurum × dal · ÖSYM resmî 1. dönem 2023→2025",
        "/veri/dus.json",
        [(1, "Uzmanlık Dalı", "b"), (0, "Kurum", "t"), (3, "Kont.", "n"),
         (4, "2025 Taban", "p"), (6, "2024", "pv"), (7, "2023", "pv"), (8, "Trend", "t"), (5, "Tavan", "pv")],
        [(1, "Uzmanlık Dalı")], [0, 1],
        "DUS'ta her kurum ve diş hekimliği uzmanlık dalı için ÖSYM'nin açıkladığı taban ve tavan puanlar, "
        "<b>son 3 yılın (2023-2024-2025) karşılaştırmasıyla</b>. Trend sütunu 2025 tabanının bir önceki yıla göre değişimini gösterir.",
        "ÖSYM 2023, 2024 ve 2025 DUS 'En Küçük ve En Büyük Puanlar' resmî yayınları (dokuman.osym.gov.tr).",
        ph="Dal / kurum ara…")


def page_dgs_taban():
    if not (ROOT / "veri" / "dgs.json").exists():
        return None
    return minmax_page(
        "dgs-taban-puanlari.html", "DGS Taban Puanları 2023-2025 — Üniversite ve Program | SınavVeri",
        "DGS taban ve tavan puanları (2025) + 2024 ve 2023 karşılaştırması, her üniversite programı için. Dikey geçiş ÖSYM resmî verisi, 7000+ program, 3 yıllık trend.",
        "DGS Taban Puanları (3 Yıllık Trend)", "Dikey Geçiş · üniversite × program · ÖSYM resmî 2023→2025",
        "/veri/dgs.json",
        [(1, "Program", "b"), (0, "Üniversite", "t"), (2, "Kont.", "n"),
         (3, "2025 Taban", "p"), (5, "2024", "pv"), (6, "2023", "pv"), (7, "Trend", "t"), (4, "Tavan", "pv")],
        [], [0, 1],
        "DGS ile ön lisanstan lisansa geçişte her üniversite programının ÖSYM'nin açıkladığı taban ve tavan puanları, "
        "<b>son 3 yılın (2023-2024-2025) karşılaştırmasıyla</b>. Trend sütunu 2025 tabanının bir önceki yıla göre değişimini gösterir "
        "(↑ yükseliş, ↓ düşüş). Program kodu yıllar arası eşleştirilir; yeni açılan programlarda geçmiş boştur. "
        "Program veya üniversite adı arayın. DGS net hesaplama için <a href='/dgs-puan-hesaplama.html'>DGS puan hesaplama</a>.",
        "ÖSYM 2023, 2024 ve 2025 'DGS Yerleştirme Sonuçlarına İlişkin En Küçük ve En Büyük Puanlar' resmî yayınları (dokuman.osym.gov.tr).",
        ph="Program / üniversite ara…")


def page_kpss_atama():
    if not (ROOT / "veri" / "kpss.json").exists():
        return None
    return minmax_page(
        "kpss-atama-taban-puanlari.html", "KPSS Atama Taban Puanları 2025 — Kadro Bazında | SınavVeri",
        "2025 KPSS atama taban ve tavan puanları, kadro/pozisyon bazında. ÖSYM resmî yerleştirme verisi (KPSS-2025/1 ve Sağlık Bakanlığı).",
        "KPSS Atama Taban Puanları 2025", "Kadro/pozisyon bazında atama puanları · ÖSYM resmî · 2025 tüm yerleştirmeler",
        "/veri/kpss.json",
        [(1, "Kadro", "b"), (0, "Kurum", "t"), (2, "İl", "t"), (3, "Düzey", "t"), (4, "Dönem", "t"), (6, "Taban", "p"), (7, "Tavan", "pv")],
        [(2, "İl"), (3, "Düzey"), (4, "Dönem")], [0, 1],
        "KPSS ile atanılan her kadro/pozisyon için ÖSYM'nin açıkladığı taban ve tavan puanlar. "
        "Kadro veya kurum arayın; il, öğrenim düzeyi ve yerleştirme dönemine göre filtreleyin. "
        "<b>Kapsam:</b> 2025 yılının tüm KPSS yerleştirmeleri (2025/1–2025/5: Genel, Çevre Bak., Sağlık Bak.).",
        OSYM_KAYNAK, ph="Kadro / kurum ara…")


# ───────────────────────── DOLULUK ANALİZİ ─────────────────────────
def page_doluluk(programs):
    from collections import defaultdict

    def agg(recs):
        k = sum(r["kont"] for r in recs if r.get("kont"))
        y = sum(r["yer"] for r in recs if r.get("yer") is not None and r.get("kont"))
        return k, y, (round(y / k * 100, 1) if k else 0)

    valid = [r for r in programs if r.get("kont") and r.get("yer") is not None]
    tk, ty, tp = agg(valid)

    # tür bazında
    tur_rows = ""
    for code, name in [("D", "Devlet"), ("V", "Vakıf"), ("K", "KKTC")]:
        k, y, p = agg([r for r in valid if r.get("t") == code])
        if k:
            tur_rows += f"<tr><td><strong>{name}</strong></td><td>{fmt_sira(k)}</td><td>{fmt_sira(y)}</td><td><strong>%{p}</strong></td></tr>"
    # düzey bazında
    lis = [r for r in valid if r.get("p") in ("SAY", "EA", "SÖZ", "DİL")]
    onl = [r for r in valid if r.get("p") == "TYT"]
    lk, ly, lp = agg(lis); ok, oy, op = agg(onl)
    duzey_rows = (f"<tr><td><strong>Lisans (4 yıllık)</strong></td><td>{fmt_sira(lk)}</td><td>{fmt_sira(ly)}</td><td><strong>%{lp}</strong></td></tr>"
                  f"<tr><td><strong>Önlisans (2 yıllık)</strong></td><td>{fmt_sira(ok)}</td><td>{fmt_sira(oy)}</td><td><strong>%{op}</strong></td></tr>")

    # bölüm grubu bazında (>=30 program)
    groups = defaultdict(list)
    for r in valid:
        if r.get("g"):
            groups[r["g"]].append(r)
    grp_stats = []
    for g, recs in groups.items():
        if len(recs) >= 30:
            k, y, p = agg(recs)
            grp_stats.append((g, p, len(recs), k, y))
    grp_stats.sort(key=lambda x: x[1])
    bos = grp_stats[:15]
    dolu = sorted(grp_stats, key=lambda x: -x[1])[:15]

    def grp_table(rows):
        out = ""
        for g, p, n, k, y in rows:
            sl = slugify(g)
            out += f'<tr><td><a href="/bolum/{sl}.html">{g}</a></td><td>{n}</td><td>{fmt_sira(k)}</td><td><strong>%{p}</strong></td></tr>'
        return out

    # Plotly: devlet/vakıf + lisans/önlisans bar
    bar = [{"x": ["Devlet", "Vakıf", "Lisans", "Önlisans"],
            "y": [agg([r for r in valid if r.get("t") == "D"])[2], agg([r for r in valid if r.get("t") == "V"])[2], lp, op],
            "type": "bar", "marker": {"color": ["#1e3a8a", "#b45309", "#0891b2", "#7c3aed"]},
            "text": [f"%{agg([r for r in valid if r.get('t')=='D'])[2]}", f"%{agg([r for r in valid if r.get('t')=='V'])[2]}", f"%{lp}", f"%{op}"],
            "textposition": "outside"}]
    blayout = {"margin": {"l": 44, "r": 16, "t": 10, "b": 30}, "height": 280,
               "yaxis": {"title": {"text": "Doluluk %"}, "range": [0, 105], "gridcolor": "rgba(128,128,128,.15)"},
               "xaxis": {"gridcolor": "rgba(128,128,128,.15)"}, "paper_bgcolor": "rgba(0,0,0,0)",
               "plot_bgcolor": "rgba(0,0,0,0)", "font": {"family": "Segoe UI, Arial, sans-serif", "size": 12}}
    chart = ('<div class="chart-card"><h3>Doluluk Oranı Karşılaştırması</h3><div id="dchart" style="width:100%"></div></div>'
             '<script nonce="__NONCE__">Plotly.newPlot("dchart",' + json.dumps(bar) + "," + json.dumps(blayout)
             + ',{"displayModeBar":false,"responsive":true});</script>')

    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / Doluluk Analizi</div>
<div class="page-title"><h1>Kontenjan ve Doluluk Analizi 2025</h1><span class="sub">YÖK Atlas 2025 · {fmt_sira(len(valid))} program · Doluluk = yerleşen ÷ kontenjan</span></div>
<div class="spotlight">
  <div class="spot-card"><div class="sc-label">Toplam Kontenjan</div><div class="sc-exam">{fmt_sira(tk)}</div></div>
  <div class="spot-card"><div class="sc-label">Toplam Yerleşen</div><div class="sc-exam">{fmt_sira(ty)}</div></div>
  <div class="spot-card"><div class="sc-label">Genel Doluluk</div><div class="sc-exam">%{tp}</div></div>
  <div class="spot-card"><div class="sc-label">Boş Kontenjan</div><div class="sc-exam">{fmt_sira(tk-ty)}</div></div>
</div>
{chart}
<div class="section"><h2>Türe ve Düzeye Göre Doluluk</h2>
<div class="data-table-wrap"><table class="data-table">
<thead><tr><th>Kategori</th><th>Kontenjan</th><th>Yerleşen</th><th>Doluluk</th></tr></thead>
<tbody>{tur_rows}{duzey_rows}</tbody></table></div></div>

<div class="section"><h2>En Düşük Doluluklu Bölümler</h2>
<div class="section-sub">En az 30 programı olan bölüm grupları · doluluk artan sıra</div>
<div class="data-table-wrap"><table class="data-table">
<thead><tr><th>Bölüm</th><th>Program</th><th>Kontenjan</th><th>Doluluk</th></tr></thead>
<tbody>{grp_table(bos)}</tbody></table></div></div>

<div class="section"><h2>En Yüksek Doluluklu Bölümler</h2>
<div class="data-table-wrap"><table class="data-table">
<thead><tr><th>Bölüm</th><th>Program</th><th>Kontenjan</th><th>Doluluk</th></tr></thead>
<tbody>{grp_table(dolu)}</tbody></table></div></div>

<div class="notice"><b>Kaynak:</b> YÖK Atlas 2025. Doluluk, genel kontenjana yerleşen sayısının oranıdır; ek yerleştirme/dikey
geçiş hariçtir. Düşük doluluk talebin az olduğunu, yüksek doluluk programın dolduğunu gösterir.</div>
"""
    return base("doluluk.html", "Üniversite Kontenjan ve Doluluk Analizi 2025 | SınavVeri",
                "2025 üniversite kontenjan doluluk oranları: devlet/vakıf, lisans/önlisans karşılaştırması, en dolu ve en boş bölümler. YÖK Atlas verisi.",
                body, extra_head=PLOTLY_CDN)


# ───────────────────────── HUB SAYFALARI ─────────────────────────
def page_puan_hesaplama_hub():
    tools = [("yks-puan-hesaplama.html", "🎓", "YKS Puan Hesaplama", "TYT + AYT net ve puan"),
             ("lgs-puan-hesaplama.html", "🏫", "LGS Puan Hesaplama", "Ağırlıklı net ve puan"),
             ("kpss-puan-hesaplama.html", "🏛️", "KPSS Puan Hesaplama", "GY-GK net hesaplama"),
             ("dgs-puan-hesaplama.html", "📈", "DGS Puan Hesaplama", "Sayısal-Sözel net"),
             ("ales-puan-hesaplama.html", "📚", "ALES Puan Hesaplama", "Sayısal-Sözel net")]
    cards = "".join(f'<a class="tool-btn" href="/{h}"><span class="tb-icon">{i}</span><span class="tb-text"><b>{t}</b><span>{s}</span></span></a>' for h, i, t, s in tools)
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / Puan Hesaplama</div>
<div class="page-title"><h1>Puan Hesaplama Araçları</h1><span class="sub">Net ve puanını saniyeler içinde, ücretsiz hesapla</span></div>
<div class="tool-row">{cards}</div>
<div class="info-box" style="margin-top:20px"><h3>Net nasıl hesaplanır?</h3>
Her sınavda net = doğru − (yanlış ÷ k). YKS/KPSS/DGS/ALES'te <strong>4 yanlış</strong>, LGS'de <strong>3 yanlış</strong> 1 doğruyu götürür.
Araçlarımız net hesabını kesin verir; puan tahminleri standart puan sistemi nedeniyle yaklaşıktır.</div>
"""
    return base("puan-hesaplama.html", "Puan Hesaplama Araçları — YKS, LGS, KPSS, DGS, ALES | SınavVeri",
                "Ücretsiz puan ve net hesaplama araçları: YKS (TYT/AYT), LGS, KPSS, DGS ve ALES. Doğru-yanlış gir, netini anında öğren.",
                body)


def page_rehberler_hub():
    g = [("yks.html", "🎓", "YKS", "Üniversite giriş sınavı rehberi"),
         ("lgs.html", "🏫", "LGS", "Liselere geçiş sınavı rehberi"),
         ("kpss.html", "🏛️", "KPSS", "Kamu personel seçme sınavı"),
         ("dgs.html", "📈", "DGS", "Dikey geçiş sınavı"),
         ("ales.html", "📚", "ALES", "Akademik personel / lisansüstü")]
    cards = "".join(f'<a class="tool-btn" href="/{h}"><span class="tb-icon">{i}</span><span class="tb-text"><b>{t}</b><span>{s}</span></span></a>' for h, i, t, s in g)
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / Rehberler</div>
<div class="page-title"><h1>Sınav Rehberleri</h1><span class="sub">Her sınavın formatı, soru dağılımı ve puan mantığı</span></div>
<div class="tool-row">{cards}</div>
"""
    return base("rehberler.html", "Sınav Rehberleri — YKS, LGS, KPSS, DGS, ALES | SınavVeri",
                "YKS, LGS, KPSS, DGS ve ALES sınav rehberleri: format, soru dağılımı, puan hesaplama ve 2026 tarihleri.",
                body)


# ───────────────────────── DGS / ALES HESAPLAMA ─────────────────────────
def _two_section_calc(slug, exam, guide_slug, title, desc, s1name, s1count, s2name, s2count, intro):
    sub = [("s1", s1name, s1count), ("s2", s2name, s2count)]
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / <a href="/{guide_slug}">{exam}</a> / Puan Hesaplama</div>
<div class="page-title"><h1>{exam} Net Hesaplama</h1><span class="sub">{intro} · <b>4 yanlış = 1 doğru</b></span></div>
<div class="calc-wrap">
  <div class="calc-card">
    <h2>{exam} — Testler</h2>
    <div class="calc-hint">Doğru ve yanlış sayılarını gir; net otomatik hesaplanır.</div>
    <div class="calc-block" id="calc">{calc_subj_rows(sub)}</div>
    <div class="calc-actions"><button type="button" class="btn btn-primary" id="calcBtn">Hesapla</button><button type="button" class="btn btn-ghost" id="resetBtn">Temizle</button></div>
  </div>
  <div class="result-card">
    <h3>Sonuç</h3>
    <div class="res-net"><div class="rn-label">Toplam Net</div><div class="rn-value" id="rTotal">0,00</div></div>
    <ul class="res-list"><li><span>{s1name} Net</span><b id="rS1">0,00</b></li><li><span>{s2name} Net</span><b id="rS2">0,00</b></li></ul>
  </div>
</div>
<div class="notice"><b>Önemli:</b> Net hesabı <b>kesindir</b>. {exam} puanı ÖSYM'nin <b>standart puan</b> yöntemiyle, adayın puan türü
ağırlıklarına göre hesaplanır ve net→puan dönüşümü her sınavda değişir; kesin puan ÖSYM sonuç belgenizdedir.</div>
<div class="info-box"><h3>{exam} net nasıl hesaplanır?</h3>
Her test için: <strong>Net = Doğru − (Yanlış ÷ 4)</strong>. Ayrıntılı bilgi için <a href="/{guide_slug}">{exam} rehberi</a>.</div>
<script nonce="__NONCE__">
(function(){{
  var TR=function(n){{return n.toLocaleString('tr-TR',{{minimumFractionDigits:2,maximumFractionDigits:2}});}};
  function netOf(r){{var d=parseFloat(r.querySelector('.in-d').value)||0,y=parseFloat(r.querySelector('.in-y').value)||0,max=+r.getAttribute('data-max');
    d=Math.max(0,Math.min(d,max));y=Math.max(0,Math.min(y,max));if(d+y>max)y=Math.max(0,max-d);var n=d-(y/4);if(n<0)n=0;r.querySelector('[data-net]').textContent=TR(n);return n;}}
  function calc(){{var rows=document.querySelectorAll('#calc .subj-row');var s1=netOf(rows[0]),s2=netOf(rows[1]);
    document.getElementById('rS1').textContent=TR(s1);document.getElementById('rS2').textContent=TR(s2);document.getElementById('rTotal').textContent=TR(s1+s2);}}
  document.getElementById('calcBtn').addEventListener('click',calc);
  document.querySelectorAll('#calc input').forEach(function(i){{i.addEventListener('input',calc);}});
  document.getElementById('resetBtn').addEventListener('click',function(){{document.querySelectorAll('#calc input').forEach(function(i){{i.value='';}});
    document.querySelectorAll('[data-net]').forEach(function(n){{n.textContent='0,00';}});['rS1','rS2','rTotal'].forEach(function(id){{document.getElementById(id).textContent='0,00';}});}});
}})();
</script>
"""
    return base(slug, title, desc, body)


def page_dgs_calc():
    return _two_section_calc("dgs-puan-hesaplama.html", "DGS", "dgs.html",
        "DGS Net Hesaplama 2026 (Sayısal + Sözel) | SınavVeri",
        "2026 DGS net hesaplama: Sayısal ve Sözel testlerde doğru-yanlış gir, netini anında öğren. 4 yanlış 1 doğru.",
        "Sayısal", 60, "Sözel", 60, "120 soru · Sayısal (60) + Sözel (60)")


def page_ales_calc():
    return _two_section_calc("ales-puan-hesaplama.html", "ALES", "ales.html",
        "ALES Net Hesaplama 2026 (Sayısal + Sözel) | SınavVeri",
        "2026 ALES net hesaplama: Sayısal ve Sözel testlerde doğru-yanlış gir, netini anında öğren. 4 yanlış 1 doğru.",
        "Sayısal", 50, "Sözel", 50, "100 soru · Sayısal (50) + Sözel (50)")


# ───────────────────────── ÇALIŞTIR ─────────────────────────
def main():
    print("SınavVeri.com inşa ediliyor...")
    slugs = []  # sitemap için

    def W(slug, html):
        write(slug, html)
        slugs.append(slug)

    # Sabit sayfalar
    W("index.html", page_index())
    W("takvim.html", page_takvim())
    W("taban-puanlari.html", page_taban_hub())
    W("universite-taban-puanlari.html", page_taban_index())
    # ÖSYM resmî taban puanları (TUS/DUS/DGS/KPSS) — istemci JSON üret + sayfalar
    print("  ÖSYM resmî veri (TUS/DUS/DGS/KPSS) işleniyor...")
    write_osym_veri()
    for slug, fn in [("tus-taban-puanlari.html", page_tus), ("dus-taban-puanlari.html", page_dus),
                     ("dgs-taban-puanlari.html", page_dgs_taban), ("kpss-atama-taban-puanlari.html", page_kpss_atama)]:
        html = fn()
        if html:
            W(slug, html)
    W("tercih-robotu.html", page_tercih_robotu())
    W("puan-hesaplama.html", page_puan_hesaplama_hub())
    W("rehberler.html", page_rehberler_hub())
    W("yks.html", page_yks())
    W("lgs.html", page_lgs())
    W("kpss.html", page_kpss())
    W("dgs.html", page_dgs())
    W("ales.html", page_ales())
    W("yks-puan-hesaplama.html", page_yks_calc())
    W("lgs-puan-hesaplama.html", page_lgs_calc())
    W("kpss-puan-hesaplama.html", page_kpss_calc())
    W("dgs-puan-hesaplama.html", page_dgs_calc())
    W("ales-puan-hesaplama.html", page_ales_calc())
    write("404.html", page_error("404", "Aradığınız sayfa bulunamadı."))
    write("5xx.html", page_error("Hata", "Geçici bir sorun oluştu. Lütfen daha sonra tekrar deneyin."))

    # Veri tabanlı sayfalar
    programs = load_programs()
    print(f"  {len(programs)} program yüklendi (YÖK Atlas 2025)")
    write_veri(programs)
    W("doluluk.html", page_doluluk(programs))
    print("  Bölüm sayfaları üretiliyor...")
    g_by_slug = gen_bolum_pages(programs)
    for s in g_by_slug:
        slugs.append(f"bolum/{s}.html")
    W("bolumler.html", page_bolumler(g_by_slug, programs))
    print(f"  → {len(g_by_slug)} bölüm sayfası")
    print("  Üniversite sayfaları üretiliyor...")
    u_by_slug = gen_universite_pages(programs)
    for s in u_by_slug:
        slugs.append(f"universite/{s}.html")
    W("universiteler.html", page_universiteler(u_by_slug, programs))
    print(f"  → {len(u_by_slug)} üniversite sayfası")

    # LGS lise taban puanları
    lgs = load_lgs()
    if lgs:
        print(f"  {len(lgs)} lise yüklendi (LGS 2025)")
        write_lgs_veri(lgs)
        il_slugs = gen_lise_il_pages(lgs)
        for s in il_slugs:
            slugs.append(f"lise/{s}.html")
        W("lise-taban-puanlari.html", page_lise_taban_index(lgs, il_slugs))
        print(f"  → {len(il_slugs)} il lise sayfası")
    else:
        print("  ! LGS verisi yok (pipeline/fetch_lgs.py çalıştırılmalı)")

    write_support(slugs)
    print(f"Tamamlandı. Toplam {len(slugs)} sayfa sitemap'te.")


if __name__ == "__main__":
    main()
