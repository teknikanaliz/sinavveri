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
ASSET_VER = "20260604e"

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


SV_HELPER_JS = r"""<script nonce="__NONCE__">
(function(){
  var SV = window.SV = window.SV || {};
  SV.qsGet = function(){ var o={}; try{ new URLSearchParams(location.search).forEach(function(v,k){o[k]=v;}); }catch(e){} return o; };
  SV.qsSet = function(obj){
    try{
      var p=new URLSearchParams();
      Object.keys(obj).forEach(function(k){ var v=obj[k]; if(v!=null && v!=='') p.set(k,v); });
      var s=p.toString();
      history.replaceState(null,'',location.pathname+(s?'?'+s:'')+location.hash);
    }catch(e){}
  };
  SV.chips = function(id, items, onRemove){
    var c=document.getElementById(id); if(!c) return;
    c.innerHTML='';
    if(!items.length){ c.style.display='none'; return; }
    c.style.display='flex';
    items.forEach(function(it){
      var ch=document.createElement('span'); ch.className='fchip';
      ch.appendChild(document.createTextNode(it.label+' '));
      var b=document.createElement('button'); b.type='button'; b.setAttribute('aria-label','Kaldır'); b.textContent='×';
      b.addEventListener('click',function(){ onRemove(it.key); });
      ch.appendChild(b); c.appendChild(ch);
    });
    var clr=document.createElement('button'); clr.type='button'; clr.className='fchip-clear'; clr.textContent='Tümünü temizle';
    clr.addEventListener('click',function(){ onRemove('__all__'); });
    c.appendChild(clr);
  };
  // Üniversite kısaltmaları → ad içinde aranan bitişik ifade (yanlış eşleşmeyi önlemek için ifade-tam)
  SV.alias = {
    'odtü':'orta doğu teknik','odtu':'orta doğu teknik','metu':'orta doğu teknik',
    'itü':'istanbul teknik','itu':'istanbul teknik',
    'ytü':'yıldız teknik','ytu':'yıldız teknik',
    'gtü':'gebze teknik','gtu':'gebze teknik',
    'ktü':'karadeniz teknik','ktu':'karadeniz teknik',
    'btü':'bursa teknik','btu':'bursa teknik',
    'boun':'boğaziçi','boğaziçi':'boğaziçi',
    'iü':'istanbul üniversitesi','iüc':'istanbul üniversitesi-cerrahpaşa','iü-c':'istanbul üniversitesi-cerrahpaşa',
    'aü':'ankara üniversitesi','hü':'hacettepe','gü':'gazi üniversitesi','eü':'ege üniversitesi',
    'deü':'dokuz eylül','msgsü':'mimar sinan','iyte':'izmir yüksek teknoloji','iztech':'izmir yüksek teknoloji',
    'omü':'ondokuz mayıs','sdü':'süleyman demirel','akü':'afyon kocatepe','pau':'pamukkale',
    'çü':'çukurova','atatürk':'atatürk üniversitesi','asbü':'ankara sosyal bilimler','ybü':'yıldırım beyazıt',
    'gop':'gaziosmanpaşa','nef':'necmettin erbakan','marmara':'marmara üniversitesi','msü':'millî savunma'
  };
  SV.estSira = function(curve, p){
    if(!curve || !curve.length || !(p>0)) return null;
    if(p<=curve[0][0]) return curve[0][1];
    if(p>=curve[curve.length-1][0]) return curve[curve.length-1][1];
    var lo=0,hi=curve.length-1;
    while(hi-lo>1){ var m=(lo+hi)>>1; if(curve[m][0]<=p)lo=m; else hi=m; }
    var a=curve[lo],b=curve[hi],t=(p-a[0])/((b[0]-a[0])||1);
    return Math.max(1, Math.round(a[1]+(b[1]-a[1])*t));
  };
  SV.estPuan = function(curve, sira){
    if(!curve || !curve.length || !(sira>0)) return null;
    if(sira>=curve[0][1]) return curve[0][0];
    if(sira<=curve[curve.length-1][1]) return curve[curve.length-1][0];
    var lo=0,hi=curve.length-1;
    while(hi-lo>1){ var m=(lo+hi)>>1; if(curve[m][1]>=sira)lo=m; else hi=m; }
    var a=curve[lo],b=curve[hi],d=(a[1]-b[1])||1,t=(a[1]-sira)/d;
    return Math.round((a[0]+(b[0]-a[0])*t)*100)/100;
  };
  SV.spark = function(vals){
    var pts=[]; for(var i=0;i<vals.length;i++){ var v=vals[i]; if(v!=null && !isNaN(v)) pts.push({i:i,v:Number(v)}); }
    if(pts.length<2) return '';
    var w=42,h=14,pad=2,xs=vals.length-1||1;
    var vs=pts.map(function(p){return p.v;}); var mn=Math.min.apply(null,vs),mx=Math.max.apply(null,vs),rng=mx-mn||1;
    var d=pts.map(function(p){var x=pad+(p.i/xs)*(w-2*pad);var y=h-pad-((p.v-mn)/rng)*(h-2*pad);return x.toFixed(1)+','+y.toFixed(1);}).join(' ');
    var f=pts[0].v,l=pts[pts.length-1].v,col=l>f?'#16a34a':(l<f?'#dc2626':'#94a3b8');
    return '<svg width="'+w+'" height="'+h+'" viewBox="0 0 '+w+' '+h+'" style="vertical-align:middle;margin-left:6px;flex:0 0 auto" aria-hidden="true"><polyline fill="none" stroke="'+col+'" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" points="'+d+'"/></svg>';
  };
  SV.tokMatch = function(hay, q){
    hay = (hay || '').toLocaleLowerCase('tr');
    var ts = (q || '').toLocaleLowerCase('tr').trim().split(/\s+/);
    for (var i = 0; i < ts.length; i++){
      var t = ts[i]; if (!t) continue;
      var exp = SV.alias[t];
      if (exp){ if (hay.indexOf(exp) < 0) return false; }
      else if (hay.indexOf(t) < 0) return false;
    }
    return true;
  };
  SV.skel = function(tbodyId, cols, n){
    var tb=document.getElementById(tbodyId); if(!tb) return;
    var h=''; for(var r=0;r<(n||8);r++){ h+='<tr>'; for(var c=0;c<cols;c++){ h+='<td><div class="skel-cell"></div></td>'; } h+='</tr>'; }
    tb.innerHTML=h;
  };
  SV.empty = function(tbodyId, cols, msg){
    var tb=document.getElementById(tbodyId); if(!tb) return;
    tb.innerHTML='<tr><td colspan="'+cols+'"><div class="empty-state"><b>Eşleşme yok</b>'+(msg||'Filtreyi gevşetmeyi veya aramayı sadeleştirmeyi deneyin.')+'</div></td></tr>';
  };
  SV.copy = function(text, btn){
    function done(){ if(btn){ var t=btn.getAttribute('data-lbl')||btn.textContent; btn.setAttribute('data-lbl',t); btn.textContent='Kopyalandı ✓'; setTimeout(function(){btn.textContent=t;},1600); } }
    function fallback(){ try{ var ta=document.createElement('textarea'); ta.value=text; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta); done(); }catch(e){} }
    try{ if(navigator.clipboard&&navigator.clipboard.writeText){ navigator.clipboard.writeText(text).then(done,fallback); } else { fallback(); } }catch(e){ fallback(); }
  };
  SV.fav = function(ns){
    var KEY='sv-fav-'+ns;
    function read(){ try{ return JSON.parse(localStorage.getItem(KEY)||'[]'); }catch(e){ return []; } }
    function write(a){ try{ localStorage.setItem(KEY,JSON.stringify(a)); }catch(e){} }
    return {
      list: read,
      has: function(id){ return read().some(function(x){return x.id===id;}); },
      toggle: function(it){ var a=read(); var i=-1,k; for(k=0;k<a.length;k++){ if(a[k].id===it.id){i=k;break;} } if(i>=0){a.splice(i,1);} else {a.push(it);} write(a); return i<0; },
      remove: function(id){ write(read().filter(function(x){return x.id!==id;})); },
      clear: function(){ write([]); },
      move: function(id,dir){ var a=read(); var i=-1,k; for(k=0;k<a.length;k++){if(a[k].id===id){i=k;break;}} if(i<0)return; var j=i+dir; if(j<0||j>=a.length)return; var t=a[i];a[i]=a[j];a[j]=t; write(a); }
    };
  };
  // Tercih Listem UI controller — bar/panel + ☆ stars
  SV.initFav = function(opts){
    var store=SV.fav(opts.ns);
    var bar=document.getElementById(opts.barId), panel=document.getElementById(opts.panelId), btn=document.getElementById(opts.btnId);
    function esc(s){ return (''+(s==null?'':s)).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
    function asText(arr){ return arr.map(function(x,i){return (i+1)+'. '+x.name+(x.sub?' — '+x.sub:'')+(x.meta?' ('+x.meta+')':'');}).join('\n'); }
    function renderPanel(arr){
      if(!panel)return;
      var h='<h3>⭐ Tercih Listem ('+arr.length+')</h3>';
      if(!arr.length){ h+='<p style="font-size:13px;color:var(--fg-faded);margin:6px 0 0">Henüz tercih eklemediniz. Tablodaki ☆ simgesiyle ekleyin; listeniz bu tarayıcıda saklanır.</p>'; }
      else{
        h+='<p style="font-size:12px;color:var(--fg-faded);margin:0 0 8px">Sıralamak için ↑↓ kullanın — tercih sıranız bu düzendir.</p>';
        h+='<div class="fp-actions">'
          +'<button type="button" class="btn btn-ghost" id="'+opts.panelId+'C">📋 Kopyala</button>'
          +'<button type="button" class="btn btn-ghost" id="'+opts.panelId+'P">🖨️ Yazdır / PDF</button>'
          +'<button type="button" class="btn btn-ghost" id="'+opts.panelId+'S">🔗 Paylaş</button>'
          +'<button type="button" class="fchip-clear" id="'+opts.panelId+'X">Temizle</button></div>';
        h+='<ul class="fav-list">';
        arr.forEach(function(it,i){
          h+='<li><span style="display:flex;align-items:baseline;gap:8px"><span class="fl-n">'+(i+1)+'.</span><span><b>'+esc(it.name)+'</b>'+(it.sub?' <small>'+esc(it.sub)+'</small>':'')+(it.meta?' — '+esc(it.meta):'')+'</span></span>'
            +'<span class="fl-ops"><button type="button" class="fl-mv" data-mv="'+esc(it.id)+'" data-dir="-1" aria-label="Yukarı"'+(i===0?' disabled':'')+'>↑</button>'
            +'<button type="button" class="fl-mv" data-mv="'+esc(it.id)+'" data-dir="1" aria-label="Aşağı"'+(i===arr.length-1?' disabled':'')+'>↓</button>'
            +'<button type="button" class="fl-x" aria-label="Çıkar" data-rm="'+esc(it.id)+'">×</button></span></li>';
        });
        h+='</ul>';
      }
      panel.innerHTML=h;
    }
    function refresh(){
      var arr=store.list();
      if(bar)bar.classList.toggle('show',arr.length>0);
      if(btn)btn.textContent='⭐ Tercih Listem ('+arr.length+')';
      if(panel&&panel.classList.contains('open'))renderPanel(arr);
      document.querySelectorAll('.fav-star[data-fid]').forEach(function(s){ var on=store.has(s.getAttribute('data-fid')); s.classList.toggle('on',on); s.textContent=on?'★':'☆'; });
    }
    function printList(){
      var arr=store.list(); if(!arr.length)return;
      var rows=arr.map(function(x,i){return '<tr><td>'+(i+1)+'<\/td><td><b>'+esc(x.name)+'<\/b>'+(x.sub?'<br><small>'+esc(x.sub)+'<\/small>':'')+'<\/td><td>'+esc(x.meta||'')+'<\/td><\/tr>';}).join('');
      var w=window.open('','_blank'); if(!w)return;
      w.document.write('<!doctype html><html lang=tr><head><meta charset=utf-8><title>Tercih Listem — SınavVeri.com<\/title><style>body{font-family:Arial,sans-serif;padding:24px;color:#15192b}h1{font-size:20px;color:#b45309}table{width:100%;border-collapse:collapse;margin-top:12px;font-size:13px}td,th{border:1px solid #ccc;padding:7px 10px;text-align:left}th{background:#f0f3fa}td:first-child{width:36px;text-align:center;font-weight:700}small{color:#666}.f{margin-top:16px;font-size:11px;color:#888}<\/style><\/head><body><h1>⭐ Tercih Listem<\/h1><table><thead><tr><th>#<\/th><th>Program / Üniversite<\/th><th>Bilgi<\/th><\/tr><\/thead><tbody>'+rows+'<\/tbody><\/table><div class=f>SınavVeri.com · '+arr.length+' tercih · Bu liste resmî tercih belgesi değildir; kesin tercih ÖSYM AİS üzerinden yapılır.<\/div><\/body><\/html>');
      w.document.close(); setTimeout(function(){try{w.print();}catch(e){}},300);
    }
    function shareLink(t){
      var arr=store.list(); if(!arr.length)return;
      try{ var slim=arr.map(function(x){return {n:x.name,s:x.sub||'',m:x.meta||''};});
        var enc=btoa(unescape(encodeURIComponent(JSON.stringify(slim))));
        var url=location.origin+location.pathname+'?l='+enc;
        SV.copy(url,t);
      }catch(e){}
    }
    if(btn)btn.addEventListener('click',function(){ var op=panel.classList.toggle('open'); if(op)renderPanel(store.list()); });
    if(panel)panel.addEventListener('click',function(e){
      var t=e.target;
      if(t.getAttribute&&t.getAttribute('data-rm')!=null){ store.remove(t.getAttribute('data-rm')); refresh(); }
      else if(t.getAttribute&&t.getAttribute('data-mv')!=null){ store.move(t.getAttribute('data-mv'),parseInt(t.getAttribute('data-dir'),10)); refresh(); }
      else if(t.id===opts.panelId+'X'){ if(confirm('Tercih listeniz silinsin mi?')){store.clear(); refresh();} }
      else if(t.id===opts.panelId+'C'){ SV.copy('Tercih Listem — SınavVeri.com\n\n'+asText(store.list()), t); }
      else if(t.id===opts.panelId+'P'){ printList(); }
      else if(t.id===opts.panelId+'S'){ shareLink(t); }
    });
    // Paylaşılan liste (?l=) → kendi listene ekleme önerisi
    (function(){
      try{ var qs=SV.qsGet?SV.qsGet():{}; if(!qs.l)return;
        var slim=JSON.parse(decodeURIComponent(escape(atob(qs.l))));
        if(!slim||!slim.length||!bar)return;
        var box=document.createElement('div'); box.className='fav-panel open'; box.style.marginBottom='10px';
        box.innerHTML='<h3>🔗 Paylaşılan Tercih Listesi ('+slim.length+')</h3><ul class="fav-list">'+
          slim.map(function(x,i){return '<li><span>'+(i+1)+'. <b>'+esc(x.n)+'</b>'+(x.s?' <small>'+esc(x.s)+'</small>':'')+'</span></li>';}).join('')+
          '</ul><div class="fp-actions"><button type="button" class="btn btn-primary" id="'+opts.panelId+'imp">Bu listeyi listeme ekle</button></div>';
        bar.parentNode.insertBefore(box,bar);
        box.querySelector('#'+opts.panelId+'imp').addEventListener('click',function(){
          slim.forEach(function(x){ var id=x.n+'|'+x.s; if(!store.has(id))store.toggle({id:id,name:x.n,sub:x.s,meta:x.m}); });
          refresh(); box.parentNode.removeChild(box);
        });
      }catch(e){}
    })();
    return { store:store, toggle:function(it){ store.toggle(it); refresh(); }, has:function(id){return store.has(id);}, refresh:refresh };
  };
})();
</script>"""

HEADER_SEARCH_JS = r"""<script nonce="__NONCE__">
(function(){
  var form=document.getElementById('hsearch'); if(!form) return;
  var inp=document.getElementById('hsQ'), drop=document.getElementById('hsDrop');
  var DATA=null, loading=false, sel=-1;
  function load(cb){ if(DATA){cb&&cb();return;} if(loading)return; loading=true;
    fetch('/veri/arama.json').then(function(r){return r.json();}).then(function(j){DATA=j;loading=false;cb&&cb();}).catch(function(){loading=false;}); }
  function norm(s){return (s||'').toLocaleLowerCase('tr');}
  function tok(hay,q){ var SV=window.SV; if(SV&&SV.tokMatch)return SV.tokMatch(hay,q); return norm(hay).indexOf(norm(q))>=0; }
  function search(q){ if(!DATA)return []; if(q.trim().length<2)return [];
    var out=[]; for(var i=0;i<DATA.length && out.length<8;i++){ var d=DATA[i]; if(tok((d.n||'')+' '+(d.s||''),q)){ out.push(d); } } return out; }
  function esc(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
  function close(){ drop.classList.remove('open'); drop.innerHTML=''; sel=-1; }
  function show(){ var q=inp.value; if(!q||q.trim().length<2){ close(); return; } var res=search(q);
    var multi=q.trim().split(/\s+/).filter(Boolean).length>=2;
    var prog=multi?'<a class="hs-item" href="/universite-taban-puanlari.html?q='+encodeURIComponent(q)+'"><span class="hs-kind">Program →</span>🎓 “'+esc(q)+'” programları</a>':'';
    if(!res.length){ drop.innerHTML=prog+'<a class="hs-item" href="/ara.html?q='+encodeURIComponent(q)+'">"'+esc(q)+'" için tüm sonuçlar…</a>'; drop.classList.add('open'); return; }
    var h=prog; res.forEach(function(d){ h+='<a class="hs-item" href="'+d.u+'"><span class="hs-kind">'+esc(d.t)+'</span>'+esc(d.n)+(d.s?'<small>'+esc(d.s)+'</small>':'')+'</a>'; });
    h+='<a class="hs-item" href="/ara.html?q='+encodeURIComponent(q)+'" style="text-align:center;color:var(--accent);font-weight:700">Tüm sonuçlar →</a>';
    drop.innerHTML=h; drop.classList.add('open'); sel=-1;
  }
  inp.addEventListener('focus',function(){ load(show); });
  inp.addEventListener('input',function(){ load(show); });
  inp.addEventListener('keydown',function(e){
    var links=drop.querySelectorAll('.hs-item');
    if(e.key==='ArrowDown'){ e.preventDefault(); sel=Math.min(sel+1,links.length-1); }
    else if(e.key==='ArrowUp'){ e.preventDefault(); sel=Math.max(sel-1,0); }
    else if(e.key==='Enter'){ if(sel>=0&&links[sel]){ e.preventDefault(); location.href=links[sel].getAttribute('href'); } return; }
    else { return; }
    links.forEach(function(l,i){ l.classList.toggle('sel',i===sel); });
  });
  document.addEventListener('click',function(e){ if(!form.contains(e.target)) close(); });
})();
</script>"""


NAV_TOGGLE_JS = r"""<script nonce="__NONCE__">
(function(){
  var b=document.getElementById('navToggle'), n=document.getElementById('mainNav'); if(!b||!n)return;
  function close(){ n.classList.remove('open'); b.setAttribute('aria-expanded','false'); b.textContent='☰'; }
  b.addEventListener('click',function(e){ e.stopPropagation(); var o=n.classList.toggle('open'); b.setAttribute('aria-expanded',o?'true':'false'); b.textContent=o?'✕':'☰'; });
  n.addEventListener('click',function(e){ if(e.target.tagName==='A')close(); });
  document.addEventListener('click',function(e){ if(n.classList.contains('open') && !n.contains(e.target) && e.target!==b)close(); });
})();
</script>"""

CARD_LABEL_JS = r"""<script nonce="__NONCE__">
(function(){
  function label(tbl){
    var ths=tbl.querySelectorAll('thead th'); if(!ths.length)return;
    var L=Array.prototype.map.call(ths,function(t){return t.textContent.trim();});
    tbl.querySelectorAll('tbody>tr').forEach(function(tr){
      Array.prototype.forEach.call(tr.children,function(td,i){ if(L[i]!=null && !td.hasAttribute('data-label')) td.setAttribute('data-label',L[i]); });
    });
  }
  document.querySelectorAll('table.data-table').forEach(function(tbl){
    label(tbl);
    var b=tbl.querySelector('tbody');
    if(b && window.MutationObserver){ new MutationObserver(function(){label(tbl);}).observe(b,{childList:true}); }
  });
})();
</script>"""


def breadcrumb_ld(items):
    """items: [(name, slug_or_None)]. Son öğe genelde slug'sız (mevcut sayfa)."""
    el = []
    for i, (name, slug) in enumerate(items, 1):
        item = {"@type": "ListItem", "position": i, "name": name}
        if slug:
            item["item"] = SITE + "/" + (slug if slug != "index.html" else "")
        el.append(item)
    return {"@type": "BreadcrumbList", "itemListElement": el}


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
{SV_HELPER_JS}
<link rel="stylesheet" href="/assets/style.css?v={ASSET_VER}">
<link rel="manifest" href="/manifest.json">
{extra_head}
</head>
<body>
<header>
  <div class="header-inner">
    <a href="/index.html" class="logo">Sınav<span class="logo-veri">Veri</span></a>
    <div class="header-right">
      <form class="hsearch" id="hsearch" role="search" action="/ara.html" method="get" autocomplete="off">
        <span class="hs-ic">🔍</span>
        <input type="search" name="q" id="hsQ" placeholder="Üniversite, bölüm, lise, kadro…" aria-label="Sitede ara">
        <div class="hs-drop" id="hsDrop" role="listbox"></div>
      </form>
      <button type="button" class="nav-toggle" id="navToggle" aria-label="Menü" aria-expanded="false">☰</button>
      <nav id="mainNav">{nav_html}</nav>
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
{HEADER_SEARCH_JS}
{NAV_TOGGLE_JS}
{CARD_LABEL_JS}
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
TUR_FULL = {"D": "Devlet", "V": "Vakıf", "K": "KKTC", "DK": "Devlet (KKTC Kampüs)", "DU": "Devlet (Ücretli)", "DKU": "Devlet (KKTC Uyruklu)", "Y": "Diğer", "?": "—"}


def _short_fak(f):
    return (f or "").replace("Meslek Yüksekokulu", "MYO").replace(" Fakültesi", "").strip()


def _disambiguate_programs(progs):
    """Aynı (program, üniversite, il) görünen programları, birincil kaynaktaki (YÖK Atlas)
    gerçek ayırt edici alanla parantez içinde işaretler. Öncelik: fakülte/MYO → ilçe →
    yabancı dil → burs → ikinci öğretim → (son çare) kontenjan. Adı yerinde değiştirir."""
    from collections import defaultdict
    g = defaultdict(list)
    for r in progs:
        g[((r.get("b") or "").strip(), (r.get("u") or "").strip(), (r.get("il") or "").strip())].append(r)
    for group in g.values():
        if len(group) < 2:
            continue
        def vary(attr):
            return len({(r.get(attr) or "") for r in group}) > 1
        for r in group:
            b = r.get("b") or ""
            parts = []
            if vary("fak") and r.get("fak"):
                parts.append(_short_fak(r["fak"]))
            if vary("ilce") and r.get("ilce"):
                parts.append(r["ilce"])
            if vary("dil") and r.get("dil") and r["dil"] not in b:
                parts.append(r["dil"])
            if vary("bs") and r.get("bs") and r["bs"] not in b:
                parts.append(r["bs"])
            if vary("o") and "İkinci" in (r.get("o") or ""):
                parts.append("İÖ")
            r["_lbl"] = parts
        # aynı etikete düşenleri kontenjanla, hâlâ eşitse sırayla ayır
        for _ in range(2):
            buckets = defaultdict(list)
            for r in group:
                buckets[tuple(r["_lbl"])].append(r)
            for lbl, rs in buckets.items():
                if len(rs) > 1:
                    if len({r.get("kont") for r in rs}) == len(rs) and all(r.get("kont") for r in rs):
                        for r in rs:
                            r["_lbl"] = list(lbl) + [f"{r['kont']} kont."]
                    else:
                        for i, r in enumerate(sorted(rs, key=lambda x: (x.get("tp") is None, -(x.get("tp") or 0))), 1):
                            r["_lbl"] = list(lbl) + [str(i)]
        for r in group:
            if r.get("_lbl"):
                lbl = ", ".join(r["_lbl"])
                b = r["b"]
                # ad zaten "(...)" ile bitiyorsa çift parantez yerine tek parantez içine ekle
                r["b"] = (b[:-1] + ", " + lbl + ")") if b.endswith(")") else (b + " (" + lbl + ")")
            r.pop("_lbl", None)
    return progs


def load_programs():
    progs = json.loads((ROOT / "data" / "programs_raw.json").read_text(encoding="utf-8"))
    # Türk devlet üniversitelerinin KKTC kampüsleri (ODTÜ/İTÜ/ASBÜ Kıbrıs) normal ücretsiz
    # devlet programı DEĞİL → ayrı tür "DK". (YÖK Atlas universiteTuru=DEVLET döner; gösterim/filtre için ayrıştırılır.)
    for r in progs:
        # Türkçe büyük-İ artefaktı: .title() "İZMİR"→"İzmi̇r" (i + U+0307 birleşik nokta) üretir → temizle
        for f in ("il", "ilce"):
            if r.get(f):
                r[f] = r[f].replace("̇", "")
        if r.get("t") == "D" and "KKTC Uyruklu" in (r.get("b") or ""):
            r["t"] = "DKU"  # Devlet üniv.'de KKTC uyruklu özel kontenjan (ad zaten "(KKTC Uyruklu)" içerir)
            continue
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
    return _disambiguate_programs(progs)


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
  <p>2026 tercih robotu, 2025 üniversite LGS TUS DUS DGS KPSS taban puanları, puan hesaplama araçları ve güncel sınav takvimi. Sade, hızlı ve detaylı bilgi.</p>
  <div class="hero-badges"><a href="/taban-puanlari.html">📊 21.602 Üniversite Programı</a><a href="/tercih-robotu.html">🎯 Tercih Robotu</a><a href="/puan-hesaplama.html">🧮 Puan Hesaplama</a><a href="/takvim.html">📅 2026 Takvimi</a></div>
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
_GUIDE_SLUG = [("YÖKDİL", "yokdil.html"), ("YDUS", "ydus.html"), ("YKS", "yks.html"),
               ("YDS", "yds.html"), ("LGS", "lgs.html"), ("KPSS", "kpss.html"),
               ("DGS", "dgs.html"), ("DUS", "dus.html"), ("TUS", "tus.html"),
               ("ALES", "ales.html"), ("MSÜ", "msu.html"), ("STS", "sts.html")]


def _guide_for(ad):
    a = (ad or "").upper()
    for key, slug in _GUIDE_SLUG:
        if a.startswith(key):
            return slug
    return None


def page_takvim():
    rows = ""
    for s in CAL["sinavlar"]:
        lbl, cls = TUR_LABEL.get(s["tur"], TUR_LABEL["other"])
        sinav = fmt_date(s["sinav"]) if s["sinav"].count("-") == 2 else s["sinav"]
        gslug = _guide_for(s["ad"])
        ad_html = f'<a href="/{gslug}" title="{s["ad"]} sınav rehberi">{s["ad"]}</a>' if gslug else s["ad"]
        rows += f"""<tr>
  <td><span class="tag {cls}">{lbl}</span></td>
  <td><strong>{ad_html}</strong>{('<br><small class="soon">'+s['not']+'</small>') if s['not'] else ''}</td>
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
<div class="notice"><b>Not:</b> Tarihler ÖSYM 2026 Yılı Sınav Takvimi ve her sınavın resmî <b>kılavuz/duyurularıyla</b> (YKS, LGS, KPSS, DGS, ALES, TUS, DUS, YDS…) teyit edilmiştir.
Yaklaşmayan sınavların başvuru tarihleri ilgili kılavuz yayımlanınca kesinleşir; güncel bilgi için <a href="https://www.osym.gov.tr" target="_blank" rel="noopener">osym.gov.tr</a> ve <a href="https://www.meb.gov.tr" target="_blank" rel="noopener">meb.gov.tr</a> esastır.</div>
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
<div class="tool-row" style="margin-top:16px"><a class="tool-btn" href="/yks-siralama-hesaplama.html"><span class="tb-icon">📈</span><span class="tb-text"><b>Tahmini Sıralaman ve Gidebileceğin Bölümler</b><span>Puanından başarı sıranı tahmin et → tercih robotuna git</span></span></a></div>
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


def page_yks_siralama():
    body = """
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / <a href="/puan-hesaplama.html">Puan Hesaplama</a> / YKS Sıralama</div>
<div class="page-title"><h1>2026 YKS Sıralama Hesaplama — Puan → Tahmini Başarı Sırası</h1><span class="sub">Puanını gir, tahmini sıralamanı ve gidebileceğin bölümleri gör · 2025 YÖK Atlas verisine göre</span></div>
<div class="info-box">Denemende/ÖSYM sonucunda aldığın <b>yerleştirme puanını</b> ve puan türünü gir → 2025 gerçek yerleştirme verisinden
<b>tahmini başarı sıralaman</b> ve o sırayla <b>gidebileceğin bölümler</b>. Puanını bilmiyorsan aşağıdaki net aracıyla kaba tahmin alabilirsin.</div>
<div class="calc-card" style="margin-bottom:18px">
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;align-items:end">
    <div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">Puan Türü</label>
      <select id="sPt" class="btn btn-ghost" style="text-align:left;width:100%;margin-top:4px">
        <option value="say">Sayısal (SAY)</option><option value="ea">Eşit Ağırlık (EA)</option>
        <option value="soz">Sözel (SÖZ)</option><option value="dil">Dil (DİL)</option><option value="tyt">TYT (Önlisans)</option></select></div>
    <div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">Yerleştirme Puanın</label>
      <input id="sPuan" type="text" inputmode="decimal" placeholder="örn. 480,50" style="width:100%;margin-top:4px;padding:9px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:15px"></div>
    <div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">— veya — Sıralaman</label>
      <input id="sSiraIn" type="text" inputmode="numeric" placeholder="örn. 45000" style="width:100%;margin-top:4px;padding:9px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:15px"></div>
    <button type="button" class="btn btn-primary" id="sBtn">Hesapla</button>
  </div>
  <div id="sResult" style="margin-top:16px;display:none">
    <div class="res-est" style="background:var(--bg-soft);text-align:center;padding:16px">
      <div class="re-label">Tahmini Başarı Sıralaman</div>
      <div class="re-value" id="sSira" style="font-size:30px">—</div>
      <div id="sNote" style="font-size:12px;color:var(--fg-faded);margin-top:4px"></div>
    </div>
    <a id="sBolum" class="btn btn-primary" style="display:block;text-align:center;margin-top:12px;text-decoration:none">Bu sırayla gidebileceğim bölümler →</a>
  </div>
</div>
<details style="margin-bottom:18px">
  <summary style="cursor:pointer;font-weight:700;color:var(--accent)">Puanını bilmiyor musun? Net'ten kaba puan tahmini al</summary>
  <div class="calc-card" style="margin-top:10px">
    <div class="calc-hint" style="margin-bottom:12px">Denemendeki <b>toplam</b> TYT ve AYT netini gir; sana kaba bir yerleştirme puanı tahmini hesaplar (üstteki kutuya yazılır).</div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;align-items:end">
      <div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">TYT Net (/120)</label>
        <input id="nTyt" type="number" min="0" max="120" step="0.25" inputmode="decimal" placeholder="0" style="width:100%;margin-top:4px;padding:8px;border:1px solid var(--border);border-radius:8px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit"></div>
      <div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">AYT Net (/80)</label>
        <input id="nAyt" type="number" min="0" max="80" step="0.25" inputmode="decimal" placeholder="0" style="width:100%;margin-top:4px;padding:8px;border:1px solid var(--border);border-radius:8px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit"></div>
      <div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">Diploma (50-100)</label>
        <input id="nDip" type="number" min="50" max="100" step="0.01" inputmode="decimal" placeholder="opsiyonel" style="width:100%;margin-top:4px;padding:8px;border:1px solid var(--border);border-radius:8px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit"></div>
      <button type="button" class="btn btn-ghost" id="nBtn">Kaba Puan Tahmini</button>
    </div>
    <div id="nOut" style="margin-top:10px;font-size:13px;color:var(--accent);font-weight:700"></div>
  </div>
</details>
<div class="notice"><b>Nasıl çalışır?</b> Tahmini sıralama, 2025 yılında <b>gerçek</b> yerleşen adayların (taban puan ↔ başarı sırası) verisinden
enterpolasyonla bulunur — bu kısım veriye dayalıdır. Net'ten puan tahmini ise ÖSYM'nin standart puan sistemi nedeniyle
<b>çok kabadır</b>; mümkünse denemenizin/ÖSYM'nin verdiği yerleştirme puanını girin. 2026 sıralamaları kontenjan ve aday
sayısına göre değişebilir.</div>
""" + r"""<script nonce="__NONCE__">
(function(){
  var SV=window.SV||{}, DATA=null;
  function el(i){return document.getElementById(i);}
  var PTL={say:'Sayısal',ea:'Eşit Ağırlık',soz:'Sözel',dil:'Dil',tyt:'TYT'};
  fetch('/veri/puan_sira.json').then(function(r){return r.json();}).then(function(j){DATA=j;}).catch(function(){});
  function pnum(s){s=(s||'').replace(/\./g,'').replace(',','.').replace(/[^0-9.]/g,'');return parseFloat(s);}
  function run(){
    if(!DATA){el('sNote').textContent='Veri yükleniyor, tekrar deneyin.';return;}
    var pt=el('sPt').value, curve=DATA[pt]||[];
    var p=pnum(el('sPuan').value), sIn=parseInt((el('sSiraIn').value||'').replace(/\D/g,''),10);
    var sira=null, note='';
    if(p>0){ sira=SV.estSira?SV.estSira(curve,p):null; note=PTL[pt]+' · puan '+p.toLocaleString('tr-TR')+' → tahmini sıra';
      var top=curve.length?curve[curve.length-1][0]:0, low=curve.length?curve[0][0]:0;
      if(p>=top)note='En yüksek puan aralığında — ilk sıralarda.'; else if(p<=low)note='Veri aralığının altında — sıralama daha geride olabilir.';
    } else if(sIn>0){ sira=sIn; var ep=SV.estPuan?SV.estPuan(curve,sIn):null;
      note=ep? (PTL[pt]+' · '+sIn.toLocaleString('tr-TR')+'. sıra ≈ '+ep.toLocaleString('tr-TR')+' puan'):(PTL[pt]+' · sıralamana göre');
    } else { el('sResult').style.display='none'; return; }
    el('sResult').style.display='block';
    if(sira==null){el('sSira').textContent='—';el('sNote').textContent='Bu puan türü için veri yok.';el('sBolum').style.display='none';return;}
    el('sSira').textContent='~ '+sira.toLocaleString('tr-TR');
    el('sNote').textContent=note;
    el('sBolum').style.display='block';
    el('sBolum').setAttribute('href','/tercih-robotu.html?pt='+pt+'&sira='+sira);
  }
  el('sBtn').addEventListener('click',run);
  el('sPuan').addEventListener('keydown',function(e){if(e.key==='Enter')run();});
  el('sSiraIn').addEventListener('keydown',function(e){if(e.key==='Enter')run();});
  el('sPuan').addEventListener('input',function(){if(el('sPuan').value)el('sSiraIn').value='';});
  el('sSiraIn').addEventListener('input',function(){if(el('sSiraIn').value)el('sPuan').value='';});
  el('sPt').addEventListener('change',function(){if(el('sPuan').value)run();});
  // net → kaba puan
  el('nBtn').addEventListener('click',function(){
    var tyt=parseFloat(el('nTyt').value)||0, ayt=parseFloat(el('nAyt').value)||0, dip=parseFloat(el('nDip').value)||0;
    tyt=Math.max(0,Math.min(120,tyt)); ayt=Math.max(0,Math.min(80,ayt));
    var obp=(dip>=50&&dip<=100)?Math.min(dip*5*0.12,60):0;
    var puan=100+(tyt/120)*190+(ayt/80)*190+obp;
    puan=Math.round(puan*100)/100;
    el('sPuan').value=puan.toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2});
    el('nOut').textContent='Kaba tahmini puan: '+puan.toLocaleString('tr-TR')+' (yukarıda hesaplandı)';
    run();
  });
})();
</script>"""
    return base("yks-siralama-hesaplama.html", "2026 YKS Sıralama Hesaplama — Puanına Göre Tahmini Başarı Sırası | SınavVeri",
                "2026 YKS sıralama hesaplama: yerleştirme puanını gir, 2025 YÖK Atlas verisine göre tahmini başarı sıralamanı ve gidebileceğin bölümleri anında gör.",
                body, extra_ld=[breadcrumb_ld([("Ana Sayfa", "index.html"), ("Puan Hesaplama", "puan-hesaplama.html"), ("YKS Sıralama", None)])])


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
# Sınav → (taban puanları, tercih robotu, puan hesaplama) sayfaları. None = o sınavda yok.
EXAM_TOOLS = {
    "YKS": ("universite-taban-puanlari.html", "tercih-robotu.html", "yks-puan-hesaplama.html"),
    "LGS": ("lise-taban-puanlari.html", "lgs-tercih-robotu.html", "lgs-puan-hesaplama.html"),
    "KPSS": ("kpss-atama-taban-puanlari.html", "kpss-tercih-robotu.html", "kpss-puan-hesaplama.html"),
    "DGS": ("dgs-taban-puanlari.html", "dgs-tercih-robotu.html", "dgs-puan-hesaplama.html"),
    "TUS": ("tus-taban-puanlari.html", "tus-tercih-robotu.html", None),
    "DUS": ("dus-taban-puanlari.html", "dus-tercih-robotu.html", None),
    "ALES": (None, None, "ales-puan-hesaplama.html"),
}


def _exam_tool_cards(exam):
    """Sınav sayfasının en üstündeki Taban / Robot / Hesaplama kartları (yan yana)."""
    taban, robot, calc = EXAM_TOOLS.get(exam, (None, None, None))
    items = [
        (taban, "📊", "Taban Puanları", "Kurum/bölüm taban puanları"),
        (robot, "🎯", "Tercih Robotu", "Puanına göre yerini bul"),
        (calc, "🧮", "Puan Hesaplama", "Net ve puan hesapla"),
    ]
    cards = "".join(
        f'<a class="tool-btn" href="/{h}"><span class="tb-icon">{i}</span>'
        f'<span class="tb-text"><b>{exam} {t}</b><span>{s}</span></span></a>'
        for h, i, t, s in items if h)
    return f'<div class="tool-row" style="margin:0 0 22px">{cards}</div>' if cards else ""


import re as _re


def _strip_html(s):
    return _re.sub(r"\s+", " ", _re.sub(r"<[^>]+>", "", s)).strip()


def guide(slug, exam, title_full, icon, calc_slug, intro, sections, has_calc=True):
    sec_html = ""
    faqs = []
    for h, paras in sections:
        sec_html += f"<h2>{h}</h2>"
        ans_parts = []
        for p in paras:
            if isinstance(p, tuple):
                if p[0] == "ul":
                    sec_html += "<ul>" + "".join(f"<li>{x}</li>" for x in p[1]) + "</ul>"
                    ans_parts.append("; ".join(_strip_html(x) for x in p[1]))
                elif p[0] == "ol":
                    sec_html += "<ol>" + "".join(f"<li>{x}</li>" for x in p[1]) + "</ol>"
                    ans_parts.append("; ".join(_strip_html(x) for x in p[1]))
            else:
                sec_html += f"<p>{p}</p>"
                ans_parts.append(_strip_html(p))
        q = h if h.endswith("?") else h
        ans = " ".join(x for x in ans_parts if x)
        if ans:
            faqs.append((q, ans))
    body = f"""
<div class="crumb"><a href="index.html">Ana Sayfa</a> / {exam}</div>
<div class="hero" style="padding:30px 28px">
  <h1>{icon} {exam} — {title_full}</h1>
  <p>{intro}</p>
</div>
{_exam_tool_cards(exam)}
<div class="prose">
{sec_html}
</div>
<div class="notice" style="max-width:880px"><b>Bilgi:</b> Bu sayfa bilgilendirme amaçlıdır. Başvuru koşulları ve güncel kurallar için
resmî kaynak <a href="https://www.osym.gov.tr" target="_blank" rel="noopener">ÖSYM</a>/<a href="https://www.meb.gov.tr" target="_blank" rel="noopener">MEB</a> esas alınmalıdır.</div>
"""
    extra_ld = [breadcrumb_ld([("Ana Sayfa", "index.html"), (f"{exam} Rehberi", None)])]
    if faqs:
        extra_ld.append({"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]})
    return base(slug, f"{exam} Nedir? {title_full} Rehberi 2026 | SınavVeri",
                intro[:155], body, extra_ld=extra_ld)


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
            ("2026 LGS Tarihleri (MEB resmî kılavuzu)", [
                ("ul", ["Başvuru: 23 Mart – 10 Nisan 2026 (e-Okul üzerinden)", "Sınav giriş belgesi: 3 Haziran 2026",
                        "Sınav: 14 Haziran 2026 (Pazar)", "Sonuç: Haziran 2026 sonu"]),
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
                "Yılda iki ana dönem (İlkbahar/Sonbahar) yapılır; ayrıca bilgisayar tabanlı <strong>e-YDS</strong> ile yıl içinde ek dönemler açılır.",
            ]),
            ("2026 YDS Tarihleri (ÖSYM)", [
                ("ul", ["<strong>YDS/1 (İlkbahar):</strong> 5 Nisan 2026 — başvuru 18–26 Şubat (geç: 4 Mart), sonuç 28 Nisan 2026",
                        "<strong>YDS/2 (Sonbahar):</strong> 22 Kasım 2026 — başvuru 30 Eylül–8 Ekim (geç: 14 Ekim), sonuç 10 Aralık 2026",
                        "e-YDS: yıl içinde 12 ayrı dönem (İngilizce ve diğer diller) ÖSYM e-sınav merkezlerinde"]),
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
            ("2026 YÖKDİL Tarihleri (ÖSYM)", [
                ("ul", ["<strong>YÖKDİL/1:</strong> 8 Mart 2026 — başvuru 21–29 Ocak (geç: 4 Şubat), sonuç 18 Mart 2026",
                        "<strong>YÖKDİL/2:</strong> 9 Ağustos 2026 — başvuru 16–24 Haziran (geç: 30 Haziran), sonuç 26 Ağustos 2026",
                        "Ayrıca e-YÖKDİL (elektronik) dönemleri yıl içinde açılır."]),
                "Kesin başvuru tarihleri her dönemin <strong>kılavuzunda</strong> duyurulur.",
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
            ("2026 MSÜ Tarihleri (ÖSYM)", [
                ("ul", ["Başvuru: 5 – 29 Ocak 2026 (geç başvuru: 3 Şubat)", "Sınav: 1 Mart 2026", "Sonuç: 24 Mart 2026"]),
                "Sınav sonrası fizikî yeterlilik ve mülakat aşamaları MSÜ tarafından ayrıca duyurulur.",
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
            ("2026 YDUS Tarihleri (ÖSYM)", [
                ("ul", ["Başvuru: 13 – 23 Mart 2026 (geç başvuru: 2 Nisan)", "Sınav: 2 Mayıs 2026", "Sonuç: 4 Haziran 2026"]),
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
            ("2026 STS Tarihleri (ÖSYM)", [
                "<strong>Tıp Doktorluğu:</strong>",
                ("ul", ["1. Dönem: 15 Mart 2026 (sonuç 15 Nisan)", "2. Dönem: 23 Ağustos 2026 (sonuç 17 Eylül)"]),
                "<strong>Diş Hekimliği:</strong>",
                ("ul", ["1. Dönem: 26 Nisan 2026 (sonuç 22 Mayıs)", "2. Dönem: 1 Kasım 2026 (sonuç 26 Kasım)"]),
                "<strong>Eczacılık:</strong> 7 Kasım 2026 · <strong>Öğretmenlik:</strong> 13 Haziran 2026.",
                "Başvuru tarihleri her dönemin kılavuzunda açıklanır; denklik baraj puanı YÖK/ÖSYM tarafından belirlenir.",
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
                             r.get("kont"), r.get("tp"), r.get("sira"), r.get("yer"),
                             hist_taban(r, 2024), hist_taban(r, 2023)])
    for pt, rows in buckets.items():
        rows.sort(key=lambda x: (x[11] is None, x[11] or 0))
        path = veri / f"{fname[pt]}.json"
        path.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"  [veri] {fname[pt]}.json  {len(rows)} kayıt, {path.stat().st_size//1024} KB")


def write_puan_sira(programs):
    """Gerçek (taban puan, başarı sırası) çiftlerinden puan→sıralama eğrisi üretir.
    Her puan türü için monoton (puan↑ → sıra↓), ~200 çapa noktasına indirgenmiş tablo.
    İstemci bu eğride enterpolasyon yaparak verilen puanın tahmini sırasını bulur."""
    from collections import defaultdict
    fname = {"SAY": "say", "EA": "ea", "SÖZ": "soz", "DİL": "dil", "TYT": "tyt"}
    pairs = defaultdict(list)
    for r in programs:
        pt = r.get("p"); tp = r.get("tp"); s = r.get("sira")
        if pt in fname and tp and s:
            pairs[pt].append((float(tp), int(s)))
    out = {}
    for pt, key in fname.items():
        pr = sorted(pairs.get(pt, []), key=lambda x: x[0])  # puana göre artan
        if len(pr) < 5:
            out[key] = []
            continue
        # ~200 çapa: puana göre eşit aralıklı örnekle, her noktada o puana en yakın sıra
        # ve monotonluğu zorla (puan arttıkça sıra azalır → running min)
        N = 200
        step = max(1, len(pr) // N)
        anc = pr[::step]
        if anc[-1] != pr[-1]:
            anc.append(pr[-1])
        best = None
        curve = []
        for p, s in anc:
            best = s if best is None else min(best, s)  # puan↑ iken sıra non-increasing
            curve.append([round(p, 2), best])
        # aynı puanlı tekrarları sadeleştir (son değer kalsın)
        dedup = {}
        for p, s in curve:
            dedup[p] = s
        out[key] = [[p, dedup[p]] for p in sorted(dedup)]
    (ROOT / "veri").mkdir(exist_ok=True)
    (ROOT / "veri" / "puan_sira.json").write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  [veri] puan_sira.json  " + ", ".join(f"{k}:{len(v)}" for k, v in out.items()))


# ───────────────────────── TABAN PUANLARI (interaktif arama) ─────────────────────────
SEARCH_JS = r"""<script nonce="__NONCE__">
(function(){
  var IDX={k:0,u:1,b:2,g:3,il:4,t:5,o:6,dil:7,bs:8,kont:9,tp:10,sira:11,yer:12,t24:13,t23:14};
  var TUR={D:'Devlet',V:'Vakıf',K:'KKTC',DK:'Devlet (KKTC Kampüs)',DU:'Devlet (Ücretli)',DKU:'Devlet (KKTC Uyruklu)',Y:'Diğer','?':'—'};
  var PTL={say:'Sayısal',ea:'Eşit Ağırlık',soz:'Sözel',dil:'Dil',tyt:'TYT (Önlisans)'};
  var SV=window.SV||{};
  function doluluk(r){var k=r[IDX.kont],y=r[IDX.yer];if(!k||y==null)return '—';var p=Math.round(y/k*100);var c=p>=100?'tag-lgs':(p>=70?'tag-kpss':'tag-other');return '<span class="tag '+c+'">%'+p+'</span>';}
  var data=[], shown=0, PAGE=50, cache={};
  var nf=function(n){return n==null?'—':n.toLocaleString('tr-TR');};
  var pf=function(n){return n==null?'—':n.toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2});};
  function el(id){return document.getElementById(id);}
  function rkey(r){return (r[IDX.b]||'')+'|'+(r[IDX.u]||'')+'|'+(r[IDX.il]||'');}
  var cmp={}, byKey={};
  function load(pt){
    if(cache[pt]){data=cache[pt];afterLoad();return;}
    if(SV.skel)SV.skel('tbody',8,7);
    el('status').textContent='Veriler yükleniyor…';
    fetch('/veri/'+pt+'.json').then(function(r){return r.json();}).then(function(j){
      cache[pt]=j; data=j; afterLoad();
    }).catch(function(){el('status').textContent='Veri yüklenemedi. Lütfen tekrar deneyin.';});
  }
  function bdil(s){ s=s||''; var i=s.indexOf(' ('); return i>0?s.slice(0,i):s; }
  function fillIl(){
    var set={}; data.forEach(function(r){if(r[IDX.il])set[r[IDX.il]]=1;});
    var ils=Object.keys(set).sort(function(a,b){return a.localeCompare(b,'tr');});
    var cur=el('fIl').value; var sel=el('fIl'); sel.innerHTML='<option value="">Tüm iller</option>';
    ils.forEach(function(i){var o=document.createElement('option');o.value=i;o.textContent=i;if(i===cur)o.selected=true;sel.appendChild(o);});
  }
  function fillDil(){
    var sel=el('fDil');if(!sel)return;var cur=sel.value;
    var cnt={};data.forEach(function(r){var b=bdil(r[IDX.dil]);if(b)cnt[b]=(cnt[b]||0)+1;});
    var ks=Object.keys(cnt).sort(function(a,b){return cnt[b]-cnt[a]||a.localeCompare(b,'tr');});
    sel.innerHTML='<option value="">Tüm öğrenim dilleri</option>';
    ks.forEach(function(k){var o=document.createElement('option');o.value=k;o.textContent=k+' ('+cnt[k]+')';if(k===cur)o.selected=true;sel.appendChild(o);});
  }
  function applyQS(){
    var qs=SV.qsGet?SV.qsGet():{};
    if(qs.q!=null)el('fQ').value=qs.q;
    if(qs.tur!=null)el('fTur').value=qs.tur;
    if(qs.burs==='1'&&el('fBurs'))el('fBurs').checked=true;
    if(qs.dol==='1'&&el('fDol'))el('fDol').checked=true;
    if(qs.dil!=null&&el('fDil')){var s=el('fDil');var o=document.createElement('option');o.value=qs.dil;o.textContent=qs.dil;o.selected=true;s.appendChild(o);}
    if(qs.il!=null){var si=el('fIl');var oi=document.createElement('option');oi.value=qs.il;oi.textContent=qs.il;oi.selected=true;si.appendChild(oi);}
  }
  function syncQS(){
    var o={pt:el('ptSel').value};var q=el('fQ').value.trim();if(q)o.q=q;
    if(el('fIl').value)o.il=el('fIl').value; if(el('fTur').value)o.tur=el('fTur').value;
    if(el('fDil')&&el('fDil').value)o.dil=el('fDil').value;
    if(el('fBurs')&&el('fBurs').checked)o.burs='1';
    if(el('fDol')&&el('fDol').checked)o.dol='1';
    if(SV.qsSet)SV.qsSet(o); drawChips();
  }
  function drawChips(){
    if(!SV.chips)return;var items=[{key:'pt',label:'Puan: '+(PTL[el('ptSel').value]||el('ptSel').value)}];
    var q=el('fQ').value.trim();if(q)items.push({key:'q',label:'“'+q+'”'});
    if(el('fIl').value)items.push({key:'il',label:'İl: '+el('fIl').value});
    if(el('fTur').value)items.push({key:'tur',label:'Tür: '+(TUR[el('fTur').value]||el('fTur').value)});
    if(el('fDil')&&el('fDil').value)items.push({key:'dil',label:'Dil: '+el('fDil').value});
    if(el('fBurs')&&el('fBurs').checked)items.push({key:'burs',label:'Sadece burslu'});
    if(el('fDol')&&el('fDol').checked)items.push({key:'dol',label:'Kontenjanı dolmamış'});
    SV.chips('chips',items,function(key){
      if(key==='pt')return;
      if(key==='__all__'){el('fQ').value='';el('fIl').value='';el('fTur').value='';if(el('fDil'))el('fDil').value='';if(el('fBurs'))el('fBurs').checked=false;if(el('fDol'))el('fDol').checked=false;}
      else if(key==='q')el('fQ').value='';else if(key==='il')el('fIl').value='';
      else if(key==='tur')el('fTur').value='';else if(key==='dil'&&el('fDil'))el('fDil').value='';
      else if(key==='burs'&&el('fBurs'))el('fBurs').checked=false;
      else if(key==='dol'&&el('fDol'))el('fDol').checked=false;
      render(true);
    });
  }
  function afterLoad(){fillIl();fillDil();render();}
  function filtered(){
    var q=(el('fQ').value||'').toLocaleLowerCase('tr').trim();
    var il=el('fIl').value, tur=el('fTur').value, dilSel=el('fDil')?el('fDil').value:'';
    var bursOnly=el('fBurs')&&el('fBurs').checked;
    var dolOnly=el('fDol')&&el('fDol').checked;
    var out=data.filter(function(r){
      if(il&&r[IDX.il]!==il)return false;
      if(tur&&r[IDX.t]!==tur)return false;
      if(dilSel&&bdil(r[IDX.dil])!==dilSel)return false;
      if(bursOnly&&!/Burslu/i.test(r[IDX.bs]||''))return false;
      if(dolOnly){var k=r[IDX.kont],y=r[IDX.yer];if(!(k!=null&&y!=null&&y<k))return false;}
      if(q){
        var hay=(r[IDX.b]||'')+' '+(r[IDX.u]||'')+' '+(r[IDX.g]||'')+' '+(r[IDX.il]||'');
        if(SV.tokMatch?!SV.tokMatch(hay,q):hay.toLocaleLowerCase('tr').indexOf(q)<0)return false;
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
    if(reset!==false){shown=0;syncQS();}
    var rows=applySort(filtered());
    el('status').textContent=rows.length.toLocaleString('tr-TR')+' program bulundu';
    if(!rows.length){if(SV.empty)SV.empty('tbody',8);el('moreWrap').style.display='none';return;}
    shown=Math.min(shown+PAGE,rows.length); if(shown===0&&rows.length)shown=Math.min(PAGE,rows.length);
    var tb=el('tbody'); tb.innerHTML=''; byKey={};
    rows.slice(0,shown||PAGE).forEach(function(r){
      var k=rkey(r); byKey[k]=r;
      var tr=document.createElement('tr');
      var kc=nf(r[IDX.kont]),kk=r[IDX.kont],yy=r[IDX.yer];
      if(kk!=null&&yy!=null&&yy<kk)kc=nf(kk)+' <small style="color:var(--fg-faded)">/ '+nf(yy)+' yerleşti</small>';
      tr.innerHTML='<td><strong>'+(r[IDX.b]||'')+'</strong><br><small>'+(r[IDX.u]||'')+'</small></td>'+
        '<td>'+(r[IDX.il]||'—')+'</td>'+
        '<td><span class="tag tag-other">'+(TUR[r[IDX.t]]||'—')+'</span></td>'+
        '<td>'+kc+'</td>'+
        '<td><strong>'+pf(r[IDX.tp])+'</strong>'+(SV.spark?SV.spark([r[IDX.t23],r[IDX.t24],r[IDX.tp]]):'')+'</td>'+
        '<td>'+nf(r[IDX.sira])+'</td>'+
        '<td>'+doluluk(r)+'</td>'+
        '<td style="text-align:center"><input type="checkbox" class="cmp-cb" aria-label="Karşılaştır" data-k="'+k.replace(/"/g,'&quot;')+'"'+(cmp[k]?' checked':'')+'></td>';
      tb.appendChild(tr);
    });
    el('moreWrap').style.display = (shown<rows.length)?'block':'none';
    el('moreInfo').textContent=shown+' / '+rows.length.toLocaleString('tr-TR');
  }
  // ── Karşılaştırma ──
  function cmpCount(){var n=0;for(var k in cmp)if(cmp.hasOwnProperty(k))n++;return n;}
  function updateBar(){
    var n=cmpCount();var bar=el('cmpBar');if(!bar)return;
    bar.classList.toggle('show',n>0);
    el('cmpBtn').textContent='Karşılaştır ('+n+')';
  }
  function buildPanel(){
    var panel=el('cmpPanel');var keys=Object.keys(cmp);if(!keys.length){panel.classList.remove('open');return;}
    var rowsDef=[['İl',IDX.il],['Tür',IDX.t],['Kontenjan',IDX.kont],['Taban Puan',IDX.tp],['Başarı Sırası',IDX.sira]];
    var h='<div class="cmp-grid">';
    keys.forEach(function(k){var r=cmp[k];
      h+='<div class="cmp-col"><h4>'+(r[IDX.b]||'')+'</h4><div class="cc-sub">'+(r[IDX.u]||'')+'</div><dl>';
      rowsDef.forEach(function(d){var v=r[d[1]];var txt;
        if(d[1]===IDX.t)txt=TUR[v]||'—';else if(d[1]===IDX.tp)txt=pf(v);else txt=nf(v);
        h+='<dt>'+d[0]+'</dt><dd>'+txt+'</dd>';});
      h+='<dt>Doluluk</dt><dd>'+doluluk(r)+'</dd></dl></div>';
    });
    h+='</div>';panel.innerHTML=h;panel.classList.add('open');
    try{panel.scrollIntoView({behavior:'smooth',block:'center'});}catch(e){}
  }
  el('tbody').addEventListener('change',function(e){
    var cb=e.target;if(!cb.classList||!cb.classList.contains('cmp-cb'))return;
    var k=cb.getAttribute('data-k');
    if(cb.checked){ if(cmpCount()>=3){cb.checked=false;return;} cmp[k]=byKey[k]; }
    else { delete cmp[k]; }
    updateBar(); if(el('cmpPanel').classList.contains('open'))buildPanel();
  });
  el('cmpBtn').addEventListener('click',function(){
    var p=el('cmpPanel');if(p.classList.contains('open'))p.classList.remove('open');else buildPanel();
  });
  el('cmpClear').addEventListener('click',function(){
    cmp={};el('cmpPanel').classList.remove('open');updateBar();
    document.querySelectorAll('.cmp-cb').forEach(function(c){c.checked=false;});
  });
  ['fQ','fIl','fTur','fDil'].forEach(function(id){var e=el(id);if(e)e.addEventListener('input',function(){render(true);});});
  if(el('fBurs'))el('fBurs').addEventListener('change',function(){render(true);});
  if(el('fDol'))el('fDol').addEventListener('change',function(){render(true);});
  el('ptSel').addEventListener('change',function(){load(this.value);});
  el('moreBtn').addEventListener('click',function(){render(false);});
  (function(){var ths=document.querySelectorAll('.data-table thead th');ths.forEach(function(th,i){
    if(th.hasAttribute('data-nosort'))return;
    th.style.cursor='pointer';th.title='Sıralamak için tıklayın';
    th.addEventListener('click',function(){sortD=(sortI===i)?-sortD:1;sortI=i;
      ths.forEach(function(o){var a=o.querySelector('.s-arrow');if(a)a.remove();});
      var ar=document.createElement('span');ar.className='s-arrow';ar.textContent=sortD>0?' ▲':' ▼';th.appendChild(ar);render(true);});});})();
  applyQS();
  var qs0=SV.qsGet?SV.qsGet():{}; if(qs0.pt&&PTL[qs0.pt])el('ptSel').value=qs0.pt;
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
      <option value="">Tüm türler</option><option value="D">Devlet</option><option value="V">Vakıf</option><option value="K">KKTC</option><option value="DK">Devlet (KKTC Kampüs)</option><option value="DU">Devlet (Ücretli)</option><option value="DKU">Devlet (KKTC Uyruklu)</option>
    </select>
    <select id="fDil" class="btn btn-ghost" style="text-align:left"><option value="">Tüm öğrenim dilleri</option></select>
    <label style="display:flex;align-items:center;gap:6px;font-size:13px;color:var(--fg-muted)"><input type="checkbox" id="fBurs"> Sadece burslu</label>
    <label style="display:flex;align-items:center;gap:6px;font-size:13px;color:var(--fg-muted)"><input type="checkbox" id="fDol"> Sadece kontenjanı dolmamışlar</label>
  </div>
  <div class="filter-chips" id="chips" style="display:none"></div>
  <div id="status" style="margin-top:12px;font-size:13px;color:var(--accent);font-weight:700">Yükleniyor…</div>
</div>

<div class="data-table-wrap">
<table class="data-table cardify" data-live="1">
<thead><tr><th>Program / Üniversite</th><th>İl</th><th>Tür</th><th>Kont. / Yerleşen</th><th>Taban Puan</th><th>Başarı Sırası</th><th>Doluluk</th><th data-nosort title="Karşılaştırmak için seç">Kıyas</th></tr></thead>
<tbody id="tbody"></tbody>
</table>
</div>
<div class="fav-panel" id="cmpPanel"></div>
<div class="cmp-bar" id="cmpBar">
  <button type="button" class="fav-toggle" id="cmpBtn">Karşılaştır (0)</button>
  <button type="button" class="fchip-clear" id="cmpClear" style="margin-left:8px">Seçimi temizle</button>
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
                body, extra_ld=[breadcrumb_ld([("Ana Sayfa", "index.html"), ("Taban Puanları", "taban-puanlari.html"), ("Üniversite", None)])])


# ───────────────────────── TERCİH ROBOTU ─────────────────────────
ROBOT_JS = r"""<script nonce="__NONCE__">
(function(){
  var IDX={k:0,u:1,b:2,g:3,il:4,t:5,o:6,dil:7,bs:8,kont:9,tp:10,sira:11};
  var TUR={D:'Devlet',V:'Vakıf',K:'KKTC',DK:'Devlet (KKTC Kampüs)',DU:'Devlet (Ücretli)',DKU:'Devlet (KKTC Uyruklu)',Y:'Diğer','?':'—'};
  var PTL={say:'Sayısal',ea:'Eşit Ağırlık',soz:'Sözel',dil:'Dil',tyt:'TYT (Önlisans)'};
  var SV=window.SV||{};
  var data=[],cache={},byId={};
  var fav=SV.initFav?SV.initFav({ns:'yks',barId:'favBar',panelId:'favPanel',btnId:'favBtn'}):null;
  var nf=function(n){return n==null?'—':n.toLocaleString('tr-TR');};
  var pf=function(n){return n==null?'—':n.toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2});};
  function el(id){return document.getElementById(id);}
  function rkey(r){return (r[IDX.b]||'')+'|'+(r[IDX.u]||'');}
  function bdil(s){ s=s||''; var i=s.indexOf(' ('); return i>0?s.slice(0,i):s; }
  function load(pt,cb){
    if(cache[pt]){data=cache[pt];cb();return;}
    if(SV.skel)SV.skel('rbody',7,6);
    el('rstatus').textContent='Veriler yükleniyor…';
    fetch('/veri/'+pt+'.json').then(function(r){return r.json();}).then(function(j){cache[pt]=j;data=j;cb();})
      .catch(function(){el('rstatus').textContent='Veri yüklenemedi.';});
  }
  function syncQS(){
    var o={pt:el('rPt').value};var s=el('rSira').value.replace(/\D/g,'');if(s)o.sira=s;
    if(el('rIl').value)o.il=el('rIl').value;if(el('rTur').value)o.tur=el('rTur').value;
    if(el('rDil')&&el('rDil').value)o.dil=el('rDil').value;
    if(SV.qsSet)SV.qsSet(o);drawChips();
  }
  function drawChips(){
    if(!SV.chips)return;var items=[{key:'pt',label:'Puan: '+(PTL[el('rPt').value]||el('rPt').value)}];
    var s=el('rSira').value.replace(/\D/g,'');if(s)items.push({key:'sira',label:'Sıra: '+Number(s).toLocaleString('tr-TR')});
    if(el('rIl').value)items.push({key:'il',label:'İl: '+el('rIl').value});
    if(el('rTur').value)items.push({key:'tur',label:'Tür: '+(TUR[el('rTur').value]||el('rTur').value)});
    if(el('rDil')&&el('rDil').value)items.push({key:'dil',label:'Dil: '+el('rDil').value});
    SV.chips('chips',items,function(key){
      if(key==='pt')return;
      if(key==='__all__'){el('rSira').value='';el('rIl').value='';el('rTur').value='';if(el('rDil'))el('rDil').value='';}
      else if(key==='sira')el('rSira').value='';else if(key==='il')el('rIl').value='';else if(key==='tur')el('rTur').value='';else if(key==='dil'&&el('rDil'))el('rDil').value='';
      run();
    });
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
    var tb=el('rbody'); tb.innerHTML=''; byId={};
    if(!lastReach.length){if(SV.empty)SV.empty('rbody',7,'Bu sıralama ve filtrelerle yerleşebileceğin program bulunamadı. Filtreyi gevşetmeyi deneyin.');el('rhint').style.display='none';return;}
    lastReach.slice(0,200).forEach(function(r){
      var margin=r[IDX.sira]-lastSira;
      var safe = margin>lastSira*0.25 ? '<span class="tag tag-lgs">Rahat</span>' : (margin>lastSira*0.05 ? '<span class="tag tag-kpss">Olası</span>' : '<span class="tag tag-other">Sınırda</span>');
      var k=rkey(r); byId[k]={id:k,name:r[IDX.b]||'',sub:r[IDX.u]||'',meta:'taban sıra '+nf(r[IDX.sira])};
      var on=fav&&fav.has(k);
      var tr=document.createElement('tr');
      tr.innerHTML='<td><strong>'+(r[IDX.b]||'')+'</strong><br><small>'+(r[IDX.u]||'')+'</small></td>'+
        '<td>'+(r[IDX.il]||'—')+'</td>'+'<td>'+(TUR[r[IDX.t]]||'—')+'</td>'+
        '<td><strong>'+pf(r[IDX.tp])+'</strong></td>'+'<td>'+nf(r[IDX.sira])+'</td>'+'<td>'+safe+'</td>'+
        '<td style="text-align:center"><button type="button" class="fav-star'+(on?' on':'')+'" data-fid="'+k.replace(/"/g,'&quot;')+'" aria-label="Tercih listeme ekle">'+(on?'★':'☆')+'</button></td>';
      tb.appendChild(tr);
    });
    el('rhint').style.display = lastReach.length>200 ? 'block':'none';
    el('rhint').textContent='İlk 200 program gösteriliyor. Sütun başlığına tıklayarak sıralayın; il/tür ile daraltın.';
  }
  function run(){
    var pt=el('rPt').value;
    load(pt,function(){
      syncQS();
      var sira=parseInt((el('rSira').value||'').replace(/\D/g,''),10);
      if(!sira||sira<1){el('rstatus').textContent='Lütfen geçerli bir başarı sıranızı girin.';el('rbody').innerHTML='';return;}
      var il=el('rIl').value, tur=el('rTur').value, dilSel=el('rDil')?el('rDil').value:'';
      lastSira=sira;
      lastReach=data.filter(function(r){
        if(r[IDX.sira]==null)return false;
        if(il&&r[IDX.il]!==il)return false;
        if(tur&&r[IDX.t]!==tur)return false;
        if(dilSel&&bdil(r[IDX.dil])!==dilSel)return false;
        return r[IDX.sira]>=sira;
      });
      sortReach();
      el('rstatus').innerHTML='<b>'+lastReach.length.toLocaleString('tr-TR')+'</b> programa yerleşebilirsin (sıran: '+sira.toLocaleString('tr-TR')+')';
      draw();
    });
  }
  el('rbody').addEventListener('click',function(e){
    var b=e.target;if(!b.classList||!b.classList.contains('fav-star'))return;
    var k=b.getAttribute('data-fid');if(fav&&byId[k])fav.toggle(byId[k]);
  });
  el('rBtn').addEventListener('click',run);
  el('rSira').addEventListener('keydown',function(e){if(e.key==='Enter')run();});
  el('rPt').addEventListener('change',syncQS);
  (function(){var ths=document.querySelectorAll('.data-table thead th');ths.forEach(function(th,i){
    if(th.hasAttribute('data-nosort'))return;
    th.style.cursor='pointer';th.title='Sıralamak için tıklayın';
    th.addEventListener('click',function(){if(!lastReach.length)return;sortD=(sortI===i)?-sortD:1;sortI=i;
      ths.forEach(function(o){var a=o.querySelector('.s-arrow');if(a)a.remove();});
      var ar=document.createElement('span');ar.className='s-arrow';ar.textContent=sortD>0?' ▲':' ▼';th.appendChild(ar);sortReach();draw();});});})();
  (function(){
    var qs=SV.qsGet?SV.qsGet():{};
    if(qs.pt&&PTL[qs.pt])el('rPt').value=qs.pt;
    if(qs.tur)el('rTur').value=qs.tur;
    if(qs.il){var s=el('rIl');var o=document.createElement('option');o.value=qs.il;o.textContent=qs.il;o.selected=true;s.appendChild(o);}
    if(qs.dil&&el('rDil')){var sd=el('rDil');var od=document.createElement('option');od.value=qs.dil;od.textContent=qs.dil;od.selected=true;sd.appendChild(od);}
    if(qs.sira){el('rSira').value=qs.sira;run();}else{drawChips();}
  })();
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
      <select id="rTur" class="btn btn-ghost" style="text-align:left;width:100%;margin-top:4px"><option value="">Hepsi</option><option value="D">Devlet</option><option value="V">Vakıf</option><option value="K">KKTC</option><option value="DK">Devlet (KKTC Kampüs)</option><option value="DU">Devlet (Ücretli)</option><option value="DKU">Devlet (KKTC Uyruklu)</option></select></div>
    <div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">Öğrenim Dili (ops.)</label>
      <select id="rDil" class="btn btn-ghost" style="text-align:left;width:100%;margin-top:4px"><option value="">Tüm diller</option></select></div>
    <button type="button" class="btn btn-primary" id="rBtn">Programları Göster</button>
  </div>
  <div class="filter-chips" id="chips" style="display:none"></div>
  <div id="rstatus" style="margin-top:14px;font-size:14px;color:var(--accent);font-weight:700"></div>
</div>

<div class="data-table-wrap">
<table class="data-table" data-live="1">
<thead><tr><th>Program / Üniversite</th><th>İl</th><th>Tür</th><th>Taban Puan</th><th>Başarı Sırası</th><th>Şans</th><th data-nosort title="Tercih listene ekle">⭐</th></tr></thead>
<tbody id="rbody"></tbody>
</table>
</div>
<div id="rhint" style="display:none;font-size:12px;color:var(--fg-faded);margin-top:10px;text-align:center"></div>
<div class="fav-panel" id="favPanel"></div>
<div class="fav-bar" id="favBar"><button type="button" class="fav-toggle" id="favBtn">⭐ Tercih Listem (0)</button></div>

<div class="notice"><b>Nasıl çalışır?</b> Başarı sıran, bir programın 2025 taban başarı sırasından <b>daha iyi (küçük)</b> veya eşitse
o programa yerleşebilirsin. "Şans" sütunu güvenlik payını gösterir: <b>Rahat</b> (geniş pay), <b>Olası</b>, <b>Sınırda</b>.
Bu bir tahmindir; 2026 taban puanları kontenjan ve tercih yoğunluğuna göre değişir. Resmî tercih için
<a href="https://www.osym.gov.tr" target="_blank" rel="noopener">ÖSYM</a> kılavuzu esastır.</div>
""" + ROBOT_JS
    # rIl doldurma — robot da fillIl benzeri ister; basitçe SEARCH veri yüklenince doldurulmuyor.
    fill = r"""<script nonce="__NONCE__">
(function(){
  var sel=document.getElementById('rIl'),dsel=document.getElementById('rDil'),ptSel=document.getElementById('rPt');
  function bdil(s){s=s||'';var i=s.indexOf(' (');return i>0?s.slice(0,i):s;}
  function fill(){fetch('/veri/'+ptSel.value+'.json').then(function(r){return r.json();}).then(function(j){
    var set={};j.forEach(function(r){if(r[4])set[r[4]]=1;});
    var ils=Object.keys(set).sort(function(a,b){return a.localeCompare(b,'tr');});
    var cur=sel.value; sel.innerHTML='<option value="">Tüm iller</option>';
    ils.forEach(function(i){var o=document.createElement('option');o.value=i;o.textContent=i;if(i===cur)o.selected=true;sel.appendChild(o);});
    if(dsel){var cnt={};j.forEach(function(r){var b=bdil(r[7]);if(b)cnt[b]=(cnt[b]||0)+1;});
      var ks=Object.keys(cnt).sort(function(a,b){return cnt[b]-cnt[a]||a.localeCompare(b,'tr');});
      var dc=dsel.value; dsel.innerHTML='<option value="">Tüm diller</option>';
      ks.forEach(function(k){var o=document.createElement('option');o.value=k;o.textContent=k+' ('+cnt[k]+')';if(k===dc)o.selected=true;dsel.appendChild(o);});}
  }).catch(function(){});}
  ptSel.addEventListener('change',fill); fill();
})();
</script>"""
    body += fill
    return base("tercih-robotu.html", "2026 YKS Tercih Robotu — Sıralamana Göre Bölüm Bul | SınavVeri",
                "2026 YKS tercih robotu: başarı sıranı gir, 2025 YÖK Atlas yerleştirme verisine göre yerleşebileceğin üniversite programlarını anında gör. Ücretsiz.",
                body, extra_ld=[breadcrumb_ld([("Ana Sayfa", "index.html"), ("Tercih Robotu", None)])])


# ───────────────────────── BÖLÜM (program grubu) SAYFALARI ─────────────────────────
PUAN_ROBOT_JS = r"""<script nonce="__NONCE__">
(function(){
  var CFG=__CFG__, SV=window.SV||{}, NCOL=CFG.show.length+4;
  var data=[],byId={};
  var fav=SV.initFav?SV.initFav({ns:CFG.ns_key||'robot',barId:'favBar',panelId:'favPanel',btnId:'favBtn'}):null;
  function el(id){return document.getElementById(id);}
  var pf=function(n){return n==null?'—':Number(n).toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2});};
  if(SV.skel)SV.skel('rbody',NCOL,6);
  el('rstatus').textContent='Veriler yükleniyor…';
  fetch(CFG.file).then(function(r){return r.json();}).then(function(j){data=j;initFilters();el('rstatus').textContent='';applyQS();})
    .catch(function(){el('rstatus').textContent='Veri yüklenemedi.';});
  function initFilters(){
    CFG.filters.forEach(function(f,n){
      var set={};data.forEach(function(r){if(r[f[0]]!=null&&r[f[0]]!=='')set[r[f[0]]]=1;});
      var vals=Object.keys(set).sort(function(a,b){return a.localeCompare(b,'tr');});
      var sel=el('rf'+n);if(!sel)return;
      vals.forEach(function(v){var o=document.createElement('option');o.value=v;o.textContent=v;sel.appendChild(o);});
    });
  }
  function applyQS(){
    var qs=SV.qsGet?SV.qsGet():{};
    if(qs.puan!=null)el('rPuan').value=qs.puan;
    CFG.filters.forEach(function(f,n){var s=el('rf'+n);if(s&&qs['f'+n]!=null)s.value=qs['f'+n];});
    if(qs.puan){run();}else{drawChips();}
  }
  function syncQS(){
    var o={};var p=el('rPuan').value.trim();if(p)o.puan=p;
    CFG.filters.forEach(function(f,n){var s=el('rf'+n);if(s&&s.value)o['f'+n]=s.value;});
    if(SV.qsSet)SV.qsSet(o);drawChips();
  }
  function drawChips(){
    if(!SV.chips)return;var items=[];var p=el('rPuan').value.trim();
    if(p)items.push({key:'puan',label:'Puan: '+p});
    CFG.filters.forEach(function(f,n){var s=el('rf'+n);if(s&&s.value)items.push({key:'f'+n,label:f[1]+': '+s.value});});
    SV.chips('chips',items,function(key){
      if(key==='__all__'){el('rPuan').value='';CFG.filters.forEach(function(f,n){var s=el('rf'+n);if(s)s.value='';});}
      else if(key==='puan')el('rPuan').value='';
      else CFG.filters.forEach(function(f,n){if('f'+n===key){var s=el('rf'+n);if(s)s.value='';}});
      run();
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
  function rkey(r){return String(r[CFG.nb])+'|'+(CFG.ns!=null?String(r[CFG.ns]):'')+'|'+String(r[CFG.taban]);}
  function draw(){
    var tb=el('rbody');tb.innerHTML='';byId={};
    if(!lastReach.length){if(SV.empty)SV.empty('rbody',NCOL,'Bu puan ve filtrelerle yerleşebileceğin sonuç bulunamadı. Puanı veya filtreleri gözden geçirin.');el('rhint').style.display='none';return;}
    lastReach.slice(0,200).forEach(function(r){
      var m=userP-r[CFG.taban];
      var safe=m>=CFG.t1?'<span class="tag tag-lgs">Rahat</span>':(m>=CFG.t2?'<span class="tag tag-kpss">Olası</span>':'<span class="tag tag-other">Sınırda</span>');
      var name='<td><strong>'+(r[CFG.nb]||'')+'</strong>'+(CFG.ns!=null?'<br><small>'+(r[CFG.ns]||'')+'</small>':'')+'</td>';
      var show='';CFG.show.forEach(function(c){show+='<td>'+(r[c[0]]==null||r[c[0]]===''?'—':r[c[0]])+'</td>';});
      var k=rkey(r);byId[k]={id:k,name:String(r[CFG.nb]||''),sub:(CFG.ns!=null?String(r[CFG.ns]||''):''),meta:'taban '+pf(r[CFG.taban])};
      var on=fav&&fav.has(k);
      var star='<td style="text-align:center"><button type="button" class="fav-star'+(on?' on':'')+'" data-fid="'+k.replace(/"/g,'&quot;')+'" aria-label="Tercih listeme ekle">'+(on?'★':'☆')+'</button></td>';
      var tr=document.createElement('tr');
      tr.innerHTML=name+show+'<td><strong>'+pf(r[CFG.taban])+'</strong></td><td>'+safe+'</td>'+star;
      tb.appendChild(tr);
    });
    el('rhint').style.display=lastReach.length>200?'block':'none';
    el('rhint').textContent='İlk 200 sonuç gösteriliyor. Daha hassas için filtre/sıralama kullanın.';
  }
  function run(){
    syncQS();
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
  el('rbody').addEventListener('click',function(e){
    var b=e.target;if(!b.classList||!b.classList.contains('fav-star'))return;
    var k=b.getAttribute('data-fid');if(fav&&byId[k])fav.toggle(byId[k]);
  });
  el('rBtn').addEventListener('click',run);
  el('rPuan').addEventListener('keydown',function(e){if(e.key==='Enter')run();});
  (function(){
    var ths=document.querySelectorAll('.data-table thead th');
    ths.forEach(function(th,i){
      if(th.hasAttribute('data-nosort'))return;
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
    thead = "<th>" + ("Program" if ns is not None else "Ad") + "</th>" + "".join(f"<th>{l}</th>" for _, l in show) + '<th>Taban</th><th>Şans</th><th data-nosort title="Tercih listene ekle">⭐</th>'
    ns_key = slug.replace("-tercih-robotu.html", "").replace(".html", "")
    cfg = {"file": veri_file, "nb": nb, "ns": ns, "show": [[i, l] for i, l in show],
           "taban": taban, "filters": [[i, l] for i, l in filters], "noun": noun, "t1": t1, "t2": t2, "ns_key": ns_key}
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
  <div class="filter-chips" id="chips" style="display:none"></div>
  <div id="rstatus" style="margin-top:14px;font-size:14px;color:var(--accent);font-weight:700"></div>
</div>
<div class="data-table-wrap">
<table class="data-table" data-live="1"><thead><tr>{thead}</tr></thead><tbody id="rbody"></tbody></table>
</div>
<div id="rhint" style="display:none;font-size:12px;color:var(--fg-faded);margin-top:10px;text-align:center"></div>
<div class="fav-panel" id="favPanel"></div>
<div class="fav-bar" id="favBar"><button type="button" class="fav-toggle" id="favBtn">⭐ Tercih Listem (0)</button></div>
<div class="notice"><b>Nasıl çalışır?</b> Puanın bir programın/kadronun taban puanından <b>yüksek veya eşitse</b> oraya yerleşebilirsin.
"Şans" payı güvenliği gösterir: <b>Rahat</b> (geniş pay), <b>Olası</b>, <b>Sınırda</b>. Bu bir tahmindir; gelecek yıl taban puanları
kontenjan ve tercih yoğunluğuna göre değişir. <b>Kaynak:</b> {kaynak} Resmî tercih için <a href="https://www.osym.gov.tr" target="_blank" rel="noopener">ÖSYM</a> esastır.</div>
{js}
"""
    return base(slug, title, desc, body,
                extra_ld=[breadcrumb_ld([("Ana Sayfa", "index.html"), ("Tercih Robotu", "tercih-robotu.html"), (h1, None)])])


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
        "/veri/liseler.json", 2, None, [(0, "İl"), (1, "İlçe")], 5, [(0, "İl"), (1, "İlçe"), (10, "Yabancı Dil")],
        "liseye", 15, 4,
        "LGS puanını girin ve ilini seçin; o puanla yerleşebileceğin (taban ≤ puanın) liseleri en yüksek tabandan başlayarak listeler. "
        "LGS hesaplama için <a href='/lgs-puan-hesaplama.html'>LGS puan hesaplama</a>.",
        "MEB 2025 LGS yerleştirme verisi.", "LGS Puanın", "örn. 420,5")


def _bdil_py(s):
    s = s or ""
    i = s.find(" (")
    return s[:i] if i > 0 else s


def _pdet_btn(r):
    """Program detayı 'ℹ️' butonu: akademik kadro / akreditasyon / süre / ücret / koşul kodları
    data-attribute olarak; istemci kosul_map ile açıklamayı çözer. Veri yoksa boş döner."""
    kadro = r.get("kadro") or []
    kosul = r.get("kosul") or ""
    akr = r.get("akr") or ""
    sure = r.get("sure")
    ucret = r.get("ucret")
    if not (kosul or any(kadro) or akr or sure):
        return ""
    kd = ",".join(str(x if x else 0) for x in (kadro + [0, 0, 0, 0, 0])[:5])
    attrs = (f' data-kosul="{kosul}" data-kadro="{kd}"'
             + (f' data-akr="{akr}"' if akr else "")
             + (f' data-sure="{sure}"' if sure else "")
             + (f' data-ucret="{ucret}"' if ucret else ""))
    return f'<button type="button" class="pdet" title="Program detayı"{attrs}>ℹ️</button>'


# Detay (bölüm/üniversite) statik tablolarına dil filtresi + karşılaştırma katmanı
DETAIL_BAR = """
<div class="calc-card" style="margin-bottom:14px;padding:13px 16px">
  <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center">
    <span id="dDilWrap"><label style="font-size:12px;color:var(--fg-faded);font-weight:700;margin-right:6px">Öğrenim dili</label>
      <select id="dDil" class="btn btn-ghost" style="text-align:left"><option value="">Tümü</option></select></span>
    <span id="dStatus" style="font-size:12px;color:var(--fg-faded)"></span>
  </div>
  <div class="filter-chips" id="dChips" style="display:none;margin-top:8px"></div>
</div>"""

DETAIL_CMP = """
<div class="fav-panel" id="dCmpPanel"></div>
<div class="cmp-bar" id="dCmpBar"><button type="button" class="fav-toggle" id="dCmpBtn">Karşılaştır (0)</button><button type="button" class="fchip-clear" id="dCmpClear" style="margin-left:8px">Seçimi temizle</button></div>"""

DETAIL_TOOLS_JS = r"""<script nonce="__NONCE__">
(function(){
  var SV=window.SV||{};
  var tbl=document.querySelector('table.detail-table'); if(!tbl)return;
  var tb=tbl.querySelector('tbody'); if(!tb)return;
  var rows=Array.prototype.slice.call(tb.querySelectorAll(':scope>tr'));
  var ths=Array.prototype.slice.call(tbl.querySelectorAll('thead th')).map(function(h){return h.textContent.trim();});
  var ncol=ths.length;
  var dilSel=document.getElementById('dDil');
  function applyFilter(){
    var d=dilSel?dilSel.value:'',shown=0;
    rows.forEach(function(r){var ok=!d||r.getAttribute('data-dil')===d;r.style.display=ok?'':'none';if(ok)shown++;});
    var st=document.getElementById('dStatus');if(st)st.textContent=shown.toLocaleString('tr-TR')+' / '+rows.length.toLocaleString('tr-TR')+' program';
    if(SV.chips){var it=[];if(d)it.push({key:'dil',label:'Dil: '+d});SV.chips('dChips',it,function(){if(dilSel)dilSel.value='';applyFilter();});}
  }
  if(dilSel){
    var cnt={};rows.forEach(function(r){var d=r.getAttribute('data-dil')||'';if(d)cnt[d]=(cnt[d]||0)+1;});
    var ks=Object.keys(cnt).sort(function(a,b){return cnt[b]-cnt[a]||a.localeCompare(b,'tr');});
    if(ks.length<2){var w=document.getElementById('dDilWrap');if(w)w.style.display='none';}
    else{ks.forEach(function(k){var o=document.createElement('option');o.value=k;o.textContent=k+' ('+cnt[k]+')';dilSel.appendChild(o);});dilSel.addEventListener('change',applyFilter);}
    applyFilter();
  }
  var cmp={},order=[];
  function refreshBar(){var bar=document.getElementById('dCmpBar');if(bar)bar.classList.toggle('show',order.length>0);var b=document.getElementById('dCmpBtn');if(b)b.textContent='Karşılaştır ('+order.length+')';}
  function buildPanel(){
    var p=document.getElementById('dCmpPanel');if(!p)return;
    if(!order.length){p.classList.remove('open');p.innerHTML='';return;}
    var h='<div class="cmp-grid">';
    order.forEach(function(idx){var c=cmp[idx].children;
      h+='<div class="cmp-col"><h4>'+(c[0]?c[0].textContent.trim():'')+'</h4><dl>';
      for(var i=1;i<ncol-1;i++){h+='<dt>'+ths[i]+'</dt><dd>'+(c[i]?c[i].textContent.trim():'—')+'</dd>';}
      h+='</dl></div>';});
    p.innerHTML=h+'</div>';p.classList.add('open');
    try{p.scrollIntoView({behavior:'smooth',block:'center'});}catch(e){}
  }
  tb.addEventListener('change',function(e){var cb=e.target;if(!cb.classList||!cb.classList.contains('dcmp'))return;
    var idx=rows.indexOf(cb.closest('tr'));
    if(cb.checked){if(order.length>=3){cb.checked=false;return;}cmp[idx]=cb.closest('tr');order.push(idx);}
    else{delete cmp[idx];order=order.filter(function(x){return x!==idx;});}
    refreshBar();if(document.getElementById('dCmpPanel').classList.contains('open'))buildPanel();});
  var b1=document.getElementById('dCmpBtn');if(b1)b1.addEventListener('click',function(){var p=document.getElementById('dCmpPanel');if(p.classList.contains('open'))p.classList.remove('open');else buildPanel();});
  var b2=document.getElementById('dCmpClear');if(b2)b2.addEventListener('click',function(){cmp={};order=[];document.getElementById('dCmpPanel').classList.remove('open');refreshBar();tb.querySelectorAll('.dcmp').forEach(function(c){c.checked=false;});});
  // Program detayı (ℹ️): akademik kadro / akreditasyon / süre / ücret / koşullar
  var KOSUL=null, KLAB=['Profesör','Doçent','Dr. Öğr. Üyesi','Araştırma Gör.','Öğretim Gör.'];
  function esc(s){return (''+(s==null?'':s)).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
  function nf(n){return Number(n).toLocaleString('tr-TR');}
  if(tb.querySelector('.pdet')){
    fetch('/veri/kosul_map.json').then(function(r){return r.json();}).then(function(j){KOSUL=j;}).catch(function(){KOSUL={};});
    tb.addEventListener('click',function(e){
      var btn=e.target; if(!btn.classList||!btn.classList.contains('pdet'))return;
      var tr=btn.closest('tr');
      var nx=tr.nextElementSibling;
      if(nx&&nx.classList.contains('pdet-row')){ nx.parentNode.removeChild(nx); return; }
      var kadro=(btn.getAttribute('data-kadro')||'').split(',').map(function(x){return parseInt(x,10)||0;});
      var parts=[];
      var kp=[]; kadro.forEach(function(v,i){ if(v>0)kp.push(KLAB[i]+': '+v); });
      if(kp.length)parts.push('<div><b>Akademik kadro:</b> '+kp.join(' · ')+'</div>');
      var akr=btn.getAttribute('data-akr'); if(akr)parts.push('<div><b>Akreditasyon:</b> '+esc(akr)+'</div>');
      var sure=btn.getAttribute('data-sure'); if(sure)parts.push('<div><b>Öğrenim süresi:</b> '+esc(sure)+' yıl</div>');
      var uc=btn.getAttribute('data-ucret'); if(uc)parts.push('<div><b>Ücret:</b> '+nf(uc)+' ₺/yıl</div>');
      var ks=(btn.getAttribute('data-kosul')||'').split(',').filter(Boolean);
      if(ks.length&&KOSUL){ var li=ks.map(function(c){return KOSUL[c]?'<li>'+esc(KOSUL[c])+'</li>':'';}).filter(Boolean).join('');
        if(li)parts.push('<div style="margin-top:6px"><b>Özel koşullar:</b><ul style="margin:4px 0 0 18px">'+li+'</ul></div>'); }
      if(!parts.length)parts.push('<div style="color:var(--fg-faded)">Ek detay bulunmuyor.</div>');
      var row=document.createElement('tr'); row.className='pdet-row';
      row.innerHTML='<td colspan="'+ncol+'"><div class="pdet-box">'+parts.join('')+'</div></td>';
      tr.parentNode.insertBefore(row,tr.nextSibling);
    });
  }
})();
</script>"""


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
            _dl = _bdil_py(r.get("dil"))
            rows += (f'<tr data-dil="{_dl}"><td><strong>' + (r.get("u") or "") + "</strong> " + _pdet_btn(r) + "</td>"
                     "<td>" + (r.get("b") or "") + "</td>"
                     "<td>" + (r.get("il") or "—") + "</td>"
                     "<td>" + TUR_FULL.get(r.get("t"), "—") + "</td>"
                     "<td>" + fmt_sira(r.get("kont")) + "</td>"
                     "<td>" + doluluk_html(r) + "</td>"
                     "<td><strong>" + fmt_puan(r.get("tp")) + "</strong></td>"
                     "<td>" + fmt_puan(hist_taban(r, 2024)) + "</td>"
                     "<td>" + fmt_puan(hist_taban(r, 2023)) + "</td>"
                     "<td>" + fmt_sira(r.get("sira")) + "</td>"
                     '<td style="text-align:center"><input type="checkbox" class="dcmp" aria-label="Karşılaştır"></td></tr>')
        tabans = [r["tp"] for r in with_p]
        en_yuksek = max(tabans) if tabans else None
        en_dusuk = min(tabans) if tabans else None
        pts = sorted(set(r.get("p") for r in recs if r.get("p")))
        summary = (f"<strong>{g}</strong> bölümü 2025'te <strong>{len(recs)}</strong> programda açıldı"
                   + (f", taban puanları <strong>{fmt_puan(en_dusuk)}</strong> – <strong>{fmt_puan(en_yuksek)}</strong> aralığında." if tabans else "."))
        # Veri-dayalı FAQ (uydurma yok — yalnızca YÖK Atlas 2025 verisinden türetilir)
        from collections import Counter as _C
        wp = sorted(with_p, key=lambda r: -(r.get("tp") or 0))
        top = wp[0] if wp else None
        ilc = _C(r.get("il") for r in recs if r.get("il"))
        top_iller = ", ".join(i for i, _ in ilc.most_common(3))
        dev = sum(1 for r in recs if r.get("t") in ("D", "DK", "DU", "DKU"))
        vak = sum(1 for r in recs if r.get("t") == "V")
        pts_tr = ", ".join(pts)
        faqs = []
        if tabans:
            faqs.append((f"{g} taban puanı 2025'te kaç oldu?",
                f"2025 yılında {g} programları en düşük {fmt_puan(en_dusuk)}, en yüksek {fmt_puan(en_yuksek)} taban puanıyla öğrenci aldı."
                + (f" En yüksek tabanı {top.get('u')} ({fmt_puan(top.get('tp'))}) yaptı." if top else "")))
        faqs.append((f"{g} hangi puan türüyle tercih edilir?",
            f"{g} {pts_tr} puan türüyle tercih edilir ve 2025'te toplam {len(recs)} programda açıldı"
            + (f" ({dev} devlet, {vak} vakıf üniversitesi)." if (dev or vak) else ".")))
        if top_iller:
            faqs.append((f"{g} en çok hangi illerde okutuluyor?",
                f"{g} bölümü en çok {top_iller} illerinde bulunuyor."))
        sures = _C(r.get("sure") for r in recs if r.get("sure"))
        if sures:
            sy = sures.most_common(1)[0][0]
            faqs.append((f"{g} kaç yıllık bir bölümdür?",
                f"{g} programları genel olarak {sy} yıllık lisans eğitimidir (bazı üniversitelerde süre değişebilir)."))
        faq_html = ('<div class="section" style="margin-top:24px"><h2>' + g + ' — Sık Sorulan Sorular</h2><div class="prose" style="max-width:none">'
                    + "".join(f"<h3>{q}</h3><p>{a}</p>" for q, a in faqs) + "</div></div>")
        extra_ld_b = [breadcrumb_ld([("Ana Sayfa", "index.html"), ("Bölümler", "bolumler.html"), (g, None)]),
                      {"@type": "FAQPage", "mainEntity": [
                          {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}]
        chart = trend_chart(recs, "trend_" + s.replace("-", "_")[:40])
        head = PLOTLY_CDN if chart else ""
        body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / <a href="/bolumler.html">Bölümler</a> / {g}</div>
<div class="page-title"><h1>{g} Taban Puanları 2025</h1><span class="sub">YÖK Atlas 2025 · {len(recs)} program · Puan türü: {', '.join(pts)}</span></div>
<div class="info-box">{summary} Aşağıdaki tablo başarı sırasına göre sıralıdır (en düşük sıra = en yüksek puan).</div>
{chart}
{DETAIL_BAR}
<div class="data-table-wrap">
<table class="data-table detail-table">
<thead><tr><th>Üniversite</th><th>Program</th><th>İl</th><th>Tür</th><th>Kont.</th><th>Doluluk</th><th>Taban 2025</th><th>Taban 2024</th><th>Taban 2023</th><th>Sıra 2025</th><th data-nosort title="Karşılaştır">Kıyas</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</div>
{DETAIL_CMP}
{DETAIL_TOOLS_JS}
<div class="notice"><b>Kaynak:</b> YÖK Atlas 2025 Tercih Kılavuzu (geçmiş: 2024/2023). Boş (—) değerler o yıl yerleşen/veri olmadığını gösterir.
Doluluk = yerleşen ÷ kontenjan. Daha fazlası: <a href="/taban-puanlari.html">tüm taban puanları</a> · <a href="/tercih-robotu.html">tercih robotu</a> · <a href="/doluluk.html">doluluk analizi</a>.</div>
{faq_html}
"""
        html = base(f"bolum/{s}.html", f"{g} Taban Puanları 2025 ve Başarı Sıralaması | SınavVeri",
                    f"{g} bölümü 2025 taban puanları, son 4 yıl trendi, doluluk oranları ve başarı sıralaması. {len(recs)} üniversite programı YÖK Atlas verisiyle.",
                    body, extra_head=head, extra_ld=extra_ld_b)
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
        # Üniversite kartı türü: program-düzeyi özel kontenjanları (DKU/DU) temel devlet türüne indir
        _base = {"DKU": "D", "DU": "D"}
        tur = next((TUR_FULL.get(_base.get(r.get("t"), r.get("t"))) for r in recs if r.get("t")), "")
        rows = ""
        for r in recs:
            _dl = _bdil_py(r.get("dil"))
            rows += (f'<tr data-dil="{_dl}"><td><strong>' + (r.get("b") or "") + "</strong> " + _pdet_btn(r) + "</td>"
                     "<td>" + (r.get("g") or "—") + "</td>"
                     "<td>" + PT_LABEL.get(r.get("p"), r.get("p") or "—") + "</td>"
                     "<td>" + fmt_sira(r.get("kont")) + "</td>"
                     "<td>" + doluluk_html(r) + "</td>"
                     "<td><strong>" + fmt_puan(r.get("tp")) + "</strong></td>"
                     "<td>" + fmt_puan(hist_taban(r, 2024)) + "</td>"
                     "<td>" + fmt_sira(r.get("sira")) + "</td>"
                     '<td style="text-align:center"><input type="checkbox" class="dcmp" aria-label="Karşılaştır"></td></tr>')
        body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / <a href="/universiteler.html">Üniversiteler</a> / {u}</div>
<div class="page-title"><h1>{u} Taban Puanları 2025</h1><span class="sub">{il} · {tur} · {len(recs)} program · YÖK Atlas 2025</span></div>
{DETAIL_BAR}
<div class="data-table-wrap">
<table class="data-table detail-table">
<thead><tr><th>Program</th><th>Bölüm Grubu</th><th>Puan Türü</th><th>Kont.</th><th>Doluluk</th><th>Taban 2025</th><th>Taban 2024</th><th>Başarı Sırası</th><th data-nosort title="Karşılaştır">Kıyas</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</div>
{DETAIL_CMP}
{DETAIL_TOOLS_JS}
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


def _lise_haz_flag(r):
    t = (r.get("tur_ham") or "").lower()
    if "bulunan" in t:
        return "Hazırlıklı"
    if "bulunmayan" in t:
        return "Hazırlıksız"
    return None


def _disambiguate_lise(lgs):
    """Aynı il+ilçe+ad'a sahip okulları ayırt edici alanla (yabancı dil / hazırlık sınıfı /
    son çare kontenjan) parantez içinde işaretler. Tekil okullarda yalnızca İngilizce-dışı
    yabancı dil gösterilir. Adı yerinde değiştirir → tüm sayfalara (arama/robot/il) yayılır."""
    from collections import defaultdict
    g = defaultdict(list)
    for r in lgs:
        g[(r["il"], r["ilce"], r["okul"])].append(r)
    for group in g.values():
        hazs = {_lise_haz_flag(r) for r in group if _lise_haz_flag(r)}
        dup = len(group) > 1
        for r in group:
            parts = []
            yd = r.get("ydil")
            if yd:  # yabancı dili olan HER okula yaz (İngilizce dahil)
                parts.append(yd)
            hf = _lise_haz_flag(r)
            if dup and hf and len(hazs) > 1:
                parts.append(hf)
            r["_lbl"] = parts
        if dup:
            # aynı etiketi paylaşan satırlara kontenjan, hâlâ eşitse sıra ekle
            for _ in range(2):
                buckets = defaultdict(list)
                for r in group:
                    buckets[tuple(r["_lbl"])].append(r)
                for lbl, rs in buckets.items():
                    if len(rs) > 1:
                        if all(r.get("kont") for r in rs) and len({r["kont"] for r in rs}) == len(rs):
                            for r in rs:
                                r["_lbl"] = list(lbl) + [f"{r['kont']} kont."]
                        else:
                            for i, r in enumerate(sorted(rs, key=lambda x: -(x.get("tp") or 0)), 1):
                                r["_lbl"] = list(lbl) + [str(i)]
        for r in group:
            if r.get("_lbl"):
                r["okul"] = r["okul"] + " (" + ", ".join(r["_lbl"]) + ")"
            r.pop("_lbl", None)
    return lgs


def load_lgs():
    p = ROOT / "data" / "lgs_liseler.json"
    if not p.exists():
        return []
    return _disambiguate_lise(json.loads(p.read_text(encoding="utf-8")))


def write_lgs_veri(lgs):
    # [il, ilce, okul, türKodu, kontenjan, taban(2025), yüzdelik, tp24, tp23, trend, ydil] — çok-yıllık
    rows = [[r["il"], r["ilce"], r["okul"], LISE_TUR_CODE.get(r["tur"], "D"),
             r["kont"], r["tp"], r["yuz"], r.get("tp24"), r.get("tp23"), _osym_trend(r),
             r.get("ydil") or ""] for r in lgs]
    rows.sort(key=lambda x: (x[5] is None, -(x[5] or 0)))
    (ROOT / "veri").mkdir(exist_ok=True)
    path = ROOT / "veri" / "liseler.json"
    path.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  [veri] liseler.json  {len(rows)} okul, {path.stat().st_size//1024} KB")


LISE_SEARCH_JS = r"""<script nonce="__NONCE__">
(function(){
  var TUR={F:'Fen Lisesi',S:'Sosyal Bilimler L.',A:'Anadolu Lisesi',I:'Anadolu İmam Hatip L.',M:'Mesleki ve Teknik',G:'Güzel Sanatlar L.',P:'Spor Lisesi',D:'Diğer'};
  var data=[],shown=0,PAGE=50,SV=window.SV||{};
  var nf=function(n){return n==null?'—':n.toLocaleString('tr-TR');};
  var pf=function(n){return n==null?'—':n.toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2});};
  function el(id){return document.getElementById(id);}
  if(SV.skel)SV.skel('tbody',9,7);
  fetch('/veri/liseler.json').then(function(r){return r.json();}).then(function(j){data=j;fillIl();fillDil();applyQS();render();})
    .catch(function(){el('status').textContent='Veri yüklenemedi.';});
  function fillIl(){
    var set={};data.forEach(function(r){if(r[0])set[r[0]]=1;});
    var ils=Object.keys(set).sort(function(a,b){return a.localeCompare(b,'tr');});
    var sel=el('fIl');ils.forEach(function(i){var o=document.createElement('option');o.value=i;o.textContent=i;sel.appendChild(o);});
  }
  function fillDil(){
    var sel=el('fDil');if(!sel)return;
    var cnt={};data.forEach(function(r){if(r[10])cnt[r[10]]=(cnt[r[10]]||0)+1;});
    var dils=Object.keys(cnt).sort(function(a,b){return cnt[b]-cnt[a]||a.localeCompare(b,'tr');});
    dils.forEach(function(d){var o=document.createElement('option');o.value=d;o.textContent=d+' ('+cnt[d]+')';sel.appendChild(o);});
  }
  function applyQS(){var qs=SV.qsGet?SV.qsGet():{};if(qs.q!=null)el('fQ').value=qs.q;if(qs.il!=null)el('fIl').value=qs.il;if(qs.tur!=null)el('fTur').value=qs.tur;if(qs.dil!=null&&el('fDil'))el('fDil').value=qs.dil;}
  function syncQS(){var o={};var q=el('fQ').value.trim();if(q)o.q=q;if(el('fIl').value)o.il=el('fIl').value;if(el('fTur').value)o.tur=el('fTur').value;if(el('fDil')&&el('fDil').value)o.dil=el('fDil').value;if(SV.qsSet)SV.qsSet(o);drawChips();}
  function drawChips(){
    if(!SV.chips)return;var items=[];var q=el('fQ').value.trim();
    if(q)items.push({key:'q',label:'“'+q+'”'});
    if(el('fIl').value)items.push({key:'il',label:'İl: '+el('fIl').value});
    if(el('fTur').value)items.push({key:'tur',label:'Tür: '+(TUR[el('fTur').value]||el('fTur').value)});
    if(el('fDil')&&el('fDil').value)items.push({key:'dil',label:'Dil: '+el('fDil').value});
    SV.chips('chips',items,function(key){
      if(key==='__all__'){el('fQ').value='';el('fIl').value='';el('fTur').value='';if(el('fDil'))el('fDil').value='';}
      else if(key==='q')el('fQ').value='';else if(key==='il')el('fIl').value='';else if(key==='tur')el('fTur').value='';else if(key==='dil'&&el('fDil'))el('fDil').value='';
      render(true);
    });
  }
  function filtered(){
    var q=(el('fQ').value||'').toLocaleLowerCase('tr').trim(),il=el('fIl').value,tur=el('fTur').value,dil=el('fDil')?el('fDil').value:'';
    return data.filter(function(r){
      if(il&&r[0]!==il)return false;
      if(tur&&r[3]!==tur)return false;
      if(dil&&r[10]!==dil)return false;
      if(q){var hay=(r[2]||'')+' '+(r[1]||'')+' '+(r[0]||'');if(SV.tokMatch?!SV.tokMatch(hay,q):hay.toLocaleLowerCase('tr').indexOf(q)<0)return false;}
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
    if(reset!==false){shown=0;syncQS();}
    var rows=applySort(filtered());
    el('status').textContent=rows.length.toLocaleString('tr-TR')+' lise bulundu';
    if(!rows.length){if(SV.empty)SV.empty('tbody',9);el('moreWrap').style.display='none';return;}
    shown=Math.min(shown+PAGE,rows.length);if(shown===0&&rows.length)shown=Math.min(PAGE,rows.length);
    var tb=el('tbody');tb.innerHTML='';
    rows.slice(0,shown||PAGE).forEach(function(r){
      var tr=document.createElement('tr');
      tr.innerHTML='<td><strong>'+(r[2]||'')+'</strong></td><td>'+(r[0]||'')+(r[1]?' / '+r[1]:'')+'</td>'+
        '<td><span class="tag tag-other">'+(TUR[r[3]]||'—')+'</span></td>'+
        '<td>'+nf(r[4])+'</td><td><strong>'+pf(r[5])+'</strong>'+(SV.spark?SV.spark([r[8],r[7],r[5]]):'')+'</td>'+
        '<td>'+pf(r[7])+'</td><td>'+pf(r[8])+'</td><td>'+(r[9]||'')+'</td>'+
        '<td>'+(r[6]==null?'—':'%'+pf(r[6]))+'</td>';
      tb.appendChild(tr);
    });
    el('moreWrap').style.display=(shown<rows.length)?'block':'none';
    el('moreInfo').textContent=shown+' / '+rows.length.toLocaleString('tr-TR');
  }
  ['fQ','fIl','fTur','fDil'].forEach(function(id){var e=el(id);if(e)e.addEventListener('input',function(){render(true);});});
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
    <select id="fDil" class="btn btn-ghost" style="text-align:left"><option value="">Tüm yabancı diller</option></select>
  </div>
  <div class="filter-chips" id="chips" style="display:none"></div>
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
                body, extra_ld=[breadcrumb_ld([("Ana Sayfa", "index.html"), ("LGS Lise Taban Puanları", None)])])


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
  var CFG=__CFG__, NCOL=CFG.cols.length, SV=window.SV||{};
  var data=[],shown=0,PAGE=50;
  function el(id){return document.getElementById(id);}
  var nf=function(n){return n==null?'—':Number(n).toLocaleString('tr-TR');};
  var pf=function(n){return n==null?'—':Number(n).toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2});};
  if(SV.skel)SV.skel('tbody',NCOL,7);
  el('status').textContent='Veriler yükleniyor…';
  fetch(CFG.file).then(function(r){return r.json();}).then(function(j){data=j;initFilters();applyQS();render();})
    .catch(function(){el('status').textContent='Veri yüklenemedi.';});
  function initFilters(){
    CFG.filters.forEach(function(f){
      var set={};data.forEach(function(r){if(r[f[0]])set[r[f[0]]]=1;});
      var vals=Object.keys(set).sort(function(a,b){return a.localeCompare(b,'tr');});
      var sel=el('fil'+f[1]);if(!sel)return;
      vals.forEach(function(v){var o=document.createElement('option');o.value=v;o.textContent=v;sel.appendChild(o);});
    });
  }
  function applyQS(){
    var qs=SV.qsGet?SV.qsGet():{};
    if(qs.q!=null)el('fQ').value=qs.q;
    CFG.filters.forEach(function(f){var s=el('fil'+f[1]);if(s&&qs['f'+f[1]]!=null)s.value=qs['f'+f[1]];});
  }
  function syncQS(){
    var o={}; var q=el('fQ').value.trim(); if(q)o.q=q;
    CFG.filters.forEach(function(f){var s=el('fil'+f[1]);if(s&&s.value)o['f'+f[1]]=s.value;});
    if(SV.qsSet)SV.qsSet(o); drawChips();
  }
  function drawChips(){
    if(!SV.chips)return;
    var items=[]; var q=el('fQ').value.trim();
    if(q)items.push({key:'q',label:'“'+q+'”'});
    CFG.filters.forEach(function(f){var s=el('fil'+f[1]);if(s&&s.value)items.push({key:'f'+f[1],label:f[2]+': '+s.value});});
    SV.chips('chips',items,function(key){
      if(key==='__all__'){el('fQ').value='';CFG.filters.forEach(function(f){var s=el('fil'+f[1]);if(s)s.value='';});}
      else if(key==='q'){el('fQ').value='';}
      else {CFG.filters.forEach(function(f){if('f'+f[1]===key){var s=el('fil'+f[1]);if(s)s.value='';}});}
      render(true);
    });
  }
  function filtered(){
    var q=(el('fQ').value||'').toLocaleLowerCase('tr').trim();
    return data.filter(function(r){
      for(var k=0;k<CFG.filters.length;k++){var f=CFG.filters[k];var s=el('fil'+f[1]);if(s&&s.value&&String(r[f[0]])!==s.value)return false;}
      if(q){var hay='';CFG.search.forEach(function(i){hay+=' '+(r[i]||'');});if(SV.tokMatch?!SV.tokMatch(hay,q):hay.toLocaleLowerCase('tr').indexOf(q)<0)return false;}
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
    if(reset!==false){shown=0;syncQS();}
    var rows=applySort(filtered());
    el('status').textContent=rows.length.toLocaleString('tr-TR')+' sonuç bulundu';
    if(!rows.length){if(SV.empty)SV.empty('tbody',NCOL);el('moreWrap').style.display='none';return;}
    shown=Math.min(shown+PAGE,rows.length);if(shown===0&&rows.length)shown=Math.min(PAGE,rows.length);
    var tb=el('tbody');tb.innerHTML='';
    rows.slice(0,shown||PAGE).forEach(function(r){
      var html='';
      CFG.cols.forEach(function(c){
        var v=r[c[0]],cell;
        if(c[1]==='p')cell='<strong>'+pf(v)+'</strong>'+(CFG.spark&&SV.spark?SV.spark(CFG.spark.map(function(i){return r[i];})):'');
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


def minmax_page(slug, title, desc, h1, sub, file, cols, filters, search_idx, intro, kaynak, ph="Ara…", hub_html="", spark=None):
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
           "filters": [[idx, n, label] for n, (idx, label) in enumerate(filters)], "search": search_idx, "spark": spark}
    js = GENERIC_SEARCH_JS.replace("__CFG__", json.dumps(cfg, ensure_ascii=False))
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / <a href="/taban-puanlari.html">Taban Puanları</a> / {h1}</div>
<div class="page-title"><h1>{h1}</h1><span class="sub">{sub}</span></div>
<div class="info-box">{intro}</div>
<div class="calc-card" style="margin-bottom:18px">
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px">{fhtml}</div>
  <div class="filter-chips" id="chips" style="display:none"></div>
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
    return base(slug, title, desc, body,
                extra_ld=[breadcrumb_ld([("Ana Sayfa", "index.html"), ("Taban Puanları", "taban-puanlari.html"), (h1, None)])])


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
        # Aynı kurum+kadro+il+dönem birden çok kez açılır (farklı nitelik şartı) → kadro koduyla ayırt et.
        # Kadro kodu ÖSYM tercih kılavuzunda nitelikleri aramak için benzersiz anahtardır.
        from collections import defaultdict
        grp = defaultdict(list)
        for r in d:
            grp[(r.get("kurum"), r.get("kadro"), r.get("il"), r.get("donem"))].append(r)
        for rs in grp.values():
            if len(rs) > 1:
                for r in rs:
                    if r.get("kod"):
                        r["kadro"] = f'{r["kadro"]} (Kadro Kodu: {r["kod"]})'
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
        ph="Dal / kurum / şehir ara…", hub_html=hub_links_html("tus", hubs), spark=[7, 6, 4])


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
        ph="Dal / kurum ara…", hub_html=hub_links_html("dus", hubs), spark=[7, 6, 4])


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
        ph="Program / üniversite ara…", hub_html=hub_links_html("dgs", hubs), spark=[6, 5, 3])


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
        "KPSS atamaları tek-seferlik ilanlar olduğundan eşleşme kısmidir (Çevre Bak. için 2024 verisi yoktur). "
        "<b>Aynı unvanlı birden çok kadro</b> farklı <b>nitelik (aranan şartlar)</b> içerir; ayırmak için kadro adının yanına "
        "<b>(Kadro Kodu: …)</b> eklenir. Bir kadronun tüm niteliklerini görmek için bu kodu, ilgili dönemin "
        "<a href='https://www.osym.gov.tr/TR,62/kpss.html' target='_blank' rel='noopener'>ÖSYM KPSS tercih kılavuzunda</a> aratın.",
        OSYM_KAYNAK, ph="Kadro / kurum ara…", hub_html=hub_links_html("kpss", hubs), spark=[8, 6])


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
    <select id="btur" class="btn btn-ghost" style="text-align:left"><option value="">Tüm türler</option><option value="D">Devlet</option><option value="V">Özel (Vakıf)</option><option value="K">KKTC</option><option value="DK">Devlet (KKTC Kampüs)</option><option value="DU">Devlet (Ücretli)</option><option value="DKU">Devlet (KKTC Uyruklu)</option></select>
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
  var TUR={{D:'Devlet',V:'Özel (Vakıf)',K:'KKTC',DK:'Devlet (KKTC Kampüs)',DU:'Devlet (Ücretli)',DKU:'Devlet (KKTC Uyruklu)','?':'—'}},DUZ={{L:'Lisans',O:'Önlisans'}};
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
             ("yks-siralama-hesaplama.html", "📈", "YKS Sıralama Hesaplama", "Puanına göre tahmini sıra + bölümler"),
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


# ───────────────────────── GENEL ARAMA ─────────────────────────
ARA_JS = r"""<script nonce="__NONCE__">
(function(){
  var SV=window.SV||{};
  var inp=document.getElementById('aQ'), out=document.getElementById('aResults'), st=document.getElementById('aStatus');
  var DATA=null, ORDER=['Üniversite','Bölüm','Lise','Rehber','Araç'];
  function norm(s){return (s||'').toLocaleLowerCase('tr');}
  function esc(s){return (''+(s==null?'':s)).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
  function progCta(q){
    return '<a class="ara-item" href="/universite-taban-puanlari.html?q='+encodeURIComponent(q)+'" style="border-color:var(--accent-light)">'+
      '<span class="hs-kind" style="float:right;color:var(--accent);font-weight:700">Program ara →</span>'+
      '<b>🎓 “'+esc(q)+'” için üniversite programları</b><small>Üniversite + bölüm birlikte yazdıysanız (örn. “ODTÜ kimya”) taban puanları sayfasında arayın</small></a>';
  }
  function render(){
    var q=inp.value.trim();
    if(SV.qsSet)SV.qsSet(q?{q:q}:{});
    if(!DATA){st.textContent='Yükleniyor…';return;}
    if(q.length<2){st.textContent='Aramak için en az 2 karakter yazın.';out.innerHTML='';return;}
    var hits=DATA.filter(function(d){return SV.tokMatch?SV.tokMatch((d.n||'')+' '+(d.s||''),q):(norm(d.n).indexOf(norm(q))>=0);});
    var multi=q.split(/\s+/).filter(Boolean).length>=2;
    st.textContent=hits.length.toLocaleString('tr-TR')+' sonuç · “'+esc(q)+'”';
    if(!hits.length){
      out.innerHTML=(multi?progCta(q):'')+'<div class="empty-state"><b>Doğrudan eşleşme yok</b>Üniversite + bölüm birlikte ararken yukarıdaki “Program ara” bağlantısını kullanın; ya da tek tek (üniversite veya bölüm) yazın.</div>';
      return;
    }
    var groups={};hits.forEach(function(d){(groups[d.t]=groups[d.t]||[]).push(d);});
    var keys=Object.keys(groups).sort(function(a,b){var ia=ORDER.indexOf(a),ib=ORDER.indexOf(b);return (ia<0?99:ia)-(ib<0?99:ib);});
    var h='';keys.forEach(function(k){
      var arr=groups[k].slice(0,30);
      h+='<div class="ara-group"><h2>'+esc(k)+' ('+groups[k].length+')</h2>';
      arr.forEach(function(d){h+='<a class="ara-item" href="'+d.u+'"><b>'+esc(d.n)+'</b>'+(d.s?' <small>'+esc(d.s)+'</small>':'')+'</a>';});
      if(groups[k].length>30)h+='<div style="font-size:12px;color:var(--fg-faded);padding:4px 2px">… ve '+(groups[k].length-30)+' sonuç daha. Aramayı daraltın.</div>';
      h+='</div>';
    });
    out.innerHTML=(multi?progCta(q):'')+h;
  }
  fetch('/veri/arama.json').then(function(r){return r.json();}).then(function(j){DATA=j;render();}).catch(function(){st.textContent='Arama verisi yüklenemedi.';});
  inp.addEventListener('input',render);
  var qs=SV.qsGet?SV.qsGet():{};if(qs.q){inp.value=qs.q;}
})();
</script>"""


def page_ara():
    body = """
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / Arama</div>
<div class="page-title"><h1>Arama</h1><span class="sub">Üniversite, bölüm, lise, sınav rehberi ve araçlar — hepsinde tek aramada</span></div>
<div class="calc-card" style="margin-bottom:18px">
  <input id="aQ" type="search" autofocus placeholder="Örn. boğaziçi, tıp, fen lisesi, kpss, ankara…" style="width:100%;padding:11px 14px;border:1px solid var(--border);border-radius:9px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:15px">
  <div id="aStatus" style="margin-top:12px;font-size:13px;color:var(--accent);font-weight:700">Yükleniyor…</div>
</div>
<div id="aResults"></div>
""" + ARA_JS
    return base("ara.html", "Arama — Üniversite, Bölüm, Lise, Sınav | SınavVeri",
                "SınavVeri genel arama: üniversite, bölüm/program grubu, lise, sınav rehberi ve hesaplama araçlarında tek aramada sonuç bul.",
                body, extra_ld=[breadcrumb_ld([("Ana Sayfa", "index.html"), ("Arama", None)])])


def page_listeler(programs):
    """GEO/SEO: gerçek veriden türetilmiş sıralama listeleri + ItemList şeması (AI alıntı)."""
    PTL = {"SAY": "Sayısal", "EA": "Eşit Ağırlık", "SÖZ": "Sözel", "DİL": "Dil"}
    sections = ""
    item_list = []
    for pt in ("SAY", "EA", "SÖZ", "DİL"):
        rows = sorted([r for r in programs if r.get("p") == pt and r.get("tp")], key=lambda r: -r["tp"])[:20]
        if not rows:
            continue
        trs = ""
        for i, r in enumerate(rows, 1):
            trs += (f"<tr><td>{i}</td><td><strong>{r.get('b') or ''}</strong><br><small>{r.get('u') or ''}</small></td>"
                    f"<td>{r.get('il') or '—'}</td><td><strong>{fmt_puan(r.get('tp'))}</strong></td><td>{fmt_sira(r.get('sira'))}</td></tr>")
            if pt == "SAY" and i <= 10:
                item_list.append({"@type": "ListItem", "position": i, "name": f"{r.get('b')} — {r.get('u')}"})
        sections += (f'<div class="section"><h2>En Yüksek Taban — {PTL[pt]} (2025, ilk 20)</h2>'
                     '<div class="data-table-wrap"><table class="data-table"><thead><tr><th data-nosort>#</th>'
                     '<th>Program / Üniversite</th><th>İl</th><th>Taban</th><th>Sıra</th></tr></thead>'
                     f'<tbody>{trs}</tbody></table></div></div>')
    konts = sorted([r for r in programs if r.get("kont")], key=lambda r: -r["kont"])[:20]
    if konts:
        trs = "".join(f"<tr><td>{i}</td><td><strong>{r.get('b') or ''}</strong><br><small>{r.get('u') or ''}</small></td>"
                      f"<td>{r.get('il') or '—'}</td><td><strong>{fmt_sira(r.get('kont'))}</strong></td><td>{fmt_puan(r.get('tp'))}</td></tr>"
                      for i, r in enumerate(konts, 1))
        sections += ('<div class="section"><h2>En Çok Kontenjanlı 20 Program (2025)</h2>'
                     '<div class="data-table-wrap"><table class="data-table"><thead><tr><th data-nosort>#</th>'
                     '<th>Program / Üniversite</th><th>İl</th><th>Kontenjan</th><th>Taban</th></tr></thead>'
                     f'<tbody>{trs}</tbody></table></div></div>')
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / Listeler ve Sıralamalar</div>
<div class="page-title"><h1>Üniversite Listeleri ve Sıralamalar 2025</h1><span class="sub">YÖK Atlas 2025 gerçek yerleştirme verisinden · en yüksek taban, en çok kontenjan</span></div>
<div class="info-box">2025 yerleştirme verisine göre öne çıkan program listeleri. Tüm taban puanları için
<a href="/universite-taban-puanlari.html">üniversite taban puanları</a>, puanına göre bölüm için
<a href="/tercih-robotu.html">tercih robotu</a>.</div>
{sections}
<div class="notice"><b>Kaynak:</b> YÖK Atlas 2025 Tercih Kılavuzu yerleştirme verisi. Sıralamalar 2025 taban puanı / kontenjanına göredir.</div>
"""
    extra = [breadcrumb_ld([("Ana Sayfa", "index.html"), ("Listeler ve Sıralamalar", None)])]
    if item_list:
        extra.append({"@type": "ItemList", "name": "En Yüksek Taban Puanlı Sayısal Programlar 2025", "itemListElement": item_list})
    return base("listeler.html", "Üniversite Listeleri ve Sıralamalar 2025 — En Yüksek Taban, En Çok Kontenjan | SınavVeri",
                "2025 üniversite sıralamaları: en yüksek taban puanlı programlar (SAY/EA/SÖZ/DİL) ve en çok kontenjanlı bölümler. YÖK Atlas gerçek yerleştirme verisi.",
                body, extra_ld=extra)


def page_meslek_testi(g_by_slug):
    """İlgi alanı testi → bölüm önerisi. İstemci-taraflı; backend yok. Öneriler bölüm sayfalarına linklenir."""
    name2slug = {v: k for k, v in (g_by_slug or {}).items()}

    def lnk(names):
        out = []
        for n in names:
            sl = name2slug.get(n)
            href = f"/bolum/{sl}.html" if sl else f"/ara.html?q={n.replace(' ', '+')}"
            out.append({"n": n, "h": href})
        return out
    CATS = {
        "muh": ("Mühendislik & Sayısal", lnk(["Bilgisayar Mühendisliği", "Elektrik-Elektronik Mühendisliği", "Makine Mühendisliği", "Endüstri Mühendisliği", "İnşaat Mühendisliği"])),
        "sag": ("Sağlık", lnk(["Tıp", "Diş Hekimliği", "Eczacılık", "Hemşirelik", "Fizyoterapi ve Rehabilitasyon"])),
        "sos": ("Sosyal & Hukuk/İşletme", lnk(["Hukuk", "İşletme", "Psikoloji", "İktisat", "Uluslararası İlişkiler"])),
        "egt": ("Eğitim & Sözel", lnk(["Rehberlik ve Psikolojik Danışmanlık", "Türk Dili ve Edebiyatı", "Tarih", "Sınıf Öğretmenliği", "İngilizce Öğretmenliği"])),
        "san": ("Sanat & Tasarım", lnk(["Mimarlık", "İç Mimarlık", "Grafik Tasarımı", "Endüstriyel Tasarım"])),
        "bil": ("Bilişim & Veri", lnk(["Yazılım Mühendisliği", "Bilgisayar Mühendisliği", "İstatistik", "Yönetim Bilişim Sistemleri"])),
    }
    QS = [
        ("En çok hangi dersten keyif alırsın?", [("Matematik / problem çözme", {"muh": 2, "bil": 2}), ("Biyoloji / sağlık", {"sag": 3}),
            ("Edebiyat / tarih / felsefe", {"egt": 2, "sos": 1}), ("Resim / müzik / tasarım", {"san": 3}), ("Ekonomi / hukuk / toplum", {"sos": 3})]),
        ("Nasıl çalışmaktan hoşlanırsın?", [("Bir şeyler tasarlayıp inşa etmek", {"muh": 2, "san": 1}), ("İnsanlara yardım/bakım", {"sag": 2, "egt": 1}),
            ("Veri ve analizle uğraşmak", {"bil": 3, "sos": 1}), ("Yazmak / anlatmak / öğretmek", {"egt": 3}), ("Yaratıcı/görsel üretim", {"san": 3})]),
        ("Geleceğte seni en çok ne motive eder?", [("Teknoloji geliştirmek", {"muh": 2, "bil": 2}), ("İnsan sağlığına katkı", {"sag": 3}),
            ("Adalet/iş dünyası/liderlik", {"sos": 3}), ("Nesiller yetiştirmek", {"egt": 3}), ("Estetik/sanat üretmek", {"san": 3})]),
        ("Hangisi sana daha yakın?", [("Mantık ve sistem kurmak", {"muh": 2, "bil": 1}), ("Empati ve iletişim", {"sag": 1, "egt": 2, "sos": 1}),
            ("Sayılar ve istatistik", {"bil": 2, "sos": 1}), ("Hayal gücü ve tasarım", {"san": 3}), ("İkna ve müzakere", {"sos": 3})]),
        ("Bir projede rolün ne olurdu?", [("Teknik çözümü kuran", {"muh": 2, "bil": 2}), ("İnsanlarla ilgilenen", {"sag": 2, "egt": 1}),
            ("Stratejiyi/planı yapan", {"sos": 2, "bil": 1}), ("Görseli/tasarımı yapan", {"san": 3}), ("Eğiten/sunan", {"egt": 3})]),
    ]
    cfg = {"cats": {k: {"label": v[0], "items": v[1]} for k, v in CATS.items()},
           "qs": [{"q": q, "opts": [{"t": t, "w": w} for t, w in opts]} for q, opts in QS]}
    qhtml = ""
    for qi, (q, opts) in enumerate(QS):
        ohtml = "".join(
            f'<label class="mt-opt"><input type="radio" name="q{qi}" value="{oi}"> {t}</label>'
            for oi, (t, _w) in enumerate(opts))
        qhtml += f'<div class="mt-q"><div class="mt-qt">{qi+1}. {q}</div>{ohtml}</div>'
    js = '<script nonce="__NONCE__">var MT=' + json.dumps(cfg, ensure_ascii=False) + r""";
(function(){
  function el(i){return document.getElementById(i);}
  el('mtBtn').addEventListener('click',function(){
    var sc={}; Object.keys(MT.cats).forEach(function(k){sc[k]=0;});
    var answered=0;
    MT.qs.forEach(function(qq,qi){
      var r=document.querySelector('input[name="q'+qi+'"]:checked'); if(!r)return; answered++;
      var w=qq.opts[+r.value].w; Object.keys(w).forEach(function(k){sc[k]=(sc[k]||0)+w[k];});
    });
    if(answered<3){el('mtRes').innerHTML='<div class="notice">Daha isabetli öneri için en az 3 soruyu yanıtla.</div>';el('mtRes').style.display='block';return;}
    var order=Object.keys(sc).sort(function(a,b){return sc[b]-sc[a];}).filter(function(k){return sc[k]>0;}).slice(0,2);
    var h='<h2 style="font-size:18px;color:var(--accent);margin:6px 0 10px">Sana en uygun alanlar</h2>';
    order.forEach(function(k){var c=MT.cats[k];
      h+='<div class="calc-card" style="margin-bottom:12px"><h3 style="color:var(--accent-2);margin-bottom:8px">'+c.label+'</h3><div class="tool-row">';
      c.items.forEach(function(it){h+='<a class="tool-btn" href="'+it.h+'"><span class="tb-icon">📘</span><span class="tb-text"><b>'+it.n+'</b><span>taban puanları →</span></span></a>';});
      h+='</div></div>';
    });
    h+='<div class="notice">Bu test yalnızca <b>fikir vermek</b> içindir; kesin tercih ilgi, yetenek ve puanına bağlıdır. Önerilen bölümlerin gerçek taban puanlarını sayfalarından inceleyebilirsin.</div>';
    el('mtRes').innerHTML=h; el('mtRes').style.display='block';
    el('mtRes').scrollIntoView({behavior:'smooth',block:'start'});
  });
})();
</script>"""
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / Bölüm Bulma Testi</div>
<div class="page-title"><h1>Hangi Bölüm Bana Uygun? — İlgi Alanı Testi</h1><span class="sub">Kısa testi yanıtla, ilgine uygun bölüm önerileri al · ücretsiz</span></div>
<div class="info-box">5 soruluk kısa bir ilgi testi. Sonunda sana en uygun <b>2 alan</b> ve örnek bölümler önerilir; her biri o bölümün taban puanları sayfasına götürür. (Backend yok — yanıtların hiçbir yere gönderilmez.)</div>
<div class="calc-card">{qhtml}
  <div style="margin-top:14px"><button type="button" class="btn btn-primary" id="mtBtn">Sonucu Göster</button></div>
</div>
<div id="mtRes" style="display:none;margin-top:18px"></div>
{js}
"""
    return base("bolum-bulma-testi.html", "Hangi Bölüm Bana Uygun? İlgi Alanı Testi | SınavVeri",
                "Ücretsiz bölüm bulma testi: 5 soruluk ilgi alanı testiyle sana uygun üniversite bölümlerini keşfet ve taban puanlarını gör.",
                body, extra_ld=[breadcrumb_ld([("Ana Sayfa", "index.html"), ("Bölüm Bulma Testi", None)])])


def write_arama(g_by_slug, u_by_slug, il_slugs):
    """Header global arama + /ara.html için birleşik hafif indeks."""
    items = []
    for s, u in u_by_slug.items():
        items.append({"t": "Üniversite", "n": u, "u": f"/universite/{s}.html"})
    for s, g in g_by_slug.items():
        items.append({"t": "Bölüm", "n": g, "s": "Tüm üniversitelerde", "u": f"/bolum/{s}.html"})
    for s, il in (il_slugs or {}).items():
        items.append({"t": "Lise", "n": f"{il} liseleri", "s": "İl lise taban puanları", "u": f"/lise/{s}.html"})
    rehber = [("YKS", "yks.html"), ("LGS", "lgs.html"), ("KPSS", "kpss.html"), ("DGS", "dgs.html"),
              ("TUS", "tus.html"), ("DUS", "dus.html"), ("ALES", "ales.html"), ("MSÜ", "msu.html"),
              ("YDS", "yds.html"), ("YÖKDİL", "yokdil.html"), ("YDUS", "ydus.html"), ("STS", "sts.html")]
    for ad, sl in rehber:
        items.append({"t": "Rehber", "n": f"{ad} sınav rehberi", "s": "Format, soru dağılımı, tarih", "u": f"/{sl}"})
    arac = [("Üniversite Taban Puanları", "universite-taban-puanlari.html"),
            ("YKS Tercih Robotu", "tercih-robotu.html"), ("DGS Tercih Robotu", "dgs-tercih-robotu.html"),
            ("TUS Tercih Robotu", "tus-tercih-robotu.html"), ("DUS Tercih Robotu", "dus-tercih-robotu.html"),
            ("KPSS Tercih Robotu", "kpss-tercih-robotu.html"), ("LGS Tercih Robotu", "lgs-tercih-robotu.html"),
            ("LGS Lise Taban Puanları", "lise-taban-puanlari.html"), ("TUS Taban Puanları", "tus-taban-puanlari.html"),
            ("DUS Taban Puanları", "dus-taban-puanlari.html"), ("DGS Taban Puanları", "dgs-taban-puanlari.html"),
            ("KPSS Atama Taban Puanları", "kpss-atama-taban-puanlari.html"), ("Doluluk Analizi", "doluluk.html"),
            ("YKS Puan Hesaplama", "yks-puan-hesaplama.html"), ("YKS Sıralama Hesaplama", "yks-siralama-hesaplama.html"),
            ("LGS Puan Hesaplama", "lgs-puan-hesaplama.html"),
            ("KPSS Puan Hesaplama", "kpss-puan-hesaplama.html"), ("DGS Puan Hesaplama", "dgs-puan-hesaplama.html"),
            ("ALES Puan Hesaplama", "ales-puan-hesaplama.html"), ("Sınav Takvimi", "takvim.html"),
            ("Listeler ve Sıralamalar", "listeler.html"), ("Bölüm Bulma Testi", "bolum-bulma-testi.html")]
    for ad, sl in arac:
        if (ROOT / sl).exists() or sl in ("universite-taban-puanlari.html",):
            items.append({"t": "Araç", "n": ad, "u": f"/{sl}"})
    (ROOT / "veri").mkdir(exist_ok=True)
    (ROOT / "veri" / "arama.json").write_text(
        json.dumps(items, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  → arama indeksi: {len(items)} kayıt")


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
    W("yks-siralama-hesaplama.html", page_yks_siralama())
    W("lgs-puan-hesaplama.html", page_lgs_calc())
    W("kpss-puan-hesaplama.html", page_kpss_calc())
    W("dgs-puan-hesaplama.html", page_dgs_calc())
    W("ales-puan-hesaplama.html", page_ales_calc())
    write("404.html", page_error("404", "Aradığınız sayfa bulunamadı."))
    write("5xx.html", page_error("Hata", "Geçici bir sorun oluştu. Lütfen daha sonra tekrar deneyin."))

    W("ara.html", page_ara())

    # Veri tabanlı sayfalar
    il_slugs = {}
    programs = load_programs()
    print(f"  {len(programs)} program yüklendi (YÖK Atlas 2025)")
    write_veri(programs)
    write_puan_sira(programs)
    _km = ROOT / "data" / "kosul_map.json"
    if _km.exists():
        (ROOT / "veri" / "kosul_map.json").write_text(_km.read_text(encoding="utf-8"), encoding="utf-8")
        print("  [veri] kosul_map.json kopyalandı")
    W("doluluk.html", page_doluluk(programs))
    print("  Bölüm sayfaları üretiliyor...")
    g_by_slug = gen_bolum_pages(programs)
    for s in g_by_slug:
        slugs.append(f"bolum/{s}.html")
    W("bolumler.html", page_bolumler(g_by_slug, programs))
    W("listeler.html", page_listeler(programs))
    W("bolum-bulma-testi.html", page_meslek_testi(g_by_slug))
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

    print("  Genel arama indeksi üretiliyor...")
    write_arama(g_by_slug, u_by_slug, il_slugs)

    write_support(slugs)
    print(f"Tamamlandı. Toplam {len(slugs)} sayfa sitemap'te.")


if __name__ == "__main__":
    main()
