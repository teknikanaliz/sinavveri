/* TrVeri STANDART veri tablosu bileşeni — servermimari/assets/table.js
   --------------------------------------------------------------------
   İKİ İŞ YAPAR (kalıcı kural):
   1) KOLON AÇIKLAMASI (tooltip): `<th data-tip="...">` üzerinde masaüstünde MOUSE ile
      beklendiğinde, mobilde ⓘ düğmesine dokununca açıklama baloncuğu görünür.
   2) TIKLA-SIRALA: sütun başlığına tıklayınca artan/azalan sıralama + ▲/▼ göstergesi
      (TrVeri kural 3.7). Türkçe locale, sayı/tarih duyarlı, boş/— değerler en sona.

   KULLANIM:
     <table data-tvtable>                     ← sıralama + tooltip (yeni tablolar)
       <thead><tr>
         <th data-tip="Bildirimin KAP'ta yayımlandığı tarih" data-type="date">Tarih</th>
         <th data-tip="Şirketin ünvanı">Şirket</th>
       </tr></thead>
       <tbody>…</tbody>
     </table>

   ⚠️ SIRALAMA OPT-IN'dir (`data-tvtable` veya `data-tvsort`): sitede ZATEN bir sorter
   varsa (spk.js, site-içi global sorter) çift-bağlama olmasın. TOOLTIP ise her
   `th[data-tip]` için otomatik çalışır → mevcut tablolara güvenle eklenebilir.

   Sıralama sonrası `tv:sorted` event'i yayılır → pager.js sayfalamayı tazeler (1. sayfa).
   Hücre değeri: `<span data-sort="…">` varsa o (ISO tarih / ham sayı), yoksa metin.
   Sütun tipi: `<th data-type="num|date|text">` (varsayılan text).

   Kanonik kaynak: servermimari/assets/table.js  ·  TrVeri içi. */
(function () {
  "use strict";
  if (window.TVTable && window.TVTable.__v) return;

  var CSS_ID = "tv-table-css";
  var CSS =
    // --- sıralanabilir başlık ---
    "th.tv-th{cursor:pointer;position:relative;-webkit-user-select:none;user-select:none}" +
    "th.tv-th:hover{color:var(--tvt-accent,var(--accent,#0d9488))}" +
    "th.tv-th:focus-visible{outline:2px solid var(--tvt-accent,var(--accent,#0d9488));outline-offset:-2px}" +
    "th.tv-th .tv-th__ind{margin-left:.25rem;opacity:.35;font-size:.8em}" +
    "th.tv-th[aria-sort] .tv-th__ind{opacity:1;color:var(--tvt-accent,var(--accent,#0d9488))}" +
    // --- ⓘ ipucu düğmesi (mobil) ---
    ".tv-th__i{display:none;margin-left:.3rem;width:1.05rem;height:1.05rem;line-height:1.05rem;" +
    "padding:0;border:0;border-radius:50%;background:var(--tvt-accent,var(--accent,#0d9488));color:#fff;" +
    "font-size:.72rem;font-weight:700;text-align:center;cursor:pointer;vertical-align:middle;flex:0 0 auto}" +
    // --- açıklama baloncuğu ---
    ".tv-tip{position:fixed;z-index:9999;max-width:min(20rem,88vw);padding:.5rem .65rem;" +
    "border-radius:.5rem;background:var(--tvt-tipbg,#111827);color:#f9fafb;font-size:.82rem;" +
    "font-weight:400;line-height:1.4;text-align:left;white-space:normal;" +
    "box-shadow:0 6px 20px rgba(0,0,0,.25);opacity:0;transform:translateY(.25rem);" +
    "transition:opacity .13s ease,transform .13s ease;pointer-events:none}" +
    ".tv-tip[data-show]{opacity:1;transform:translateY(0)}" +
    "@media(max-width:640px){.tv-th__i{display:inline-block}}";

  function injectCSS() {
    if (document.getElementById(CSS_ID)) return;
    var s = document.createElement("style");
    s.id = CSS_ID;
    var n = document.querySelector("script[nonce]");
    if (n && n.nonce) s.setAttribute("nonce", n.nonce);
    s.textContent = CSS;
    (document.head || document.documentElement).appendChild(s);
  }

  /* ---------------- Tooltip (kolon açıklaması) ---------------- */
  var tipEl = null, tipHideT = null;

  function tipNode() {
    if (!tipEl) {
      tipEl = document.createElement("div");
      tipEl.className = "tv-tip";
      tipEl.setAttribute("role", "tooltip");
      document.body.appendChild(tipEl);
    }
    return tipEl;
  }
  function showTip(anchor, text) {
    if (!text) return;
    if (tipHideT) { clearTimeout(tipHideT); tipHideT = null; }
    var t = tipNode();
    t.textContent = text;              // düz metin → XSS yok
    t.setAttribute("data-show", "1");
    var r = anchor.getBoundingClientRect();
    var tr = t.getBoundingClientRect();
    var left = r.left + r.width / 2 - tr.width / 2;
    left = Math.max(8, Math.min(left, window.innerWidth - tr.width - 8));
    var top = r.bottom + 8;
    if (top + tr.height > window.innerHeight - 8) top = Math.max(8, r.top - tr.height - 8);
    t.style.left = left + "px";
    t.style.top = top + "px";
  }
  function hideTip() {
    if (!tipEl) return;
    tipEl.removeAttribute("data-show");
    tipHideT = setTimeout(function () { if (tipEl) tipEl.textContent = ""; }, 150);
  }

  function wireTip(th) {
    var text = th.getAttribute("data-tip");
    if (!text || th.hasAttribute("data-tvtip-done")) return;
    th.setAttribute("data-tvtip-done", "1");
    th.setAttribute("title", "");                 // yerleşik tarayıcı tooltip'i kapat (çift gösterim olmasın)
    th.removeAttribute("title");
    th.setAttribute("aria-description", text);

    th.addEventListener("mouseenter", function () { showTip(th, text); });
    th.addEventListener("mouseleave", hideTip);
    th.addEventListener("focus", function () { showTip(th, text); });
    th.addEventListener("blur", hideTip);

    // Mobil: ⓘ düğmesi — dokununca ipucu açılır, SIRALAMAYI tetiklemez.
    var i = document.createElement("button");
    i.type = "button";
    i.className = "tv-th__i";
    i.textContent = "i";
    i.setAttribute("aria-label", "Sütun açıklaması: " + text);
    i.addEventListener("click", function (e) {
      e.stopPropagation();
      e.preventDefault();
      if (tipEl && tipEl.hasAttribute("data-show")) { hideTip(); return; }
      showTip(th, text);
      setTimeout(function () {
        document.addEventListener("click", function onDoc() {
          hideTip();
          document.removeEventListener("click", onDoc);
        });
      }, 0);
    });
    th.appendChild(i);
  }

  /* ---------------- Tıkla-sırala ---------------- */
  function cellVal(td) {
    if (!td) return "";
    var s = td.querySelector("[data-sort]");
    return s ? s.getAttribute("data-sort") : (td.textContent || "").trim();
  }
  function num(v) {
    if (v === null || v === undefined) return null;
    v = String(v).trim();
    if (!v || v === "—" || v === "-") return null;
    if (/^-?\d+(\.\d+)?$/.test(v)) return parseFloat(v);
    var t = v.replace(/[^\d.,-]/g, "").replace(/\./g, "").replace(",", ".");  // "1.234.567,89"
    var f = parseFloat(t);
    return isNaN(f) ? null : f;
  }
  function dateVal(v) {
    v = String(v || "").trim();
    if (!v) return null;
    var m = v.match(/^(\d{2})\.(\d{2})\.(\d{4})/);      // DD.MM.YYYY
    if (m) return Date.parse(m[3] + "-" + m[2] + "-" + m[1]) || null;
    var p = Date.parse(v);
    return isNaN(p) ? null : p;
  }

  function sortTable(table, colIdx, type, dir) {
    var tb = table.tBodies[0];
    if (!tb) return;
    var rows = [].slice.call(tb.rows);
    var mul = dir === "descending" ? -1 : 1;
    rows.sort(function (a, b) {
      var av = cellVal(a.cells[colIdx]), bv = cellVal(b.cells[colIdx]);
      if (type === "num" || type === "date") {
        var an = type === "date" ? dateVal(av) : num(av);
        var bn = type === "date" ? dateVal(bv) : num(bv);
        if (an === null && bn === null) return 0;
        if (an === null) return 1;     // boş → yönden bağımsız SONA
        if (bn === null) return -1;
        return (an - bn) * mul;
      }
      var ae = !av || av === "—", be = !bv || bv === "—";
      if (ae && be) return 0;
      if (ae) return 1;
      if (be) return -1;
      return av.localeCompare(bv, "tr", { sensitivity: "base", numeric: true }) * mul;
    });
    var frag = document.createDocumentFragment();
    rows.forEach(function (r) { frag.appendChild(r); });
    tb.appendChild(frag);
    try { table.dispatchEvent(new CustomEvent("tv:sorted", { bubbles: true })); } catch (e) {}
  }

  function wireSort(table) {
    if (!table.tHead || !table.tHead.rows[0]) return;
    var ths = [].slice.call(table.tHead.rows[0].cells);
    ths.forEach(function (th, idx) {
      if (th.hasAttribute("data-tvsort-skip") || th.hasAttribute("data-tvth-done")) return;
      th.setAttribute("data-tvth-done", "1");
      th.classList.add("tv-th");
      th.setAttribute("tabindex", "0");
      th.setAttribute("role", "columnheader");
      var ind = document.createElement("span");
      ind.className = "tv-th__ind";
      ind.textContent = "↕";
      th.appendChild(ind);

      var doSort = function () {
        var cur = th.getAttribute("aria-sort");
        var dir = cur === "ascending" ? "descending" : "ascending";
        ths.forEach(function (o) {
          o.removeAttribute("aria-sort");
          var oi = o.querySelector(".tv-th__ind");
          if (oi) oi.textContent = "↕";
        });
        th.setAttribute("aria-sort", dir);
        ind.textContent = dir === "ascending" ? "▲" : "▼";
        sortTable(table, idx, th.getAttribute("data-type") || "text", dir);
      };
      th.addEventListener("click", doSort);
      th.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); doSort(); }
      });
    });
  }

  /* ---------------- Başlatma ---------------- */
  function init(root) {
    injectCSS();
    root = root || document;
    // Tooltip: her th[data-tip] (mevcut tablolara güvenli, çakışmaz)
    [].slice.call(root.querySelectorAll("th[data-tip]")).forEach(wireTip);
    // Sıralama: yalnız opt-in tablolar (çift-bağlama önlenir)
    [].slice.call(root.querySelectorAll("table[data-tvtable],table[data-tvsort]")).forEach(wireSort);
  }

  window.TVTable = { init: init, sort: sortTable, __v: 1 };

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", function () { init(); });
  else init();
  window.addEventListener("resize", hideTip);
  window.addEventListener("scroll", hideTip, true);
})();
