/* DEEPKIN — Field Archive: interacciones del sitio. Sin dependencias. */
(function () {
  "use strict";
  var doc = document.documentElement;
  doc.classList.add("js");
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  // Preferencia de idioma (la usa la puerta de la raiz).
  $$("[data-setlang]").forEach(function (a) {
    a.addEventListener("click", function () { try { localStorage.setItem("deepkin-lang", a.getAttribute("data-setlang")); } catch (e) {} });
  });

  // Menu movil.
  var toggle = $(".navtoggle"), nav = $("#mainnav");
  if (toggle && nav) {
    // Menu a pantalla completa: bloquea el scroll de fondo, cierra con Esc,
    // con un enlace o al volver a ancho de escritorio (2026-10-09).
    var setNav = function (open) {
      nav.classList.toggle("open", open);
      doc.classList.toggle("nav-open", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    };
    toggle.addEventListener("click", function () { setNav(!nav.classList.contains("open")); });
    $$("a", nav).forEach(function (a) { a.addEventListener("click", function () { setNav(false); }); });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && nav.classList.contains("open")) { setNav(false); toggle.focus(); }
    });
    if (window.matchMedia) {
      var wide = window.matchMedia("(min-width: 1321px)");
      var onWide = function () { if (wide.matches) setNav(false); };
      if (wide.addEventListener) wide.addEventListener("change", onWide); else if (wide.addListener) wide.addListener(onWide);
    }
  }


  // Busqueda del wiki (2026-10-10): indice prebuilt en <idioma>/wiki/search.js, cargado al abrir (funciona en file://).
  var sbox = $("#search"), sq = $("#search-q"), sres = $("#search-res");
  if (sbox && sq && sres) {
    var root = document.body.getAttribute("data-root") || "";
    var es = document.body.getAttribute("data-lang") === "es";
    var loaded = false, sel = 0, hits = [], lastFocus = null;
    var norm = function (x) { return String(x).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, ""); };
    var escH = function (x) { return String(x).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
    var kinds = es ? { item: "Objeto", mob: "Criatura", npc: "Persona", zone: "Zona", faction: "Facción", material: "Material", quest: "Misión", mech: "Mecánica", "class": "Clase", page: "Página" }
                   : { item: "Item", mob: "Creature", npc: "Person", zone: "Zone", faction: "Faction", material: "Material", quest: "Quest", mech: "Mechanic", "class": "Class", page: "Page" };
    function load(cb) {
      if (window.DKS) { cb(); return; }
      if (loaded) return;
      loaded = true;
      var sc = document.createElement("script");
      sc.src = root + "wiki/search.js";
      sc.onload = cb;
      document.head.appendChild(sc);
    }
    function score(e, q) {
      var n = norm(e.n), s = norm(e.s || "");
      if (n === q) return 100;
      if (n.indexOf(q) === 0) return 80;
      if (n.split(/[\s\-·]+/).some(function (w) { return w.indexOf(q) === 0; })) return 60;
      if (n.indexOf(q) > -1) return 40;
      if (s.indexOf(q) > -1) return 15;
      return 0;
    }
    function mark(name, q) {
      var i = norm(name).indexOf(q);
      if (i < 0 || !q) return escH(name);
      return escH(name.slice(0, i)) + "<mark>" + escH(name.slice(i, i + q.length)) + "</mark>" + escH(name.slice(i + q.length));
    }
    function render() {
      var q = norm(sq.value.trim());
      var list = window.DKS || [];
      if (!q) hits = list.filter(function (e) { return e.k === "mech"; }).slice(0, 8);
      else hits = list.map(function (e) { return [score(e, q), e]; }).filter(function (x) { return x[0] > 0; })
        .sort(function (a, b) { return b[0] - a[0] || a[1].n.localeCompare(b[1].n); }).slice(0, 14).map(function (x) { return x[1]; });
      sel = 0;
      if (!hits.length) { sres.innerHTML = '<li class="s-empty">' + (es ? "Sin resultados." : "No results.") + "</li>"; return; }
      sres.innerHTML = hits.map(function (e, i) {
        var ico = e.i ? '<img src="' + root + e.i + '" alt="" loading="lazy">' : '<span class="s-ph">' + escH(e.n.charAt(0)) + "</span>";
        return '<li><a role="option" href="' + root + e.u + '" aria-selected="' + (i === 0) + '">' + ico + "<span><b>" + mark(e.n, q) + "</b><small>" + escH(kinds[e.k] || "") + (e.s ? " · " + escH(e.s) : "") + "</small></span></a></li>";
      }).join("");
    }
    function setSel(i) {
      var as = $$("a", sres);
      if (!as.length) return;
      sel = (i + as.length) % as.length;
      as.forEach(function (a, j) { a.setAttribute("aria-selected", j === sel ? "true" : "false"); });
      as[sel].scrollIntoView({ block: "nearest" });
    }
    function open() {
      lastFocus = document.activeElement;
      sbox.hidden = false;
      doc.classList.add("search-open");
      sq.focus();
      sq.select();
      load(render);
      if (window.DKS) render();
    }
    function close() {
      sbox.hidden = true;
      doc.classList.remove("search-open");
      if (lastFocus && lastFocus.focus) lastFocus.focus();
    }
    $$("[data-search-open]").forEach(function (b) { b.addEventListener("click", open); });
    $$("[data-search-close]").forEach(function (b) { b.addEventListener("click", close); });
    sbox.addEventListener("click", function (ev) { if (ev.target === sbox) close(); });
    sq.addEventListener("input", function () { if (window.DKS) render(); });
    sq.addEventListener("keydown", function (ev) {
      if (ev.key === "ArrowDown") { ev.preventDefault(); setSel(sel + 1); }
      else if (ev.key === "ArrowUp") { ev.preventDefault(); setSel(sel - 1); }
      else if (ev.key === "Enter") { var a = $$("a", sres)[sel]; if (a) { ev.preventDefault(); location.href = a.href; } }
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && !sbox.hidden) { close(); return; }
      var tag = (ev.target.tagName || "").toLowerCase();
      if (ev.key === "/" && sbox.hidden && tag !== "input" && tag !== "textarea" && tag !== "select" && !ev.target.isContentEditable) { ev.preventDefault(); open(); }
    });
  }

  // Aparicion al hacer scroll.
  var reveals = $$(".reveal");
  if ("IntersectionObserver" in window && !reduced) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });
    reveals.forEach(function (el, i) { el.style.transitionDelay = Math.min(i % 6, 5) * 60 + "ms"; io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add("in"); });
  }

  // Medidor de profundidad: el scroll es el descenso.
  var fill = $(".depth-fill"), val = $(".depth-val");
  var maxDepth = document.body.classList.contains("story-page") ? 2318 : 1200;
  function onScroll() {
    var h = document.documentElement.scrollHeight - window.innerHeight;
    var f = h > 0 ? Math.min(1, Math.max(0, window.scrollY / h)) : 0;
    if (fill) fill.style.height = (f * 100).toFixed(1) + "%";
    if (val) val.textContent = "−" + String(Math.round(f * maxDepth)).padStart(4, "0") + " m";
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // Linterna del hero: el circulo de luz sigue al puntero; si no hay puntero, deriva solo.
  var hero = $("[data-lantern]");
  if (hero) {
    var tx = 50, ty = 55, x = 50, y = 55, idle = true, t0 = performance.now();
    hero.addEventListener("pointermove", function (ev) {
      var r = hero.getBoundingClientRect();
      tx = ((ev.clientX - r.left) / r.width) * 100;
      ty = ((ev.clientY - r.top) / r.height) * 100;
      idle = false;
    });
    hero.addEventListener("pointerleave", function (ev) { if (ev.pointerType === "mouse") idle = true; });
    // En tactil no hay "hover": tocar el hero lleva la luz ahi y despues vuelve a derivar (2026-10-09).
    var idleTimer;
    hero.addEventListener("pointerdown", function (ev) {
      if (ev.pointerType === "mouse") return;
      var r = hero.getBoundingClientRect();
      tx = ((ev.clientX - r.left) / r.width) * 100;
      ty = ((ev.clientY - r.top) / r.height) * 100;
      idle = false;
      clearTimeout(idleTimer);
      idleTimer = setTimeout(function () { idle = true; }, 2600);
    });
    var running = true;
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (en) { running = en[0].isIntersecting; if (running) requestAnimationFrame(tick); }).observe(hero);
    }
    function tick(now) {
      if (!running) return;
      if (idle) {
        var s = (now - t0) / 1000;
        tx = 50 + Math.sin(s * 0.35) * 22;
        ty = 52 + Math.sin(s * 0.53) * 12;
      }
      var k = reduced ? 1 : 0.08;
      x += (tx - x) * k; y += (ty - y) * k;
      hero.style.setProperty("--x", x.toFixed(2) + "%");
      hero.style.setProperty("--y", y.toFixed(2) + "%");
      if (!reduced) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  // Indice lateral: resalta la seccion visible.
  var tocLinks = $$(".toc a");
  if (tocLinks.length && "IntersectionObserver" in window) {
    var map = {};
    tocLinks.forEach(function (a) { map[a.getAttribute("href").slice(1)] = a; });
    var targets = Object.keys(map).map(function (id) { return document.getElementById(id); }).filter(Boolean);
    var tio = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) {
          tocLinks.forEach(function (a) { a.classList.remove("active"); });
          var a = map[en.target.id];
          if (a) {
            a.classList.add("active");
            if (a.scrollIntoView && window.innerWidth < 960) a.parentNode.scrollTo({ left: a.offsetLeft - 20, behavior: reduced ? "auto" : "smooth" });
          }
        }
      });
    }, { rootMargin: "-20% 0px -70% 0px" });
    targets.forEach(function (t) { tio.observe(t); });
  }

  // Texto que se "descifra" (261.6.66).
  var glyphs = "!<>-_\\/[]{}—=+*^?#01";
  $$(".scramble").forEach(function (el) {
    var text = el.getAttribute("data-text") || el.textContent;
    function run() {
      if (reduced) { el.textContent = text; return; }
      var frame = 0, total = 28;
      (function step() {
        var out = "";
        for (var i = 0; i < text.length; i++) {
          out += frame > (i / text.length) * total + 6 || text[i] === "." ? text[i] : glyphs[Math.floor(Math.random() * glyphs.length)];
        }
        el.textContent = out;
        if (frame++ < total + 8) requestAnimationFrame(step); else el.textContent = text;
      })();
    }
    if ("IntersectionObserver" in window) {
      var sio = new IntersectionObserver(function (en) { if (en[0].isIntersecting) { run(); sio.disconnect(); } }, { threshold: 1 });
      sio.observe(el);
    } else { run(); }
  });

  // Arsenal: filtros y orden.
  var filters = $(".filters");
  if (filters) {
    var grid = $(filters.getAttribute("data-target"));
    var cards = $$(".wcard", grid);
    var original = cards.slice();
    var rows = $$("#wtable tbody tr");
    var chips = $$(".fchip", filters);
    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        chips.forEach(function (c) { c.setAttribute("aria-pressed", "false"); });
        chip.setAttribute("aria-pressed", "true");
        var f = chip.getAttribute("data-filter");
        var match = function (el) {
          if (f === "all") return true;
          var p = f.split(":");
          return el.getAttribute("data-" + p[0]) === p[1];
        };
        cards.forEach(function (c) { c.hidden = !match(c); });
        rows.forEach(function (r) { r.hidden = !match(r); });
      });
    });
    var sel = $("[data-sort-select]", filters);
    if (sel) sel.addEventListener("change", function () {
      var k = sel.value;
      var list = original.slice();
      if (k !== "default") {
        list.sort(function (a, b) {
          if (k === "name") return a.dataset.name.localeCompare(b.dataset.name);
          var av = parseFloat(a.dataset[k]), bv = parseFloat(b.dataset[k]);
          return k === "speed" ? av - bv : bv - av;
        });
      }
      list.forEach(function (c) { grid.appendChild(c); });
    });
  }

  // Tablas ordenables.
  $$("table.sortable").forEach(function (table) {
    var ths = $$("thead th", table);
    ths.forEach(function (th, idx) {
      if (!th.hasAttribute("data-sort")) return;
      th.tabIndex = 0;
      var go = function () {
        var asc = th.getAttribute("aria-sort") !== "ascending";
        ths.forEach(function (o) { o.removeAttribute("aria-sort"); });
        th.setAttribute("aria-sort", asc ? "ascending" : "descending");
        var num = th.getAttribute("data-sort") === "num";
        var body = table.tBodies[0];
        $$("tr", body).sort(function (a, b) {
          var x = a.cells[idx].textContent.trim(), y = b.cells[idx].textContent.trim();
          var r = num ? parseFloat(x.replace(",", ".")) - parseFloat(y.replace(",", ".")) : x.localeCompare(y);
          return asc ? r : -r;
        }).forEach(function (tr) { body.appendChild(tr); });
      };
      th.addEventListener("click", go);
      th.addEventListener("keydown", function (ev) { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); go(); } });
    });
  });

  // Calculadora de daño (mismas formulas que shared/gameplay/rpg_rules.gd).
  var dataEl = $("#calc-data");
  if (dataEl) {
    var D = JSON.parse(dataEl.textContent);
    var es = D.lang === "es";
    var fmt = function (v, d) { var s = v.toFixed(d); return es ? s.replace(".", ",") : s; };
    var el = { cls: $("#c-class"), w: $("#c-weapon"), ammo: $("#c-ammo"), skill: $("#c-skill"), lvl: $("#c-lvl"),
      skillO: $("#c-skill-o"), lvlO: $("#c-lvl-o"), hit: $("#c-hit"), dps: $("#c-dps"), pow: $("#c-pow"), powL: $("#c-pow-l"), note: $("#c-note") };
    var byId = function (arr, id) { for (var i = 0; i < arr.length; i++) if (arr[i].id === id) return arr[i]; };
    var statMult = function (v) { return Math.min(1.25, Math.max(0.75, 1 + (v - 10) * 0.015)); };
    var powLabel = el.powL.textContent;
    function calc() {
      var c = byId(D.classes, el.cls.value), w = byId(D.weapons, el.w.value);
      var skill = +el.skill.value, lvl = +el.lvl.value;
      el.skillO.textContent = skill; el.lvlO.textContent = lvl;
      el.ammo.disabled = !w.ammo;
      var ammo = w.ammo ? parseFloat(el.ammo.value) : 1;
      var attr = w.type === "melee" ? "might" : "precision";
      var coef = c.coef[w.type] || 1;
      var factor = 1 + 0.01 * (skill - 1) + 0.006 * (lvl - 1);
      var raw = w.base * coef * statMult(c.attributes[attr]) * ammo * factor;
      var hit = Math.max(1, Math.round(raw));
      el.hit.textContent = hit;
      el.dps.textContent = fmt(hit / w.interval, 1);
      el.pow.textContent = c.powerMult > 1 ? Math.round(raw * c.powerMult) : "—";
      el.powL.textContent = c.power + (c.powerMult > 1 ? " ×" + fmt(c.powerMult, 1).replace(/[.,]0$/, "") : "") + " · " + powLabel;
      el.note.textContent = (es ? "Base " : "Base ") + w.base + " × " + (es ? "coef. " : "coef. ") + fmt(coef, 2) + " (" + (w.type === "melee" ? (es ? "cuerpo a cuerpo" : "melee") : (es ? "a distancia" : "ranged")) + ")" +
        " × " + fmt(statMult(c.attributes[attr]), 3) + " (" + (D.attrNames[attr] || attr) + " " + c.attributes[attr] + ")" +
        (w.ammo ? " × " + fmt(ammo, 2) + (es ? " (munición)" : " (ammo)") : "") +
        " × " + fmt(factor, 3) + (es ? " (habilidad y nivel)" : " (skill & level)") + " · " + w.family;
      el.hit.parentNode.style.setProperty("--c", c.color);
    }
    ["cls", "w", "ammo", "skill", "lvl"].forEach(function (k) { el[k].addEventListener("input", calc); el[k].addEventListener("change", calc); });
    // Arma inicial segun la clase elegida, para que el primer resultado tenga sentido.
    calc();
  }
})();

/* Intro de terminal en la portada (2026-10-11): la primera visita ve el arranque de un terminal de campo,
   "connect 261.6.66", SIGNAL LOCKED y el logo, en el verde fosforo del final de DEEPKIN_Historia. ~4 s; se salta con
   clic, tecla, rueda o toque; con prefers-reduced-motion se muestra quieta y breve. Se recuerda en localStorage. */
(function () {
  "use strict";
  var root = document.documentElement;
  var box = document.getElementById("dk-intro");
  if (!box || !root.classList.contains("dk-intro-on")) return;
  try { localStorage.setItem("dk-intro", "1"); } catch (e) {}
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var es = document.documentElement.lang === "es";
  var log = box.querySelector(".dki-log"), big = box.querySelector(".dki-big"), bar = box.querySelector(".dki-bar i");
  var canvas = box.querySelector(".dki-rain"), ctx = canvas && canvas.getContext ? canvas.getContext("2d") : null;
  var CH = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ@#$%&*+-/<>=?§±∞¶•カキクケコサシスセソㄱㄴㄷㄹΔΩλπψΦΘΞΣ";
  var rnd = function (n) { var s = ""; for (var i = 0; i < n; i++) s += CH.charAt(Math.floor(Math.random() * CH.length)); return s; };
  var LINES = [
    ["DEEPKIN FIELD TERMINAL · v0.2 · 2318", 0],
    [es ? "> chequeo de memoria ........ OK" : "> memory check .............. OK", 0],
    [es ? "> barrido de enlace ......... 3 NODOS" : "> uplink scan ............... 3 NODES", 0],
    [es ? "> profundidad ............... 60 m · OUTPOST" : "> depth ..................... 60 m · OUTPOST", 0],
    ["guest@outpost-7:~$ ", 1]
  ];
  var CMD = "connect 261.6.66";
  var timers = [], raf = 0, done = false, t0 = performance.now(), TOTAL = 4200;

  function finish(fast) {
    if (done) return;
    done = true;
    timers.forEach(clearTimeout);
    cancelAnimationFrame(raf);
    ["click", "keydown", "wheel", "touchstart"].forEach(function (ev) { window.removeEventListener(ev, skip, true); });
    box.classList.add("dki-out");
    setTimeout(function () { root.classList.remove("dk-intro-on"); box.remove(); }, fast || reduced ? 0 : 520);
  }
  function skip(ev) {
    if (ev && ev.type === "keydown" && (ev.key === "Tab" || ev.key === "Shift")) return;
    if (ev && ev.cancelable && ev.type !== "touchstart") ev.preventDefault();
    finish(false);
  }
  ["click", "keydown", "wheel", "touchstart"].forEach(function (ev) { window.addEventListener(ev, skip, { capture: true, passive: ev !== "keydown" && ev !== "click" }); });
  var skipBtn = box.querySelector(".dki-skip");
  if (skipBtn) skipBtn.focus({ preventScroll: true });

  if (reduced) {
    log.textContent = LINES.map(function (l) { return l[0]; }).join("\n") + CMD;
    big.textContent = "SIGNAL LOCKED";
    box.classList.add("dki-logo-on", "dki-locked");
    if (bar) bar.style.width = "100%";
    timers.push(setTimeout(function () { finish(true); }, 1800));
    return;
  }

  // Lluvia de glifos
  var cols = [], fs = 16;
  function size() {
    if (!canvas) return;
    var dpr = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = innerWidth * dpr; canvas.height = innerHeight * dpr;
    canvas.style.width = innerWidth + "px"; canvas.style.height = innerHeight + "px";
    if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    fs = innerWidth < 560 ? 13 : 16;
    cols = [];
    for (var i = 0; i < Math.ceil(innerWidth / fs); i++) cols.push(Math.random() * -40);
  }
  size();
  window.addEventListener("resize", size);
  var last = 0;
  function frame(now) {
    if (done) return;
    var t = now - t0;
    if (bar) bar.style.width = Math.min(100, t / TOTAL * 100).toFixed(1) + "%";
    if (ctx && now - last > 45) {
      last = now;
      var k = Math.min(1, Math.max(0, (t - 600) / 1800));   // la lluvia crece hacia SIGNAL LOCKED
      ctx.fillStyle = "rgba(3,5,3,0.16)";
      ctx.fillRect(0, 0, innerWidth, innerHeight);
      ctx.font = fs + "px 'Courier New', monospace";
      for (var i = 0; i < cols.length; i++) {
        if (Math.random() > 0.25 + 0.75 * k) continue;
        var y = cols[i] * fs;
        ctx.fillStyle = Math.random() < 0.08 ? "#c8ffd2" : "rgba(0,255,65," + (0.25 + 0.5 * k).toFixed(2) + ")";
        ctx.fillText(CH.charAt(Math.floor(Math.random() * CH.length)), i * fs, y);
        cols[i] = y > innerHeight && Math.random() > 0.96 ? 0 : cols[i] + 1;
      }
    }
    raf = requestAnimationFrame(frame);
  }
  raf = requestAnimationFrame(frame);

  // Arranque tipeado
  var text = "", at = 120;
  LINES.forEach(function (l, li) {
    var line = l[0];
    timers.push(setTimeout(function () { text += (li ? "\n" : "") + line; log.textContent = text; }, at));
    at += li === LINES.length - 1 ? 160 : 190;
  });
  for (var c = 1; c <= CMD.length; c++) {
    (function (n) { timers.push(setTimeout(function () { log.textContent = text + CMD.slice(0, n) + (n < CMD.length ? "▌" : ""); }, at + n * 42)); })(c);
  }
  at += CMD.length * 42 + 220;
  // Desencriptado: ruido -> 261.6.66 -> SIGNAL LOCKED
  var dec = function (target, from, dur, then) {
    var start = 0;
    timers.push(setTimeout(function step() {
      start = start || performance.now();
      var p = Math.min(1, (performance.now() - start) / dur), out = "";
      for (var i = 0; i < target.length; i++) out += (target[i] === " " || Math.random() < p * 1.15) ? target[i] : rnd(1);
      big.textContent = out;
      if (p < 1 && !done) timers.push(setTimeout(step, 40)); else if (then) then();
    }, from));
  };
  dec("261.6.66", at, 650, function () { box.classList.add("dki-pulse"); });
  at += 900;
  dec("SIGNAL LOCKED", at, 520, function () { box.classList.add("dki-locked"); });
  at += 700;
  timers.push(setTimeout(function () { box.classList.add("dki-logo-on"); }, at));
  timers.push(setTimeout(function () { finish(false); }, Math.max(TOTAL, at + 900)));
})();
