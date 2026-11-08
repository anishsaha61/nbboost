(function () {
  "use strict";
  var ROOT_ID = "__ROOT_ID__";
  var root = document.getElementById(ROOT_ID);
  var dataEl = document.getElementById(ROOT_ID + "-data");
  if (!root || !dataEl || root.getAttribute("data-ready")) return;
  root.setAttribute("data-ready", "1");
  var P = JSON.parse(dataEl.textContent);
  var cols = P.columns, rows = P.rows;
  var RH = 32, HDR = 36, IDXW = 56;
  var COLORS = ["#077A9D","#FFAB00","#00A972","#FF3621","#8BCAE7","#AB4057","#99DDB4","#FCA4A1","#919191","#BF7080"];
  var NUMK = { int: 1, long: 1, float: 1, decimal: 1 };

  // ------------------------------------------------------------- helpers
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function isNum(c) { return !!NUMK[c.kind]; }
  function isTime(c) { return c.kind === "date" || c.kind === "timestamp" || c.kind === "timestamp_ntz"; }
  function toNum(v) { return v === null || v === undefined || v === "" ? NaN : Number(v); }
  function fmtInt(n) { return Number(n).toLocaleString("en-US"); }
  function fmtNum(v) {
    if (!isFinite(v)) return String(v);
    var a = Math.abs(v);
    if (a >= 1e12) return (v / 1e12).toFixed(1).replace(/\.0$/, "") + "T";
    if (a >= 1e9) return (v / 1e9).toFixed(1).replace(/\.0$/, "") + "B";
    if (a >= 1e6) return (v / 1e6).toFixed(1).replace(/\.0$/, "") + "M";
    if (a >= 1e3) return (v / 1e3).toFixed(1).replace(/\.0$/, "") + "K";
    return v.toLocaleString("en-US", { maximumFractionDigits: a < 1 && a > 0 ? 4 : 2 });
  }
  function fmtStat(v) { return isFinite(v) ? Number(v).toLocaleString("en-US", { maximumFractionDigits: 4 }) : "–"; }
  function valStr(v, c) {
    if (v === null || v === undefined) return "null";
    if (c && c.kind === "bool") return v ? "true" : "false";
    return String(v);
  }
  function timeVal(v, c) {
    if (v === null || v === undefined) return NaN;
    var s = String(v);
    if (c.kind === "date") s += "T00:00:00Z";
    else if (c.kind === "timestamp_ntz") s += "Z";
    return Date.parse(s);
  }
  function fmtTime(ms, withTime) {
    var d = new Date(ms), p = function (n) { return (n < 10 ? "0" : "") + n; };
    var s = d.getUTCFullYear() + "-" + p(d.getUTCMonth() + 1) + "-" + p(d.getUTCDate());
    return withTime ? s + " " + p(d.getUTCHours()) + ":" + p(d.getUTCMinutes()) : s;
  }
  function el(html) { var t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; }
  var ICONS = {
    cal: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="12" height="11" rx="1.5"/><path d="M2 6.5h12M5 1.5v3M11 1.5v3"/></svg>',
    clock: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><path d="M8 4.5V8l2.5 1.5"/></svg>',
    search: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5 14 14"/></svg>',
    dl: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M8 2v8M4.5 6.5 8 10l3.5-3.5M2.5 13.5h11"/></svg>',
    up: '<svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M8 3 13 10H3z"/></svg>',
    down: '<svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M8 13 3 6h10z"/></svg>',
    prof: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M2.5 13.5V8M6.5 13.5V3M10.5 13.5V6M14 13.5H2"/></svg>',
    filter: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><path d="M2 3h12L9.5 8.5V13l-3-1.5V8.5z"/></svg>'
  };
  function typeIcon(c) {
    switch (c.kind) {
      case "int": case "long": return "123";
      case "float": case "decimal": return "1.2";
      case "string": return "ABC";
      case "bool": return "T/F";
      case "date": return ICONS.cal;
      case "timestamp": case "timestamp_ntz": return ICONS.clock;
      case "binary": return "01";
      case "complex": return c.sub === "array" ? "[ ]" : "{ }";
      default: return "?";
    }
  }
  function copyText(t) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(t).catch(fallback);
    fallback();
    function fallback() {
      var ta = document.createElement("textarea"); ta.value = t; ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select(); try { document.execCommand("copy"); } catch (e) {} ta.remove();
    }
  }
  var toastTimer;
  function toast(msg) {
    toastEl.textContent = msg; toastEl.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(function () { toastEl.hidden = true; }, 1400);
  }
  function prettyJson(s) {
    var o; try { o = JSON.parse(s); } catch (e) { return esc(s); }
    var t = esc(JSON.stringify(o, null, 2));
    return t.replace(/(&quot;(?:\\&quot;|\\[^&]|(?!&quot;)[^\\])*&quot;)(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g,
      function (m, str, colon, kw) {
        if (str) return '<span class="' + (colon ? "nbb-jk" : "nbb-js") + '">' + str + "</span>" + (colon || "");
        if (kw) return '<span class="nbb-jb">' + kw + "</span>";
        return '<span class="nbb-jn">' + m + "</span>";
      });
  }

  // ------------------------------------------------------------- shell
  root.innerHTML =
    '<div class="nbb-bar"><div class="nbb-tabs" role="tablist"></div>' +
    '<div class="nbb-actions"><button class="nbb-fbtn nbb-pbtn" title="Show profile of the selected column" hidden>' + ICONS.prof + 'Column profile</button><button class="nbb-fbtn nbb-fbt2" title="Add a filter">' + ICONS.filter + 'Filter</button><div class="nbb-search">' + ICONS.search + '<input type="text" placeholder="Search" aria-label="Search results"></div>' +
    '<button class="nbb-ibtn nbb-dlbtn" title="Download / copy results" aria-label="Download or copy">' + ICONS.dl + "</button></div></div>" +
    '<div class="nbb-panels"></div>' +
    '<div class="nbb-foot"><span class="nbb-fl"></span><span class="nbb-fr"></span></div>' +
    '<div class="nbb-menu" hidden></div><div class="nbb-fed" hidden></div><div class="nbb-pop" hidden></div><div class="nbb-toast" hidden></div>';
  var tabsEl = root.querySelector(".nbb-tabs"), panelsEl = root.querySelector(".nbb-panels");
  var menuEl = root.querySelector(".nbb-menu"), filEd = root.querySelector(".nbb-fed"), popEl = root.querySelector(".nbb-pop"), toastEl = root.querySelector(".nbb-toast");
  var searchIn = root.querySelector(".nbb-search input"), footL = root.querySelector(".nbb-fl"), footR = root.querySelector(".nbb-fr");

  if (!cols.length) {
    panelsEl.innerHTML = '<div class="nbb-empty">OK</div>';
    root.querySelector(".nbb-actions").style.display = "none";
  }

  // ------------------------------------------------------------- tabs
  var tabs = [], active = null, vizCount = 0, restoring = true;
  var STORE_KEY = "nbb:v1:" + location.pathname + ":" + (P.key || "");
  function persist() {
    if (restoring || !P.key) return;
    try {
      var out = [], act = -1;
      tabs.forEach(function (t) {
        if (t.id === "table") return;
        var item = null;
        if (t.st) item = { k: "viz", label: t.label, cfg: serViz(t.st) };
        else if (t.id === "profile") item = { k: "profile" };
        if (!item) return;
        out.push(item); if (t === active) act = out.length - 1;
      });
      var tbl = { sort: sort.dir && cols[sort.c] ? { c: cols[sort.c].name, dir: sort.dir } : null,
        filters: filters.map(function (f) { return { c: cols[f.c].name, op: f.op, a: f.a, b: f.b }; }) };
      if (out.length || tbl.sort || tbl.filters.length) localStorage.setItem(STORE_KEY, JSON.stringify({ tabs: out, active: act, vc: vizCount, tbl: tbl }));
      else localStorage.removeItem(STORE_KEY);
    } catch (e) {}
  }
  function serViz(st) {
    return { type: st.type, x: cols[st.x] ? cols[st.x].name : null, ys: st.ys.map(function (i) { return cols[i].name; }),
      group: st.group >= 0 ? cols[st.group].name : null, agg: st.agg, stacked: st.stacked, bins: st.bins, sort: st.sort, top: st.top };
  }
  function colIdx(name) { for (var i = 0; i < cols.length; i++) if (cols[i].name === name) return i; return -1; }
  function resolveViz(cfg) {                     // saved config -> state, or null when its columns are gone
    var x = colIdx(cfg.x); if (x < 0) return null;
    var ys = (cfg.ys || []).map(colIdx).filter(function (i) { return i >= 0 && isNum(cols[i]); });
    var t = cfg.type;
    if (["bar", "barh", "line", "area", "combo", "scatter", "pie", "donut", "heatmap", "box", "histogram", "funnel", "counter", "wordcloud"].indexOf(t) < 0) return null;
    if (t === "box" && !ys.length) return null;
    if (t === "heatmap" && (cfg.group ? colIdx(cfg.group) : -1) < 0) return null;
    if (t === "histogram" && !isNum(cols[x])) return null;
    if (t === "scatter" && (!(isNum(cols[x]) || isTime(cols[x])) || !ys.length)) return null;
    if (t !== "histogram" && t !== "scatter" && t !== "wordcloud" && t !== "box" && cfg.agg !== "count" && !ys.length) return null;
    var g = cfg.group ? colIdx(cfg.group) : -1;
    return { type: t, x: x, ys: ys, group: g, agg: cfg.agg, stacked: !!cfg.stacked, bins: cfg.bins || 20, sort: cfg.sort || "auto", top: cfg.top || 30, hidden: {} };
  }
  function addTab(id, label, panel, closable, onShow) {
    var t = { id: id, label: label, panel: panel, closable: closable, onShow: onShow };
    tabs.push(t); panelsEl.appendChild(panel); renderTabs(); return t;
  }
  function renderTabs() {
    tabsEl.innerHTML = tabs.map(function (t) {
      return '<button class="nbb-tab' + (t === active ? " nbb-on" : "") + '" data-tab="' + t.id + '" role="tab">' + esc(t.label) +
        (t.closable ? '<span class="nbb-x" data-close="' + t.id + '" title="Remove">×</span>' : "") + "</button>";
    }).join("") + (cols.length ? '<button class="nbb-plus" title="Add visualization or data profile" aria-label="Add">+</button>' : "");
  }
  function show(t) {
    active = t; popEl.hidden = true; menuEl.hidden = true;
    tabs.forEach(function (x) { x.panel.hidden = x !== t; });
    root.querySelector(".nbb-search").style.visibility = t.id === "table" ? "visible" : "hidden";
    root.querySelector(".nbb-fbt2").style.visibility = t.id === "table" ? "visible" : "hidden";
    pbtn.style.visibility = t.id === "table" ? "visible" : "hidden";
    filEd.hidden = true;
    renderTabs(); if (t.onShow) t.onShow();
    persist();
  }
  tabsEl.addEventListener("click", function (e) {
    var x = e.target.closest("[data-close]");
    if (x) {
      var i = tabs.findIndex(function (t) { return t.id === x.getAttribute("data-close"); });
      var t = tabs[i]; t.panel.remove(); tabs.splice(i, 1);
      if (active === t) show(tabs[0]); else { renderTabs(); persist(); }
      e.stopPropagation(); return;
    }
    if (e.target.closest(".nbb-plus")) {
      var hasProf = tabs.some(function (t) { return t.id === "profile"; });
      openMenu(e.target.closest(".nbb-plus"), [
        ["Visualization", function () { show(addViz()); }],
        hasProf ? null : ["Data profile", function () { show(addProfile()); }]
      ].filter(Boolean));
      return;
    }
    var b = e.target.closest("[data-tab]");
    if (b) show(tabs.find(function (t) { return t.id === b.getAttribute("data-tab"); }));
  });

  // ------------------------------------------------------------- menu
  function openMenu(anchor, items) {
    menuEl.innerHTML = items.map(function (it, i) { return it === "-" ? '<div class="nbb-msep"></div>' : '<button class="nbb-mi" data-i="' + i + '">' + esc(it[0]) + "</button>"; }).join("");
    var rr = root.getBoundingClientRect(), ar = anchor.getBoundingClientRect();
    menuEl.hidden = false;
    var left = ar.left - rr.left; if (left + menuEl.offsetWidth > rr.width) left = ar.right - rr.left - menuEl.offsetWidth;
    menuEl.style.left = Math.max(4, left) + "px"; menuEl.style.top = (ar.bottom - rr.top + 4) + "px";
    menuEl.onclick = function (e) { var b = e.target.closest("[data-i]"); if (!b) return; menuEl.hidden = true; items[+b.getAttribute("data-i")][1](); };
  }
  document.addEventListener("mousedown", function (e) {
    if (!menuEl.hidden && !menuEl.contains(e.target) && !e.target.closest(".nbb-plus,.nbb-dlbtn")) menuEl.hidden = true;
  }, true);

  // ------------------------------------------------------------- table
  var view = rows.map(function (_, i) { return i; }), sort = { c: -1, dir: 0 }, q = "", sel = null, R = null, hay = [], filters = [];
  var widths = cols.map(function (c, ci) {
    var m = c.name.length + 5;
    for (var r = 0; r < Math.min(rows.length, 300); r++) { var v = rows[r][ci]; var s = v === null ? 4 : String(v).length; if (s > m) m = s; }
    return Math.max(90, Math.min(380, Math.round(m * 7.4) + 30));
  });
  var tablePanel = el('<div class="nbb-panel nbb-tpanel"><div class="nbb-tmain"><div class="nbb-fbar" hidden></div><div class="nbb-scroll" tabindex="0"><div class="nbb-head"></div><div class="nbb-canvas"></div></div></div><div class="nbb-side" hidden><div class="nbb-sin"></div></div></div>');
  var side = tablePanel.querySelector(".nbb-side"), sideIn = tablePanel.querySelector(".nbb-sin"), pbtn = root.querySelector(".nbb-pbtn"), sideCol = null;
  var fbar = tablePanel.querySelector(".nbb-fbar"), scroll = tablePanel.querySelector(".nbb-scroll"), head = tablePanel.querySelector(".nbb-head"), canvas = tablePanel.querySelector(".nbb-canvas");
  scroll.style.setProperty("--nbb-h", Math.min(HDR + Math.max(rows.length, 1) * RH + 2, 420) + "px");

  function applyWidths() {
    var tot = IDXW + widths.reduce(function (a, b) { return a + b; }, 0);
    root.style.setProperty("--nbb-cols", IDXW + "px " + widths.map(function (w) { return w + "px"; }).join(" "));
    root.style.setProperty("--nbb-w", tot + "px");
  }
  function rowHay(i) {
    if (hay[i] === undefined) hay[i] = rows[i].map(function (v, ci) { return valStr(v, cols[ci]); }).join("\u0001").toLowerCase();
    return hay[i];
  }
  function recompute() {
    var v = rows.map(function (_, i) { return i; });
    if (q) v = v.filter(function (i) { return rowHay(i).indexOf(q) !== -1; });
    if (filters.length) v = v.filter(function (i) { var r = rows[i]; for (var k = 0; k < filters.length; k++) if (!fMatch(filters[k], r[filters[k].c])) return false; return true; });
    if (sort.dir) {
      var c = sort.c, k = cols[c], d = sort.dir;
      var cmp = isNum(k) ? function (a, b) { var x = toNum(a), y = toNum(b), nx = x !== x, ny = y !== y; return nx || ny ? (nx === ny ? 0 : nx ? 1 : -1) : x - y; }
        : k.kind === "bool" ? function (a, b) { return a === b ? 0 : a ? 1 : -1; }
        : function (a, b) { return a < b ? -1 : a > b ? 1 : 0; };
      v.sort(function (i, j) {
        var a = rows[i][c], b = rows[j][c];
        if (a === null && b === null) return i - j;
        if (a === null) return 1;
        if (b === null) return -1;
        return ((cmp(a, b) || 0) * d) || i - j;
      });
    }
    view = v; sel = null;
  }
  function hl(t) {
    if (!q) return esc(t);
    var lt = t.toLowerCase(), out = "", i = 0, j;
    while ((j = lt.indexOf(q, i)) !== -1) { out += esc(t.slice(i, j)) + "<mark>" + esc(t.slice(j, j + q.length)) + "</mark>"; i = j + q.length; }
    return out + esc(t.slice(i));
  }
  function renderHead() {
    head.innerHTML = '<div class="nbb-row nbb-hrow"><div class="nbb-hc nbb-idx" title="Select all"></div>' + cols.map(function (c, ci) {
      var on = sort.c === ci && sort.dir, fon = filters.some(function (f) { return f.c === ci; }), nb = (on ? 1 : 0) + (fon ? 1 : 0);
      var s = '<span class="nbb-hb"><button class="nbb-filb' + (fon ? " nbb-on" : "") + '" data-fil="' + ci + '" title="Filter" tabindex="-1">' + ICONS.filter + '</button><button class="nbb-sortb' + (on ? " nbb-on" : "") + '" data-sort="' + ci + '" title="Sort" tabindex="-1">' + (on && sort.dir < 0 ? ICONS.down : ICONS.up) + "</button></span>";
      return '<div class="nbb-hc' + (nb ? " nbb-n" + nb : "") + '" data-c="' + ci + '" title="' + esc(c.name) + "\n" + esc(c.type) + '"><span class="nbb-ti">' + typeIcon(c) +
        '</span><span class="nbb-hn">' + esc(c.name) + '</span>' + s + '<span class="nbb-rz" data-rz="' + ci + '"></span></div>';
    }).join("") + "</div>";
    paintSel();
  }
  function cellHtml(v, c, p, ci) {
    var s = selCls(p, ci);
    var cls = "nbb-c" + (isNum(c) ? " nbb-num" : "") + s;
    if (v === null || v === undefined) return '<div class="' + cls + ' nbb-null" data-p="' + p + '" data-c="' + ci + '">null</div>';
    var t = valStr(v, c), long = c.kind === "complex" || t.length > 50;
    var shown = t.length > 400 ? t.slice(0, 400) + "…" : t;
    return '<div class="' + cls + (c.kind === "complex" ? " nbb-cx" : "") + '" data-p="' + p + '" data-c="' + ci + '">' + hl(shown) +
      (long ? '<button class="nbb-exp" data-exp="1" title="Expand (Enter)" tabindex="-1">⤢</button>' : "") + "</div>";
  }
  var pending = false;
  function renderRows() {
    pending = false; R = rectOf();
    canvas.style.height = view.length * RH + "px";
    if (!view.length) {
      canvas.innerHTML = '<div class="nbb-empty" style="position:sticky;left:0;width:' + scroll.clientWidth + 'px">' + (q || filters.length ? "No matching rows" : "Query returned no results") + "</div>";
      canvas.style.height = "auto"; return;
    }
    var st = scroll.scrollTop, h = scroll.clientHeight || 420;
    var start = Math.max(0, Math.floor((st - HDR) / RH) - 6), end = Math.min(view.length, Math.ceil((st + h) / RH) + 6);
    var out = [];
    for (var p = start; p < end; p++) {
      var row = rows[view[p]], cells = "";
      for (var ci = 0; ci < cols.length; ci++) cells += cellHtml(row[ci], cols[ci], p, ci);
      out.push('<div class="nbb-row nbb-brow" style="top:' + p * RH + 'px"><div class="nbb-c nbb-idx' + (R && p >= R.r0 && p <= R.r1 ? " nbb-selh" : "") + '" data-p="' + p + '">' + (p + 1) + "</div>" + cells + "</div>");
    }
    canvas.innerHTML = out.join("");
  }
  function schedule() { if (!pending) { pending = true; requestAnimationFrame(renderRows); } }
  scroll.addEventListener("scroll", schedule, { passive: true });
  if (window.ResizeObserver) new ResizeObserver(schedule).observe(scroll);

  // ---- filters (per column, AND-ed): header funnel button, toolbar "Filter", chips, right-click "Filter to this value"
  var OPLIST = {
    n: [["eq", "="], ["ne", "≠"], ["gt", ">"], ["ge", "≥"], ["lt", "<"], ["le", "≤"], ["btw", "between"], ["nul", "is null"], ["nn", "is not null"]],
    t: [["eq", "is"], ["bf", "before"], ["af", "after"], ["btw", "between"], ["nul", "is null"], ["nn", "is not null"]],
    b: [["t", "is true"], ["f", "is false"], ["nul", "is null"], ["nn", "is not null"]],
    s: [["ct", "contains"], ["nct", "does not contain"], ["eq", "equals"], ["ne", "does not equal"], ["sw", "starts with"], ["ew", "ends with"], ["nul", "is null"], ["nn", "is not null"]]
  };
  var NOARG = { nul: 1, nn: 1, t: 1, f: 1 };
  function fGroup(c) { return isNum(c) ? "n" : isTime(c) ? "t" : c.kind === "bool" ? "b" : "s"; }
  function opLabel(g, op) { var l = OPLIST[g].filter(function (o) { return o[0] === op; })[0]; return l ? l[1] : op; }
  function parseT(a, c) {
    var t = String(a).trim(); if (!t) return { ms: NaN, day: false };
    var day = /^\d{4}-\d\d-\d\d$/.test(t);
    if (day) t += "T00:00:00Z";
    else { t = t.replace(" ", "T"); if (!/(Z|[+-]\d\d:?\d\d)$/i.test(t)) t += "Z"; }
    return { ms: Date.parse(t), day: day };
  }
  function fPrep(f) {                       // returns true when the filter's values are valid
    var c = cols[f.c], g = fGroup(c), two = f.op === "btw";
    f.g = g;
    if (NOARG[f.op]) return true;
    if (g === "n") { f.x = Number(f.a); f.y = Number(f.b); return String(f.a).trim() !== "" && isFinite(f.x) && (!two || (String(f.b).trim() !== "" && isFinite(f.y))); }
    if (g === "t") { f.x = parseT(f.a, c); f.y = parseT(f.b, c); return isFinite(f.x.ms) && (!two || isFinite(f.y.ms)); }
    f.x = String(f.a).toLowerCase(); return true;
  }
  function fMatch(f, v) {
    var op = f.op; if (op === "nul") return v === null; if (op === "nn") return v !== null;
    if (v === null || v === undefined) return false;
    var g = f.g;
    if (g === "b") return op === "t" ? !!v : !v;
    if (g === "n") {
      var n = Number(v); if (n !== n) return false;
      switch (op) { case "eq": return n === f.x; case "ne": return n !== f.x; case "gt": return n > f.x; case "ge": return n >= f.x; case "lt": return n < f.x; case "le": return n <= f.x; case "btw": return n >= Math.min(f.x, f.y) && n <= Math.max(f.x, f.y); }
      return true;
    }
    if (g === "t") {
      var t = timeVal(v, cols[f.c]); if (t !== t) return false;
      switch (op) {
        case "eq": return f.x.day ? t >= f.x.ms && t < f.x.ms + 864e5 : t === f.x.ms;
        case "bf": return t < f.x.ms;
        case "af": return f.x.day ? t >= f.x.ms + 864e5 : t > f.x.ms;
        case "btw": var lo = Math.min(f.x.ms, f.y.ms), hi = Math.max(f.x.ms + (f.x.day ? 0 : 0), f.y.ms + (f.y.day ? 864e5 - 1 : 0)); return t >= lo && t <= hi;
      }
      return true;
    }
    var sv = valStr(v, cols[f.c]).toLowerCase();
    switch (op) { case "ct": return sv.indexOf(f.x) !== -1; case "nct": return sv.indexOf(f.x) === -1; case "eq": return sv === f.x; case "ne": return sv !== f.x; case "sw": return sv.indexOf(f.x) === 0; case "ew": return sv.length >= f.x.length && sv.lastIndexOf(f.x) === sv.length - f.x.length; }
    return true;
  }
  function chipText(f) {
    var g = fGroup(cols[f.c]), t = "<b>" + esc(cols[f.c].name) + "</b> " + esc(opLabel(g, f.op));
    if (!NOARG[f.op]) t += " " + esc(f.a) + (f.op === "btw" ? " and " + esc(f.b) : "");
    return t;
  }
  function renderChips() {
    fbar.hidden = !filters.length;
    fbar.innerHTML = filters.map(function (f, i) {
      return '<span class="nbb-chip" data-fi="' + i + '" title="Edit filter"><span class="nbb-ct">' + chipText(f) + '</span><span class="nbb-cx2" data-fx="' + i + '" title="Remove filter">×</span></span>';
    }).join("") + (filters.length > 1 ? '<button class="nbb-clr" data-fclr="1">Clear all</button>' : "");
  }
  function refilter() {
    closeFilter(); recompute(); scroll.scrollTop = 0; renderChips(); renderHead(); renderRows(); updateFooter(); refreshSide(); persist();
  }
  function addFilter(f, idx) {
    if (!fPrep(f)) return false;
    if (idx === null || idx === undefined) filters.push(f); else filters[idx] = f;
    refilter(); return true;
  }
  function removeFilter(i) { filters.splice(i, 1); refilter(); }
  function clearFilters() { filters = []; refilter(); }
  fbar.addEventListener("click", function (e) {
    if (e.target.closest("[data-fclr]")) return clearFilters();
    var x = e.target.closest("[data-fx]"); if (x) return removeFilter(+x.getAttribute("data-fx"));
    var ch = e.target.closest("[data-fi]"); if (ch) { var i = +ch.getAttribute("data-fi"); openFilter(filters[i].c, ch, i); }
  });
  root.querySelector(".nbb-fbt2").addEventListener("click", function (e) { openFilter(0, e.currentTarget, null); });

  var feState = null;
  function closeFilter() { filEd.hidden = true; feState = null; }
  function openFilter(ci, anchor, idx) {
    if (!cols.length) return;
    var ex = idx === null ? null : filters[idx];
    feState = { c: ex ? ex.c : ci, op: ex ? ex.op : null, a: ex ? ex.a : "", b: ex ? ex.b : "", idx: idx };
    function build() {
      var c = cols[feState.c], g = fGroup(c), ops = OPLIST[g];
      if (!feState.op || !ops.some(function (o) { return o[0] === feState.op; })) feState.op = ops[0][0];
      var ph = g === "t" ? (c.kind === "date" ? "YYYY-MM-DD" : "YYYY-MM-DD or ISO time") : g === "n" ? "Number" : "Value";
      filEd.innerHTML = '<div class="nbb-fh">' + (idx === null ? "Add filter" : "Edit filter") + "</div>" +
        '<select class="nbb-fi" data-k="c">' + cols.map(function (k, i) { return '<option value="' + i + '"' + (i === feState.c ? " selected" : "") + ">" + esc(k.name) + "</option>"; }).join("") + "</select>" +
        '<select class="nbb-fi" data-k="op">' + ops.map(function (o) { return '<option value="' + o[0] + '"' + (o[0] === feState.op ? " selected" : "") + ">" + esc(o[1]) + "</option>"; }).join("") + "</select>" +
        '<input class="nbb-fi" data-k="a" placeholder="' + ph + '" value="' + esc(feState.a) + '"' + (NOARG[feState.op] ? " hidden" : "") + ">" +
        '<input class="nbb-fi" data-k="b" placeholder="' + ph + ' (end)" value="' + esc(feState.b) + '"' + (feState.op === "btw" ? "" : " hidden") + ">" +
        '<div class="nbb-fa">' + (idx === null ? "" : '<button class="nbb-fb nbb-lnk" data-fa="rm">Remove</button>') + '<span class="nbb-sp"></span><button class="nbb-fb" data-fa="cancel">Cancel</button><button class="nbb-fb nbb-pri" data-fa="ok">Apply</button></div>';
    }
    build();
    var rr = root.getBoundingClientRect(), ar = anchor.getBoundingClientRect();
    filEd.hidden = false; menuEl.hidden = true;
    var left = ar.left - rr.left; if (left + filEd.offsetWidth > rr.width - 4) left = rr.width - filEd.offsetWidth - 4;
    filEd.style.left = Math.max(4, left) + "px"; filEd.style.top = (ar.bottom - rr.top + 4) + "px";
    function sync() { feState.a = filEd.querySelector('[data-k="a"]').value; feState.b = filEd.querySelector('[data-k="b"]').value; }
    function apply() {
      sync();
      var f = { c: feState.c, op: feState.op, a: feState.a, b: feState.b };
      if (!fPrep(f)) { Array.prototype.forEach.call(filEd.querySelectorAll("input:not([hidden])"), function (i) { i.classList.add("nbb-bad"); }); return; }
      addFilter(f, feState.idx);
    }
    filEd.onchange = function (e) {
      var k = e.target.getAttribute("data-k"); sync();
      if (k === "c") { feState.c = +e.target.value; feState.op = null; feState.a = ""; feState.b = ""; build(); }
      else if (k === "op") { feState.op = e.target.value; build(); }
      var fi = filEd.querySelector("input:not([hidden])"); if (fi && (k === "c" || k === "op")) fi.focus();
    };
    filEd.oninput = function (e) { e.target.classList.remove("nbb-bad"); };
    filEd.onclick = function (e) {
      var b = e.target.closest("[data-fa]"); if (!b) return; var a = b.getAttribute("data-fa");
      if (a === "ok") apply(); else if (a === "rm") removeFilter(feState.idx); else closeFilter();
    };
    filEd.onkeydown = function (e) {
      e.stopPropagation();
      if (e.key === "Enter" && e.target.tagName !== "SELECT") { e.preventDefault(); apply(); }
      else if (e.key === "Escape") { closeFilter(); if (active && active.id === "table") scroll.focus({ preventScroll: true }); }
    };
    var f0 = filEd.querySelector("input:not([hidden])"); if (f0) f0.focus(); else filEd.querySelector("select").focus();
  }
  document.addEventListener("mousedown", function (e) {
    if (!filEd.hidden && !filEd.contains(e.target) && !e.target.closest(".nbb-fbt2,[data-fil],.nbb-chip")) closeFilter();
  }, true);

  // ---- column profile side panel
  function singleFullCol() { return R && R.c0 === R.c1 && R.r0 === 0 && R.r1 === lastR() ? R.c0 : -1; }
  function renderSide() {
    if (sideCol === null || !cols[sideCol]) { side.hidden = true; pbtn.classList.remove("nbb-on"); return; }
    var c = cols[sideCol], filtered = view.length !== rows.length;
    side.hidden = false; pbtn.classList.add("nbb-on");
    sideIn.innerHTML = '<div class="nbb-sh"><span class="nbb-ti">' + typeIcon(c) + '</span><span class="nbb-hn" title="' + esc(c.name) + '">' + esc(c.name) + '</span><span class="nbb-sp"></span><button class="nbb-ibtn" data-sx="1" title="Close profile">×</button></div>' +
      '<div class="nbb-pnote">Profile of <b>' + fmtInt(view.length) + "</b> row" + (view.length === 1 ? "" : "s") + (filtered ? " (filtered)" : " shown") + (P.truncated && !filtered ? ", results truncated" : "") + ".</div>" +
      profRow(c, sideCol, view);
    schedule();
  }
  function refreshSide() { if (sideCol !== null) renderSide(); }
  function syncProfBtn() {
    var c = singleFullCol();
    if (c >= 0 && sideCol !== null && c !== sideCol) { sideCol = c; renderSide(); }     // follow the selected column while the panel is open
    pbtn.hidden = !(c >= 0 || sideCol !== null);
    pbtn.title = sideCol !== null ? "Close column profile" : "Show profile of the selected column";
  }
  pbtn.addEventListener("click", function () {
    if (sideCol !== null) { sideCol = null; renderSide(); syncProfBtn(); return; }
    var c = singleFullCol(); if (c < 0) return;
    sideCol = c; renderSide(); syncProfBtn();
  });
  side.addEventListener("click", function (e) { if (e.target.closest("[data-sx]")) { sideCol = null; renderSide(); syncProfBtn(); } });

  // ---- selection model: sel = {a:{r,c} anchor, f:{r,c} focus}; any rectangle of cells
  var NAMES = ["st", "sb", "sl", "sr", "act"], lastKey = "";
  function lastR() { return view.length - 1; }
  function lastC() { return cols.length - 1; }
  function rectOf() {
    if (!sel || !view.length) return null;
    return { r0: Math.min(sel.a.r, sel.f.r), r1: Math.max(sel.a.r, sel.f.r), c0: Math.min(sel.a.c, sel.f.c), c1: Math.max(sel.a.c, sel.f.c) };
  }
  function isMulti() { return !!R && (R.r0 !== R.r1 || R.c0 !== R.c1); }
  function selFlags(p, ci) {
    if (!R || p < R.r0 || p > R.r1 || ci < R.c0 || ci > R.c1) return null;
    return { st: p === R.r0, sb: p === R.r1, sl: ci === R.c0, sr: ci === R.c1, act: isMulti() && sel.a.r === p && sel.a.c === ci };
  }
  function selCls(p, ci) {
    var f = selFlags(p, ci); if (!f) return "";
    return " nbb-sel" + NAMES.map(function (n) { return f[n] ? " nbb-" + n : ""; }).join("");
  }
  function paintSel() {
    R = rectOf();
    var key = R ? [R.r0, R.r1, R.c0, R.c1, sel.a.r, sel.a.c].join(",") : "";
    var fullRows = !!R && R.c0 === 0 && R.c1 === lastC(), fullCols = !!R && R.r0 === 0 && R.r1 === lastR();
    Array.prototype.forEach.call(canvas.querySelectorAll(".nbb-brow"), function (rowEl) {
      Array.prototype.forEach.call(rowEl.children, function (cell) {
        var p = +cell.getAttribute("data-p"), cs = cell.getAttribute("data-c");
        if (cs === null) { cell.classList.toggle("nbb-selh", !!R && p >= R.r0 && p <= R.r1); return; }
        var f = selFlags(p, +cs);
        cell.classList.toggle("nbb-sel", !!f);
        NAMES.forEach(function (n) { cell.classList.toggle("nbb-" + n, !!f && !!f[n]); });
      });
    });
    Array.prototype.forEach.call(head.querySelectorAll(".nbb-hc"), function (h) {
      var cs = h.getAttribute("data-c");
      if (cs === null) h.classList.toggle("nbb-selh", fullRows && fullCols);
      else h.classList.toggle("nbb-selh", !!R && +cs >= R.c0 && +cs <= R.c1);
    });
    if (key !== lastKey) { lastKey = key; updateFooter(); syncProfBtn(); }
  }
  function setSel(a, f) { sel = { a: a, f: f }; paintSel(); }
  function selectAll() { if (view.length && cols.length) setSel({ r: 0, c: 0 }, { r: lastR(), c: lastC() }); }
  function selText(withHeaders) {
    var rc = rectOf(); if (!rc) return "";
    var out = [], c, r;
    function cell(v, col) { return v === null || v === undefined ? "" : valStr(v, col).replace(/[\t\n\r]/g, " "); }
    if (withHeaders) { var h = []; for (c = rc.c0; c <= rc.c1; c++) h.push(cols[c].name); out.push(h.join("\t")); }
    for (r = rc.r0; r <= rc.r1; r++) {
      var row = rows[view[r]], line = [];
      for (c = rc.c0; c <= rc.c1; c++) line.push(cell(row[c], cols[c]));
      out.push(line.join("\t"));
    }
    return out.join("\n");
  }
  function copySel(withHeaders) {
    var rc = rectOf(); if (!rc) return;
    var n = (rc.r1 - rc.r0 + 1) * (rc.c1 - rc.c0 + 1);
    var hdr = withHeaders === undefined ? (rc.r0 === 0 && rc.r1 === lastR() && (rc.c1 > rc.c0 || rc.r1 > rc.r0)) : withHeaders;
    copyText(selText(hdr)); toast(n === 1 ? "Copied cell" : "Copied " + fmtInt(n) + " cells" + (hdr ? " with headers" : ""));
  }

  // ---- hit-testing + drag (cell / row / column modes) with edge auto-scroll
  function hitTest(x, y) {
    var br = scroll.getBoundingClientRect();
    var xd = x - br.left - scroll.clientLeft + scroll.scrollLeft - IDXW, yd = y - br.top - scroll.clientTop + scroll.scrollTop - HDR;
    var c = 0, acc = 0;
    while (c < cols.length - 1 && xd >= acc + widths[c]) { acc += widths[c]; c++; }
    return { r: Math.max(0, Math.min(lastR(), Math.floor(yd / RH))), c: c };
  }
  function startDrag(mode) {
    var lx = null, ly = 0, raf = 0, done = false;
    function apply() {
      if (lx === null) return;
      var h = hitTest(lx, ly);
      var f = mode === "row" ? { r: h.r, c: lastC() } : mode === "col" ? { r: lastR(), c: h.c } : { r: h.r, c: h.c };
      if (f.r !== sel.f.r || f.c !== sel.f.c) setSel(sel.a, f);
    }
    function tick() {
      if (done) return;
      if (lx !== null) {
        var br = scroll.getBoundingClientRect(), E = 32, dx = 0, dy = 0;
        if (lx > br.right - E) dx = Math.min(40, 6 + (lx - (br.right - E)) / 2); else if (lx < br.left + IDXW + E) dx = -Math.min(40, 6 + ((br.left + IDXW + E) - lx) / 2);
        if (ly > br.bottom - E) dy = Math.min(40, 6 + (ly - (br.bottom - E)) / 2); else if (ly < br.top + HDR + E) dy = -Math.min(40, 6 + ((br.top + HDR + E) - ly) / 2);
        if (mode === "row") dx = 0; if (mode === "col") dy = 0;
        if (dx || dy) { var l0 = scroll.scrollLeft, t0 = scroll.scrollTop; scroll.scrollLeft += dx; scroll.scrollTop += dy; if (scroll.scrollLeft !== l0 || scroll.scrollTop !== t0) apply(); }
      }
      raf = requestAnimationFrame(tick);
    }
    function mv(ev) { lx = ev.clientX; ly = ev.clientY; apply(); }
    function up() { done = true; cancelAnimationFrame(raf); document.removeEventListener("mousemove", mv, true); document.removeEventListener("mouseup", up, true); }
    document.addEventListener("mousemove", mv, true); document.addEventListener("mouseup", up, true);
    raf = requestAnimationFrame(tick);
  }

  head.addEventListener("click", function (e) {
    var fb = e.target.closest("[data-fil]");
    if (fb) { var fc = +fb.getAttribute("data-fil"), fi = -1; filters.forEach(function (f, i) { if (fi < 0 && f.c === fc) fi = i; }); openFilter(fc, fb, fi < 0 ? null : fi); return; }
    var sb = e.target.closest("[data-sort]"); if (!sb) return;
    var c = +sb.getAttribute("data-sort");
    if (sort.c !== c) sort = { c: c, dir: 1 }; else sort.dir = sort.dir === 1 ? -1 : sort.dir === -1 ? 0 : 1;
    recompute(); renderHead(); renderRows(); updateFooter(); persist();
  });
  head.addEventListener("mousedown", function (e) {
    if (e.button !== 0) return;
    var rz = e.target.closest("[data-rz]");
    if (rz) {
      e.preventDefault(); e.stopPropagation();
      var ci = +rz.getAttribute("data-rz"), x0 = e.clientX, w0 = widths[ci];
      rz.classList.add("nbb-drag");
      var mv = function (ev) { widths[ci] = Math.max(48, w0 + ev.clientX - x0); applyWidths(); };
      var up = function () { rz.classList.remove("nbb-drag"); document.removeEventListener("mousemove", mv); document.removeEventListener("mouseup", up); };
      document.addEventListener("mousemove", mv); document.addEventListener("mouseup", up);
      return;
    }
    if (e.target.closest("[data-sort]") || e.target.closest("[data-fil]") || !view.length) return;
    e.preventDefault(); scroll.focus({ preventScroll: true });
    var hc = e.target.closest("[data-c]");
    if (!hc) { selectAll(); return; }                              // top-left corner
    var c = +hc.getAttribute("data-c"), ac = e.shiftKey && sel ? sel.a.c : c;
    setSel({ r: 0, c: ac }, { r: lastR(), c: c });
    startDrag("col");
  });
  head.addEventListener("dblclick", function (e) {         // double-click resize handle = autofit
    var rz = e.target.closest("[data-rz]"); if (!rz) return;
    var ci = +rz.getAttribute("data-rz"), m = cols[ci].name.length + 5;
    view.slice(0, 500).forEach(function (i) { var v = rows[i][ci]; m = Math.max(m, v === null ? 4 : Math.min(String(v).length, 120)); });
    widths[ci] = Math.round(m * 7.4) + 30; applyWidths();
  });
  canvas.addEventListener("mousedown", function (e) {
    var t = e.target.closest(".nbb-c"); if (!t) return;
    var p = +t.getAttribute("data-p"), cs = t.getAttribute("data-c");
    if (e.button !== 0) {                                              // right-click: keep an existing selection if it contains the cell
      if (!(R && p >= R.r0 && p <= R.r1 && (cs === null || (+cs >= R.c0 && +cs <= R.c1)))) setSel({ r: p, c: cs === null ? 0 : +cs }, { r: p, c: cs === null ? lastC() : +cs });
      return;
    }
    e.preventDefault(); scroll.focus({ preventScroll: true });
    if (cs === null) {                                                 // row number -> whole row
      var ar = e.shiftKey && sel ? sel.a.r : p;
      setSel({ r: ar, c: 0 }, { r: p, c: lastC() });
      startDrag("row");
    } else {
      var c = +cs;
      if (e.shiftKey && sel) setSel(sel.a, { r: p, c: c }); else setSel({ r: p, c: c }, { r: p, c: c });
      startDrag("cell");
    }
  });
  canvas.addEventListener("click", function (e) {
    if (e.target.closest("[data-exp]")) { var c = e.target.closest(".nbb-c[data-c]"); if (c) openPop(+c.getAttribute("data-p"), +c.getAttribute("data-c")); }
  });
  canvas.addEventListener("dblclick", function (e) {
    var c = e.target.closest(".nbb-c[data-c]"); if (c) openPop(+c.getAttribute("data-p"), +c.getAttribute("data-c"));
  });
  canvas.addEventListener("contextmenu", function (e) {
    var tc = e.target.closest(".nbb-c[data-c]");
    if (!R && !tc) return; e.preventDefault(); e.stopPropagation();   // keep JupyterLab's own context menu from also opening
    var x = e.clientX, y = e.clientY, anchor = { getBoundingClientRect: function () { return { left: x, right: x, top: y, bottom: y }; } };
    var n = R ? (R.r1 - R.r0 + 1) * (R.c1 - R.c0 + 1) : 0, items = [];
    if (R) items.push(["Copy" + (n > 1 ? " (" + fmtInt(n) + " cells)" : ""), function () { copySel(false); }], ["Copy with headers", function () { copySel(true); }]);
    if (tc) {
      var tci = +tc.getAttribute("data-c"), tv = rows[view[+tc.getAttribute("data-p")]][tci], tcol = cols[tci], g = fGroup(tcol);
      var lab = tv === null ? "null" : valStr(tv, tcol); if (lab.length > 24) lab = lab.slice(0, 24) + "…";
      var mk = function (inc) {
        return function () {
          var f = { c: tci, a: tv === null ? "" : valStr(tv, tcol), b: "" };
          if (tv === null) f.op = inc ? "nul" : "nn";
          else if (g === "b") f.op = (tv ? inc : !inc) ? "t" : "f";
          else f.op = inc ? "eq" : "ne";
          if (g === "t" && tv !== null && !inc) { f.op = "bf"; f.a = f.b = ""; return toast("Exclude isn't available for dates — use the column filter"); }
          addFilter(f);
        };
      };
      if (items.length) items.push("-");
      items.push(["Filter: " + tcol.name + " = " + lab, mk(true)], ["Exclude: " + tcol.name + " ≠ " + lab, mk(false)]);
      if (filters.length) items.push(["Clear all filters", clearFilters]);
    }
    openMenu(anchor, items);
  });
  function ensureVisible(p, c) {
    var top = p * RH, ch = scroll.clientHeight - HDR;
    if (top < scroll.scrollTop) scroll.scrollTop = top;
    else if (top + RH > scroll.scrollTop + ch) scroll.scrollTop = top + RH - ch;
    var left = IDXW; for (var i = 0; i < c; i++) left += widths[i];
    if (left - IDXW < scroll.scrollLeft) scroll.scrollLeft = left - IDXW;
    else if (left + widths[c] > scroll.scrollLeft + scroll.clientWidth) scroll.scrollLeft = left + widths[c] - scroll.clientWidth;
  }
  scroll.addEventListener("keydown", function (e) {
    var k = e.key, mod = e.metaKey || e.ctrlKey;
    if (!popEl.hidden) { if (k === "Escape") { closePop(); e.preventDefault(); e.stopPropagation(); } return; }
    if (!view.length) return;
    if (mod && k.toLowerCase() === "a") { selectAll(); e.preventDefault(); e.stopPropagation(); return; }
    if (!sel) { if (k.indexOf("Arrow") === 0) { setSel({ r: 0, c: 0 }, { r: 0, c: 0 }); e.preventDefault(); e.stopPropagation(); } return; }
    if (mod && k.toLowerCase() === "c") { copySel(); e.preventDefault(); e.stopPropagation(); return; }
    if (k === "Escape") { sel = null; paintSel(); e.stopPropagation(); return; }
    var p = sel.f.r, c = sel.f.c, ext = e.shiftKey && k !== "Tab";
    if (k === "Enter") { openPop(p, c); e.preventDefault(); e.stopPropagation(); return; }
    var page = Math.max(1, Math.floor(scroll.clientHeight / RH));
    if (k === "ArrowDown") p = mod ? lastR() : Math.min(lastR(), p + 1);
    else if (k === "ArrowUp") p = mod ? 0 : Math.max(0, p - 1);
    else if (k === "ArrowRight" || (k === "Tab" && !e.shiftKey)) c = mod ? lastC() : Math.min(lastC(), c + 1);
    else if (k === "ArrowLeft" || (k === "Tab" && e.shiftKey)) c = mod ? 0 : Math.max(0, c - 1);
    else if (k === "PageDown") p = Math.min(lastR(), p + page);
    else if (k === "PageUp") p = Math.max(0, p - page);
    else if (k === "Home") { c = 0; if (mod) p = 0; }
    else if (k === "End") { c = lastC(); if (mod) p = lastR(); }
    else return;
    e.preventDefault(); e.stopPropagation();
    if (ext) setSel(sel.a, { r: p, c: c }); else setSel({ r: p, c: c }, { r: p, c: c });
    ensureVisible(p, c); renderRows();
  });

  // ------------------------------------------------------------- cell popover
  function openPop(p, c) {
    var col = cols[c], v = rows[view[p]][c], s = valStr(v, col);
    var body = v === null ? '<span class="nbb-null">null</span>' : col.kind === "complex" ? prettyJson(s) : esc(s);
    popEl.innerHTML = '<div class="nbb-pop-h"><span class="nbb-ti">' + typeIcon(col) + "</span><span>" + esc(col.name) +
      '</span><span class="nbb-pm" title="' + esc(col.type) + '">row ' + (p + 1) + " · " + esc(col.type) + '</span>' +
      '<button class="nbb-ibtn" data-act="copy" title="Copy value">⧉</button><button class="nbb-ibtn" data-act="close" title="Close (Esc)">×</button></div><div class="nbb-pv' + (col.kind === "complex" ? " nbb-mono" : "") + '">' + body + "</div>";
    popEl.hidden = false;
    popEl.onclick = function (e) {
      var a = e.target.closest("[data-act]"); if (!a) return;
      if (a.getAttribute("data-act") === "copy") { copyText(col.kind === "complex" && v !== null ? JSON.stringify(JSON.parse(s), null, 2) : s); toast("Copied value"); }
      else closePop();
    };
  }
  function closePop() { if (popEl.hidden) return; popEl.hidden = true; if (active && active.id === "table") scroll.focus({ preventScroll: true }); }
  root.addEventListener("keydown", function (e) { if (e.key === "Escape" && !popEl.hidden) { closePop(); e.stopPropagation(); } });
  document.addEventListener("mousedown", function (e) { if (!popEl.hidden && !popEl.contains(e.target) && !e.target.closest(".nbb-exp")) closePop(); }, true);

  // ------------------------------------------------------------- search + export
  var searchTimer;
  searchIn.addEventListener("input", function () {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(function () { q = searchIn.value.trim().toLowerCase(); recompute(); scroll.scrollTop = 0; renderRows(); updateFooter(); refreshSide(); }, 120);
  });
  searchIn.addEventListener("keydown", function (e) { e.stopPropagation(); if (e.key === "Escape") { searchIn.value = ""; searchIn.dispatchEvent(new Event("input")); } });

  function exportText(sep, quoteAll) {
    function cell(v, c) {
      var s = v === null ? "" : valStr(v, c);
      if (sep === "md") return s.replace(/\|/g, "\\|").replace(/\n/g, " ");
      if (sep === "\t") return s.replace(/[\t\n\r]/g, " ");
      return /[",\n\r]/.test(s) || quoteAll ? '"' + s.replace(/"/g, '""') + '"' : s;
    }
    if (sep === "md") {
      var lines = ["| " + cols.map(function (c) { return cell(c.name); }).join(" | ") + " |", "|" + cols.map(function (c) { return isNum(c) ? " ---: " : " --- "; }).join("|") + "|"];
      view.forEach(function (i) { lines.push("| " + rows[i].map(function (v, ci) { return cell(v, cols[ci]); }).join(" | ") + " |"); });
      return lines.join("\n");
    }
    var out = [cols.map(function (c) { return cell(c.name); }).join(sep)];
    view.forEach(function (i) { out.push(rows[i].map(function (v, ci) { return cell(v, cols[ci]); }).join(sep)); });
    return out.join("\n");
  }
  root.querySelector(".nbb-dlbtn").addEventListener("click", function (e) {
    var n = fmtInt(view.length) + " row" + (view.length === 1 ? "" : "s");
    openMenu(e.currentTarget, [
      ["Download CSV (" + n + ")", function () {
        var a = document.createElement("a");
        a.href = URL.createObjectURL(new Blob(["﻿" + exportText(",")], { type: "text/csv;charset=utf-8" }));
        a.download = "export.csv"; document.body.appendChild(a); a.click(); a.remove();
        setTimeout(function () { URL.revokeObjectURL(a.href); }, 4000);
      }],
      "-",
      ["Copy as CSV", function () { copyText(exportText(",")); toast("Copied " + n + " as CSV"); }],
      ["Copy as TSV", function () { copyText(exportText("\t")); toast("Copied " + n + " as TSV"); }],
      ["Copy as Markdown", function () { copyText(exportText("md")); toast("Copied " + n + " as Markdown"); }]
    ]);
  });

  // ------------------------------------------------------------- footer
  function rel(ms) {
    var s = Math.round((Date.now() - ms) / 1000);
    if (s < 45) return "now";
    var m = Math.round(s / 60); if (m < 60) return m + " minute" + (m === 1 ? "" : "s") + " ago";
    var h = Math.round(m / 60); if (h < 24) return h + " hour" + (h === 1 ? "" : "s") + " ago";
    var d = Math.round(h / 24); return d + " day" + (d === 1 ? "" : "s") + " ago";
  }
  function updateFooter() {
    var parts = [];
    var nTxt = "<b>" + fmtInt(rows.length) + (P.truncated ? "+" : "") + "</b> row" + (rows.length === 1 ? "" : "s");
    if (q || filters.length) nTxt = "<b>" + fmtInt(view.length) + "</b> of " + nTxt;
    parts.push(nTxt);
    if (P.truncated) parts.push('<span class="nbb-trunc" title="Showing the first ' + fmtInt(P.limit) + ' rows. Call display(df, limit=N) to change the cap, or limit=None for all rows.">Truncated data</span>');
    parts.push(Number(P.elapsed).toFixed(2) + " seconds runtime");
    if (R && (R.r1 > R.r0 || R.c1 > R.c0)) parts.push(fmtInt(R.r1 - R.r0 + 1) + " × " + fmtInt(R.c1 - R.c0 + 1) + " selected");
    footL.innerHTML = parts.join(" &nbsp;|&nbsp; ");
    footR.textContent = "Refreshed " + rel(P.generatedAt);
  }
  var footTimer = setInterval(function () { if (!document.body.contains(root)) return clearInterval(footTimer); footR.textContent = "Refreshed " + rel(P.generatedAt); }, 30000);

  // ------------------------------------------------------------- visualization
  function niceScale(lo, hi, n) {
    if (!isFinite(lo) || !isFinite(hi)) { lo = 0; hi = 1; }
    if (lo === hi) { var d = lo === 0 ? 1 : Math.abs(lo) * 0.1; lo -= d; hi += d; }
    var span = hi - lo, step0 = Math.pow(10, Math.floor(Math.log10(span / n))), err = span / n / step0;
    var step = step0 * (err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1);
    var a = Math.floor(lo / step) * step, b = Math.ceil(hi / step) * step, ticks = [];
    for (var v = a; v <= b + step / 2; v += step) ticks.push(+v.toFixed(10));
    return { lo: a, hi: b, ticks: ticks };
  }
  function addViz(init) {
    vizCount++;
    var numIdx = [], catIdx = [];
    cols.forEach(function (c, i) { if (isNum(c)) numIdx.push(i); else if (c.kind !== "complex" && c.kind !== "binary") catIdx.push(i); });
    var x0 = catIdx.length ? catIdx[0] : 0;
    var y0 = numIdx.filter(function (i) { return i !== x0; })[0];
    var st = { type: "bar", x: x0, ys: y0 === undefined ? [] : [y0], group: -1, agg: y0 === undefined ? "count" : "sum", stacked: false, bins: 20, sort: "auto", top: 30, hidden: {} };
    if (init) st = init;
    var opt = function (i, label) { return '<option value="' + i + '">' + esc(label) + "</option>"; };
    var panel = el(
      '<div class="nbb-panel"><div class="nbb-viz"><div class="nbb-vctl">' +
      '<label>Visualization type<select data-k="type">' + [["bar", "Bar"], ["barh", "Horizontal bar"], ["line", "Line"], ["area", "Area"], ["combo", "Combo (bar + line)"], ["scatter", "Scatter"], ["pie", "Pie"], ["donut", "Donut"], ["heatmap", "Heatmap"], ["box", "Box plot"], ["histogram", "Histogram"], ["funnel", "Funnel"], ["counter", "Counter"], ["wordcloud", "Word cloud"]].map(function (t) { return opt(t[0], t[1]); }).join("") + "</select></label>" +
      '<label data-for="x"><span class="nbb-xlab">X column</span><select data-k="x">' + cols.map(function (c, i) { return opt(i, c.name); }).join("") + "</select></label>" +
      '<div class="nbb-vlab" data-for="ys">Y columns<div class="nbb-ylist">' + (numIdx.length ? numIdx.map(function (i) { return '<label><input type="checkbox" data-y="' + i + '"' + (st.ys.indexOf(i) !== -1 ? " checked" : "") + "> " + esc(cols[i].name) + "</label>"; }).join("") : '<span style="font-weight:400">No numeric columns</span>') + "</div></div>" +
      '<label data-for="agg">Aggregation<select data-k="agg">' + [["sum", "Sum"], ["avg", "Average"], ["count", "Count"], ["min", "Min"], ["max", "Max"]].map(function (t) { return opt(t[0], t[1]); }).join("") + "</select></label>" +
      '<label data-for="group"><span class="nbb-glab">Group by</span><select data-k="group"><option value="-1">None</option>' + catIdx.concat(numIdx.filter(function (i) { return cols[i].kind === "int"; })).map(function (i) { return opt(i, cols[i].name); }).join("") + "</select></label>" +
      '<label class="nbb-chk" data-for="stacked"><input type="checkbox" data-k="stacked"> Stacked</label>' +
      '<label data-for="sort">Sort<select data-k="sort">' + [["auto", "Auto (top values first)"], ["x", "X axis order"], ["desc", "Value, high to low"], ["asc", "Value, low to high"]].map(function (t) { return opt(t[0], t[1]); }).join("") + "</select></label>" +
      '<label data-for="top">Max X values<input type="number" data-k="top" min="1" max="1000" value="30"></label>' +
      '<label data-for="bins">Number of bins<input type="number" data-k="bins" min="2" max="200" value="20"></label>' +
      '</div><div class="nbb-vchart"><div class="nbb-vmsg"></div><svg></svg><div class="nbb-legend"></div><div class="nbb-tip" hidden></div></div></div></div>');
    var ctl = panel.querySelector(".nbb-vctl"), chart = panel.querySelector(".nbb-vchart"), svg = chart.querySelector("svg");
    var msg = chart.querySelector(".nbb-vmsg"), legend = chart.querySelector(".nbb-legend"), tip = chart.querySelector(".nbb-tip");
    ctl.querySelector('[data-k="type"]').value = st.type; ctl.querySelector('[data-k="x"]').value = st.x; ctl.querySelector('[data-k="agg"]').value = st.agg;
    ctl.querySelector('[data-k="group"]').value = st.group;
    if (ctl.querySelector('[data-k="group"]').value !== String(st.group)) st.group = -1;
    ctl.querySelector('[data-k="stacked"]').checked = st.stacked; ctl.querySelector('[data-k="bins"]').value = st.bins;
    ctl.querySelector('[data-k="sort"]').value = st.sort; ctl.querySelector('[data-k="top"]').value = st.top;
    function syncCtl() {
      var t = st.type, one = function (list) { return list.indexOf(t) !== -1; }, vis = {
        x: t !== "counter",
        ys: ((t !== "histogram" && st.agg !== "count") || t === "scatter" || t === "box") && t !== "wordcloud",
        agg: !one(["scatter", "histogram", "box", "wordcloud"]),
        group: one(["bar", "barh", "line", "area", "combo", "heatmap"]),
        stacked: one(["bar", "barh", "area"]),
        bins: t === "histogram",
        sort: one(["bar", "barh", "line", "area", "pie", "donut", "combo", "heatmap", "box", "funnel", "wordcloud"]),
        top: one(["bar", "barh", "line", "area", "pie", "donut", "combo", "heatmap", "box", "funnel", "wordcloud"])
      };
      Object.keys(vis).forEach(function (k) { var n = ctl.querySelector('[data-for="' + k + '"]'); if (n) n.style.display = vis[k] ? "" : "none"; });
      ctl.querySelector(".nbb-xlab").textContent = t === "histogram" ? "Column" : t === "wordcloud" ? "Words column" : "X column";
      ctl.querySelector(".nbb-glab").textContent = t === "heatmap" ? "Y axis category" : "Group by";
    }
    ctl.addEventListener("change", function (e) {
      var t = e.target, k = t.getAttribute("data-k");
      if (t.hasAttribute("data-y")) { st.ys = Array.prototype.map.call(ctl.querySelectorAll("[data-y]:checked"), function (n) { return +n.getAttribute("data-y"); }); }
      else if (k === "stacked") st.stacked = t.checked;
      else if (k === "type" || k === "agg" || k === "sort") st[k] = t.value;
      else if (k) st[k] = +t.value;
      st.hidden = {}; syncCtl(); draw(); persist();
    });
    legend.addEventListener("click", function (e) { var li = e.target.closest("[data-s]"); if (!li) return; var s = li.getAttribute("data-s"); st.hidden[s] = !st.hidden[s]; draw(); });
    svg.addEventListener("mousemove", function (e) {
      var n = e.target.closest("[data-tip]");
      if (!n) { tip.hidden = true; return; }
      tip.innerHTML = n.getAttribute("data-tip"); tip.hidden = false;
      var cr = chart.getBoundingClientRect(), x = e.clientX - cr.left + 14, y = e.clientY - cr.top + 14;
      if (x + tip.offsetWidth > cr.width) x = e.clientX - cr.left - tip.offsetWidth - 10;
      tip.style.left = x + "px"; tip.style.top = y + "px";
    });
    svg.addEventListener("mouseleave", function () { tip.hidden = true; });

    function keyOf(v, c) { return v === null || v === undefined ? "null" : valStr(v, c); }
    function aggregate() {
      var xc = cols[st.x], xs = new Map(), series = new Map(), ys = st.agg === "count" ? [-1] : st.ys;
      rows.forEach(function (row) {
        var xk = keyOf(row[st.x], xc); if (!xs.has(xk)) xs.set(xk, row[st.x]);
        var g = st.group >= 0 ? keyOf(row[st.group], cols[st.group]) : null;
        ys.forEach(function (yi) {
          var name = yi < 0 ? (g === null ? "count" : g) : g === null ? cols[yi].name : ys.length > 1 ? g + " · " + cols[yi].name : g;
          if (!series.has(name)) series.set(name, new Map());
          var m = series.get(name), a = m.get(xk);
          if (!a) { a = { sum: 0, n: 0, min: Infinity, max: -Infinity, rows: 0 }; m.set(xk, a); }
          a.rows++;
          if (yi >= 0) { var y = toNum(row[yi]); if (isFinite(y)) { a.sum += y; a.n++; if (y < a.min) a.min = y; if (y > a.max) a.max = y; } }
        });
      });
      var keys = Array.from(xs.keys());
      if (isNum(xc)) keys.sort(function (a, b) { return a === "null" ? 1 : b === "null" ? -1 : toNum(a) - toNum(b); });
      else keys.sort(function (a, b) { return a === "null" ? 1 : b === "null" ? -1 : a.localeCompare(b, undefined, { numeric: true }); });
      var out = [];
      series.forEach(function (m, name) {
        var vals = {};
        m.forEach(function (a, k) {
          vals[k] = st.agg === "count" ? a.rows : !a.n ? NaN : st.agg === "sum" ? a.sum : st.agg === "avg" ? a.sum / a.n : st.agg === "min" ? a.min : a.max;
        });
        out.push({ name: name, vals: vals });
      });
      out.sort(function (a, b) { return String(a.name).localeCompare(String(b.name), undefined, { numeric: true }); });
      return { keys: keys, series: out, xraw: xs };
    }
    var aggLabel = { sum: "Sum", avg: "Average", count: "Count", min: "Min", max: "Max" };

    function draw() {
      var W = Math.max(320, chart.clientWidth - 24), H = 360;
      sizeSvg(W, H);
      msg.textContent = ""; legend.innerHTML = ""; tip.hidden = true;
      if (!rows.length) { svg.innerHTML = ""; msg.textContent = "No data to plot."; return; }
      var t = st.type;
      if (t === "histogram") return drawHist(W, H);
      var needY = t === "box" || (t !== "scatter" && t !== "wordcloud" && st.agg !== "count");
      if (needY && !st.ys.length) { svg.innerHTML = ""; msg.textContent = "Select at least one Y column" + (t === "box" ? "." : " (or use Count)."); return; }
      if (t === "scatter") return drawScatter(W, H);
      if (t === "counter") return drawCounter(W);
      if (t === "box") return drawBox(W, H);
      if (t === "wordcloud") return drawWords(W);
      if (t === "heatmap" && st.group < 0) { svg.innerHTML = ""; msg.textContent = "Heatmap needs a \u201cY axis category\u201d column."; return; }
      var d = aggregate(), keys = d.keys, cap = st.top > 0 ? st.top : 1000;
      if (t === "pie" || t === "donut") cap = Math.min(cap, 50);
      var xc0 = cols[st.x], cont0 = (t === "line" || t === "area") && (isNum(xc0) || isTime(xc0));
      if (!cont0) {
        var mode = st.sort === "auto" ? (keys.length > cap || t === "pie" || t === "donut" || t === "funnel" ? "desc" : "x") : st.sort;
        if (mode !== "x") {
          var tot = {};
          d.series.forEach(function (sr) { keys.forEach(function (k) { var v = sr.vals[k]; if (isFinite(v)) tot[k] = (tot[k] || 0) + v; }); });
          keys = keys.slice().sort(function (a, b) { return (mode === "desc" ? (tot[b] || 0) - (tot[a] || 0) : (tot[a] || 0) - (tot[b] || 0)) || (a < b ? -1 : 1); });
        }
        if (keys.length > cap) { msg.textContent = "Showing " + (mode === "x" ? "the first " : mode === "asc" ? "the lowest " : "the top ") + cap + " of " + fmtInt(keys.length) + " X values" + (mode === "x" ? "." : " by value. Change Sort or Max X values to see more."); keys = keys.slice(0, cap); }
      } else if (keys.length > 1000) { msg.textContent = "Showing the first 1,000 of " + fmtInt(keys.length) + " X values."; keys = keys.slice(0, 1000); }
      var smax = t === "heatmap" ? 40 : 50, series = d.series.slice(0, smax);
      if (d.series.length > smax) msg.textContent += " Showing " + smax + " of " + d.series.length + " series.";
      series.forEach(function (s, i) { s.color = COLORS[i % COLORS.length]; });
      if (t === "pie" || t === "donut") return drawPie(W, H, keys, series[0], t === "donut");
      if (t === "heatmap") return drawHeat(W, keys, series);
      if (t === "funnel") return drawFunnel(W, keys, series[0]);
      renderLegend(series);
      var vis = series.filter(function (s) { return !st.hidden[s.name]; });
      if (t === "barh") return drawBarH(W, keys, vis);
      var xc = cols[st.x], cont = (t === "line" || t === "area") && (isNum(xc) || isTime(xc));
      drawXY(W, H, keys, vis, cont, d.xraw);
    }
    function renderLegend(series) {
      if (series.length < 2 && st.group < 0) { legend.innerHTML = ""; return; }
      legend.innerHTML = series.map(function (s) {
        return '<span class="nbb-li' + (st.hidden[s.name] ? " nbb-off" : "") + '" data-s="' + esc(s.name) + '"><span class="nbb-sw" style="background:' + s.color + '"></span>' + esc(s.name) + "</span>";
      }).join("");
    }
    function yAxis(lo, hi, m, W, H) {
      var sc = niceScale(lo, hi, 5), ys = function (v) { return m.t + (H - m.t - m.b) * (1 - (v - sc.lo) / (sc.hi - sc.lo)); };
      var g = sc.ticks.map(function (v) { var y = ys(v); return '<line class="nbb-grid" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + y + '" y2="' + y + '"/><text x="' + (m.l - 6) + '" y="' + (y + 4) + '" text-anchor="end">' + fmtNum(v) + "</text>"; }).join("");
      return { scale: ys, svg: g, sc: sc };
    }
    function yTitle(m, H) {
      var lab = st.type === "histogram" ? "Count" : st.agg === "count" ? "Count" : st.ys.length === 1 ? aggLabel[st.agg] + " of " + cols[st.ys[0]].name : aggLabel[st.agg];
      if (st.type === "scatter") lab = st.ys.length === 1 ? cols[st.ys[0]].name : "";
      return '<text transform="translate(12,' + (m.t + (H - m.t - m.b) / 2) + ') rotate(-90)" text-anchor="middle" style="font-weight:600">' + esc(lab) + "</text>";
    }
    function xLabels(keys, bandX, bw, m, H) {
      var maxLen = keys.reduce(function (a, k) { return Math.max(a, Math.min(k.length, 18)); }, 1);
      var rot = maxLen * 6.5 > bw, step = rot ? Math.max(1, Math.ceil(14 / bw)) : Math.max(1, Math.ceil(maxLen * 6.5 / bw));
      var y = H - m.b + 14, out = "";
      keys.forEach(function (k, i) {
        if (i % step) return;
        var lab = k.length > 18 ? k.slice(0, 17) + "…" : k, x = bandX(i) + bw / 2;
        out += rot ? '<text text-anchor="end" transform="translate(' + x + "," + (y - 4) + ') rotate(-40)">' + esc(lab) + "</text>" : '<text x="' + x + '" y="' + y + '" text-anchor="middle">' + esc(lab) + "</text>";
      });
      return out;
    }
    function bottomMargin(keys, bw) {
      var maxLen = keys.reduce(function (a, k) { return Math.max(a, Math.min(k.length, 18)); }, 1);
      return maxLen * 6.5 > bw ? Math.min(110, maxLen * 5 + 26) : 34;
    }
    function drawXY(W, H, keys, series, cont, xraw) {
      var t = st.type, xc = cols[st.x];
      var lo = Infinity, hi = -Infinity, stack = st.stacked && (t === "bar" || t === "area");
      if (stack) keys.forEach(function (k) { var p = 0, n = 0; series.forEach(function (s) { var v = s.vals[k]; if (isFinite(v)) { if (v >= 0) p += v; else n += v; } }); hi = Math.max(hi, p); lo = Math.min(lo, n); });
      else series.forEach(function (s) { keys.forEach(function (k) { var v = s.vals[k]; if (isFinite(v)) { lo = Math.min(lo, v); hi = Math.max(hi, v); } }); });
      if (t === "bar" || t === "area" || t === "combo" || !isFinite(lo)) { lo = Math.min(0, isFinite(lo) ? lo : 0); hi = Math.max(0, isFinite(hi) ? hi : 1); }
      var m = { t: 10, r: 16, l: 64, b: 34 };
      var bw0 = (W - m.l - m.r) / Math.max(keys.length, 1);
      if (!cont) m.b = bottomMargin(keys, bw0);
      var ya = yAxis(lo, hi, m, W, H), Y = ya.scale, base = Y(Math.max(ya.sc.lo, Math.min(0, ya.sc.hi)));
      var pw = W - m.l - m.r, body = "", xs, xTicks = "";
      if (cont) {
        var tv = function (k) { var r = xraw.get(k); return isTime(xc) ? timeVal(r, xc) : toNum(r); };
        var vals = keys.map(tv).filter(isFinite), xlo = Math.min.apply(null, vals), xhi = Math.max.apply(null, vals);
        if (xlo === xhi) { xlo -= 1; xhi += 1; }
        if (isTime(xc)) {
          xs = function (k) { return m.l + pw * (tv(k) - xlo) / (xhi - xlo); };
          var withT = xc.kind !== "date" && keys.some(function (k) { return !/T00:00:00(\.000)?/.test(String(xraw.get(k))); });
          for (var i = 0; i <= 5; i++) { var v = xlo + (xhi - xlo) * i / 5, xp = m.l + pw * i / 5; xTicks += '<text x="' + xp + '" y="' + (H - m.b + 14) + '" text-anchor="' + (i === 0 ? "start" : i === 5 ? "end" : "middle") + '">' + fmtTime(v, withT) + "</text>"; }
        } else {
          var sc = niceScale(xlo, xhi, 6); xlo = sc.lo; xhi = sc.hi;
          xs = function (k) { return m.l + pw * (tv(k) - xlo) / (xhi - xlo); };
          sc.ticks.forEach(function (v) { var xp = m.l + pw * (v - xlo) / (xhi - xlo); xTicks += '<text x="' + xp + '" y="' + (H - m.b + 14) + '" text-anchor="middle">' + fmtNum(v) + "</text>"; });
        }
        keys = keys.filter(function (k) { return isFinite(tv(k)); });
      } else {
        var bw = pw / Math.max(keys.length, 1);
        xs = function (k, i) { return m.l + bw * i + bw / 2; };
        xTicks = xLabels(keys, function (i) { return m.l + bw * i; }, bw, m, H);
      }
      var tipT = function (s, k, v) { return "<b>" + esc(xc.name) + ":</b> " + esc(k) + "<br>" + (series.length > 1 || st.group >= 0 ? "<b>" + esc(s.name) + ":</b> " : "<b>" + esc(st.agg === "count" ? "Count" : aggLabel[st.agg] + " of " + s.name) + ":</b> ") + fmtStat(v); };
      if (t === "bar" || t === "combo") {
        var bwb = pw / Math.max(keys.length, 1), inner = bwb * 0.8, pad = bwb * 0.1;
        var pos = {}, neg = {}, bs = t === "combo" ? series.slice(0, 1) : series;
        bs.forEach(function (s, si) {
          keys.forEach(function (k, i) {
            var v = s.vals[k]; if (!isFinite(v)) return;
            var x, w, y0, y1;
            if (stack) { var acc = v >= 0 ? pos : neg, b0 = acc[k] || 0; acc[k] = b0 + v; y0 = Y(b0); y1 = Y(b0 + v); x = m.l + bwb * i + pad; w = inner; }
            else { w = inner / bs.length; x = m.l + bwb * i + pad + w * si; y0 = base; y1 = Y(v); }
            body += '<rect x="' + x + '" y="' + Math.min(y0, y1) + '" width="' + Math.max(1, w - (stack ? 0 : 1)) + '" height="' + Math.max(0.5, Math.abs(y1 - y0)) + '" fill="' + s.color + '" data-tip="' + esc(tipT(s, k, v)) + '"/>';
          });
        });
      }
      if (t !== "bar") {
        var cum = {};
        (t === "combo" ? series.slice(1) : series).forEach(function (s) {
          var pts = [];
          keys.forEach(function (k, i) {
            var v = s.vals[k]; if (!isFinite(v)) return;
            var b0 = stack ? (cum[k] || 0) : 0; if (stack) cum[k] = b0 + v;
            pts.push({ x: xs(k, i), y: Y(b0 + v), y0: Y(b0), k: k, v: v });
          });
          if (!pts.length) return;
          if (cont) pts.sort(function (a, b) { return a.x - b.x; });
          var line = pts.map(function (p, i) { return (i ? "L" : "M") + p.x.toFixed(1) + "," + p.y.toFixed(1); }).join("");
          if (t === "area") {
            var back = pts.slice().reverse().map(function (p) { return "L" + p.x.toFixed(1) + "," + (stack ? p.y0 : base).toFixed(1); }).join("");
            body += '<path d="' + line + back + 'Z" fill="' + s.color + '" fill-opacity="' + (stack ? 0.55 : 0.25) + '" stroke="none"/>';
          }
          body += '<path d="' + line + '" fill="none" stroke="' + s.color + '" stroke-width="2" stroke-linejoin="round"/>';
          var r = pts.length > 120 ? 2 : 3.5;
          pts.forEach(function (p) { body += '<circle cx="' + p.x + '" cy="' + p.y + '" r="' + r + '" fill="' + s.color + '" data-tip="' + esc(tipT(s, p.k, p.v)) + '"/>'; });
        });
      }
      svg.innerHTML = ya.svg + '<line class="nbb-axis" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + (H - m.b) + '" y2="' + (H - m.b) + '"/>' + body + xTicks + yTitle(m, H);
    }
    function drawScatter(W, H) {
      var xc = cols[st.x];
      if (!(isNum(xc) || isTime(xc))) { svg.innerHTML = ""; msg.textContent = "Scatter needs a numeric or date X column."; return; }
      if (!st.ys.length) { svg.innerHTML = ""; msg.textContent = "Select at least one Y column."; return; }
      var xv = function (r) { return isTime(xc) ? timeVal(r[st.x], xc) : toNum(r[st.x]); };
      var groups = new Map();
      rows.forEach(function (r) {
        var x = xv(r); if (!isFinite(x)) return;
        st.ys.forEach(function (yi) {
          var y = toNum(r[yi]); if (!isFinite(y)) return;
          var g = st.group >= 0 ? keyOf(r[st.group], cols[st.group]) : null;
          var name = g === null ? cols[yi].name : st.ys.length > 1 ? g + " · " + cols[yi].name : g;
          if (!groups.has(name)) groups.set(name, []);
          groups.get(name).push([x, y]);
        });
      });
      var series = Array.from(groups.keys()).sort().slice(0, 50).map(function (n, i) { return { name: n, pts: groups.get(n), color: COLORS[i % COLORS.length] }; });
      renderLegend(series);
      var vis = series.filter(function (s) { return !st.hidden[s.name]; });
      var xlo = Infinity, xhi = -Infinity, ylo = Infinity, yhi = -Infinity;
      vis.forEach(function (s) { s.pts.forEach(function (p) { xlo = Math.min(xlo, p[0]); xhi = Math.max(xhi, p[0]); ylo = Math.min(ylo, p[1]); yhi = Math.max(yhi, p[1]); }); });
      var m = { t: 10, r: 16, l: 64, b: 34 }, ya = yAxis(ylo, yhi, m, W, H), Y = ya.scale, pw = W - m.l - m.r, xTicks = "", X;
      if (isTime(xc)) {
        if (xlo === xhi) { xlo -= 864e5; xhi += 864e5; }
        X = function (v) { return m.l + pw * (v - xlo) / (xhi - xlo); };
        for (var i = 0; i <= 5; i++) xTicks += '<text x="' + (m.l + pw * i / 5) + '" y="' + (H - m.b + 14) + '" text-anchor="' + (i === 0 ? "start" : i === 5 ? "end" : "middle") + '">' + fmtTime(xlo + (xhi - xlo) * i / 5, xc.kind !== "date") + "</text>";
      } else {
        var sc = niceScale(xlo, xhi, 6);
        X = function (v) { return m.l + pw * (v - sc.lo) / (sc.hi - sc.lo); };
        sc.ticks.forEach(function (v) { xTicks += '<text x="' + X(v) + '" y="' + (H - m.b + 14) + '" text-anchor="middle">' + fmtNum(v) + "</text>"; });
      }
      var body = "", total = 0;
      vis.forEach(function (s) {
        s.pts.forEach(function (p) {
          if (total++ > 20000) return;
          body += '<circle cx="' + X(p[0]).toFixed(1) + '" cy="' + Y(p[1]).toFixed(1) + '" r="3.5" fill="' + s.color + '" fill-opacity=".75" data-tip="' +
            esc("<b>" + esc(xc.name) + ":</b> " + (isTime(xc) ? fmtTime(p[0], xc.kind !== "date") : fmtStat(p[0])) + "<br><b>" + esc(s.name) + ":</b> " + fmtStat(p[1])) + '"/>';
        });
      });
      if (total > 20000) msg.textContent = "Plotting the first 20,000 points.";
      svg.innerHTML = ya.svg + '<line class="nbb-axis" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + (H - m.b) + '" y2="' + (H - m.b) + '"/>' + body + xTicks + yTitle(m, H) +
        '<text x="' + (m.l + pw / 2) + '" y="' + (H - 2) + '" text-anchor="middle" style="font-weight:600">' + esc(xc.name) + "</text>";
    }
    function drawPie(W, H, keys, s, donut) {
      if (!s) { svg.innerHTML = ""; msg.textContent = "Nothing to plot."; return; }
      var items = keys.map(function (k, i) { return { k: k, v: s.vals[k], color: COLORS[i % COLORS.length] }; }).filter(function (d) { return isFinite(d.v) && d.v > 0; });
      var total = items.reduce(function (a, d) { return a + d.v; }, 0);
      if (!total) { svg.innerHTML = ""; msg.textContent = "Pie charts need positive values."; return; }
      var vis = items.filter(function (d) { return !st.hidden[d.k]; }), vt = vis.reduce(function (a, d) { return a + d.v; }, 0) || 1;
      var cx = W / 2, cy = H / 2, R = Math.min(W, H) / 2 - 16, a0 = -Math.PI / 2, body = "", ri = donut ? R * 0.58 : 0;
      vis.forEach(function (d) {
        var a1 = a0 + 2 * Math.PI * d.v / vt, large = a1 - a0 > Math.PI ? 1 : 0, tipS = esc("<b>" + esc(d.k) + "</b><br>" + fmtStat(d.v) + " (" + (100 * d.v / vt).toFixed(1) + "%)");
        if (vis.length === 1) body += donut ? '<circle cx="' + cx + '" cy="' + cy + '" r="' + (R + ri) / 2 + '" fill="none" stroke="' + d.color + '" stroke-width="' + (R - ri) + '" data-tip="' + tipS + '"/>' : '<circle cx="' + cx + '" cy="' + cy + '" r="' + R + '" fill="' + d.color + '" data-tip="' + tipS + '"/>';
        else if (donut) body += '<path d="M' + (cx + R * Math.cos(a0)) + "," + (cy + R * Math.sin(a0)) + "A" + R + "," + R + " 0 " + large + " 1 " + (cx + R * Math.cos(a1)) + "," + (cy + R * Math.sin(a1)) +
          "L" + (cx + ri * Math.cos(a1)) + "," + (cy + ri * Math.sin(a1)) + "A" + ri + "," + ri + " 0 " + large + " 0 " + (cx + ri * Math.cos(a0)) + "," + (cy + ri * Math.sin(a0)) + 'Z" fill="' + d.color + '" stroke="var(--nbb-bg)" stroke-width="1" data-tip="' + tipS + '"/>';
        else body += '<path d="M' + cx + "," + cy + "L" + (cx + R * Math.cos(a0)) + "," + (cy + R * Math.sin(a0)) + "A" + R + "," + R + " 0 " + large + " 1 " + (cx + R * Math.cos(a1)) + "," + (cy + R * Math.sin(a1)) +
          'Z" fill="' + d.color + '" stroke="var(--nbb-bg)" stroke-width="1" data-tip="' + tipS + '"/>';
        var mid = (a0 + a1) / 2, pct = 100 * d.v / vt;
        if (pct >= 4) body += '<text x="' + (cx + (donut ? (R + ri) / 2 : R * 0.65) * Math.cos(mid)) + '" y="' + (cy + (donut ? (R + ri) / 2 : R * 0.65) * Math.sin(mid) + 4) + '" text-anchor="middle" style="fill:#fff;font-weight:600;pointer-events:none">' + pct.toFixed(0) + "%</text>";
        a0 = a1;
      });
      if (donut) body += '<text x="' + cx + '" y="' + (cy + 2) + '" text-anchor="middle" style="font-size:22px;font-weight:600;fill:var(--nbb-fg)">' + esc(fmtNum(vt)) + '</text><text x="' + cx + '" y="' + (cy + 20) + '" text-anchor="middle">Total</text>';
      svg.innerHTML = body;
      legend.innerHTML = items.map(function (d) { return '<span class="nbb-li' + (st.hidden[d.k] ? " nbb-off" : "") + '" data-s="' + esc(d.k) + '"><span class="nbb-sw" style="background:' + d.color + '"></span>' + esc(d.k) + "</span>"; }).join("");
    }
    function sizeSvg(W, H) { svg.setAttribute("viewBox", "0 0 " + W + " " + H); svg.setAttribute("height", H); }
    function ellip(s, n) { s = String(s); return s.length > n ? s.slice(0, n - 1) + "…" : s; }
    function xAxisTitle() { return st.agg === "count" ? "Count" : st.ys.length === 1 ? aggLabel[st.agg] + " of " + cols[st.ys[0]].name : aggLabel[st.agg]; }

    // ---- horizontal bar
    function drawBarH(W, keys, series) {
      var stack = st.stacked, lo = Infinity, hi = -Infinity;
      if (stack) keys.forEach(function (k) { var p = 0, n = 0; series.forEach(function (s) { var v = s.vals[k]; if (isFinite(v)) { if (v >= 0) p += v; else n += v; } }); hi = Math.max(hi, p); lo = Math.min(lo, n); });
      else series.forEach(function (s) { keys.forEach(function (k) { var v = s.vals[k]; if (isFinite(v)) { lo = Math.min(lo, v); hi = Math.max(hi, v); } }); });
      lo = Math.min(0, isFinite(lo) ? lo : 0); hi = Math.max(0, isFinite(hi) ? hi : 1);
      var perKey = stack ? 26 : Math.max(20, 13 * series.length + 8), maxLen = keys.reduce(function (a, k) { return Math.max(a, Math.min(k.length, 24)); }, 1);
      var m = { t: 8, r: 24, l: Math.max(56, Math.min(190, maxLen * 6.4 + 16)), b: 44 }, H = m.t + keys.length * perKey + m.b;
      sizeSvg(W, H);
      var sc = niceScale(lo, hi, 6), pw = W - m.l - m.r, X = function (v) { return m.l + pw * (v - sc.lo) / (sc.hi - sc.lo); }, base = X(Math.max(sc.lo, Math.min(0, sc.hi)));
      var grid = sc.ticks.map(function (v) { var x = X(v); return '<line class="nbb-grid" x1="' + x + '" x2="' + x + '" y1="' + m.t + '" y2="' + (H - m.b) + '"/><text x="' + x + '" y="' + (H - m.b + 14) + '" text-anchor="middle">' + fmtNum(v) + "</text>"; }).join("");
      var body = "", pos = {}, neg = {}, band = perKey * 0.78, pad = (perKey - band) / 2;
      keys.forEach(function (k, i) {
        var y0 = m.t + perKey * i;
        body += '<text x="' + (m.l - 6) + '" y="' + (y0 + perKey / 2 + 4) + '" text-anchor="end"><title>' + esc(k) + "</title>" + esc(ellip(k, 24)) + "</text>";
        series.forEach(function (s, si) {
          var v = s.vals[k]; if (!isFinite(v)) return;
          var x0, x1, h, y;
          if (stack) { var acc = v >= 0 ? pos : neg, b0 = acc[k] || 0; acc[k] = b0 + v; x0 = X(b0); x1 = X(b0 + v); h = band; y = y0 + pad; }
          else { h = band / series.length; y = y0 + pad + h * si; x0 = base; x1 = X(v); }
          body += '<rect x="' + Math.min(x0, x1) + '" y="' + y + '" width="' + Math.max(0.5, Math.abs(x1 - x0)) + '" height="' + Math.max(1, h - (stack ? 0 : 1)) + '" fill="' + s.color + '" data-tip="' +
            esc("<b>" + esc(cols[st.x].name) + ":</b> " + esc(k) + "<br><b>" + esc(series.length > 1 || st.group >= 0 ? s.name : xAxisTitle()) + ":</b> " + fmtStat(v)) + '"/>';
        });
      });
      svg.innerHTML = grid + '<line class="nbb-axis" x1="' + base + '" x2="' + base + '" y1="' + m.t + '" y2="' + (H - m.b) + '"/>' + body +
        '<text x="' + (m.l + pw / 2) + '" y="' + (H - 4) + '" text-anchor="middle" style="font-weight:600">' + esc(xAxisTitle()) + "</text>";
    }

    // ---- heatmap (X = columns, Group by = rows, colour = aggregated value)
    function drawHeat(W, keys, series) {
      var ch = 26, maxS = series.reduce(function (a, s) { return Math.max(a, Math.min(String(s.name).length, 22)); }, 1);
      var m = { t: 8, r: 16, l: Math.max(56, Math.min(170, maxS * 6.4 + 16)), b: 34 }, pw = W - m.l - m.r, cw = pw / Math.max(keys.length, 1);
      m.b = bottomMargin(keys, cw) + 30;
      var H = m.t + series.length * ch + m.b; sizeSvg(W, H);
      var lo = Infinity, hi = -Infinity;
      series.forEach(function (s) { keys.forEach(function (k) { var v = s.vals[k]; if (isFinite(v)) { lo = Math.min(lo, v); hi = Math.max(hi, v); } }); });
      if (!isFinite(lo)) { svg.innerHTML = ""; msg.textContent = "No values to plot."; return; }
      var span = hi - lo || 1, body = "";
      series.forEach(function (s, r) {
        body += '<text x="' + (m.l - 6) + '" y="' + (m.t + ch * r + ch / 2 + 4) + '" text-anchor="end"><title>' + esc(s.name) + "</title>" + esc(ellip(s.name, 22)) + "</text>";
        keys.forEach(function (k, c) {
          var v = s.vals[k], x = m.l + cw * c, y = m.t + ch * r;
          if (!isFinite(v)) { body += '<rect x="' + x + '" y="' + y + '" width="' + Math.max(1, cw - 1) + '" height="' + (ch - 1) + '" fill="var(--nbb-bg3)" fill-opacity=".5"/>'; return; }
          var tt = (v - lo) / span;
          body += '<rect x="' + x + '" y="' + y + '" width="' + Math.max(1, cw - 1) + '" height="' + (ch - 1) + '" fill="' + COLORS[0] + '" fill-opacity="' + (0.1 + 0.9 * tt).toFixed(3) + '" data-tip="' +
            esc("<b>" + esc(cols[st.x].name) + ":</b> " + esc(k) + "<br><b>" + esc(cols[st.group].name) + ":</b> " + esc(s.name) + "<br><b>" + esc(xAxisTitle()) + ":</b> " + fmtStat(v)) + '"/>';
          if (cw >= 40) body += '<text x="' + (x + cw / 2) + '" y="' + (y + ch / 2 + 4) + '" text-anchor="middle" style="pointer-events:none;font-size:10px;fill:' + (tt > 0.55 ? "#fff" : "var(--nbb-fg)") + '">' + esc(fmtNum(v)) + "</text>";
        });
      });
      var ly = H - 16, lx = m.l, lw = Math.min(180, pw);
      svg.innerHTML = '<defs><linearGradient id="' + ROOT_ID + 'hg"><stop offset="0" stop-color="' + COLORS[0] + '" stop-opacity=".1"/><stop offset="1" stop-color="' + COLORS[0] + '"/></linearGradient></defs>' + body +
        xLabels(keys, function (i) { return m.l + cw * i; }, cw, m, H) +
        '<rect x="' + lx + '" y="' + (ly - 8) + '" width="' + lw + '" height="8" rx="2" fill="url(#' + ROOT_ID + 'hg)"/><text x="' + lx + '" y="' + (ly + 8) + '">' + esc(fmtNum(lo)) + '</text><text x="' + (lx + lw) + '" y="' + (ly + 8) + '" text-anchor="end">' + esc(fmtNum(hi)) + "</text>";
    }

    // ---- box plot (distribution of the first Y column for each X value)
    function drawBox(W, H) {
      var xc = cols[st.x], yi = st.ys[0], groups = new Map();
      rows.forEach(function (r) { var y = toNum(r[yi]); if (!isFinite(y)) return; var k = keyOf(r[st.x], xc); if (!groups.has(k)) groups.set(k, []); groups.get(k).push(y); });
      var keys = Array.from(groups.keys()), cap = st.top > 0 ? st.top : 1000, total = keys.length;
      if (!keys.length) { svg.innerHTML = ""; msg.textContent = "No numeric values to plot."; return; }
      keys.sort(function (a, b) { return groups.get(b).length - groups.get(a).length || (a < b ? -1 : 1); });
      if (keys.length > cap) { keys = keys.slice(0, cap); msg.textContent = "Showing the " + cap + " most frequent of " + fmtInt(total) + " X values."; }
      var stats = {};
      keys.forEach(function (k) {
        var v = groups.get(k).slice().sort(function (a, b) { return a - b; }), q = function (p) { var i = (v.length - 1) * p, a = Math.floor(i), b = Math.ceil(i); return v[a] + (v[b] - v[a]) * (i - a); };
        var q1 = q(0.25), md = q(0.5), q3 = q(0.75), iqr = q3 - q1, lf = q1 - 1.5 * iqr, hf = q3 + 1.5 * iqr, wl = v[v.length - 1], wh = v[0], out = [];
        v.forEach(function (x) { if (x < lf || x > hf) out.push(x); else { if (x < wl) wl = x; if (x > wh) wh = x; } });
        stats[k] = { n: v.length, min: v[0], max: v[v.length - 1], q1: q1, md: md, q3: q3, wl: Math.min(wl, q1), wh: Math.max(wh, q3), out: out.slice(0, 200) };
      });
      if (st.sort === "desc" || st.sort === "asc") keys.sort(function (a, b) { return (st.sort === "desc" ? -1 : 1) * (stats[a].md - stats[b].md); });
      else keys.sort(function (a, b) { return a === "null" ? 1 : b === "null" ? -1 : isNum(xc) ? toNum(a) - toNum(b) : a.localeCompare(b, undefined, { numeric: true }); });
      var lo = Infinity, hi = -Infinity;
      keys.forEach(function (k) { var s = stats[k]; lo = Math.min(lo, s.wl, s.out.length ? Math.min.apply(null, s.out) : Infinity); hi = Math.max(hi, s.wh, s.out.length ? Math.max.apply(null, s.out) : -Infinity); });
      var m = { t: 10, r: 16, l: 64, b: 34 }, pw = W - m.l - m.r, bw = pw / keys.length;
      m.b = bottomMargin(keys, bw); sizeSvg(W, H);
      var ya = yAxis(lo, hi, m, W, H), Y = ya.scale, body = "", bx = Math.min(bw * 0.6, 60);
      keys.forEach(function (k, i) {
        var s = stats[k], cx = m.l + bw * i + bw / 2, tp = esc("<b>" + esc(xc.name) + ":</b> " + esc(k) + "<br>n: " + fmtInt(s.n) + "<br>max: " + fmtStat(s.max) + "<br>Q3: " + fmtStat(s.q3) + "<br>median: " + fmtStat(s.md) + "<br>Q1: " + fmtStat(s.q1) + "<br>min: " + fmtStat(s.min));
        body += '<line x1="' + cx + '" x2="' + cx + '" y1="' + Y(s.wh) + '" y2="' + Y(s.q3) + '" stroke="' + COLORS[0] + '" stroke-width="1.5"/><line x1="' + cx + '" x2="' + cx + '" y1="' + Y(s.q1) + '" y2="' + Y(s.wl) + '" stroke="' + COLORS[0] + '" stroke-width="1.5"/>' +
          '<line x1="' + (cx - bx / 4) + '" x2="' + (cx + bx / 4) + '" y1="' + Y(s.wh) + '" y2="' + Y(s.wh) + '" stroke="' + COLORS[0] + '" stroke-width="1.5"/><line x1="' + (cx - bx / 4) + '" x2="' + (cx + bx / 4) + '" y1="' + Y(s.wl) + '" y2="' + Y(s.wl) + '" stroke="' + COLORS[0] + '" stroke-width="1.5"/>' +
          '<rect x="' + (cx - bx / 2) + '" y="' + Y(s.q3) + '" width="' + bx + '" height="' + Math.max(1, Y(s.q1) - Y(s.q3)) + '" fill="' + COLORS[0] + '" fill-opacity=".35" stroke="' + COLORS[0] + '" stroke-width="1.5" data-tip="' + tp + '"/>' +
          '<line x1="' + (cx - bx / 2) + '" x2="' + (cx + bx / 2) + '" y1="' + Y(s.md) + '" y2="' + Y(s.md) + '" stroke="var(--nbb-fg)" stroke-width="2"/>';
        s.out.forEach(function (o) { body += '<circle cx="' + cx + '" cy="' + Y(o) + '" r="2.5" fill="' + COLORS[0] + '" fill-opacity=".6" data-tip="' + esc("<b>" + esc(k) + ":</b> " + fmtStat(o)) + '"/>'; });
      });
      svg.innerHTML = ya.svg + '<line class="nbb-axis" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + (H - m.b) + '" y2="' + (H - m.b) + '"/>' + body +
        xLabels(keys, function (i) { return m.l + bw * i; }, bw, m, H) +
        '<text transform="translate(12,' + (m.t + (H - m.t - m.b) / 2) + ') rotate(-90)" text-anchor="middle" style="font-weight:600">' + esc(cols[yi].name) + "</text>";
    }

    // ---- funnel (stages ranked by value, widths relative to the largest)
    function drawFunnel(W, keys, s) {
      var items = keys.map(function (k) { return { k: k, v: s ? s.vals[k] : NaN }; }).filter(function (d) { return isFinite(d.v) && d.v > 0; });
      if (!items.length) { svg.innerHTML = ""; msg.textContent = "Funnel charts need positive values."; return; }
      var sh = 40, H = items.length * sh + 12; sizeSvg(W, H);
      var mx = Math.max.apply(null, items.map(function (d) { return d.v; })), top = items[0].v, body = "", pw = W - 24;
      items.forEach(function (d, i) {
        var w = Math.max(4, pw * d.v / mx), x = (W - w) / 2, y = 6 + sh * i, color = COLORS[i % COLORS.length];
        var lab = ellip(d.k, 28) + " — " + fmtNum(d.v) + " (" + (100 * d.v / top).toFixed(d.v === top ? 0 : 1) + "%)", fits = w > lab.length * 6.4 + 16;
        body += '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + (sh - 6) + '" rx="3" fill="' + color + '" data-tip="' + esc("<b>" + esc(d.k) + "</b><br>" + xAxisTitle() + ": " + fmtStat(d.v) + "<br>" + (100 * d.v / top).toFixed(1) + "% of the first stage") + '"/>' +
          (fits ? '<text x="' + W / 2 + '" y="' + (y + (sh - 6) / 2 + 4) + '" text-anchor="middle" style="fill:#fff;font-weight:600;pointer-events:none">' + esc(lab) + "</text>"
            : '<text x="' + (x + w + 8) + '" y="' + (y + (sh - 6) / 2 + 4) + '" style="pointer-events:none">' + esc(lab) + "</text>");
      });
      svg.innerHTML = body;
    }

    // ---- counter (one big number per selected column, over all rows)
    function drawCounter(W) {
      var ys = st.agg === "count" ? [-1] : st.ys, per = Math.min(4, ys.length), rowsN = Math.ceil(ys.length / per), th = 120, H = rowsN * th; sizeSvg(W, H);
      var tw = W / per, body = "";
      ys.forEach(function (yi, i) {
        var v, n = 0, sum = 0, mn = Infinity, mx = -Infinity;
        if (yi < 0) v = rows.length;
        else {
          rows.forEach(function (r) { var y = toNum(r[yi]); if (isFinite(y)) { n++; sum += y; if (y < mn) mn = y; if (y > mx) mx = y; } });
          v = !n ? NaN : st.agg === "sum" ? sum : st.agg === "avg" ? sum / n : st.agg === "min" ? mn : mx;
        }
        var cx = tw * (i % per) + tw / 2, cy = th * Math.floor(i / per), txt = isFinite(v) ? v.toLocaleString("en-US", { maximumFractionDigits: 2 }) : "–";
        var fs = Math.max(20, Math.min(48, (tw - 24) / Math.max(txt.length, 3) * 1.7));
        body += '<text x="' + cx + '" y="' + (cy + 62) + '" text-anchor="middle" style="font-size:' + fs + 'px;font-weight:600;fill:var(--nbb-fg)">' + esc(txt) + "</text>" +
          '<text x="' + cx + '" y="' + (cy + 88) + '" text-anchor="middle" style="font-size:12px">' + esc(yi < 0 ? "Count" : aggLabel[st.agg] + " of " + cols[yi].name) + "</text>";
      });
      svg.innerHTML = body;
    }

    // ---- word cloud (size = how often a value occurs)
    function drawWords(W) {
      var counts = new Map();
      rows.forEach(function (r) { if (r[st.x] === null || r[st.x] === undefined) return; var k = valStr(r[st.x], cols[st.x]); counts.set(k, (counts.get(k) || 0) + 1); });
      var cap = Math.min(st.top > 0 ? st.top : 60, 150), all = Array.from(counts.entries()).sort(function (a, b) { return b[1] - a[1] || (a[0] < b[0] ? -1 : 1); }), words = all.slice(0, cap), H = 420;
      if (!words.length) { svg.innerHTML = ""; msg.textContent = "No values to plot."; return; }
      if (all.length > cap) msg.textContent = "Showing the top " + cap + " of " + fmtInt(all.length) + " values.";
      sizeSvg(W, H);
      var mx = words[0][1], mn = words[words.length - 1][1], placed = [], body = "", cx = W / 2, cy = H / 2;
      words.forEach(function (w, i) {
        var label = ellip(w[0], 26), t = mx === mn ? 1 : Math.sqrt((w[1] - mn) / (mx - mn)), size = 13 + 33 * t, tw = label.length * size * 0.56 + 6, th = size * 1.15, ok = false, x = cx, y = cy;
        for (var a = 0; a < 900 && !ok; a += 1) {
          var ang = a * 0.35, rad = 2.2 * a * 0.35 + (i ? 0 : 0);
          x = cx + rad * Math.cos(ang) * 1.5; y = cy + rad * Math.sin(ang);
          if (x - tw / 2 < 0 || x + tw / 2 > W || y - th / 2 < 0 || y + th / 2 > H) continue;
          ok = !placed.some(function (p) { return Math.abs(p.x - x) < (p.w + tw) / 2 && Math.abs(p.y - y) < (p.h + th) / 2; });
        }
        if (!ok) return;
        placed.push({ x: x, y: y, w: tw, h: th });
        body += '<text x="' + x.toFixed(1) + '" y="' + (y + size * 0.33).toFixed(1) + '" text-anchor="middle" style="font-size:' + size.toFixed(1) + 'px;font-weight:600;fill:' + COLORS[i % COLORS.length] + '" data-tip="' + esc("<b>" + esc(w[0]) + "</b><br>Count: " + fmtInt(w[1])) + '">' + esc(label) + "</text>";
      });
      svg.innerHTML = body;
    }
    function drawHist(W, H) {
      var c = cols[st.x];
      if (!isNum(c)) { svg.innerHTML = ""; msg.textContent = "Histogram needs a numeric column."; return; }
      var vals = rows.map(function (r) { return toNum(r[st.x]); }).filter(isFinite);
      if (!vals.length) { svg.innerHTML = ""; msg.textContent = "No numeric values."; return; }
      var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals), nb = Math.max(2, Math.min(200, st.bins || 20));
      if (lo === hi) { lo -= 0.5; hi += 0.5; }
      var w = (hi - lo) / nb, counts = new Array(nb).fill(0);
      vals.forEach(function (v) { counts[Math.min(nb - 1, Math.floor((v - lo) / w))]++; });
      var m = { t: 10, r: 16, l: 64, b: 34 }, ya = yAxis(0, Math.max.apply(null, counts), m, W, H), Y = ya.scale, pw = W - m.l - m.r, bw = pw / nb, body = "", xt = "";
      counts.forEach(function (n, i) {
        var a = lo + w * i, b = a + w;
        body += '<rect x="' + (m.l + bw * i + 0.5) + '" y="' + Y(n) + '" width="' + Math.max(1, bw - 1) + '" height="' + Math.max(0, Y(0) - Y(n)) + '" fill="' + COLORS[0] + '" data-tip="' + esc("<b>" + fmtStat(a) + " – " + fmtStat(b) + "</b><br>Count: " + fmtInt(n)) + '"/>';
      });
      for (var i = 0; i <= 5; i++) xt += '<text x="' + (m.l + pw * i / 5) + '" y="' + (H - m.b + 14) + '" text-anchor="middle">' + fmtNum(lo + (hi - lo) * i / 5) + "</text>";
      svg.innerHTML = ya.svg + '<line class="nbb-axis" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + (H - m.b) + '" y2="' + (H - m.b) + '"/>' + body + xt + yTitle(m, H) +
        '<text x="' + (m.l + pw / 2) + '" y="' + (H - 2) + '" text-anchor="middle" style="font-weight:600">' + esc(c.name) + "</text>";
    }
    syncCtl();
    if (window.ResizeObserver) { var rT; new ResizeObserver(function () { clearTimeout(rT); rT = setTimeout(function () { if (!panel.hidden) draw(); }, 80); }).observe(chart); }
    var vt = addTab("viz" + vizCount, init && init.label ? init.label : "Visualization " + vizCount, panel, true, function () { requestAnimationFrame(draw); });
    vt.st = st; return vt;
  }

  // ------------------------------------------------------------- data profile
  // ---- column profile (shared by the Data profile tab and the table's side panel)
  function stat(label, v) { return "<div><span>" + label + "</span><b title=\"" + esc(v) + "\">" + esc(v) + "</b></div>"; }
  function hist(vals) {
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals), nb = 24;
    if (lo === hi) { lo -= 0.5; hi += 0.5; }
    var w = (hi - lo) / nb, c = new Array(nb).fill(0);
    vals.forEach(function (v) { c[Math.min(nb - 1, Math.floor((v - lo) / w))]++; });
    var mx = Math.max.apply(null, c), W = 240, H = 64, bw = W / nb;
    return '<svg width="' + W + '" height="' + (H + 14) + '" style="overflow:visible">' + c.map(function (n, i) {
      var h = n ? Math.max(1, H * n / mx) : 0;
      return '<rect x="' + (i * bw + 0.5) + '" y="' + (H - h) + '" width="' + (bw - 1) + '" height="' + h + '" fill="#077A9D" fill-opacity=".8"><title>' + fmtStat(lo + w * i) + " – " + fmtStat(lo + w * (i + 1)) + ": " + n + "</title></rect>";
    }).join("") + '<text x="0" y="' + (H + 12) + '" style="font-size:10px;fill:var(--nbb-fg3)">' + fmtNum(lo) + '</text><text x="' + W + '" y="' + (H + 12) + '" text-anchor="end" style="font-size:10px;fill:var(--nbb-fg3)">' + fmtNum(hi) + "</text></svg>";
  }
  function profRow(c, ci, src) {
    var c_ = c, n = src ? src.length : rows.length;
        var nn = 0, distinct = new Map();
        for (var r = 0; r < n; r++) { var v = rows[src ? src[r] : r][ci]; if (v === null || v === undefined) continue; nn++; var k = valStr(v, c); distinct.set(k, (distinct.get(k) || 0) + 1); }
        var miss = n - nn, mp = n ? 100 * miss / n : 0, stats = "", viz = "";
        stats += stat("Count", fmtInt(nn)) + stat("Missing", fmtInt(miss) + " (" + mp.toFixed(mp && mp < 1 ? 2 : 1) + "%)") + stat("Distinct", fmtInt(distinct.size) + (nn ? " (" + (100 * distinct.size / nn).toFixed(1) + "%)" : ""));
        if (isNum(c)) {
          var vals = []; for (var r2 = 0; r2 < n; r2++) { var x = toNum(rows[src ? src[r2] : r2][ci]); if (isFinite(x)) vals.push(x); }
          if (vals.length) {
            var srt = vals.slice().sort(function (a, b) { return a - b; }), sum = 0, zeros = 0;
            vals.forEach(function (x) { sum += x; if (x === 0) zeros++; });
            var mean = sum / vals.length, sq = 0; vals.forEach(function (x) { sq += (x - mean) * (x - mean); });
            var qtl = function (p) { var i = (srt.length - 1) * p, a = Math.floor(i), b = Math.ceil(i); return srt[a] + (srt[b] - srt[a]) * (i - a); };
            stats += stat("Mean", fmtStat(mean)) + stat("Std dev", fmtStat(vals.length > 1 ? Math.sqrt(sq / (vals.length - 1)) : 0)) + stat("Min", fmtStat(srt[0])) +
              stat("Median", fmtStat(qtl(0.5))) + stat("Max", fmtStat(srt[srt.length - 1])) + stat("Zeros", fmtInt(zeros));
            viz = hist(vals);
          }
        } else {
          if (isTime(c) && nn) {
            var ks = Array.from(distinct.keys()).sort();
            stats += stat("Min", ks[0]) + stat("Max", ks[ks.length - 1]);
          } else if (c.kind === "string" && nn) {
            var tl = 0, mn = Infinity, mx = 0, empty = 0;
            distinct.forEach(function (cnt, k) { tl += k.length * cnt; mn = Math.min(mn, k.length); mx = Math.max(mx, k.length); if (!k.length) empty += cnt; });
            stats += stat("Avg length", (tl / nn).toFixed(1)) + stat("Min length", fmtInt(mn)) + stat("Max length", fmtInt(mx)) + stat("Empty", fmtInt(empty));
          }
          if (nn && c.kind !== "complex" && c.kind !== "binary") {
            var top = Array.from(distinct.entries()).sort(function (a, b) { return b[1] - a[1]; }).slice(0, 5), mxc = top.length ? top[0][1] : 1;
            viz = '<div class="nbb-ptop">' + top.map(function (e) {
              return '<div><span class="nbb-tr" title="' + esc(e[0]) + '"><i style="width:' + Math.max(2, 100 * e[1] / mxc) + '%"></i><em>' + esc(e[0]) + "</em></span><small>" + (100 * e[1] / nn).toFixed(1) + "%</small></div>";
            }).join("") + (distinct.size > 5 ? '<div style="color:var(--nbb-fg3)">+ ' + fmtInt(distinct.size - 5) + " other values</div>" : "") + "</div>";
          }
        }
        return '<div class="nbb-prow"><div><div class="nbb-pname"><span class="nbb-ti">' + typeIcon(c) + "</span><span>" + esc(c.name) + '</span></div><div class="nbb-ptype">' + esc(c.type) +
          '</div><div class="nbb-pbar" title="' + (100 - mp).toFixed(1) + '% present"><span style="width:' + (100 - mp) + '%;background:#00A972"></span><span style="width:' + mp + '%;background:#FF3621"></span></div></div><div class="nbb-pstats">' + stats + "</div><div>" + viz + "</div></div>";
  }

  function addProfile() {
    var panel = el('<div class="nbb-panel"><div class="nbb-prof"></div></div>'), box = panel.firstChild, done = false;
    function build() {
      var n = rows.length, out = ['<div class="nbb-pnote">Profile of the <b>' + fmtInt(n) + "</b> rows shown" + (P.truncated ? " (results are truncated, so statistics cover only these rows)" : "") + ".</div>"];
      cols.forEach(function (c, ci) { out.push(profRow(c, ci, null)); });
      box.innerHTML = out.join("");
    }
    return addTab("profile", "Data profile", panel, true, function () { if (!done) { done = true; build(); } });
  }

  // ------------------------------------------------------------- boot
  if (cols.length) {
    applyWidths(); renderHead();
    show(addTab("table", "Table", tablePanel, false));
    var sv = null;
    try { var raw = P.key ? localStorage.getItem(STORE_KEY) : null; if (raw) sv = JSON.parse(raw); } catch (e) {}
    // bring back sort + filters from the previous run of this cell
    try {
      if (sv && sv.tbl) {
        var sc = sv.tbl.sort ? colIdx(sv.tbl.sort.c) : -1;
        if (sc >= 0) sort = { c: sc, dir: sv.tbl.sort.dir === -1 ? -1 : 1 };
        (sv.tbl.filters || []).forEach(function (sf) {
          var fc = colIdx(sf.c); if (fc < 0) return;
          var f = { c: fc, op: sf.op, a: sf.a == null ? "" : String(sf.a), b: sf.b == null ? "" : String(sf.b) };
          if (!OPLIST[fGroup(cols[fc])].some(function (o) { return o[0] === f.op; })) return;
          if (fPrep(f)) filters.push(f);
        });
        if (sc >= 0 || filters.length) { recompute(); renderChips(); renderHead(); }
      }
    } catch (e) {}
    renderRows(); updateFooter();
    // bring back visualizations / profile from the previous run of this cell, now fed with the latest data
    try { if (sv) { var made = [];
      sv.tabs.forEach(function (it, i) {
        var tb = null;
        if (it.k === "viz") { var cfg = resolveViz(it.cfg); if (cfg) { cfg.label = it.label; tb = addViz(cfg); } }
        else if (it.k === "profile" && !tabs.some(function (t) { return t.id === "profile"; })) tb = addProfile();
        made[i] = tb;
      });
      vizCount = Math.max(vizCount, sv.vc || 0);
      show(made[sv.active] || tabs[0]);        // always re-sync panel visibility (restored panels start visible)
    } } catch (e) {}
    // nbutils.data.summarize(df): open the profile tab
    try { if (P.openTab === "profile") { show(tabs.find(function (t) { return t.id === "profile"; }) || addProfile()); } } catch (e) {}
    restoring = false; persist();
  }
  updateFooter();
})();
