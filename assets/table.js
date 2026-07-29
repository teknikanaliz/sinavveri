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
    // Gösterge ve ⓘ etiketi CSS ile çizilir (::before) → th.textContent KİRLENMEZ.
    // (Aksi halde başlık metnini okuyan kod "Tarih↕i" görür — SinavVeri'de yakalandı.)
    "th.tv-th .tv-th__ind{margin-left:.25rem;opacity:.35;font-size:.8em}" +
    "th.tv-th .tv-th__ind::before{content:\"\\2195\"}" +                       /* ↕ */
    "th.tv-th[aria-sort=\"ascending\"] .tv-th__ind::before{content:\"\\25B2\"}" +  /* ▲ */
    "th.tv-th[aria-sort=\"descending\"] .tv-th__ind::before{content:\"\\25BC\"}" + /* ▼ */
    "th.tv-th[aria-sort] .tv-th__ind{opacity:1;color:var(--tvt-accent,var(--accent,#0d9488))}" +
    // --- ⓘ ipucu düğmesi (mobil) ---
    ".tv-th__i{display:none;margin-left:.3rem;width:1.05rem;height:1.05rem;line-height:1.05rem;" +
    "padding:0;border:0;border-radius:50%;background:var(--tvt-accent,var(--accent,#0d9488));color:#fff;" +
    "font-size:.72rem;font-weight:700;text-align:center;cursor:pointer;vertical-align:middle;flex:0 0 auto}" +
    ".tv-th__i::before{content:\"i\"}" +
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
    i.className = "tv-th__i";        // "i" harfi CSS ::before ile çizilir (textContent kirlenmesin)
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
  // Hücre değeri + KAYNAĞI: data-sort → HAM (İngilizce/ISO biçim), yoksa görünen METİN (TR biçim).
  // Kaynağı bilmek "1.234" belirsizliğini çözer: ham ise 1.234, TR metin ise 1234.
  function cell(td) {
    if (!td) return { v: "", raw: false };
    var s = td.querySelector("[data-sort]");
    return s ? { v: s.getAttribute("data-sort"), raw: true }
             : { v: (td.textContent || "").trim(), raw: false };
  }
  function cellVal(td) { return cell(td).v; }   // geriye uyum
  // Sayı ayrıştırma — TR ve EN biçimlerini AYIRT EDER.
  // ⚠️ Eski sürüm "%0.05" gibi nokta-ondalıklı değerleri binlik sanıp 5 yapıyordu (FaizVeri'de yakalandı).
  //    Kural: virgül varsa → TR (nokta=binlik, virgül=ondalık); yalnız nokta varsa → tam binlik
  //    gruplaması ise (1.234 / 1.234.567) binlik, değilse (0.05 / 12.5) ONDALIK.
  // NOT: işaret metinde ▲/▼ ile taşınıyorsa (eksi yoksa) buradan anlaşılamaz →
  //      o sütunlarda hücreye <span data-sort="ham_değer"> koyun (kanonik yol).
  function num(v, raw) {
    if (v === null || v === undefined) return null;
    v = String(v).trim();
    if (!v || v === "—" || v === "-") return null;
    if (raw) { var r = parseFloat(v); return isNaN(r) ? null : r; }  // data-sort → ham/EN biçim
    var neg = /^\s*[-−]/.test(v);                          // baştaki eksi (ASCII veya U+2212)
    var t = v.replace(/[^\d.,]/g, "");
    if (!t) return null;
    if (t.indexOf(",") !== -1) t = t.replace(/\./g, "").replace(",", ".");  // "1.234.567,89" → TR
    else if (/^\d{1,3}(\.\d{3})+$/.test(t)) t = t.replace(/\./g, "");       // "1.234" → binlik (TR)
    // aksi halde nokta ONDALIK ayırıcıdır ("0.05", "12.5") → dokunma
    var f = parseFloat(t);
    if (isNaN(f)) return null;
    return neg ? -f : f;
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
      var ac = cell(a.cells[colIdx]), bc = cell(b.cells[colIdx]);
      var av = ac.v, bv = bc.v;
      if (type === "num" || type === "date") {
        var an = type === "date" ? dateVal(av) : num(av, ac.raw);
        var bn = type === "date" ? dateVal(bv) : num(bv, bc.raw);
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
      ind.className = "tv-th__ind";   // ↕/▲/▼ CSS ::before ile (aria-sort'a bağlı) → textContent temiz
      ind.setAttribute("aria-hidden", "true");
      th.appendChild(ind);

      var doSort = function () {
        var cur = th.getAttribute("aria-sort");
        var dir = cur === "ascending" ? "descending" : "ascending";
        ths.forEach(function (o) { o.removeAttribute("aria-sort"); });
        th.setAttribute("aria-sort", dir);   // gösterge CSS ile aria-sort'tan türetilir
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
