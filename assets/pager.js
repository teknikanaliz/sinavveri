/* TrVeri STANDART sayfalama (pagination) bileşeni — servermimari/assets/pager.js  [v2]
   ------------------------------------------------------------------------------------
   AMAÇ (kalıcı kural): 50+ satırlı hiçbir liste tek blokta gösterilmez. Her uzun liste
   ‹ Önceki / numaralı sayfa / Sonraki › + İlk/Son + "Sayfa [__] Git" + kayıt/sayfa
   seçici + "Sayfa X / N · N kayıt" navigasyonu alır. Tema-uyumlu, mobil uyumlu.

   İLKE — Progressive enhancement: JS çalışmazsa TÜM satırlar görünür (SEO güvenli,
   no-JS erişilebilir). JS varsa liste 'per' satıra bölünür, altına navigasyon çizilir.

   SEKTÖR STANDARDI (2026-07 araştırma): sonsuz-kaydırma KULLANILMAZ (SEO + bulunabilirlik
   zararlı); numaralı sayfalama + jump-to-page + rows-per-page seçici = veri/rehber siteleri
   için doğru desen. Varsayılan 25 kayıt/sayfa (yoğun tek-satır tablolarda 50, kart ızgarasında 24).

   KULLANIM (iki yol):

   1) DEKLARATİF (otomatik) — hiç JS yazmadan:
      <table data-tvpager data-per="50"> ... <tbody> N satır </tbody> </table>
      veya bir kart ızgarası:
      <div class="card-grid" data-tvpager data-per="24"> N kart </div>
      Sayfa yüklenince otomatik bulunur ve sayfalanır. (per verilmezse 25.)

   2) PROGRAMATİK (mevcut arama/filtre/sıralama ile entegre) — HVP üst-kümesi:
      var p = TVPager.attach({ grid: tableEl, per: 25, match: fn, mount: elem });
      // arama/filtre değişince: p.reset();  yalnız yeniden çiz: p.refresh();
      'match(el)->bool' verilirse yalnız eşleşen satırlar sayılır/gösterilir.

   NOT: window.HVP çağrıları da desteklenir (geriye dönük uyumluluk shim'i en altta).

   Kanonik kaynak: servermimari/assets/pager.js  ·  TrVeri içi. */
(function () {
  "use strict";
  if (window.TVPager && window.TVPager.__v >= 2) return; // çift-yükleme koruması

  var THRESHOLD = 100;                      // ≤100 kayıt → TÜMÜ görünür, sayfalama YOK
  var DEFAULT_PER = 25;                     // >100 kayıt → standart 25 kayıt/sayfa
  var PER_OPTIONS = [10, 25, 50, 100];      // kayıt/sayfa seçenekleri
  var LS_KEY = "tv-pager-per";              // kullanıcının kayıt/sayfa tercihi (kalıcı)
  var JUMP_MIN_PAGES = 7;                   // bu sayfadan fazlaysa "Sayfa [__] Git" göster

  var CSS_ID = "tv-pager-css";
  var CSS =
    ".tv-pager{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:.4rem;" +
    "margin:1.25rem 0 .25rem;font-size:.95rem;line-height:1;-webkit-user-select:none;user-select:none}" +
    ".tv-pager__row{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:.4rem}" +
    ".tv-pager__row--meta{width:100%;gap:.75rem;margin-top:.15rem;font-size:.9rem}" +
    ".tv-pager__b{display:inline-flex;align-items:center;justify-content:center;min-width:2.25rem;" +
    "height:2.25rem;padding:0 .55rem;border:1px solid var(--tvp-border,var(--border,#d7dbe0));" +
    "border-radius:.55rem;background:var(--tvp-bg,var(--card,var(--bg-card,#fff)));" +
    "color:var(--tvp-fg,var(--text,var(--fg,#1f2937)));cursor:pointer;font:inherit;font-weight:600;" +
    "text-decoration:none;transition:background .15s,border-color .15s,color .15s}" +
    ".tv-pager__b:hover:not([disabled]):not([aria-current]){border-color:var(--tvp-accent,var(--accent,#0d9488));" +
    "color:var(--tvp-accent,var(--accent,#0d9488))}" +
    ".tv-pager__b:focus-visible{outline:2px solid var(--tvp-accent,var(--accent,#0d9488));outline-offset:2px}" +
    ".tv-pager__b[aria-current]{background:var(--tvp-accent,var(--accent,#0d9488));" +
    "border-color:var(--tvp-accent,var(--accent,#0d9488));color:#fff;cursor:default}" +
    ".tv-pager__b[disabled]{opacity:.4;cursor:default;pointer-events:none}" +
    ".tv-pager__gap{min-width:1.25rem;text-align:center;color:var(--tvp-muted,var(--muted,#8a94a6));padding:0 .1rem}" +
    ".tv-pager__lbl{margin:0 .28rem}" +
    ".tv-pager__info{color:var(--tvp-muted,var(--muted,#8a94a6));font-weight:500}" +
    ".tv-pager__ctl{display:inline-flex;align-items:center;gap:.35rem;color:var(--tvp-muted,var(--muted,#8a94a6))}" +
    ".tv-pager__ctl label{font-weight:500}" +
    ".tv-pager__num,.tv-pager__sel{height:2rem;padding:0 .4rem;border:1px solid var(--tvp-border,var(--border,#d7dbe0));" +
    "border-radius:.45rem;background:var(--tvp-bg,var(--card,var(--bg-card,#fff)));" +
    "color:var(--tvp-fg,var(--text,var(--fg,#1f2937)));font:inherit;font-size:.9rem}" +
    ".tv-pager__num{width:4rem;text-align:center;-moz-appearance:textfield}" +
    ".tv-pager__num::-webkit-outer-spin-button,.tv-pager__num::-webkit-inner-spin-button{-webkit-appearance:none;margin:0}" +
    ".tv-pager__sel{cursor:pointer}" +
    ".tv-pager__go{height:2rem;padding:0 .6rem;border:1px solid var(--tvp-accent,var(--accent,#0d9488));" +
    "border-radius:.45rem;background:transparent;color:var(--tvp-accent,var(--accent,#0d9488));" +
    "cursor:pointer;font:inherit;font-size:.9rem;font-weight:600}" +
    ".tv-pager__go:hover{background:var(--tvp-accent,var(--accent,#0d9488));color:#fff}" +
    // Mobil: tüm düğmeler KALIR (İlk/Son dahil); Önceki/Sonraki kelimesi gizlenir (yalnız ok),
    // böylece tüm sayfa düğmeleri tek satıra sığar. Alt satır (git/kayıt-sayfa/bilgi) dikey akar.
    "@media(max-width:560px){.tv-pager{font-size:.9rem;gap:.3rem}" +
    ".tv-pager__b{min-width:2.1rem;height:2.1rem;padding:0 .4rem}" +
    ".tv-pager__lbl{display:none}" +
    ".tv-pager__row--meta{flex-direction:column;gap:.5rem}}";

  function injectCSS() {
    if (document.getElementById(CSS_ID)) return;
    var s = document.createElement("style");
    s.id = CSS_ID;
    // CSP: nonce'lu ortamlarda mevcut nonce'u devral (strict-dynamic uyumu).
    var n = document.querySelector("script[nonce]");
    if (n && n.nonce) s.setAttribute("nonce", n.nonce);
    s.textContent = CSS;
    (document.head || document.documentElement).appendChild(s);
  }

  function savedPer() {
    try {
      var v = parseInt(localStorage.getItem(LS_KEY), 10);
      return PER_OPTIONS.indexOf(v) !== -1 ? v : null;
    } catch (e) { return null; }
  }
  function savePer(v) { try { localStorage.setItem(LS_KEY, String(v)); } catch (e) {} }

  // Görünecek sayfa numaraları: ilk, son, aktif±1 + elipsis (0 = "…").
  function windowed(cur, n) {
    var out = [], i, add = function (x) { if (out[out.length - 1] !== x) out.push(x); };
    for (i = 1; i <= n; i++) {
      if (i === 1 || i === n || (i >= cur - 1 && i <= cur + 1)) add(i);
      else if (out[out.length - 1] !== 0) add(0);
    }
    return out;
  }

  function attach(o) {
    injectCSS();
    var grid = typeof o.grid === "string" ? document.getElementById(o.grid) : o.grid;
    if (!grid) return { reset: function () {}, refresh: function () {} };

    // Satır kaynağı: <table> ise ilk <tbody>, değilse kabın doğrudan çocukları.
    var host = grid;
    if (/table/i.test(grid.tagName)) host = grid.tBodies[0] || grid;

    var declared = Math.max(1, parseInt(o.per, 10) || DEFAULT_PER);
    var per = savedPer() || declared;          // kullanıcı tercihi > sayfanın önerdiği
    var match = o.match || function () { return true; };
    var page = 0;

    // Navigasyon montaj noktası
    var mount = o.mount;
    if (!mount) {
      mount = document.createElement("nav");
      var anchor = /table/i.test(grid.tagName) ? grid : host;
      anchor.parentNode.insertBefore(mount, anchor.nextSibling);
    }
    mount.className = (mount.className ? mount.className + " " : "") + "tv-pager";
    mount.setAttribute("aria-label", "Sayfalama");

    function items() {
      return [].slice.call(host.children).filter(function (el) { return match(el); });
    }
    function pages(v) { return Math.max(1, Math.ceil(v.length / per)); }

    function draw() {
      var all = [].slice.call(host.children);
      var v = items();
      // KURAL: ≤100 kayıt → TÜM liste görünür, sayfalama YOK (nav gizlenir).
      if (v.length <= THRESHOLD) {
        all.forEach(function (el) { el.style.display = "none"; });
        v.forEach(function (el) { el.style.display = ""; });
        mount.textContent = "";
        mount.style.display = "none";
        return;
      }
      var n = pages(v);
      if (page >= n) page = n - 1;
      if (page < 0) page = 0;
      var start = page * per, end = start + per, seen = -1;
      all.forEach(function (el) { el.style.display = "none"; });
      v.forEach(function (el) { seen++; el.style.display = (seen >= start && seen < end) ? "" : "none"; });
      renderNav(v.length, n);
    }

    function go(p, scroll) {
      var n = pages(items());
      page = Math.min(Math.max(0, p), n - 1);
      draw();
      if (scroll !== false) { try { grid.scrollIntoView({ block: "start", behavior: "smooth" }); } catch (x) {} }
    }

    function btn(label, p, opts) {
      opts = opts || {};
      var b = document.createElement("button");
      b.type = "button";
      b.className = "tv-pager__b" + (opts.edge ? " tv-pager__b--edge" : "");
      if (opts.word) {
        // "‹ Önceki" / "Sonraki ›" → dar ekranda yalnız ok kalsın diye kelime ayrı span'de
        var pre = opts.word === "before" ? "‹ " : "";
        var post = opts.word === "after" ? " ›" : "";
        if (pre) b.appendChild(document.createTextNode("‹"));
        var w = document.createElement("span");
        w.className = "tv-pager__lbl";
        w.textContent = label;
        b.appendChild(w);
        if (post) b.appendChild(document.createTextNode("›"));
      } else {
        b.textContent = label;               // label her zaman sabit metin → XSS yok
      }
      if (opts.current) b.setAttribute("aria-current", "page");
      if (opts.disabled) b.disabled = true;
      if (opts.aria) b.setAttribute("aria-label", opts.aria);
      if (!opts.current && !opts.disabled) b.addEventListener("click", function () { go(p); });
      return b;
    }
    function gap() {
      var s = document.createElement("span");
      s.className = "tv-pager__gap";
      s.textContent = "…";
      return s;
    }

    function renderNav(count, n) {   // yalnız >THRESHOLD kayıtta çağrılır
      mount.textContent = "";
      mount.style.display = "";

      // --- 1. satır: sayfa düğmeleri ---
      var row = document.createElement("div");
      row.className = "tv-pager__row";
      if (n > 1) {
        row.appendChild(btn("«", 0, { disabled: page === 0, aria: "İlk sayfa", edge: true }));
        row.appendChild(btn("Önceki", page - 1, { disabled: page === 0, aria: "Önceki sayfa", word: "before" }));
        windowed(page + 1, n).forEach(function (num) {
          row.appendChild(num === 0 ? gap()
            : btn(String(num), num - 1, { current: num - 1 === page, aria: num + ". sayfa" }));
        });
        row.appendChild(btn("Sonraki", page + 1, { disabled: page >= n - 1, aria: "Sonraki sayfa", word: "after" }));
        row.appendChild(btn("»", n - 1, { disabled: page >= n - 1, aria: "Son sayfa", edge: true }));
        mount.appendChild(row);
      }

      // --- 2. satır: sayfaya git + kayıt/sayfa + bilgi ---
      var meta = document.createElement("div");
      meta.className = "tv-pager__row tv-pager__row--meta";

      if (n > JUMP_MIN_PAGES) {              // çok sayfalıysa doğrudan sayfa numarası yazıp git
        var jump = document.createElement("div");
        jump.className = "tv-pager__ctl";
        var jl = document.createElement("label");
        jl.textContent = "Sayfa";
        var ji = document.createElement("input");
        ji.type = "number"; ji.className = "tv-pager__num";
        ji.min = "1"; ji.max = String(n); ji.value = String(page + 1);
        ji.setAttribute("aria-label", "Gidilecek sayfa numarası (1-" + n + ")");
        var jb = document.createElement("button");
        jb.type = "button"; jb.className = "tv-pager__go"; jb.textContent = "Git";
        var doJump = function () {
          var t = parseInt(ji.value, 10);
          if (!isNaN(t)) go(Math.min(Math.max(1, t), n) - 1);
        };
        jb.addEventListener("click", doJump);
        ji.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); doJump(); } });
        var jt = document.createElement("span");
        jt.textContent = "/ " + n;
        jump.appendChild(jl); jump.appendChild(ji); jump.appendChild(jt); jump.appendChild(jb);
        meta.appendChild(jump);
      }

      var perCtl = document.createElement("div");   // kayıt/sayfa seçici (10/25/50/100)
      perCtl.className = "tv-pager__ctl";
      var sel = document.createElement("select");
      sel.className = "tv-pager__sel";
      sel.setAttribute("aria-label", "Sayfa başına kayıt sayısı");
      var opts = PER_OPTIONS.slice();
      if (opts.indexOf(per) === -1) opts.push(per);
      opts.sort(function (a, b) { return a - b; }).forEach(function (v) {
        var op = document.createElement("option");
        op.value = String(v); op.textContent = String(v);
        if (v === per) op.selected = true;
        sel.appendChild(op);
      });
      sel.addEventListener("change", function () {
        var first = page * per;                    // görünen ilk kaydı koru
        per = parseInt(sel.value, 10) || DEFAULT_PER;
        savePer(per);
        page = Math.floor(first / per);
        draw();
      });
      var pl = document.createElement("label");
      pl.textContent = "kayıt/sayfa";
      perCtl.appendChild(sel); perCtl.appendChild(pl);
      meta.appendChild(perCtl);

      var info = document.createElement("span");
      info.className = "tv-pager__info";
      // "Sayfa [__] / N" kutusu zaten varken sayfa bilgisini tekrarlama → yalnız toplam kayıt.
      info.textContent = (n > JUMP_MIN_PAGES)
        ? ("Toplam " + count.toLocaleString("tr-TR") + " kayıt")
        : ("Sayfa " + (page + 1) + " / " + n + " · " + count.toLocaleString("tr-TR") + " kayıt");
      meta.appendChild(info);

      mount.appendChild(meta);
    }

    // Tıkla-sırala entegrasyonu — EVRENSEL: herhangi bir sorter satırları yeniden dizince
    // (childList mutasyonu) pager kendini tazeler → sorter'ın işbirliğine GEREK YOK.
    // pager yalnız style.display (attribute) değiştirir, childList DEĞİL → sonsuz döngü olmaz.
    if (window.MutationObserver) {
      var moT = null;
      var mo = new MutationObserver(function () {
        if (moT) clearTimeout(moT);
        moT = setTimeout(function () { page = 0; draw(); }, 30);
      });
      try { mo.observe(host, { childList: true }); } catch (e) {}
    }
    // Ek: açıkça 'tv:sorted' yayan sorter'lar (spk.js, table.js) için de dinle.
    var tableEl = /table/i.test(grid.tagName) ? grid : null;
    if (tableEl) tableEl.addEventListener("tv:sorted", function () { page = 0; draw(); });

    draw();
    return {
      reset: function () { page = 0; draw(); },
      refresh: function () { draw(); },
      goto: function (p) { go(p); }
    };
  }

  // Deklaratif otomatik başlatma: [data-tvpager]
  function autoInit(root) {
    var els = (root || document).querySelectorAll("[data-tvpager]:not([data-tvpager-done])");
    [].slice.call(els).forEach(function (el) {
      el.setAttribute("data-tvpager-done", "1");
      attach({ grid: el, per: parseInt(el.getAttribute("data-per"), 10) || DEFAULT_PER });
    });
  }

  window.TVPager = { attach: attach, autoInit: autoInit, DEFAULT_PER: DEFAULT_PER, __v: 2 };

  // Geriye dönük uyumluluk: window.HVP(o) → attach (numaralı navigasyonu bedava kazandırır).
  // HVP imzası: {grid, per, match, pager}; 'pager' verilmişse mount olarak kullanılır.
  if (!window.HVP || !window.HVP.__tv) {
    window.HVP = function (o) {
      var mount = o.pager && typeof o.pager !== "string" ? o.pager
        : (o.pager ? document.getElementById(o.pager) : null);
      if (mount) mount.textContent = "";   // eski .hvp-prev/.hvp-next/.hvp-pg kabuğunu boşalt
      return attach({ grid: o.grid, per: o.per, match: o.match, mount: mount || undefined });
    };
    window.HVP.__tv = 1;
  }

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", function () { autoInit(); });
  else autoInit();
})();
