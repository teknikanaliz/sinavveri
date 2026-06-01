#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TUS/DUS geçmiş-yıl taban eşleştirme DENETİM raporu (HTML).
Her 2025 programı için: eşleşme tipi (tam/çekirdek/yok), eşleşen 2024/2023 KAYNAK adı + değer,
eşleşmeyenlerde neden. Çıktı: argümanla verilen yola self-contained HTML.
Kullanım: python3 pipeline/audit_match.py /cıkış/yol.html
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_osym as fo


def maps_with_src(url):
    """full/core/all döndür. full: tdkey→(taban,kaynak_kurum). core: corekey→(taban,kaynak) [belirsiz=None].
    all_keys: yerleşen olsun olmasın TÜM tdkey'ler (neden sınıflandırması için)."""
    rows = fo.norm_tus_dus(fo.parse_rows(fo.fetch_pdf_text(url)))
    full, core_tmp, all_keys = {}, {}, set()
    for r in rows:
        tdk = fo._tdkey(r["kurum"], r["dal"], r["tur"])
        all_keys.add(tdk)
        if r["tp"] is None:
            continue
        full[tdk] = (r["tp"], r["kurum"])
        ck = fo._corekey(r["kurum"], r["dal"], r["tur"])
        if ck in core_tmp:
            if core_tmp[ck] is not None and core_tmp[ck][0] != r["tp"]:
                core_tmp[ck] = None  # belirsiz
        else:
            core_tmp[ck] = (r["tp"], r["kurum"])
    return full, core_tmp, all_keys


def match_one(r, full, core, all_keys):
    """(tip, deger, kaynak, neden) → tip: 'tam'/'çekirdek'/'yok'."""
    tdk = fo._tdkey(r["kurum"], r["dal"], r["tur"])
    if tdk in full:
        v, src = full[tdk]
        return "tam", v, src, ""
    ck = fo._corekey(r["kurum"], r["dal"], r["tur"])
    cv = core.get(ck)
    if cv is not None:
        return "çekirdek", cv[0], cv[1], ""
    if ck in core and core[ck] is None:
        return "yok", None, "", "belirsiz (aynı çekirdeğe birden çok farklı kayıt)"
    if tdk in all_keys:
        return "yok", None, "", "o yıl açık ama yerleşen yok (—)"
    return "yok", None, "", "o yıl bu program/kurum yok"


def build(out_path):
    sections = []
    stats = []
    for exam, ad in (("tus", "TUS"), ("dus", "DUS")):
        n25 = fo.norm_tus_dus(fo.parse_rows(fo.fetch_pdf_text(fo.SOURCES[exam][0])))
        years = {}
        for y in (2024, 2023):
            years[y] = maps_with_src(fo.HIST_URLS[exam][y])
        rows = []
        cnt = {"tam": 0, "çekirdek": 0, "yok": 0}
        for r in n25:
            if r["tp"] is None:
                continue
            rec = {"k": r["kurum"], "d": r["dal"], "t": r["tur"], "p": r["tp"]}
            for y in (2024, 2023):
                full, core, allk = years[y]
                tip, v, src, neden = match_one(r, full, core, allk)
                rec[str(y)] = {"tip": tip, "v": v, "src": src, "n": neden}
                if y == 2024:
                    cnt[tip] += 1
            rows.append(rec)
        tot = len(rows)
        stats.append((ad, tot, cnt, fo.SOURCES[exam][0], fo.HIST_URLS[exam][2024], fo.HIST_URLS[exam][2023]))
        sections.append((exam, ad, rows))

    # ---- HTML ----
    data_json = json.dumps({ex: rows for ex, ad, rows in sections}, ensure_ascii=False, separators=(",", ":"))
    stat_html = ""
    for ad, tot, cnt, u25, u24, u23 in stats:
        pct = lambda n: f"{100*n//tot if tot else 0}%"
        stat_html += f"""<div class="card">
        <h3>{ad} — {tot} yerleşen program (2025)</h3>
        <div class="bars">
          <span class="b tam">Tam eşleşme: {cnt['tam']} ({pct(cnt['tam'])})</span>
          <span class="b cek">Çekirdek eşleşme: {cnt['çekirdek']} ({pct(cnt['çekirdek'])})</span>
          <span class="b yok">Eşleşme yok: {cnt['yok']} ({pct(cnt['yok'])})</span>
        </div>
        <div class="src">2024 kaynak: <a href="{u24}" target="_blank" rel="noopener">{u24.split('/')[-1]}</a> ·
        2023 kaynak: <a href="{u23}" target="_blank" rel="noopener">{u23.split('/')[-1]}</a></div>
        </div>"""

    html = """<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>TUS/DUS Geçmiş Yıl Eşleştirme Denetimi — SınavVeri</title>
<style>
:root{color-scheme:dark}
body{font-family:system-ui,Segoe UI,Roboto,sans-serif;margin:0;background:#0f172a;color:#e2e8f0;font-size:14px}
header{padding:20px 24px;background:#1e293b;border-bottom:1px solid #334155}
h1{margin:0 0 4px;font-size:20px}.muted{color:#94a3b8;font-size:13px}
.wrap{padding:20px 24px;max-width:1400px;margin:0 auto}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px;margin-bottom:18px}
.card{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:14px 16px}
.card h3{margin:0 0 10px;font-size:15px}
.bars{display:flex;flex-direction:column;gap:5px;font-size:13px}
.b{padding:3px 8px;border-radius:6px}.b.tam{background:#14532d;color:#bbf7d0}.b.cek{background:#713f12;color:#fde68a}.b.yok{background:#334155;color:#cbd5e1}
.src{margin-top:10px;font-size:11px;color:#94a3b8;word-break:break-all}
.ctl{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
select,input{padding:8px 10px;border:1px solid #334155;border-radius:8px;background:#0f172a;color:#e2e8f0;font:inherit}
input{flex:1;min-width:220px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:7px 9px;border-bottom:1px solid #1e293b;text-align:left;vertical-align:top}
th{position:sticky;top:0;background:#1e293b;font-size:12px}
tr:hover{background:#1e293b}
.pill{font-size:11px;padding:1px 7px;border-radius:10px;white-space:nowrap}
.pill.tam{background:#14532d;color:#bbf7d0}.pill.cek{background:#713f12;color:#fde68a}.pill.yok{background:#334155;color:#94a3b8}
.v{font-weight:700}.src2{font-size:11px;color:#64748b;display:block;margin-top:2px}
.status{color:#38bdf8;font-weight:700;margin-bottom:8px}
</style></head><body>
<header><h1>TUS/DUS Geçmiş Yıl Taban Eşleştirme Denetimi</h1>
<div class="muted">Her 2025 programının 2024/2023 tabanıyla nasıl eşleştiği — kaynak adıyla. Yeşil=tam isim, Sarı=çekirdek-kurum (T.C. Sağlık Bakanlığı/şehir öneki normalize), Gri=eşleşme yok (neden belirtilir). Kaynak: ÖSYM resmî PDF'leri.</div></header>
<div class="wrap">
<div class="cards">__STATS__</div>
<div class="ctl">
  <select id="ex"><option value="tus">TUS</option><option value="dus">DUS</option></select>
  <select id="fl"><option value="">Tüm eşleşme tipleri</option><option value="tam">Sadece tam</option><option value="çekirdek">Sadece çekirdek</option><option value="yok">Sadece eşleşmeyen</option></select>
  <input id="q" placeholder="Kurum / dal ara…">
</div>
<div class="status" id="st"></div>
<table><thead><tr><th>Kurum (2025)</th><th>Uzmanlık Dalı</th><th>Tür</th><th>2025</th><th>2024 (eşleşme)</th><th>2023 (eşleşme)</th></tr></thead>
<tbody id="tb"></tbody></table>
</div>
<script>
var DATA=__DATA__;
function el(i){return document.getElementById(i)}
var pf=function(n){return n==null?'—':Number(n).toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2})};
function cell(o){
  if(!o||o.tip==='yok')return '<span class="pill yok">yok</span>'+(o&&o.n?'<span class="src2">'+o.n+'</span>':'');
  return '<span class="v">'+pf(o.v)+'</span> <span class="pill '+(o.tip==='tam'?'tam':'cek')+'">'+o.tip+'</span>'+(o.src?'<span class="src2">← '+o.src+'</span>':'');
}
function render(){
  var ex=el('ex').value,fl=el('fl').value,q=(el('q').value||'').toLocaleLowerCase('tr').trim();
  var rows=DATA[ex].filter(function(r){
    if(fl&&r['2024'].tip!==fl)return false;
    if(q&&((r.k+' '+r.d).toLocaleLowerCase('tr').indexOf(q)<0))return false;
    return true;
  });
  el('st').textContent=rows.length.toLocaleString('tr-TR')+' satır';
  var h='';rows.slice(0,1500).forEach(function(r){
    h+='<tr><td>'+r.k+'</td><td>'+r.d+'</td><td>'+r.t+'</td><td class="v">'+pf(r.p)+'</td><td>'+cell(r['2024'])+'</td><td>'+cell(r['2023'])+'</td></tr>';
  });
  if(rows.length>1500)h+='<tr><td colspan="6" style="text-align:center;color:#64748b">İlk 1500 satır gösteriliyor — daralt.</td></tr>';
  el('tb').innerHTML=h;
}
el('ex').onchange=render;el('fl').onchange=render;el('q').oninput=render;render();
</script></body></html>"""
    html = html.replace("__STATS__", stat_html).replace("__DATA__", data_json)
    Path(out_path).write_text(html, encoding="utf-8")
    print(f"Yazıldı: {out_path} ({len(html)//1024} KB)")
    for ad, tot, cnt, *_ in stats:
        print(f"  {ad}: {tot} | tam {cnt['tam']} çekirdek {cnt['çekirdek']} yok {cnt['yok']}")


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "audit_match.html")
