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
<script nonce="__NONCE__">
(function(){{
  function num(s){{s=(s||'').replace(/[^0-9,.\\-]/g,'').replace(/\\./g,'').replace(',','.');return s===''||s==='-'?NaN:parseFloat(s);}}
  function sortBody(tb,idx,dir){{
    var body=tb.querySelector('tbody'); if(!body)return;
    var rows=Array.prototype.slice.call(body.querySelectorAll(':scope>tr'));
    rows.sort(function(a,b){{
      var x=a.children[idx],y=b.children[idx]; if(!x||!y)return 0;
      var xt=x.textContent.trim(),yt=y.textContent.trim(),xn=num(xt),yn=num(yt),c;
      if(!isNaN(xn)&&!isNaN(yn))c=xn-yn;
      else if(isNaN(xn)&&isNaN(yn))c=xt.localeCompare(yt,'tr');
      else c=isNaN(xn)?1:-1;
      return c*dir;
    }});
    rows.forEach(function(r){{body.appendChild(r);}});
  }}
  document.querySelectorAll('table.data-table:not([data-live])').forEach(function(tb){{
    var ths=tb.querySelectorAll('thead th'); if(!ths.length)return;
    ths.forEach(function(th,i){{
      if(th.hasAttribute('data-nosort'))return;
      th.style.cursor='pointer'; th.title='Sıralamak için tıklayın'; th.dataset.dir='0';
      th.addEventListener('click',function(){{
        var dir=th.dataset.dir==='1'?-1:1;
        ths.forEach(function(o){{o.dataset.dir='0';var a=o.querySelector('.s-arrow');if(a)a.remove();}});
        th.dataset.dir=dir>0?'1':'-1';
        sortBody(tb,i,dir);
        var ar=document.createElement('span');ar.className='s-arrow';ar.textContent=dir>0?' ▲':' ▼';th.appendChild(ar);
      }});
    }});
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
TUR_FULL = {"D": "Devlet", "V": "Vakıf", "K": "KKTC", "DK": "Devlet (KKTC Kampüs)", "DU": "Devlet (Ücretli)", "Y": "Diğer", "?": "—"}


def load_programs():
    progs = json.loads((ROOT / "data" / "programs_raw.json").read_text(encoding="utf-8"))
    # Türk devlet üniversitelerinin KKTC kampüsleri (ODTÜ/İTÜ/ASBÜ Kıbrıs) normal ücretsiz
    # devlet programı DEĞİL → ayrı tür "DK". (YÖK Atlas universiteTuru=DEVLET döner; gösterim/filtre için ayrıştırılır.)
    for r in progs:
        il = (r.get("il") or "").replace("İ", "i").replace("I", "i").replace("ı", "i").lower()
        if r.get("t") == "D" and il in ("kibris", "kktc"):
            r["t"] = "DK"
            # Kıbrıs kampüsünü AYRI üniversite kartı yap: "… (ANKARA)" → "… (KIBRIS)"
            u = (r.get("u") or "").strip()
            if u.endswith(")") and "(" in u:
                u = u[:u.rfind("(")].strip()  # sondaki (ŞEHİR) ekini at
            r["u"] = u + " (KIBRIS)"
        elif r.get("t") == "D" and r.get("bs") == "Ücretli":
            r["t"] = "DU"  # Devlet üniv. ücretli program (ör. İTÜ UOLP) — ad zaten "(Ücretli)" içerir
    return progs


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


def page_tus_rehber():
    return guide("tus.html", "TUS", "Tıpta Uzmanlık Eğitimi Giriş Sınavı", "🩺", "",
        "TUS, tıp fakültesi mezunlarının uzmanlık eğitimi (asistanlık) için girdiği merkezi sınavdır. ÖSYM tarafından yılda iki dönem (ilkbahar/sonbahar) yapılır.",
        [
            ("TUS Nedir?", [
                "Tıpta Uzmanlık Eğitimi Giriş Sınavı (TUS), tıp doktorlarının kardiyoloji, genel cerrahi, radyoloji gibi uzmanlık dallarında eğitim almak üzere yerleştirilmesinde kullanılan ÖSYM sınavıdır. Yılda 2 dönem (1. ve 2. dönem) düzenlenir.",
                "Sınav iki testten oluşur: <strong>Temel Tıp Bilimleri Testi (TTBT)</strong> ve <strong>Klinik Tıp Bilimleri Testi (KTBT)</strong>.",
            ]),
            ("Soru Dağılımı (2023'ten itibaren 200 soru)", [
                "Eylül 2023 itibarıyla toplam soru sayısı 240'tan <strong>200'e</strong> düşürülmüştür:",
                "<strong>Temel Tıp Bilimleri Testi — 100 soru:</strong>",
                ("ul", ["Anatomi, Fizyoloji, Biyokimya", "Mikrobiyoloji, Patoloji, Farmakoloji"]),
                "<strong>Klinik Tıp Bilimleri Testi — 100 soru:</strong>",
                ("ul", ["Dahiliye (İç Hastalıkları), Pediatri (Çocuk Sağlığı)", "Genel Cerrahi, Kadın Hastalıkları ve Doğum", "Küçük stajlar (KBB, Göz, Psikiyatri, Nöroloji vb.)"]),
            ]),
            ("Puan Mantığı", [
                "Her test için <strong>Net = Doğru − (Yanlış ÷ 4)</strong> uygulanır (4 yanlış 1 doğruyu götürür).",
                "Ham puanlar, her test için ortalaması <strong>50</strong>, standart sapması <strong>10</strong> olan <strong>standart puanlara</strong> dönüştürülür. Bu standart puanlardan ağırlık katsayılarıyla <strong>Ağırlıklı Temel (Ağırlıklı T)</strong>, <strong>Ağırlıklı Klinik (Ağırlıklı K)</strong> ve <strong>Ağırlıklı (Ağırlıklı A)</strong> puanları üretilir; her uzmanlık dalı için kullanılan puan türü ÖSYM kılavuzunda belirtilir.",
                "Yerleştirme, adayın TUS puanı ve tercihlerine göre ÖSYM tarafından yapılır. Kurum ve dal bazında taban puanları için <a href='/tus-taban-puanlari.html'>TUS taban puanları</a> ve <a href='/tus-tercih-robotu.html'>TUS tercih robotu</a>.",
            ]),
            ("2026 TUS Tarihleri (ÖSYM resmî kılavuzu)", [
                "<strong>1. Dönem:</strong>",
                ("ul", ["Başvuru: 28 Ocak – 5 Şubat 2026 (geç başvuru: 12 Şubat)", "Sınav: 15 Mart 2026"]),
                "<strong>2. Dönem:</strong>",
                ("ul", ["Başvuru: 8 – 16 Temmuz 2026 (geç başvuru: 24 Temmuz)", "Sınav: 23 Ağustos 2026"]),
            ]),
        ], has_calc=False)


def page_dus_rehber():
    return guide("dus.html", "DUS", "Diş Hekimliği Uzmanlık Eğitimi Giriş Sınavı", "🦷", "",
        "DUS, diş hekimliği fakültesi mezunlarının uzmanlık eğitimi için girdiği merkezi sınavdır. ÖSYM tarafından düzenlenir.",
        [
            ("DUS Nedir?", [
                "Diş Hekimliği Uzmanlık Eğitimi Giriş Sınavı (DUS), diş hekimlerinin ortodonti, ağız-diş-çene cerrahisi, protetik diş tedavisi gibi dallarda uzmanlık eğitimi almak için girdiği ÖSYM sınavıdır.",
                "Sınav iki testten oluşur: <strong>Diş Hekimliği Temel Bilimler Testi</strong> ve <strong>Diş Hekimliği Klinik Bilimler Testi</strong>.",
            ]),
            ("Soru Dağılımı (tek oturum · 150 dk · 120 soru)", [
                "DUS tek oturumda (saat 10.15, 150 dakika) yapılır ve iki testten oluşur:",
                "<strong>Diş Hekimliği Temel Bilimler Testi — 40 soru:</strong>",
                ("ul", ["Anatomi, Fizyoloji, Biyokimya, Mikrobiyoloji, Patoloji, Farmakoloji (temel tıp + diş)"]),
                "<strong>Diş Hekimliği Klinik Bilimler Testi — 80 soru:</strong>",
                ("ul", ["Restoratif diş tedavisi, Endodonti, Protetik diş tedavisi", "Ağız-diş-çene cerrahisi/radyolojisi, Ortodonti, Periodontoloji, Pedodonti"]),
            ]),
            ("Puan Mantığı", [
                "Her test için <strong>Net = Doğru − (Yanlış ÷ 4)</strong> uygulanır.",
                "Ham puanlar ortalaması 50, standart sapması 10 olan standart puanlara dönüştürülür; DUS puanı Temel ve Klinik standart puanların ağırlıklı birleşimidir.",
                "Kurum ve dal bazında taban puanları için <a href='/dus-taban-puanlari.html'>DUS taban puanları</a> ve <a href='/dus-tercih-robotu.html'>DUS tercih robotu</a>.",
            ]),
            ("2026 DUS Tarihleri (ÖSYM resmî kılavuzu)", [
                "<strong>1. Dönem:</strong>",
                ("ul", ["Başvuru: 10 – 17 Mart 2026", "Sınav: 26 Nisan 2026"]),
                "<strong>2. Dönem:</strong>",
                ("ul", ["Başvuru: 16 – 24 Eylül 2026", "Sınav: 1 Kasım 2026"]),
            ]),
        ], has_calc=False)


def page_yds_rehber():
    return guide("yds.html", "YDS", "Yabancı Dil Bilgisi Seviye Tespit Sınavı", "🌐", "",
        "YDS, akademik ve mesleki amaçlarla yabancı dil bilgisini ölçen ÖSYM sınavıdır; doktora başvurusu, akademik kadrolar ve bazı kamu görevlerinde kullanılır.",
        [
            ("YDS Nedir?", [
                "Yabancı Dil Bilgisi Seviye Tespit Sınavı (YDS), ÖSYM tarafından İngilizce, Almanca, Fransızca, Arapça, Rusça gibi dillerde yapılan merkezi yabancı dil sınavıdır. Sonuç açıklandığı tarihten itibaren <strong>5 yıl</strong> geçerlidir.",
            ]),
            ("Format ve Soru Dağılımı", [
                "Tek oturumda, tek kitapçıkla yapılır ve <strong>80 çoktan seçmeli soru</strong> içerir. Sorular; kelime bilgisi, dil bilgisi, cloze test, cümle tamamlama, çeviri (TR↔YD), paragraf ve okuma-anlama gibi bölümlerden oluşur.",
            ]),
            ("Puan Mantığı", [
                "Her doğru cevap <strong>1,25 puan</strong>; toplam 100 puan üzerinden değerlendirilir. <strong>Yanlış cevaplar doğruları GÖTÜRMEZ</strong> (net = doğru sayısı).",
                "Puan ayrıca harf notu/CEFR seviyesine karşılık gelir (ör. 90+ A, 80+ B …).",
            ]),
            ("Dönemler", [
                "Yılda iki ana dönem (İlkbahar/Sonbahar) yapılır; ayrıca bilgisayar tabanlı <strong>e-YDS</strong> ile yıl içinde ek dönemler açılır. Kesin tarihler ÖSYM sınav takviminde duyurulur.",
            ]),
        ], has_calc=False)


def page_yokdil_rehber():
    return guide("yokdil.html", "YÖKDİL", "Yükseköğretim Kurumları Yabancı Dil Sınavı", "🎓", "",
        "YÖKDİL, yükseköğretimde (lisansüstü ve akademik) yabancı dil şartını karşılamak için alan bazlı yapılan ÖSYM sınavıdır.",
        [
            ("YÖKDİL Nedir?", [
                "Yükseköğretim Kurumları Yabancı Dil Sınavı (YÖKDİL), YDS ile aynı formatta ancak adayın <strong>alanına göre</strong> hazırlanan akademik yabancı dil sınavıdır. ÖSYM tarafından yılda iki kez yapılır.",
            ]),
            ("Alanlar ve Format", [
                "Üç ayrı alanda uygulanır:",
                ("ul", ["Sağlık Bilimleri", "Sosyal Bilimler", "Fen Bilimleri"]),
                "Tek oturum, <strong>80 soru</strong>; soru tipleri ve süre YDS ile aynıdır. Metinler adayın alanından seçilir.",
            ]),
            ("Puan Mantığı", [
                "Her doğru <strong>1,25 puan</strong>, 100 üzerinden; <strong>yanlış doğruyu götürmez</strong>. Geçerlilik ve kullanım YDS'ye benzer (lisansüstü başvuru, akademik kadrolar).",
            ]),
        ], has_calc=False)


def page_msu_rehber():
    return guide("msu.html", "MSÜ", "Millî Savunma Üniversitesi Askerî Öğrenci Aday Belirleme Sınavı", "🎖️", "",
        "MSÜ, Harp Okulları ve Astsubay Meslek Yüksekokullarına askerî öğrenci olmak isteyen adayların girdiği, ÖSYM tarafından yapılan ön eleme sınavıdır.",
        [
            ("MSÜ Nedir?", [
                "Millî Savunma Üniversitesi Askerî Öğrenci Aday Belirleme Sınavı (MSÜ), ÖSYM tarafından 81 ilde uygulanır. Sınavda yeterli puanı alan adaylar, fizikî yeterlilik ve mülakat gibi <strong>seçim aşamalarına</strong> çağrılır.",
            ]),
            ("Soru Dağılımı (120 soru · 165 dk)", [
                ("ul", ["Türkçe — 40 soru", "Sosyal Bilimler — 20 soru", "Temel Matematik — 40 soru", "Fen Bilimleri — 20 soru"]),
                "İçerik TYT ile benzerdir.",
            ]),
            ("Puan Mantığı", [
                "Net = Doğru − (Yanlış ÷ 4). Ham puanlar standart puana dönüştürülür ve farklı puan türlerinde ağırlıklı olarak hesaplanır.",
            ]),
            ("2026 MSÜ", [
                ("ul", ["Sınav: 1 Mart 2026 (ÖSYM)"]),
            ]),
        ], has_calc=False)


def page_ydus_rehber():
    return guide("ydus.html", "YDUS", "Tıpta Yan Dal Uzmanlık Eğitimi Giriş Sınavı", "🩺", "",
        "YDUS, ana dal uzmanlığını tamamlamış hekimlerin yan dal uzmanlık eğitimi (ör. iç hastalıkları → kardiyoloji) için girdiği ÖSYM sınavıdır.",
        [
            ("YDUS Nedir?", [
                "Tıpta Yan Dal Uzmanlık Eğitimi Giriş Sınavı (YDUS), uzman hekimlerin yan dal kontenjanlarına yerleşmek için girdiği sınavdır. Her aday yalnızca kendi <strong>ana dalının</strong> testine girer.",
            ]),
            ("Format ve Puan", [
                "İlgili ana dala göre ayrı düzenlenen tek bir testten oluşur; sorular adayın ana dal alanındandır. Net = Doğru − (Yanlış ÷ 4); ham puan standart puana dönüştürülür ve yerleştirme bu puanla yapılır.",
                "Her ana dalın soru sayısı ve yan dal kontenjanları ÖSYM kılavuzunda belirtilir.",
            ]),
        ], has_calc=False)


def page_sts_rehber():
    return guide("sts.html", "STS", "Seviye Tespit Sınavı (Yurt Dışı Diploma Denkliği)", "📋", "",
        "STS, yurt dışında tıp veya diş hekimliği eğitimi alıp Türkiye'de mesleğini icra etmek isteyenlerin diploma denkliği için girdiği ÖSYM sınavıdır.",
        [
            ("STS Nedir?", [
                "Seviye Tespit Sınavı (STS), YÖK'ün diploma denklik sürecinde uygulanır. İki ayrı sınav vardır: <strong>STS Tıp Doktorluğu</strong> ve <strong>STS Diş Hekimliği</strong>.",
            ]),
            ("Format ve Başarı", [
                "Çoktan seçmeli olup temel ve klinik tıp/diş hekimliği bilgisini ölçer. Denklik için ÖSYM/YÖK tarafından belirlenen <strong>baraj puanının</strong> (genellikle 100 üzerinden 50) aşılması gerekir.",
            ]),
            ("2026 STS", [
                ("ul", ["STS Tıp Doktorluğu 1. Dönem: 15 Mart 2026 (TUS 1. dönem ile aynı tarih)"]),
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
        if p.startswith(("tus-taban/", "dus-taban/", "dgs-taban/", "kpss-taban/")):
            return "monthly", "0.7"
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
  var TUR={D:'Devlet',V:'Vakıf',K:'KKTC',DK:'Devlet (KKTC Kampüs)',DU:'Devlet (Ücretli)',Y:'Diğer','?':'—'};
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
  var sortI=null,sortD=1;
  var SCOLS=[[IDX.b,0],[IDX.il,0],[IDX.t,0],[IDX.kont,1],[IDX.tp,1],[IDX.sira,1],['dol',1]];
  function sval(r,f){if(f==='dol'){var k=r[IDX.kont],y=r[IDX.yer];return (k&&y!=null)?y/k:null;}return r[f];}
  function applySort(rows){
    if(sortI==null||sortI>=SCOLS.length)return rows;
    var c=SCOLS[sortI],f=c[0],num=c[1];
    rows.sort(function(a,b){var x=sval(a,f),y=sval(b,f);
      if(num){x=(x==null?null:Number(x));y=(y==null?null:Number(y));if(x==null&&y==null)return 0;if(x==null)return 1;if(y==null)return -1;return (x-y)*sortD;}
      return String(x==null?'':x).localeCompare(String(y==null?'':y),'tr')*sortD;});
    return rows;
  }
  function render(reset){
    if(reset!==false)shown=0;
    var rows=applySort(filtered());
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
  (function(){var ths=document.querySelectorAll('.data-table thead th');ths.forEach(function(th,i){
    th.style.cursor='pointer';th.title='Sıralamak için tıklayın';
    th.addEventListener('click',function(){sortD=(sortI===i)?-sortD:1;sortI=i;
      ths.forEach(function(o){var a=o.querySelector('.s-arrow');if(a)a.remove();});
      var ar=document.createElement('span');ar.className='s-arrow';ar.textContent=sortD>0?' ▲':' ▼';th.appendChild(ar);render(true);});});})();
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
      <option value="">Tüm türler</option><option value="D">Devlet</option><option value="V">Vakıf</option><option value="K">KKTC</option><option value="DK">Devlet (KKTC Kampüs)</option><option value="DU">Devlet (Ücretli)</option>
    </select>
    <label style="display:flex;align-items:center;gap:6px;font-size:13px;color:var(--fg-muted)"><input type="checkbox" id="fBurs"> Sadece burslu</label>
  </div>
  <div id="status" style="margin-top:12px;font-size:13px;color:var(--accent);font-weight:700">Yükleniyor…</div>
</div>

<div class="data-table-wrap">
<table class="data-table" data-live="1">
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
  var TUR={D:'Devlet',V:'Vakıf',K:'KKTC',DK:'Devlet (KKTC Kampüs)',DU:'Devlet (Ücretli)',Y:'Diğer','?':'—'};
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
  var lastReach=[],lastSira=0,sortI=null,sortD=1;
  var SCOLS=[[IDX.b,0],[IDX.il,0],[IDX.t,0],[IDX.tp,1],[IDX.sira,1]];
  function sortReach(){
    if(sortI==null||sortI>=SCOLS.length){lastReach.sort(function(a,b){return a[IDX.sira]-b[IDX.sira];});return;}
    var f=SCOLS[sortI][0],num=SCOLS[sortI][1];
    lastReach.sort(function(a,b){var x=a[f],y=b[f];
      if(num){x=(x==null?null:Number(x));y=(y==null?null:Number(y));if(x==null&&y==null)return 0;if(x==null)return 1;if(y==null)return -1;return (x-y)*sortD;}
      return String(x==null?'':x).localeCompare(String(y==null?'':y),'tr')*sortD;});
  }
  function draw(){
    var tb=el('rbody'); tb.innerHTML='';
    lastReach.slice(0,200).forEach(function(r){
      var margin=r[IDX.sira]-lastSira;
      var safe = margin>lastSira*0.25 ? '<span class="tag tag-lgs">Rahat</span>' : (margin>lastSira*0.05 ? '<span class="tag tag-kpss">Olası</span>' : '<span class="tag tag-other">Sınırda</span>');
      var tr=document.createElement('tr');
      tr.innerHTML='<td><strong>'+(r[IDX.b]||'')+'</strong><br><small>'+(r[IDX.u]||'')+'</small></td>'+
        '<td>'+(r[IDX.il]||'—')+'</td>'+'<td>'+(TUR[r[IDX.t]]||'—')+'</td>'+
        '<td><strong>'+pf(r[IDX.tp])+'</strong></td>'+'<td>'+nf(r[IDX.sira])+'</td>'+'<td>'+safe+'</td>';
      tb.appendChild(tr);
    });
    el('rhint').style.display = lastReach.length>200 ? 'block':'none';
    el('rhint').textContent='İlk 200 program gösteriliyor. Sütun başlığına tıklayarak sıralayın; il/tür ile daraltın.';
  }
  function run(){
    var pt=el('rPt').value;
    load(pt,function(){
      var sira=parseInt((el('rSira').value||'').replace(/\D/g,''),10);
      if(!sira||sira<1){el('rstatus').textContent='Lütfen geçerli bir başarı sıranızı girin.';el('rbody').innerHTML='';return;}
      var il=el('rIl').value, tur=el('rTur').value;
      lastSira=sira;
      lastReach=data.filter(function(r){
        if(r[IDX.sira]==null)return false;
        if(il&&r[IDX.il]!==il)return false;
        if(tur&&r[IDX.t]!==tur)return false;
        return r[IDX.sira]>=sira;
      });
      sortReach();
      el('rstatus').innerHTML='<b>'+lastReach.length.toLocaleString('tr-TR')+'</b> programa yerleşebilirsin (sıran: '+sira.toLocaleString('tr-TR')+')';
      draw();
    });
  }
  el('rBtn').addEventListener('click',run);
  el('rSira').addEventListener('keydown',function(e){if(e.key==='Enter')run();});
  (function(){var ths=document.querySelectorAll('.data-table thead th');ths.forEach(function(th,i){
    th.style.cursor='pointer';th.title='Sıralamak için tıklayın';
    th.addEventListener('click',function(){if(!lastReach.length)return;sortD=(sortI===i)?-sortD:1;sortI=i;
      ths.forEach(function(o){var a=o.querySelector('.s-arrow');if(a)a.remove();});
      var ar=document.createElement('span');ar.className='s-arrow';ar.textContent=sortD>0?' ▲':' ▼';th.appendChild(ar);sortReach();draw();});});})();
})();
</script>"""


def page_tercih_robotu():
    body = """
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / Tercih Robotu</div>
<div class="page-title"><h1>2026 YKS Tercih Robotu</h1><span class="sub">Başarı sıranı gir, yerleşebileceğin programları gör · 2025 YÖK Atlas yerleştirme verisine göre</span></div>
""" + robot_nav("tercih-robotu.html") + """

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
      <select id="rTur" class="btn btn-ghost" style="text-align:left;width:100%;margin-top:4px"><option value="">Hepsi</option><option value="D">Devlet</option><option value="V">Vakıf</option><option value="K">KKTC</option><option value="DK">Devlet (KKTC Kampüs)</option><option value="DU">Devlet (Ücretli)</option></select></div>
    <button type="button" class="btn btn-primary" id="rBtn">Programları Göster</button>
  </div>
  <div id="rstatus" style="margin-top:14px;font-size:14px;color:var(--accent);font-weight:700"></div>
</div>

<div class="data-table-wrap">
<table class="data-table" data-live="1">
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
    return base("tercih-robotu.html", "2026 YKS Tercih Robotu — Sıralamana Göre Bölüm Bul | SınavVeri",
                "2026 YKS tercih robotu: başarı sıranı gir, 2025 YÖK Atlas yerleştirme verisine göre yerleşebileceğin üniversite programlarını anında gör. Ücretsiz.",
                body)


# ───────────────────────── BÖLÜM (program grubu) SAYFALARI ─────────────────────────
PUAN_ROBOT_JS = r"""<script nonce="__NONCE__">
(function(){
  var CFG=__CFG__;
  var data=[];
  function el(id){return document.getElementById(id);}
  var pf=function(n){return n==null?'—':Number(n).toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2});};
  el('rstatus').textContent='Veriler yükleniyor…';
  fetch(CFG.file).then(function(r){return r.json();}).then(function(j){data=j;initFilters();el('rstatus').textContent='';})
    .catch(function(){el('rstatus').textContent='Veri yüklenemedi.';});
  function initFilters(){
    CFG.filters.forEach(function(f,n){
      var set={};data.forEach(function(r){if(r[f[0]]!=null&&r[f[0]]!=='')set[r[f[0]]]=1;});
      var vals=Object.keys(set).sort(function(a,b){return a.localeCompare(b,'tr');});
      var sel=el('rf'+n);if(!sel)return;
      vals.forEach(function(v){var o=document.createElement('option');o.value=v;o.textContent=v;sel.appendChild(o);});
    });
  }
  var lastReach=[],userP=0,sortI=null,sortD=1;
  var SCOLS=[[CFG.nb,0]];CFG.show.forEach(function(c){SCOLS.push([c[0],0]);});SCOLS.push([CFG.taban,1]);
  function sortReach(){
    if(sortI==null||sortI>=SCOLS.length){lastReach.sort(function(a,b){return (b[CFG.taban]||0)-(a[CFG.taban]||0);});return;}
    var f=SCOLS[sortI][0],num=SCOLS[sortI][1];
    lastReach.sort(function(a,b){var x=a[f],y=b[f];
      if(num){x=(x==null?null:Number(x));y=(y==null?null:Number(y));if(x==null&&y==null)return 0;if(x==null)return 1;if(y==null)return -1;return (x-y)*sortD;}
      return String(x==null?'':x).localeCompare(String(y==null?'':y),'tr')*sortD;});
  }
  function draw(){
    var tb=el('rbody');tb.innerHTML='';
    lastReach.slice(0,200).forEach(function(r){
      var m=userP-r[CFG.taban];
      var safe=m>=CFG.t1?'<span class="tag tag-lgs">Rahat</span>':(m>=CFG.t2?'<span class="tag tag-kpss">Olası</span>':'<span class="tag tag-other">Sınırda</span>');
      var name='<td><strong>'+(r[CFG.nb]||'')+'</strong>'+(CFG.ns!=null?'<br><small>'+(r[CFG.ns]||'')+'</small>':'')+'</td>';
      var show='';CFG.show.forEach(function(c){show+='<td>'+(r[c[0]]==null||r[c[0]]===''?'—':r[c[0]])+'</td>';});
      var tr=document.createElement('tr');
      tr.innerHTML=name+show+'<td><strong>'+pf(r[CFG.taban])+'</strong></td><td>'+safe+'</td>';
      tb.appendChild(tr);
    });
    el('rhint').style.display=lastReach.length>200?'block':'none';
    el('rhint').textContent='İlk 200 sonuç gösteriliyor. Daha hassas için filtre/sıralama kullanın.';
  }
  function run(){
    var p=parseFloat((el('rPuan').value||'').replace(',','.').replace(/[^0-9.]/g,''));
    if(isNaN(p)||p<=0){el('rstatus').textContent='Lütfen geçerli bir puan girin.';el('rbody').innerHTML='';return;}
    userP=p;
    lastReach=data.filter(function(r){
      for(var k=0;k<CFG.filters.length;k++){var s=el('rf'+k);if(s&&s.value&&String(r[CFG.filters[k][0]])!==s.value)return false;}
      var t=r[CFG.taban];return t!=null&&t<=p;
    });
    sortReach();
    el('rstatus').innerHTML='<b>'+lastReach.length.toLocaleString('tr-TR')+'</b> '+CFG.noun+' yerleşebilirsin (puanın: '+pf(p)+')';
    draw();
  }
  el('rBtn').addEventListener('click',run);
  el('rPuan').addEventListener('keydown',function(e){if(e.key==='Enter')run();});
  (function(){
    var ths=document.querySelectorAll('.data-table thead th');
    ths.forEach(function(th,i){
      th.style.cursor='pointer'; th.title='Sıralamak için tıklayın';
      th.addEventListener('click',function(){
        if(!lastReach.length)return;
        sortD=(sortI===i)?-sortD:1; sortI=i;
        ths.forEach(function(o){var a=o.querySelector('.s-arrow');if(a)a.remove();});
        var ar=document.createElement('span');ar.className='s-arrow';ar.textContent=sortD>0?' ▲':' ▼';th.appendChild(ar);
        sortReach();draw();
      });
    });
  })();
})();
</script>"""


def robot_nav(active):
    items = [("tercih-robotu.html", "YKS"), ("dgs-tercih-robotu.html", "DGS"),
             ("tus-tercih-robotu.html", "TUS"), ("dus-tercih-robotu.html", "DUS"),
             ("kpss-tercih-robotu.html", "KPSS"), ("lgs-tercih-robotu.html", "LGS")]
    out = []
    for slug, lbl in items:
        if slug == active:
            out.append(f'<span class="btn btn-primary" style="pointer-events:none">{lbl} Robotu</span>')
        else:
            out.append(f'<a class="btn btn-ghost" href="/{slug}">{lbl} Robotu</a>')
    return '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px">' + "".join(out) + "</div>"


def puan_robot_page(slug, title, desc, h1, sub, veri_file, nb, ns, show, taban, filters,
                    noun, t1, t2, intro, kaynak, puan_label, ph):
    """Generic puan-bazlı tercih robotu. nb/ns: ad sütun idx (bold/alt). show: [(idx,label)] ek sütun.
    taban: taban puan idx. filters: [(idx,label)]. t1/t2: 'Rahat'/'Olası' eşik (puan farkı)."""
    fhtml = ""
    for n, (idx, label) in enumerate(filters):
        fhtml += (f'<div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">{label}</label>'
                  f'<select id="rf{n}" class="btn btn-ghost" style="text-align:left;width:100%;margin-top:4px">'
                  f'<option value="">Tümü</option></select></div>')
    thead = "<th>" + ("Program" if ns is not None else "Ad") + "</th>" + "".join(f"<th>{l}</th>" for _, l in show) + "<th>Taban</th><th>Şans</th>"
    cfg = {"file": veri_file, "nb": nb, "ns": ns, "show": [[i, l] for i, l in show],
           "taban": taban, "filters": [[i, l] for i, l in filters], "noun": noun, "t1": t1, "t2": t2}
    js = PUAN_ROBOT_JS.replace("__CFG__", json.dumps(cfg, ensure_ascii=False))
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / <a href="/tercih-robotu.html">Tercih Robotu</a> / {h1}</div>
<div class="page-title"><h1>{h1}</h1><span class="sub">{sub}</span></div>
{robot_nav(slug)}
<div class="info-box">{intro}</div>
<div class="calc-card" style="margin-bottom:18px">
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;align-items:end">
    <div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">{puan_label}</label>
      <input id="rPuan" type="text" inputmode="decimal" placeholder="{ph}" style="width:100%;margin-top:4px;padding:9px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:14px"></div>
    {fhtml}
    <button type="button" class="btn btn-primary" id="rBtn">Yerleşebileceklerimi Göster</button>
  </div>
  <div id="rstatus" style="margin-top:14px;font-size:14px;color:var(--accent);font-weight:700"></div>
</div>
<div class="data-table-wrap">
<table class="data-table" data-live="1"><thead><tr>{thead}</tr></thead><tbody id="rbody"></tbody></table>
</div>
<div id="rhint" style="display:none;font-size:12px;color:var(--fg-faded);margin-top:10px;text-align:center"></div>
<div class="notice"><b>Nasıl çalışır?</b> Puanın bir programın/kadronun taban puanından <b>yüksek veya eşitse</b> oraya yerleşebilirsin.
"Şans" payı güvenliği gösterir: <b>Rahat</b> (geniş pay), <b>Olası</b>, <b>Sınırda</b>. Bu bir tahmindir; gelecek yıl taban puanları
kontenjan ve tercih yoğunluğuna göre değişir. <b>Kaynak:</b> {kaynak} Resmî tercih için <a href="https://www.osym.gov.tr" target="_blank" rel="noopener">ÖSYM</a> esastır.</div>
{js}
"""
    return base(slug, title, desc, body)


def page_dgs_robot():
    if not (ROOT / "veri" / "dgs.json").exists():
        return None
    return puan_robot_page(
        "dgs-tercih-robotu.html", "2026 DGS Tercih Robotu — Puanına Göre Bölüm Bul | SınavVeri",
        "2026 DGS tercih robotu: DGS puanını gir, 2025 ÖSYM yerleştirme verisine göre yerleşebileceğin lisans programlarını anında gör. Ücretsiz.",
        "2026 DGS Tercih Robotu", "Dikey Geçiş · DGS puanını gir, yerleşebileceğin programları gör · 2025 ÖSYM verisine göre",
        "/veri/dgs.json", 1, 0, [], 3, [],
        "programa", 15, 4,
        "DGS puanını girin; o puanla yerleşebileceğin (taban puanı ≤ senin puanın) tüm lisans programlarını en yüksek tabandan başlayarak listeler. "
        "DGS net hesaplama için <a href='/dgs-puan-hesaplama.html'>DGS puan hesaplama</a>.",
        "2025 DGS resmî ÖSYM yerleştirme verisi.", "DGS Puanın", "örn. 290,5")


def page_tus_robot():
    if not (ROOT / "veri" / "tus.json").exists():
        return None
    return puan_robot_page(
        "tus-tercih-robotu.html", "2026 TUS Tercih Robotu — Puanına Göre Uzmanlık Dalı Bul | SınavVeri",
        "2026 TUS tercih robotu: TUS puanını gir, 2025 ÖSYM yerleştirme verisine göre girebileceğin uzmanlık dalı ve kurumları gör. Ücretsiz.",
        "2026 TUS Tercih Robotu", "Tıpta Uzmanlık · TUS puanını gir, girebileceğin dal/kurumları gör · 2025 ÖSYM verisine göre",
        "/veri/tus.json", 1, 0, [(2, "Tür")], 4, [(9, "Uzmanlık Dalı"), (2, "Kontenjan Türü")],
        "uzmanlık dalına", 4, 1,
        "TUS puanını girin; o puanla girebileceğin (taban ≤ puanın) kurum ve uzmanlık dallarını en yüksek tabandan başlayarak listeler. "
        "Uzmanlık dalı ve kontenjan türüne göre filtreleyebilirsin. TUS hesaplama için <a href='/yks-puan-hesaplama.html'>puan araçları</a>.",
        "2025 TUS 1. dönem resmî ÖSYM yerleştirme verisi.", "TUS Puanın", "örn. 58,40")


def page_dus_robot():
    if not (ROOT / "veri" / "dus.json").exists():
        return None
    return puan_robot_page(
        "dus-tercih-robotu.html", "2026 DUS Tercih Robotu — Puanına Göre Uzmanlık Dalı Bul | SınavVeri",
        "2026 DUS tercih robotu: DUS puanını gir, 2025 ÖSYM yerleştirme verisine göre girebileceğin diş hekimliği uzmanlık dalı ve kurumları gör. Ücretsiz.",
        "2026 DUS Tercih Robotu", "Diş Hekimliği Uzmanlık · DUS puanını gir, girebileceğin dal/kurumları gör · 2025 ÖSYM verisine göre",
        "/veri/dus.json", 1, 0, [(2, "Tür")], 4, [(9, "Uzmanlık Dalı"), (2, "Kontenjan Türü")],
        "uzmanlık dalına", 4, 1,
        "DUS puanını girin; o puanla girebileceğin (taban ≤ puanın) kurum ve diş hekimliği uzmanlık dallarını listeler. "
        "Uzmanlık dalı ve kontenjan türüne göre filtreleyebilirsin.",
        "2025 DUS resmî ÖSYM yerleştirme verisi.", "DUS Puanın", "örn. 55,20")


def page_kpss_robot():
    if not (ROOT / "veri" / "kpss.json").exists():
        return None
    return puan_robot_page(
        "kpss-tercih-robotu.html", "2026 KPSS Tercih Robotu — Puanına Göre Kadro Bul | SınavVeri",
        "2026 KPSS tercih robotu: KPSS puanını gir, 2025 ÖSYM atama verisine göre yerleşebileceğin kadro/pozisyonları gör. Ücretsiz (Lisans/Önlisans/Ortaöğretim).",
        "2026 KPSS Tercih Robotu", "KPSS puanını gir, atanabileceğin kadroları gör · 2025 ÖSYM yerleştirmelerine göre",
        "/veri/kpss.json", 1, 0, [(2, "İl"), (3, "Düzey")], 6, [(2, "İl"), (3, "Düzey"), (4, "Dönem")],
        "kadroya", 4, 1,
        "KPSS puanını girin ve öğrenim düzeyinizi (Lisans/Önlisans/Ortaöğretim) seçin; o puanla atanabileceğin (taban ≤ puanın) kadroları listeler. "
        "İl ve döneme göre de filtreleyebilirsin. KPSS hesaplama için <a href='/kpss-puan-hesaplama.html'>KPSS puan hesaplama</a>.",
        "ÖSYM 2025 KPSS resmî yerleştirme verisi (2025/1–2025/5).", "KPSS Puanın", "örn. 85,40")


def page_lgs_robot(lgs):
    if not lgs or not (ROOT / "veri" / "liseler.json").exists():
        return None
    return puan_robot_page(
        "lgs-tercih-robotu.html", "2026 LGS Tercih Robotu — Puanına Göre Lise Bul | SınavVeri",
        "2026 LGS tercih robotu: LGS puanını gir, 2025 MEB yerleştirme verisine göre yerleşebileceğin liseleri il ve ilçeye göre gör. Ücretsiz.",
        "2026 LGS Tercih Robotu", "LGS puanını gir, yerleşebileceğin liseleri gör · 2025 MEB yerleştirmesine göre",
        "/veri/liseler.json", 2, None, [(0, "İl"), (1, "İlçe")], 5, [(0, "İl"), (1, "İlçe")],
        "liseye", 15, 4,
        "LGS puanını girin ve ilini seçin; o puanla yerleşebileceğin (taban ≤ puanın) liseleri en yüksek tabandan başlayarak listeler. "
        "LGS hesaplama için <a href='/lgs-puan-hesaplama.html'>LGS puan hesaplama</a>.",
        "MEB 2025 LGS yerleştirme verisi.", "LGS Puanın", "örn. 420,5")


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
    # [il, ilce, okul, türKodu, kontenjan, taban(2025), yüzdelik, tp24, tp23, trend] — çok-yıllık
    rows = [[r["il"], r["ilce"], r["okul"], LISE_TUR_CODE.get(r["tur"], "D"),
             r["kont"], r["tp"], r["yuz"], r.get("tp24"), r.get("tp23"), _osym_trend(r)] for r in lgs]
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
  var sortI=null,sortD=1,SCOLS=[[2,0],[0,0],[3,0],[4,1],[5,1],[7,1],[8,1],[9,0],[6,1]];
  function applySort(rows){
    if(sortI==null||sortI>=SCOLS.length)return rows;
    var f=SCOLS[sortI][0],num=SCOLS[sortI][1];
    rows.sort(function(a,b){var x=a[f],y=b[f];
      if(num){x=(x==null?null:Number(x));y=(y==null?null:Number(y));if(x==null&&y==null)return 0;if(x==null)return 1;if(y==null)return -1;return (x-y)*sortD;}
      return String(x==null?'':x).localeCompare(String(y==null?'':y),'tr')*sortD;});
    return rows;
  }
  function render(reset){
    if(reset!==false)shown=0;
    var rows=applySort(filtered());
    el('status').textContent=rows.length.toLocaleString('tr-TR')+' lise bulundu';
    shown=Math.min(shown+PAGE,rows.length);if(shown===0&&rows.length)shown=Math.min(PAGE,rows.length);
    var tb=el('tbody');tb.innerHTML='';
    rows.slice(0,shown||PAGE).forEach(function(r){
      var tr=document.createElement('tr');
      tr.innerHTML='<td><strong>'+(r[2]||'')+'</strong></td><td>'+(r[0]||'')+(r[1]?' / '+r[1]:'')+'</td>'+
        '<td><span class="tag tag-other">'+(TUR[r[3]]||'—')+'</span></td>'+
        '<td>'+nf(r[4])+'</td><td><strong>'+pf(r[5])+'</strong></td>'+
        '<td>'+pf(r[7])+'</td><td>'+pf(r[8])+'</td><td>'+(r[9]||'')+'</td>'+
        '<td>'+(r[6]==null?'—':'%'+pf(r[6]))+'</td>';
      tb.appendChild(tr);
    });
    el('moreWrap').style.display=(shown<rows.length)?'block':'none';
    el('moreInfo').textContent=shown+' / '+rows.length.toLocaleString('tr-TR');
  }
  ['fQ','fIl','fTur'].forEach(function(id){el(id).addEventListener('input',function(){render(true);});});
  el('moreBtn').addEventListener('click',function(){render(false);});
  (function(){var ths=document.querySelectorAll('.data-table thead th');ths.forEach(function(th,i){
    th.style.cursor='pointer';th.title='Sıralamak için tıklayın';
    th.addEventListener('click',function(){sortD=(sortI===i)?-sortD:1;sortI=i;
      ths.forEach(function(o){var a=o.querySelector('.s-arrow');if(a)a.remove();});
      var ar=document.createElement('span');ar.className='s-arrow';ar.textContent=sortD>0?' ▲':' ▼';th.appendChild(ar);render(true);});});})();
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
<table class="data-table" data-live="1">
<thead><tr><th>Lise</th><th>İl / İlçe</th><th>Tür</th><th>Kont.</th><th>2025 Taban</th><th>2024</th><th>2023</th><th>Trend</th><th>Yüzdelik</th></tr></thead>
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
                     "<td>" + fmt_puan(r.get("tp24")) + "</td>"
                     "<td>" + fmt_puan(r.get("tp23")) + "</td>"
                     "<td>" + _osym_trend(r) + "</td>"
                     "<td>" + yuz + "</td></tr>")
        tabans = [r["tp"] for r in recs if r.get("tp")]
        fen = [r for r in recs if r["tur"] == "Fen Lisesi"]
        summary = (f"<strong>{il}</strong> ilinde 2025 LGS ile öğrenci alan <strong>{len(recs)}</strong> lise listelenmiştir"
                   + (f"; taban puanları <strong>{fmt_puan(min(tabans))}</strong> – <strong>{fmt_puan(max(tabans))}</strong> aralığında." if tabans else "."))
        body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / <a href="/lise-taban-puanlari.html">LGS Liseler</a> / {il}</div>
<div class="page-title"><h1>{il} Liseleri Taban Puanları (LGS · 3 Yıllık Trend)</h1><span class="sub">{len(recs)} sınavla öğrenci alan lise · MEB resmî · 2023-2024-2025 taban + yüzdelik dilim</span></div>
<div class="info-box">{summary} 2024/2023 sütunları geçmiş yıl tabanı, Trend sütunu 2025'in bir önceki yıla göre değişimidir. Tablo 2025 tabanına göre sıralıdır; başlığa tıklayarak yeniden sıralayabilirsiniz.</div>
<div class="data-table-wrap">
<table class="data-table">
<thead><tr><th>Lise</th><th>İlçe</th><th>Tür</th><th>Kont.</th><th>2025 Taban</th><th>2024</th><th>2023</th><th>Trend</th><th>Yüzdelik</th></tr></thead>
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
    # ⚠️ BU LİSTE YAYINLANAN "Yakında Eklenecekler"DİR — bir madde tamamlanınca BURADAN ÇIKAR (güncel tut).
    # Tamamlananlar (artık canlı): KPSS tüm 2025 dönemleri · çok-yıllık trend (DGS/TUS/DUS/LGS 2022-2025, KPSS 2024).
    roadmap = ["YDUS (Yan Dal Uzmanlık) taban puanları",
               "Çok yıllık taban puanı için interaktif trend grafikleri",
               "KPSS: kadro unvanı bazlı yıllık ortalama puan trendi"]
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
  var sortI=null,sortD=1;
  function applySort(rows){
    if(sortI==null)return rows;
    var c=CFG.cols[sortI],fi=c[0],numeric=(c[1]==='p'||c[1]==='pv'||c[1]==='n');
    rows.sort(function(a,b){
      var x=a[fi],y=b[fi];
      if(numeric){var xn=(x==null?null:Number(x)),yn=(y==null?null:Number(y));
        if(xn==null&&yn==null)return 0; if(xn==null)return 1; if(yn==null)return -1; return (xn-yn)*sortD;}
      return String(x==null?'':x).localeCompare(String(y==null?'':y),'tr')*sortD;
    });
    return rows;
  }
  function render(reset){
    if(reset!==false)shown=0;
    var rows=applySort(filtered());
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
  (function(){
    var ths=document.querySelectorAll('.data-table thead th');
    ths.forEach(function(th,i){
      th.style.cursor='pointer'; th.title='Sıralamak için tıklayın';
      th.addEventListener('click',function(){
        sortD=(sortI===i)?-sortD:1; sortI=i;
        ths.forEach(function(o){var a=o.querySelector('.s-arrow');if(a)a.remove();});
        var ar=document.createElement('span');ar.className='s-arrow';ar.textContent=sortD>0?' ▲':' ▼';th.appendChild(ar);
        render(true);
      });
    });
  })();
})();
</script>"""


def minmax_page(slug, title, desc, h1, sub, file, cols, filters, search_idx, intro, kaynak, ph="Ara…", hub_html=""):
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
<table class="data-table" data-live="1"><thead><tr>{thead}</tr></thead><tbody id="tbody"></tbody></table>
</div>
<div id="moreWrap" style="text-align:center;margin-top:16px;display:none">
  <button type="button" class="btn btn-primary" id="moreBtn">Daha fazla göster</button>
  <div id="moreInfo" style="font-size:12px;color:var(--fg-faded);margin-top:6px"></div>
</div>
<div class="notice"><b>Kaynak:</b> {kaynak} Taban = o programa/kadroya yerleşen <b>en düşük</b>, tavan = <b>en yüksek</b> puan.
Yerleşen olmayan satırlarda değer boştur (—). Resmî bilgi için <a href="https://www.osym.gov.tr" target="_blank" rel="noopener">ÖSYM</a> esastır.</div>
{hub_html}
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

    # TUS/DUS: [kurum, dal+(kadro), tur, kont, tp(2025), tavan, tp24, tp23, trend, dal_temiz] — çok-yıllık
    # idx1 = gösterim (kadro türü parantezde: SBA/ÜNİ/EAH…), idx9 = filtre için temiz dal.
    for ex in ("tus", "dus"):
        d = _load_osym(ex)
        if not d:
            continue

        def _dd(r):
            k = r.get("kadro")
            return f'{r["dal"]} ({k})' if k else r["dal"]
        rows = [[r["kurum"], _dd(r), r["tur"], r["kont"], r["tp"], r["tavan"],
                 r.get("tp24"), r.get("tp23"), _osym_trend(r), r["dal"]] for r in d]
        rows.sort(key=lambda x: (x[4] is None, -(x[4] or 0)))
        dump(ex, rows)
    # DGS: [uni, bolum, kont, tp(2025), tavan, tp24, tp23, trend] — çok-yıllık
    d = _load_osym("dgs")
    if d:
        rows = [[r["uni"], r["bolum"], r["kont"], r["tp"], r["tavan"],
                 r.get("tp24"), r.get("tp23"), _osym_trend(r)] for r in d]
        rows.sort(key=lambda x: (x[3] is None, -(x[3] or 0)))
        dump("dgs", rows)
    # KPSS: [kurum, kadro, il, duzey, donem, kont, tp(2025), tavan, tp24, trend]
    d = _load_osym("kpss")
    if d:
        rows = [[r["kurum"], r["kadro"], r["il"], r["duzey"], r.get("donem", ""), r["kont"], r["tp"], r["tavan"],
                 r.get("tp24"), _osym_trend(r)] for r in d]
        rows.sort(key=lambda x: (x[6] is None, -(x[6] or 0)))
        dump("kpss", rows)
    return counts


def page_tus(hubs=None):
    if not (ROOT / "veri" / "tus.json").exists():
        return None
    return minmax_page(
        "tus-taban-puanlari.html", "TUS Taban Puanları 2023-2025 — Kurum ve Uzmanlık Dalı | SınavVeri",
        "TUS taban ve tavan puanları (2025/1) + 2024 ve 2023 karşılaştırması, her hastane/üniversite ve uzmanlık dalı için. ÖSYM resmî, 3 yıllık trend. Kardiyoloji, radyoloji, genel cerrahi ve tüm branşlar.",
        "TUS Taban Puanları (3 Yıllık Trend)", "Tıpta Uzmanlık · kurum × uzmanlık dalı · ÖSYM resmî yerleştirme 2023→2025",
        "/veri/tus.json",
        [(1, "Uzmanlık Dalı", "b"), (0, "Kurum", "t"), (3, "Kont.", "n"),
         (4, "2025 Taban", "p"), (6, "2024", "pv"), (7, "2023", "pv"), (8, "Trend", "t"), (5, "Tavan", "pv")],
        [(9, "Uzmanlık Dalı"), (2, "Kontenjan Türü")], [0, 1],
        "TUS'ta her kurum ve uzmanlık dalı için ÖSYM'nin açıkladığı en düşük (taban) ve en yüksek (tavan) puanlar, "
        "<b>son 3 yılın (2023-2024-2025) yerleştirme karşılaştırmasıyla</b>. Trend sütunu 2025 tabanının bir önceki yıla göre değişimini gösterir. "
        "Dal adının yanındaki parantez <b>kadro türüdür</b> (ÖSYM kontenjan tablosu): "
        "<b>ÜNİ</b> üniversite, <b>SBA</b> Sağlık Bakanlığı Adına, <b>EAH</b> eğitim-araştırma hastanesi, <b>MSB</b> Milli Savunma, "
        "<b>MAP</b> Misafir Askeri Personel, <b>KKTC</b> Kıbrıs, <b>ADL</b> Adalet Bakanlığı, <b>YBU</b> yabancı uyruklu. "
        "Aynı kurum+dalda birden çok kadro ayrı satırdır. Dal veya kurum/şehir arayın, uzmanlık dalına göre filtreleyin.",
        "ÖSYM 2023, 2024 ve 2025 TUS Yerleştirme 'En Küçük ve En Büyük Puanlar' resmî yayınları (dokuman.osym.gov.tr).",
        ph="Dal / kurum / şehir ara…", hub_html=hub_links_html("tus", hubs))


def page_dus(hubs=None):
    if not (ROOT / "veri" / "dus.json").exists():
        return None
    return minmax_page(
        "dus-taban-puanlari.html", "DUS Taban Puanları 2023-2025 — Kurum ve Uzmanlık Dalı | SınavVeri",
        "DUS taban ve tavan puanları (2025/1) + 2024 ve 2023 karşılaştırması, her diş hekimliği fakültesi ve uzmanlık dalı için. ÖSYM resmî, 3 yıllık trend.",
        "DUS Taban Puanları (3 Yıllık Trend)", "Diş Hekimliği Uzmanlık · kurum × dal · ÖSYM resmî 1. dönem 2023→2025",
        "/veri/dus.json",
        [(1, "Uzmanlık Dalı", "b"), (0, "Kurum", "t"), (3, "Kont.", "n"),
         (4, "2025 Taban", "p"), (6, "2024", "pv"), (7, "2023", "pv"), (8, "Trend", "t"), (5, "Tavan", "pv")],
        [(9, "Uzmanlık Dalı")], [0, 1],
        "DUS'ta her kurum ve diş hekimliği uzmanlık dalı için ÖSYM'nin açıkladığı taban ve tavan puanlar, "
        "<b>son 3 yılın (2023-2024-2025) karşılaştırmasıyla</b>. Trend sütunu 2025 tabanının bir önceki yıla göre değişimini gösterir.",
        "ÖSYM 2023, 2024 ve 2025 DUS 'En Küçük ve En Büyük Puanlar' resmî yayınları (dokuman.osym.gov.tr).",
        ph="Dal / kurum ara…", hub_html=hub_links_html("dus", hubs))


def page_dgs_taban(hubs=None):
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
        ph="Program / üniversite ara…", hub_html=hub_links_html("dgs", hubs))


def page_kpss_atama(hubs=None):
    if not (ROOT / "veri" / "kpss.json").exists():
        return None
    return minmax_page(
        "kpss-atama-taban-puanlari.html", "KPSS Atama Taban Puanları 2025 — Kadro Bazında | SınavVeri",
        "2025 KPSS atama taban ve tavan puanları, kadro/pozisyon bazında. ÖSYM resmî yerleştirme verisi (KPSS-2025/1 ve Sağlık Bakanlığı).",
        "KPSS Atama Taban Puanları 2025", "Kadro/pozisyon bazında atama puanları · ÖSYM resmî · 2025 tüm yerleştirmeler",
        "/veri/kpss.json",
        [(1, "Kadro", "b"), (0, "Kurum", "t"), (2, "İl", "t"), (3, "Düzey", "t"), (4, "Dönem", "t"),
         (6, "2025 Taban", "p"), (8, "2024", "pv"), (9, "Trend", "t"), (7, "Tavan", "pv")],
        [(2, "İl"), (3, "Düzey"), (4, "Dönem")], [0, 1],
        "KPSS ile atanılan her kadro/pozisyon için ÖSYM'nin açıkladığı taban ve tavan puanlar. "
        "Kadro veya kurum arayın; il, öğrenim düzeyi ve yerleştirme dönemine göre filtreleyin. "
        "<b>Kapsam:</b> 2025 yılının tüm KPSS yerleştirmeleri (2025/1–2025/5: Genel, Çevre Bak., Sağlık Bak.). "
        "<b>2024</b> sütunu aynı kurum+il+kadronun bir önceki yıl (aynı tür yerleştirme) tabanıdır; Trend değişimi gösterir. "
        "KPSS atamaları tek-seferlik ilanlar olduğundan eşleşme kısmidir (Çevre Bak. için 2024 verisi yoktur).",
        OSYM_KAYNAK, ph="Kadro / kurum ara…", hub_html=hub_links_html("kpss", hubs))


# ───────────────────────── ÖSYM KATEGORİ HUB SAYFALARI (SEO) ─────────────────────────
_TR_ALPHABET = "abcçdefgğhıijklmnoöprsştuüvyz"


def tr_sort_key(text):
    if not text:
        return []
    text = text.replace("İ", "i").replace("I", "ı").lower()
    return [_TR_ALPHABET.index(c) if c in _TR_ALPHABET else 255 for c in text]


# Dikey başına: (group_key, subdir, EX_kısa, sınav_adı, min_kurum, kategori_kelime, kategori_çoğul)
_HUB_CFG = {
    "tus": ("dal", "tus-taban", "TUS", "Tıpta Uzmanlık (TUS)", 1, "uzmanlık dalı", "uzmanlık dalları"),
    "dus": ("dal", "dus-taban", "DUS", "Diş Hekimliği Uzmanlık (DUS)", 1, "uzmanlık dalı", "uzmanlık dalları"),
    "dgs": ("bolum", "dgs-taban", "DGS", "Dikey Geçiş (DGS)", 3, "bölüm", "bölümler"),
    "kpss": ("kadro", "kpss-taban", "KPSS", "KPSS Atama", 2, "kadro", "kadrolar"),
}
# Dikey başına tablo kolonları: (başlık, alan, tür) tür: t=metin, n=tamsayı, p=puan, trend=hesaplanan
_HUB_COLS = {
    "tus": [("Kurum", "kurum", "t"), ("Kadro", "kadro", "t"), ("Tür", "tur", "t"), ("Kont.", "kont", "n"),
            ("2025 Taban", "tp", "p"), ("2024", "tp24", "p"), ("2023", "tp23", "p"), ("Trend", None, "trend"), ("Tavan", "tavan", "p")],
    "dus": [("Kurum", "kurum", "t"), ("Kadro", "kadro", "t"), ("Tür", "tur", "t"), ("Kont.", "kont", "n"),
            ("2025 Taban", "tp", "p"), ("2024", "tp24", "p"), ("2023", "tp23", "p"), ("Trend", None, "trend"), ("Tavan", "tavan", "p")],
    "dgs": [("Üniversite", "uni", "t"), ("Kont.", "kont", "n"),
            ("2025 Taban", "tp", "p"), ("2024", "tp24", "p"), ("2023", "tp23", "p"), ("Trend", None, "trend"), ("Tavan", "tavan", "p")],
    "kpss": [("Kurum", "kurum", "t"), ("İl", "il", "t"), ("Düzey", "duzey", "t"), ("Dönem", "donem", "t"),
             ("Kont.", "kont", "n"), ("2025 Taban", "tp", "p"), ("2024", "tp24", "p"), ("Trend", None, "trend"), ("Tavan", "tavan", "p")],
}
_HUB_MAIN = {"tus": "tus-taban-puanlari.html", "dus": "dus-taban-puanlari.html",
             "dgs": "dgs-taban-puanlari.html", "kpss": "kpss-atama-taban-puanlari.html"}


def _hub_cell(r, field, kind):
    if kind == "trend":
        return _osym_trend(r)
    v = r.get(field)
    if kind == "p":
        return "<strong>" + fmt_puan(v) + "</strong>" if field == "tp" else fmt_puan(v)
    if kind == "n":
        return fmt_sira(v)
    return v if v else "—"


def gen_osym_hub_pages():
    """ÖSYM dikeylerinde kategori (uzmanlık dalı / bölüm / kadro) bazlı toplulaştırıcı
    hub sayfaları — SEO için her kategori = 1 zengin sayfa (tüm kurumlar + 3-yıl trend + özet).
    Döner: (sitemap_slugs, {exam: [(slug, kategori, kurum_sayısı)]})."""
    from collections import defaultdict
    slugs = []
    hub_links = {}
    for exam, (gkey, subdir, EX, sinav, mink, kw, kwp) in _HUB_CFG.items():
        d = _load_osym(exam)
        if not d:
            continue
        groups = defaultdict(list)
        for r in d:
            if r.get(gkey):
                groups[r[gkey]].append(r)
        # çakışmasız slug
        slugmap = {}
        for g in sorted(groups):
            s = slugify(g) or "x"
            base_s, i = s, 2
            while s in slugmap and slugmap[s] != g:
                s = f"{base_s}-{i}"; i += 1
            slugmap[s] = g
        cols = _HUB_COLS[exam]
        links = []
        for s, g in slugmap.items():
            recs = groups[g]
            if len(recs) < mink:
                continue
            recs = sorted(recs, key=lambda r: (r.get("tp") is None, -(r.get("tp") or 0)))
            thead = "".join(f"<th>{h}</th>" for h, _, _ in cols)
            rws = ""
            for r in recs:
                rws += "<tr>" + "".join(f"<td>{_hub_cell(r, f, k)}</td>" for _, f, k in cols) + "</tr>"
            tabans = [r["tp"] for r in recs if r.get("tp")]
            ozet = (f"<strong>{g}</strong> {kw}nda 2025'te <strong>{len(recs)}</strong> "
                    + ("kadro/pozisyon" if exam == "kpss" else "kurum/program") + " yer aldı"
                    + (f"; taban puanları <strong>{fmt_puan(min(tabans))}</strong> – <strong>{fmt_puan(max(tabans))}</strong> "
                       f"aralığında (ortalama <strong>{fmt_puan(round(sum(tabans)/len(tabans),2))}</strong>)." if tabans else "."))
            main = _HUB_MAIN[exam]
            body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / <a href="/taban-puanlari.html">Taban Puanları</a> / <a href="/{main}">{EX}</a> / {g}</div>
<div class="page-title"><h1>{g} {EX} Taban Puanları 2025</h1><span class="sub">{sinav} · {len(recs)} {'kadro' if exam=='kpss' else 'kurum'} · ÖSYM resmî{'' if exam=='kpss' else ' · 3 yıllık trend (2023-2025)'}</span></div>
<div class="info-box">{ozet} Tablo 2025 tabanına göre yüksekten düşüğe sıralıdır.{'' if exam=='kpss' else ' Trend sütunu 2025 tabanının bir önceki yıla göre değişimini gösterir (↑/↓).'}</div>
<div class="data-table-wrap">
<table class="data-table"><thead><tr>{thead}</tr></thead><tbody>{rws}</tbody></table>
</div>
<div class="notice"><b>Kaynak:</b> ÖSYM resmî 'En Küçük ve En Büyük Puanlar' yayını (dokuman.osym.gov.tr).
Tüm {EX} verisi için <a href="/{main}">{EX} taban puanları arama</a> · <a href="/taban-puanlari.html">tüm taban puanları</a>.</div>
"""
            title = f"{g} {EX} Taban Puanları 2025 — Kurum Bazında {'ve 3 Yıllık Trend ' if exam!='kpss' else ''}| SınavVeri"
            desc = (f"{g} {EX.lower()} 2025 taban ve tavan puanları, {len(recs)} {'kadro' if exam=='kpss' else 'kurum'} bazında"
                    + ("" if exam == "kpss" else ", 2023-2024-2025 karşılaştırmasıyla") + ". ÖSYM resmî verisi.")
            write(f"{subdir}/{s}.html", base(f"{subdir}/{s}.html", title, desc, body))
            slugs.append(f"{subdir}/{s}.html")
            links.append((s, g, len(recs)))
        hub_links[exam] = sorted(links, key=lambda x: tr_sort_key(x[1]))
        print(f"  → {len(links)} {EX} hub sayfası ({subdir}/)")
    return slugs, hub_links


def hub_links_html(exam, hub_links):
    """Ana taban sayfasına gömülecek 'kategorilere göz at' iç-link bloğu."""
    links = (hub_links or {}).get(exam) or []
    if not links:
        return ""
    EX = _HUB_CFG[exam][2]
    kwp = _HUB_CFG[exam][6]
    sub = _HUB_CFG[exam][1]
    CAP = 200
    shown = links[:CAP]
    items = " · ".join(f'<a href="/{sub}/{s}.html">{g}</a> <span style="color:var(--fg-faded)">({n})</span>'
                       for s, g, n in shown)
    extra = "" if len(links) <= CAP else f' <span style="color:var(--fg-faded)">… ve {len(links)-CAP} kategori daha (yukarıdaki aramayı kullanın).</span>'
    return (f'<div class="info-box" style="margin-top:14px"><b>{EX} {kwp}na göre göz atın ({len(links)}):</b> '
            f'<div style="margin-top:8px;line-height:2;font-size:13px">{items}{extra}</div></div>')


# ───────────────────────── DOLULUK ANALİZİ ─────────────────────────
def page_doluluk(programs):
    from collections import defaultdict

    def agg(recs):
        k = sum(r["kont"] for r in recs if r.get("kont"))
        y = sum(r["yer"] for r in recs if r.get("yer") is not None and r.get("kont"))
        return k, y, (round(y / k * 100, 1) if k else 0)

    valid = [r for r in programs if r.get("kont") and r.get("yer") is not None]
    tk, ty, tp = agg(valid)

    # Boş kalan / tam dolmayan programlar (yer < kont) → istemci JSON (tab'lı bölüm)
    # satır: [uni, program, il, tür(D/V/K), düzey(L/O), kont, yer, doluluk%]
    bos_list = sorted(
        [[r.get("u") or "", r.get("b") or "", r.get("il") or "", r.get("t") or "?",
          ("O" if r.get("p") == "TYT" else "L"), r["kont"], r["yer"], round(r["yer"] / r["kont"] * 100, 1)]
         for r in valid if r["yer"] < r["kont"]],
        key=lambda x: -(x[5] - x[6]))
    (ROOT / "veri").mkdir(exist_ok=True)
    (ROOT / "veri" / "doluluk_bos.json").write_text(
        json.dumps(bos_list, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # tür bazında
    tur_rows = ""
    for code, name in [("D", "Devlet"), ("V", "Vakıf"), ("K", "KKTC"), ("DK", "Devlet (KKTC Kampüs)")]:
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

<div class="section"><h2>Boş Kalan / Tam Dolmayan Bölümler</h2>
<div class="section-sub">Kontenjanı tamamen dolmayan (yerleşen &lt; kontenjan) programlar · {fmt_sira(len(bos_list))} program · en çok boş kalan üstte</div>
<div class="calc-card" style="margin-bottom:14px">
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px">
    <input id="bq" type="text" placeholder="Program / üniversite ara…" style="padding:9px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:13px">
    <select id="bil" class="btn btn-ghost" style="text-align:left"><option value="">Tüm iller</option></select>
    <select id="btur" class="btn btn-ghost" style="text-align:left"><option value="">Tüm türler</option><option value="D">Devlet</option><option value="V">Özel (Vakıf)</option><option value="K">KKTC</option><option value="DK">Devlet (KKTC Kampüs)</option><option value="DU">Devlet (Ücretli)</option></select>
    <select id="bduz" class="btn btn-ghost" style="text-align:left"><option value="">Tüm düzeyler</option><option value="L">Lisans</option><option value="O">Önlisans</option></select>
  </div>
  <div id="bstatus" style="margin-top:12px;font-size:13px;color:var(--accent);font-weight:700">Yükleniyor…</div>
</div>
<div class="data-table-wrap"><table class="data-table" data-live="1">
<thead><tr><th>Program / Üniversite</th><th>İl</th><th>Tür</th><th>Düzey</th><th>Kont.</th><th>Yerleşen</th><th>Boş</th><th>Doluluk</th></tr></thead>
<tbody id="bbody"></tbody></table></div>
<div style="display:flex;justify-content:center;align-items:center;gap:14px;margin-top:14px">
  <button type="button" class="btn btn-ghost" id="bprev">← Geri</button>
  <span id="bpginfo" style="font-size:13px;color:var(--fg-faded);min-width:180px;text-align:center"></span>
  <button type="button" class="btn btn-ghost" id="bnext">İleri →</button>
</div></div>
<script nonce="__NONCE__">
(function(){{
  var TUR={{D:'Devlet',V:'Özel (Vakıf)',K:'KKTC',DK:'Devlet (KKTC Kampüs)',DU:'Devlet (Ücretli)','?':'—'}},DUZ={{L:'Lisans',O:'Önlisans'}};
  var data=[],page=0,PAGE=20,sortI=null,sortD=1;
  var SCOLS=[[1,0],[2,0],[3,0],[4,0],[5,1],[6,1],['bos',1],[7,1]];
  function el(i){{return document.getElementById(i);}}
  var nf=function(n){{return n==null?'—':Number(n).toLocaleString('tr-TR');}};
  function val(r,f){{return f==='bos'?(r[5]-r[6]):r[f];}}
  function filtered(){{
    var q=(el('bq').value||'').toLocaleLowerCase('tr').trim(),il=el('bil').value,tu=el('btur').value,du=el('bduz').value;
    return data.filter(function(r){{
      if(il&&r[2]!==il)return false;
      if(tu&&r[3]!==tu)return false;
      if(du&&r[4]!==du)return false;
      if(q&&((r[1]+' '+r[0]).toLocaleLowerCase('tr').indexOf(q)<0))return false;
      return true;
    }});
  }}
  function sortRows(rows){{
    if(sortI==null)return rows;
    var c=SCOLS[sortI],f=c[0],num=c[1];
    rows.sort(function(a,b){{var x=val(a,f),y=val(b,f);
      if(num){{x=(x==null?null:Number(x));y=(y==null?null:Number(y));if(x==null&&y==null)return 0;if(x==null)return 1;if(y==null)return -1;return (x-y)*sortD;}}
      return String(x==null?'':x).localeCompare(String(y==null?'':y),'tr')*sortD;}});
    return rows;
  }}
  function render(){{
    var rows=sortRows(filtered());
    var total=rows.length,pages=Math.max(1,Math.ceil(total/PAGE));
    if(page>=pages)page=pages-1; if(page<0)page=0;
    el('bstatus').textContent=total.toLocaleString('tr-TR')+' boş kalan program bulundu';
    var start=page*PAGE,tb=el('bbody');tb.innerHTML='';
    rows.slice(start,start+PAGE).forEach(function(r){{
      var tr=document.createElement('tr');
      tr.innerHTML='<td><strong>'+(r[1]||'')+'</strong><br><small>'+(r[0]||'')+'</small></td>'+
        '<td>'+(r[2]||'—')+'</td><td>'+(TUR[r[3]]||'—')+'</td><td>'+(DUZ[r[4]]||'—')+'</td>'+
        '<td>'+nf(r[5])+'</td><td>'+nf(r[6])+'</td><td><strong>'+nf(r[5]-r[6])+'</strong></td>'+
        '<td><span class="tag tag-other">%'+r[7]+'</span></td>';
      tb.appendChild(tr);
    }});
    el('bpginfo').textContent=total?((start+1)+'–'+Math.min(start+PAGE,total)+' / '+total.toLocaleString('tr-TR')+' · sayfa '+(page+1)+'/'+pages):'sonuç yok';
    el('bprev').disabled=page<=0; el('bnext').disabled=page>=pages-1;
    el('bprev').style.opacity=page<=0?'.45':'1'; el('bnext').style.opacity=page>=pages-1?'.45':'1';
  }}
  function reset(){{page=0;render();}}
  fetch('/veri/doluluk_bos.json').then(function(r){{return r.json();}}).then(function(j){{
    data=j;
    var set={{}};data.forEach(function(r){{if(r[2])set[r[2]]=1;}});
    var sel=el('bil');Object.keys(set).sort(function(a,b){{return a.localeCompare(b,'tr');}})
      .forEach(function(i){{var o=document.createElement('option');o.value=i;o.textContent=i;sel.appendChild(o);}});
    render();
  }}).catch(function(){{el('bstatus').textContent='Veri yüklenemedi.';}});
  ['bq','bil','btur','bduz'].forEach(function(id){{el(id).addEventListener('input',reset);el(id).addEventListener('change',reset);}});
  el('bprev').addEventListener('click',function(){{page--;render();}});
  el('bnext').addEventListener('click',function(){{page++;render();}});
  var hs=document.querySelectorAll('.section table[data-live] thead th');
  hs.forEach(function(th,i){{th.style.cursor='pointer';th.title='Sıralamak için tıklayın';
    th.addEventListener('click',function(){{sortD=(sortI===i)?-sortD:1;sortI=i;
      hs.forEach(function(o){{var a=o.querySelector('.s-arrow');if(a)a.remove();}});
      var ar=document.createElement('span');ar.className='s-arrow';ar.textContent=sortD>0?' ▲':' ▼';th.appendChild(ar);reset();}});}});
}})();
</script>

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
    # Popüler/ana sınavlar üstte
    g = [("yks.html", "🎓", "YKS", "Üniversite giriş sınavı rehberi"),
         ("lgs.html", "🏫", "LGS", "Liselere geçiş sınavı rehberi"),
         ("kpss.html", "🏛️", "KPSS", "Kamu personel seçme sınavı"),
         ("dgs.html", "📈", "DGS", "Dikey geçiş sınavı"),
         ("tus.html", "🩺", "TUS", "Tıpta uzmanlık eğitimi giriş sınavı"),
         ("dus.html", "🦷", "DUS", "Diş hekimliği uzmanlık giriş sınavı"),
         ("ales.html", "📚", "ALES", "Akademik personel / lisansüstü")]
    # Diğer / akademik & özel sınavlar altta
    g2 = [("msu.html", "🎖️", "MSÜ", "Millî Savunma Üniversitesi askerî öğrenci"),
          ("yds.html", "🌐", "YDS", "Yabancı dil seviye tespit sınavı"),
          ("yokdil.html", "🎓", "YÖKDİL", "Akademik yabancı dil (alan bazlı)"),
          ("ydus.html", "🩺", "YDUS", "Tıpta yan dal uzmanlık sınavı"),
          ("sts.html", "📋", "STS", "Yurt dışı diploma denklik sınavı")]
    mk = lambda lst: "".join(f'<a class="tool-btn" href="/{h}"><span class="tb-icon">{i}</span><span class="tb-text"><b>{t}</b><span>{s}</span></span></a>' for h, i, t, s in lst)
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / Rehberler</div>
<div class="page-title"><h1>Sınav Rehberleri</h1><span class="sub">Her sınavın formatı, soru dağılımı ve puan mantığı · resmî (ÖSYM/MEB) bilgilere göre</span></div>
<div class="tool-row">{mk(g)}</div>
<h2 style="margin:26px 0 4px;font-size:18px">Diğer Sınavlar</h2>
<div class="section-sub">Akademik ve özel amaçlı sınavlar</div>
<div class="tool-row">{mk(g2)}</div>
"""
    return base("rehberler.html", "Sınav Rehberleri — YKS, LGS, KPSS, DGS, TUS, DUS, ALES, MSÜ, YDS, YÖKDİL | SınavVeri",
                "Tüm sınav rehberleri: YKS, LGS, KPSS, DGS, TUS, DUS, ALES, MSÜ, YDS, YÖKDİL, YDUS, STS — format, soru dağılımı, puan mantığı ve 2026 tarihleri (ÖSYM/MEB resmî).",
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
    print("  ÖSYM kategori hub sayfaları (SEO) üretiliyor...")
    hub_slugs, hub_links = gen_osym_hub_pages()
    slugs.extend(hub_slugs)
    for slug, fn, ex in [("tus-taban-puanlari.html", page_tus, "tus"), ("dus-taban-puanlari.html", page_dus, "dus"),
                         ("dgs-taban-puanlari.html", page_dgs_taban, "dgs"), ("kpss-atama-taban-puanlari.html", page_kpss_atama, "kpss")]:
        html = fn(hub_links)
        if html:
            W(slug, html)
    print(f"  → toplam {len(hub_slugs)} ÖSYM hub sayfası")
    W("tercih-robotu.html", page_tercih_robotu())
    for slug, fn in [("dgs-tercih-robotu.html", page_dgs_robot), ("tus-tercih-robotu.html", page_tus_robot),
                     ("dus-tercih-robotu.html", page_dus_robot), ("kpss-tercih-robotu.html", page_kpss_robot)]:
        html = fn()
        if html:
            W(slug, html)
    W("puan-hesaplama.html", page_puan_hesaplama_hub())
    W("rehberler.html", page_rehberler_hub())
    W("yks.html", page_yks())
    W("lgs.html", page_lgs())
    W("kpss.html", page_kpss())
    W("dgs.html", page_dgs())
    W("tus.html", page_tus_rehber())
    W("dus.html", page_dus_rehber())
    W("ales.html", page_ales())
    W("msu.html", page_msu_rehber())
    W("yds.html", page_yds_rehber())
    W("yokdil.html", page_yokdil_rehber())
    W("ydus.html", page_ydus_rehber())
    W("sts.html", page_sts_rehber())
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
        h = page_lgs_robot(lgs)
        if h:
            W("lgs-tercih-robotu.html", h)
        print(f"  → {len(il_slugs)} il lise sayfası")
    else:
        print("  ! LGS verisi yok (pipeline/fetch_lgs.py çalıştırılmalı)")

    write_support(slugs)
    print(f"Tamamlandı. Toplam {len(slugs)} sayfa sitemap'te.")


if __name__ == "__main__":
    main()
