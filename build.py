#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SınavVeri.com statik site jeneratörü.
Tüm sayfaları assets/style.css + ortak şablonla üretir.
Inline <script>'lar nonce="__NONCE__" taşır (nginx sub_filter ile per-request nonce).
Inline event handler (onclick/onload) YOK — addEventListener kullanılır (CSP strict-dynamic)."""
import json
import re
from datetime import date, datetime
from pathlib import Path
try:  # paket icinde relative, top-level script olarak duz import
    from .ldjson_safe import ld_escape, ld_json
except ImportError:  # generators/ gibi dizinler __init__.py'li olsa da
    from ldjson_safe import ld_escape, ld_json   # modul top-level import edilebiliyor


def html_escape(s):
    return (str(s) if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

ROOT = Path(__file__).parent
SITE = "https://sinavveri.com"
ASSET_VER = "20260819a"

# Kişiye Özel KPSS Tercih Raporu — hizmet yapılandırması
# whatsapp: "905XXXXXXXXX" (boşsa WhatsApp butonu gizlenir) · email: sipariş e-postası
# stripe: Stripe Payment Link URL (boşsa "sipariş sonrası ödeme linki iletilir" akışı)
KPSS_RAPOR = {
    "fiyat": "999",
    "whatsapp": "447576165476",
    "email": "teknikanaliz@gmail.com",
    # Embedded Checkout (sayfa-içi): backend /api/kpss/checkout + Stripe.js publishable key
    "pk": "pk_live_51TZZptL9vmvDCXaicmic9YgJyMVAVmSLIbNtfd6vtPzJpmHS3zH5k869AqDGc6aCyQdbeTlAbQDkGbnop4ZdIqP700J6qnFiHa",
    "api": "/api/kpss/checkout",
    "stripe": "",  # eski Payment Link (embedded'a geçildi; boş = link butonu yok)
}

NAV = [
    ("/index.html", "Ana Sayfa"),
    ("/taban-puanlari.html", "Taban Puanları"),
    ("/tercih-robotu.html", "Tercih Robotu"),
    ("/puan-hesaplama.html", "Puan Hesaplama"),
    ("/bolumler.html", "Bölümler"),
    ("/universiteler.html", "Üniversiteler"),
    ("/listeler.html", "Listeler"),
    ("/takvim.html", "Takvim"),
    ("/duyurular.html", "Duyurular"),
    ("/rehberler.html", "Rehberler"),
    ("/hakkimizda.html", "Hakkımızda"),
]

# TrVeri STANDART paylaş bileşeni (rule 3.16) — servermimari/assets/share.js kopyası.
# İçerik/detay sayfasında ana veri tablosunun ÜSTÜNE <div class="share-bar"></div> konur;
# SHARE_JS (nonce'lu external script, CSP strict-dynamic ile yüklenir) yalnız o sayfalarda base(share=True) ile eklenir.
SHARE_BAR = '<div class="share-bar"></div>'
SHARE_JS = f'<script src="/assets/share.js?v={ASSET_VER}" nonce="__NONCE__" defer></script>'

# TrVeri STANDART veri tablosu bileşenleri (rule 3.17) — servermimari/assets/{pager,table}.js kopyası.
# ⚠️ defer YOK: sayfa gövdesindeki inline script'ler (DETAIL_TOOLS_JS, SEARCH_JS…) senkron olarak
# window.TVPager çağırır; defer'li yüklemede bu script'ler TVPager tanımlanmadan çalışırdı.
TABLE_JS = (f'<script src="/assets/pager.js?v={ASSET_VER}" nonce="__NONCE__"></script>\n'
            f'<script src="/assets/table.js?v={ASSET_VER}" nonce="__NONCE__"></script>')


# ───────── KOLON BAŞLIĞI AÇIKLAMALARI (TrVeri rule 3.17) ─────────
# th[data-tip] → masaüstünde hover, mobilde ⓘ ile görünür (assets/table.js).
# Yalnız sütunun GERÇEK anlamına göre yazılır; bilinmeyen başlığa açıklama üretilmez.
TH_TIPS = {
    "Kurum": ("Kadronun/kontenjanın ait olduğu kurum (üniversite, hastane, bakanlık vb.).", "text"),
    "Üniversite": ("Programın açıldığı üniversite.", "text"),
    "Program": ("Programın ÖSYM/YÖK Atlas kılavuzundaki tam adı.", "text"),
    "Bölüm": ("Bölüm/program adı.", "text"),
    "Bölüm Grubu": ("Programın bağlı olduğu genel bölüm grubu.", "text"),
    "Uzmanlık Dalı": ("Uzmanlık dalı; parantez içi kadro türüdür (ÜNİ, SBA, EAH…).", "text"),
    "Kadro": ("Atama yapılan kadro/pozisyon unvanı; parantezdeki kod ÖSYM kadro kodudur.", "text"),
    "Ad": ("Kayıt adı.", "text"),
    "İl": ("Kurumun/programın bulunduğu il.", "text"),
    "İlçe": ("Okulun bulunduğu ilçe.", "text"),
    "İl / İlçe": ("Okulun bulunduğu il ve ilçe.", "text"),
    "Şehir": ("Üniversitenin bulunduğu şehir.", "text"),
    "Tür": ("Kurum/kontenjan türü.", "text"),
    "Kontenjan Türü": ("ÖSYM kontenjan türü (ÜNİ, SBA, EAH, MSB, KKTC…).", "text"),
    "Düzey": ("Kadronun istediği öğrenim düzeyi: Lisans, Önlisans veya Ortaöğretim.", "text"),
    "Dönem": ("Kadronun yer aldığı ÖSYM yerleştirme dönemi (ör. KPSS-2025/1).", "text"),
    "Puan Türü": ("Programın tercih edildiği puan türü (Sayısal, Eşit Ağırlık, Sözel, Dil, TYT).", "text"),
    "Kont.": ("İlan edilen kontenjan (alınacak öğrenci/personel sayısı).", "num"),
    "Kontenjan": ("İlan edilen kontenjan (alınacak öğrenci/personel sayısı).", "num"),
    "Yerleşen": ("Kontenjana yerleşen kişi sayısı.", "num"),
    "Boş": ("Dolmayan kontenjan sayısı (kontenjan − yerleşen).", "num"),
    "Doluluk": ("Doluluk = yerleşen ÷ kontenjan. %100 kontenjanın tamamen dolduğunu gösterir.", "num"),
    "Taban": ("Yerleşen son adayın puanı (en düşük yerleşme puanı).", "num"),
    "Tavan": ("Yerleşen ilk adayın puanı (en yüksek yerleşme puanı).", "num"),
    "Önceki Yıl": ("Aynı kurum/il/kadronun bir önceki yılki (aynı tür) yerleştirme tabanı. "
                   "KPSS atamaları tek-seferlik ilan olduğundan eşleşme kısmidir.", "num"),
    "2025 Taban": ("2025'te yerleşen son adayın puanı (en düşük yerleşme puanı).", "num"),
    "2024": ("2024 yılı taban puanı; yıllar arası değişimi görmek için.", "num"),
    "2023": ("2023 yılı taban puanı; yıllar arası değişimi görmek için.", "num"),
    "2025": ("2025 yılı taban puanı.", "num"),
    "Trend": ("2025 tabanının bir önceki yıla göre değişimi (↑ yükseldi, ↓ düştü, → aynı).", "text"),
    "Şans": ("Girdiğin puana göre yerleşme şansı: Rahat (güvenli), Olası, Sınırda (riskli).", "text"),
    "Başarı Sırası": ("Yerleşen son adayın başarı sırası. Küçük sıra = daha yüksek başarı.", "num"),
    "Sıra": ("Yerleşen son adayın başarı sırası. Küçük sıra = daha yüksek başarı.", "num"),
    "Yüzdelik": ("Yerleşen son öğrencinin LGS yüzdelik dilimi. Küçük yüzdelik = daha başarılı.", "num"),
    "Lise": ("Sınavla öğrenci alan lisenin resmî adı.", "text"),
    "Yabancı Dil": ("Lisede okutulan birinci yabancı dil.", "text"),
    "2025 Taban Puan": ("2025'te liseye yerleşen son öğrencinin LGS puanı.", "num"),
    "Vakıf Prog.": ("Bu bölümün vakıf üniversitelerindeki program sayısı.", "num"),
    "Ücret Aralığı": ("Bölümün vakıf üniversitelerindeki en düşük – en yüksek yıllık öğrenim ücreti.", "num"),
    "Yıllık Ücret Aralığı": ("Üniversitenin programlarındaki en düşük – en yüksek yıllık öğrenim ücreti.", "num"),
    "Medyan": ("Bölümün vakıf üniversitelerindeki ortanca (medyan) yıllık öğrenim ücreti.", "num"),
    "Burs": ("Üniversitede burslu (tam/kısmi) program bulunup bulunmadığı.", "text"),
    "Sınav": ("Sınavın resmî adı.", "text"),
    "Başvuru": ("Sınav başvurularının alındığı tarih aralığı.", "text"),
    "Sınav Tarihi": ("Sınavın yapılacağı resmî tarih.", "date"),
    "Sonuç": ("Sonuçların açıklanacağı resmî tarih.", "date"),
}


_YIL_BASLIK_RE = re.compile(r"^(20\d{2})( Taban(?: Puan)?)?$")


def th_html(label, extra=""):
    """<th> üretir; başlık TH_TIPS'te tanımlıysa data-tip + data-type ekler (rule 3.17)."""
    t = TH_TIPS.get(label)
    if not t:
        # Yıl başlıkları artık dinamik ("2026 Taban", "2025"…) — sözlükte sabit anahtar
        # tutmak yerine kalıptan açıklama üretilir, böylece her yıl otomatik doğru olur.
        m = _YIL_BASLIK_RE.match(label)
        if m:
            y = m.group(1)
            t = ((f"{y} yılında yerleşen son adayın puanı (en düşük yerleşme puanı)." if m.group(2)
                  else f"{y} yılı taban puanı; yıllar arası değişimi görmek için."), "num")
    if not t:
        return f"<th{(' ' + extra) if extra else ''}>{label}</th>"
    tip = t[0].replace('"', "&quot;")
    return f'<th data-tip="{tip}" data-type="{t[1]}"{(" " + extra) if extra else ""}>{label}</th>'


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
  SV.spark = function(vals, invert){
    // invert=true → küçük değer daha iyi (başarı sırası): iyileşme yeşil + grafikte yukarı
    var pts=[]; for(var i=0;i<vals.length;i++){ var v=vals[i]; if(v!=null && !isNaN(v)) pts.push({i:i,v:Number(v)}); }
    if(pts.length<2) return '';
    var w=42,h=14,pad=2,xs=vals.length-1||1;
    var vs=pts.map(function(p){return p.v;}); var mn=Math.min.apply(null,vs),mx=Math.max.apply(null,vs),rng=mx-mn||1;
    var d=pts.map(function(p){var x=pad+(p.i/xs)*(w-2*pad);var fr=(p.v-mn)/rng;
      var y=invert?(pad+fr*(h-2*pad)):(h-pad-fr*(h-2*pad));return x.toFixed(1)+','+y.toFixed(1);}).join(' ');
    var f=pts[0].v,l=pts[pts.length-1].v,better=invert?(l<f):(l>f),worse=invert?(l>f):(l<f);
    var col=better?'#16a34a':(worse?'#dc2626':'#94a3b8');
    var ttl=invert?(l<f?'Başarı sırası iyileşiyor (2023→2025)':(l>f?'Başarı sırası geriliyor':'Sabit')):'';
    return '<svg width="'+w+'" height="'+h+'" viewBox="0 0 '+w+' '+h+'" style="vertical-align:middle;margin-left:6px;flex:0 0 auto"'+(ttl?' aria-label="'+ttl+'"><title>'+ttl+'</title':' aria-hidden="true"')+'><polyline fill="none" stroke="'+col+'" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" points="'+d+'"/></svg>';
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
  // Sonuç tablolarını (tercih robotları) CSV indir — Excel/Sheets'te Türkçe karakter için UTF-8 BOM.
  SV.downloadCSV = function(filename, headers, rows){
    function cell(v){
      v = v==null ? '' : String(v);
      return /[",\n;]/.test(v) ? '"'+v.replace(/"/g,'""')+'"' : v;
    }
    var lines = [headers.map(cell).join(';')].concat(rows.map(function(r){ return r.map(cell).join(';'); }));
    var blob = new Blob(['﻿'+lines.join('\r\n')], {type:'text/csv;charset=utf-8;'});
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a'); a.href=url; a.download=filename; document.body.appendChild(a); a.click();
    document.body.removeChild(a); setTimeout(function(){ URL.revokeObjectURL(url); }, 1000);
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

# Logo yükleme dayanıklılığı: yavaş bağlantıda ilk yüklemede kopan üniversite
# logolarını otomatik yeniden dener (kullanıcı elle "yenile" demek zorunda kalmaz).
LOGO_RETRY_JS = r"""<script nonce="__NONCE__">
(function(){
  document.addEventListener('error',function(e){
    var t=e.target;
    if(!t||t.tagName!=='IMG'||!t.classList||!t.classList.contains('uni-logo'))return;
    var n=+(t.getAttribute('data-rt')||0); if(n>=2)return;
    t.setAttribute('data-rt',n+1);
    var u=(t.getAttribute('src')||'').split('?')[0];
    if(u) setTimeout(function(){t.setAttribute('src',u+'?r='+(n+1)+'-'+Date.now());},350*(n+1));
  },true);
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


def base(slug, title, desc, body, *, extra_head="", extra_ld=None, og_image=None, share=False):
    canonical = SITE + "/" + (slug if slug != "index.html" else "")
    share_js = SHARE_JS if share else ""
    og_url = SITE + (og_image if og_image else "/assets/og.png")
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
<meta property="og:image" content="{og_url}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="tr_TR">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{og_url}">
<script nonce="__NONCE__" type="application/ld+json">{ld_escape(ld)}</script>
<script nonce="__NONCE__">
  (function(){{ try {{ if (localStorage.getItem('sinavveri-theme') === 'dark') document.documentElement.setAttribute('data-theme','dark'); }} catch(e){{}} }})();
</script>
{SV_HELPER_JS}
{TABLE_JS}
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
      <button type="button" class="push-toggle" id="pushToggle" hidden aria-label="Sınav sonucu bildirimlerine abone ol" title="Sınav sonucu açıklandığında bildirim al"><span class="toggle-icon">🔕</span><span class="toggle-text">Bildirimler</span></button>
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
// Sınav sonucu bildirimleri — push-server (SinavVeri.com/push-server/server.js).
// Buton yalnız tarayıcı Push API'yi destekliyorsa görünür (Safari/eski tarayıcı → hiç görünmez).
(function(){{
  var btn=document.getElementById('pushToggle'); if(!btn) return;
  if(!('serviceWorker' in navigator) || !('PushManager' in window)) return;
  var ic=btn.querySelector('.toggle-icon'), tx=btn.querySelector('.toggle-text');
  var API='https://sinavveri.com/api/push';

  function b64ToArr(b64){{
    var pad='='.repeat((4-b64.length%4)%4), s=(b64+pad).replace(/-/g,'+').replace(/_/g,'/');
    var raw=atob(s), out=new Uint8Array(raw.length);
    for(var i=0;i<raw.length;i++) out[i]=raw.charCodeAt(i);
    return out;
  }}
  function paint(on){{
    ic.textContent = on ? '🔔' : '🔕';
    tx.textContent = on ? 'Bildirimler Açık' : 'Bildirimler';
    btn.classList.toggle('on', on);
    btn.title = on ? 'Sınav sonucu bildirimleri açık — kapatmak için tıkla' : 'Sınav sonucu açıklandığında bildirim al';
  }}
  function currentSub(){{
    return navigator.serviceWorker.ready.then(function(reg){{ return reg.pushManager.getSubscription(); }});
  }}
  btn.removeAttribute('hidden');
  currentSub().then(function(sub){{ paint(!!sub); }}).catch(function(){{}});

  btn.addEventListener('click',function(){{
    currentSub().then(function(sub){{
      if(sub){{
        return sub.unsubscribe().then(function(){{
          return fetch(API+'/unsubscribe',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{endpoint:sub.endpoint}})}});
        }}).then(function(){{ paint(false); }});
      }}
      if(Notification.permission==='denied'){{
        alert('Bildirimlere izin vermemişsiniz. Tarayıcı ayarlarından bu site için bildirim iznini açmanız gerekir.');
        return;
      }}
      return Notification.requestPermission().then(function(perm){{
        if(perm!=='granted') return;
        return fetch(API+'/vapid-public-key').then(function(r){{return r.json();}}).then(function(j){{
          return navigator.serviceWorker.ready.then(function(reg){{
            return reg.pushManager.subscribe({{userVisibleOnly:true, applicationServerKey:b64ToArr(j.key)}});
          }});
        }}).then(function(newSub){{
          return fetch(API+'/subscribe',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(newSub)}})
            .then(function(){{ paint(true); }});
        }});
      }});
    }}).catch(function(err){{ console.warn('push abonelik hatası',err); }});
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
        ths.forEach(function(o){{o.dataset.dir='0';o.removeAttribute('aria-sort');var a=o.querySelector('.s-arrow');if(a)a.remove();}});
        th.dataset.dir=dir>0?'1':'-1';
        th.setAttribute('aria-sort',dir>0?'ascending':'descending');
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
{LOGO_RETRY_JS}
<script nonce="__NONCE__">if('serviceWorker' in navigator){{navigator.serviceWorker.register('/sw.js').catch(function(){{}});}}</script>
{share_js}
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
        else:
            _bs = r.get("bs") or ""
            if r.get("t") == "D" and ("Ücretli" in _bs or "İndirimli" in _bs):
                r["t"] = "DU"  # Devlet üniv. paralı program (Ücretli VEYA %X İndirimli — ör. UOLP)
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


def hist_sira(r, year):
    for h in r.get("hist", []):
        if h[0] == year:
            return h[2]
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
    """Grup için 2022-2025 medyan + en iyi BAŞARI SIRASI trend grafiği (Plotly).
    Puan değil sıra: puan çarpanları yıldan yıla değişir; başarı sırası asıl gösterge.
    Y ekseni ters (autorange reversed) → yukarı = daha iyi (küçük) sıra."""
    years = [2022, 2023, 2024, 2025]
    med, best = [], []
    for yr in years:
        if yr == 2025:
            vals = [r.get("sira") for r in group_recs if r.get("sira")]
        else:
            vals = [hist_sira(r, yr) for r in group_recs]
            vals = [v for v in vals if v]
        med.append(median(vals))
        best.append(min(vals) if vals else None)
    if sum(1 for m in med if m) < 2:
        return ""  # yeterli geçmiş yok
    data = [
        {"x": years, "y": med, "name": "Medyan başarı sırası", "mode": "lines+markers",
         "line": {"color": "#b45309", "width": 3}, "connectgaps": True},
        {"x": years, "y": best, "name": "En iyi (en düşük) sıra", "mode": "lines+markers",
         "line": {"color": "#1e3a8a", "width": 2, "dash": "dot"}, "connectgaps": True},
    ]
    layout = {
        "margin": {"l": 62, "r": 16, "t": 10, "b": 36}, "height": 300,
        "xaxis": {"tickvals": years, "tickformat": "d", "gridcolor": "rgba(128,128,128,.15)"},
        "yaxis": {"title": {"text": "Başarı Sırası"}, "autorange": "reversed", "tickformat": ",d", "gridcolor": "rgba(128,128,128,.15)"},
        "legend": {"orientation": "h", "y": -0.18, "x": 0}, "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)", "font": {"family": "Segoe UI, Arial, sans-serif", "size": 12},
        "hovermode": "x unified",
    }
    cfg = {"displayModeBar": False, "responsive": True}
    return (f'<div class="chart-card"><h3>Yıllara Göre Başarı Sırası Trendi (2022–2025)</h3>'
            f'<div style="font-size:11.5px;color:var(--fg-faded);margin:-2px 0 8px">Eksen ters: <b>yukarı = daha iyi (küçük) sıra</b>. Puan çarpanları yıldan yıla değiştiği için trend puanla değil sırayla gösterilir.</div>'
            f'<div id="{divid}" style="width:100%"></div></div>'
            f'<script nonce="__NONCE__">Plotly.newPlot("{divid}",'
            + json.dumps(data) + "," + json.dumps(layout) + "," + json.dumps(cfg) + ");</script>")


# ───────────────────────── TAKVİM VERİSİ ─────────────────────────
CAL = json.loads((ROOT / "data" / "takvim-2026.json").read_text(encoding="utf-8"))
# ── VERİ YILLARI — SABİT YAZILMAZ, meta dosyalarından okunur ─────────────────
# NEDEN (2026-08-19): sayfa başlıkları/kaynak notları "YÖK Atlas {YKS_YIL}", "MEB {LGS_YIL} LGS",
# "2025 Taban" diye elle yazılıydı. Veri 2026'ya geçtiğinde etiketler 2025 kalıyor ve
# site YANLIŞ YIL gösteriyordu. Artık her etiket ilgili çekicinin meta dosyasından gelir.
def _meta(ad):
    f = ROOT / "data" / ad
    try:
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    except Exception:
        return {}


YOKATLAS_META = _meta("yokatlas_meta.json")
# taban_yili = taban puanı/başarı sırasının ait olduğu YERLEŞTİRME yılı (kılavuz yılından
# farklı olabilir: kılavuz Temmuz'da çıkar, o yılın yerleştirmesi Ağustos'ta biter).
YKS_YIL = int(YOKATLAS_META.get("taban_yili") or YOKATLAS_META.get("yil") or 2025)
YKS_HIST = [int(x) for x in (YOKATLAS_META.get("hist_yillari") or [YKS_YIL - 1, YKS_YIL - 2, YKS_YIL - 3])]
YKS_KILAVUZ_YIL = int(YOKATLAS_META.get("yil") or YKS_YIL)

LGS_META = _meta("lgs_meta.json")
LGS_YIL = int(LGS_META.get("yil") or 2025)
LGS_HIST = [int(x) for x in (LGS_META.get("yillar") or [LGS_YIL, LGS_YIL - 1, LGS_YIL - 2, LGS_YIL - 3])][1:]

OSYM_META = _meta("osym_meta.json")


def osym_yil(exam):
    """TUS/DUS/DGS/KPSS için veri yılı. DGS 2026 yerleştirmesi henüz yapılmadığı için
    sınav başına AYRI yıl tutulur — hepsini tek yıla sabitlemek yanlış etiket üretir."""
    y = OSYM_META.get("yillar") or {}
    return int(y.get(exam) or OSYM_META.get("yil") or 2025)


_demo_p = ROOT / "data" / "demografi.json"
DEMOGRAFI = json.loads(_demo_p.read_text(encoding="utf-8")) if _demo_p.exists() else {}
_univ_p = ROOT / "data" / "universiteler.json"
UNIV = json.loads(_univ_p.read_text(encoding="utf-8")) if _univ_p.exists() else {}
_vid_p = ROOT / "data" / "uni_videos.json"
UNI_VIDEOS = json.loads(_vid_p.read_text(encoding="utf-8")) if _vid_p.exists() else {}


def tr_phone(raw):
    """Ham telefonu (ör. 2223350581) Türkçe biçime + tıklanır tel: linkine çevirir."""
    d = re.sub(r"\D", "", raw or "")
    if d.startswith("90") and len(d) == 12:
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    if len(d) != 10:
        return None
    return {"display": f"0{d[0:3]} {d[3:6]} {d[6:8]} {d[8:10]}", "tel": f"+90{d}"}


def uni_video(u):
    """Üniversitenin seçili tanıtım video kaydı (id/başlık) veya None."""
    info = uni_info(u)
    uid = info.get("id")
    if uid and str(uid) in UNI_VIDEOS:
        return UNI_VIDEOS[str(uid)]
    nk = "n_" + _uni_norm(u).replace(" ", "-")
    return UNI_VIDEOS.get(nk)


def _uni_norm(s):
    """Üniversite adı normalize (universiteler.json anahtarıyla aynı kural)."""
    s = (s or "").strip().lower().replace("i̇", "i")
    s = re.sub(r"\([^)]*\)", "", s)
    tr = {"ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c", "â": "a", "î": "i", "û": "u"}
    s = "".join(tr.get(c, c) for c in s)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def uni_info(u):
    return UNIV.get(_uni_norm(u)) or {}


def uni_logo_html(u, size=40, cls="uni-logo"):
    """Üniversite logosu <img> (self-host). ID'li → <id>.png; ID'siz (KKTC/yurtdışı)
    → isim-bazlı n_<normAd>.png fallback. Yoksa boş döner."""
    info = uni_info(u)
    uid = info.get("id")
    logos = ROOT / "assets" / "logos"
    src = None
    if uid and (logos / f"{uid}.png").exists():
        src = f"/assets/logos/{uid}.png"
    else:
        nk = "n_" + _uni_norm(u).replace(" ", "-")
        if (logos / f"{nk}.png").exists():
            src = f"/assets/logos/{nk}.png"
    if not src:
        return ""
    return (f'<img class="{cls}" src="{src}" alt="{html_escape(u)} logosu" '
            f'width="{size}" height="{size}" loading="lazy" decoding="async">')


def nf_tr(n):
    try:
        return f"{int(n):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def tr_loc(s):
    """Türkçe bulunma hâli eki (ünlü uyumu + ünsüz benzeşmesi): İstanbul'da, İzmir'de, Sinop'ta."""
    s = (s or "").strip()
    if not s:
        return ""
    vowels = [c for c in s.lower() if c in "aeıioöuü"]
    back = vowels[-1] in "aıou" if vowels else True
    hard = s[-1] in "fstkçşhpFSTKÇŞHP"
    ek = ("ta" if hard else "da") if back else ("te" if hard else "de")
    return f"{s}'{ek}"


def tr_loc_ki(s):
    return tr_loc(s) + "ki"


_OG_FONT = {}


def _font(size, bold=False):
    key = (size, bold)
    if key not in _OG_FONT:
        from PIL import ImageFont
        p = ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
             else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        try:
            _OG_FONT[key] = ImageFont.truetype(p, size)
        except Exception:
            _OG_FONT[key] = ImageFont.load_default()
    return _OG_FONT[key]


def gen_uni_og(slug, u, info, recs):
    """Üniversiteye özel 1200×630 OG sosyal paylaşım görseli üretir (idempotent).
    Marka + logo + ad + il/tür/kuruluş + öğrenci/akademisyen/program istatistikleri."""
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    ogdir = ROOT / "assets" / "og" / "uni"
    ogdir.mkdir(parents=True, exist_ok=True)
    dest = ogdir / f"{slug}.png"
    if dest.exists() and dest.stat().st_size > 1000:
        return f"/assets/og/uni/{slug}.png"

    W, H = 1200, 630
    img = Image.new("RGB", (W, H), (21, 25, 43))  # koyu lacivert zemin
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 14, H], fill=(245, 158, 11))           # sol turuncu şerit
    d.rectangle([0, H - 70, W, H], fill=(17, 20, 35))         # alt bar

    # Logo (varsa, beyaz yuvarlak zemin)
    x0 = 70
    uid = info.get("id")
    lp = None
    if uid and (ROOT / "assets" / "logos" / f"{uid}.png").exists():
        lp = ROOT / "assets" / "logos" / f"{uid}.png"
    else:
        nk = "n_" + _uni_norm(u).replace(" ", "-")
        if (ROOT / "assets" / "logos" / f"{nk}.png").exists():
            lp = ROOT / "assets" / "logos" / f"{nk}.png"
    if lp:
        try:
            logo = Image.open(lp).convert("RGBA").resize((150, 150))
            d.rounded_rectangle([x0, 70, x0 + 174, 70 + 174], radius=20, fill=(255, 255, 255))
            img.paste(logo, (x0 + 12, 82), logo)
        except Exception:
            lp = None
    tx = (x0 + 200) if lp else x0

    # Üniversite adı (sığması için kelime sar, max 2 satır)
    name = u.split(" (")[0]
    fn = _font(54, True)
    words = name.split(" ")
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=fn) <= (W - tx - 60):
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > 2:
        lines = lines[:2]
        lines[1] = lines[1][:30] + "…"
    ty = 90 if len(lines) == 2 else 120
    for ln in lines:
        d.text((tx, ty), ln, font=fn, fill=(255, 255, 255))
        ty += 64

    # Alt başlık: il · tür · kuruluş
    sub_parts = [p for p in [info.get("il"), info.get("tur"), (info.get("kurulus") + " kuruluş") if info.get("kurulus") else ""] if p]
    if sub_parts:
        d.text((tx, ty + 6), "  ·  ".join(sub_parts), font=_font(30), fill=(245, 158, 11))

    # İstatistik kutuları
    stats = []
    if info.get("ogrenci"):
        stats.append(("ÖĞRENCİ", nf_tr(info["ogrenci"])))
    if info.get("akademisyen"):
        stats.append(("AKADEMİSYEN", nf_tr(info["akademisyen"])))
    stats.append(("PROGRAM", str(len(recs))))
    bw, bx, by = 320, 70, 380
    for lbl, val in stats[:3]:
        d.rounded_rectangle([bx, by, bx + bw - 20, by + 110], radius=16, fill=(31, 37, 58))
        d.text((bx + 24, by + 20), val, font=_font(46, True), fill=(255, 255, 255))
        d.text((bx + 24, by + 76), lbl, font=_font(22), fill=(150, 160, 185))
        bx += bw

    # Alt bar metni
    d.text((70, H - 52), "SınavVeri.com", font=_font(30, True), fill=(245, 158, 11))
    d.text((W - 430, H - 50), f"{YKS_YIL} Taban Puanları · YÖK Atlas", font=_font(26), fill=(200, 208, 225))

    img.save(dest, "PNG")
    return f"/assets/og/uni/{slug}.png"


def uni_analiz(u, info, recs):
    """SinavVeri.com Üniversite Analizi — künye + program verisinden türetilmiş özgün metin.
    Şablon değil: değerlere göre dallanan cümleler kurar."""
    il = info.get("il") or (next((r.get("il") for r in recs if r.get("il")), ""))
    tur = info.get("tur") or ""
    kur = info.get("kurulus") or ""
    ogr = info.get("ogrenci") or 0
    aka = info.get("akademisyen") or 0
    fak = len({r.get("fak") for r in recs if r.get("fak")})
    nprog = len(recs)
    pt = {}
    for r in recs:
        if r.get("p"):
            pt[r["p"]] = pt.get(r["p"], 0) + 1
    # En güçlü 3 bölüm (en düşük başarı sırası)
    top = [r for r in recs if r.get("sira")]
    top.sort(key=lambda r: r["sira"])
    top_names = []
    seen = set()
    for r in top:
        g = r.get("g") or r.get("b")
        if g and g not in seen:
            seen.add(g)
            top_names.append(g)
        if len(top_names) >= 3:
            break

    s = []
    # 1. Kuruluş + konum + tür
    p1 = f"<b>{html_escape(u.split(' (')[0].title() if u.isupper() else u)}</b>"
    if kur:
        yas = 2026 - int(kur)
        konum = (f"{tr_loc(il)} kurulan bir {tur.lower()} üniversitesi olan " if il and tur else "kurulan ")
        p1 = f"{kur} yılında {konum}<b>{html_escape(u)}</b>, {yas} yıllık akademik geçmişe sahiptir."
    else:
        p1 = f"<b>{html_escape(u)}</b>" + (f", {tr_loc(il)} yer alan bir {tur.lower()} üniversitesidir." if il and tur else " kurumudur.")
    s.append(p1)

    # 2. Öğrenci + akademisyen
    if ogr and aka:
        oran = round(ogr / aka)
        s.append(f"Toplam <b>{nf_tr(ogr)} öğrenci</b> ve <b>{nf_tr(aka)} akademisyen</b> ile öğretim üyesi başına yaklaşık {oran} öğrenci düşmektedir"
                 + (" — bu, görece bireysel bir eğitim ortamına işaret eder." if oran <= 18 else "." if oran <= 30 else " — kalabalık bir öğrenci profili söz konusudur."))
    elif ogr:
        s.append(f"Üniversitede toplam <b>{nf_tr(ogr)} öğrenci</b> öğrenim görmektedir.")

    # 3. Program zenginliği + güçlü bölümler
    p3 = f"YÖK Atlas {YKS_YIL} verisine göre {nprog} programı"
    if fak:
        p3 += f" ve {fak} fakülte/birimi"
    p3 += " bulunan üniversitenin"
    if top_names:
        p3 += f" giriş başarısı en yüksek bölümleri <b>{html_escape(', '.join(top_names))}</b> olarak öne çıkmaktadır."
    else:
        p3 += " bölümleri çeşitli puan türlerine yayılmaktadır."
    s.append(p3)

    # 4. Puan türü dağılımı (varsa)
    if pt:
        parts = [f"{PT_LABEL.get(k, k)} ({v})" for k, v in sorted(pt.items(), key=lambda kv: -kv[1])]
        s.append(f"Program dağılımı puan türüne göre: {html_escape(', '.join(parts))}.")

    return " ".join(s)


def uni_kunye_html(u, recs):
    """Üniversite künye kartı: logo + istatistik grid + analiz + kurumsal bilgiler + harita."""
    info = uni_info(u)
    if not info:
        return ""
    il = info.get("il") or (next((r.get("il") for r in recs if r.get("il")), ""))
    fak = len({r.get("fak") for r in recs if r.get("fak")})
    logo = uni_logo_html(u, size=72, cls="uni-logo-lg")
    # İstatistik kutuları
    stats = []
    if info.get("ogrenci"):
        stats.append(("👥", "Öğrenci", nf_tr(info["ogrenci"])))
    if info.get("akademisyen"):
        stats.append(("🎓", "Akademisyen", nf_tr(info["akademisyen"])))
    if fak:
        stats.append(("🏛️", "Fakülte/Birim", str(fak)))
    stats.append(("📚", "Program", str(len(recs))))
    if info.get("kurulus"):
        stats.append(("📅", "Kuruluş", info["kurulus"]))
    if info.get("tur"):
        stats.append(("🏷️", "Tür", info["tur"]))
    stat_html = "".join(
        f'<div class="uk-stat"><span class="uk-ico">{i}</span><span class="uk-val">{html_escape(v)}</span><span class="uk-lbl">{html_escape(l)}</span></div>'
        for i, l, v in stats)

    # Kurumsal bilgiler satırları (öğrenci kırılımı tam-genişlik, yan yana)
    rows = []
    if info.get("website"):
        w = info["website"].replace("http://", "").replace("https://", "").rstrip("/")
        rows.append(("Web", f'<a href="{html_escape(info["website"])}" target="_blank" rel="noopener nofollow">{html_escape(w)}</a>', False))
    if info.get("rektor"):
        rows.append(("Rektör", html_escape(info["rektor"]), False))
    ph = tr_phone(info.get("telefon"))
    if ph:
        rows.append(("Telefon", f'<a href="tel:{ph["tel"]}">{ph["display"]}</a>', False))
    elif info.get("telefon"):
        rows.append(("Telefon", html_escape(info["telefon"]), False))
    if info.get("bolge"):
        rows.append(("Bölge", html_escape(info["bolge"]), False))
    if info.get("lisans") or info.get("onlisans"):
        det = []
        for lbl, k in [("Lisans", "lisans"), ("Önlisans", "onlisans"), ("Yüksek lisans", "yukseklisans"), ("Doktora", "doktora")]:
            if info.get(k):
                det.append(f"{lbl}: {nf_tr(info[k])}")
        if det:
            rows.append(("Öğrenci kırılımı", html_escape(" · ".join(det)), True))
    kurumsal = "".join(
        f'<div class="uk-row{" uk-row-full" if full else ""}"><dt>{l}</dt><dd>{v}</dd></div>'
        for l, v, full in rows)

    # Harita + Tanıtım Videosu — tab/akordeon (tıkla aç-kapa, içerik hemen altında)
    adres = info.get("adres") or ""
    uname = u.split(" (")[0]
    vd = uni_video(u)
    map_q = html_escape(((uname + " " + (il or "")).strip()).replace(" ", "+")) if (adres or il) else ""
    panels = []   # (buton, panel-içerik)
    if map_q:
        map_embed = f'https://www.google.com/maps?q={map_q}&output=embed&hl=tr'
        panels.append(("🗺️ Haritada Aç",
                       (f'<div class="uk-adres">📍 {html_escape(adres)} '
                        f'<button type="button" class="uk-copy" data-adres="{html_escape(adres)}">📋 Kopyala</button></div>' if adres else "")
                       + f'<iframe class="uk-embed" loading="lazy" referrerpolicy="no-referrer-when-downgrade" data-src="{map_embed}" title="{html_escape(uname)} harita"></iframe>'))
    if vd and vd.get("id"):
        panels.append(("🎬 Tanıtım Videosu",
                       f'<div class="uk-vtitle">{html_escape(vd.get("t",""))}{(" · " + html_escape(vd.get("ch",""))) if vd.get("ch") else ""}</div>'
                       f'<iframe class="uk-embed" loading="lazy" allowfullscreen referrerpolicy="strict-origin-when-cross-origin" '
                       f'data-src="https://www.youtube-nocookie.com/embed/{html_escape(vd["id"])}?rel=0" title="{html_escape(uname)} tanıtım videosu"></iframe>'))
    harita = ""
    if panels:
        tabs = "".join(f'<button type="button" class="uk-tab" data-tab="{i}">{lbl}</button>' for i, (lbl, _) in enumerate(panels))
        pans = "".join(f'<div class="uk-pan" data-pan="{i}" hidden>{c}</div>' for i, (_, c) in enumerate(panels))
        harita = f'<div class="uk-tabs">{tabs}</div>{pans}'

    analiz = uni_analiz(u, info, recs)
    return f"""
<div class="uk-card">
  <div class="uk-head">{logo}<div class="uk-stats">{stat_html}</div></div>
  <div class="uk-analiz"><h2>📊 SinavVeri.com Üniversite Analizi</h2><p>{analiz}</p></div>
  {f'<div class="uk-kurumsal"><h3>Kurumsal Bilgiler</h3><dl>{kurumsal}</dl></div>' if kurumsal else ''}
  {harita}
</div>"""


def uni_yorum_html(u):
    """Yorumlar & değerlendirmeler — şimdilik PASİF (yakında). Backend bağlanınca aktifleşecek
    şekilde DOM hazır: .uk-rev[data-uni], form alanları disabled + 'yakında' rozeti."""
    uname = html_escape(u.split(" (")[0])
    return f"""<div class="uk-rev" data-uni="{html_escape(u)}">
  <div class="uk-rev-head"><h3>💬 Öğrenci Yorumları & Değerlendirmeleri</h3><span class="uk-soon">Yakında</span></div>
  <p class="uk-rev-note">{uname} hakkında öğrenci deneyimleri ve puanlamaları <b>çok yakında</b> burada olacak. Kampüs, eğitim kalitesi, sosyal yaşam ve barınma hakkında gerçek öğrenci görüşleri ekleyebileceksiniz.</p>
  <form class="uk-rev-form" onsubmit="return false" aria-disabled="true">
    <div class="uk-rev-stars" title="Puanlama yakında aktifleşecek">★★★★★</div>
    <textarea placeholder="Deneyimini paylaş (yakında açılacak)…" disabled></textarea>
    <button type="button" class="btn btn-primary" disabled>Gönder</button>
  </form>
</div>"""


TUR_LABEL = {"yks": ("YKS", "tag-yks"), "lgs": ("LGS", "tag-lgs"), "kpss": ("KPSS", "tag-kpss"), "other": ("Diğer", "tag-other")}
AY_TR = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def fmt_date(iso):
    try:
        y, m, d = iso.split("-")
        return f"{int(d)} {AY_TR[int(m)]} {y}"
    except Exception:
        return iso


# ───────────────────── DİNAMİK TARİH / ÇEKİM MOTORU ─────────────────────
# NEDEN (2026-08-19): sayfalarda "2026'da TYT 20 Haziran'da yapılacaktır" gibi SABİT
# çekimli cümleler vardı — sınav geçtikten sonra bile "yapılacaktır" yazıyordu. Artık
# tüm tarih ifadeleri BUILD ANINDA bugüne göre çekimlenir. build.py cron'da 3 saatte bir
# koştuğu için sayfa kendini gün içinde en geç 3 saatte doğru çekime çevirir.
#
# İKİNCİ KATMAN — GERÇEKLEŞEN tarih düzeltmesi: planlanan takvim ile ÖSYM'nin fiilî
# duyuru tarihi ayrışabiliyor (ör. 2026-YKS sonucu takvimde 22 Tem, fiilen 21 Tem
# açıklandı). `GERCEKLESEN` tablosu duyuru arşivinden türetilir ve planlanan tarihi ezer.

BUGUN = date.today()
# Takvim verisi hem tam ("6 Şubat") hem kısa ("6 Şub") ay adı kullanıyor — ikisi de tanınır.
AY_KISA = ["", "Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
_AY_NO = {a: i for i, a in enumerate(AY_TR) if a}
_AY_NO.update({a: i for i, a in enumerate(AY_KISA) if a})
# Uzun adlar ÖNCE: alternatifte "Mart" | "Mar" sırası korunmazsa "Mart" yalnız "Mar" eşleşir.
AY_RE = "|".join(sorted((a for a in _AY_NO), key=len, reverse=True))
TR_TARIH_RE = re.compile(r"\b(\d{1,2})\s+(" + AY_RE + r")\s+(20\d{2})\b")

# Yıl için Türkçe bulunma-hâli eki: okunuşun SON kelimesine göre (2026 'yirmi altı' → 'da').
_YIL_EK_BIRLER = {1: "de", 2: "de", 3: "te", 4: "te", 5: "te", 6: "da", 7: "de", 8: "de", 9: "da"}
_YIL_EK_ONLAR = {1: "da", 2: "de", 3: "da", 4: "ta", 5: "de", 6: "ta", 7: "te", 8: "de", 9: "da"}


def yil_lok(y):
    """2026 → "2026'da", 2025 → "2025'te" (bulunma hâli, okunuşa göre doğru ek)."""
    y = int(y)
    b, o = y % 10, (y % 100) // 10
    ek = _YIL_EK_BIRLER.get(b) or _YIL_EK_ONLAR.get(o) or "de"
    return f"{y}'{ek}"


def _d(iso):
    """ISO metni → date; çözülemezse None (muğlak 'Haziran 2026 sonu' gibi değerler)."""
    if not iso or not isinstance(iso, str):
        return None
    try:
        return date.fromisoformat(iso[:10])
    except ValueError:
        return None


def gecmis_mi(iso):
    d = _d(iso)
    return d is not None and d < BUGUN


def bugun_mu(iso):
    return _d(iso) == BUGUN


def kalan_gun(iso):
    """Bugünden hedefe kalan gün (geçmişse negatif); çözülemezse None."""
    d = _d(iso)
    return None if d is None else (d - BUGUN).days


def cekim(iso, gelecek, gecmis, bugun=None):
    """Tarihe göre fiil/ifade seçer. Tarih çözülemezse GELECEK biçimi (güvenli varsayılan)."""
    d = _d(iso)
    if d is None:
        return gelecek
    if d < BUGUN:
        return gecmis
    if d == BUGUN:
        return bugun or gelecek
    return gelecek


def tarih_ifade(iso, gelecek="yapılacak", gecmis="yapıldı", bugun=None):
    """'20 Haziran 2026 tarihinde yapıldı' — 'tarihinde' bilinçli: yıl ekini (2026'da/2025'te)
    cümlenin ortasında tekrar üretmek gerekmez, her yıl için doğru okunur."""
    d = _d(iso)
    if d is None:
        return ""
    return f"{fmt_date(iso)} tarihinde {cekim(iso, gelecek, gecmis, bugun)}"


def gun_rozet(iso, gecmis_lbl="tamamlandı", bugun_lbl="bugün"):
    """Liste maddelerinin sonuna eklenen küçük durum çipi. Boş dönerse çip basılmaz."""
    d = _d(iso)
    if d is None:
        return ""
    fark = (d - BUGUN).days
    if fark < 0:
        return f'<span class="tarih-cip gecmis">✓ {gecmis_lbl}</span>'
    if fark == 0:
        return f'<span class="tarih-cip bugun">● {bugun_lbl}</span>'
    if fark == 1:
        return '<span class="tarih-cip yakin">⏳ yarın</span>'
    if fark <= 30:
        return f'<span class="tarih-cip yakin">⏳ {fark} gün kaldı</span>'
    return f'<span class="tarih-cip">⏳ {fark} gün kaldı</span>'


def _metinden_son_tarih(metin):
    """Metindeki SON 'GG Ay YYYY' tarihini ISO olarak döndürür.
    NEDEN sonuncusu: 'Başvuru: 6 Şubat – 2 Mart 2026' gibi aralıklarda durum BİTİŞ
    tarihine göre belirlenir (başvuru 2 Mart'ta kapanır, 6 Şubat'ta değil)."""
    son = None
    for m in TR_TARIH_RE.finditer(metin):
        g, ay, y = m.group(1), m.group(2), m.group(3)
        ay_no = _AY_NO.get(ay)
        if not ay_no:
            continue
        try:
            son = f"{int(y):04d}-{ay_no:02d}-{int(g):02d}"
        except ValueError:
            continue
    return son


def tarih_durumlu(metin, gecmis_lbl="tamamlandı"):
    """İçinde 'GG Ay YYYY' tarihi geçen SERBEST METNE bugüne göre durum çipi ekler.
    Tüm sınav rehberi 'Tarihleri' listeleri bundan geçer → tek yerden, her sayfada
    doğru çekim. Tarih yoksa metin AYNEN döner (zarar vermez)."""
    iso = _metinden_son_tarih(metin)
    if not iso:
        return metin
    cip = gun_rozet(iso, gecmis_lbl=gecmis_lbl)
    return f"{metin} {cip}" if cip else metin


# ── GERÇEKLEŞEN tarihler: ÖSYM/MEB duyuru arşivinden (planlanan takvimi ezer) ──
# ⚠ Arşiv 2015'e kadar uzanıyor ve duyuru TARİHİ ile SINAV YILI aynı değil
# (ör. "2025-DUS 1. Dönem: Yerleştirme Sonuçları Açıklandı" duyurusu 24 Nis 2026'da yayımlandı).
# Bu yüzden anahtar BAŞLIKTAN okunan sınav yılıdır, duyurunun yayım tarihi değil.
_SINAVLAR_RE = "YKS|LGS|KPSS|EKPSS|DGS|ALES|TUS|DUS|YDUS|YDS|YÖKDİL|MSÜ|STS"
# İki yazım da var: "2026-YKS" (yıl önde) ve "KPSS-2025/2" (yıl arkada).
_SINAV_YIL_RE = re.compile(r"\b(20\d{2})\s*[-–—]?\s*(?:" + _SINAVLAR_RE + r")\b")
_SINAV_YIL_RE2 = re.compile(r"\b(?:" + _SINAVLAR_RE + r")\s*[-–—/]?\s*(20\d{2})\b")


def _gerceklesen_yukle():
    """duyuru arşivi → {(sınav, yıl, aşama): 'YYYY-MM-DD'} — FİİLEN gerçekleşmiş tarihler.
    Aşama: 'sonuc' (sınav sonucu açıklandı) · 'yerlestirme' · 'tercih'.
    Duyuru arşivi 30 dk'da bir tazelendiği için bu tablo kendiliğinden güncel kalır."""
    out = {}
    for ad in ("osym_duyurular.json", "meb_duyurular.json"):
        f = ROOT / "data" / ad
        if not f.exists():
            continue
        try:
            kayitlar = json.loads(f.read_text(encoding="utf-8")).get("duyurular", [])
        except Exception:
            continue
        for k in kayitlar:
            sinav, baslik, tarih = k.get("sinav"), (k.get("baslik") or ""), (k.get("tarih") or "")
            if not sinav or len(tarih) < 10:
                continue
            if "Ek Yerleştirme" in baslik:      # ek yerleştirme ana takvim aşaması değil
                continue
            if "Yerleştirme Sonuçları" in baslik:
                asama = "yerlestirme"
            elif "Sınav Sonuçları" in baslik or "Sonuçları Açıklandı" in baslik:
                asama = "sonuc"
            elif k.get("tip") == "tercih" and "Tercihlerin Alınması" in baslik:
                asama = "tercih"
            else:
                continue
            m = _SINAV_YIL_RE.search(baslik) or _SINAV_YIL_RE2.search(baslik)
            # başlıkta sınav yılı yoksa (çoğunlukla MEB/LGS) duyuru yılına düşülür —
            # LGS aşamaları aynı takvim yılı içinde duyurulur, bu güvenli.
            yil = int(m.group(1)) if m else int(tarih[:4])
            anahtar = (sinav, yil, asama)
            # aynı sınav+yıl+aşama için EN ERKEN duyuru esas (sonraki düzeltme duyuruları değil)
            if anahtar not in out or tarih < out[anahtar]:
                out[anahtar] = tarih[:10]
    return out


GERCEKLESEN = _gerceklesen_yukle()


def fmt_gunay(iso):
    """'2026-06-20' → '20 Haziran' (yıl cümlede zaten geçiyorsa tekrar etmemek için)."""
    d = _d(iso)
    return f"{d.day} {AY_TR[d.month]}" if d else (iso or "")


def cal_bul(*parcalar):
    """Takvimden adında verilen parçaların HEPSİ geçen ilk sınavı bulur ({} = yok)."""
    for sv in CAL["sinavlar"]:
        if all(x in sv["ad"] for x in parcalar):
            return sv
    return {}


# Takvimdeki en ileri sınav yılı — sayfa başlıklarında "2026" SABİT yazılmasın diye.
TAKVIM_YILI = max((int(sv["sinav"][:4]) for sv in CAL["sinavlar"]
                   if isinstance(sv.get("sinav"), str) and sv["sinav"][:4].isdigit()),
                  default=BUGUN.year)


def sinav_aralik_metni(isolar):
    """['2026-06-20','2026-06-21'] → '20-21 Haziran 2026' (aynı ay) / tam tarih aralığı."""
    isolar = sorted(set(x for x in isolar if _d(x)))
    if not isolar:
        return ""
    ilk, son = _d(isolar[0]), _d(isolar[-1])
    if ilk == son:
        return fmt_date(isolar[-1])
    if (ilk.year, ilk.month) == (son.year, son.month):
        return f"{ilk.day}-{son.day} {AY_TR[son.month]} {son.year}"
    return f"{fmt_gunay(isolar[0])} – {fmt_date(isolar[-1])}"


def sinav_cumle(*parcalar, on=""):
    """Takvimden sınav tarihini alıp BUGÜNE göre çekimli cümle üretir:
    gelecekse '…14 Haziran tarihinde yapılacaktır.', geçmişse '…yapılmıştır.'"""
    iso = cal_bul(*parcalar).get("sinav")
    if not iso:
        return ""
    return (f"{on}{yil_lok(iso[:4])} {fmt_gunay(iso)} tarihinde "
            f"{cekim(iso, 'yapılacaktır', 'yapılmıştır', 'yapılıyor')}.")


def yks_oturum_cumle():
    """YKS iki oturumlu — TYT ve AYT tarihlerini tek cümlede, bugüne göre çekimli verir."""
    tyt = cal_bul("YKS", "TYT").get("sinav")
    ayt = cal_bul("YKS", "AYT").get("sinav")
    if not (tyt and ayt):
        return ""
    return (f"{yil_lok(tyt[:4])} TYT {fmt_gunay(tyt)}, AYT {fmt_gunay(ayt)} tarihinde "
            f"{cekim(ayt, 'yapılacaktır', 'yapılmıştır', 'yapılıyor')}.")


def yks_tarih_listesi():
    """YKS rehberindeki tarih listesi — takvim + ÖSYM duyuru arşivinden üretilir.
    Tercih dönemi ve yerleştirme sonucu satırları EKSİKTİ (2026-08-19'da eklendi);
    artık sezonun her aşaması otomatik görünür ve bugüne göre çekimlenir."""
    tyt, ayt = cal_bul("YKS", "TYT"), cal_bul("YKS", "AYT")
    if not tyt.get("sinav"):
        return []
    yil = int(tyt["sinav"][:4])
    o = []
    if tyt.get("basvuru"):
        o.append(f"Başvuru: {tyt['basvuru']}")
    o.append(f"TYT: {fmt_date(tyt['sinav'])}")
    if ayt.get("sinav"):
        o.append(f"AYT & YDT: {fmt_date(ayt['sinav'])}")
    sonuc = gercek_tarih("YKS", "sonuc", tyt.get("sonuc"), yil)
    if sonuc:
        o.append(f"Sınav sonucu: {fmt_date(sonuc)}")
    t_bas = tyt.get("tercih_bas") or gercek_tarih("YKS", "tercih", None, yil)
    t_bit = tyt.get("tercih_bit")
    if t_bas:
        o.append(f"Tercih dönemi: {tyt.get('tercih') or fmt_date(t_bas)}"
                 if t_bit else f"Tercih başlangıcı: {fmt_date(t_bas)}")
    yer = tyt.get("yerlestirme") or gercek_tarih("YKS", "yerlestirme", None, yil)
    if yer:
        o.append(f"Yerleştirme sonuçları: {fmt_date(yer)}")
    return o


def kart_meta(kod, *adlar):
    """Ana sayfa sınav kartının alt satırı. Kart hiçbir zaman geçmiş bir tarihi 'yaklaşan'
    gibi göstermez: sınav geçtiyse OTOMATİK sonraki aşamaya (sonuç → yerleştirme) döner.
    Çok oturumlu sınavlarda (ALES/1-2-3 gibi) SIRADAKİ oturum gösterilir; aynı haftaya
    düşen oturumlar (YKS TYT+AYT, KPSS GY-GK+ÖABT) tek aralıkta birleştirilir."""
    kayitlar = [k for k in (cal_bul(a) for a in adlar) if k.get("sinav")]
    if not kayitlar:
        return ""
    isolar = sorted({k["sinav"] for k in kayitlar})
    gelecek = [x for x in isolar if not gecmis_mi(x)]
    if gelecek:
        ilk = _d(gelecek[0])
        grup = [x for x in gelecek if (_d(x) - ilk).days <= 7]     # aynı oturum bloğu
        return f"Sınav: {sinav_aralik_metni(grup)} {gun_rozet(max(grup), 'yapıldı')}"

    yil = int(isolar[-1][:4])
    sonuc = gercek_tarih(kod, "sonuc", kayitlar[-1].get("sonuc"), yil)
    if sonuc and not gecmis_mi(sonuc):
        return f"Sonuç: {fmt_date(sonuc)} {gun_rozet(sonuc, 'açıklandı')}"
    # yerleştirme: önce takvimdeki alan, yoksa duyuru arşivi
    yer = next((k.get("yerlestirme") for k in kayitlar if k.get("yerlestirme")), None) \
        or gercek_tarih(kod, "yerlestirme", None, yil)
    if yer:
        return f"Yerleştirme sonucu: {fmt_date(yer)} {gun_rozet(yer, 'açıklandı')}"
    if sonuc:
        return f"Sonuç: {fmt_date(sonuc)} {gun_rozet(sonuc, 'açıklandı')}"
    return f"Sınav: {sinav_aralik_metni(isolar)} {gun_rozet(isolar[-1], 'yapıldı')}"


def takvim_kart_meta():
    """'Tüm Takvim' kartı: kaç sınavın geçtiği / kaçının kaldığı — otomatik."""
    isolar = [sv["sinav"] for sv in CAL["sinavlar"] if _d(sv.get("sinav"))]
    kalan = sum(1 for x in isolar if not gecmis_mi(x))
    if kalan:
        return f"{len(isolar)} sınav · {kalan} tanesi henüz yapılmadı"
    return f"{len(isolar)} sınav · tümü tamamlandı"


def gercek_tarih(sinav, asama, planlanan=None, yil=None):
    """Fiilî duyuru tarihi varsa onu, yoksa planlanan tarihi döndürür.
    `yil` verilmezse planlanan tarihin (yoksa bugünün) yılı kullanılır."""
    if yil is None:
        yil = int((planlanan or "")[:4]) if (planlanan or "")[:4].isdigit() else BUGUN.year
    return GERCEKLESEN.get((sinav, int(yil), asama)) or planlanan


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

    # Kart alt satırı SABİT YAZILMAZ — takvim + ÖSYM duyurularından bugüne göre üretilir.
    exams = [
        ("yks.html", "🎓", "YKS", "Yükseköğretim Kurumları Sınavı", "TYT + AYT ile üniversiteye giriş. ~2 milyon aday.",
         kart_meta("YKS", "YKS — TYT", "YKS — AYT", "YKS — YDT")),
        ("lgs.html", "🏫", "LGS", "Liselere Geçiş Sınavı", "8. sınıf merkezi sınavı ile liseye yerleşme.",
         kart_meta("LGS", "LGS")),
        ("kpss.html", "🏛️", "KPSS", "Kamu Personel Seçme Sınavı", "Kamu kadrolarına atanma için temel sınav.",
         kart_meta("KPSS", "KPSS Lisans (GY-GK)", "KPSS Lisans (Alan Bilgisi)")),
        ("dgs.html", "📈", "DGS", "Dikey Geçiş Sınavı", "Önlisanstan lisansa geçiş sınavı.",
         kart_meta("DGS", "DGS")),
        ("ales.html", "📚", "ALES", "Akademik Personel ve Lisansüstü Eğitimi Giriş Sınavı", "Yüksek lisans, doktora ve akademik kadro.",
         kart_meta("ALES", "ALES/1", "ALES/2", "ALES/3")),
        ("takvim.html", "🗓️", "Tüm Takvim", f"{BUGUN.year} Sınav Takvimi", "YKS, LGS, KPSS, DGS, ALES, TUS, YDS ve daha fazlası.",
         takvim_kart_meta()),
    ]
    cards = ""
    for href, icon, t, full, desc, meta in exams:
        cards += f"""<a class="exam-card" href="{href}">
  <div class="ec-top"><span class="ec-icon">{icon}</span><div><div class="ec-title">{t}</div><div class="ec-full">{full}</div></div></div>
  <div class="ec-desc">{desc}</div>
  <div class="ec-meta"><span>{meta}</span><span>İncele →</span></div>
</a>"""

    tools = [
        ("taban-puanlari.html", "📊", "Taban Puanları Merkezi", "Üniversite · LGS · TUS"),
        ("universite-taban-puanlari.html", "🎓", "Üniversite Taban Puanları", "21.602 program · YÖK Atlas"),
        ("lise-taban-puanlari.html", "🏫", "LGS Lise Taban Puanları", "81 il · 3.000+ lise"),
        ("tus-taban-puanlari.html", "🩺", "TUS Taban Puanları", "40 uzmanlık dalı · 2025"),
        ("tercih-robotu.html", "🎯", "Tercih Robotu", "Sıralamana göre bölüm bul"),
        ("takvim.html", "🗓️", f"Sınav Takvimi {TAKVIM_YILI}", "Tüm tarihler tek sayfada"),
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

<div class="section">
  <h2>Keşfet</h2>
  <div class="section-sub">Bölüm/üniversite detayları, sıralamalar ve sana uygun bölümü bul.</div>
  <div class="tool-row">
    <a class="tool-btn" href="/bolumler.html"><span class="tb-icon">📚</span><span class="tb-text"><b>Bölümler</b><span>Bölüm bazlı taban + SSS + program detayı (ℹ️)</span></span></a>
    <a class="tool-btn" href="/universiteler.html"><span class="tb-icon">🏛️</span><span class="tb-text"><b>Üniversiteler</b><span>Üniversite bazlı tüm programlar</span></span></a>
    <a class="tool-btn" href="/listeler.html"><span class="tb-icon">📈</span><span class="tb-text"><b>Listeler & Sıralamalar</b><span>En yüksek taban, en çok kontenjan</span></span></a>
    <a class="tool-btn" href="/bolum-bulma-testi.html"><span class="tb-icon">🧭</span><span class="tb-text"><b>Bölüm Bulma Testi</b><span>Hangi bölüm bana uygun?</span></span></a>
    <a class="tool-btn" href="/yks-siralama-hesaplama.html"><span class="tb-icon">🎯</span><span class="tb-text"><b>Sıralama Hesaplama</b><span>Puan → tahmini sıra → bölümler</span></span></a>
    <a class="tool-btn" href="/doluluk.html"><span class="tb-icon">📦</span><span class="tb-text"><b>Doluluk Analizi</b><span>Boş kalan / dolan kontenjanlar</span></span></a>
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
    desc = f"Türkiye sınav verileri platformu: YKS, LGS, KPSS, DGS, ALES için {TAKVIM_YILI} sınav takvimi, puan hesaplama araçları ve sınav rehberleri."
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


# Durum rozeti + geri sayım CSS — takvim tablosunun "Sonuç" hücresinde.
# JS ile boyanır (ziyaretçinin YEREL tarihine göre) → build bayatlasa da rozet doğru kalır;
# JS kapalıysa sunucu-render `sonuc_ham` metni (ör. "10 Temmuz 2026") zaten görünür — SEO güvenli.
TAKVIM_DURUM_CSS = """<style>
.sn-durum{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:999px;font-size:12.5px;font-weight:700;white-space:nowrap}
.sn-durum.gecti{background:color-mix(in srgb, #16a34a 16%, transparent);color:#16a34a}
.sn-durum.yakin{background:color-mix(in srgb, var(--accent) 18%, transparent);color:var(--accent)}
.sn-durum.uzak{background:var(--bg-card-alt);color:var(--fg-faded);border:1px solid var(--border)}
.sn-durum.belirsiz{background:var(--bg-card-alt);color:var(--fg-faded);border:1px dashed var(--border)}
.sn-tarih{display:block;font-size:12px;color:var(--fg-faded);margin-top:2px}
</style>"""

TAKVIM_DURUM_JS = r"""<script nonce="__NONCE__">
(function(){
  var rows = document.querySelectorAll('#takvimBody tr');
  var bugun = new Date(); bugun.setHours(0,0,0,0);
  Array.prototype.forEach.call(rows, function(tr){
    var td = tr.querySelector('.sn-sonuc'); if(!td) return;
    var kesin = td.getAttribute('data-kesin') === '1';
    var iso = td.getAttribute('data-iso');
    var ham = td.getAttribute('data-ham') || '';
    var span = document.createElement('span');
    if(kesin && iso){
      var hedef = new Date(iso+'T00:00:00'); hedef.setHours(0,0,0,0);
      var gun = Math.round((hedef-bugun)/86400000);
      if(gun < 0){ span.className='sn-durum gecti'; span.textContent='✅ Açıklandı'; }
      else if(gun === 0){ span.className='sn-durum yakin'; span.textContent='🔴 Bugün açıklanıyor'; }
      else if(gun <= 14){ span.className='sn-durum yakin'; span.textContent='⏳ '+gun+' gün kaldı'; }
      else { span.className='sn-durum uzak'; span.textContent=gun+' gün kaldı'; }
    } else {
      span.className='sn-durum belirsiz'; span.textContent='🔜 Yaklaşıyor';
      span.title='Kesin tarih ÖSYM/MEB tarafından henüz ilan edilmedi.';
    }
    var tarih=document.createElement('span'); tarih.className='sn-tarih'; tarih.textContent=ham;
    td.textContent=''; td.appendChild(span); td.appendChild(tarih);
  });
})();
</script>"""


def page_takvim():
    rows = ""
    for s in CAL["sinavlar"]:
        lbl, cls = TUR_LABEL.get(s["tur"], TUR_LABEL["other"])
        sinav = fmt_date(s["sinav"]) if s["sinav"].count("-") == 2 else s["sinav"]
        gslug = _guide_for(s["ad"])
        ad_html = f'<a href="/{gslug}" title="{s["ad"]} sınav rehberi">{s["ad"]}</a>' if gslug else s["ad"]
        kesin = "1" if s.get("sonuc_kesin") else "0"
        sonuc_iso = s.get("sonuc") or ""
        sonuc_ham = html_escape(s.get("sonuc_ham") or s["sonuc"])
        rows += f"""<tr>
  <td><span class="tag {cls}">{lbl}</span></td>
  <td><strong>{ad_html}</strong>{('<br><small class="soon">'+s['not']+'</small>') if s['not'] else ''}</td>
  <td>{s['basvuru']}</td>
  <td><strong>{sinav}</strong></td>
  <td class="sn-sonuc" data-kesin="{kesin}" data-iso="{sonuc_iso}" data-ham="{sonuc_ham}">{sonuc_ham}</td>
</tr>"""
    body = TAKVIM_DURUM_CSS + f"""
<div class="crumb"><a href="index.html">Ana Sayfa</a> / Sınav Takvimi</div>
<div class="page-title"><h1>{TAKVIM_YILI} Sınav Takvimi</h1><span class="sub">ÖSYM ve MEB resmî takvimine göre · Güncelleme: {fmt_date(CAL['guncelleme'])}</span></div>
<div class="data-table-wrap">
<table class="data-table">
<thead><tr><th data-tip="Sınavı düzenleyen kurum / sınav ailesi." data-type="text">Tür</th><th data-tip="Sınavın resmî adı." data-type="text">Sınav</th><th data-tip="Sınav başvurularının alındığı tarih aralığı." data-type="text">Başvuru</th><th data-tip="Sınavın yapılacağı resmî tarih." data-type="date">Sınav Tarihi</th><th data-tip="Sonuçların açıklanma durumu ve geri sayımı. Kesin tarih ilan edilmemişse 'Yaklaşıyor' gösterilir." data-type="text">Sonuç</th></tr></thead>
<tbody id="takvimBody">
{rows}
</tbody>
</table>
</div>
<div class="notice"><b>Not:</b> Tarihler ÖSYM {TAKVIM_YILI} Yılı Sınav Takvimi ve her sınavın resmî <b>kılavuz/duyurularıyla</b> (YKS, LGS, KPSS, DGS, ALES, TUS, DUS, YDS…) teyit edilmiştir.
Yaklaşmayan sınavların başvuru tarihleri ilgili kılavuz yayımlanınca kesinleşir; güncel bilgi için <a href="https://www.osym.gov.tr" target="_blank" rel="noopener">osym.gov.tr</a> ve <a href="https://www.meb.gov.tr" target="_blank" rel="noopener">meb.gov.tr</a> esastır.
Sınav sonucu/duyuru geçmişi için <a href="/duyurular.html">ÖSYM Duyuruları</a> sayfamıza bakabilirsiniz.</div>
""" + TAKVIM_DURUM_JS
    ev = [{"@type": "Event", "name": s["ad"], "startDate": s["sinav"],
           "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
           "location": {"@type": "Country", "name": "Türkiye"}}
          for s in CAL["sinavlar"] if s["sinav"].count("-") == 2]
    return base("takvim.html", f"{TAKVIM_YILI} Sınav Takvimi — YKS, LGS, KPSS, DGS, ALES | SınavVeri",
                f"{TAKVIM_YILI} ÖSYM ve MEB sınav takvimi: YKS (TYT/AYT), LGS, KPSS, DGS, ALES, TUS, YDS başvuru, sınav ve sonuç tarihleri.",
                body, extra_ld=ev)


# ───────────────────────── ÖSYM DUYURULARI ─────────────────────────
DUYURU_TIP_LABEL = {
    "sonuc_aciklandi": ("Sonuç Açıklandı", "tag-lgs"), "yerlestirme": ("Yerleştirme", "tag-lgs"),
    "tercih": ("Tercih", "tag-kpss"), "kilavuz": ("Kılavuz", "tag-kpss"),
    "basvuru": ("Başvuru", "tag-other"), "giris_belgesi": ("Giriş Belgesi", "tag-other"),
    "cevap_anahtari": ("Cevap Anahtarı", "tag-other"), "diger": ("Diğer", "tag-other"),
}
DUYURU_JS = r"""<script nonce="__NONCE__">
(function(){
  var list=document.getElementById('dList'), q=document.getElementById('dSearch'),
      kaynakSel=document.getElementById('dKaynak'),
      sinavSel=document.getElementById('dSinav'), tipSel=document.getElementById('dTip'), term='';
  function match(tr){
    if(term && tr.textContent.toLocaleLowerCase('tr').indexOf(term)<0) return false;
    if(kaynakSel&&kaynakSel.value && tr.getAttribute('data-kaynak')!==kaynakSel.value) return false;
    if(sinavSel.value && tr.getAttribute('data-sinav')!==sinavSel.value) return false;
    if(tipSel.value && tr.getAttribute('data-tip-key')!==tipSel.value) return false;
    return true;
  }
  var p=window.TVPager?window.TVPager.attach({grid:list,per:25,
        mount:document.getElementById('dPagerNav'),match:match}):null;
  function apply(){ if(p)p.reset(); else Array.prototype.forEach.call(list.children,function(tr){tr.style.display=match(tr)?'':'none';}); }
  q.addEventListener('input',function(){term=this.value.toLocaleLowerCase('tr').trim();apply();});
  if(kaynakSel) kaynakSel.addEventListener('change',apply);
  sinavSel.addEventListener('change',apply);
  tipSel.addEventListener('change',apply);
})();
</script>"""


def page_duyurular():
    """ÖSYM + MEB (LGS) duyuru akışlarını birleştirir. LGS ÖSYM'nin değil MEB'in sınavıdır —
    yalnız ÖSYM akışına bakınca LGS sonuç/tercih/kılavuz duyuruları hiç görünmezdi (2026-08-04
    kullanıcı tespiti). data/meb_duyurular.json AYRI dosyada (pipeline/fetch_meb_duyuru.py) —
    iki cron farklı zamanlarda çalışıp aynı dosyaya yazmasın diye kaynaklar hep ayrı tutulur."""
    p = ROOT / "data" / "osym_duyurular.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    duyurular = [dict(r, kaynak="ÖSYM") for r in d.get("duyurular", [])]
    guncelleme = d.get("guncelleme", "")[:10]

    mp = ROOT / "data" / "meb_duyurular.json"
    meb_guncelleme = None
    if mp.exists():
        md = json.loads(mp.read_text(encoding="utf-8"))
        duyurular += [dict(r, kaynak="MEB") for r in md.get("duyurular", [])]
        meb_guncelleme = md.get("guncelleme", "")[:10]
        if not guncelleme or (meb_guncelleme and meb_guncelleme > guncelleme):
            guncelleme = meb_guncelleme

    duyurular.sort(key=lambda r: r.get("tarih") or "", reverse=True)
    from collections import Counter
    sinav_cnt = Counter(r["sinav"] for r in duyurular if r.get("sinav"))
    KAYNAK_CLS = {"ÖSYM": "tag-yks", "MEB": "tag-lgs"}
    rows = ""
    for r in duyurular:
        tip_lbl, tip_cls = DUYURU_TIP_LABEL.get(r.get("tip"), DUYURU_TIP_LABEL["diger"])
        sinav = r.get("sinav") or ""
        kaynak = r["kaynak"]
        rows += (f'<tr data-sinav="{html_escape(sinav)}" data-tip-key="{html_escape(r.get("tip") or "diger")}" '
                 f'data-kaynak="{kaynak}">'
                 f'<td data-sort="{r.get("tarih") or ""}">{fmt_date(r["tarih"]) if r.get("tarih") else "—"}</td>'
                 f'<td><span class="tag {KAYNAK_CLS.get(kaynak,"tag-other")}">{kaynak}</span></td>'
                 f'<td>{html_escape(sinav) or "—"}</td>'
                 f'<td><span class="tag {tip_cls}">{tip_lbl}</span></td>'
                 f'<td><a href="{html_escape(r["url"])}" target="_blank" rel="noopener">{html_escape(r["baslik"])}</a></td></tr>')
    sinav_opts = "".join(f'<option value="{html_escape(s)}">{html_escape(s)} ({n})</option>'
                         for s, n in sorted(sinav_cnt.items(), key=lambda x: -x[1]))
    tip_opts = "".join(f'<option value="{k}">{lbl}</option>' for k, (lbl, _) in DUYURU_TIP_LABEL.items())
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / Duyurular</div>
<div class="page-title"><h1>Sınav Duyuruları</h1><span class="sub">{len(duyurular)} duyuru · ÖSYM + MEB'den · Güncelleme: {fmt_date(guncelleme) if guncelleme else "—"}</span></div>
<div class="info-box">ÖSYM ve MEB'in (LGS) resmî duyuru akışları — sınav sonuçları, yerleştirme, tercih ve kılavuz duyuruları. Sınav sonucu açıklandığında burada
görünür; hangi sınavın sonucunun ne zaman açıklanacağını görmek için <a href="/takvim.html">{TAKVIM_YILI} Sınav Takvimi</a>'ni kullanın.</div>
<div class="msf" style="margin-bottom:14px">
  <input id="dSearch" type="text" placeholder="Duyuru ara…" style="flex:1 1 240px;min-width:0;padding:10px 12px;border:1px solid var(--border);border-radius:9px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:14px">
  <select id="dKaynak" class="btn btn-ghost" style="text-align:left"><option value="">ÖSYM + MEB</option><option value="ÖSYM">Yalnız ÖSYM</option><option value="MEB">Yalnız MEB (LGS)</option></select>
  <select id="dSinav" class="btn btn-ghost" style="text-align:left"><option value="">Tüm sınavlar</option>{sinav_opts}</select>
  <select id="dTip" class="btn btn-ghost" style="text-align:left"><option value="">Tüm duyuru türleri</option>{tip_opts}</select>
</div>
<div class="data-table-wrap">
<table class="data-table">
<thead><tr><th data-tip="Duyurunun yayımlandığı tarih." data-type="date">Tarih</th><th data-tip="Duyurunun resmî kaynağı: ÖSYM veya MEB." data-type="text">Kaynak</th><th data-tip="İlgili sınav (belirtilmemişse boş)." data-type="text">Sınav</th><th data-tip="Duyuru türü: sonuç, yerleştirme, tercih, kılavuz, başvuru…" data-type="text">Tür</th><th data-tip="Duyuru başlığı — tıklayınca kaynağın resmî sayfası açılır." data-type="text">Başlık</th></tr></thead>
<tbody id="dList">
{rows}
</tbody>
</table>
</div>
<nav id="dPagerNav"></nav>
<div class="notice"><b>Kaynak:</b> ÖSYM resmî duyuru akışı (osym.gov.tr/Duyurular) + MEB ÖDSGM Haberler akışı (LGS). Bu liste düzenli olarak güncellenir; kaynak sayfadan kaldırsa
bile duyuru burada arşivde kalır.</div>
""" + DUYURU_JS
    return base("duyurular.html", "Sınav Duyuruları — ÖSYM ve MEB Sonuç/Kılavuz Duyuruları | SınavVeri",
                f"ÖSYM ve MEB'in güncel duyuruları: sınav sonuçları, yerleştirme, tercih ve kılavuz duyuruları (LGS dahil). {len(duyurular)} duyuru, kaynak/sınav/türe göre filtrelenebilir.",
                body, extra_ld=[breadcrumb_ld([("Ana Sayfa", "index.html"), ("Duyurular", None)])])


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
    return base("yks-puan-hesaplama.html", f"YKS Puan Hesaplama {TAKVIM_YILI} (TYT + AYT Net) | SınavVeri",
                f"{TAKVIM_YILI} YKS puan ve net hesaplama: TYT ve AYT doğru-yanlış gir, dersbazlı net ve toplam netini anında öğren. 4 yanlış 1 doğru.",
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
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / <a href="/puan-hesaplama.html">Puan Hesaplama</a> / YKS Sıralama</div>
<div class="page-title"><h1>{TAKVIM_YILI} YKS Sıralama Hesaplama — Puan → Tahmini Başarı Sırası</h1><span class="sub">Puanını gir, tahmini sıralamanı ve gidebileceğin bölümleri gör · 2025 YÖK Atlas verisine göre</span></div>
<div class="info-box">Denemende/ÖSYM sonucunda aldığın <b>yerleştirme puanını</b> ve puan türünü gir → {YKS_YIL} gerçek yerleştirme verisinden
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
    return base("yks-siralama-hesaplama.html", f"{TAKVIM_YILI} YKS Sıralama Hesaplama — Puanına Göre Tahmini Başarı Sırası | SınavVeri",
                f"{TAKVIM_YILI} YKS sıralama hesaplama: yerleştirme puanını gir, 2025 YÖK Atlas verisine göre tahmini başarı sıralamanı ve gidebileceğin bölümleri anında gör.",
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
                    # "… Tarihleri" bölümlerinde her maddeye bugüne göre durum çipi eklenir
                    # (✓ tamamlandı / ⏳ N gün kaldı). SSS metnine (ans_parts) çip GİRMEZ.
                    gor = [tarih_durumlu(x) for x in p[1]] if "Tarih" in h else p[1]
                    sec_html += "<ul>" + "".join(f"<li>{x}</li>" for x in gor) + "</ul>"
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
        "YKS, Türkiye'de üniversiteye girişin tek yoludur. TYT ve AYT olmak üzere iki temel oturumdan oluşur; " + yks_oturum_cumle(),
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
            (f"{TAKVIM_YILI} YKS Tarihleri", [
                ("ul", yks_tarih_listesi()),
            ]),
        ])


def page_lgs():
    return guide("lgs.html", "LGS", "Liselere Geçiş Sınavı", "🏫", "lgs-puan-hesaplama.html",
        "LGS, 8. sınıf öğrencilerinin fen lisesi, sosyal bilimler lisesi ve nitelikli Anadolu liselerine yerleşmek için girdiği merkezi sınavdır. " + sinav_cumle("LGS"),
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
            (f"{TAKVIM_YILI} LGS Tarihleri (MEB resmî kılavuzu)", [
                ("ul", ["Başvuru: 23 Mart – 10 Nisan 2026 (e-Okul üzerinden)", "Sınav giriş belgesi: 3 Haziran 2026",
                        "Sınav: 14 Haziran 2026 (Pazar)",
                        f"Sınav sonucu: {fmt_date(gercek_tarih('LGS', 'sonuc', cal_bul('LGS').get('sonuc'), TAKVIM_YILI))}",
                        f"Merkezi yerleştirme sonucu: {fmt_date(cal_bul('LGS').get('yerlestirme'))}"]),
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
            (f"{TAKVIM_YILI} KPSS Tarihleri", [
                ("ul", ["Lisans GY-GK: 6 Eylül 2026", "Lisans ÖABT: 12-13 Eylül 2026", "Ön Lisans: 4 Ekim 2026", "Ortaöğretim: 25 Ekim 2026"]),
            ]),
        ])


def page_dgs():
    return guide("dgs.html", "DGS", "Dikey Geçiş Sınavı", "📈", "",
        "DGS, ön lisans (2 yıllık) mezunlarının veya son sınıf öğrencilerinin lisans (4 yıllık) programlarına dikey geçiş yapabilmesi için girdiği sınavdır. " + sinav_cumle("DGS"),
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
            (f"{TAKVIM_YILI} DGS Tarihleri", [
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
            (f"{TAKVIM_YILI} ALES Tarihleri", [
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
            (f"{TAKVIM_YILI} TUS Tarihleri (ÖSYM resmî kılavuzu)", [
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
            (f"{TAKVIM_YILI} DUS Tarihleri (ÖSYM resmî kılavuzu)", [
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
            (f"{TAKVIM_YILI} YDS Tarihleri (ÖSYM)", [
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
            (f"{TAKVIM_YILI} YÖKDİL Tarihleri (ÖSYM)", [
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
            (f"{TAKVIM_YILI} MSÜ Tarihleri (ÖSYM)", [
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
            (f"{TAKVIM_YILI} YDUS Tarihleri (ÖSYM)", [
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
            (f"{TAKVIM_YILI} STS Tarihleri (ÖSYM)", [
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

    sw = """const CACHE='sinavveri-v2';
const ASSETS=['/','/index.html','/takvim.html','/assets/style.css'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  e.respondWith(fetch(e.request).then(r=>{const cp=r.clone();caches.open(CACHE).then(c=>c.put(e.request,cp));return r;}).catch(()=>caches.match(e.request)));
});

// Push bildirimi — sınav sonucu açıklandığında push-server (server.js) tetikler.
self.addEventListener('push',e=>{
  var data={}; try{ data=e.data?e.data.json():{}; }catch(err){}
  var title=data.title||'SınavVeri';
  var opts={
    body: data.body||'',
    icon: '/assets/brand/sinavveri-icon.png',
    badge: '/assets/brand/sinavveri-icon.png',
    data: { url: data.url||'/' },
    tag: data.tag||'sinavveri-duyuru'
  };
  e.waitUntil(self.registration.showNotification(title, opts));
});
self.addEventListener('notificationclick',e=>{
  e.notification.close();
  var url=(e.notification.data&&e.notification.data.url)||'/';
  e.waitUntil(clients.matchAll({type:'window',includeUncontrolled:true}).then(function(list){
    for(var i=0;i<list.length;i++){ if(list[i].url.indexOf(url)>=0 && 'focus' in list[i]) return list[i].focus(); }
    if(clients.openWindow) return clients.openWindow(url);
  }));
});
"""
    (ROOT / "sw.js").write_text(sw, encoding="utf-8")

    robots = """# TrVeri BOT-KORUMA STANDARDI — AI Bot Hibrit Politikasi (KARAR-1)
# 2026-08-18: Google-Extended hem Allow hem Disallow olarak gecmesin diye tek
# blokta toplandi (o bir AI-EGITIM sinyali → ENGEL tarafinda).

# === IZIN VER — arama ve AI-alinti botlari ===
User-agent: Googlebot
Allow: /

User-agent: Bingbot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Perplexity-User
Allow: /

User-agent: Claude-User
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: Applebot
Allow: /

User-agent: DuckDuckBot
Allow: /

User-agent: YandexBot
Allow: /

User-agent: Slurp
Allow: /

User-agent: Baiduspider
Allow: /

User-agent: Seznambot
Allow: /

User-agent: facebookexternalhit
Allow: /

User-agent: Twitterbot
Allow: /

User-agent: LinkedInBot
Allow: /

User-agent: TelegramBot
Allow: /

# === ENGELLE — AI egitim / scrape botlari ===
User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: Claude-Web
Disallow: /

User-agent: anthropic-ai
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: Applebot-Extended
Disallow: /

User-agent: Bytespider
Disallow: /

User-agent: Amazonbot
Disallow: /

User-agent: meta-externalagent
Disallow: /

User-agent: FacebookBot
Disallow: /

User-agent: cohere-ai
Disallow: /

User-agent: Diffbot
Disallow: /

User-agent: ImagesiftBot
Disallow: /

User-agent: Omgilibot
Disallow: /

User-agent: Ai2Bot
Disallow: /

User-agent: DataForSeoBot
Disallow: /

User-agent: *
Allow: /

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
def _robot_detail(r):
    """Robot ⓘ detayı için kompakt paket — _pdet_btn (bölüm/üniversite sayfası) ile AYNI
    kaynak alanlar, aynı içerik. write_veri() dizisinin SONUNA (idx 17) tek nesne olarak
    eklenir: mevcut tüketiciler (SEARCH_JS/KARSILASTIR_JS idx 0-16 okur) etkilenmez, yalnız
    ROBOT_JS bu ek alanı okur. Gösterilecek hiçbir şey yoksa None (JSON'da null, hafif kalır)."""
    kadro = r.get("kadro") or []
    kosul = r.get("kosul") or ""
    akr = r.get("akr") or ""
    sure = r.get("sure")
    ucret = r.get("ucret")
    demo = DEMOGRAFI.get(str(r.get("k"))) if r.get("k") is not None else None
    hist = r.get("hist") or []
    if not (kosul or any(kadro) or akr or sure or ucret or demo or hist):
        return None
    d = {}
    if kosul:
        d["kosul"] = kosul
    if any(kadro):
        d["kadro"] = kadro
    if akr:
        d["akr"] = akr
    if sure:
        d["sure"] = sure
    if ucret:
        d["ucret"] = ucret
    if demo:
        d["demo"] = {k: demo.get(k) for k in ("y", "k", "e", "ls", "mz", "ub", "um") if demo.get(k) is not None}
    if hist:
        d["hist"] = hist  # [[yıl,taban,sıra,yerleşen], …] — zaten ham haliyle uygun
    return d


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
                             hist_taban(r, 2024), hist_taban(r, 2023),
                             hist_sira(r, 2024), hist_sira(r, 2023),
                             _robot_detail(r)])
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
  var IDX={k:0,u:1,b:2,g:3,il:4,t:5,o:6,dil:7,bs:8,kont:9,tp:10,sira:11,yer:12,t24:13,t23:14,s24:15,s23:16};
  var TUR={D:'Devlet',V:'Vakıf',K:'KKTC',DK:'Devlet (KKTC Kampüs)',DU:'Devlet (Ücretli)',DKU:'Devlet (KKTC Uyruklu)',Y:'Diğer','?':'—'};
  var PTL={say:'Sayısal',ea:'Eşit Ağırlık',soz:'Sözel',dil:'Dil',tyt:'TYT (Önlisans)'};
  var SV=window.SV||{};
  function doluluk(r){var k=r[IDX.kont],y=r[IDX.yer];if(!k||y==null)return '—';var p=Math.round(y/k*100);var c=p>=100?'tag-lgs':(p>=70?'tag-kpss':'tag-other');return '<span class="tag '+c+'">%'+p+'</span>';}
  var data=[], cache={}, pgr=null;   // sayfalama: TrVeri STANDART pager.js (rule 3.17)
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
  // Cascading (bağımlı) filtreler: her dropdown, DİĞER seçili filtrelere göre yeniden dolar
  var FDIMS=[
    {id:'fIl', ph:'Tüm iller', get:function(r){return r[IDX.il];}},
    {id:'fTur', ph:'Tüm türler', get:function(r){return r[IDX.t];}, lab:function(v){return TUR[v]||v;}},
    {id:'fDil', ph:'Tüm öğrenim dilleri', get:function(r){return bdil(r[IDX.dil]);}},
    {id:'fOgr', ph:'Tüm öğrenim türleri', get:function(r){return r[IDX.o];}}
  ];
  function passExc(r, exceptId){
    for(var i=0;i<FDIMS.length;i++){var f=FDIMS[i];if(f.id===exceptId)continue;var s=el(f.id);if(s&&s.value&&String(f.get(r))!==s.value)return false;}
    if(el('fBurs')&&el('fBurs').checked&&!/Burslu/i.test(r[IDX.bs]||''))return false;
    if(el('fDol')&&el('fDol').checked){var k=r[IDX.kont],y=r[IDX.yer];if(!(k!=null&&y!=null&&y<k))return false;}
    return true;
  }
  function repopulate(){
    FDIMS.forEach(function(f){var sel=el(f.id);if(!sel)return;var cur=sel.value;
      var cnt={};data.forEach(function(r){if(!passExc(r,f.id))return;var v=f.get(r);if(v!=null&&v!=='')cnt[v]=(cnt[v]||0)+1;});
      var ks=Object.keys(cnt).sort(function(a,b){return cnt[b]-cnt[a]||String(a).localeCompare(String(b),'tr');});
      sel.innerHTML='<option value="">'+f.ph+'</option>';var hasCur=false;
      ks.forEach(function(k){var o=document.createElement('option');o.value=k;o.textContent=(f.lab?f.lab(k):k)+' ('+cnt[k]+')';if(k===cur){o.selected=true;hasCur=true;}sel.appendChild(o);});
      if(cur&&!hasCur){var o2=document.createElement('option');o2.value=cur;o2.textContent=(f.lab?f.lab(cur):cur)+' (0)';o2.selected=true;sel.appendChild(o2);}
    });
  }
  function fillIl(){repopulate();}
  function fillDil(){}
  function fillOgr(){}
  function applyQS(){
    var qs=SV.qsGet?SV.qsGet():{};
    if(qs.q!=null)el('fQ').value=qs.q;
    if(qs.tur!=null)el('fTur').value=qs.tur;
    if(qs.burs==='1'&&el('fBurs'))el('fBurs').checked=true;
    if(qs.dol==='1'&&el('fDol'))el('fDol').checked=true;
    if(qs.ogr!=null&&el('fOgr')){var so=el('fOgr');var oo=document.createElement('option');oo.value=qs.ogr;oo.textContent=qs.ogr;oo.selected=true;so.appendChild(oo);}
    if(qs.dil!=null&&el('fDil')){var s=el('fDil');var o=document.createElement('option');o.value=qs.dil;o.textContent=qs.dil;o.selected=true;s.appendChild(o);}
    if(qs.il!=null){var si=el('fIl');var oi=document.createElement('option');oi.value=qs.il;oi.textContent=qs.il;oi.selected=true;si.appendChild(oi);}
  }
  function syncQS(){
    var o={pt:el('ptSel').value};var q=el('fQ').value.trim();if(q)o.q=q;
    if(el('fIl').value)o.il=el('fIl').value; if(el('fTur').value)o.tur=el('fTur').value;
    if(el('fDil')&&el('fDil').value)o.dil=el('fDil').value;
    if(el('fOgr')&&el('fOgr').value)o.ogr=el('fOgr').value;
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
    if(el('fOgr')&&el('fOgr').value)items.push({key:'ogr',label:'Öğrenim: '+el('fOgr').value});
    if(el('fBurs')&&el('fBurs').checked)items.push({key:'burs',label:'Sadece burslu'});
    if(el('fDol')&&el('fDol').checked)items.push({key:'dol',label:'Kontenjanı dolmamış'});
    SV.chips('chips',items,function(key){
      if(key==='pt')return;
      if(key==='__all__'){el('fQ').value='';el('fIl').value='';el('fTur').value='';if(el('fDil'))el('fDil').value='';if(el('fOgr'))el('fOgr').value='';if(el('fBurs'))el('fBurs').checked=false;if(el('fDol'))el('fDol').checked=false;}
      else if(key==='q')el('fQ').value='';else if(key==='il')el('fIl').value='';
      else if(key==='tur')el('fTur').value='';else if(key==='dil'&&el('fDil'))el('fDil').value='';
      else if(key==='ogr'&&el('fOgr'))el('fOgr').value='';
      else if(key==='burs'&&el('fBurs'))el('fBurs').checked=false;
      else if(key==='dol'&&el('fDol'))el('fDol').checked=false;
      repopulate();render(true);
    });
  }
  function afterLoad(){fillIl();fillDil();fillOgr();render();}
  function filtered(){
    var q=(el('fQ').value||'').toLocaleLowerCase('tr').trim();
    var il=el('fIl').value, tur=el('fTur').value, dilSel=el('fDil')?el('fDil').value:'';
    var ogr=el('fOgr')?el('fOgr').value:'';
    var bursOnly=el('fBurs')&&el('fBurs').checked;
    var dolOnly=el('fDol')&&el('fDol').checked;
    var out=data.filter(function(r){
      if(il&&r[IDX.il]!==il)return false;
      if(tur&&r[IDX.t]!==tur)return false;
      if(dilSel&&bdil(r[IDX.dil])!==dilSel)return false;
      if(ogr&&r[IDX.o]!==ogr)return false;
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
    if(reset!==false){syncQS();}
    var rows=applySort(filtered());
    el('status').textContent=rows.length.toLocaleString('tr-TR')+' program bulundu';
    var tb=el('tbody'); byKey={};
    if(!rows.length){if(SV.empty)SV.empty('tbody',8);if(pgr)pgr.reset();return;}
    var out=[];
    rows.forEach(function(r){
      var k=rkey(r); byKey[k]=r;
      var kc=nf(r[IDX.kont]),kk=r[IDX.kont],yy=r[IDX.yer];
      if(kk!=null&&yy!=null&&yy<kk)kc=nf(kk)+' <small style="color:var(--fg-faded)">/ '+nf(yy)+' yerleşti</small>';
      out.push('<tr><td><strong>'+(r[IDX.b]||'')+'</strong><br><small>'+(r[IDX.u]||'')+'</small></td>'+
        '<td>'+(r[IDX.il]||'—')+'</td>'+
        '<td><span class="tag tag-other">'+(TUR[r[IDX.t]]||'—')+'</span></td>'+
        '<td>'+kc+'</td>'+
        '<td><strong>'+pf(r[IDX.tp])+'</strong></td>'+
        '<td>'+nf(r[IDX.sira])+(SV.spark?SV.spark([r[IDX.s23],r[IDX.s24],r[IDX.sira]],true):'')+'</td>'+
        '<td>'+doluluk(r)+'</td>'+
        '<td style="text-align:center"><input type="checkbox" class="cmp-cb" aria-label="Karşılaştır" data-k="'+k.replace(/"/g,'&quot;')+'"'+(cmp[k]?' checked':'')+'></td></tr>');
    });
    tb.innerHTML=out.join('');
    if(!pgr&&window.TVPager)pgr=window.TVPager.attach({grid:tb.parentNode,per:25,mount:el('moreWrap')});
    else if(pgr)pgr.reset();
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
  if(el('fQ'))el('fQ').addEventListener('input',function(){render(true);});
  ['fIl','fTur','fDil','fOgr'].forEach(function(id){var e=el(id);if(e)e.addEventListener('change',function(){repopulate();render(true);});});
  if(el('fBurs'))el('fBurs').addEventListener('change',function(){repopulate();render(true);});
  if(el('fDol'))el('fDol').addEventListener('change',function(){repopulate();render(true);});
  el('ptSel').addEventListener('change',function(){load(this.value);});
  (function(){var ths=document.querySelectorAll('.data-table thead th');ths.forEach(function(th,i){
    if(th.hasAttribute('data-nosort'))return;
    th.style.cursor='pointer';th.title='Sıralamak için tıklayın';
    th.addEventListener('click',function(){sortD=(sortI===i)?-sortD:1;sortI=i;
      ths.forEach(function(o){o.removeAttribute('aria-sort');var a=o.querySelector('.s-arrow');if(a)a.remove();});
      th.setAttribute('aria-sort',sortD>0?'ascending':'descending');
      var ar=document.createElement('span');ar.className='s-arrow';ar.textContent=sortD>0?' ▲':' ▼';th.appendChild(ar);render(true);});});})();
  applyQS();
  var qs0=SV.qsGet?SV.qsGet():{}; if(qs0.pt&&PTL[qs0.pt])el('ptSel').value=qs0.pt;
  load(el('ptSel').value);
})();
</script>"""


def page_taban_index():
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / <a href="/taban-puanlari.html">Taban Puanları</a> / Üniversite</div>
<div class="page-title"><h1>Üniversite Taban Puanları {YKS_YIL}</h1><span class="sub">YÖK Atlas {YKS_YIL} yerleştirme verisi · 21.602 program · Gerçek taban puanı ve başarı sırası</span></div>

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
    <select id="fOgr" class="btn btn-ghost" style="text-align:left"><option value="">Tüm öğrenim türleri</option></select>
    <label style="display:flex;align-items:center;gap:6px;font-size:13px;color:var(--fg-muted)"><input type="checkbox" id="fBurs"> Sadece burslu</label>
    <label style="display:flex;align-items:center;gap:6px;font-size:13px;color:var(--fg-muted)"><input type="checkbox" id="fDol"> Sadece kontenjanı dolmamışlar</label>
  </div>
  <div class="filter-chips" id="chips" style="display:none"></div>
  <div id="status" style="margin-top:12px;font-size:13px;color:var(--accent);font-weight:700">Yükleniyor…</div>
</div>

<div class="data-table-wrap">
<table class="data-table cardify" data-live="1">
<thead><tr><th data-tip="Programın YÖK Atlas'taki tam adı ve bağlı olduğu üniversite." data-type="text">Program / Üniversite</th><th data-tip="Programın bulunduğu il." data-type="text">İl</th><th data-tip="Üniversite türü: Devlet, Vakıf, KKTC veya özel kontenjan türü." data-type="text">Tür</th><th data-tip="2025 genel kontenjanı; dolmadıysa yanında yerleşen sayısı gösterilir." data-type="num">Kont. / Yerleşen</th><th data-tip="Programa en son yerleşen adayın 2025 YKS yerleştirme puanı." data-type="num">Taban Puan</th><th data-tip="En son yerleşen adayın 2025 başarı sırası. Küçük sıra = daha yüksek başarı." data-type="num">Başarı Sırası</th><th data-tip="Doluluk = yerleşen ÷ kontenjan. %100 kontenjanın tamamen dolduğunu gösterir." data-type="num">Doluluk</th><th data-nosort data-tip="En fazla 3 programı işaretleyip yan yana karşılaştırın.">Kıyas</th></tr></thead>
<tbody id="tbody"></tbody>
</table>
</div>
<div class="fav-panel" id="cmpPanel"></div>
<div class="cmp-bar" id="cmpBar">
  <button type="button" class="fav-toggle" id="cmpBtn">Karşılaştır (0)</button>
  <button type="button" class="fchip-clear" id="cmpClear" style="margin-left:8px">Seçimi temizle</button>
</div>
<nav id="moreWrap"></nav>

<div class="notice"><b>Kaynak:</b> YÖK Atlas {YKS_KILAVUZ_YIL} Tercih Kılavuzu (en güncel tamamlanmış yerleştirme). Taban puanı ve başarı sırası
o programa <b>en son yerleşen</b> adayın verisidir. Yerleşen olmayan programlarda değer boştur (—).
2026 taban puanları, yerleştirme sonrası (Ağustos 2026) güncellenecektir.</div>
""" + SEARCH_JS
    return base("universite-taban-puanlari.html", f"Üniversite Taban Puanları {YKS_YIL} — YÖK Atlas Verisi | SınavVeri",
                "2025 üniversite taban puanları ve başarı sıralamaları. 21.602 lisans ve önlisans programını puan türü, il ve üniversite türüne göre filtrele. YÖK Atlas verisi.",
                body, extra_ld=[breadcrumb_ld([("Ana Sayfa", "index.html"), ("Taban Puanları", "taban-puanlari.html"), ("Üniversite", None)])])


# ───────────────────────── TERCİH ROBOTU ─────────────────────────
ROBOT_JS = r"""<script nonce="__NONCE__">
(function(){
  var IDX={k:0,u:1,b:2,g:3,il:4,t:5,o:6,dil:7,bs:8,kont:9,tp:10,sira:11,yer:12,t24:13,t23:14,s24:15,s23:16,det:17};
  var TUR={D:'Devlet',V:'Vakıf',K:'KKTC',DK:'Devlet (KKTC Kampüs)',DU:'Devlet (Ücretli)',DKU:'Devlet (KKTC Uyruklu)',Y:'Diğer','?':'—'};
  var PTL={say:'Sayısal',ea:'Eşit Ağırlık',soz:'Sözel',dil:'Dil',tyt:'TYT (Önlisans)'};
  var SV=window.SV||{};
  var data=[],cache={},byId={},pgr=null;   // sayfalama: TrVeri STANDART pager.js (rule 3.17)
  var cmpData={},cmpSel=[];
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
  function gv(id){var e=el(id);return e?e.value:'';}
  function sv(id,v){var e=el(id);if(e)e.value=v;}
  function syncQS(){
    var o={pt:el('rPt').value};var s=el('rSira').value.replace(/\D/g,'');if(s)o.sira=s;
    if(gv('rIl'))o.il=gv('rIl');if(gv('rTur'))o.tur=gv('rTur');
    if(gv('rDil'))o.dil=gv('rDil');if(gv('rUni'))o.uni=gv('rUni');if(gv('rBol'))o.bol=gv('rBol');
    var smin=el('rSMin')&&el('rSMin').value.replace(/\D/g,'');if(smin)o.smin=smin;
    var smax=el('rSMax')&&el('rSMax').value.replace(/\D/g,'');if(smax)o.smax=smax;
    if(SV.qsSet)SV.qsSet(o);drawChips();
  }
  function drawChips(){
    if(!SV.chips)return;var items=[{key:'pt',label:'Puan: '+(PTL[el('rPt').value]||el('rPt').value)}];
    var s=el('rSira').value.replace(/\D/g,'');if(s)items.push({key:'sira',label:'Sıra: '+Number(s).toLocaleString('tr-TR')});
    if(gv('rIl'))items.push({key:'il',label:'İl: '+gv('rIl')});
    if(gv('rTur'))items.push({key:'tur',label:'Tür: '+(TUR[gv('rTur')]||gv('rTur'))});
    if(gv('rDil'))items.push({key:'dil',label:'Dil: '+gv('rDil')});
    if(gv('rUni'))items.push({key:'uni',label:'Üni: '+gv('rUni')});
    if(gv('rBol'))items.push({key:'bol',label:'Bölüm: '+gv('rBol')});
    var smin=el('rSMin')&&el('rSMin').value.trim(), smax=el('rSMax')&&el('rSMax').value.trim();
    if(smin||smax)items.push({key:'srange',label:'Başarı Sırası: '+(smin||'—')+' – '+(smax||'—')});
    SV.chips('chips',items,function(key){
      if(key==='pt')return;
      if(key==='__all__'){el('rSira').value='';sv('rIl','');sv('rTur','');sv('rDil','');sv('rUni','');sv('rBol','');if(el('rSMin'))el('rSMin').value='';if(el('rSMax'))el('rSMax').value='';}
      else if(key==='sira')el('rSira').value='';
      else if(key==='srange'){if(el('rSMin'))el('rSMin').value='';if(el('rSMax'))el('rSMax').value='';}
      else sv('r'+key.charAt(0).toUpperCase()+key.slice(1),'');
      run();
    });
  }
  var lastReach=[],lastSira=0,sortI=null,sortD=1;
  var SCOLS=[[IDX.b,0],[IDX.il,0],[IDX.t,0],[IDX.kont,1],[IDX.tp,1],[IDX.sira,1]];
  function sortReach(){
    if(sortI==null||sortI>=SCOLS.length){lastReach.sort(function(a,b){return a[IDX.sira]-b[IDX.sira];});return;}
    var f=SCOLS[sortI][0],num=SCOLS[sortI][1];
    lastReach.sort(function(a,b){var x=a[f],y=b[f];
      if(num){x=(x==null?null:Number(x));y=(y==null?null:Number(y));if(x==null&&y==null)return 0;if(x==null)return 1;if(y==null)return -1;return (x-y)*sortD;}
      return String(x==null?'':x).localeCompare(String(y==null?'':y),'tr')*sortD;});
  }
  // Bu yıl ÖSYM kılavuzundan düşmüş program kodları (kod-diff — bkz. pipeline/kilavuz_diff.py).
  // Satır SİLİNMEZ (geçmiş veri değerlidir), yalnız "Bu yıl alım yapmıyor" rozeti eklenir.
  var KAPANAN = new Set(__KAPANAN_KODLAR__);
  var pf0=function(n){return n==null?'—':n.toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2});};
  function esc(s){return (''+(s==null?'':s)).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
  // ⓘ detay içeriği bölüm/üniversite sayfalarındaki DETAIL_TOOLS_JS ile AYNI kaynak alanlardan
  // (kosul/kadro/akr/sure/ucret/demo/hist — write_veri()'nin idx17'sinde bundle edilir) VE AYNI
  // görünümle üretilir. Program kodu ayrıca eklenir (ÖSYM tercih formuna girilen kod budur —
  // ⚠️ yıldan yıla değişebilir, tercih döneminde güncel kılavuzdan doğrulanmalı).
  var KOSUL=null, KLAB=['Profesör','Doçent','Dr. Öğr. Üyesi','Araştırma Gör.','Öğretim Gör.'];
  function renderDetail(r){
    var d=r[IDX.det]||{}, parts=[];
    var yillar=[[2025,r[IDX.tp],r[IDX.sira],r[IDX.yer]]].concat(d.hist||[])
      .filter(function(y){return y[1]!=null||y[2]!=null;});
    if(yillar.length){
      var hr=yillar.map(function(y){return '<tr><td><b>'+y[0]+'</b></td><td>'+pf0(y[1])+'</td><td>'+nf(y[2])+'</td><td>'+nf(y[3])+'</td></tr>';}).join('');
      parts.push('<div><b>Yıllara göre (taban / başarı sırası / yerleşen):</b>'
        +'<table class="pdet-hist"><thead><tr><th data-tip="Yerleştirme yılı.">Yıl</th><th data-tip="O yıl programa en son yerleşen adayın puanı.">Taban</th><th data-tip="O yıl en son yerleşen adayın başarı sırası.">Başarı Sırası</th><th data-tip="O yıl programa yerleşen toplam öğrenci sayısı.">Yerleşen</th></tr></thead><tbody>'+hr+'</tbody></table></div>');
    }
    var demo=d.demo;
    if(demo){
      var kz=demo.k||0, er=demo.e||0, ls=demo.ls||0, mz=demo.mz||0, ub=demo.ub||0, um=demo.um||0, ct=kz+er;
      if(ct>0){
        var kzp=Math.round(100*kz/ct), erp=100-kzp;
        parts.push('<div style="margin-top:8px"><b>Yerleşen profili ('+esc(demo.y)+'):</b>'
          +'<div style="margin:5px 0 2px;font-size:12px">Cinsiyet — Kız %'+kzp+' · Erkek %'+erp+'</div>'
          +'<div style="display:flex;height:14px;border-radius:7px;overflow:hidden;font-size:9px;line-height:14px;color:#fff">'
          +'<div style="width:'+kzp+'%;background:#d6336c;text-align:center">'+kz+'</div>'
          +'<div style="width:'+erp+'%;background:#1c7ed6;text-align:center">'+er+'</div></div>');
        var ot=ls+mz+ub+um;
        if(ot>0){
          var seg=[['Lise son sınıf',ls,'#2f9e44'],['Önceki yıl mezunu',mz,'#f08c00'],['Üniv. öğrencisi iken',ub,'#7048e8'],['Üniv. mezunu',um,'#e8590c']].filter(function(s){return s[1]>0;});
          parts.push('<div style="margin-top:6px;font-size:12px">Öğrenim durumu:</div>'
            +'<div style="display:flex;height:14px;border-radius:7px;overflow:hidden;font-size:9px;line-height:14px;color:#fff">'
            +seg.map(function(s){return '<div style="width:'+Math.round(100*s[1]/ot)+'%;background:'+s[2]+'" title="'+s[0]+': '+s[1]+'"></div>';}).join('')+'</div>'
            +'<div style="font-size:11px;color:var(--fg-faded);margin-top:3px">'+seg.map(function(s){return esc(s[0])+' %'+Math.round(100*s[1]/ot);}).join(' · ')+'</div>');
        }
        parts.push('<div style="font-size:10px;color:var(--fg-faded);margin-top:4px">Cinsiyet ve öğrenim durumu dağılımını YÖK Atlas en son <b>'+esc(demo.y)+'</b> yerleşmeleri için yayınladı; sonraki yıllarda bu istatistik yayından kaldırıldı. Diğer tüm veriler (taban, sıra, kontenjan, yerleşen sayısı, koşullar, kadro, ücret) cari yıla aittir.</div></div>');
      }
    }
    if(d.kadro&&d.kadro.some(function(v){return v>0;})){
      var kp=[]; d.kadro.forEach(function(v,i){ if(v>0)kp.push(KLAB[i]+': '+v); });
      parts.push('<div style="margin-top:6px"><b>Akademik kadro:</b> '+kp.join(' · ')+'</div>');
    }
    if(d.akr) parts.push('<div><b>Akreditasyon:</b> '+esc(d.akr)+'</div>');
    if(d.sure) parts.push('<div><b>Öğrenim süresi:</b> '+esc(d.sure)+' yıl</div>');
    if(d.ucret) parts.push('<div><b>Ücret:</b> '+nf(d.ucret)+' ₺/yıl</div>');
    if(d.kosul&&KOSUL){
      var ks=(''+d.kosul).split(',').filter(Boolean);
      var li=ks.map(function(c){return KOSUL[c]?'<li>'+esc(KOSUL[c])+'</li>':'';}).filter(Boolean).join('');
      if(li) parts.push('<div style="margin-top:6px"><b>Özel koşullar:</b><ul style="margin:4px 0 0 18px">'+li+'</ul></div>');
    }
    if(r[IDX.k]!=null){
      parts.push('<div style="margin-top:8px;font-size:11.5px;color:var(--fg-faded)"><b>Program Kodu:</b> '+esc(r[IDX.k])
        +' <span title="ÖSYM tercih formuna girilen kod budur. Program kodları yıldan yıla değişebilir — 2026 tercih döneminde güncel ÖSYM kılavuzundan doğrulayın.">ⓘ (her yıl değişebilir, tercihte güncel kılavuzdan doğrulayın)</span></div>');
    }
    if(!parts.length) parts.push('<div style="color:var(--fg-faded)">Ek detay bulunmuyor.</div>');
    return '<div class="pdet-box">'+parts.join('')+'</div>';
  }
  function draw(){
    var tb=el('rbody'); byId={};
    if(!lastReach.length){tb.innerHTML='';if(SV.empty)SV.empty('rbody',9,'Bu sıralama ve filtrelerle yerleşebileceğin program bulunamadı. Filtreyi gevşetmeyi deneyin.');el('rhint').style.display='none';if(pgr)pgr.reset();return;}
    if(!KOSUL) fetch('/veri/kosul_map.json').then(function(r){return r.json();}).then(function(j){KOSUL=j;}).catch(function(){KOSUL={};});
    var out=[];
    lastReach.forEach(function(r,ri){
      var ratio=r[IDX.sira]/lastSira;  // taban sıra / senin sıran (>1 = taban daha geride = güvenli)
      var safe = ratio>=1.20 ? '<span class="tag tag-lgs">Rahat</span>' : (ratio>=1.0 ? '<span class="tag tag-kpss">Olası</span>' : '<span class="tag tag-other">Sınırda</span>');
      var k=rkey(r); byId[k]={id:k,name:r[IDX.b]||'',sub:r[IDX.u]||'',meta:'taban sıra '+nf(r[IDX.sira])};
      cmpData[k]=r;
      var on=fav&&fav.has(k);
      var onCmp=cmpSel.indexOf(k)>=0;
      var rozet='';
      if(KAPANAN.has(r[IDX.k])) rozet=' <span class="tag tag-other" title="ÖSYM'+"'"+'nin güncel kılavuzunda bu program bulunamadı">⛔ Bu yıl alım yapmıyor</span>';
      else if(r[IDX.t24]==null&&r[IDX.t23]==null) rozet=' <span class="tag tag-other" title="Önceki yıllarda taban puan kaydı yok — yeni açılmış veya ilk kez ilan edilmiş olabilir">🆕 Yeni</span>';
      var hasDet=!!r[IDX.det];
      var ibtn=hasDet?'<button type="button" class="pdet" data-ri="'+ri+'" aria-expanded="false" aria-label="Program detayını göster">ℹ️</button>':'';
      out.push('<tr><td><strong>'+(r[IDX.b]||'')+'</strong>'+rozet+'<br><small>'+(r[IDX.u]||'')+'</small></td>'+
        '<td>'+(r[IDX.il]||'—')+'</td>'+'<td>'+(TUR[r[IDX.t]]||'—')+'</td>'+
        '<td>'+nf(r[IDX.kont])+'</td>'+
        '<td><strong>'+pf(r[IDX.tp])+'</strong></td>'+'<td>'+nf(r[IDX.sira])+' '+ibtn+'</td>'+'<td>'+safe+'</td>'+
        '<td style="text-align:center"><button type="button" class="fav-star'+(on?' on':'')+'" data-fid="'+k.replace(/"/g,'&quot;')+'" aria-label="Tercih listeme ekle">'+(on?'★':'☆')+'</button></td>'+
        '<td style="text-align:center"><input type="checkbox" class="cmp-chk" data-cid="'+k.replace(/"/g,'&quot;')+'"'+(onCmp?' checked':'')+' aria-label="Karşılaştırmaya ekle"></td></tr>');
      if(hasDet) out.push('<tr class="pdet-row" data-ri="'+ri+'" hidden><td colspan="9"></td></tr>');
    });
    tb.innerHTML=out.join('');
    if(!pgr&&window.TVPager)pgr=window.TVPager.attach({grid:tb.parentNode,per:25,mount:el('rPager')});
    else if(pgr)pgr.reset();
    el('rhint').style.display='block';
    el('rhint').textContent='Sütun başlığına tıklayarak sıralayabilir, il/tür/dil filtreleriyle listeyi daraltabilirsiniz. ℹ️ ile program detayını görebilirsiniz.';
    cmpBar();
  }
  // Program karşılaştırma — sonuç tablosundan seçilen 2-4 kaydı yan yana (transpoze) gösterir.
  function cmpBar(){
    var bar=el('cmpBar'); if(!bar)return;
    bar.style.display=cmpSel.length?'flex':'none';
    var lbl=el('cmpCount'); if(lbl)lbl.textContent=cmpSel.length+'/4 seçili';
    var btn=el('cmpGoBtn'); if(btn)btn.disabled=cmpSel.length<2;
  }
  function renderCompare(){
    var box=el('cmpBox'); if(!box)return;
    var cols=cmpSel.map(function(k){return cmpData[k];}).filter(Boolean);
    if(cols.length<2){box.innerHTML='';return;}
    var head='<tr><th>Program</th>'+cols.map(function(r){return '<td><strong>'+(r[IDX.b]||'')+'</strong><br><small>'+(r[IDX.u]||'')+'</small></td>';}).join('')+'</tr>';
    var rowsDef=[['İl',function(r){return r[IDX.il]||'—';}],['Tür',function(r){return TUR[r[IDX.t]]||'—';}],
      ['Öğrenim Dili',function(r){return r[IDX.dil]||'—';}],['Kontenjan',function(r){return nf(r[IDX.kont]);}],
      ['Taban Puan',function(r){return '<strong>'+pf(r[IDX.tp])+'</strong>';}],['Başarı Sırası',function(r){return nf(r[IDX.sira]);}]];
    var body=rowsDef.map(function(d){return '<tr><th>'+d[0]+'</th>'+cols.map(function(r){return '<td>'+d[1](r)+'</td>';}).join('')+'</tr>';}).join('');
    box.innerHTML='<div class="data-table-wrap"><table class="data-table"><thead>'+head+'</thead><tbody>'+body+'</tbody></table></div>'
      +'<button type="button" class="btn btn-ghost" id="cmpClearBtn" style="margin-top:8px">✕ Karşılaştırmayı Kapat</button>';
    box.scrollIntoView({behavior:'smooth',block:'nearest'});
  }
  function run(){
    var pt=el('rPt').value;
    load(pt,function(){
      syncQS();
      var sira=parseInt((el('rSira').value||'').replace(/\D/g,''),10);
      if(!sira||sira<1){el('rstatus').textContent='Lütfen geçerli bir başarı sıranızı girin.';el('rbody').innerHTML='';return;}
      var il=gv('rIl'), tur=gv('rTur'), dilSel=gv('rDil'), uni=gv('rUni'), bol=gv('rBol');
      var sMin=parseInt((el('rSMin')&&el('rSMin').value||'').replace(/\D/g,''),10);
      var sMax=parseInt((el('rSMax')&&el('rSMax').value||'').replace(/\D/g,''),10);
      lastSira=sira;
      lastReach=data.filter(function(r){
        if(r[IDX.sira]==null)return false;
        if(il&&r[IDX.il]!==il)return false;
        if(tur&&r[IDX.t]!==tur)return false;
        if(dilSel&&bdil(r[IDX.dil])!==dilSel)return false;
        if(uni&&r[IDX.u]!==uni)return false;
        if(bol&&r[IDX.g]!==bol)return false;
        if(!(r[IDX.sira]>=sira*0.80))return false;  // erişebildiklerin + biraz üstündeki olası/sınırda programlar (2023-25 oynaklığına göre kalibre)
        if(!isNaN(sMin)&&r[IDX.sira]<sMin)return false;
        if(!isNaN(sMax)&&r[IDX.sira]>sMax)return false;
        return true;
      });
      sortReach();
      el('rstatus').innerHTML='<b>'+lastReach.length.toLocaleString('tr-TR')+'</b> program — şansın olan bölümler (Rahat/Olası/Sınırda · sıran: '+sira.toLocaleString('tr-TR')+')';
      draw();
    });
  }
  el('rbody').addEventListener('click',function(e){
    var b=e.target;
    if(b.classList&&b.classList.contains('fav-star')){
      var k=b.getAttribute('data-fid');if(fav&&byId[k])fav.toggle(byId[k]);return;
    }
    if(b.classList&&b.classList.contains('cmp-chk')){
      var ck=b.getAttribute('data-cid'), i=cmpSel.indexOf(ck);
      if(i>=0){cmpSel.splice(i,1);}
      else{
        if(cmpSel.length>=4){b.checked=false;el('rhint').textContent='En fazla 4 program karşılaştırabilirsiniz — önce birini çıkarın.';return;}
        cmpSel.push(ck);
      }
      cmpBar();return;
    }
    if(b.classList&&b.classList.contains('pdet')){
      var ri=b.getAttribute('data-ri');
      var row=el('rbody').querySelector('.pdet-row[data-ri="'+ri+'"]');
      if(!row)return;
      var open=row.hasAttribute('hidden');
      if(open){
        row.querySelector('td').innerHTML=renderDetail(lastReach[ri]);  // ilk açılışta üretilir (lazy)
        row.removeAttribute('hidden');
      } else {
        row.setAttribute('hidden','');
      }
      b.setAttribute('aria-expanded',open?'true':'false');
    }
  });
  var cmpBox=el('cmpBox');
  if(cmpBox)cmpBox.addEventListener('click',function(e){
    if(e.target&&e.target.id==='cmpClearBtn')cmpBox.innerHTML='';
  });
  var cmpGoBtn=el('cmpGoBtn'); if(cmpGoBtn)cmpGoBtn.addEventListener('click',renderCompare);
  var cmpClrBtn=el('cmpClrBtn'); if(cmpClrBtn)cmpClrBtn.addEventListener('click',function(){cmpSel=[];cmpBar();if(cmpBox)cmpBox.innerHTML='';draw();});
  var csvBtn=el('rCsv');
  if(csvBtn)csvBtn.addEventListener('click',function(){
    if(!lastReach.length)return;
    var headers=['Bölüm','Üniversite','İl','Tür','Kontenjan','Taban Puan','Başarı Sırası','Şans'];
    var rows=lastReach.map(function(r){
      var ratio=r[IDX.sira]/lastSira;
      var sans=ratio>=1.20?'Rahat':(ratio>=1.0?'Olası':'Sınırda');
      return [r[IDX.b]||'',r[IDX.u]||'',r[IDX.il]||'',TUR[r[IDX.t]]||'',r[IDX.kont],r[IDX.tp],r[IDX.sira],sans];
    });
    SV.downloadCSV('sinavveri-yks-tercih-robotu.csv',headers,rows);
  });
  el('rBtn').addEventListener('click',run);
  el('rSira').addEventListener('keydown',function(e){if(e.key==='Enter')run();});
  el('rSira').addEventListener('input',function(){if((el('rSira').value||'').replace(/\D/g,''))run();});
  [el('rSMin'),el('rSMax')].forEach(function(e){if(e)e.addEventListener('change',function(){
    if((el('rSira').value||'').replace(/\D/g,''))run(); else syncQS();
  });});
  // Filtre değişince otomatik yeniden hesapla (sıra girilmişse)
  ['rIl','rTur','rDil','rUni','rBol','rPt'].forEach(function(id){var e=el(id);if(e)e.addEventListener('change',function(){
    if((el('rSira').value||'').replace(/\D/g,''))run(); else syncQS();
  });});
  (function(){var ths=document.querySelectorAll('.data-table thead th');ths.forEach(function(th,i){
    if(th.hasAttribute('data-nosort'))return;
    th.style.cursor='pointer';th.title='Sıralamak için tıklayın';
    th.addEventListener('click',function(){if(!lastReach.length)return;sortD=(sortI===i)?-sortD:1;sortI=i;
      ths.forEach(function(o){o.removeAttribute('aria-sort');var a=o.querySelector('.s-arrow');if(a)a.remove();});
      th.setAttribute('aria-sort',sortD>0?'ascending':'descending');
      var ar=document.createElement('span');ar.className='s-arrow';ar.textContent=sortD>0?' ▲':' ▼';th.appendChild(ar);sortReach();draw();});});})();
  (function(){
    var qs=SV.qsGet?SV.qsGet():{};
    if(qs.pt&&PTL[qs.pt])el('rPt').value=qs.pt;
    if(qs.tur)el('rTur').value=qs.tur;
    if(qs.il){var s=el('rIl');var o=document.createElement('option');o.value=qs.il;o.textContent=qs.il;o.selected=true;s.appendChild(o);}
    if(qs.dil&&el('rDil')){var sd=el('rDil');var od=document.createElement('option');od.value=qs.dil;od.textContent=qs.dil;od.selected=true;sd.appendChild(od);}
    ['uni','bol'].forEach(function(kk){var idm={uni:'rUni',bol:'rBol'};if(qs[kk]&&el(idm[kk])){var se=el(idm[kk]);var oo=document.createElement('option');oo.value=qs[kk];oo.textContent=qs[kk];oo.selected=true;se.appendChild(oo);}});
    if(qs.smin!=null&&el('rSMin'))el('rSMin').value=qs.smin;
    if(qs.smax!=null&&el('rSMax'))el('rSMax').value=qs.smax;
    if(qs.sira){el('rSira').value=qs.sira;run();}else{drawChips();}
  })();
})();
</script>"""


# Resmî ÖSYM kılavuz kutusu — sırayla dener: (1) her yıl otomatik güncellenen kilavuz_2026.json
# (pipeline/kilavuz_diff.py), (2) o da yoksa sabit 2026 linkleri (2026-07'de doğrulandı, elle
# indirildi). dokuman.osym.gov.tr dosya adları güncellemede değişebilir — bu yüzden mümkünse
# kilavuz_2026.json TERCİH edilir (canlı sayfadan bulunmuş, güncel).
_KV_FALLBACK = {
    "pdf_url": "https://dokuman.osym.gov.tr/web/2026/7/2026-yuksekogretim-kurumlari-sinavi-yks-yuksekogretim-programlari-ve-kontenjanlari-kilavuzu-h5q8kv-30170002.pdf",
    "tablo3_url": "https://dokuman.osym.gov.tr/web/2026/7/tablo-3-29u1s7pl.xls",
    "tablo4_url": "https://dokuman.osym.gov.tr/web/2026/7/tablo-4-hohu0j-30164357.xls",
    "guncelleme": None, "kapanan_kodlar": [],
}


def _kilavuz_verisi():
    p = ROOT / "data" / "kilavuz_2026.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return _KV_FALLBACK


def page_tercih_robotu():
    kv = _kilavuz_verisi()
    guncelleme = fmt_date(kv["guncelleme"][:10]) if kv.get("guncelleme") else None
    kapanan_kodlar = [k["kod"] if isinstance(k, dict) else k for k in kv.get("kapanan_kodlar", [])]
    kilavuz_box = f"""<div class="info-box" style="margin-bottom:16px">
  <b>📋 2026 YKS Resmî Kılavuzu ve Kontenjan Tabloları</b>{f' <span style="color:var(--fg-faded);font-weight:400">· son kontrol {guncelleme}</span>' if guncelleme else ''}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px">
    <a class="btn btn-ghost" href="{kv['pdf_url']}" target="_blank" rel="noopener">📄 Kılavuz PDF'i</a>
    <a class="btn btn-ghost" href="{kv['tablo3_url']}" target="_blank" rel="noopener">📊 Tablo-3 (Kontenjanlar)</a>
    <a class="btn btn-ghost" href="{kv['tablo4_url']}" target="_blank" rel="noopener">📊 Tablo-4 (Kontenjanlar)</a>
  </div>
  <div style="font-size:12.5px;color:var(--fg-faded);margin-top:8px">Bu üç dosya ÖSYM'nin resmî 2026 YKS kılavuzudur — programımızdaki
  taban puan/sıra verisi bu tablolardaki program kodlarıyla otomatik karşılaştırılır; kılavuzdan kalkan programlar
  aşağıdaki listede <span class="tag tag-other">⛔ Bu yıl alım yapmıyor</span> rozetiyle işaretlenir.</div>
</div>"""
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / Tercih Robotu</div>
<div class="page-title"><h1>{TAKVIM_YILI} YKS Tercih Robotu</h1><span class="sub">Başarı sıranı gir, yerleşebileceğin programları gör · 2025 YÖK Atlas yerleştirme verisine göre</span></div>
""" + robot_nav("tercih-robotu.html") + kilavuz_box + """
<div class="fav-bar" id="favBar"><button type="button" class="fav-toggle" id="favBtn">⭐ Tercih Listem (0)</button></div>
<div class="fav-panel" id="favPanel"></div>

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
    <div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">Üniversite (ops.)</label>
      <select id="rUni" class="btn btn-ghost" style="text-align:left;width:100%;margin-top:4px"><option value="">Tüm üniversiteler</option></select></div>
    <div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">Bölüm (ops.)</label>
      <select id="rBol" class="btn btn-ghost" style="text-align:left;width:100%;margin-top:4px"><option value="">Tüm bölümler</option></select></div>
    <div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">Başarı Sırası (en az, ops.)</label>
      <input id="rSMin" type="text" inputmode="numeric" placeholder="örn. 30000" style="width:100%;margin-top:4px;padding:9px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:14px"></div>
    <div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">Başarı Sırası (en çok, ops.)</label>
      <input id="rSMax" type="text" inputmode="numeric" placeholder="örn. 60000" style="width:100%;margin-top:4px;padding:9px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:14px"></div>
    <button type="button" class="btn btn-primary" id="rBtn">Programları Göster</button>
    <button type="button" class="btn btn-ghost" id="rCsv">⬇️ CSV İndir</button>
  </div>
  <div class="filter-chips" id="chips" style="display:none"></div>
  <div id="rstatus" style="margin-top:14px;font-size:14px;color:var(--accent);font-weight:700"></div>
</div>

<div class="data-table-wrap">
<table class="data-table" data-live="1">
<thead><tr><th data-tip="Programın YÖK Atlas'taki tam adı ve bağlı olduğu üniversite." data-type="text">Program / Üniversite</th><th data-tip="Programın bulunduğu il." data-type="text">İl</th><th data-tip="Üniversite türü: Devlet, Vakıf, KKTC veya özel kontenjan türü." data-type="text">Tür</th><th data-tip="Programın 2025 genel kontenjanı (kaç kişi alındığı)." data-type="num">Kontenjan</th><th data-tip="Programa 2025'te en son yerleşen adayın YKS yerleştirme puanı." data-type="num">Taban Puan</th><th data-tip="Programın 2025 taban başarı sırası. Küçük sıra = daha yüksek başarı. ℹ️ ile 2024/2023 geçmişini görebilirsiniz." data-type="num">Başarı Sırası</th><th data-tip="Girdiğin sıraya göre yerleşme şansı: Rahat (güvenli), Olası (sıraya yakın), Sınırda (riskli)." data-type="text">Şans</th><th data-nosort data-tip="Programı ⭐ ile tercih listene ekle.">⭐</th><th data-nosort data-tip="En fazla 4 programı işaretleyip yan yana karşılaştırın.">⚖️</th></tr></thead>
<tbody id="rbody"></tbody>
</table>
</div>
<nav id="rPager"></nav>
<div id="rhint" style="display:none;font-size:12px;color:var(--fg-faded);margin-top:10px;text-align:center"></div>
<div id="cmpBar" style="display:none;align-items:center;gap:10px;margin-top:14px;padding:10px 14px;background:var(--bg-card-alt);border:1px solid var(--border);border-radius:10px">
  <b id="cmpCount" style="font-size:13px">0/4 seçili</b>
  <button type="button" class="btn btn-primary" id="cmpGoBtn" disabled>⚖️ Karşılaştır</button>
  <button type="button" class="btn btn-ghost" id="cmpClrBtn">Temizle</button>
</div>
<div id="cmpBox" style="margin-top:14px"></div>

<div class="notice"><b>Nasıl çalışır?</b> Sıranı girdiğinde hem rahat yerleşeceğin hem de <b>şansın olan</b> programlar listelenir.
"Şans": <b>Rahat</b> (taban sıran senden epey geride — güvenli), <b>Olası</b> (sıraya yakın), <b>Sınırda</b> (taban senden biraz daha iyi — riskli ama 2026'da değişebileceği için denenebilir).
Bu bir tahmindir; 2026 taban sıraları kontenjan ve tercih yoğunluğuna göre değişir. Resmî tercih için
<a href="https://www.osym.gov.tr" target="_blank" rel="noopener">ÖSYM</a> kılavuzu esastır.</div>
""" + ROBOT_JS.replace("__KAPANAN_KODLAR__", json.dumps(kapanan_kodlar))
    # rIl doldurma — robot da fillIl benzeri ister; basitçe SEARCH veri yüklenince doldurulmuyor.
    fill = r"""<script nonce="__NONCE__">
(function(){
  function el(i){return document.getElementById(i);}
  var ptSel=el('rPt'), DATA=null;
  function bdil(s){s=s||'';var i=s.indexOf(' (');return i>0?s.slice(0,i):s;}
  // cascading: İl/Dil/Üniversite/Bölüm birbirine + Tür'e göre daralır (rTur statik kalır)
  var DIMS=[{id:'rIl',ph:'Tüm iller',get:function(r){return r[4];}},
            {id:'rDil',ph:'Tüm diller',get:function(r){return bdil(r[7]);}},
            {id:'rUni',ph:'Tüm üniversiteler',get:function(r){return r[1];}},
            {id:'rBol',ph:'Tüm bölümler',get:function(r){return r[3];}}];
  function passExc(r,exId){
    for(var i=0;i<DIMS.length;i++){var f=DIMS[i];if(f.id===exId)continue;var s=el(f.id);if(s&&s.value&&String(f.get(r))!==s.value)return false;}
    var t=el('rTur');if(t&&t.value&&r[5]!==t.value)return false;
    return true;
  }
  function repop(){ if(!DATA)return;
    DIMS.forEach(function(f){var sel=el(f.id);if(!sel)return;var cur=sel.value;
      var cnt={};DATA.forEach(function(r){if(!passExc(r,f.id))return;var v=f.get(r);if(v!=null&&v!=='')cnt[v]=(cnt[v]||0)+1;});
      var ks=Object.keys(cnt).sort(function(a,b){return cnt[b]-cnt[a]||String(a).localeCompare(String(b),'tr');});
      sel.innerHTML='<option value="">'+f.ph+'</option>';var hc=false;
      ks.forEach(function(k){var o=document.createElement('option');o.value=k;o.textContent=k+' ('+cnt[k]+')';if(k===cur){o.selected=true;hc=true;}sel.appendChild(o);});
      if(cur&&!hc){var o2=document.createElement('option');o2.value=cur;o2.textContent=cur+' (0)';o2.selected=true;sel.appendChild(o2);}
    });
  }
  function load(){fetch('/veri/'+ptSel.value+'.json').then(function(r){return r.json();}).then(function(j){DATA=j;repop();}).catch(function(){});}
  ptSel.addEventListener('change',load);
  ['rIl','rTur','rDil','rUni','rBol'].forEach(function(id){var e=el(id);if(e)e.addEventListener('change',repop);});
  load();
})();
</script>"""
    body += fill
    return base("tercih-robotu.html", "2026 YKS Tercih Robotu — Sıralamana Göre Bölüm Bul | SınavVeri",
                f"{TAKVIM_YILI} YKS tercih robotu: başarı sıranı gir, 2025 YÖK Atlas yerleştirme verisine göre yerleşebileceğin üniversite programlarını anında gör. Ücretsiz.",
                body, extra_ld=[breadcrumb_ld([("Ana Sayfa", "index.html"), ("Tercih Robotu", None)])])


# ───────────────────────── BÖLÜM (program grubu) SAYFALARI ─────────────────────────
PUAN_ROBOT_JS = r"""<script nonce="__NONCE__">
(function(){
  var CFG=__CFG__, SV=window.SV||{}, NCOL=CFG.show.length+5+(CFG.hist?1:0);
  var data=[],byId={},cmpData={},cmpSel=[];
  var pf0=function(n){return n==null?'—':Number(n).toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2});};
  // Kodlu kolonlar (ör. LGS tür harfi 'F'→'Fen Lisesi') — CFG.maps={idx:{kod:etiket}} varsa uygulanır.
  function mapped(idx,v){ var m=CFG.maps&&CFG.maps[idx]; return m&&m[v]!=null? m[v] : v; }
  // ⓘ açılır detay: 2025/2024/2023 taban (+varsa sıra) geçmişi — bölüm/üniversite sayfalarındaki
  // .pdet/.pdet-row/.pdet-hist CSS sınıfları AYNEN kullanılır (assets/style.css, kanonik desen).
  // Robot verisi client-JSON'da kompakt dizi olduğu için burada yalnız DİZİDE ZATEN VAR OLAN
  // alanlardan kurulur (kadro/akreditasyon/koşul gibi bölüm-sayfası-özel alanlar burada yok).
  function detailRow(r,ncol){
    var yillar=[];
    if(CFG.hist){
      CFG.hist.forEach(function(h){
        var t=r[h.t]; if(t==null) return;
        yillar.push('<tr><td>'+h.yil+'</td><td>'+pf0(t)+'</td>'+(h.s!=null&&r[h.s]!=null?'<td>'+Number(r[h.s]).toLocaleString('tr-TR')+'</td>':(CFG.histHasSira?'<td>—</td>':''))+'</tr>');
      });
    }
    if(!yillar.length) return '';
    var thead='<tr><th>Yıl</th><th>Taban</th>'+(CFG.histHasSira?'<th>Sıra</th>':'')+'</tr>';
    return '<tr class="pdet-row"><td colspan="'+ncol+'"><div class="pdet-box"><b>Geçmiş yıllar</b>'+
      '<table class="pdet-hist"><thead>'+thead+'</thead><tbody>'+yillar.join('')+'</tbody></table></div></td></tr>';
  }
  var fav=SV.initFav?SV.initFav({ns:CFG.ns_key||'robot',barId:'favBar',panelId:'favPanel',btnId:'favBtn'}):null;
  function el(id){return document.getElementById(id);}
  var pf=function(n){return n==null?'—':Number(n).toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2});};
  if(SV.skel)SV.skel('rbody',NCOL,6);
  el('rstatus').textContent='Veriler yükleniyor…';
  fetch(CFG.file).then(function(r){return r.json();}).then(function(j){data=j;initFilters();el('rstatus').textContent='';applyQS();initFilters();})
    .catch(function(){el('rstatus').textContent='Veri yüklenemedi.';});
  function initFilters(){  // cascading: her filtre, diğer seçili filtrelere göre yeniden dolar
    CFG.filters.forEach(function(f,n){
      var sel=el('rf'+n);if(!sel)return;var cur=sel.value;
      var cnt={};data.forEach(function(r){
        for(var k=0;k<CFG.filters.length;k++){if(k===n)continue;var s=el('rf'+k);if(s&&s.value&&String(r[CFG.filters[k][0]])!==s.value)return;}
        var v=r[f[0]];if(v!=null&&v!=='')cnt[v]=(cnt[v]||0)+1;
      });
      var ks=Object.keys(cnt).sort(function(a,b){return cnt[b]-cnt[a]||String(a).localeCompare(String(b),'tr');});
      sel.innerHTML='<option value="">Tümü</option>';var hc=false;
      ks.forEach(function(k){var o=document.createElement('option');o.value=k;o.textContent=mapped(f[0],k)+' ('+cnt[k]+')';if(k===cur){o.selected=true;hc=true;}sel.appendChild(o);});
      if(cur&&!hc){var o2=document.createElement('option');o2.value=cur;o2.textContent=mapped(f[0],cur)+' (0)';o2.selected=true;sel.appendChild(o2);}
    });
  }
  function applyQS(){
    var qs=SV.qsGet?SV.qsGet():{};
    if(qs.puan!=null)el('rPuan').value=qs.puan;
    if(qs.tmin!=null&&el('rTMin'))el('rTMin').value=qs.tmin;
    if(qs.tmax!=null&&el('rTMax'))el('rTMax').value=qs.tmax;
    CFG.filters.forEach(function(f,n){var s=el('rf'+n);if(s&&qs['f'+n]!=null)s.value=qs['f'+n];});
    if(qs.puan){run();}else{drawChips();}
  }
  function syncQS(){
    var o={};var p=el('rPuan').value.trim();if(p)o.puan=p;
    var tmin=el('rTMin')&&el('rTMin').value.trim();if(tmin)o.tmin=tmin;
    var tmax=el('rTMax')&&el('rTMax').value.trim();if(tmax)o.tmax=tmax;
    CFG.filters.forEach(function(f,n){var s=el('rf'+n);if(s&&s.value)o['f'+n]=s.value;});
    if(SV.qsSet)SV.qsSet(o);drawChips();
  }
  function drawChips(){
    if(!SV.chips)return;var items=[];var p=el('rPuan').value.trim();
    if(p)items.push({key:'puan',label:'Puan: '+p});
    var tmin=el('rTMin')&&el('rTMin').value.trim(), tmax=el('rTMax')&&el('rTMax').value.trim();
    if(tmin||tmax)items.push({key:'trange',label:'Taban: '+(tmin||'—')+' – '+(tmax||'—')});
    CFG.filters.forEach(function(f,n){var s=el('rf'+n);if(s&&s.value)items.push({key:'f'+n,label:f[1]+': '+s.value});});
    SV.chips('chips',items,function(key){
      if(key==='__all__'){el('rPuan').value='';if(el('rTMin'))el('rTMin').value='';if(el('rTMax'))el('rTMax').value='';CFG.filters.forEach(function(f,n){var s=el('rf'+n);if(s)s.value='';});}
      else if(key==='puan')el('rPuan').value='';
      else if(key==='trange'){if(el('rTMin'))el('rTMin').value='';if(el('rTMax'))el('rTMax').value='';}
      else CFG.filters.forEach(function(f,n){if('f'+n===key){var s=el('rf'+n);if(s)s.value='';}});
      initFilters();run();
    });
  }
  var lastReach=[],userP=0,sortI=null,sortD=1,pgr=null;   // sayfalama: pager.js (rule 3.17)
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
    var tb=el('rbody');byId={};
    if(!lastReach.length){tb.innerHTML='';if(SV.empty)SV.empty('rbody',NCOL,'Bu puan ve filtrelerle yerleşebileceğin sonuç bulunamadı. Puanı veya filtreleri gözden geçirin.');el('rhint').style.display='none';if(pgr)pgr.reset();return;}
    var out=[];
    lastReach.forEach(function(r,ri){
      var m=userP-r[CFG.taban];
      var safe=m>=CFG.t1?'<span class="tag tag-lgs">Rahat</span>':(m>=0?'<span class="tag tag-kpss">Olası</span>':'<span class="tag tag-other">Sınırda</span>');
      // "Yeni" rozeti: geçmiş yıl verisinin TAMAMI boşsa (kayıt tarihçesi yok) — kesin değil ama
      // güçlü sinyal (bkz. hist alanları). CFG.hist yoksa (ör. LGS'de kısmi) rozet basılmaz.
      var yeni = CFG.hist && CFG.hist.every(function(h){return r[h.t]==null;})
        ? ' <span class="tag tag-other" title="Önceki yıllarda taban puan kaydı yok — yeni açılmış veya ilk kez ilan edilmiş olabilir">🆕 Yeni</span>' : '';
      var name='<td><strong>'+(r[CFG.nb]||'')+'</strong>'+yeni+(CFG.ns!=null?'<br><small>'+(r[CFG.ns]||'')+'</small>':'')+'</td>';
      var show='';CFG.show.forEach(function(c){var v=r[c[0]];show+='<td>'+(v==null||v===''?'—':mapped(c[0],v))+'</td>';});
      var det=CFG.hist?detailRow(r,NCOL):'';
      var dbtn=det? '<td style="text-align:center"><button type="button" class="pdet" data-ri="'+ri+'" aria-expanded="false" aria-label="Geçmiş yıl verilerini göster">ℹ️</button></td>' : (CFG.hist?'<td></td>':'');
      var k=rkey(r);byId[k]={id:k,name:String(r[CFG.nb]||''),sub:(CFG.ns!=null?String(r[CFG.ns]||''):''),meta:'taban '+pf(r[CFG.taban])};
      cmpData[k]=r;
      var on=fav&&fav.has(k);
      var star='<td style="text-align:center"><button type="button" class="fav-star'+(on?' on':'')+'" data-fid="'+k.replace(/"/g,'&quot;')+'" aria-label="Tercih listeme ekle">'+(on?'★':'☆')+'</button></td>';
      var onCmp=cmpSel.indexOf(k)>=0;
      var cmp='<td style="text-align:center"><input type="checkbox" class="cmp-chk" data-cid="'+k.replace(/"/g,'&quot;')+'"'+(onCmp?' checked':'')+' aria-label="Karşılaştırmaya ekle"></td>';
      out.push('<tr>'+name+show+'<td><strong>'+pf(r[CFG.taban])+'</strong></td><td>'+safe+'</td>'+dbtn+star+cmp+'</tr>');
      if(det) out.push(det.replace('<tr class="pdet-row">','<tr class="pdet-row" data-ri="'+ri+'" hidden>'));
    });
    tb.innerHTML=out.join('');
    if(!pgr&&window.TVPager)pgr=window.TVPager.attach({grid:tb.parentNode,per:25,mount:el('rPager')});
    else if(pgr)pgr.reset();
    el('rhint').style.display='block';
    el('rhint').textContent='Sütun başlığına tıklayarak sıralayabilir, filtrelerle listeyi daraltabilirsiniz.';
    cmpBar();
  }
  // Program karşılaştırma — sonuç tablosundan seçilen 2-4 kaydı yan yana (transpoze) gösterir.
  // Seçim yalnız bu oturumda tutulur (localStorage yok — ⭐ Tercih Listem zaten kalıcı seçenek).
  function cmpBar(){
    var bar=el('cmpBar'); if(!bar)return;
    bar.style.display=cmpSel.length?'flex':'none';
    var lbl=el('cmpCount'); if(lbl)lbl.textContent=cmpSel.length+'/4 seçili';
    var btn=el('cmpGoBtn'); if(btn)btn.disabled=cmpSel.length<2;
  }
  function renderCompare(){
    var box=el('cmpBox'); if(!box)return;
    var cols=cmpSel.map(function(k){return cmpData[k];}).filter(Boolean);
    if(cols.length<2){box.innerHTML='';return;}
    var head='<tr><th>Program</th>'+cols.map(function(r){return '<td><strong>'+(r[CFG.nb]||'')+'</strong>'+(CFG.ns!=null?'<br><small>'+(r[CFG.ns]||'')+'</small>':'')+'</td>';}).join('')+'</tr>';
    var body=CFG.show.map(function(c){
      return '<tr><th>'+c[1]+'</th>'+cols.map(function(r){var v=r[c[0]];return '<td>'+(v==null||v===''?'—':mapped(c[0],v))+'</td>';}).join('')+'</tr>';
    }).join('')+'<tr><th>Taban</th>'+cols.map(function(r){return '<td><strong>'+pf(r[CFG.taban])+'</strong></td>';}).join('')+'</tr>';
    box.innerHTML='<div class="data-table-wrap"><table class="data-table"><thead>'+head+'</thead><tbody>'+body+'</tbody></table></div>'
      +'<button type="button" class="btn btn-ghost" id="cmpClearBtn" style="margin-top:8px">✕ Karşılaştırmayı Kapat</button>';
    box.scrollIntoView({behavior:'smooth',block:'nearest'});
  }
  function run(){
    syncQS();
    var p=parseFloat((el('rPuan').value||'').replace(',','.').replace(/[^0-9.]/g,''));
    if(isNaN(p)||p<=0){el('rstatus').textContent='Lütfen geçerli bir puan girin.';el('rbody').innerHTML='';return;}
    userP=p;
    var tMin=parseFloat((el('rTMin')&&el('rTMin').value||'').replace(',','.'));
    var tMax=parseFloat((el('rTMax')&&el('rTMax').value||'').replace(',','.'));
    lastReach=data.filter(function(r){
      for(var k=0;k<CFG.filters.length;k++){var s=el('rf'+k);if(s&&s.value&&String(r[CFG.filters[k][0]])!==s.value)return false;}
      var t=r[CFG.taban];
      if(t==null||t>p+CFG.t2)return false;  // erişebildiklerin + biraz üstündeki sınırda olanlar
      if(!isNaN(tMin)&&t<tMin)return false;
      if(!isNaN(tMax)&&t>tMax)return false;
      return true;
    });
    sortReach();
    el('rstatus').innerHTML='<b>'+lastReach.length.toLocaleString('tr-TR')+'</b> '+CFG.noun+' şansın var (Rahat/Olası/Sınırda · puanın: '+pf(p)+')';
    draw();
  }
  el('rbody').addEventListener('click',function(e){
    var b=e.target;
    if(b.classList&&b.classList.contains('fav-star')){
      var k=b.getAttribute('data-fid');if(fav&&byId[k])fav.toggle(byId[k]);return;
    }
    if(b.classList&&b.classList.contains('cmp-chk')){
      var ck=b.getAttribute('data-cid'), i=cmpSel.indexOf(ck);
      if(i>=0){cmpSel.splice(i,1);}
      else{
        if(cmpSel.length>=4){b.checked=false;el('rhint').textContent='En fazla 4 program karşılaştırabilirsiniz — önce birini çıkarın.';return;}
        cmpSel.push(ck);
      }
      cmpBar();return;
    }
    if(b.classList&&b.classList.contains('pdet')){
      var ri=b.getAttribute('data-ri');
      var row=el('rbody').querySelector('.pdet-row[data-ri="'+ri+'"]');
      if(!row)return;
      var open=row.hasAttribute('hidden');
      if(open)row.removeAttribute('hidden');else row.setAttribute('hidden','');
      b.setAttribute('aria-expanded',open?'true':'false');
    }
  });
  var cmpBox=el('cmpBox');
  if(cmpBox)cmpBox.addEventListener('click',function(e){
    if(e.target&&e.target.id==='cmpClearBtn')cmpBox.innerHTML='';
  });
  var cmpGoBtn=el('cmpGoBtn'); if(cmpGoBtn)cmpGoBtn.addEventListener('click',renderCompare);
  var cmpClrBtn=el('cmpClrBtn'); if(cmpClrBtn)cmpClrBtn.addEventListener('click',function(){cmpSel=[];cmpBar();if(cmpBox)cmpBox.innerHTML='';draw();});
  var csvBtn=el('rCsv');
  if(csvBtn)csvBtn.addEventListener('click',function(){
    if(!lastReach.length)return;
    var headers=[CFG.ns!=null?'Program':'Ad'];
    if(CFG.ns!=null)headers.push('Üniversite/Kurum');
    CFG.show.forEach(function(c){headers.push(c[1]);});
    headers.push('Taban','Şans');
    var rows=lastReach.map(function(r){
      var m=userP-r[CFG.taban], sans=m>=CFG.t1?'Rahat':(m>=0?'Olası':'Sınırda');
      var row=[r[CFG.nb]||'']; if(CFG.ns!=null)row.push(r[CFG.ns]||'');
      CFG.show.forEach(function(c){var v=r[c[0]];row.push(v==null||v===''?'':mapped(c[0],v));});
      row.push(r[CFG.taban],sans); return row;
    });
    SV.downloadCSV('sinavveri-'+(CFG.ns_key||'sonuclar')+'.csv',headers,rows);
  });
  el('rBtn').addEventListener('click',run);
  el('rPuan').addEventListener('keydown',function(e){if(e.key==='Enter')run();});
  el('rPuan').addEventListener('input',function(){if(el('rPuan').value.trim())run();});
  [el('rTMin'),el('rTMax')].forEach(function(e){if(e)e.addEventListener('change',function(){if(el('rPuan').value.trim())run();else syncQS();});});
  // Filtre değişince cascade + otomatik yeniden hesapla (puan girilmişse)
  CFG.filters.forEach(function(f,n){var s=el('rf'+n);if(s)s.addEventListener('change',function(){
    initFilters(); if(el('rPuan').value.trim())run(); else syncQS();
  });});
  (function(){
    var ths=document.querySelectorAll('.data-table thead th');
    ths.forEach(function(th,i){
      if(th.hasAttribute('data-nosort'))return;
      th.style.cursor='pointer'; th.title='Sıralamak için tıklayın';
      th.addEventListener('click',function(){
        if(!lastReach.length)return;
        sortD=(sortI===i)?-sortD:1; sortI=i;
        ths.forEach(function(o){o.removeAttribute('aria-sort');var a=o.querySelector('.s-arrow');if(a)a.remove();});
        th.setAttribute('aria-sort',sortD>0?'ascending':'descending');
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
                    noun, t1, t2, intro, kaynak, puan_label, ph, hist=None, hist_has_sira=False, maps=None,
                    kilavuz_url=None):
    """Generic puan-bazlı tercih robotu. nb/ns: ad sütun idx (bold/alt). show: [(idx,label)] ek sütun.
    taban: taban puan idx. filters: [(idx,label)]. t1/t2: 'Rahat'/'Olası' eşik (puan farkı).
    hist: [{"yil":2024,"t":idx,"s":idx|None}, …] — verilirse ⓘ açılır satırında geçmiş yıl
    taban(+sıra) tablosu gösterilir VE "🆕 Yeni" rozeti (tüm hist alanları boşsa) devreye girer.
    maps: {idx: {kod: etiket}} — kodlu bir `show` kolonunu insan-okur etikete çevirir (ör. LGS türü).
    kilavuz_url: verilirse resmî ÖSYM kılavuzu bilgi kutusu eklenir (bkz. SINAV_KILAVUZ_URL)."""
    fhtml = ""
    for n, (idx, label) in enumerate(filters):
        fhtml += (f'<div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">{label}</label>'
                  f'<select id="rf{n}" class="btn btn-ghost" style="text-align:left;width:100%;margin-top:4px">'
                  f'<option value="">Tümü</option></select></div>')
    thead = (th_html("Program" if ns is not None else "Ad") + "".join(th_html(l) for _, l in show)
             + th_html("Taban") + th_html("Şans")
             + (('<th data-nosort data-tip="Geçmiş yıl taban puanlarını gösterir.">ⓘ</th>') if hist else "")
             + '<th data-nosort data-tip="Kaydı ⭐ ile tercih listene ekle.">⭐</th>'
             + '<th data-nosort data-tip="En fazla 4 kaydı işaretleyip yan yana karşılaştırın.">⚖️</th>')
    ns_key = slug.replace("-tercih-robotu.html", "").replace(".html", "")
    cfg = {"file": veri_file, "nb": nb, "ns": ns, "show": [[i, l] for i, l in show],
           "taban": taban, "filters": [[i, l] for i, l in filters], "noun": noun, "t1": t1, "t2": t2, "ns_key": ns_key,
           "hist": hist, "histHasSira": hist_has_sira,
           "maps": {str(i): m for i, m in maps.items()} if maps else None}
    js = PUAN_ROBOT_JS.replace("__CFG__", json.dumps(cfg, ensure_ascii=False))
    kilavuz_box = (f"""<div class="info-box" style="margin-bottom:16px">
  <b>📋 Resmî ÖSYM Kılavuzu</b>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px">
    <a class="btn btn-ghost" href="{kilavuz_url}" target="_blank" rel="noopener">📄 Kılavuz ve Program Bilgileri →</a>
  </div>
  <div style="font-size:12.5px;color:var(--fg-faded);margin-top:8px">Program kodu, kontenjan ve tercih koşulları için ÖSYM'nin güncel resmî kılavuzunu kontrol edin — kodlar yıldan yıla değişebilir.</div>
</div>""" if kilavuz_url else "")
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / <a href="/tercih-robotu.html">Tercih Robotu</a> / {h1}</div>
<div class="page-title"><h1>{h1}</h1><span class="sub">{sub}</span></div>
{robot_nav(slug)}{kilavuz_box}
<div class="fav-bar" id="favBar"><button type="button" class="fav-toggle" id="favBtn">⭐ Tercih Listem (0)</button></div>
<div class="fav-panel" id="favPanel"></div>
<div class="info-box">{intro}</div>
<div class="calc-card" style="margin-bottom:18px">
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;align-items:end">
    <div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">{puan_label}</label>
      <input id="rPuan" type="text" inputmode="decimal" placeholder="{ph}" style="width:100%;margin-top:4px;padding:9px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:14px"></div>
    {fhtml}
    <div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">Taban (en az, ops.)</label>
      <input id="rTMin" type="text" inputmode="decimal" placeholder="örn. 300" style="width:100%;margin-top:4px;padding:9px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:14px"></div>
    <div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">Taban (en çok, ops.)</label>
      <input id="rTMax" type="text" inputmode="decimal" placeholder="örn. 400" style="width:100%;margin-top:4px;padding:9px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:14px"></div>
    <button type="button" class="btn btn-primary" id="rBtn">Yerleşebileceklerimi Göster</button>
    <button type="button" class="btn btn-ghost" id="rCsv">⬇️ CSV İndir</button>
  </div>
  <div class="filter-chips" id="chips" style="display:none"></div>
  <div id="rstatus" style="margin-top:14px;font-size:14px;color:var(--accent);font-weight:700"></div>
</div>
<div class="data-table-wrap">
<table class="data-table" data-live="1"><thead><tr>{thead}</tr></thead><tbody id="rbody"></tbody></table>
</div>
<nav id="rPager"></nav>
<div id="rhint" style="display:none;font-size:12px;color:var(--fg-faded);margin-top:10px;text-align:center"></div>
<div id="cmpBar" style="display:none;align-items:center;gap:10px;margin-top:14px;padding:10px 14px;background:var(--bg-card-alt);border:1px solid var(--border);border-radius:10px">
  <b id="cmpCount" style="font-size:13px">0/4 seçili</b>
  <button type="button" class="btn btn-primary" id="cmpGoBtn" disabled>⚖️ Karşılaştır</button>
  <button type="button" class="btn btn-ghost" id="cmpClrBtn">Temizle</button>
</div>
<div id="cmpBox" style="margin-top:14px"></div>
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
        "/veri/dgs.json", 1, 0, [(2, "Kontenjan"), (4, "Tavan")], 3, [(1, "Bölüm"), (0, "Üniversite / Fakülte")],
        "programa", 15, 4,
        "DGS puanını girin; o puanla yerleşebileceğin (taban puanı ≤ senin puanın) tüm lisans programlarını en yüksek tabandan başlayarak listeler. "
        "DGS net hesaplama için <a href='/dgs-puan-hesaplama.html'>DGS puan hesaplama</a>.",
        "2025 DGS resmî ÖSYM yerleştirme verisi.", "DGS Puanın", "örn. 290,5",
        hist=[{"yil": 2025, "t": 3}, {"yil": 2024, "t": 5}, {"yil": 2023, "t": 6}],
        kilavuz_url="https://www.osym.gov.tr/SinavGrubu/Index/8")


def page_tus_robot():
    if not (ROOT / "veri" / "tus.json").exists():
        return None
    return puan_robot_page(
        "tus-tercih-robotu.html", "2026 TUS Tercih Robotu — Puanına Göre Uzmanlık Dalı Bul | SınavVeri",
        "2026 TUS tercih robotu: TUS puanını gir, 2025 ÖSYM yerleştirme verisine göre girebileceğin uzmanlık dalı ve kurumları gör. Ücretsiz.",
        "2026 TUS Tercih Robotu", "Tıpta Uzmanlık · TUS puanını gir, girebileceğin dal/kurumları gör · 2025 ÖSYM verisine göre",
        "/veri/tus.json", 1, 0, [(2, "Tür"), (3, "Kontenjan"), (5, "Tavan")], 4, [(9, "Uzmanlık Dalı"), (2, "Kontenjan Türü")],
        "uzmanlık dalına", 4, 1,
        "TUS puanını girin; o puanla girebileceğin (taban ≤ puanın) kurum ve uzmanlık dallarını en yüksek tabandan başlayarak listeler. "
        "Uzmanlık dalı ve kontenjan türüne göre filtreleyebilirsin. TUS hesaplama için <a href='/yks-puan-hesaplama.html'>puan araçları</a>.",
        "2025 TUS 1. dönem resmî ÖSYM yerleştirme verisi.", "TUS Puanın", "örn. 58,40",
        hist=[{"yil": 2025, "t": 4}, {"yil": 2024, "t": 6}, {"yil": 2023, "t": 7}],
        kilavuz_url="https://www.osym.gov.tr/SinavGrubu/Index/6")


def page_dus_robot():
    if not (ROOT / "veri" / "dus.json").exists():
        return None
    return puan_robot_page(
        "dus-tercih-robotu.html", "2026 DUS Tercih Robotu — Puanına Göre Uzmanlık Dalı Bul | SınavVeri",
        "2026 DUS tercih robotu: DUS puanını gir, 2025 ÖSYM yerleştirme verisine göre girebileceğin diş hekimliği uzmanlık dalı ve kurumları gör. Ücretsiz.",
        "2026 DUS Tercih Robotu", "Diş Hekimliği Uzmanlık · DUS puanını gir, girebileceğin dal/kurumları gör · 2025 ÖSYM verisine göre",
        "/veri/dus.json", 1, 0, [(2, "Tür"), (3, "Kontenjan"), (5, "Tavan")], 4, [(9, "Uzmanlık Dalı"), (2, "Kontenjan Türü")],
        "uzmanlık dalına", 4, 1,
        "DUS puanını girin; o puanla girebileceğin (taban ≤ puanın) kurum ve diş hekimliği uzmanlık dallarını listeler. "
        "Uzmanlık dalı ve kontenjan türüne göre filtreleyebilirsin.",
        "2025 DUS resmî ÖSYM yerleştirme verisi.", "DUS Puanın", "örn. 55,20",
        hist=[{"yil": 2025, "t": 4}, {"yil": 2024, "t": 6}, {"yil": 2023, "t": 7}],
        kilavuz_url="https://www.osym.gov.tr/SinavGrubu/Index/9")


def page_kpss_robot():
    if not (ROOT / "veri" / "kpss.json").exists():
        return None
    return puan_robot_page(
        "kpss-tercih-robotu.html", "2026 KPSS Tercih Robotu — Puanına Göre Kadro Bul | SınavVeri",
        "2026 KPSS tercih robotu: KPSS puanını gir, 2025 ÖSYM atama verisine göre yerleşebileceğin kadro/pozisyonları gör. Ücretsiz (Lisans/Önlisans/Ortaöğretim).",
        "2026 KPSS Tercih Robotu", "KPSS puanını gir, atanabileceğin kadroları gör · 2025 ÖSYM yerleştirmelerine göre",
        "/veri/kpss.json", 1, 0, [(2, "İl"), (3, "Düzey"), (5, "Kontenjan"), (7, "Tavan")], 6, [(2, "İl"), (3, "Düzey"), (4, "Dönem")],
        "kadroya", 4, 1,
        "KPSS puanını girin ve öğrenim düzeyinizi (Lisans/Önlisans/Ortaöğretim) seçin; o puanla atanabileceğin (taban ≤ puanın) kadroları listeler. "
        "İl ve döneme göre de filtreleyebilirsin. KPSS hesaplama için <a href='/kpss-puan-hesaplama.html'>KPSS puan hesaplama</a>."
        "<div style='margin-top:12px;padding:15px 18px;background:linear-gradient(90deg,#14532d,#0c4a6e);border:1px solid #22c55e;border-radius:10px;color:#f0fdf4;line-height:1.65'>"
        "<p style='margin:0 0 9px'><b style='color:#fff;font-size:15px'>📄 Tamamen Kişiye Özel KPSS Raporu ister misin?</b> Sadece <b style='color:#fde047'>999 TL</b>'ye Uzman KPSS Rehberi + Detaylı Veri Analiziyle Kişiye Özel KPSS Tercih Raporu</p>"
        "<p style='margin:0 0 9px'>🎯 <b style='color:#fff'>Boşta kalma, doğru kadroya yerleş.</b> Tek bir yanlış tercih sıralaması atamanı kaçırabilir. Kişiye özel taban trendi, doluluk ve şans analiziyle yanlış sıralama riskini en aza indir. <a href='/kpss-tercih-raporu.html' style='color:#fde047;font-weight:700;text-decoration:underline'>Örnek raporu gör →</a></p>"
        "<p style='margin:0 0 9px'>⏳ Kendi sınav puanın üzerinden, senin kişisel özelliklerine ve önceliklerine göre, konusunda uzman bir KPSS rehberi eşliğinde senin için sıralı, kişiye özel tercih listeni hazırlayalım. <a href='/kpss-tercih-raporu.html' style='color:#fde047;font-weight:700;text-decoration:underline'>Detaylar ve örnek rapor →</a></p>"
        "<p style='margin:0'>👨‍🏫 Tercihte yalnız kalma. KPSS uzmanı + SınavVeri verisi = sana özel, sıralı, gerekçeli tercih raporu; garanti odaklı strateji. <a href='/kpss-tercih-raporu.html' style='color:#fde047;font-weight:700;text-decoration:underline'>Örnek raporu incele →</a></p></div>",
        "ÖSYM 2025 KPSS resmî yerleştirme verisi (2025/1–2025/5).", "KPSS Puanın", "örn. 85,40",
        hist=[{"yil": 2025, "t": 6}, {"yil": 2024, "t": 8}],
        kilavuz_url="https://www.osym.gov.tr/SinavGrubu/Menu/338")


def page_lgs_robot(lgs):
    if not lgs or not (ROOT / "veri" / "liseler.json").exists():
        return None
    return puan_robot_page(
        "lgs-tercih-robotu.html", "2026 LGS Tercih Robotu — Puanına Göre Lise Bul | SınavVeri",
        "2026 LGS tercih robotu: LGS puanını gir, 2025 MEB yerleştirme verisine göre yerleşebileceğin liseleri il ve ilçeye göre gör. Ücretsiz.",
        "2026 LGS Tercih Robotu", "LGS puanını gir, yerleşebileceğin liseleri gör · 2025 MEB yerleştirmesine göre",
        "/veri/liseler.json", 2, None,
        [(0, "İl"), (1, "İlçe"), (3, "Tür"), (4, "Kontenjan"), (6, "Yüzdelik Dilim")], 5,
        [(0, "İl"), (1, "İlçe"), (3, "Tür"), (10, "Yabancı Dil")],
        "liseye", 15, 4,
        "LGS puanını girin ve ilini seçin; o puanla yerleşebileceğin (taban ≤ puanın) liseleri en yüksek tabandan başlayarak listeler. "
        "Lise türüne (Fen, Sosyal Bilimler, Anadolu…) göre de filtreleyebilirsin. LGS hesaplama için <a href='/lgs-puan-hesaplama.html'>LGS puan hesaplama</a>.",
        f"MEB {LGS_YIL} LGS yerleştirme verisi.", "LGS Puanın", "örn. 420,5",
        hist=[{"yil": 2025, "t": 5}, {"yil": 2024, "t": 7}, {"yil": 2023, "t": 8}],
        maps={3: LISE_TUR_NAME})


def _bdil_py(s):
    s = s or ""
    i = s.find(" (")
    return s[:i] if i > 0 else s


def _row_attrs(r):
    """Detay tablosu satırına filtre data-attribute'ları (il/tür/dil/üniversite)."""
    def q(s):
        return (s or "").replace('"', "&quot;")
    return (f' data-il="{q(r.get("il"))}" data-tur="{q(TUR_FULL.get(r.get("t"), "—"))}"'
            f' data-dil="{q(_bdil_py(r.get("dil")))}" data-uni="{q(r.get("u"))}"')


def _pdet_btn(r):
    """Program detayı 'ℹ️' butonu: akademik kadro / akreditasyon / süre / ücret / koşul kodları
    data-attribute olarak; istemci kosul_map ile açıklamayı çözer. Veri yoksa boş döner."""
    kadro = r.get("kadro") or []
    kosul = r.get("kosul") or ""
    akr = r.get("akr") or ""
    sure = r.get("sure")
    ucret = r.get("ucret")
    demo = DEMOGRAFI.get(str(r.get("k"))) if r.get("k") is not None else None
    hist = r.get("hist") or []
    has_hist = (r.get("tp") or r.get("sira")) or any((h[1] or h[2]) for h in hist)
    if not (kosul or any(kadro) or akr or sure or demo or has_hist):
        return ""
    kd = ",".join(str(x if x else 0) for x in (kadro + [0, 0, 0, 0, 0])[:5])
    attrs = (f' data-kosul="{kosul}" data-kadro="{kd}"'
             + (f' data-akr="{akr}"' if akr else "")
             + (f' data-sure="{sure}"' if sure else "")
             + (f' data-ucret="{ucret}"' if ucret else ""))
    if has_hist:
        # yıl:taban:sıra:yerleşen (2025 cari + hist 2024/2023/2022)
        def _v(x):
            return "" if x in (None, "") else (f"{x:.3f}".rstrip("0").rstrip(".") if isinstance(x, float) else str(x))
        cells = [f"2025:{_v(r.get('tp'))}:{_v(r.get('sira'))}:{_v(r.get('yer'))}"]
        for h in hist:
            cells.append(f"{h[0]}:{_v(h[1])}:{_v(h[2])}:{_v(h[3])}")
        attrs += f' data-hist="{";".join(cells)}"'
    if demo:
        # y|kız|erkek|liseli|mezun|üni-iken|üni-mezunu  (yerleşen profili, YÖK Atlas arşivi)
        dv = "|".join(str(demo.get(x, 0)) for x in ("y", "k", "e", "ls", "mz", "ub", "um"))
        attrs += f' data-demo="{dv}"'
    return f'<button type="button" class="pdet" title="Program detayı"{attrs}>ℹ️</button>'


# Detay (bölüm/üniversite) statik tablolarına dil filtresi + karşılaştırma katmanı
_DLBL = 'style="font-size:12px;color:var(--fg-faded);font-weight:700;display:block;margin-bottom:3px"'
DETAIL_BAR = f"""
<div class="calc-card" style="margin-bottom:14px;padding:13px 16px">
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px">
    <span id="dIlW"><label {_DLBL}>İl</label><select id="dIl" class="btn btn-ghost" style="text-align:left;width:100%"><option value="">Tüm iller</option></select></span>
    <span id="dTurW"><label {_DLBL}>Tür</label><select id="dTur" class="btn btn-ghost" style="text-align:left;width:100%"><option value="">Tüm türler</option></select></span>
    <span id="dDilW"><label {_DLBL}>Öğrenim dili</label><select id="dDil" class="btn btn-ghost" style="text-align:left;width:100%"><option value="">Tüm diller</option></select></span>
    <span id="dUniW"><label {_DLBL}>Üniversite</label><select id="dUni" class="btn btn-ghost" style="text-align:left;width:100%"><option value="">Tüm üniversiteler</option></select></span>
  </div>
  <div class="filter-chips" id="dChips" style="display:none;margin-top:8px"></div>
  <div id="dStatus" style="margin-top:8px;font-size:12px;color:var(--fg-faded)"></div>
</div>"""

# TrVeri STANDART sayfalama montaj noktası (rule 3.17) — pager.js navigasyonu buraya çizer.
# data-table-wrap DIŞINDA olmalı (wrap overflow-x:auto → nav yatay kaydırmaya takılmasın).
DETAIL_PAGER = """
<nav id="dPager"></nav>"""

DETAIL_CMP = """
<div class="fav-panel" id="dCmpPanel"></div>
<div class="cmp-bar" id="dCmpBar"><button type="button" class="fav-toggle" id="dCmpBtn">Karşılaştır (0)</button><button type="button" class="fchip-clear" id="dCmpClear" style="margin-left:8px">Seçimi temizle</button></div>"""

DETAIL_TOOLS_JS = r"""<script nonce="__NONCE__">
(function(){
  var SV=window.SV||{};
  // Künye: harita/video tab toggle (tıkla aç-kapa) + adres kopyala (delegasyon)
  document.addEventListener('click',function(e){
    var t=e.target;
    if(t.classList&&t.classList.contains('uk-copy')){var a=t.getAttribute('data-adres')||'';try{navigator.clipboard.writeText(a);var o=t.textContent;t.textContent='✓ Kopyalandı';setTimeout(function(){t.textContent=o;},1500);}catch(e2){}return;}
    if(t.classList&&t.classList.contains('uk-tab')){var i=t.getAttribute('data-tab');var pan=document.querySelector('.uk-pan[data-pan="'+i+'"]');
      if(pan){var ifr=pan.querySelector('iframe');
        if(pan.hasAttribute('hidden')){pan.removeAttribute('hidden');t.classList.add('on');if(ifr&&!ifr.getAttribute('src'))ifr.setAttribute('src',ifr.getAttribute('data-src')||'');}
        else{pan.setAttribute('hidden','');t.classList.remove('on');if(ifr)ifr.setAttribute('src','');}}return;}
  });
  var tbl=document.querySelector('table.detail-table'); if(!tbl)return;
  var tb=tbl.querySelector('tbody'); if(!tb)return;
  var rows=Array.prototype.slice.call(tb.querySelectorAll(':scope>tr')).filter(function(r){return !r.classList.contains('pdet-row');});
  var thEls=Array.prototype.slice.call(tbl.querySelectorAll('thead th'));
  // Başlık metni: table.js'in eklediği ⓘ/↕ düğmeleri ve sıralama oku hariç (karşılaştırma etiketleri için)
  function thLabel(h){var c=h.cloneNode(true);
    Array.prototype.forEach.call(c.querySelectorAll('.tv-th__i,.tv-th__ind,.s-arrow'),function(x){x.parentNode.removeChild(x);});
    return c.textContent.trim();}
  var ths=thEls.map(thLabel);
  var ncol=ths.length;
  var DIMS=[['dIl','data-il','İl'],['dTur','data-tur','Tür'],['dDil','data-dil','Dil'],['dUni','data-uni','Üni']];
  function el(i){return document.getElementById(i);}
  function num(s){s=(s||'').replace(/[^0-9,.\-]/g,'').replace(/\./g,'').replace(',','.');return s===''||s==='-'?NaN:parseFloat(s);}
  function esc(s){return (''+(s==null?'':s)).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
  function nf(n){return Number(n).toLocaleString('tr-TR');}
  var PH={dIl:'Tüm iller',dTur:'Tüm türler',dDil:'Tüm diller',dUni:'Tüm üniversiteler'};

  // ── Program detayı (ℹ️) satırları ÖNCEDEN ve GİZLİ oluşturulur ────────────────────────────
  // Neden: pager.js MutationObserver ile tbody childList'i dinler. Detay satırı tıklama anında
  // EKLENSEYDİ observer tetiklenir → sayfa 1'e sıçrar + açılan detay kaybolurdu. Boş satırlar
  // baştan var olduğu için tıklama yalnız style.display + innerHTML değiştirir (childList sabit).
  rows.forEach(function(r){
    if(!r.querySelector('.pdet'))return;
    var d=document.createElement('tr'); d.className='pdet-row'; d.style.display='none';
    var td=document.createElement('td'); td.colSpan=ncol; d.appendChild(td);
    r.parentNode.insertBefore(d,r.nextSibling);
    r.__pdet=d;
  });
  function closeAllPdet(){rows.forEach(function(r){var d=r.__pdet;if(d){d.style.display='none';d.firstChild.innerHTML='';}});}

  // tek değerli boyutu (ör. üni sayfasında il/tür/üni) gizle
  var dimActive={};
  DIMS.forEach(function(dm){var c={};rows.forEach(function(r){var v=r.getAttribute(dm[1]);if(v)c[v]=1;});dimActive[dm[0]]=Object.keys(c).length>=2;var w=el(dm[0]+'W');if(w&&!dimActive[dm[0]])w.style.display='none';});
  function rowPass(r,exceptId){for(var i=0;i<DIMS.length;i++){var dm=DIMS[i];if(dm[0]===exceptId)continue;var s=el(dm[0]);if(s&&s.value&&r.getAttribute(dm[1])!==s.value)return false;}return true;}
  function dimPass(r){return rowPass(r,null);}
  function repopD(){
    DIMS.forEach(function(dm){if(!dimActive[dm[0]])return;var sel=el(dm[0]);if(!sel)return;var cur=sel.value;
      var cnt={};rows.forEach(function(r){if(!rowPass(r,dm[0]))return;var v=r.getAttribute(dm[1]);if(v)cnt[v]=(cnt[v]||0)+1;});
      var ks=Object.keys(cnt).sort(function(a,b){return cnt[b]-cnt[a]||a.localeCompare(b,'tr');});
      sel.innerHTML='<option value="">'+PH[dm[0]]+'</option>';var hasCur=false;
      ks.forEach(function(k){var o=document.createElement('option');o.value=k;o.textContent=k+' ('+cnt[k]+')';if(k===cur){o.selected=true;hasCur=true;}sel.appendChild(o);});
      if(cur&&!hasCur){var o2=document.createElement('option');o2.value=cur;o2.textContent=cur+' (0)';o2.selected=true;sel.appendChild(o2);}
    });
  }
  // TrVeri STANDART sayfalama (rule 3.17): 25/sayfa · numaralı nav + İlk/Son + "Sayfa __ Git" + kayıt/sayfa.
  // ≤100 kayıtta pager kendini gizler (kural). JS yoksa tüm satırlar görünür (progressive enhancement).
  var pgr = window.TVPager ? window.TVPager.attach({
    grid: tbl, per: 25, mount: el('dPager'),
    match: function(r){ return !r.classList.contains('pdet-row') && dimPass(r); }
  }) : null;
  function drawStatus(){
    var n=0; rows.forEach(function(r){ if(dimPass(r))n++; });
    var st=el('dStatus'); if(st)st.textContent=n.toLocaleString('tr-TR')+' / '+rows.length.toLocaleString('tr-TR')+' program';
  }
  function apply(){
    closeAllPdet();
    if(pgr)pgr.reset();
    else rows.forEach(function(r){r.style.display=dimPass(r)?'':'none';});
    drawStatus();
    if(SV.chips){var items=DIMS.filter(function(dm){var s=el(dm[0]);return s&&s.value;}).map(function(dm){return {key:dm[0],label:dm[2]+': '+el(dm[0]).value};});
      SV.chips('dChips',items,function(key){if(key==='__all__'){DIMS.forEach(function(dm){var s=el(dm[0]);if(s)s.value='';});}else{var s=el(key);if(s)s.value='';}repopD();apply();});}
  }
  DIMS.forEach(function(dm){var sel=el(dm[0]);if(sel)sel.addEventListener('change',function(){repopD();apply();});});
  repopD();
  apply();
  var sortI=null,sortD=1;
  thEls.forEach(function(th,i){
    if(th.hasAttribute('data-nosort'))return;
    th.style.cursor='pointer';th.title='Sıralamak için tıklayın';
    th.addEventListener('click',function(){
      sortD=(sortI===i)?-sortD:1;sortI=i;
      thEls.forEach(function(o){o.removeAttribute('aria-sort');var a=o.querySelector('.s-arrow');if(a)a.remove();});
      th.setAttribute('aria-sort',sortD>0?'ascending':'descending');
      var ar=document.createElement('span');ar.className='s-arrow';ar.textContent=sortD>0?' ▲':' ▼';th.appendChild(ar);
      closeAllPdet();
      rows.sort(function(a,b){var x=a.children[i],y=b.children[i];if(!x||!y)return 0;
        var xt=x.textContent.trim(),yt=y.textContent.trim(),xn=num(xt),yn=num(yt);
        if(!isNaN(xn)&&!isNaN(yn))return (xn-yn)*sortD;
        if(isNaN(xn)&&isNaN(yn))return xt.localeCompare(yt,'tr')*sortD;
        return isNaN(xn)?1:-1;});
      // detay satırı ana satırıyla BİRLİKTE taşınır (eşleşme bozulmasın)
      var frag=document.createDocumentFragment();
      rows.forEach(function(r){frag.appendChild(r);if(r.__pdet)frag.appendChild(r.__pdet);});
      tb.appendChild(frag);
      if(pgr)pgr.reset(); else rows.forEach(function(r){r.style.display=dimPass(r)?'':'none';});
      drawStatus();
    });
  });
  var order=[];
  function refreshBar(){var bar=document.getElementById('dCmpBar');if(bar)bar.classList.toggle('show',order.length>0);var b=document.getElementById('dCmpBtn');if(b)b.textContent='Karşılaştır ('+order.length+')';}
  function buildPanel(){
    var p=document.getElementById('dCmpPanel');if(!p)return;
    if(!order.length){p.classList.remove('open');p.innerHTML='';return;}
    var h='<div class="cmp-grid">';
    order.forEach(function(tr){var c=tr.children;
      h+='<div class="cmp-col"><h4>'+esc(c[0]?c[0].textContent.trim():'')+'</h4><dl>';
      for(var i=1;i<ncol-1;i++){h+='<dt>'+esc(ths[i])+'</dt><dd>'+esc(c[i]?c[i].textContent.trim():'—')+'</dd>';}
      h+='</dl></div>';});
    p.innerHTML=h+'</div>';p.classList.add('open');
    try{p.scrollIntoView({behavior:'smooth',block:'center'});}catch(e){}
  }
  // Satır ELEMENTİ ile eşle (indeks DEĞİL): sıralama/sayfalama sonrası indeks kayması olmaz.
  tb.addEventListener('change',function(e){var cb=e.target;if(!cb.classList||!cb.classList.contains('dcmp'))return;
    var tr=cb.closest('tr');
    if(cb.checked){if(order.length>=3){cb.checked=false;return;}if(order.indexOf(tr)<0)order.push(tr);}
    else{order=order.filter(function(x){return x!==tr;});}
    refreshBar();if(document.getElementById('dCmpPanel').classList.contains('open'))buildPanel();});
  var b1=document.getElementById('dCmpBtn');if(b1)b1.addEventListener('click',function(){var p=document.getElementById('dCmpPanel');if(p.classList.contains('open'))p.classList.remove('open');else buildPanel();});
  var b2=document.getElementById('dCmpClear');if(b2)b2.addEventListener('click',function(){order=[];document.getElementById('dCmpPanel').classList.remove('open');refreshBar();tb.querySelectorAll('.dcmp').forEach(function(c){c.checked=false;});});
  // Program detayı (ℹ️): akademik kadro / akreditasyon / süre / ücret / koşullar
  var KOSUL=null, KLAB=['Profesör','Doçent','Dr. Öğr. Üyesi','Araştırma Gör.','Öğretim Gör.'];
  if(tb.querySelector('.pdet')){
    fetch('/veri/kosul_map.json').then(function(r){return r.json();}).then(function(j){KOSUL=j;}).catch(function(){KOSUL={};});
    tb.addEventListener('click',function(e){
      var btn=e.target; if(!btn.classList||!btn.classList.contains('pdet'))return;
      var tr=btn.closest('tr');
      var drow=tr.__pdet; if(!drow)return;
      if(drow.style.display!=='none'){ drow.style.display='none'; drow.firstChild.innerHTML=''; return; }
      var kadro=(btn.getAttribute('data-kadro')||'').split(',').map(function(x){return parseInt(x,10)||0;});
      var parts=[];
      var hraw=(btn.getAttribute('data-hist')||'').split(';').filter(Boolean);
      if(hraw.length){
        function pf(v){return v===''||v==null?'—':Number(v).toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2});}
        function nf2(v){return v===''||v==null?'—':Number(v).toLocaleString('tr-TR');}
        var hr=hraw.map(function(c){var p=c.split(':');
          return '<tr><td><b>'+esc(p[0])+'</b></td><td>'+pf(p[1])+'</td><td>'+nf2(p[2])+'</td><td>'+nf2(p[3])+'</td></tr>';}).join('');
        parts.push('<div><b>Yıllara göre (taban / başarı sırası / yerleşen):</b>'
          +'<table class="pdet-hist"><thead><tr><th data-tip="Yerleştirme yılı.">Yıl</th><th data-tip="O yıl programa en son yerleşen adayın puanı.">Taban</th><th data-tip="O yıl en son yerleşen adayın başarı sırası.">Başarı Sırası</th><th data-tip="O yıl programa yerleşen toplam öğrenci sayısı.">Yerleşen</th></tr></thead><tbody>'+hr+'</tbody></table></div>');
      }
      // Yerleşen profili (demografi) — yıl tablosunun hemen altında
      var dm=(btn.getAttribute('data-demo')||'').split('|');
      if(dm.length===7){
        var dy=dm[0],kz=+dm[1]||0,er=+dm[2]||0,ls=+dm[3]||0,mz=+dm[4]||0,ub=+dm[5]||0,um=+dm[6]||0;
        var ct=kz+er;
        if(ct>0){
          var kzp=Math.round(100*kz/ct),erp=100-kzp;
          parts.push('<div style="margin-top:8px"><b>Yerleşen profili ('+esc(dy)+'):</b>'
            +'<div style="margin:5px 0 2px;font-size:12px">Cinsiyet — Kız %'+kzp+' · Erkek %'+erp+'</div>'
            +'<div style="display:flex;height:14px;border-radius:7px;overflow:hidden;font-size:9px;line-height:14px;color:#fff">'
            +'<div style="width:'+kzp+'%;background:#d6336c;text-align:center">'+kz+'</div>'
            +'<div style="width:'+erp+'%;background:#1c7ed6;text-align:center">'+er+'</div></div>');
          var ot=ls+mz+ub+um;
          if(ot>0){
            var seg=[['Lise son sınıf',ls,'#2f9e44'],['Önceki yıl mezunu',mz,'#f08c00'],['Üniv. öğrencisi iken',ub,'#7048e8'],['Üniv. mezunu',um,'#e8590c']].filter(function(s){return s[1]>0;});
            parts.push('<div style="margin-top:6px;font-size:12px">Öğrenim durumu:</div>'
              +'<div style="display:flex;height:14px;border-radius:7px;overflow:hidden;font-size:9px;line-height:14px;color:#fff">'
              +seg.map(function(s){return '<div style="width:'+Math.round(100*s[1]/ot)+'%;background:'+s[2]+'" title="'+s[0]+': '+s[1]+'"></div>';}).join('')+'</div>'
              +'<div style="font-size:11px;color:var(--fg-faded);margin-top:3px">'+seg.map(function(s){return esc(s[0])+' %'+Math.round(100*s[1]/ot);}).join(' · ')+'</div>');
          }
          parts.push('<div style="font-size:10px;color:var(--fg-faded);margin-top:4px">Cinsiyet ve öğrenim durumu dağılımını YÖK Atlas en son <b>2023</b> yerleşmeleri için yayınladı; sonraki yıllarda bu istatistik yayından kaldırıldı. Diğer tüm veriler (taban, sıra, kontenjan, yerleşen sayısı, koşullar, kadro, ücret) <b>2025</b>’tir.</div></div>');
        }
      }
      var kp=[]; kadro.forEach(function(v,i){ if(v>0)kp.push(KLAB[i]+': '+v); });
      if(kp.length)parts.push('<div><b>Akademik kadro:</b> '+kp.join(' · ')+'</div>');
      var akr=btn.getAttribute('data-akr'); if(akr)parts.push('<div><b>Akreditasyon:</b> '+esc(akr)+'</div>');
      var sure=btn.getAttribute('data-sure'); if(sure)parts.push('<div><b>Öğrenim süresi:</b> '+esc(sure)+' yıl</div>');
      var uc=btn.getAttribute('data-ucret'); if(uc)parts.push('<div><b>Ücret:</b> '+nf(uc)+' ₺/yıl</div>');
      var ks=(btn.getAttribute('data-kosul')||'').split(',').filter(Boolean);
      if(ks.length&&KOSUL){ var li=ks.map(function(c){return KOSUL[c]?'<li>'+esc(KOSUL[c])+'</li>':'';}).filter(Boolean).join('');
        if(li)parts.push('<div style="margin-top:6px"><b>Özel koşullar:</b><ul style="margin:4px 0 0 18px">'+li+'</ul></div>'); }
      if(!parts.length)parts.push('<div style="color:var(--fg-faded)">Ek detay bulunmuyor.</div>');
      drow.firstChild.innerHTML='<div class="pdet-box">'+parts.join('')+'</div>';
      drow.style.display='';
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
            rows += (f'<tr{_row_attrs(r)}><td>' + uni_logo_html(r.get("u"), size=24, cls="uni-logo-sm") + "<strong>" + (r.get("u") or "") + "</strong> " + _pdet_btn(r) + "</td>"
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
        # Veri-dayalı FAQ (uydurma yok — yalnızca YÖK Atlas {YKS_YIL} verisinden türetilir)
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
<div class="page-title"><h1>{g} Taban Puanları {YKS_YIL}</h1><span class="sub">YÖK Atlas {YKS_YIL} · {len(recs)} program · Puan türü: {', '.join(pts)}</span></div>
<div class="info-box">{summary} Aşağıdaki tablo başarı sırasına göre sıralıdır (en düşük sıra = en yüksek puan).</div>
{chart}
{DETAIL_BAR}
<div class="data-table-wrap">
<table class="data-table detail-table" data-live="1">
<thead><tr><th data-tip="Programın açıldığı üniversite. ℹ️ düğmesi program detayını (kadro, koşul, ücret) açar." data-type="text">Üniversite</th><th data-tip="YÖK Atlas'taki tam program adı; öğretim türü, öğrenim dili ve burs bilgisini içerir." data-type="text">Program</th><th data-tip="Programın bulunduğu il." data-type="text">İl</th><th data-tip="Üniversite türü: Devlet, Vakıf, KKTC veya özel kontenjan türü." data-type="text">Tür</th><th data-tip="2025 genel kontenjanı: programa alınacak öğrenci sayısı." data-type="num">Kont.</th><th data-tip="Doluluk = yerleşen ÷ kontenjan. %100 kontenjanın tamamen dolduğunu gösterir." data-type="num">Doluluk</th><th data-tip="2025'te programa en son yerleşen adayın YKS yerleştirme puanı (taban puan)." data-type="num">Taban 2025</th><th data-tip="2024 yılı taban puanı; yıllar arası değişimi görmek için." data-type="num">Taban 2024</th><th data-tip="2023 yılı taban puanı; yıllar arası değişimi görmek için." data-type="num">Taban 2023</th><th data-tip="2025'te en son yerleşen adayın başarı sırası. Küçük sıra = daha yüksek başarı." data-type="num">Sıra 2025</th><th data-nosort data-tip="En fazla 3 programı işaretleyip yan yana karşılaştırın.">Kıyas</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</div>
{DETAIL_PAGER}
{DETAIL_CMP}
{DETAIL_TOOLS_JS}
<div class="notice"><b>Kaynak:</b> YÖK Atlas {YKS_KILAVUZ_YIL} Tercih Kılavuzu (geçmiş: {YKS_HIST[0]}/{YKS_HIST[1]}). Boş (—) değerler o yıl yerleşen/veri olmadığını gösterir.
Doluluk = yerleşen ÷ kontenjan. Daha fazlası: <a href="/taban-puanlari.html">tüm taban puanları</a> · <a href="/tercih-robotu.html">tercih robotu</a> · <a href="/doluluk.html">doluluk analizi</a>.</div>
{faq_html}
"""
        html = base(f"bolum/{s}.html", f"{g} Taban Puanları {YKS_YIL} ve Başarı Sıralaması | SınavVeri",
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
            rows += (f'<tr{_row_attrs(r)}><td><strong>' + (r.get("b") or "") + "</strong> " + _pdet_btn(r) + "</td>"
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
<div class="page-title uni-title">{uni_logo_html(u, size=48, cls="uni-logo-h1")}<div><h1>{u} Taban Puanları {YKS_YIL}</h1><span class="sub">{il} · {tur} · {len(recs)} program · YÖK Atlas {YKS_YIL}</span></div></div>
{uni_kunye_html(u, recs)}
{SHARE_BAR}
{DETAIL_BAR}
<div class="data-table-wrap">
<table class="data-table detail-table" data-live="1">
<thead><tr><th data-tip="Bu üniversitedeki programın YÖK Atlas'taki tam adı; öğretim türü, dil ve burs bilgisini içerir. ℹ️ program detayını açar." data-type="text">Program</th><th data-tip="Programın bağlı olduğu genel bölüm grubu (ör. Bilgisayar Mühendisliği)." data-type="text">Bölüm Grubu</th><th data-tip="Programın tercih edildiği YKS puan türü: Sayısal, Eşit Ağırlık, Sözel, Dil veya TYT." data-type="text">Puan Türü</th><th data-tip="2025 genel kontenjanı: programa alınacak öğrenci sayısı." data-type="num">Kont.</th><th data-tip="Doluluk = yerleşen ÷ kontenjan. %100 kontenjanın tamamen dolduğunu gösterir." data-type="num">Doluluk</th><th data-tip="2025'te programa en son yerleşen adayın YKS yerleştirme puanı (taban puan)." data-type="num">Taban 2025</th><th data-tip="2024 yılı taban puanı; yıllar arası değişimi görmek için." data-type="num">Taban 2024</th><th data-tip="2025'te en son yerleşen adayın başarı sırası. Küçük sıra = daha yüksek başarı." data-type="num">Başarı Sırası</th><th data-nosort data-tip="En fazla 3 programı işaretleyip yan yana karşılaştırın.">Kıyas</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</div>
{DETAIL_PAGER}
{DETAIL_CMP}
{DETAIL_TOOLS_JS}
<div class="notice"><b>Kaynak:</b> YÖK Atlas {YKS_YIL} (geçmiş: {YKS_HIST[0]}). Doluluk = yerleşen ÷ kontenjan. Başarı sırasına göre sıralı.
<a href="/taban-puanlari.html">Tüm taban puanları</a> · <a href="/tercih-robotu.html">tercih robotu</a> · <a href="/doluluk.html">doluluk analizi</a>.</div>
{uni_yorum_html(u)}
"""
        og = gen_uni_og(s, u, uni_info(u), recs)
        html = base(f"universite/{s}.html", f"{u} Taban Puanları {YKS_YIL} — Tüm Bölümler | SınavVeri",
                    f"{u} 2025 taban puanları ve başarı sıralamaları. {len(recs)} programın taban puanı, kontenjan ve sıralaması YÖK Atlas verisiyle.",
                    body, og_image=og, share=True)
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
<div class="page-title"><h1>Bölümlere Göre Taban Puanları</h1><span class="sub">{len(items)} bölüm grubu · YÖK Atlas {YKS_YIL}</span></div>
<input id="bSearch" type="text" placeholder="Bölüm ara… (örn. tıp, hukuk, bilgisayar)" style="width:100%;max-width:480px;padding:10px 12px;border:1px solid var(--border);border-radius:9px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:14px;margin-bottom:18px">
<div class="tool-row" id="bList">
{cards}
</div>
<nav id="bPagerNav"></nav>
<script nonce="__NONCE__">
(function(){{
  // Arama + TrVeri STANDART sayfalama (rule 3.17) — kart ızgarası: 24 kart/sayfa.
  var q=document.getElementById('bSearch'),list=document.getElementById('bList'),term='';
  function match(a){{return !term||a.textContent.toLocaleLowerCase('tr').indexOf(term)>=0;}}
  var p=window.TVPager?window.TVPager.attach({{grid:list,per:24,mount:document.getElementById('bPagerNav'),match:match}}):null;
  q.addEventListener('input',function(){{
    term=this.value.toLocaleLowerCase('tr').trim();
    if(p)p.reset();
    else Array.prototype.forEach.call(list.children,function(a){{a.style.display=match(a)?'':'none';}});
  }});
}})();
</script>
"""
    return base("bolumler.html", f"Bölümlere Göre Üniversite Taban Puanları {YKS_YIL} | SınavVeri",
                "Tüm üniversite bölümlerinin 2025 taban puanları. Tıp, hukuk, mühendislik, psikoloji ve 600+ bölüm grubu YÖK Atlas verisiyle.",
                body)


# ── Çoklu-seçim filtre bileşeni (ÇOK ALANLI) ────────────────────────────────────
# CSS site tema değişkenlerini devralır (açık/koyu uyumlu), mobilde tam genişliğe düşer.
MULTI_FILTER_CSS = """<style>
.msf{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
.msf>input[type=text]{flex:1 1 240px;min-width:0;padding:10px 12px;border:1px solid var(--border);border-radius:9px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:14px}
.ms{position:relative;flex:0 0 auto}
.ms-btn{display:flex;align-items:center;gap:8px;padding:10px 14px;border:1px solid var(--border);border-radius:9px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:14px;font-weight:600;cursor:pointer;white-space:nowrap}
.ms-btn:hover,.ms-btn[aria-expanded=true]{border-color:var(--accent)}
.ms-btn.on{border-color:var(--accent);font-weight:700}
.ms-caret{font-size:11px;opacity:.7}
/* left:0 — panel düğmenin SOLUNA hizalı; sağa taşan durumda JS `right:0`a çevirir. */
.ms-panel{position:absolute;z-index:40;top:calc(100% + 6px);left:0;width:290px;max-width:88vw;background:var(--bg-card);border:1px solid var(--border);border-radius:11px;box-shadow:0 10px 28px rgba(0,0,0,.22);padding:10px}
.ms-panel.right{left:auto;right:0}
.ms-panel[hidden]{display:none}
.ms-search{width:100%;padding:8px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:13px}
.ms-actions{display:flex;gap:8px;margin:8px 0 6px}
.ms-actions button{flex:1;padding:6px 8px;border:1px solid var(--border);border-radius:7px;background:transparent;color:var(--fg-faded);font-family:inherit;font-size:12px;font-weight:700;cursor:pointer}
.ms-actions button:hover{color:var(--accent);border-color:var(--accent)}
.ms-list{max-height:270px;overflow:auto;display:flex;flex-direction:column;gap:1px}
.ms-list label{display:flex;align-items:center;gap:8px;padding:6px 7px;border-radius:7px;font-size:13.5px;cursor:pointer}
.ms-list label:hover{background:var(--bg-card-alt)}
.ms-list label.zero{opacity:.38}   /* diğer filtrelerle birlikte 0 sonuç verir → çıkmaz tıklama uyarısı */
.ms-list input{accent-color:var(--accent);width:15px;height:15px;flex:0 0 auto}
.ms-n{margin-left:auto;font-size:11.5px;color:var(--fg-faded)}
.ms-chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px}
.ms-chips:empty{margin-bottom:0}
.ms-chip{display:inline-flex;align-items:center;gap:6px;padding:4px 8px 4px 10px;border:1px solid var(--accent);border-radius:999px;background:var(--bg-card-alt);color:var(--fg);font-size:12.5px;font-weight:600}
.ms-chip button{border:0;background:transparent;color:var(--fg-faded);font-size:15px;line-height:1;cursor:pointer;padding:0 2px}
.ms-chip button:hover{color:var(--accent)}
.ms-empty{padding:18px 4px;color:var(--fg-faded);font-size:14px}
/* İkincil filtreler (bölge/öğrenci/burs/…): varsayılan gizli, "Daha fazla filtre" ile açılır —
   9 dropdown'u aynı anda göstermek özellikle mobilde arama kutusunu sayfanın dışına iter. */
.msf-more{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:10px}
.msf-more[hidden]{display:none}
.msf-toggle{display:inline-flex;align-items:center;gap:6px;padding:9px 14px;border:1px dashed var(--border);border-radius:9px;background:transparent;color:var(--fg-faded);font-family:inherit;font-size:13.5px;font-weight:700;cursor:pointer;margin-bottom:10px}
.msf-toggle:hover{color:var(--accent);border-color:var(--accent)}
.msf-toggle.on{color:var(--accent);border-color:var(--accent);border-style:solid}
@media(max-width:640px){.msf>input[type=text]{flex:1 1 100%;order:9}.ms{flex:1 1 calc(50% - 5px)}.ms-btn{width:100%;justify-content:space-between}.ms-panel{width:100%;left:0;right:auto}.msf-more{flex-direction:column;align-items:stretch}.msf-more .ms{flex:1 1 100%}}
@media(max-width:400px){.ms{flex:1 1 100%}}
</style>"""

# JS ayrı sabitte: f-string içinde her süslü parantezi kaçırmak okunmaz hale getiriyor.
# ÇOK ALANLI: `.msf .ms[data-field]` bulunan her filtre otomatik devreye girer; kartlarda
# eşleşen `data-<field>` özniteliği aranır. Yeni filtre eklemek = tek satır HTML (JS değişmez).
MULTI_FILTER_JS = r"""<script nonce="__NONCE__">
(function(){
  var q=document.getElementById('uSearch'), list=document.getElementById('uList'),
      chips=document.getElementById('fChips'), empty=document.getElementById('uEmpty'), term='';
  // NOT ".msf .ms" — ikincil filtreler ("Daha fazla filtre" altında) .msf'in DIŞINDA,
  // kardeş bir .msf-more kutusunda yaşıyor; ".msf" öneki onları görmezden gelirdi (ölçüldü:
  // seçim işaretlense de hiçbir kart filtrelenmiyordu — groups dizisine hiç girmiyorlardı).
  var groups=Array.prototype.map.call(document.querySelectorAll('.ms[data-field]'),function(g){
    return {el:g, field:g.getAttribute('data-field'), allLbl:g.getAttribute('data-all'),
            multi:g.getAttribute('data-multi')==='1',
            btn:g.querySelector('.ms-btn'), panel:g.querySelector('.ms-panel'),
            lbl:g.querySelector('.ms-lbl'), search:g.querySelector('.ms-search'), sel:new Set()};
  });
  // Çoklu-değerli alanlar (burs/dil/akreditasyon): bir üniversitede birden çok program
  // farklı değer taşıyabilir → data-attr'da "|" ile ayrılmış liste. Eşleşme = KESİŞİM VAR MI.
  function cardVals(a,g){
    var raw=a.getAttribute('data-'+g.field)||'';
    return g.multi ? raw.split('|').filter(Boolean) : (raw?[raw]:[]);
  }
  function groupMatch(a,g){
    if(!g.sel.size) return true;
    var vals=cardVals(a,g);
    for(var i=0;i<vals.length;i++){ if(g.sel.has(vals[i])) return true; }
    return false;
  }
  function match(a){
    if(term && a.textContent.toLocaleLowerCase('tr').indexOf(term)<0) return false;
    for(var i=0;i<groups.length;i++){ if(!groupMatch(a,groups[i])) return false; }
    return true;
  }
  var SV=window.SV||{};
  // Filtre durumu URL'e yazılır ("şu filtreyle linki paylaş" — robotlardaki SV.qsSet ile aynı
  // desen). Çoklu seçim tek parametrede virgülle: ?il=İstanbul,Ankara&tur=Vakıf&q=teknik
  function syncQS(){
    if(!SV.qsSet) return;
    var o={}; if(term) o.q=term;
    groups.forEach(function(g){ if(g.sel.size) o[g.field]=Array.from(g.sel).join(','); });
    SV.qsSet(o);
  }
  function restoreFromQS(){
    if(!SV.qsGet) return;
    var qs=SV.qsGet();
    if(qs.q){ term=qs.q.toLocaleLowerCase('tr').trim(); q.value=qs.q; }
    groups.forEach(function(g){
      var raw=qs[g.field]; if(!raw) return;
      raw.split(',').forEach(function(v){ if(v) g.sel.add(v); });
    });
  }
  // TrVeri STANDART sayfalama (rule 3.17) — kart ızgarası: 24 kart/sayfa.
  var p=window.TVPager?window.TVPager.attach({grid:list,per:24,
        mount:document.getElementById('uPagerNav'),match:match}):null;

  // Sayaçlar DİĞER filtrelere göre yeniden hesaplanır: "Vakıf" seçiliyken İl listesinde
  // "Van 1" görmek çıkmaz tıklamadır (Van'da vakıf üniv. yok). 0 kalanlar soluklaşır.
  function recount(){
    groups.forEach(function(g){
      var others=groups.filter(function(x){return x!==g;}), cnt={};
      Array.prototype.forEach.call(list.children,function(a){
        if(term && a.textContent.toLocaleLowerCase('tr').indexOf(term)<0) return;
        for(var i=0;i<others.length;i++){ if(!groupMatch(a,others[i])) return; }
        cardVals(a,g).forEach(function(v){ cnt[v]=(cnt[v]||0)+1; });
      });
      Array.prototype.forEach.call(g.panel.querySelectorAll('.ms-list label'),function(l){
        var v=l.getAttribute('data-v'), n=cnt[v]||0;
        l.querySelector('.ms-n').textContent=n;
        l.classList.toggle('zero', n===0);
      });
    });
  }
  function apply(){
    if(p) p.reset();
    else Array.prototype.forEach.call(list.children,function(a){a.style.display=match(a)?'':'none';});
    var n=0; Array.prototype.forEach.call(list.children,function(a){ if(match(a)) n++; });
    if(empty) empty.style.display = n? 'none':'';
    recount();
    syncQS();
  }
  function chip(text,onDel,plain){
    var c=document.createElement('span'); c.className='ms-chip'; c.textContent=text;
    if(plain) c.style.borderColor='var(--border)';
    var x=document.createElement('button'); x.type='button'; x.textContent='×';
    x.setAttribute('aria-label',text+' filtresini kaldır'); x.onclick=onDel;
    c.appendChild(x); chips.appendChild(c); 
  }
  function paint(){
    var toplam=0;
    groups.forEach(function(g){
      toplam+=g.sel.size;
      g.lbl.textContent = g.sel.size ? (g.sel.size===1 ? Array.from(g.sel)[0] : g.sel.size+' seçili') : g.allLbl;
      g.btn.classList.toggle('on', g.sel.size>0);
    });
    chips.innerHTML='';
    groups.forEach(function(g){
      Array.from(g.sel).sort(function(a,b){return a.localeCompare(b,'tr');}).forEach(function(v){
        chip(v, function(){ g.sel.delete(v); sync(g); paint(); apply(); });
      });
    });
    if(toplam>1) chip('Hepsini temizle', function(){
      groups.forEach(function(g){ g.sel.clear(); sync(g); }); paint(); apply();
    }, true);
  }
  function sync(g){
    Array.prototype.forEach.call(g.panel.querySelectorAll('input[type=checkbox]'),function(b){
      b.checked = g.sel.has(b.value);
    });
  }
  function close(g){ g.panel.setAttribute('hidden',''); g.btn.setAttribute('aria-expanded','false'); }

  groups.forEach(function(g){
    g.btn.addEventListener('click',function(){
      var open = g.panel.hasAttribute('hidden');
      groups.forEach(close);                       // aynı anda tek panel açık kalsın
      if(open){
        g.panel.removeAttribute('hidden'); g.btn.setAttribute('aria-expanded','true');
        // Sağa taşıyorsa panelin hizasını çevir (düğme satırın sağ ucundaysa gerekli).
        g.panel.classList.remove('right');
        if(g.panel.getBoundingClientRect().right > document.documentElement.clientWidth-4)
          g.panel.classList.add('right');
        if(g.search) g.search.focus();
      }
    });
    g.panel.addEventListener('change',function(e){
      var b=e.target; if(b.type!=='checkbox') return;
      if(b.checked) g.sel.add(b.value); else g.sel.delete(b.value);
      paint(); apply();
    });
    var all=g.panel.querySelector('[data-act=all]'), none=g.panel.querySelector('[data-act=none]');
    if(all) all.onclick=function(){
      Array.prototype.forEach.call(g.panel.querySelectorAll('.ms-list label'),function(l){
        if(l.style.display!=='none') g.sel.add(l.querySelector('input').value);
      });
      sync(g); paint(); apply();
    };
    if(none) none.onclick=function(){ g.sel.clear(); sync(g); paint(); apply(); };
    if(g.search) g.search.addEventListener('input',function(){
      var t=this.value.toLocaleLowerCase('tr').trim();
      Array.prototype.forEach.call(g.panel.querySelectorAll('.ms-list label'),function(l){
        l.style.display = !t || l.getAttribute('data-v').toLocaleLowerCase('tr').indexOf(t)>=0 ? '':'none';
      });
    });
  });
  document.addEventListener('click',function(e){
    groups.forEach(function(g){
      if(!g.panel.hasAttribute('hidden') && !g.el.contains(e.target)) close(g);
    });
  });
  document.addEventListener('keydown',function(e){
    if(e.key!=='Escape') return;
    groups.forEach(function(g){ if(!g.panel.hasAttribute('hidden')){ close(g); g.btn.focus(); } });
  });
  q.addEventListener('input',function(){ term=this.value.toLocaleLowerCase('tr').trim(); apply(); });

  // Sayfa açılışında URL'deki filtre durumunu geri yükle (paylaşılan link) — checkbox'ları
  // işaretlemeden ÖNCE yapılmalı ki "Daha fazla filtre" otomatik-açılma kontrolü doğru çalışsın.
  restoreFromQS();
  groups.forEach(sync);

  // "Daha fazla filtre" — ikincil grupları göster/gizle. Bir ikincil filtrede seçim varken
  // sayfa tazelenirse (geri/ileri) kapalı kalmasın diye ilk paint'te otomatik açılır.
  var moreBtn=document.getElementById('fMoreBtn'), moreBox=document.getElementById('fMore');
  if(moreBtn && moreBox){
    moreBtn.addEventListener('click',function(){
      var open=moreBox.hasAttribute('hidden');
      if(open) moreBox.removeAttribute('hidden'); else moreBox.setAttribute('hidden','');
      moreBtn.classList.toggle('on', open);
      moreBtn.querySelector('.msf-toggle-caret').textContent = open? '▴':'▾';
    });
    var ikincilSecili = groups.some(function(g){ return moreBox.contains(g.el) && g.sel.size; });
    if(ikincilSecili) moreBtn.click();
  }

  paint(); recount();
  if(term || groups.some(function(g){return g.sel.size;})) apply();
})();
</script>"""


def _ms_group(field, icon, all_label, counts, *, searchable=True, order=None, multi=False, tip=None):
    """Tek bir çoklu-seçim filtresi çizer. counts: {değer: adet}.
    order verilmezse Türkçe alfabetik (§3.6) sıralanır.
    multi=True: kartın data-<field> özniteliği "|" ile ayrılmış BİRDEN ÇOK değer taşır
    (ör. bir üniversitenin hem Burslu hem Ücretli programı olabilir) — eşleşme kesişimle
    yapılır (bkz. MULTI_FILTER_JS `groupMatch`). tip: buton başlığına eklenecek açıklama."""
    vals = order or sorted(counts, key=tr_sort_key)
    opts = "".join(
        f'<label data-v="{html_escape(v)}"><input type="checkbox" value="{html_escape(v)}">'
        f'{html_escape(v)}<span class="ms-n">{counts[v]}</span></label>'
        for v in vals if v in counts)
    srch = (f'<input class="ms-search" type="text" placeholder="{all_label} ara…" autocomplete="off">'
            if searchable else "")
    multi_attr = ' data-multi="1"' if multi else ""
    tip_attr = f' title="{html_escape(tip)}"' if tip else ""
    return f"""<div class="ms" data-field="{field}" data-all="{html_escape(all_label)}"{multi_attr}{tip_attr}>
  <button type="button" class="ms-btn" aria-expanded="false" aria-haspopup="true">
    <span aria-hidden="true">{icon}</span><span class="ms-lbl">{html_escape(all_label)}</span><span class="ms-caret">▾</span>
  </button>
  <div class="ms-panel" hidden role="group" aria-label="{html_escape(all_label)} (birden fazla seçilebilir)">
    {srch}
    <div class="ms-actions"><button type="button" data-act="all">Görünenleri seç</button><button type="button" data-act="none">Temizle</button></div>
    <div class="ms-list">{opts}</div>
  </div>
</div>"""


# Program kaydındaki tür kodunu üniversite düzeyinde tek etikete indirger.
# (Devlet üniv. varyantları — ücretli/KKTC kampüs/KKTC uyruklu — hepsi "Devlet"tir.)
_TUR_BASE = {"D": "Devlet", "DU": "Devlet", "DK": "Devlet", "DKU": "Devlet",
             "V": "Vakıf", "K": "KKTC", "Y": "Diğer"}
TUR_SIRA = ["Devlet", "Vakıf", "Vakıf MYO", "KKTC", "Diğer"]

BILINMIYOR = "Bilinmiyor"


def _kova(deger, esikler_ve_etiketler):
    """deger için ilk (esik, etiket) çiftini bulur (esik = üst sınır, sonsuz için None)."""
    if deger is None:
        return BILINMIYOR
    for esik, etiket in esikler_ve_etiketler:
        if esik is None or deger < esik:
            return etiket
    return esikler_ve_etiketler[-1][1]


OGRENCI_KOVA = [(5000, "5.000 altı"), (20000, "5.000–20.000"), (50000, "20.000–50.000"), (None, "50.000 üzeri")]
OGRENCI_SIRA = ["5.000 altı", "5.000–20.000", "20.000–50.000", "50.000 üzeri", BILINMIYOR]
KURULUS_KOVA = [(1980, "1980 öncesi"), (2000, "1980–1999"), (2010, "2000–2009"), (None, "2010 sonrası")]
KURULUS_SIRA = ["1980 öncesi", "1980–1999", "2000–2009", "2010 sonrası", BILINMIYOR]
ORAN_KOVA = [(15, "15'in altı (az kalabalık)"), (25, "15–25"), (40, "25–40"), (None, "40 ve üzeri (kalabalık)")]
ORAN_SIRA = ["15'in altı (az kalabalık)", "15–25", "25–40", "40 ve üzeri (kalabalık)", BILINMIYOR]

# Eğitim dili / akreditasyon: uzun kuyruk var (bkz. veri ölçümü) — yalnız anlamlı sıklıktaki
# değerler filtre seçeneği olur; nadir olanlar "Diğer dil / Diğer akreditasyon" başlığı yerine
# sessizce dışarıda bırakılır (10'dan az üniversitede geçen değer ayrım gücü katmıyor).
DIL_MIN_UNI = 3
AKR_MIN_UNI = 3


def page_universiteler(u_by_slug, programs):
    from collections import Counter, defaultdict
    cnt = Counter(r["u"] for r in programs if r.get("u"))
    ilmap, turmap = {}, defaultdict(Counter)
    burs_of, dil_of, akr_of = defaultdict(set), defaultdict(set), defaultdict(set)
    for r in programs:
        u = r.get("u")
        if not u:
            continue
        if r.get("il") and u not in ilmap:
            ilmap[u] = r["il"]
        t = _TUR_BASE.get(r.get("t"))
        if t:
            turmap[u][t] += 1
        if r.get("bs"):
            burs_of[u].add(r["bs"])
        if r.get("dil"):
            dil_of[u].add(r["dil"])
        if r.get("akr"):
            akr_of[u].add(r["akr"])
    items = sorted(u_by_slug.items(), key=lambda kv: kv[1].lower())

    # İl/tür: önce universiteler.json künyesi (tam kapsam), yoksa program kaydından türet.
    # 21 üniversitede (KKTC + yurtdışı ortak + yeni kurulanlar) künye boş — program kaydı doldurur.
    # Bölge: künyedeki 208 kayıttan il→bölge sözlüğü kendiliğinden çıkarılır (tutarlılığı
    # ölçüldü — hiçbir il iki bölgeye düşmüyor); Kıbrıs'taki üniversiteler ayrı "Kıbrıs" bölgesi
    # sayılır (coğrafi bölge değil ama filtre olarak anlamlı); il de yoksa "Yurt Dışı Kampüs".
    il_bolge = {}
    for v in UNIV.values():
        if v.get("il") and v.get("bolge"):
            il_bolge[v["il"]] = v["bolge"]

    def bolge_for(il):
        if not il:
            return "Yurt Dışı Kampüs"
        if il == "Kıbrıs":
            return "Kıbrıs"
        return il_bolge.get(il, "")

    il_of, tur_of, bolge_of = {}, {}, {}
    ogrenci_kova_of, kurulus_kova_of, oran_kova_of = {}, {}, {}
    for _s, u in items:
        info = uni_info(u)
        il = (info.get("il") or ilmap.get(u) or "").strip()
        il_of[u] = il
        tur = (info.get("tur") or "").strip().replace("Vakıf Myo", "Vakıf MYO")
        if not tur and turmap.get(u):
            tur = turmap[u].most_common(1)[0][0]
        tur_of[u] = tur
        bolge_of[u] = bolge_for(il)
        ogrenci_kova_of[u] = _kova(info.get("ogrenci"), OGRENCI_KOVA)
        kurulus_kova_of[u] = _kova(int(info["kurulus"]) if info.get("kurulus") else None, KURULUS_KOVA)
        ogr, akd = info.get("ogrenci"), info.get("akademisyen")
        oran_kova_of[u] = _kova((ogr / akd) if ogr and akd else None, ORAN_KOVA)

    il_cnt = Counter(v for v in il_of.values() if v)
    tur_cnt = Counter(v for v in tur_of.values() if v)
    bolge_cnt = Counter(v for v in bolge_of.values() if v)
    ogrenci_cnt = Counter(ogrenci_kova_of.values())
    kurulus_cnt = Counter(kurulus_kova_of.values())
    oran_cnt = Counter(oran_kova_of.values())

    def _cok_deger_sayaci(per_uni_sets, min_uni):
        c = Counter()
        for vals in per_uni_sets.values():
            c.update(vals)
        return Counter({k: v for k, v in c.items() if v >= min_uni})

    burs_cnt = _cok_deger_sayaci(burs_of, 1)   # burs seçenekleri az sayıda (4) — eşik gereksiz
    dil_cnt = _cok_deger_sayaci(dil_of, DIL_MIN_UNI)
    akr_cnt = _cok_deger_sayaci(akr_of, AKR_MIN_UNI)

    cards = ""
    for s, u in items:
        ic = uni_logo_html(u, size=34, cls="uni-logo") or "🏛️"
        il, tur = il_of.get(u, ""), tur_of.get(u, "")
        alt = " · ".join(x for x in [il, tur, f"{cnt.get(u,0)} program"] if x)
        # sorted(): set() sırası Python process'leri arasında rastgele (hash randomization) —
        # sıralamazsak her build'de aynı içerik farklı sırada yazılır, git'te sahte gürültülü
        # diff üretir (2026-08-04'te ölçüldü: universiteler.html her cron koşumunda değişiyordu).
        burs_v = "|".join(sorted(v for v in burs_of.get(u, ()) if v in burs_cnt))
        dil_v = "|".join(sorted(v for v in dil_of.get(u, ()) if v in dil_cnt))
        akr_v = "|".join(sorted(v for v in akr_of.get(u, ()) if v in akr_cnt))
        cards += (f'<a class="tool-btn" href="/universite/{s}.html" '
                  f'data-il="{html_escape(il)}" data-tur="{html_escape(tur)}" '
                  f'data-bolge="{html_escape(bolge_of.get(u,""))}" '
                  f'data-ogrenci="{html_escape(ogrenci_kova_of.get(u,""))}" '
                  f'data-kurulus="{html_escape(kurulus_kova_of.get(u,""))}" '
                  f'data-oran="{html_escape(oran_kova_of.get(u,""))}" '
                  f'data-burs="{html_escape(burs_v)}" data-dil="{html_escape(dil_v)}" data-akr="{html_escape(akr_v)}">'
                  f'<span class="tb-icon">{ic}</span><span class="tb-text"><b>{u}</b>'
                  f'<span>{alt}</span></span></a>')

    body = MULTI_FILTER_CSS + f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / Üniversiteler</div>
<div class="page-title"><h1>Üniversitelere Göre Taban Puanları</h1><span class="sub">{len(items)} üniversite · {len(il_cnt)} il · YÖK Atlas {YKS_YIL}</span></div>
<div class="msf">
{_ms_group("il", "📍", "Tüm iller", il_cnt)}
{_ms_group("tur", "🏛️", "Tüm türler", tur_cnt, searchable=False, order=TUR_SIRA)}
  <input id="uSearch" type="text" placeholder="Üniversite ara… (örn. boğaziçi, ege, itü)">
</div>
<button type="button" class="msf-toggle" id="fMoreBtn" aria-expanded="false" aria-controls="fMore">
  <span aria-hidden="true">🔎</span> Daha fazla filtre <span class="msf-toggle-caret">▾</span>
</button>
<div class="msf-more" id="fMore" hidden>
{_ms_group("bolge", "🗺️", "Tüm bölgeler", bolge_cnt, searchable=False,
           order=["Marmara", "İç Anadolu", "Ege", "Akdeniz", "Karadeniz", "Doğu Anadolu",
                  "Güneydoğu Anadolu", "Kıbrıs", "Yurt Dışı Kampüs"])}
{_ms_group("ogrenci", "👥", "Tüm öğrenci sayıları", ogrenci_cnt, searchable=False, order=OGRENCI_SIRA,
           tip="Toplam kayıtlı öğrenci sayısına göre.")}
{_ms_group("burs", "🎓", "Burs / ücret durumu", burs_cnt, searchable=False, multi=True,
           order=["Burslu", "%50 İndirimli", "%25 İndirimli", "Ücretli"],
           tip="Yalnızca program bazında burs/ücret bilgisi bulunan (çoğunlukla vakıf) üniversiteler için geçerlidir.")}
{_ms_group("kurulus", "🏗️", "Tüm kuruluş yılları", kurulus_cnt, searchable=False, order=KURULUS_SIRA)}
{_ms_group("oran", "📊", "Öğrenci/Akademisyen", oran_cnt, searchable=False, order=ORAN_SIRA,
           tip="Bir akademisyene düşen öğrenci sayısı — düşük oran daha az kalabalık sınıf demektir.")}
{_ms_group("dil", "🌐", "Eğitim dili", dil_cnt, multi=True,
           tip="Üniversitede bu dilde en az bir program bulunuyor.")}
{_ms_group("akr", "✅", "Akreditasyon", akr_cnt, multi=True,
           tip="Üniversitede bu kurumca akredite en az bir program bulunuyor (MÜDEK, TEPDAD, FEDEK…).")}
</div>
<div class="ms-chips" id="fChips"></div>
<div class="tool-row" id="uList">
{cards}
</div>
<div class="ms-empty" id="uEmpty" style="display:none">Seçtiğiniz ölçütlere uyan üniversite bulunamadı. Filtreleri gevşetin veya aramayı temizleyin.</div>
<nav id="uPagerNav"></nav>
""" + MULTI_FILTER_JS
    return base("universiteler.html", f"Üniversitelere Göre Taban Puanları {YKS_YIL} | SınavVeri",
                "Tüm üniversitelerin 2025 taban puanları ve bölümleri. 227 devlet ve vakıf üniversitesi YÖK Atlas verisiyle. "
                "İl, bölge, tür, burs durumu, kuruluş yılı, eğitim dili ve akreditasyona göre filtreleyin.",
                body)


KARSILASTIR_JS = r"""<script nonce="__NONCE__">
(function(){
  var SV=window.SV||{};
  var TUR={D:'Devlet',V:'Vakıf',K:'KKTC',DK:'Devlet (KKTC Kampüs)',DU:'Devlet (Ücretli)',DKU:'Devlet (KKTC Uyruklu)',Y:'Diğer'};
  var PT={SAY:'Sayısal',EA:'Eşit Ağırlık','SÖZ':'Sözel','DİL':'Dil',TYT:'TYT'};
  var IDX={k:0,u:1,b:2,g:3,il:4,t:5,o:6,dil:7,bs:8,kont:9,tp:10,sira:11,yer:12,t24:13,t23:14,s24:15,s23:16};
  var cache={}, data=[], sel=[], curPT='say';
  function el(i){return document.getElementById(i);}
  function nf(n){return n==null||n===''?'—':Number(n).toLocaleString('tr-TR');}
  function pf(n){return n==null||n===''?'—':Number(n).toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2});}
  function esc(s){return (''+(s==null?'':s)).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
  function load(pt,cb){ if(cache[pt]){data=cache[pt];cb&&cb();return;}
    fetch('/veri/'+pt+'.json').then(function(r){return r.json();}).then(function(j){cache[pt]=j;data=j;cb&&cb();})
      .catch(function(){el('kStatus').textContent='Veri yüklenemedi.';}); }
  function doluluk(r){var k=r[IDX.kont],y=r[IDX.yer];if(!k)return '—';var o=Math.round(100*(y||0)/k);return (y||0)+'/'+k+' (%'+o+')';}
  function row(label,vals,bold){
    var tds=vals.map(function(v){return '<td'+(bold?' style="font-weight:700"':'')+'>'+v+'</td>';}).join('');
    return '<tr><th>'+label+'</th>'+tds+'</tr>';
  }
  function render(){
    var wrap=el('kResult');
    if(!sel.length){wrap.innerHTML='<div class="info-box">Karşılaştırmak için yukarıdan en az 2 program ekleyin. Eklediğiniz programlar yan yana kıyaslanır; bağlantıyı paylaşabilirsiniz.</div>';syncQS();return;}
    var heads=sel.map(function(r){return '<th><div class="kc-h"><b>'+esc(r[IDX.u])+'</b><span>'+esc(r[IDX.b])+'</span>'
      +'<button type="button" class="kc-x" data-rm="'+esc(r[IDX.k])+'">× çıkar</button></div></th>';}).join('');
    var h='<div class="kc-wrap"><table class="kc-table"><thead><tr><th></th>'+heads+'</tr></thead><tbody>';
    h+=row('İl',sel.map(function(r){return esc(r[IDX.il]);}));
    h+=row('Tür',sel.map(function(r){return TUR[r[IDX.t]]||r[IDX.t]||'—';}));
    h+=row('Puan Türü',sel.map(function(){return PT[curPT.toUpperCase()]||curPT.toUpperCase();}));
    h+=row('Öğrenim Türü',sel.map(function(r){return esc(r[IDX.o]||'—');}));
    h+=row('Öğrenim Dili',sel.map(function(r){return esc(r[IDX.dil]||'—');}));
    h+=row('Burs',sel.map(function(r){return esc(r[IDX.bs]||'—');}));
    h+=row('Taban 2025',sel.map(function(r){return pf(r[IDX.tp]);}),true);
    h+=row('Başarı Sırası 2025',sel.map(function(r){return nf(r[IDX.sira]);}),true);
    h+=row('Taban 2024',sel.map(function(r){return pf(r[IDX.t24]);}));
    h+=row('Başarı Sırası 2024',sel.map(function(r){return nf(r[IDX.s24]);}));
    h+=row('Taban 2023',sel.map(function(r){return pf(r[IDX.t23]);}));
    h+=row('Başarı Sırası 2023',sel.map(function(r){return nf(r[IDX.s23]);}));
    h+=row('Kontenjan',sel.map(function(r){return nf(r[IDX.kont]);}));
    h+=row('Doluluk (yerleşen)',sel.map(function(r){return doluluk(r);}));
    h+='</tbody></table></div>';
    h+='<div class="kc-actions"><button type="button" class="btn btn-ghost" id="kShare">🔗 Karşılaştırmayı Paylaş</button>'
      +'<button type="button" class="fchip-clear" id="kClear">Temizle</button></div>';
    wrap.innerHTML=h;
    syncQS();
  }
  function add(k){ if(sel.length>=4){el('kStatus').textContent='En fazla 4 program karşılaştırabilirsiniz.';return;}
    if(sel.some(function(r){return String(r[IDX.k])===String(k);}))return;
    var rec=data.filter(function(r){return String(r[IDX.k])===String(k);})[0];
    if(rec){sel.push(rec);render();} }
  function syncQS(){ try{ var p=sel.map(function(r){return r[IDX.k];}).join(','); var u=location.pathname+'?pt='+curPT+(p?'&p='+p:''); history.replaceState(null,'',u);}catch(e){} }
  // autocomplete
  var sb=el('kSearch'), sug=el('kSug');
  function suggest(){ var q=(sb.value||'').toLocaleLowerCase('tr').trim(); if(q.length<2){sug.style.display='none';return;}
    var hits=[],i; for(i=0;i<data.length&&hits.length<12;i++){ var r=data[i]; var hay=((r[IDX.u]||'')+' '+(r[IDX.b]||'')).toLocaleLowerCase('tr');
      if(hay.indexOf(q)>=0)hits.push(r); }
    if(!hits.length){sug.style.display='none';return;}
    sug.innerHTML=hits.map(function(r){return '<div class="kc-sug" data-k="'+esc(r[IDX.k])+'"><b>'+esc(r[IDX.b])+'</b> — '+esc(r[IDX.u])+' <small>'+pf(r[IDX.tp])+'</small></div>';}).join('');
    sug.style.display='block';
  }
  sb.addEventListener('input',suggest);
  sug.addEventListener('click',function(e){var d=e.target.closest('.kc-sug');if(!d)return;add(d.getAttribute('data-k'));sb.value='';sug.style.display='none';});
  document.addEventListener('click',function(e){if(!sug.contains(e.target)&&e.target!==sb)sug.style.display='none';});
  el('kResult').addEventListener('click',function(e){
    var rm=e.target.getAttribute&&e.target.getAttribute('data-rm');
    if(rm){sel=sel.filter(function(r){return String(r[IDX.k])!==String(rm);});render();return;}
    if(e.target.id==='kClear'){sel=[];render();return;}
    if(e.target.id==='kShare'){ try{SV.copy(location.href,e.target);}catch(e2){} }
  });
  var ptSel=el('kPT');
  ptSel.addEventListener('change',function(){curPT=ptSel.value;sel=[];el('kStatus').textContent='';load(curPT,render);});
  // init from QS
  (function(){ var qs=SV.qsGet?SV.qsGet():{}; if(qs.pt&&PT[qs.pt.toUpperCase()]){curPT=qs.pt;ptSel.value=qs.pt;}
    load(curPT,function(){ if(qs.p){qs.p.split(',').forEach(function(k){add(k);});} render(); }); })();
})();
</script>"""


def page_karsilastir():
    opts = "".join(f'<option value="{c.lower()}">{PT_LABEL.get(c2, c)}</option>'
                   for c, c2 in [("say", "SAY"), ("ea", "EA"), ("soz", "SÖZ"), ("dil", "DİL"), ("tyt", "TYT")])
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / Karşılaştır</div>
<div class="page-title"><h1>Bölüm & Üniversite Karşılaştırma</h1><span class="sub">2-4 programı yan yana kıyasla · paylaşılabilir bağlantı</span></div>
<div class="info-box">İki ile dört programı taban puanı, başarı sırası (2023-2025), kontenjan, doluluk, öğrenim dili ve türüne göre yan yana karşılaştırın. Önce puan türünü seçin, sonra program arayıp ekleyin. Oluşan bağlantıyı paylaşabilirsiniz.</div>
<div class="calc-card" style="margin-bottom:16px">
  <div style="display:grid;grid-template-columns:160px 1fr;gap:10px;align-items:end">
    <div><label style="font-size:12px;color:var(--fg-faded);font-weight:700">Puan Türü</label>
      <select id="kPT" class="btn btn-ghost" style="text-align:left;width:100%;margin-top:4px">{opts}</select></div>
    <div style="position:relative"><label style="font-size:12px;color:var(--fg-faded);font-weight:700">Program Ekle</label>
      <input id="kSearch" type="text" autocomplete="off" placeholder="Üniversite veya bölüm ara… (örn. boğaziçi bilgisayar)" style="width:100%;margin-top:4px;padding:9px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:14px">
      <div id="kSug" class="kc-sugbox" style="display:none"></div>
    </div>
  </div>
  <div id="kStatus" style="margin-top:10px;font-size:13px;color:var(--accent);font-weight:700"></div>
</div>
<div id="kResult"></div>
<div class="notice"><b>Kaynak:</b> YÖK Atlas {YKS_YIL} (geçmiş: {YKS_HIST[0]}, {YKS_HIST[1]}). Karşılaştırma tahmini değerlendirme amaçlıdır; resmî tercih için <a href="https://www.osym.gov.tr" target="_blank" rel="noopener">ÖSYM</a> esastır.</div>
{KARSILASTIR_JS}
"""
    return base("karsilastir.html", "Bölüm ve Üniversite Karşılaştırma 2025 — Taban Puanı Kıyasla | SınavVeri",
                "Üniversite bölümlerini taban puanı, başarı sırası, kontenjan ve dolulukla yan yana karşılaştırın. 2-4 programı kıyaslayın, bağlantıyı paylaşın.",
                body)


# ───────────────────────── KİŞİYE ÖZEL KPSS TERCİH RAPORU (HİZMET) ─────────────────────────
KPSS_RAPOR_FORM_JS = r"""<script src="https://js.stripe.com/v3/" nonce="__NONCE__"></script>
<script nonce="__NONCE__">
(function(){
  var WA="__WA__", EMAIL="__EMAIL__", PK="__PK__", API="__API__";
  function v(id){var e=document.getElementById(id);return e?e.value.trim():'';}
  function st(m,err){var s=document.getElementById('kr_status');if(s){s.textContent=m||'';s.style.color=err?'#e03131':'var(--accent)';}}
  // Sipariş + Embedded Checkout
  function order(){return {ad:v('kr_ad'),tel:v('kr_tel'),eposta:v('kr_eposta'),duzey:v('kr_duzey'),
    pt:v('kr_pt'),puan:v('kr_puan'),il:v('kr_il'),kurum:v('kr_kurum'),brans:v('kr_brans'),not:v('kr_not')};}
  function valid(){
    var req=[['kr_ad','Ad Soyad'],['kr_tel','Telefon'],['kr_duzey','Öğrenim düzeyi'],['kr_puan','KPSS puanı']];
    for(var i=0;i<req.length;i++){ if(!v(req[i][0])){ var e=document.getElementById(req[i][0]); if(e)e.focus();
      st('Lütfen '+req[i][1]+' alanını doldurun.',true); return false; } }
    st(''); return true;
  }
  var btn=document.getElementById('kr_pay');
  if(btn){ btn.addEventListener('click',function(){
    if(!valid())return;
    if(typeof Stripe==='undefined'){ st('Ödeme altyapısı yüklenemedi; sayfayı yenileyin.',true); return; }
    btn.disabled=true; st('Güvenli ödeme hazırlanıyor…');
    fetch(API,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(order())})
      .then(function(r){return r.json();})
      .then(function(d){
        if(!d.clientSecret)throw new Error('no secret');
        document.getElementById('kr_formwrap').style.display='none';
        document.getElementById('kr_checkout').style.display='block';
        st('');
        return Stripe(PK).initEmbeddedCheckout({clientSecret:d.clientSecret})
          .then(function(c){ c.mount('#kr_checkout'); });
      })
      .catch(function(){ st('Ödeme başlatılamadı, lütfen tekrar deneyin.',true); btn.disabled=false; });
  }); }
  // Soru / ön görüşme (WhatsApp / e-posta)
  function qmsg(){return '— SINAVVERİ KPSS RAPORU — SORU\nAd: '+v('q_ad')+'\nTel: '+v('q_tel')+'\nMesaj: '+v('q_not');}
  var qw=document.getElementById('q_wa');
  if(qw){ if(WA){ qw.addEventListener('click',function(){ window.open('https://wa.me/'+WA+'?text='+encodeURIComponent(qmsg()),'_blank'); }); } else qw.style.display='none'; }
  var qe=document.getElementById('q_email');
  if(qe){ qe.addEventListener('click',function(){ window.location.href='mailto:'+EMAIL+'?subject='+encodeURIComponent('KPSS Raporu — Soru')+'&body='+encodeURIComponent(qmsg()); }); }
})();
</script>"""


def page_kpss_rapor():
    wa = KPSS_RAPOR.get("whatsapp", "")
    email = KPSS_RAPOR.get("email", "")
    fiyat = KPSS_RAPOR.get("fiyat", "1.000")
    pk = KPSS_RAPOR.get("pk", "")
    api = KPSS_RAPOR.get("api", "/api/kpss/checkout")
    js = (KPSS_RAPOR_FORM_JS.replace("__WA__", wa).replace("__EMAIL__", email)
          .replace("__PK__", pk).replace("__API__", api))

    yes = '<span style="color:#2f9e44;font-weight:700">✓</span>'
    no = '<span style="color:#e03131">✕</span>'
    karsilastirma = f"""
<div class="data-table-wrap"><table class="data-table">
<thead><tr><th data-tip="Karşılaştırılan hizmet özelliği." data-type="text">Özellik</th><th data-tip="Kişiye Özel KPSS Tercih Raporumuzda bu özellik var mı?" data-type="text" style="text-align:center">SınavVeri Raporu</th><th data-tip="Piyasadaki tipik tercih danışmanlığı hizmetlerinde bu özellik var mı?" data-type="text" style="text-align:center">Tipik Hizmetler</th></tr></thead>
<tbody>
<tr><td>Puanına göre sıralı kadro listesi</td><td style="text-align:center">{yes}</td><td style="text-align:center">{yes}</td></tr>
<tr><td>Atama taban puanı <b>+ son yıllar trendi</b> (başarı sırası bazlı)</td><td style="text-align:center">{yes}</td><td style="text-align:center">{no}</td></tr>
<tr><td><b>Doluluk / yerleşen</b> analizi (kadro garanti mi, riskli mi)</td><td style="text-align:center">{yes}</td><td style="text-align:center">{no}</td></tr>
<tr><td><b>Şans bandı</b>: Rahat / Olası / Sınırda (veri-temelli)</td><td style="text-align:center">{yes}</td><td style="text-align:center">{no}</td></tr>
<tr><td>Kadro kodu + <b>nitelik kodu</b> uyum kontrolü</td><td style="text-align:center">{yes}</td><td style="text-align:center">~</td></tr>
<tr><td>Görsel PDF rapor + rehber yorumu</td><td style="text-align:center">{yes}</td><td style="text-align:center">{yes}</td></tr>
<tr><td>Rehber hocayla hazırlanır</td><td style="text-align:center">{yes}</td><td style="text-align:center">{yes}</td></tr>
<tr><td>Hizmet bedeli</td><td style="text-align:center"><b>{fiyat} TL</b></td><td style="text-align:center">2.000 TL+</td></tr>
</tbody></table></div>"""

    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / Kişiye Özel KPSS Tercih Raporu</div>
<div class="page-title"><h1>Kişiye Özel KPSS Tercih Raporu</h1><span class="sub">Tek tercih dönemi · veri-temelli sıralı liste · rehber hocayla hazırlanır · {fiyat} TL</span></div>

<div class="info-box" style="font-size:15px;line-height:1.7">
KPSS puanına ve kriterlerine göre <b>sana özel, sıralı bir atama tercih listesi</b> hazırlıyoruz: hangi kadroya
hangi sırada yazmalısın, hangileri <b>garanti</b>, hangileri <b>riskli</b>, taban puanları yıllara göre nasıl
değişmiş — hepsi gerçek YÖK/ÖSYM verisiyle. Üstüne <b>rehber hocayla birlikte hazırlanır</b>.
<a href="/kpss-tercih-raporu-ornek.html"><b>📄 Örnek raporu incele →</b></a>
</div>

<h2 style="margin:26px 0 12px">Rapor neler içerir?</h2>
<div class="tool-row">
  <div class="tool-btn" style="cursor:default"><span class="tb-icon">🎯</span><span class="tb-text"><b>Kişiye özel sıralı liste</b><span>Puanın + il/kurum/branş tercihlerine göre optimum tercih sırası</span></span></div>
  <div class="tool-btn" style="cursor:default"><span class="tb-icon">📈</span><span class="tb-text"><b>Taban puanı & başarı sırası trendi</b><span>Son yılların gerçek verisiyle "yükseliyor mu, dalgalı mı"</span></span></div>
  <div class="tool-btn" style="cursor:default"><span class="tb-icon">📊</span><span class="tb-text"><b>Doluluk / yerleşen analizi</b><span>Her kadro her dönem doluyor mu — garanti/risk değerlendirmesi</span></span></div>
  <div class="tool-btn" style="cursor:default"><span class="tb-icon">🟢</span><span class="tb-text"><b>Şans bandı</b><span>Rahat / Olası / Sınırda — veri-temelli olasılık etiketi</span></span></div>
  <div class="tool-btn" style="cursor:default"><span class="tb-icon">🔑</span><span class="tb-text"><b>Nitelik & kadro kodu kontrolü</b><span>Yanlış/uyumsuz tercih riskini sıfırlama</span></span></div>
  <div class="tool-btn" style="cursor:default"><span class="tb-icon">👨‍🏫</span><span class="tb-text"><b>Rehber hocayla hazırlanır + PDF</b><span>Uzman yorumu, görsel PDF rapor, rehber eşliğinde hazırlık</span></span></div>
</div>

<h2 style="margin:28px 0 12px">Neden SınavVeri raporu?</h2>
{karsilastirma}

<h2 style="margin:28px 0 12px">Nasıl çalışır? (3 adım)</h2>
<div class="tool-row">
  <div class="tool-btn" style="cursor:default"><span class="tb-icon">1️⃣</span><span class="tb-text"><b>Öde ve bilgilerini gir</b><span>Ödeme ekranında düzey + KPSS puanın + tercihlerini girersin (tek adım)</span></span></div>
  <div class="tool-btn" style="cursor:default"><span class="tb-icon">2️⃣</span><span class="tb-text"><b>Uzman hazırlar</b><span>Ödeme + bilgilerin bize tek kayıtta ulaşır; raporun 1-2 iş gününde hazırlanır</span></span></div>
  <div class="tool-btn" style="cursor:default"><span class="tb-icon">3️⃣</span><span class="tb-text"><b>Rapor + rehber</b><span>PDF raporun rehber hoca eşliğinde hazırlanır ve e-posta ile gelir</span></span></div>
</div>

<h2 style="margin:28px 0 12px" id="basvuru">🚀 Hemen Başla — Bilgilerini Gir, Öde, Rapor Yolda</h2>
<div class="calc-card">
  <div id="kr_formwrap">
    <p style="font-size:13px;color:var(--fg-faded);margin:0 0 14px">Bilgilerini gir; ödeme bu sayfada güvenle alınır. Bilgilerin ve ödemen <b>tek kayıtta</b> bize ulaşır — başka form doldurman gerekmez.</p>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px">
      <div><label class="kr-l">Ad Soyad *</label><input id="kr_ad" type="text" class="kr-i" placeholder="Adınız Soyadınız"></div>
      <div><label class="kr-l">Telefon *</label><input id="kr_tel" type="tel" class="kr-i" placeholder="05XX XXX XX XX"></div>
      <div><label class="kr-l">E-posta</label><input id="kr_eposta" type="email" class="kr-i" placeholder="ornek@eposta.com"></div>
      <div><label class="kr-l">Öğrenim Düzeyi *</label>
        <select id="kr_duzey" class="kr-i"><option value="">Seçiniz</option><option>Ortaöğretim (Lise)</option><option>Önlisans</option><option>Lisans</option></select></div>
      <div><label class="kr-l">KPSS Puan Türü</label><input id="kr_pt" type="text" class="kr-i" placeholder="örn. P3, P93, P94"></div>
      <div><label class="kr-l">KPSS Puanı *</label><input id="kr_puan" type="text" inputmode="decimal" class="kr-i" placeholder="örn. 78,540"></div>
      <div><label class="kr-l">Tercih Edilen İller</label><input id="kr_il" type="text" class="kr-i" placeholder="örn. Ankara, İstanbul"></div>
      <div><label class="kr-l">Kurum / Kadro Tercihleri</label><input id="kr_kurum" type="text" class="kr-i" placeholder="örn. belediye, üniversite, bakanlık"></div>
      <div><label class="kr-l">Branş / Alan / Bölüm</label><input id="kr_brans" type="text" class="kr-i" placeholder="örn. Büro Personeli, Mühendis, VHKİ"></div>
    </div>
    <div style="margin-top:12px"><label class="kr-l">Eklemek istedikleriniz</label>
      <textarea id="kr_not" class="kr-i" style="min-height:56px;resize:vertical" placeholder="Önceliklerin, özel durumun…"></textarea></div>
    <div id="kr_status" style="margin-top:10px;font-size:13px;font-weight:700"></div>
    <div style="margin-top:14px">
      <button type="button" class="btn btn-primary" id="kr_pay" style="font-size:17px;padding:14px 30px">💳 Öde ve Raporu Oluştur — {fiyat} TL</button>
      <p style="font-size:12px;color:var(--fg-faded);margin-top:10px">🔒 Ödeme bu sayfada Stripe güvencesiyle alınır (kredi/banka kartı). Bilgilerin yalnızca raporun için kullanılır.</p>
    </div>
  </div>
  <div id="kr_checkout" style="display:none;min-height:320px"></div>
</div>

<div class="calc-card" style="margin-top:16px">
  <b style="font-size:15px">💬 Önce sormak ister misin?</b>
  <p style="font-size:13px;color:var(--fg-faded);margin:6px 0 12px">Ödeme öncesi aklına takılanı sor; ön görüşme yapalım.</p>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px">
    <div><label class="kr-l">Ad Soyad</label><input id="q_ad" type="text" class="kr-i" placeholder="Adınız"></div>
    <div><label class="kr-l">Telefon</label><input id="q_tel" type="tel" class="kr-i" placeholder="05XX XXX XX XX"></div>
  </div>
  <div style="margin-top:12px"><label class="kr-l">Sorun / mesajın</label>
    <textarea id="q_not" class="kr-i" style="min-height:56px;resize:vertical" placeholder="Sormak istediğin…"></textarea></div>
  <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px">
    <button type="button" class="btn btn-primary" id="q_wa" style="background:#25d366;border-color:#25d366">📲 WhatsApp'tan Sor</button>
    <button type="button" class="btn btn-ghost" id="q_email">✉️ E-posta ile Sor</button>
  </div>
</div>

<div class="notice" style="margin-top:20px"><b>Not:</b> Bu hizmet kişisel danışmanlık ve veri-temelli analiz sunar; kesin yerleştirme garantisi vermez.
Resmî tercih işlemi <a href="https://www.osym.gov.tr" target="_blank" rel="noopener">ÖSYM</a> üzerinden yapılır.
Önce ücretsiz <a href="/kpss-tercih-robotu.html">KPSS tercih robotumuzu</a> deneyebilirsiniz.</div>
{js}
"""
    return base("kpss-tercih-raporu.html",
                f"Kişiye Özel KPSS Tercih Raporu {fiyat} TL — Veri Temelli Atama Tercih Listesi | SınavVeri",
                f"KPSS puanına göre kişiye özel, sıralı atama tercih listesi-raporu: taban puanı trendi, doluluk analizi, şans bandı; rehber hocayla hazırlanır. {fiyat} TL.",
                body)


def page_kpss_rapor_ornek():
    chip = lambda t, c: f'<span style="display:inline-block;background:{c};color:#fff;font-size:11px;font-weight:700;padding:2px 9px;border-radius:999px">{t}</span>'
    rahat, olasi, sinir = chip("RAHAT", "#2f9e44"), chip("OLASI", "#f59e0b"), chip("SINIRDA", "#e8590c")
    # Örnek (temsilî) veri — gerçek YÖK/ÖSYM 2025 değer aralıklarıyla tutarlı
    rows = [
        ("Çevre, Şehircilik ve İklim Değişikliği Bakanlığı", "Tekniker (301245112)", "Ankara", 4, "70/70 (%100)", "72,4", "71,1 ↑", "70,2 ↑", rahat),
        ("Sağlık Bakanlığı", "Sağlık Teknikeri (301188204)", "İstanbul", 12, "12/12 (%100)", "74,8", "73,9 ↑", "72,0 ↑", olasi),
        ("Karayolları Genel Müdürlüğü", "Tekniker (301250431)", "İzmir", 3, "3/3 (%100)", "75,6", "74,2 ↑", "73,8 ~", sinir),
        ("Bir Belediye (Ankara)", "Büro Personeli (301301077)", "Ankara", 5, "5/5 (%100)", "71,2", "69,8 ↑", "68,1 ↑", rahat),
        ("Bir Üniversite", "Tekniker (301277905)", "Ankara", 2, "2/2 (%100)", "76,1", "75,0 ↑", "—", sinir),
    ]
    tr = ""
    for kurum, kadro, il, kont, dol, t25, t24, t23, band in rows:
        tr += (f"<tr><td><b>{kurum}</b><br><small style='color:var(--fg-faded)'>{kadro}</small></td>"
               f"<td>{il}</td><td style='text-align:center'>{kont}</td><td style='text-align:center'>{dol}</td>"
               f"<td style='text-align:right'><b>{t25}</b></td><td style='text-align:right'>{t24}</td><td style='text-align:right'>{t23}</td>"
               f"<td style='text-align:center'>{band}</td></tr>")
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / <a href="/kpss-tercih-raporu.html">Kişiye Özel KPSS Tercih Raporu</a> / Örnek</div>
<div class="page-title"><h1>Örnek Rapor — Kişiye Özel KPSS Tercih Raporu</h1><span class="sub">Temsilî örnektir · gerçek raporunuz kendi puan ve kriterlerinize göre hazırlanır</span></div>

<div class="uk-card">
  <div class="uk-analiz"><h2 style="margin-top:0">👤 Aday Profili (örnek)</h2>
  <p><b>Öğrenim:</b> Önlisans · <b>KPSS Puan Türü:</b> KPSSP93 · <b>Puan:</b> 73,540 ·
  <b>Tercih illeri:</b> Ankara, İstanbul, İzmir · <b>Alan:</b> Tekniker / Büro Personeli · <b>Dönem:</b> 2025/1</p></div>
</div>

<h2 style="margin:24px 0 10px">🎯 Sana Önerilen Tercih Sırası</h2>
<div class="info-box">Aşağıdaki liste puanına en uygun kadrolardan, <b>tercih sırası</b> mantığıyla dizilmiştir: üstte yüksek-şans/yüksek-değer kadrolar.
Şans bandı son 3 yılın taban puanı oynaklığına göre hesaplanır.</div>
<div class="data-table-wrap"><table class="data-table">
<thead><tr><th data-tip="Kadronun ait olduğu kurum ve kadro unvanı." data-type="text">Kurum / Kadro</th><th data-tip="Kadronun bulunduğu il." data-type="text">İl</th><th data-tip="İlan edilen kadro sayısı." data-type="num" style="text-align:center">Kont.</th><th data-tip="Doluluk = yerleşen ÷ kontenjan." data-type="num" style="text-align:center">Doluluk</th><th data-tip="2025'te kadroya atanan son adayın KPSS puanı." data-type="num" style="text-align:right">Taban 2025</th><th data-tip="2024 atama taban puanı." data-type="num" style="text-align:right">2024</th><th data-tip="2023 atama taban puanı." data-type="num" style="text-align:right">2023</th><th data-tip="Puanına göre atanma şansı: Rahat (güvenli), Olası, Sınırda (riskli)." data-type="text" style="text-align:center">Şans</th></tr></thead>
<tbody>{tr}</tbody></table></div>

<h2 style="margin:24px 0 10px">🧭 Rehber Yorumu</h2>
<div class="uk-card"><div class="uk-analiz" style="border:0;padding:0">
<p>Puanın (73,540), Önlisans düzeyinde <b>Tekniker</b> ve <b>Büro Personeli</b> kadrolarının çoğunda <b>Rahat–Olası</b> banttadır.
1. ve 4. sıradaki kadrolar son 3 yıldır taban puanını <b>istikrarlı koruyor</b> ve her dönem doluyor; güvenli tercih olarak <b>listenin başına</b> alınmıştır.</p>
<p>3. ve 5. sıradaki kadrolar yüksek puanlı/az kontenjanlı; taban <b>yükseliş eğiliminde</b> olduğundan <b>Sınırda</b> işaretlendi —
bunları üst sıralara yazmak yerleşme şansını riske atabilir, <b>orta sıralarda</b> değerlendirilmesi önerilir.</p>
<p><b>Strateji:</b> Garanti kadroları (Rahat) listenin <b>sonuna doğru değil</b>, dengeli biçimde yerleştir; yüksek-değer/sınırda kadroları
üst-orta sıralara koy. Böylece hem yüksek bir kadroyu kovalar hem de boşta kalma riskini düşürürsün.
Detaylı sıralama ve alternatifler rehber hocayla hazırlık aşamasında netleştirilir.</p>
</div></div>

<div style="text-align:center;margin:28px 0">
  <a class="btn btn-primary" href="/kpss-tercih-raporu.html#basvuru" style="font-size:16px;padding:13px 30px">Kendi Raporumu İste →</a>
</div>
<div class="notice"><b>Kaynak:</b> YÖK Atlas / ÖSYM. Bu sayfa temsilî bir örnektir; sayılar gerçek bir adaya ait değildir.</div>
"""
    return base("kpss-tercih-raporu-ornek.html",
                "Örnek KPSS Tercih Raporu — Kişiye Özel Atama Tercih Listesi | SınavVeri",
                "Kişiye özel KPSS tercih raporu örneği: sıralı kadro listesi, taban puanı trendi, doluluk ve şans bandı analizi, rehber yorumu.",
                body)


KPSS_RAPORU_JS = r"""<script nonce="__NONCE__">
(function(){
  var qs=new URLSearchParams(location.search); var sid=qs.get('s')||qs.get('session_id');
  var elc=document.getElementById('rapor');
  function err(m){ elc.innerHTML='<div class="info-box" style="border-color:#e03131"><b>'+m+'</b></div>'; }
  function ndz(d){ d=(d||''); if(d.indexOf('Ortaöğretim')>=0||d.indexOf('Lise')>=0)return 'Ortaöğretim'; if(d.indexOf('Önlisans')>=0)return 'Önlisans'; if(d.indexOf('Lisans')>=0)return 'Lisans'; return d; }
  function num(s){ s=(''+(s||'')).replace(/[^0-9,.]/g,'').replace(/\./g,'').replace(',','.'); var n=parseFloat(s); return isNaN(n)?null:n; }
  function esc(s){ return (''+(s==null?'':s)).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  function pf(n){ return n==null?'—':Number(n).toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2}); }
  if(!sid){ err('Rapor bağlantısı geçersiz (sipariş kimliği yok).'); return; }
  elc.innerHTML='<div class="info-box">Raporun hazırlanıyor…</div>';
  fetch('/api/kpss/status?session_id='+encodeURIComponent(sid)).then(function(r){return r.json();}).then(function(o){
    if(!o || o.payment_status!=='paid'){ err('Ödeme bulunamadı veya henüz işleniyor. Birkaç dakika sonra tekrar deneyin.'); return; }
    var md=o.metadata||{};
    fetch('/veri/kpss.json').then(function(r){return r.json();}).then(function(DATA){ render(md,o,DATA); }).catch(function(){err('Veri yüklenemedi.');});
  }).catch(function(){ err('Rapor yüklenemedi.'); });

  function render(md,o,DATA){
    var duzey=ndz(md.duzey), puan=num(md.kpsspuan);
    if(!puan){ err('KPSS puanı okunamadı; lütfen bizimle iletişime geçin.'); return; }
    var iller=(md.iller||'').toLocaleLowerCase('tr').split(/[,;]/).map(function(s){return s.trim();}).filter(Boolean);
    var kw=((md.kurum||'')+' '+(md.brans||'')).toLocaleLowerCase('tr').split(/[\s,;]+/).filter(function(t){return t.length>2;});
    var rows=DATA.filter(function(r){ return r[3]===duzey && r[8]!=null && r[8]<=puan+1; });
    var byIl=iller.length?rows.filter(function(r){var il=(r[2]||'').toLocaleLowerCase('tr');return iller.some(function(x){return il.indexOf(x)>=0;});}):rows;
    if(byIl.length>=3)rows=byIl;
    if(kw.length){ var byKw=rows.filter(function(r){var h=((r[0]||'')+' '+(r[1]||'')).toLocaleLowerCase('tr');return kw.some(function(t){return h.indexOf(t)>=0;});}); if(byKw.length>=3)rows=byKw; }
    rows.sort(function(a,b){return (b[8]||0)-(a[8]||0);});
    var rahat=0,olasi=0,sinir=0;
    rows.forEach(function(r){var m=puan-r[8]; if(m>=4)rahat++; else if(m>=0)olasi++; else sinir++;});
    var top=rows.slice(0,60);
    var tr=top.map(function(r,i){
      var m=puan-r[8]; var band=m>=4?'<span class="tag tag-lgs">Rahat</span>':(m>=0?'<span class="tag tag-kpss">Olası</span>':'<span class="tag tag-other">Sınırda</span>');
      return '<tr><td>'+(i+1)+'</td><td><b>'+esc(r[0])+'</b><br><small style="color:var(--fg-faded)">'+esc(r[1])+'</small></td>'
        +'<td>'+esc(r[2])+'</td><td>'+esc(r[4])+'</td><td style="text-align:right"><b>'+pf(r[8])+'</b></td><td style="text-align:center">'+band+'</td></tr>';
    }).join('');
    var ad=esc(md.ad||'Aday');
    var prof='<div class="uk-card"><div class="uk-analiz" style="border:0;padding:0"><h2 style="margin-top:0">👤 '+ad+' — Aday Profili</h2>'
      +'<p><b>Öğrenim:</b> '+esc(duzey)+' · <b>KPSS Puanı:</b> '+pf(puan)+(md.puanturu?' ('+esc(md.puanturu)+')':'')
      +(iller.length?' · <b>Tercih illeri:</b> '+esc(md.iller):'')+(md.brans?' · <b>Alan:</b> '+esc(md.brans):'')+'</p></div></div>';
    var ozet='<div class="uk-stats" style="margin:16px 0"><div class="uk-stat"><span class="uk-val">'+rows.length.toLocaleString("tr-TR")+'</span><span class="uk-lbl">Uygun Kadro</span></div>'
      +'<div class="uk-stat"><span class="uk-val" style="color:#2f9e44">'+rahat+'</span><span class="uk-lbl">Rahat</span></div>'
      +'<div class="uk-stat"><span class="uk-val" style="color:#f59e0b">'+olasi+'</span><span class="uk-lbl">Olası</span></div>'
      +'<div class="uk-stat"><span class="uk-val" style="color:#e8590c">'+sinir+'</span><span class="uk-lbl">Sınırda</span></div></div>';
    var tablo= rows.length? ('<h2 style="margin:18px 0 10px">🎯 Sana Önerilen Tercih Sırası <small style="font-weight:400;color:var(--fg-faded)">(en yüksek değerli/güvenli kadrolar üstte · ilk 60)</small></h2>'
      +'<div class="data-table-wrap"><table class="data-table"><thead><tr><th data-nosort data-tip="Önerilen tercih sırası.">#</th><th data-tip="Kadronun ait olduğu kurum ve kadro unvanı.">Kurum / Kadro</th><th data-tip="Kadronun bulunduğu il.">İl</th><th data-tip="Kadronun yer aldığı KPSS yerleştirme dönemi.">Dönem</th><th data-tip="Kadroya atanan son adayın KPSS taban puanı.">Taban</th><th data-tip="Puanına göre atanma şansı: Rahat, Olası, Sınırda.">Şans</th></tr></thead><tbody>'+tr+'</tbody></table></div>')
      : '<div class="info-box">Bu kriterlerle uygun kadro bulunamadı. Rehberimiz seninle iletişime geçip kriterleri birlikte gözden geçirecek.</div>';
    var rehber='<div class="uk-card" style="margin-top:18px"><div class="uk-analiz" style="border:0;padding:0"><h2 style="margin-top:0">🧭 Rehber Notu</h2>'
      +'<p>Bu liste, puanına ve tercihlerine göre derlenmiş bir <b>ön rapordur</b>. Uzman KPSS rehberimiz; puanın, önceliklerin ve güncel kontenjan eğilimlerine göre listeyi <b>tercih sırasına</b> göre optimize edip '
      +'<b>1-2 iş günü içinde</b> seninle iletişime geçecek ve raporunu rehber hocayla birlikte hazırlayacak.</p>'
      +'<p style="font-size:11px;color:var(--fg-faded)">Kaynak: ÖSYM 2025 KPSS yerleştirme verisi. Tahmini değerlendirmedir; kesin tercih ÖSYM AİS üzerinden yapılır.</p></div></div>';
    elc.innerHTML=prof+ozet+tablo+rehber
      +'<div style="text-align:center;margin:20px 0"><button type="button" class="btn btn-ghost" onclick="window.print()">🖨️ Yazdır / PDF kaydet</button></div>';
  }
})();
</script>"""


def page_kpss_raporu():
    body = ("""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / <a href="/kpss-tercih-raporu.html">Kişiye Özel KPSS Tercih Raporu</a> / Raporum</div>
<div class="page-title"><h1>📄 Kişiye Özel KPSS Tercih Raporun</h1><span class="sub">Ödemene özel hazırlanan ön rapor · veri-temelli</span></div>
<div id="rapor"></div>
""" + KPSS_RAPORU_JS)
    return base("kpss-raporu.html", "Kişiye Özel KPSS Tercih Raporun | SınavVeri",
                "Ödemenize özel hazırlanan kişiye özel KPSS tercih raporu: sıralı kadro listesi, taban puanı ve şans analizi.",
                body, extra_head='<meta name="robots" content="noindex,nofollow">')


def page_kpss_rapor_tesekkurler():
    wa = KPSS_RAPOR.get("whatsapp", "")
    wa_html = (f' veya <a href="https://wa.me/{wa}" target="_blank" rel="noopener">WhatsApp</a>' if wa else "")
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / <a href="/kpss-tercih-raporu.html">Kişiye Özel KPSS Tercih Raporu</a> / Teşekkürler</div>
<div class="page-title"><h1>✅ Ödemen alındı, teşekkürler!</h1><span class="sub">Kişiye özel ön raporun hazır</span></div>
<div class="uk-card"><div class="uk-analiz" style="border:0;padding:0">
<p style="font-size:15px;line-height:1.7">Ödemen başarıyla alındı ve <b>kişiye özel ön raporun hazırlandı.</b> Aşağıdaki butondan hemen görebilirsin.</p>
<div style="text-align:center;margin:18px 0">
  <a class="btn btn-primary" id="raporBtn" href="/kpss-tercih-raporu.html" style="font-size:17px;padding:14px 32px">📄 Ön Raporunu Gör</a>
</div>
<p style="font-size:15px;line-height:1.7"><b>Sırada ne var?</b></p>
<ul style="font-size:14px;line-height:1.8;margin:0 0 8px 18px">
<li>Uzman KPSS rehberimiz raporunu <b>tercih sırasına göre optimize edip 1-2 iş günü içinde</b> seninle iletişime geçecek.</li>
<li>Sana <b>e-posta</b>{wa_html} ile ulaşıp raporunu <b>rehber hocayla birlikte hazırlayacağız</b>.</li>
<li>Nihai görsel PDF raporun rehber yorumuyla iletilecek.</li>
</ul>
</div></div>
<div style="text-align:center;margin:24px 0">
  <a class="btn btn-ghost" href="/kpss-tercih-robotu.html">← KPSS Tercih Robotu</a>
  <a class="btn btn-ghost" href="/index.html">Ana Sayfa</a>
</div>
<script nonce="__NONCE__">
(function(){{
  try{{ var s=new URLSearchParams(location.search).get('session_id');
    var b=document.getElementById('raporBtn');
    if(s&&b){{ b.href='/kpss-raporu.html?s='+encodeURIComponent(s); }}
  }}catch(e){{}}
}})();
</script>
"""
    return base("kpss-tercih-raporu-tesekkurler.html",
                "Teşekkürler — Kişiye Özel KPSS Tercih Raporu | SınavVeri",
                "Ödemeniz alındı. Kişiye özel ön KPSS tercih raporunuz hazır.",
                body)


# ───────────────────────── ŞEHİR (İL) ÜNİVERSİTE SAYFALARI ─────────────────────────
def gen_sehir_pages(programs, u_by_slug):
    """Her il için o ildeki üniversitelerin listesi (logo + program sayısı + tür)."""
    from collections import defaultdict
    slug_by_u = {u: s for s, u in u_by_slug.items()}
    il_unis = defaultdict(set)
    uni_prog = defaultdict(int)
    uni_il = {}
    uni_tur = {}
    for r in programs:
        u, il = r.get("u"), r.get("il")
        if not (u and il):
            continue
        il_unis[il].add(u)
        uni_prog[u] += 1
        uni_il.setdefault(u, il)
        if u not in uni_tur and r.get("t"):
            _b = {"DKU": "D", "DU": "D"}
            uni_tur[u] = TUR_FULL.get(_b.get(r["t"], r["t"]), "")
    il_slugs = {}
    items = sorted(il_unis.items(), key=lambda kv: tr_sort_key(kv[0]))
    for il, uset in items:
        s = slugify(il)
        il_slugs[s] = il
        unis = sorted(uset, key=lambda u: (-uni_prog[u], u.lower()))
        dev = sum(1 for u in unis if uni_tur.get(u) == "Devlet")
        vak = sum(1 for u in unis if uni_tur.get(u, "").startswith("Vakıf"))
        cards = ""
        for u in unis:
            us = slug_by_u.get(u)
            if not us:
                continue
            ic = uni_logo_html(u, size=34, cls="uni-logo") or "🏛️"
            cards += (f'<a class="tool-btn" href="/universite/{us}.html"><span class="tb-icon">{ic}</span>'
                      f'<span class="tb-text"><b>{u}</b><span>{uni_tur.get(u,"")} · {uni_prog[u]} program</span></span></a>')
        body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / <a href="/sehirler.html">Şehirler</a> / {il}</div>
<div class="page-title"><h1>{il} Üniversiteleri {YKS_YIL}</h1><span class="sub">{len(unis)} üniversite · {dev} devlet · {vak} vakıf · YÖK Atlas {YKS_YIL}</span></div>
<div class="info-box">{il} ilinde bulunan tüm üniversitelerin bölümleri, taban puanları ve başarı sıralamaları. Bir üniversiteye tıklayarak {tr_loc_ki(il)} programların 2025 taban puanlarını inceleyebilirsiniz.</div>
{SHARE_BAR}
<div class="tool-row">{cards}</div>
<div class="notice"><b>Kaynak:</b> YÖK Atlas {YKS_YIL}. <a href="/universite-taban-puanlari.html?il={il}">{il} programlarını ara</a> · <a href="/sehirler.html">tüm şehirler</a>.</div>
"""
        html = base(f"sehir/{s}.html", f"{il} Üniversiteleri {YKS_YIL} — Taban Puanları ve Bölümler | SınavVeri",
                    f"{il} ilindeki {len(unis)} üniversitenin 2025 taban puanları, bölümleri ve başarı sıralamaları. Devlet ve vakıf üniversiteleri YÖK Atlas verisiyle.",
                    body, share=True)
        write(f"sehir/{s}.html", html)
    return il_slugs


def page_sehirler(il_slugs, programs):
    from collections import defaultdict
    cnt = defaultdict(set)
    for r in programs:
        if r.get("il") and r.get("u"):
            cnt[r["il"]].add(r["u"])
    items = sorted(il_slugs.items(), key=lambda kv: tr_sort_key(kv[1]))
    cards = ""
    for s, il in items:
        cards += (f'<a class="tool-btn" href="/sehir/{s}.html"><span class="tb-icon">📍</span>'
                  f'<span class="tb-text"><b>{il}</b><span>{len(cnt.get(il,[]))} üniversite</span></span></a>')
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / Şehirler</div>
<div class="page-title"><h1>Şehirlere Göre Üniversiteler</h1><span class="sub">{len(items)} il · YÖK Atlas {YKS_YIL}</span></div>
<input id="cSearch" type="text" placeholder="Şehir ara… (örn. ankara, izmir)" style="width:100%;max-width:480px;padding:10px 12px;border:1px solid var(--border);border-radius:9px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:14px;margin-bottom:18px">
<div class="tool-row" id="cList">{cards}</div>
<script nonce="__NONCE__">
(function(){{
  var q=document.getElementById('cSearch'),list=document.getElementById('cList');
  var items=Array.prototype.slice.call(list.children);
  q.addEventListener('input',function(){{var v=this.value.toLocaleLowerCase('tr').trim();
    items.forEach(function(a){{a.style.display=a.textContent.toLocaleLowerCase('tr').indexOf(v)>=0?'':'none';}});}});
}})();
</script>
"""
    return base("sehirler.html", "Şehirlere Göre Üniversiteler 2025 — İl İl Taban Puanları | SınavVeri",
                "Türkiye'deki 81 ilin üniversiteleri ve 2025 taban puanları. İstanbul, Ankara, İzmir ve tüm şehirlerdeki devlet ve vakıf üniversiteleri.",
                body)


# ───────────────────────── ÜCRET SAYFALARI (VAKIF) ─────────────────────────
def page_universite_ucretleri(programs, u_by_slug):
    """Vakıf üniversitelerinin yıllık öğrenim ücretleri (ücretli program aralığı) + burs."""
    from collections import defaultdict
    slug_by_u = {u: s for s, u in u_by_slug.items()}
    uc = defaultdict(list)   # uni -> [ücretler]
    burslu = defaultdict(bool)
    uni_il = {}
    for r in programs:
        u = r.get("u")
        if not u:
            continue
        t = r.get("t")
        if t not in ("V", "DU"):  # vakıf + devlet ücretli
            continue
        uni_il.setdefault(u, r.get("il", ""))
        if r.get("ucret"):
            uc[u].append(r["ucret"])
        if "Burslu" in (r.get("bs") or "") or (r.get("ucret") == 0):
            burslu[u] = True
    rows = ""
    data_unis = sorted(uc.keys(), key=lambda u: (min(uc[u]) if uc[u] else 0))
    for u in data_unis:
        vals = uc[u]
        if not vals:
            continue
        lo, hi = min(vals), max(vals)
        us = slug_by_u.get(u)
        name = f'<a href="/universite/{us}.html">{u}</a>' if us else u
        ic = uni_logo_html(u, size=26, cls="uni-logo-sm")
        rng = nf_tr(lo) + (f" – {nf_tr(hi)}" if hi != lo else "")
        rows += (f'<tr><td>{ic}{name}</td><td>{html_escape(uni_il.get(u,""))}</td>'
                 f'<td style="text-align:right">{rng} ₺</td>'
                 f'<td style="text-align:center">{"✅" if burslu.get(u) else "—"}</td></tr>')
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / Üniversite Ücretleri</div>
<div class="page-title"><h1>Vakıf Üniversitesi Ücretleri 2026</h1><span class="sub">{len(data_unis)} vakıf üniversitesi · yıllık öğrenim ücreti · YÖK Atlas</span></div>
<div class="info-box">Vakıf üniversitelerinin 2026 yıllık öğrenim ücreti aralıkları (en düşük – en yüksek program ücreti) ve burslu (tam/kısmi) program imkânı. Ücretler programa göre değişir; kesin tutar için üniversite ile teyit ediniz.</div>
<input id="ufS" type="text" placeholder="Üniversite veya şehir ara…" style="width:100%;max-width:460px;padding:9px 12px;border:1px solid var(--border);border-radius:9px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:14px;margin-bottom:14px">
<div class="data-table-wrap"><table class="data-table" id="ufT">
<thead><tr><th data-tip="Vakıf üniversitesinin resmî adı." data-type="text">Üniversite</th><th data-tip="Üniversitenin bulunduğu şehir." data-type="text">Şehir</th><th data-tip="Üniversitenin programlarındaki en düşük – en yüksek yıllık öğrenim ücreti (₺)." data-type="num" style="text-align:right">Yıllık Ücret Aralığı</th><th data-tip="Üniversitede burslu (tam/kısmi) program bulunup bulunmadığı." data-type="text" style="text-align:center">Burs</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<nav id="ufPager"></nav>
<div class="notice"><b>Kaynak:</b> YÖK Atlas {YKS_YIL} program ücretleri. <a href="/bolum-ucretleri.html">Bölüm bazında ücretler</a> · <a href="/universiteler.html">tüm üniversiteler</a>.</div>
<script nonce="__NONCE__">
(function(){{
  // Arama + TrVeri STANDART sayfalama (rule 3.17). Sıralama: base() içindeki global
  // .data-table sorter tarafından yapılır (çift-bağlama olmasın diye burada tekrarlanmaz);
  // sıralama tbody'yi yeniden dizince pager MutationObserver ile 1. sayfaya döner.
  var q=document.getElementById('ufS'),t=document.getElementById('ufT'),term='';
  function match(r){{return !term||r.textContent.toLocaleLowerCase('tr').indexOf(term)>=0;}}
  var p=window.TVPager?window.TVPager.attach({{grid:t,per:25,mount:document.getElementById('ufPager'),match:match}}):null;
  q.addEventListener('input',function(){{
    term=this.value.toLocaleLowerCase('tr').trim();
    if(p)p.reset();
    else Array.prototype.forEach.call(t.querySelectorAll('tbody tr'),function(r){{r.style.display=match(r)?'':'none';}});
  }});
}})();
</script>
"""
    return base("universite-ucretleri.html", "Vakıf Üniversitesi Ücretleri 2026 — Öğrenim Ücretleri ve Burs | SınavVeri",
                "Türkiye'deki vakıf üniversitelerinin 2026 yıllık öğrenim ücretleri ve burs imkânları. Ücret aralıklarını şehir ve üniversiteye göre karşılaştır.",
                body)


def page_bolum_ucretleri(programs, g_by_slug):
    """Bölüm gruplarına göre ücret özeti — her bölümün vakıf ücret aralığı."""
    from collections import defaultdict
    slug_by_g = {g: s for s, g in g_by_slug.items()}
    uc = defaultdict(list)
    for r in programs:
        if r.get("g") and r.get("t") in ("V", "DU") and r.get("ucret"):
            uc[r["g"]].append(r["ucret"])
    rows = ""
    for g in sorted(uc.keys(), key=lambda g: tr_sort_key(g)):
        vals = uc[g]
        if not vals:
            continue
        gs = slug_by_g.get(g)
        name = f'<a href="/bolum/{gs}.html">{g}</a>' if gs else g
        lo, hi = min(vals), max(vals)
        med = sorted(vals)[len(vals) // 2]
        rng = nf_tr(lo) + (f" – {nf_tr(hi)}" if hi != lo else "")
        rows += (f'<tr><td>{name}</td><td style="text-align:center">{len(vals)}</td>'
                 f'<td style="text-align:right">{rng} ₺</td><td style="text-align:right">{nf_tr(med)} ₺</td></tr>')
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / Bölüm Ücretleri</div>
<div class="page-title"><h1>Bölüm Bazında Üniversite Ücretleri 2026</h1><span class="sub">Vakıf programlarının yıllık öğrenim ücreti · YÖK Atlas</span></div>
<div class="info-box">Her bölüm grubunun vakıf üniversitelerindeki yıllık ücret aralığı ve medyan ücreti. Bölüme tıklayarak üniversite bazında ücret ve taban puanlarını görebilirsiniz.</div>
<input id="bfS" type="text" placeholder="Bölüm ara… (örn. tıp, hukuk, bilgisayar)" style="width:100%;max-width:460px;padding:9px 12px;border:1px solid var(--border);border-radius:9px;background:var(--bg-card-alt);color:var(--fg);font-family:inherit;font-size:14px;margin-bottom:14px">
<div class="data-table-wrap"><table class="data-table" id="bfT">
<thead><tr><th data-tip="Bölüm grubunun adı; tıklayınca üniversite bazında ücret ve taban puanlarına gider." data-type="text">Bölüm</th><th data-tip="Bu bölümün vakıf üniversitelerindeki program sayısı." data-type="num" style="text-align:center">Vakıf Prog.</th><th data-tip="Bölümün vakıf üniversitelerindeki en düşük – en yüksek yıllık öğrenim ücreti (₺)." data-type="num" style="text-align:right">Ücret Aralığı</th><th data-tip="Bölümün vakıf üniversitelerindeki ortanca (medyan) yıllık öğrenim ücreti (₺)." data-type="num" style="text-align:right">Medyan</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<nav id="bfPager"></nav>
<div class="notice"><b>Kaynak:</b> YÖK Atlas {YKS_YIL}. <a href="/universite-ucretleri.html">Üniversite bazında ücretler</a>.</div>
<script nonce="__NONCE__">
(function(){{
  // Arama + TrVeri STANDART sayfalama (rule 3.17). Sıralama: base() içindeki global
  // .data-table sorter tarafından yapılır (çift-bağlama olmasın diye burada tekrarlanmaz);
  // sıralama tbody'yi yeniden dizince pager MutationObserver ile 1. sayfaya döner.
  var q=document.getElementById('bfS'),t=document.getElementById('bfT'),term='';
  function match(r){{return !term||r.textContent.toLocaleLowerCase('tr').indexOf(term)>=0;}}
  var p=window.TVPager?window.TVPager.attach({{grid:t,per:25,mount:document.getElementById('bfPager'),match:match}}):null;
  q.addEventListener('input',function(){{
    term=this.value.toLocaleLowerCase('tr').trim();
    if(p)p.reset();
    else Array.prototype.forEach.call(t.querySelectorAll('tbody tr'),function(r){{r.style.display=match(r)?'':'none';}});
  }});
}})();
</script>
"""
    return base("bolum-ucretleri.html", "Bölüm Bazında Üniversite Ücretleri 2026 — Vakıf Öğrenim Ücretleri | SınavVeri",
                "Bölümlere göre vakıf üniversitesi yıllık öğrenim ücretleri 2026. Tıp, hukuk, mühendislik ve tüm bölümlerin ücret aralıkları ve medyanı.",
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
  var data=[],pgr=null,SV=window.SV||{};   // sayfalama: TrVeri STANDART pager.js (rule 3.17)
  var nf=function(n){return n==null?'—':n.toLocaleString('tr-TR');};
  var pf=function(n){return n==null?'—':n.toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2});};
  function el(id){return document.getElementById(id);}
  if(SV.skel)SV.skel('tbody',9,7);
  fetch('/veri/liseler.json').then(function(r){return r.json();}).then(function(j){data=j;repopulate();applyQS();repopulate();render();})
    .catch(function(){el('status').textContent='Veri yüklenemedi.';});
  var FDIMS=[
    {id:'fIl', ph:'Tüm iller', get:function(r){return r[0];}},
    {id:'fTur', ph:'Tüm türler', get:function(r){return r[3];}, lab:function(v){return TUR[v]||v;}},
    {id:'fDil', ph:'Tüm yabancı diller', get:function(r){return r[10];}}
  ];
  function passExc(r,exId){for(var i=0;i<FDIMS.length;i++){var f=FDIMS[i];if(f.id===exId)continue;var s=el(f.id);if(s&&s.value&&String(f.get(r))!==s.value)return false;}return true;}
  function repopulate(){
    FDIMS.forEach(function(f){var sel=el(f.id);if(!sel)return;var cur=sel.value;
      var cnt={};data.forEach(function(r){if(!passExc(r,f.id))return;var v=f.get(r);if(v!=null&&v!=='')cnt[v]=(cnt[v]||0)+1;});
      var ks=Object.keys(cnt).sort(function(a,b){return cnt[b]-cnt[a]||String(a).localeCompare(String(b),'tr');});
      sel.innerHTML='<option value="">'+f.ph+'</option>';var hasCur=false;
      ks.forEach(function(k){var o=document.createElement('option');o.value=k;o.textContent=(f.lab?f.lab(k):k)+' ('+cnt[k]+')';if(k===cur){o.selected=true;hasCur=true;}sel.appendChild(o);});
      if(cur&&!hasCur){var o2=document.createElement('option');o2.value=cur;o2.textContent=(f.lab?f.lab(cur):cur)+' (0)';o2.selected=true;sel.appendChild(o2);}
    });
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
      repopulate();render(true);
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
    if(reset!==false){syncQS();}
    var rows=applySort(filtered());
    el('status').textContent=rows.length.toLocaleString('tr-TR')+' lise bulundu';
    var tb=el('tbody');
    if(!rows.length){tb.innerHTML='';if(SV.empty)SV.empty('tbody',9);if(pgr)pgr.reset();return;}
    var out=[];
    rows.forEach(function(r){
      out.push('<tr><td><strong>'+(r[2]||'')+'</strong></td><td>'+(r[0]||'')+(r[1]?' / '+r[1]:'')+'</td>'+
        '<td><span class="tag tag-other">'+(TUR[r[3]]||'—')+'</span></td>'+
        '<td>'+nf(r[4])+'</td><td><strong>'+pf(r[5])+'</strong>'+(SV.spark?SV.spark([r[8],r[7],r[5]]):'')+'</td>'+
        '<td>'+pf(r[7])+'</td><td>'+pf(r[8])+'</td><td>'+(r[9]||'')+'</td>'+
        '<td>'+(r[6]==null?'—':'%'+pf(r[6]))+'</td></tr>');
    });
    tb.innerHTML=out.join('');
    if(!pgr&&window.TVPager)pgr=window.TVPager.attach({grid:tb.parentNode,per:25,mount:el('moreWrap')});
    else if(pgr)pgr.reset();
  }
  if(el('fQ'))el('fQ').addEventListener('input',function(){render(true);});
  ['fIl','fTur','fDil'].forEach(function(id){var e=el(id);if(e)e.addEventListener('change',function(){repopulate();render(true);});});
  (function(){var ths=document.querySelectorAll('.data-table thead th');ths.forEach(function(th,i){
    th.style.cursor='pointer';th.title='Sıralamak için tıklayın';
    th.addEventListener('click',function(){sortD=(sortI===i)?-sortD:1;sortI=i;
      ths.forEach(function(o){o.removeAttribute('aria-sort');var a=o.querySelector('.s-arrow');if(a)a.remove();});
      th.setAttribute('aria-sort',sortD>0?'ascending':'descending');
      var ar=document.createElement('span');ar.className='s-arrow';ar.textContent=sortD>0?' ▲':' ▼';th.appendChild(ar);render(true);});});})();
})();
</script>"""


def page_lise_taban_index(lgs, il_slugs):
    il_links = ""
    for sl, il in sorted(il_slugs.items(), key=lambda kv: kv[1].lower()):
        il_links += f'<a href="/lise/{sl}.html" style="display:inline-block;margin:2px 4px;font-size:13px">{il}</a>'
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / LGS Lise Taban Puanları</div>
<div class="page-title"><h1>LGS Lise Taban Puanları {LGS_YIL}</h1><span class="sub">81 il · 3.000+ sınavla öğrenci alan lise · Taban puanı ve yüzdelik dilim</span></div>
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
<thead><tr><th data-tip="Sınavla öğrenci alan lisenin resmî adı." data-type="text">Lise</th><th data-tip="Lisenin bulunduğu il ve ilçe." data-type="text">İl / İlçe</th><th data-tip="Lise türü: Fen, Sosyal Bilimler, Anadolu, İmam Hatip, Mesleki ve Teknik vb." data-type="text">Tür</th><th data-tip="Liseye alınacak öğrenci sayısı (kontenjan)." data-type="num">Kont.</th><th data-tip="{LGS_YIL}'te liseye yerleşen son öğrencinin LGS merkezi sınav puanı." data-type="num">{LGS_YIL} Taban</th><th data-tip="{LGS_HIST[0]} LGS taban puanı; yıllar arası değişimi görmek için." data-type="num">{LGS_HIST[0]}</th><th data-tip="{LGS_HIST[1]} LGS taban puanı; yıllar arası değişimi görmek için." data-type="num">{LGS_HIST[1]}</th><th data-tip="{LGS_YIL} tabanının bir önceki yıla göre değişimi (↑ yükseldi, ↓ düştü, → aynı)." data-type="text">Trend</th><th data-tip="Yerleşen son öğrencinin LGS yüzdelik dilimi. Küçük yüzdelik = daha başarılı." data-type="num">Yüzdelik</th></tr></thead>
<tbody id="tbody"></tbody>
</table>
</div>
<nav id="moreWrap"></nav>
<div class="notice"><b>Kaynak:</b> MEB {LGS_YIL} LGS merkezi yerleştirme verileri. Taban puanı ve yüzdelik dilim,
o liseye <b>en son yerleşen</b> öğrencinin değeridir. Yalnızca <b>sınavla öğrenci alan</b> liseler listelenir.
Resmî kayıt için <a href="https://www.meb.gov.tr" target="_blank" rel="noopener">MEB</a>/e-Okul esastır.</div>
<div class="section" style="margin-top:24px"><h2>İllere Göre Lise Taban Puanları</h2>
<div class="section-sub">İl sayfasında o ilin tüm liseleri taban puanına göre sıralı.</div>
<div style="line-height:2">""" + il_links + """</div></div>
""" + LISE_SEARCH_JS
    return base("lise-taban-puanlari.html", f"LGS Lise Taban Puanları {LGS_YIL} — İl İl Tüm Liseler | SınavVeri",
                f"{LGS_YIL} LGS lise taban puanları ve yüzdelik dilimleri. 81 ilde 3000+ Fen, Anadolu, İmam Hatip ve Meslek lisesi. İl ve türe göre filtrele.",
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
        summary = (f"<strong>{il}</strong> ilinde {LGS_YIL} LGS ile öğrenci alan <strong>{len(recs)}</strong> lise listelenmiştir"
                   + (f"; taban puanları <strong>{fmt_puan(min(tabans))}</strong> – <strong>{fmt_puan(max(tabans))}</strong> aralığında." if tabans else "."))
        body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / <a href="/lise-taban-puanlari.html">LGS Liseler</a> / {il}</div>
<div class="page-title"><h1>{il} Liseleri Taban Puanları (LGS · 3 Yıllık Trend)</h1><span class="sub">{len(recs)} sınavla öğrenci alan lise · MEB resmî · 2023-2024-2025 taban + yüzdelik dilim</span></div>
<div class="info-box">{summary} 2024/2023 sütunları geçmiş yıl tabanı, Trend sütunu 2025'in bir önceki yıla göre değişimidir. Tablo 2025 tabanına göre sıralıdır; başlığa tıklayarak yeniden sıralayabilirsiniz.</div>
{SHARE_BAR}
<div class="data-table-wrap">
<table class="data-table" data-tvpager>
<thead><tr><th data-tip="Sınavla öğrenci alan lisenin resmî adı." data-type="text">Lise</th><th data-tip="Lisenin bulunduğu ilçe." data-type="text">İlçe</th><th data-tip="Lise türü: Fen, Sosyal Bilimler, Anadolu, İmam Hatip, Mesleki ve Teknik vb." data-type="text">Tür</th><th data-tip="Liseye alınacak öğrenci sayısı (kontenjan)." data-type="num">Kont.</th><th data-tip="{LGS_YIL}'te liseye yerleşen son öğrencinin LGS merkezi sınav puanı." data-type="num">{LGS_YIL} Taban</th><th data-tip="{LGS_HIST[0]} LGS taban puanı; yıllar arası değişimi görmek için." data-type="num">{LGS_HIST[0]}</th><th data-tip="{LGS_HIST[1]} LGS taban puanı; yıllar arası değişimi görmek için." data-type="num">{LGS_HIST[1]}</th><th data-tip="{LGS_YIL} tabanının bir önceki yıla göre değişimi (↑ yükseldi, ↓ düştü, → aynı)." data-type="text">Trend</th><th data-tip="Yerleşen son öğrencinin LGS yüzdelik dilimi. Küçük yüzdelik = daha başarılı." data-type="num">Yüzdelik</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</div>
<div class="notice"><b>Kaynak:</b> MEB {LGS_YIL} LGS merkezi yerleştirme verileri. Yalnızca sınavla öğrenci alan liseler.
Tüm Türkiye: <a href="/lise-taban-puanlari.html">LGS lise taban puanları</a> · <a href="/lgs-puan-hesaplama.html">LGS puan hesaplama</a>.</div>
"""
        html = base(f"lise/{sl}.html", f"{il} Liseleri Taban Puanları {LGS_YIL} LGS — Yüzdelik Dilim | SınavVeri",
                    f"{il} {LGS_YIL} LGS lise taban puanları ve yüzdelik dilimleri. {len(recs)} sınavla öğrenci alan Fen, Anadolu, İmam Hatip ve Meslek lisesi. MEB verisi.",
                    body, share=True)
        write(f"lise/{sl}.html", html)
    return slugs


# ───────────────────────── TABAN PUANLARI HUB ─────────────────────────
def page_taban_hub():
    live = [
        ("/universite-taban-puanlari.html", "🎓", "Üniversite Taban Puanları", f"YKS · 21.602 lisans/önlisans programı · YÖK Atlas {YKS_YIL}"),
        ("/lise-taban-puanlari.html", "🏫", "LGS Lise Taban Puanları", f"81 il · 3.000+ sınavla öğrenci alan lise · MEB {LGS_YIL}"),
        ("/tus-taban-puanlari.html", "🩺", "TUS Taban Puanları", "Tıpta uzmanlık · kurum × dal · ÖSYM resmî 2025"),
        ("/dus-taban-puanlari.html", "🦷", "DUS Taban Puanları", "Diş hekimliği uzmanlık · kurum × dal · ÖSYM resmî 2025"),
        ("/dgs-taban-puanlari.html", "📈", "DGS Taban Puanları", "Dikey geçiş · 7.000+ üniversite programı · ÖSYM resmî 2025"),
        ("/kpss-atama-taban-puanlari.html", "🏛️", "KPSS Atama Taban Puanları", "Kadro bazında atama puanları · ÖSYM resmî 2025"),
        ("/bolumler.html", "📘", "Bölümlere Göre", "600+ bölüm grubu taban puanı"),
        ("/universiteler.html", "🏫", "Üniversitelere Göre", "227 üniversite · künye, analiz, logo"),
        ("/sehirler.html", "📍", "Şehirlere Göre", "81 il · ildeki üniversiteler"),
        ("/karsilastir.html", "⚖️", "Karşılaştır", "2-4 programı yan yana kıyasla"),
        ("/kpss-tercih-raporu.html", "📄", "Kişiye Özel KPSS Tercih Raporu", "Veri-temelli sıralı liste · rehber hocayla hazırlanır"),
        ("/universite-ucretleri.html", "💰", "Vakıf Üniversite Ücretleri", "Yıllık öğrenim ücreti & burs"),
        ("/bolum-ucretleri.html", "🧾", "Bölüm Ücretleri", "Bölüm bazında vakıf ücretleri"),
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
    return base("taban-puanlari.html", "Taban Puanları — Üniversite, LGS, TUS, DUS, DGS, KPSS | SınavVeri",
                "2025 taban puanları merkezi: üniversite (YKS), LGS lise, TUS, DUS, DGS ve KPSS atama taban puanları ve başarı sıralamaları tek çatıda.",
                body)


# ───────────────────────── ÖSYM RESMİ TABAN PUANLARI (TUS/DUS/DGS/KPSS) ─────────────────────────
# Kaynak: ÖSYM 'En Küçük ve En Büyük Puanlar' resmî PDF'leri (dokuman.osym.gov.tr).
GENERIC_SEARCH_JS = r"""<script nonce="__NONCE__">
(function(){
  var CFG=__CFG__, NCOL=CFG.cols.length, SV=window.SV||{};
  var data=[],pgr=null;   // sayfalama: TrVeri STANDART pager.js (rule 3.17)
  function el(id){return document.getElementById(id);}
  var nf=function(n){return n==null?'—':Number(n).toLocaleString('tr-TR');};
  var pf=function(n){return n==null?'—':Number(n).toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2});};
  if(SV.skel)SV.skel('tbody',NCOL,7);
  el('status').textContent='Veriler yükleniyor…';
  fetch(CFG.file).then(function(r){return r.json();}).then(function(j){data=j;initFilters();applyQS();render();})
    .catch(function(){el('status').textContent='Veri yüklenemedi.';});
  function initFilters(){  // cascading: her dropdown diğer seçili dropdownlara göre yeniden dolar
    CFG.filters.forEach(function(f){
      var sel=el('fil'+f[1]);if(!sel)return;var cur=sel.value;
      var cnt={};data.forEach(function(r){
        for(var k=0;k<CFG.filters.length;k++){var g=CFG.filters[k];if(g[1]===f[1])continue;var s=el('fil'+g[1]);if(s&&s.value&&String(r[g[0]])!==s.value)return;}
        var v=r[f[0]];if(v)cnt[v]=(cnt[v]||0)+1;
      });
      var ks=Object.keys(cnt).sort(function(a,b){return cnt[b]-cnt[a]||String(a).localeCompare(String(b),'tr');});
      sel.innerHTML='<option value="">'+(f[2]||'')+' (tümü)</option>';var hc=false;
      ks.forEach(function(k){var o=document.createElement('option');o.value=k;o.textContent=k+' ('+cnt[k]+')';if(k===cur){o.selected=true;hc=true;}sel.appendChild(o);});
      if(cur&&!hc){var o2=document.createElement('option');o2.value=cur;o2.textContent=cur+' (0)';o2.selected=true;sel.appendChild(o2);}
    });
  }
  function applyQS(){
    var qs=SV.qsGet?SV.qsGet():{};
    if(qs.q!=null)el('fQ').value=qs.q;
    CFG.filters.forEach(function(f){var s=el('fil'+f[1]);if(s&&qs['f'+f[1]]!=null)s.value=qs['f'+f[1]];});
    initFilters();
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
      initFilters();render(true);
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
    if(reset!==false){syncQS();}
    var rows=applySort(filtered());
    el('status').textContent=rows.length.toLocaleString('tr-TR')+' sonuç bulundu';
    var tb=el('tbody');
    if(!rows.length){tb.innerHTML='';if(SV.empty)SV.empty('tbody',NCOL);if(pgr)pgr.reset();return;}
    var out=[];
    rows.forEach(function(r){
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
      out.push('<tr>'+html+'</tr>');
    });
    tb.innerHTML=out.join('');
    if(!pgr&&window.TVPager)pgr=window.TVPager.attach({grid:tb.parentNode,per:25,mount:el('moreWrap')});
    else if(pgr)pgr.reset();
  }
  el('fQ').addEventListener('input',function(){render(true);});
  CFG.filters.forEach(function(f){var s=el('fil'+f[1]);if(s)s.addEventListener('change',function(){initFilters();render(true);});});
  (function(){
    var ths=document.querySelectorAll('.data-table thead th');
    ths.forEach(function(th,i){
      th.style.cursor='pointer'; th.title='Sıralamak için tıklayın';
      th.addEventListener('click',function(){
        sortD=(sortI===i)?-sortD:1; sortI=i;
        ths.forEach(function(o){o.removeAttribute('aria-sort');var a=o.querySelector('.s-arrow');if(a)a.remove();});
        th.setAttribute('aria-sort',sortD>0?'ascending':'descending');
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
    thead = "".join(th_html(c[1]) for c in cols)
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
<nav id="moreWrap"></nav>
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
        "tus-taban-puanlari.html", f"TUS Taban Puanları {osym_yil('tus')-2}-{osym_yil('tus')} — Kurum ve Uzmanlık Dalı | SınavVeri",
        f"TUS taban ve tavan puanları ({osym_yil('tus')}/1) + {osym_yil('tus')-1} ve {osym_yil('tus')-2} karşılaştırması, her hastane/üniversite ve uzmanlık dalı için. ÖSYM resmî, 3 yıllık trend. Kardiyoloji, radyoloji, genel cerrahi ve tüm branşlar.",
        "TUS Taban Puanları (3 Yıllık Trend)", f"Tıpta Uzmanlık · kurum × uzmanlık dalı · ÖSYM resmî yerleştirme {osym_yil('tus')-2}→{osym_yil('tus')}",
        "/veri/tus.json",
        [(1, "Uzmanlık Dalı", "b"), (0, "Kurum", "t"), (3, "Kont.", "n"),
         (4, f"{osym_yil('tus')} Taban", "p"), (6, f"{osym_yil('tus')-1}", "pv"), (7, f"{osym_yil('tus')-2}", "pv"), (8, "Trend", "t"), (5, "Tavan", "pv")],
        [(9, "Uzmanlık Dalı"), (2, "Kontenjan Türü")], [0, 1],
        "TUS'ta her kurum ve uzmanlık dalı için ÖSYM'nin açıkladığı en düşük (taban) ve en yüksek (tavan) puanlar, "
        f"<b>son 3 yılın ({osym_yil('tus')-2}-{osym_yil('tus')-1}-{osym_yil('tus')}) yerleştirme karşılaştırmasıyla</b>. Trend sütunu {osym_yil('tus')} tabanının bir önceki yıla göre değişimini gösterir. "
        "Dal adının yanındaki parantez <b>kadro türüdür</b> (ÖSYM kontenjan tablosu): "
        "<b>ÜNİ</b> üniversite, <b>SBA</b> Sağlık Bakanlığı Adına, <b>EAH</b> eğitim-araştırma hastanesi, <b>MSB</b> Milli Savunma, "
        "<b>MAP</b> Misafir Askeri Personel, <b>KKTC</b> Kıbrıs, <b>ADL</b> Adalet Bakanlığı, <b>YBU</b> yabancı uyruklu. "
        "Aynı kurum+dalda birden çok kadro ayrı satırdır. Dal veya kurum/şehir arayın, uzmanlık dalına göre filtreleyin.",
        f"ÖSYM {osym_yil('tus')-2}, {osym_yil('tus')-1} ve {osym_yil('tus')} TUS Yerleştirme 'En Küçük ve En Büyük Puanlar' resmî yayınları (dokuman.osym.gov.tr).",
        ph="Dal / kurum / şehir ara…", hub_html=hub_links_html("tus", hubs), spark=[7, 6, 4])


def page_dus(hubs=None):
    if not (ROOT / "veri" / "dus.json").exists():
        return None
    return minmax_page(
        "dus-taban-puanlari.html", f"DUS Taban Puanları {osym_yil('dus')-2}-{osym_yil('dus')} — Kurum ve Uzmanlık Dalı | SınavVeri",
        f"DUS taban ve tavan puanları ({osym_yil('dus')}/1) + {osym_yil('dus')-1} ve {osym_yil('dus')-2} karşılaştırması, her diş hekimliği fakültesi ve uzmanlık dalı için. ÖSYM resmî, 3 yıllık trend.",
        "DUS Taban Puanları (3 Yıllık Trend)", f"Diş Hekimliği Uzmanlık · kurum × dal · ÖSYM resmî 1. dönem {osym_yil('dus')-2}→{osym_yil('dus')}",
        "/veri/dus.json",
        [(1, "Uzmanlık Dalı", "b"), (0, "Kurum", "t"), (3, "Kont.", "n"),
         (4, f"{osym_yil('dus')} Taban", "p"), (6, f"{osym_yil('dus')-1}", "pv"), (7, f"{osym_yil('dus')-2}", "pv"), (8, "Trend", "t"), (5, "Tavan", "pv")],
        [(9, "Uzmanlık Dalı")], [0, 1],
        "DUS'ta her kurum ve diş hekimliği uzmanlık dalı için ÖSYM'nin açıkladığı taban ve tavan puanlar, "
        f"<b>son 3 yılın ({osym_yil('dus')-2}-{osym_yil('dus')-1}-{osym_yil('dus')}) karşılaştırmasıyla</b>. Trend sütunu {osym_yil('dus')} tabanının bir önceki yıla göre değişimini gösterir.",
        f"ÖSYM {osym_yil('dus')-2}, {osym_yil('dus')-1} ve {osym_yil('dus')} DUS 'En Küçük ve En Büyük Puanlar' resmî yayınları (dokuman.osym.gov.tr).",
        ph="Dal / kurum ara…", hub_html=hub_links_html("dus", hubs), spark=[7, 6, 4])


def page_dgs_taban(hubs=None):
    if not (ROOT / "veri" / "dgs.json").exists():
        return None
    return minmax_page(
        "dgs-taban-puanlari.html", f"DGS Taban Puanları {osym_yil('dgs')-2}-{osym_yil('dgs')} — Üniversite ve Program | SınavVeri",
        f"DGS taban ve tavan puanları (2025) + {osym_yil('dgs')-1} ve {osym_yil('dgs')-2} karşılaştırması, her üniversite programı için. Dikey geçiş ÖSYM resmî verisi, 7000+ program, 3 yıllık trend.",
        "DGS Taban Puanları (3 Yıllık Trend)", f"Dikey Geçiş · üniversite × program · ÖSYM resmî {osym_yil('dgs')-2}→{osym_yil('dgs')}",
        "/veri/dgs.json",
        [(1, "Program", "b"), (0, "Üniversite", "t"), (2, "Kont.", "n"),
         (3, f"{osym_yil('dgs')} Taban", "p"), (5, f"{osym_yil('dgs')-1}", "pv"), (6, f"{osym_yil('dgs')-2}", "pv"), (7, "Trend", "t"), (4, "Tavan", "pv")],
        [], [0, 1],
        "DGS ile ön lisanstan lisansa geçişte her üniversite programının ÖSYM'nin açıkladığı taban ve tavan puanları, "
        f"<b>son 3 yılın ({osym_yil('dgs')-2}-{osym_yil('dgs')-1}-{osym_yil('dgs')}) karşılaştırmasıyla</b>. Trend sütunu {osym_yil('dgs')} tabanının bir önceki yıla göre değişimini gösterir "
        "(↑ yükseliş, ↓ düşüş). Program kodu yıllar arası eşleştirilir; yeni açılan programlarda geçmiş boştur. "
        "Program veya üniversite adı arayın. DGS net hesaplama için <a href='/dgs-puan-hesaplama.html'>DGS puan hesaplama</a>.",
        f"ÖSYM {osym_yil('dgs')-2}, {osym_yil('dgs')-1} ve {osym_yil('dgs')} 'DGS Yerleştirme Sonuçlarına İlişkin En Küçük ve En Büyük Puanlar' resmî yayınları (dokuman.osym.gov.tr).",
        ph="Program / üniversite ara…", hub_html=hub_links_html("dgs", hubs), spark=[6, 5, 3])


def page_kpss_atama(hubs=None):
    if not (ROOT / "veri" / "kpss.json").exists():
        return None
    return minmax_page(
        "kpss-atama-taban-puanlari.html", f"KPSS Atama Taban Puanları {osym_yil('kpss')} — Kadro Bazında | SınavVeri",
        f"{osym_yil('kpss')} KPSS atama taban ve tavan puanları, kadro/pozisyon bazında. ÖSYM resmî yerleştirme verisi (KPSS-{osym_yil('kpss')}/1 ve Sağlık Bakanlığı).",
        f"KPSS Atama Taban Puanları {osym_yil('kpss')}", f"Kadro/pozisyon bazında atama puanları · ÖSYM resmî · {osym_yil('kpss')} tüm yerleştirmeler",
        "/veri/kpss.json",
        [(1, "Kadro", "b"), (0, "Kurum", "t"), (2, "İl", "t"), (3, "Düzey", "t"), (4, "Dönem", "t"),
         (6, "Taban", "p"), (8, "Önceki Yıl", "pv"), (9, "Trend", "t"), (7, "Tavan", "pv")],
        [(2, "İl"), (3, "Düzey"), (4, "Dönem")], [0, 1],
        "KPSS ile atanılan her kadro/pozisyon için ÖSYM'nin açıkladığı taban ve tavan puanlar. "
        "Kadro veya kurum arayın; il, öğrenim düzeyi ve yerleştirme dönemine göre filtreleyin. "
        f"<b>Kapsam:</b> {kpss_kapsam_metni()} "
        f"<b>{osym_yil('kpss')-1}</b> sütunu aynı kurum+il+kadronun bir önceki yıl (aynı tür yerleştirme) tabanıdır; Trend değişimi gösterir. "
        "KPSS atamaları tek-seferlik ilanlar olduğundan eşleşme kısmidir; bir dönemin karşılığı "
        "önceki yılda hiç açılmamış olabilir. "
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
def kpss_kapsam_metni():
    """KPSS kapsam cümlesi veriden türetilir — '2026/1–2026/5' gibi SABİT aralık yazmak,
    o yıl henüz tek yerleştirme yapıldığında yanlış bilgi veriyordu."""
    y = osym_yil("kpss")
    try:
        kayit = json.loads((ROOT / "veri" / "kpss.json").read_text(encoding="utf-8"))
        donemler = sorted({r[4] for r in kayit if len(r) > 4 and r[4]})
    except Exception:
        donemler = []
    if not donemler:
        return f"{y} yılı KPSS yerleştirmeleri."
    if len(donemler) == 1:
        return f"{y} yılı KPSS yerleştirmesi ({donemler[0]})."
    return f"{y} yılının tüm KPSS yerleştirmeleri ({' · '.join(donemler)})."


def hub_cols(exam):
    """Hub tablosu kolonları — yıl etiketleri o sınavın veri yılından türetilir.
    (tp24/tp23 alan adları TARİHSEL; anlamı KONUMSALDIR: cari-1, cari-2.)"""
    y = osym_yil(exam)
    puan = [(f"{y} Taban", "tp", "p"), (f"{y-1}", "tp24", "p"), (f"{y-2}", "tp23", "p"),
            ("Trend", None, "trend"), ("Tavan", "tavan", "p")]
    if exam == "kpss":
        # KPSS tablosu cari + önceki yılın yerleştirmelerini birlikte içerir → satırların
        # yılı farklı. Bu yüzden sütun sabit yıl DEĞİL; hangi dönem olduğu "Dönem" sütununda.
        return ([("Kurum", "kurum", "t"), ("İl", "il", "t"), ("Düzey", "duzey", "t"),
                 ("Dönem", "donem", "t"), ("Kont.", "kont", "n"),
                 ("Taban", "tp", "p"), ("Önceki Yıl", "tp24", "p"),
                 ("Trend", None, "trend"), ("Tavan", "tavan", "p")])
    if exam == "dgs":
        return [("Üniversite", "uni", "t"), ("Kont.", "kont", "n")] + puan
    return [("Kurum", "kurum", "t"), ("Kadro", "kadro", "t"), ("Tür", "tur", "t"),
            ("Kont.", "kont", "n")] + puan


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
        cols = hub_cols(exam)
        links = []
        for s, g in slugmap.items():
            recs = groups[g]
            if len(recs) < mink:
                continue
            recs = sorted(recs, key=lambda r: (r.get("tp") is None, -(r.get("tp") or 0)))
            thead = "".join(th_html(h) for h, _, _ in cols)
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
<div class="page-title"><h1>{g} {EX} Taban Puanları {osym_yil(exam)}</h1><span class="sub">{sinav} · {len(recs)} {'kadro' if exam=='kpss' else 'kurum'} · ÖSYM resmî{'' if exam=='kpss' else ' · 3 yıllık trend (2023-2025)'}</span></div>
<div class="info-box">{ozet} Tablo 2025 tabanına göre yüksekten düşüğe sıralıdır.{'' if exam=='kpss' else ' Trend sütunu 2025 tabanının bir önceki yıla göre değişimini gösterir (↑/↓).'}</div>
<div class="data-table-wrap">
<table class="data-table" data-tvpager><thead><tr>{thead}</tr></thead><tbody>{rws}</tbody></table>
</div>
<div class="notice"><b>Kaynak:</b> ÖSYM resmî 'En Küçük ve En Büyük Puanlar' yayını (dokuman.osym.gov.tr).
Tüm {EX} verisi için <a href="/{main}">{EX} taban puanları arama</a> · <a href="/taban-puanlari.html">tüm taban puanları</a>.</div>
"""
            title = f"{g} {EX} Taban Puanları {osym_yil(exam)} — Kurum Bazında {'ve 3 Yıllık Trend ' if exam!='kpss' else ''}| SınavVeri"
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
    items = " · ".join(f'<a href="/{sub}/{s}.html">{g}</a> <span style="color:var(--fg-faded)">({n})</span>'
                       for s, g, n in links)
    extra = ""
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
<div class="page-title"><h1>Kontenjan ve Doluluk Analizi {YKS_YIL}</h1><span class="sub">YÖK Atlas {YKS_YIL} · {fmt_sira(len(valid))} program · Doluluk = yerleşen ÷ kontenjan</span></div>
<div class="spotlight">
  <div class="spot-card"><div class="sc-label">Toplam Kontenjan</div><div class="sc-exam">{fmt_sira(tk)}</div></div>
  <div class="spot-card"><div class="sc-label">Toplam Yerleşen</div><div class="sc-exam">{fmt_sira(ty)}</div></div>
  <div class="spot-card"><div class="sc-label">Genel Doluluk</div><div class="sc-exam">%{tp}</div></div>
  <div class="spot-card"><div class="sc-label">Boş Kontenjan</div><div class="sc-exam">{fmt_sira(tk-ty)}</div></div>
</div>
{chart}
<div class="section"><h2>Türe ve Düzeye Göre Doluluk</h2>
<div class="data-table-wrap"><table class="data-table">
<thead><tr><th data-tip="Üniversite türü veya öğrenim düzeyi kategorisi." data-type="text">Kategori</th><th data-tip="Kategorideki toplam kontenjan." data-type="num">Kontenjan</th><th data-tip="Kategoriye yerleşen toplam öğrenci sayısı." data-type="num">Yerleşen</th><th data-tip="Doluluk = yerleşen ÷ kontenjan." data-type="num">Doluluk</th></tr></thead>
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
<thead><tr><th data-tip="Programın adı ve bağlı olduğu üniversite." data-type="text">Program / Üniversite</th><th data-tip="Programın bulunduğu il." data-type="text">İl</th><th data-tip="Üniversite türü: Devlet, Vakıf, KKTC veya özel kontenjan türü." data-type="text">Tür</th><th data-tip="Öğrenim düzeyi: Lisans (4 yıl) veya Önlisans (2 yıl)." data-type="text">Düzey</th><th data-tip="2025 genel kontenjanı: programa alınacak öğrenci sayısı." data-type="num">Kont.</th><th data-tip="Kontenjana yerleşen öğrenci sayısı." data-type="num">Yerleşen</th><th data-tip="Dolmayan kontenjan (kontenjan − yerleşen)." data-type="num">Boş</th><th data-tip="Doluluk = yerleşen ÷ kontenjan." data-type="num">Doluluk</th></tr></thead>
<tbody id="bbody"></tbody></table></div>
<nav id="bPager"></nav></div>
<script nonce="__NONCE__">
(function(){{
  var TUR={{D:'Devlet',V:'Özel (Vakıf)',K:'KKTC',DK:'Devlet (KKTC Kampüs)',DU:'Devlet (Ücretli)',DKU:'Devlet (KKTC Uyruklu)','?':'—'}},DUZ={{L:'Lisans',O:'Önlisans'}};
  var data=[],pgr=null,sortI=null,sortD=1;   // sayfalama: TrVeri STANDART pager.js (rule 3.17)
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
    el('bstatus').textContent=rows.length.toLocaleString('tr-TR')+' boş kalan program bulundu';
    var tb=el('bbody'),out=[];
    rows.forEach(function(r){{
      out.push('<tr><td><strong>'+(r[1]||'')+'</strong><br><small>'+(r[0]||'')+'</small></td>'+
        '<td>'+(r[2]||'—')+'</td><td>'+(TUR[r[3]]||'—')+'</td><td>'+(DUZ[r[4]]||'—')+'</td>'+
        '<td>'+nf(r[5])+'</td><td>'+nf(r[6])+'</td><td><strong>'+nf(r[5]-r[6])+'</strong></td>'+
        '<td><span class="tag tag-other">%'+r[7]+'</span></td></tr>');
    }});
    tb.innerHTML=out.join('');
    if(!pgr&&window.TVPager)pgr=window.TVPager.attach({{grid:tb.parentNode,per:25,mount:el('bPager')}});
    else if(pgr)pgr.reset();
  }}
  function reset(){{render();}}
  fetch('/veri/doluluk_bos.json').then(function(r){{return r.json();}}).then(function(j){{
    data=j;
    var set={{}};data.forEach(function(r){{if(r[2])set[r[2]]=1;}});
    var sel=el('bil');Object.keys(set).sort(function(a,b){{return a.localeCompare(b,'tr');}})
      .forEach(function(i){{var o=document.createElement('option');o.value=i;o.textContent=i;sel.appendChild(o);}});
    render();
  }}).catch(function(){{el('bstatus').textContent='Veri yüklenemedi.';}});
  ['bq','bil','btur','bduz'].forEach(function(id){{el(id).addEventListener('input',reset);el(id).addEventListener('change',reset);}});
  var hs=document.querySelectorAll('.section table[data-live] thead th');
  hs.forEach(function(th,i){{th.style.cursor='pointer';th.title='Sıralamak için tıklayın';
    th.addEventListener('click',function(){{sortD=(sortI===i)?-sortD:1;sortI=i;
      hs.forEach(function(o){{o.removeAttribute('aria-sort');var a=o.querySelector('.s-arrow');if(a)a.remove();}});
      th.setAttribute('aria-sort',sortD>0?'ascending':'descending');
      var ar=document.createElement('span');ar.className='s-arrow';ar.textContent=sortD>0?' ▲':' ▼';th.appendChild(ar);reset();}});}});
}})();
</script>

<div class="section"><h2>En Düşük Doluluklu Bölümler</h2>
<div class="section-sub">En az 30 programı olan bölüm grupları · doluluk artan sıra</div>
<div class="data-table-wrap"><table class="data-table">
<thead><tr><th data-tip="Bölüm grubu adı." data-type="text">Bölüm</th><th data-tip="Bu bölüm grubundaki program sayısı." data-type="num">Program</th><th data-tip="Bölüm grubunun toplam kontenjanı." data-type="num">Kontenjan</th><th data-tip="Doluluk = yerleşen ÷ kontenjan." data-type="num">Doluluk</th></tr></thead>
<tbody>{grp_table(bos)}</tbody></table></div></div>

<div class="section"><h2>En Yüksek Doluluklu Bölümler</h2>
<div class="data-table-wrap"><table class="data-table">
<thead><tr><th data-tip="Bölüm grubu adı." data-type="text">Bölüm</th><th data-tip="Bu bölüm grubundaki program sayısı." data-type="num">Program</th><th data-tip="Bölüm grubunun toplam kontenjanı." data-type="num">Kontenjan</th><th data-tip="Doluluk = yerleşen ÷ kontenjan." data-type="num">Doluluk</th></tr></thead>
<tbody>{grp_table(dolu)}</tbody></table></div></div>

<div class="notice"><b>Kaynak:</b> YÖK Atlas {YKS_YIL}. Doluluk, genel kontenjana yerleşen sayısının oranıdır; ek yerleştirme/dikey
geçiş hariçtir. Düşük doluluk talebin az olduğunu, yüksek doluluk programın dolduğunu gösterir.</div>
"""
    return base("doluluk.html", f"Üniversite Kontenjan ve Doluluk Analizi {YKS_YIL} | SınavVeri",
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
    <div class="calc-hint">Doğru ve yanlış sayılarını gir; net hesaplanır.</div>
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
    """GEO/SEO: gerçek veriden türetilmiş sıralama listeleri (tab'lı) + ItemList şeması (AI alıntı)."""
    PTL = {"SAY": "Sayısal", "EA": "Eşit Ağırlık", "SÖZ": "Sözel", "DİL": "Dil"}
    item_list = []
    tabs = []  # (id, label, table_html)
    for pt in ("SAY", "EA", "SÖZ", "DİL"):
        rows = sorted([r for r in programs if r.get("p") == pt and r.get("tp")], key=lambda r: -r["tp"])[:25]
        if not rows:
            continue
        trs = ""
        for i, r in enumerate(rows, 1):
            trs += (f"<tr><td>{i}</td><td><strong>{r.get('b') or ''}</strong><br><small>{r.get('u') or ''}</small></td>"
                    f"<td>{r.get('il') or '—'}</td><td><strong>{fmt_puan(r.get('tp'))}</strong></td><td>{fmt_sira(r.get('sira'))}</td></tr>")
            if pt == "SAY" and i <= 10:
                item_list.append({"@type": "ListItem", "position": i, "name": f"{r.get('b')} — {r.get('u')}"})
        table = ('<div class="data-table-wrap"><table class="data-table"><thead><tr><th data-nosort data-tip="Listedeki sıra numarası.">#</th>'
                 '<th data-tip="Programın adı ve bağlı olduğu üniversite." data-type="text">Program / Üniversite</th>'
                 '<th data-tip="Programın bulunduğu il." data-type="text">İl</th>'
                 '<th data-tip="Programa en son yerleşen adayın 2025 taban puanı." data-type="num">Taban</th>'
                 '<th data-tip="En son yerleşen adayın 2025 başarı sırası." data-type="num">Sıra</th></tr></thead>'
                 f'<tbody>{trs}</tbody></table></div>')
        tabs.append((pt.lower().replace("ö", "o").replace("i̇", "i"), f"En Yüksek Taban — {PTL[pt]}", table))
    konts = sorted([r for r in programs if r.get("kont")], key=lambda r: -r["kont"])[:25]
    if konts:
        trs = "".join(f"<tr><td>{i}</td><td><strong>{r.get('b') or ''}</strong><br><small>{r.get('u') or ''}</small></td>"
                      f"<td>{r.get('il') or '—'}</td><td><strong>{fmt_sira(r.get('kont'))}</strong></td><td>{fmt_puan(r.get('tp'))}</td></tr>"
                      for i, r in enumerate(konts, 1))
        tabs.append(("kont", "En Çok Kontenjan",
                     '<div class="data-table-wrap"><table class="data-table"><thead><tr><th data-nosort data-tip="Listedeki sıra numarası.">#</th>'
                     '<th data-tip="Programın adı ve bağlı olduğu üniversite." data-type="text">Program / Üniversite</th>'
                     '<th data-tip="Programın bulunduğu il." data-type="text">İl</th>'
                     '<th data-tip="2025 genel kontenjanı: programa alınacak öğrenci sayısı." data-type="num">Kontenjan</th>'
                     '<th data-tip="Programa en son yerleşen adayın 2025 taban puanı." data-type="num">Taban</th></tr></thead>'
                     f'<tbody>{trs}</tbody></table></div>'))
    SHORT = {"SAY": "Sayısal", "EA": "Eşit Ağırlık", "SÖZ": "Sözel", "DİL": "Dil"}
    btns = "".join(
        f'<button type="button" class="ltab-btn{" active" if n == 0 else ""}" data-tab="{tid}">{SHORT.get(tid.upper(), lbl.split("— ")[-1])}</button>'
        for n, (tid, lbl, _t) in enumerate(tabs))
    panels = "".join(
        f'<div class="ltab-panel{" active" if n == 0 else ""}" id="lt-{tid}"><h2 style="font-size:17px;color:var(--accent);margin:4px 0 10px">{lbl} (2025, ilk 25)</h2>{table}</div>'
        for n, (tid, lbl, table) in enumerate(tabs))
    body = f"""
<div class="crumb"><a href="/index.html">Ana Sayfa</a> / Listeler ve Sıralamalar</div>
<div class="page-title"><h1>Üniversite Listeleri ve Sıralamalar {YKS_YIL}</h1><span class="sub">YÖK Atlas {YKS_YIL} gerçek yerleştirme verisinden · en yüksek taban, en çok kontenjan</span></div>
<div class="info-box">Puan türüne göre sekmelerden öne çıkan programları gör. Tüm taban puanları için
<a href="/universite-taban-puanlari.html">üniversite taban puanları</a>, puanına göre bölüm için
<a href="/tercih-robotu.html">tercih robotu</a>.</div>
<div class="ltabs">{btns}</div>
{panels}
<div class="notice"><b>Kaynak:</b> YÖK Atlas {YKS_KILAVUZ_YIL} Tercih Kılavuzu yerleştirme verisi. Sıralamalar {YKS_YIL} taban puanı / kontenjanına göredir.</div>
<script nonce="__NONCE__">
(function(){{
  var btns=document.querySelectorAll('.ltab-btn');
  btns.forEach(function(b){{b.addEventListener('click',function(){{
    var id=b.getAttribute('data-tab');
    btns.forEach(function(x){{x.classList.toggle('active',x===b);}});
    document.querySelectorAll('.ltab-panel').forEach(function(p){{p.classList.toggle('active',p.id==='lt-'+id);}});
  }});}});
}})();
</script>
"""
    extra = [breadcrumb_ld([("Ana Sayfa", "index.html"), ("Listeler ve Sıralamalar", None)])]
    if item_list:
        extra.append({"@type": "ItemList", "name": "En Yüksek Taban Puanlı Sayısal Programlar 2025", "itemListElement": item_list})
    return base("listeler.html", f"Üniversite Listeleri ve Sıralamalar {YKS_YIL} — En Yüksek Taban, En Çok Kontenjan | SınavVeri",
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
# AboutPage JSON-LD (SEO) — mevcut Organization/WebPage @graph LD'sine EK ayrı blok.
# ld+json bir veri bloğudur (yürütülmez) → CSP script-src'e takılmaz, nonce gerekmez.
HAKKIMIZDA_ABOUTPAGE_LD = """<script type="application/ld+json">
{"@context":"https://schema.org","@type":"AboutPage","name":"Hakkımızda — SınavVeri","url":"https://sinavveri.com/hakkimizda.html","inLanguage":"tr-TR","isPartOf":{"@type":"WebSite","name":"SınavVeri","url":"https://sinavveri.com/"},"about":{"@type":"Organization","name":"SınavVeri","url":"https://sinavveri.com/","email":"info@sinavveri.com","memberOf":{"@type":"Organization","name":"TrVeri (Türkiye Veri Platformu)","url":"https://www.trveri.com/"}}}
</script>"""


def page_hakkimizda():
    body = f"""
<div class="hero">
  <h1>Hakkımızda</h1>
  <p style="font-style:italic">Veriyi rakam değil, doğru karar verme rehberi olarak görüyoruz.</p>
</div>

<div class="prose">
<p>Hayatın her anında doğru veriye ulaşmanın kritik olduğunu biliyoruz. <b>Yaşam, sağlık, gıda, ekonomi, enerji, teknoloji</b> ve günlük ihtiyaçlara kadar uzanan dijital ağımızla, geniş bir yelpazede, hayatınızı kolaylaştıracak bilgiyi topluyor, doğruluyor ve sade arayüzlerle <b>eksiksiz, kesintisiz ve en hızlı şekilde</b> size sunuyoruz.</p>
<p>Ekibimizin <b>30 yılı aşkın</b> saha tecrübesini dijital dünyanın hızıyla birleştiriyor, karmaşık verileri herkes için <b>anlaşılır, erişilebilir ve faydalı</b> hale getiriyoruz. Herkesin veriye eksiksiz, kesintisiz ve hızlı ulaşması gerektiğine inanıyor; bu amaçla farklı uzmanlık alanlarında <b>20+ canlı</b> web ve mobil uygulamamızla kesintisiz hizmet veriyoruz.</p>

<h2>SınavVeri nedir?</h2>
<p><b>SınavVeri.com</b>, Türkiye'deki merkezi sınavlara hazırlanan öğrenciler ve adaylar için taban puanları, başarı sıralamaları, kontenjanlar, puan hesaplama araçları ve sınav takvimini tek çatı altında toplayan bağımsız bir eğitim verisi platformudur. YKS, LGS, KPSS, DGS, ALES, TUS, DUS ve daha fazlası için binlerce üniversite programının, lisenin ve kadronun güncel verisini sade, hızlı ve reklamsız bir arayüzle sunuyoruz.</p>
<p>Amacımız; dağınık ve karmaşık resmî verileri, tercih döneminde doğru karar vermenizi sağlayacak <b>karşılaştırılabilir, aranabilir ve anlaşılır</b> hâle getirmek. Bir bölümü mü araştırıyorsunuz, sıralamanıza uygun üniversiteleri mi arıyorsunuz, yoksa puanınızı mı hesaplamak istiyorsunuz — hepsi tek yerde.</p>

<h2>Neyi farklı yapıyoruz?</h2>
<ul>
<li><b>Tek çatı:</b> YKS, LGS, KPSS, DGS, ALES, TUS ve DUS taban puanları ile başarı sıralamaları aynı platformda.</li>
<li><b>Akıllı tercih robotu:</b> Sıralamanıza ve puanınıza göre uygun bölüm ve üniversiteleri saniyeler içinde listeleyin.</li>
<li><b>Yıllara göre trend:</b> Taban puanı ve başarı sırasının geçmiş yıllara göre değişimini tek bakışta görün.</li>
<li><b>Ücretsiz puan hesaplama:</b> YKS, LGS, KPSS, DGS ve ALES için net–puan hesaplama araçları.</li>
<li><b>Sade ve hızlı:</b> Kayıt gerektirmeyen, mobil uyumlu ve karanlık tema destekli, hızlı bir arayüz.</li>
</ul>

<h2>Veri Kaynağı ve Güncellik</h2>
<p>Üniversite taban puanları ve başarı sıralamaları <b>ÖSYM</b> ve <b>YÖK Atlas</b> verilerinden; LGS lise taban puanları <b>MEB</b> merkezi yerleştirme sonuçlarından derlenir. Veriler her yeni yerleştirme dönemi açıklandığında güncellenir; sınav takvimi resmî duyurulara göre düzenli olarak yenilenir. SınavVeri resmî bir kurum değildir; sunulan bilgiler yalnızca yol gösterme amaçlıdır, kesin tercih ve başvuru işlemleri ilgili kurumların resmî sistemleri üzerinden yapılmalıdır.</p>

<h2>İletişim</h2>
<p>Soru ve önerileriniz, reklam ve işbirliği teklifleriniz için: <a href="mailto:info@sinavveri.com">info@sinavveri.com</a></p>

<p>SınavVeri, <a href="https://www.trveri.com" target="_blank" rel="noopener noreferrer">TrVeri (Türkiye Veri Platformu)</a> ailesinin üyesidir.</p>
</div>

<div class="prose" style="margin-top:20px;text-align:center;border-left:4px solid var(--accent)">
<p style="font-size:19px;font-weight:700;font-style:italic;color:var(--accent);margin:0;line-height:1.5">“Gücümüzü geçmişimizden, hızımızı teknolojimizden alıyoruz.”</p>
<p style="margin-top:12px;font-style:italic;color:var(--fg-faded)">— SınavVeri Ekibi</p>
</div>

<div style="margin-top:22px">{SHARE_BAR}</div>
"""
    return base("hakkimizda.html", "Hakkımızda | SınavVeri.com",
                "SınavVeri.com: YKS, LGS, KPSS, DGS ve ALES taban puanları, başarı sıralamaları ve "
                "puan hesaplama araçlarını tek çatıda sunan bağımsız eğitim verisi platformu. "
                "TrVeri (Türkiye Veri Platformu) ailesinin üyesidir.",
                body, share=True, extra_head=HAKKIMIZDA_ABOUTPAGE_LD)


def main():
    print("SınavVeri.com inşa ediliyor...")
    slugs = []  # sitemap için

    def W(slug, html):
        write(slug, html)
        slugs.append(slug)

    # Sabit sayfalar
    W("index.html", page_index())
    W("takvim.html", page_takvim())
    _duyurular_html = page_duyurular()
    if _duyurular_html:
        W("duyurular.html", _duyurular_html)
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
    W("hakkimizda.html", page_hakkimizda())
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
    print(f"  {len(programs)} program yüklendi (YÖK Atlas {YKS_YIL})")
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
    print("  Şehir (il) üniversite sayfaları üretiliyor...")
    sehir_slugs = gen_sehir_pages(programs, u_by_slug)
    for s in sehir_slugs:
        slugs.append(f"sehir/{s}.html")
    W("sehirler.html", page_sehirler(sehir_slugs, programs))
    print(f"  → {len(sehir_slugs)} şehir sayfası")
    W("universite-ucretleri.html", page_universite_ucretleri(programs, u_by_slug))
    W("bolum-ucretleri.html", page_bolum_ucretleri(programs, g_by_slug))
    print("  → ücret sayfaları (üniversite + bölüm)")
    W("karsilastir.html", page_karsilastir())
    print("  → karşılaştırma sayfası")
    W("kpss-tercih-raporu.html", page_kpss_rapor())
    W("kpss-tercih-raporu-ornek.html", page_kpss_rapor_ornek())
    W("kpss-tercih-raporu-tesekkurler.html", page_kpss_rapor_tesekkurler())
    W("kpss-raporu.html", page_kpss_raporu())
    print("  → Kişiye Özel KPSS Tercih Raporu (satış + örnek + teşekkür + rapor)")

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
