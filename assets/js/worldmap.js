/* DEEPKIN — Field Archive: mapa interactivo del mundo (pagina Mundo).
   Pan/zoom con rueda, arrastre y pellizco; panel lateral (escritorio) u hoja inferior (movil);
   vista del continente por niveles de profundidad (superficie, −1, −2, −3) y plano de Dustline.
   Datos: #worldmap-data, generado de world_map.json (2026-10-09; niveles 2026-10-12). */
(function () {
  "use strict";
  var root = document.querySelector("[data-worldmap]");
  if (!root) return;
  var D = JSON.parse(document.getElementById("worldmap-data").textContent);
  var T = D.t;
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var $ = function (s, r) { return (r || root).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || root).querySelectorAll(s)); };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
  var panel = $(".wm-panel"), panelIn = $(".wm-panel-in");
  var LEVELS = [0, -1, -2, -3];

  // ---------- Visor con pan/zoom ----------
  function Viewer(frame, opts) {
    var vp = $(".wm-viewport", frame), stage = $(".wm-stage", frame), svg = $("svg", stage);
    var vbw = svg.viewBox.baseVal.width;
    var scaled = $$(".wm-sc", svg);
    var tip = $(".wm-tip", frame);
    var s = 1, x = 0, y = 0, MIN = 1, MAX = 6;
    var pts = {}, drag = null, pinch = null;
    var HIT = "[data-vlink],[data-ghost],[data-id]";

    function size() { return { w: vp.clientWidth, h: vp.clientHeight }; }
    function clamp() {
      var z = size();
      s = Math.min(MAX, Math.max(MIN, s));
      x = Math.min(0, Math.max(z.w - z.w * s, x));
      y = Math.min(0, Math.max(z.h - z.h * s, y));
    }
    function apply(animate) {
      clamp();
      stage.classList.toggle("anim", !!animate && !reduced);
      stage.style.transform = "translate(" + x.toFixed(1) + "px," + y.toFixed(1) + "px) scale(" + s.toFixed(4) + ")";
      // Marcas en px de pantalla: 1 unidad = 1 px sin importar el zoom ni el ancho.
      // En pantallas angostas las marcas se achican (hasta 60%) para no tapar el corredor inicial.
      var fit = vp.clientWidth / vbw, k = Math.min(1, Math.max(0.6, vp.clientWidth / 900)) / (fit * s);
      if (!isFinite(k) || k <= 0) return; // panel oculto o sin layout todavia
      scaled.forEach(function (g) {
        g.setAttribute("transform", "translate(" + g.getAttribute("data-x") + "," + g.getAttribute("data-y") + ") scale(" + k.toFixed(4) + ")");
      });
      frame.classList.toggle("zoomed", s > 1.01);
      frame.classList.toggle("lowzoom", fit * s < 0.45);
      vp.style.touchAction = s > 1.01 ? "none" : "pan-y";
    }
    function zoomAt(px, py, ns, animate) {
      ns = Math.min(MAX, Math.max(MIN, ns));
      x = px - (px - x) * (ns / s);
      y = py - (py - y) * (ns / s);
      s = ns;
      apply(animate);
    }
    function local(ev) { var r = vp.getBoundingClientRect(); return { x: ev.clientX - r.left, y: ev.clientY - r.top }; }

    vp.addEventListener("wheel", function (ev) {
      var ns = Math.min(MAX, Math.max(MIN, s * Math.exp(-ev.deltaY * (ev.deltaMode === 1 ? 0.05 : 0.0016))));
      if (Math.abs(ns - s) < 1e-4) return; // en el limite, deja scrollear la pagina
      ev.preventDefault();
      var p = local(ev);
      zoomAt(p.x, p.y, ns);
    }, { passive: false });

    vp.addEventListener("pointerdown", function (ev) {
      if (ev.button !== undefined && ev.button > 0) return;
      pts[ev.pointerId] = local(ev);
      var ids = Object.keys(pts);
      if (ids.length === 1) {
        var t = ev.target.closest ? ev.target.closest(HIT) : null;
        drag = { sx: pts[ev.pointerId].x, sy: pts[ev.pointerId].y, x0: x, y0: y, moved: false, target: t };
      } else if (ids.length === 2) {
        var a = pts[ids[0]], b = pts[ids[1]];
        pinch = { d: Math.hypot(a.x - b.x, a.y - b.y) || 1, s0: s, mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2, x0: x, y0: y };
        if (drag) drag.moved = true;
      }
      try { vp.setPointerCapture(ev.pointerId); } catch (e) {}
    });
    vp.addEventListener("pointermove", function (ev) {
      if (ev.pointerType === "mouse" && tip) hover(ev);
      if (!pts[ev.pointerId]) return;
      pts[ev.pointerId] = local(ev);
      var ids = Object.keys(pts);
      if (pinch && ids.length >= 2) {
        var a = pts[ids[0]], b = pts[ids[1]];
        var ns = Math.min(MAX, Math.max(MIN, pinch.s0 * Math.hypot(a.x - b.x, a.y - b.y) / pinch.d));
        var mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
        x = mx - (pinch.mx - pinch.x0) * (ns / pinch.s0);
        y = my - (pinch.my - pinch.y0) * (ns / pinch.s0);
        s = ns;
        apply();
      } else if (drag) {
        var p = pts[ev.pointerId], dx = p.x - drag.sx, dy = p.y - drag.sy;
        if (!drag.moved && Math.hypot(dx, dy) > 5) { drag.moved = true; frame.classList.add("dragging"); }
        if (drag.moved && s > 1.01) { x = drag.x0 + dx; y = drag.y0 + dy; apply(); }
      }
    });
    function end(ev) {
      if (!pts[ev.pointerId]) return;
      delete pts[ev.pointerId];
      var left = Object.keys(pts).length;
      if (left < 2) pinch = null;
      if (left === 0) {
        if (drag && !drag.moved && ev.type === "pointerup") opts.onPick(drag.target);
        drag = null;
        frame.classList.remove("dragging");
      } else if (left === 1) {
        var id = Object.keys(pts)[0];
        drag = { sx: pts[id].x, sy: pts[id].y, x0: x, y0: y, moved: true, target: null };
      }
    }
    vp.addEventListener("pointerup", end);
    vp.addEventListener("pointercancel", end);

    function hover(ev) {
      var t = ev.target.closest ? ev.target.closest("[data-tip],[data-id]") : null;
      var text = null;
      if (t) {
        if (t.hasAttribute("data-tip")) text = t.getAttribute("data-tip");
        else { var info = D.zones[t.getAttribute("data-id")] || D.districts[t.getAttribute("data-id")]; text = info && info.name; }
      }
      if (!text || frame.classList.contains("dragging")) { tip.hidden = true; return; }
      var r = frame.getBoundingClientRect();
      tip.textContent = text;
      tip.hidden = false;
      var tx = ev.clientX - r.left + 14, ty = ev.clientY - r.top + 16;
      tip.style.transform = "translate(" + Math.max(8, Math.min(tx, r.width - tip.offsetWidth - 8)) + "px," + Math.min(ty, r.height - 34) + "px)";
    }
    vp.addEventListener("pointerleave", function () { if (tip) tip.hidden = true; });

    vp.addEventListener("keydown", function (ev) {
      var z = size(), step = 60;
      if (ev.key === "+" || ev.key === "=") zoomAt(z.w / 2, z.h / 2, s * 1.4, true);
      else if (ev.key === "-" || ev.key === "_") zoomAt(z.w / 2, z.h / 2, s / 1.4, true);
      else if (ev.key === "0") { s = 1; x = y = 0; apply(true); }
      else if (ev.key === "ArrowLeft") { x += step; apply(true); }
      else if (ev.key === "ArrowRight") { x -= step; apply(true); }
      else if (ev.key === "ArrowUp") { y += step; apply(true); }
      else if (ev.key === "ArrowDown") { y -= step; apply(true); }
      else if (ev.key === "PageDown" && opts.onDive) opts.onDive(-1);
      else if (ev.key === "PageUp" && opts.onDive) opts.onDive(1);
      else return;
      ev.preventDefault();
    });
    $$("[data-zoom]", frame).forEach(function (b) {
      b.addEventListener("click", function () {
        var z = size(), k = b.getAttribute("data-zoom");
        if (k === "reset") { s = 1; x = y = 0; apply(true); } else zoomAt(z.w / 2, z.h / 2, k === "in" ? s * 1.6 : s / 1.6, true);
      });
    });
    window.addEventListener("resize", function () { apply(); });
    window.addEventListener("load", function () { apply(); });

    return {
      apply: apply,
      // Centra un punto del SVG (unidades del viewBox) con al menos ese zoom.
      focus: function (ux, uy, minS, shiftX) {
        var z = size(), fit = z.w / vbw;
        s = Math.max(s, minS || 1);
        x = z.w / 2 - (shiftX || 0) - ux * fit * s;
        y = z.h / 2 - uy * fit * s;
        apply(true);
      }
    };
  }

  // ---------- Panel ----------
  var mobile = window.matchMedia("(max-width: 720px)");
  // A pending hide from closePanel must never win over a newer openPanel.
  var hideTimer = 0;
  function openPanel(html) {
    clearTimeout(hideTimer);
    panelIn.innerHTML = html;
    panel.hidden = false;
    void panel.offsetWidth; // commit the unhidden state so the transition runs
    panel.classList.add("open");
    panel.scrollTop = 0;
  }
  function closePanel() {
    clearTimeout(hideTimer);
    panel.classList.remove("open");
    $$(".is-sel").forEach(function (el) { el.classList.remove("is-sel"); });
    hideTimer = setTimeout(function () { if (!panel.classList.contains("open")) panel.hidden = true; }, reduced ? 0 : 260);
  }
  $(".wm-close").addEventListener("click", closePanel);
  document.addEventListener("keydown", function (ev) { if (ev.key === "Escape" && !panel.hidden) closePanel(); });

  function meter(d) {
    var out = '<span class="wm-meter" aria-hidden="true">';
    for (var i = 0; i < 5; i++) out += '<i class="' + (i <= d ? "on dg-" + d : "") + '"></i>';
    return out + "</span>";
  }
  function depthText(z) { return z.lv === 0 ? esc(T.surface) : "−" + z.dm + " m · " + esc(z.lvname.toLowerCase()); }
  function exitsList(list, cls) {
    var h = '<ul class="wm-exits">';
    list.forEach(function (c) {
      var oz = D.zones[c.to];
      var chip = c.dir === "same" ? esc(c.kind) : ((c.dir === "up" ? "↑ " : "↓ ") + (c.lv === 0 ? esc(T.surface) : "−" + c.dm + " m"));
      var sub = c.dir === "same" ? esc(c.exit) + (c.edge ? " · " + esc(c.edge) : "") : esc(c.kind) + " · " + esc(c.exit);
      h += '<li class="ex-' + c.status + '"><button type="button" data-goto="' + c.to + '" data-vl="' + esc(c.conn) + '"><span class="ex-k k-' + c.k + (c.dir !== "same" ? " ex-lv" : "") + '">' + chip + "</span><b>" + esc(oz.name) + "</b>" +
        '<span class="ex-l">' + sub + "</span></button></li>";
    });
    return h + "</ul>";
  }
  function zoneHtml(id) {
    var z = D.zones[id];
    var planned = z.s === "planned" ? ' <span class="tag tag-soon">' + esc(z.status) + "</span>" : ' <span class="tag tag-live">' + esc(z.status) + "</span>";
    var h = '<p class="kicker">' + esc(z.kind) + " · " + esc(z.lvname) + (z.floor ? " · " + esc(z.floor) : "") + "</p>";
    h += "<h3>" + esc(z.name) + "</h3>" + (z.sub ? '<p class="wm-sub">' + esc(z.sub) + "</p>" : "");
    h += '<dl class="wm-facts">';
    h += "<div><dt>" + esc(T.biome) + '</dt><dd><i class="sw" style="background:' + z.b + '"></i>' + esc(z.biome) + "</dd></div>";
    h += "<div><dt>" + esc(T.danger) + "</dt><dd>" + meter(z.d) + esc(z.danger) + "</dd></div>";
    h += "<div><dt>" + esc(T.depth) + '</dt><dd><span class="wm-lv l-' + Math.abs(z.lv) + '">' + (z.lv === 0 ? "0" : z.lv) + "</span>" + depthText(z) + "</dd></div>";
    h += "<div><dt>" + esc(T.layer) + "</dt><dd>" + esc(z.layer) + "</dd></div>";
    h += "<div><dt>" + esc(T.tier) + "</dt><dd>T" + z.tier + "</dd></div>";
    h += "<div><dt>" + esc(T.status) + "</dt><dd>" + planned + "</dd></div></dl>";
    if (z.step !== null && z.step !== undefined) h += '<p class="wm-stepnote">' + esc(T.step) + " " + String(z.step).padStart(2, "0") + " · " + esc(D.journeyName || "") + "</p>";
    h += '<p class="wm-sum">' + esc(z.summary) + "</p>";
    if (z.svc && z.svc.length) {
      h += '<p class="kicker wm-k2">' + esc(T.here) + '</p><ul class="wm-svc">';
      z.svc.forEach(function (s) { h += "<li>" + esc(s) + "</li>"; });
      h += "</ul>";
    }
    if (z.wiki) h += '<p class="wm-wiki"><a class="textlink" href="' + esc(z.wiki) + '">' + esc(T.wiki_page) + " →</a></p>";
    if (z.city) h += '<button type="button" class="btn wm-opencity" data-open-city>' + esc(T.open_city) + "</button>";
    var up = z.conns.filter(function (c) { return c.dir === "up"; }), down = z.conns.filter(function (c) { return c.dir === "down"; }),
      same = z.conns.filter(function (c) { return c.dir === "same"; });
    if (up.length) h += '<p class="kicker wm-k2">' + esc(T.above) + "</p>" + exitsList(up);
    if (down.length) h += '<p class="kicker wm-k2">' + esc(T.below) + "</p>" + exitsList(down);
    if (same.length) h += '<p class="kicker wm-k2">' + esc(T.exits) + "</p>" + exitsList(same);
    return h;
  }
  function districtHtml(id) {
    var d = D.districts[id];
    var h = '<p class="kicker">' + esc(d.kind) + (d.num ? " " + d.num : "") + " · Dustline</p><h3>" + esc(d.name) + "</h3>";
    h += '<p class="wm-sum">' + esc(d.summary) + "</p>";
    if (d.services.length) {
      h += '<p class="kicker wm-k2">' + esc(T.services) + '</p><ul class="wm-svc">';
      d.services.forEach(function (s) { h += "<li>" + esc(s) + "</li>"; });
      h += "</ul>";
    }
    if (d.landmarks.length) h += '<p class="wm-sub">' + esc(T.landmark) + ": " + d.landmarks.map(esc).join(" · ") + "</p>";
    if (d["in"] && D.districts[d["in"]]) h += '<ul class="wm-exits"><li><button type="button" data-goto-d="' + d["in"] + '"><span class="ex-k">↑</span><b>' + esc(D.districts[d["in"]].name) + "</b></button></li></ul>";
    if (d.wiki) h += '<p class="wm-wiki"><a class="textlink" href="' + esc(d.wiki) + '">' + esc(T.wiki_page) + " →</a></p>";
    h += '<p class="wm-sub wm-planned">' + esc(T.planned_city) + "</p>";
    h += '<button type="button" class="textlink wm-back" data-back-map>← ' + esc(T.back_map) + "</button>";
    return h;
  }

  // ---------- Niveles ----------
  var frames = { map: $('[data-pane="map"]'), city: $('[data-pane="city"]') };
  var layers = $$(".wm-layer", frames.map);
  var rail = $(".wm-rail", frames.map);
  var gaugeM = $("[data-m]", rail), gaugeBand = $("[data-band]", rail);
  var level = 0, shownM = 0, tickRaf = 0;
  function levelInfo(n) { return D.levels[String(n)]; }
  // El indicador baja o sube en metros, como el del juego al cambiar de zona.
  function tick(toM) {
    cancelAnimationFrame(tickRaf);
    var fromM = shownM, t0 = performance.now(), dur = reduced ? 0 : 520;
    rail.classList.add("ticking");
    function frame(now) {
      var k = dur ? Math.min(1, (now - t0) / dur) : 1;
      k = 1 - Math.pow(1 - k, 3);
      shownM = Math.round(fromM + (toM - fromM) * k);
      gaugeM.textContent = (shownM ? "−" : "") + shownM;
      if (k < 1) tickRaf = requestAnimationFrame(frame); else rail.classList.remove("ticking");
    }
    tickRaf = requestAnimationFrame(frame);
  }
  function setLevel(n, meters) {
    if (LEVELS.indexOf(n) < 0) return;
    var prev = level;
    level = n;
    frames.map.setAttribute("data-level", String(n));
    frames.map.setAttribute("data-dir", n < prev ? "down" : n > prev ? "up" : "");
    layers.forEach(function (g) {
      var l = +g.getAttribute("data-level");
      g.classList.toggle("is-active", l === n);
      if (l > n) g.setAttribute("data-above", ""); else g.removeAttribute("data-above");
      if (l < n) g.setAttribute("data-below", ""); else g.removeAttribute("data-below");
    });
    $$("[data-level]", rail).forEach(function (b) { b.setAttribute("aria-pressed", +b.getAttribute("data-level") === n ? "true" : "false"); });
    $('[data-dive="up"]', rail).disabled = n === 0;
    $('[data-dive="down"]', rail).disabled = n === LEVELS[LEVELS.length - 1];
    var info = levelInfo(n);
    gaugeBand.textContent = info.band;
    tick(meters !== undefined ? meters : info.m);
    if (viewers.map) viewers.map.apply();
  }
  function dive(dir) {
    var i = LEVELS.indexOf(level) - dir; // dir -1 = bajar (indice sube)
    if (i < 0 || i >= LEVELS.length) return;
    closePanel();
    setLevel(LEVELS[i]);
  }
  $$("[data-level]", rail).forEach(function (b) { b.addEventListener("click", function () { closePanel(); setLevel(+b.getAttribute("data-level")); }); });
  $$("[data-dive]", rail).forEach(function (b) { b.addEventListener("click", function () { dive(b.getAttribute("data-dive") === "down" ? -1 : 1); }); });

  // ---------- Vistas ----------
  var view = "map";
  var viewers = {};
  function mark(sel, id) {
    $$(".is-sel").forEach(function (el) { el.classList.remove("is-sel"); });
    $$('[data-id="' + id + '"],[data-ghost="' + id + '"]', frames[sel]).forEach(function (el) { el.classList.add("is-sel"); });
  }
  function pulse(el) {
    if (!el) return;
    el.classList.remove("is-arrive");
    void el.getBoundingClientRect();
    el.classList.add("is-arrive");
  }
  function pickZone(id, arriveConn) {
    if (!id || !D.zones[id]) { closePanel(); return; }
    var z = D.zones[id];
    if (z.lv !== level) setLevel(z.lv, z.dm); else tick(z.dm);
    mark("map", id);
    if (arriveConn) {
      var el = $('.wm-layer[data-level="' + z.lv + '"] [data-vlink="' + arriveConn + '"]', frames.map);
      if (el) { el.classList.add("is-sel"); pulse(el); }
    }
    openPanel(zoneHtml(id));
  }
  function pickDistrict(id) {
    if (!id || !D.districts[id]) { closePanel(); return; }
    mark("city", id);
    openPanel(districtHtml(id));
  }
  // Toque en el continente: pasaje vertical (cambia de nivel y resalta la llegada), fantasma del nivel de abajo (baja), zona, o nada.
  function pickMap(el) {
    if (!el) { closePanel(); return; }
    if (el.hasAttribute("data-vlink")) {
      var to = el.getAttribute("data-to");
      pickZone(to, el.getAttribute("data-vlink"));
      focusZone(to, true);
      return;
    }
    if (el.hasAttribute("data-ghost")) { pickZone(el.getAttribute("data-ghost")); return; }
    pickZone(el.getAttribute("data-id"));
  }
  function setView(v) {
    if (v === view) return;
    view = v;
    closePanel();
    $$("[data-view]").forEach(function (b) { b.setAttribute("aria-selected", b.getAttribute("data-view") === v ? "true" : "false"); });
    frames.map.hidden = v !== "map";
    frames.city.hidden = v !== "city";
    $$(".wm-legend, .wm-note").forEach(function (l) { l.hidden = l.getAttribute("data-for") !== v; });
    if (!viewers[v]) viewers[v] = Viewer(frames[v], { onPick: function (el) { pickDistrict(el && el.getAttribute("data-id")); } });
    viewers[v].apply();
  }
  viewers.map = Viewer(frames.map, { onPick: pickMap, onDive: dive });
  viewers.map.apply();
  $$("[data-view]").forEach(function (b) { b.addEventListener("click", function () { setView(b.getAttribute("data-view")); }); });

  function focusZone(id, keepZoom) {
    var el = $('.wm-mark[data-id="' + id + '"]', frames.map);
    if (!el) return;
    var x = parseFloat(el.getAttribute("data-x")), y = parseFloat(el.getAttribute("data-y"));
    if (isNaN(x)) { var m = /translate\(([-\d.]+),([-\d.]+)\)/.exec(el.getAttribute("transform")); x = +m[1]; y = +m[2]; }
    // En escritorio el panel tapa la derecha: el punto se centra en lo que queda visible.
    var shift = (!mobile.matches && !panel.hidden) ? panel.offsetWidth / 2 : 0;
    viewers.map.focus(x, y, keepZoom ? 1 : (mobile.matches ? 2.4 : 1.8), shift);
  }
  function go(id, scroll, conn) {
    setView("map");
    pickZone(id, conn);
    focusZone(id);
    if (scroll) frames.map.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "center" });
  }
  panel.addEventListener("click", function (ev) {
    var b = ev.target.closest("button");
    if (!b) return;
    if (b.hasAttribute("data-goto")) go(b.getAttribute("data-goto"), false, b.getAttribute("data-vl"));
    else if (b.hasAttribute("data-goto-d")) pickDistrict(b.getAttribute("data-goto-d"));
    else if (b.hasAttribute("data-open-city")) { setView("city"); frames.city.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "nearest" }); }
    else if (b.hasAttribute("data-back-map")) go("zone.dustline", false);
  });
  $$(".wm-journey-list [data-goto]").forEach(function (b) {
    b.addEventListener("click", function () { go(b.getAttribute("data-goto"), true); });
  });
  D.journeyName = ($(".wm-journey-list .kicker") || {}).textContent || "";

  // Enlaces desde el wiki (2026-10-10): world.html?zone=<id>#map o ?district=<id>#map abren esa zona (en su nivel) o distrito.
  var params = null;
  try { params = new URLSearchParams(location.search); } catch (e) {}
  if (params) {
    var wantZone = params.get("zone"), wantDistrict = params.get("district");
    var openDeep = function () {
      if (wantZone && D.zones[wantZone]) go(wantZone, false);
      else if (wantDistrict && D.districts[wantDistrict]) { setView("city"); pickDistrict(wantDistrict); }
    };
    if (wantZone || wantDistrict) {
      if (document.readyState === "complete") openDeep(); else window.addEventListener("load", openDeep);
    }
  }
})();
