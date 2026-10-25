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

  // Tablas ordenables. Una celda con data-v ordena por ese valor (numeros con coma, "—" y textos con iconos);
  // las filas de grupo (tr.grp) se ocultan mientras la tabla esta ordenada por una columna.
  $$("table.sortable").forEach(function (table) {
    var ths = $$("thead th", table);
    var key = function (cell, num) {
      var v = cell.hasAttribute("data-v") ? cell.getAttribute("data-v") : cell.textContent.trim();
      if (!num) return v.toLowerCase();
      var f = parseFloat(String(v).replace(/\s/g, "").replace(",", "."));
      return isNaN(f) ? null : f;
    };
    ths.forEach(function (th, idx) {
      if (!th.hasAttribute("data-sort")) return;
      th.tabIndex = 0;
      var go = function () {
        var asc = th.getAttribute("aria-sort") !== "ascending";
        ths.forEach(function (o) { o.removeAttribute("aria-sort"); });
        th.setAttribute("aria-sort", asc ? "ascending" : "descending");
        table.classList.add("is-sorted");
        var num = th.getAttribute("data-sort") === "num";
        var body = table.tBodies[0];
        $$("tr", body).filter(function (tr) { return !tr.classList.contains("grp") && tr.cells[idx]; }).sort(function (a, b) {
          var x = key(a.cells[idx], num), y = key(b.cells[idx], num);
          if (x === null || y === null) return x === y ? 0 : (x === null ? 1 : -1);
          var r = num ? x - y : x.localeCompare(y);
          return asc ? r : -r;
        }).forEach(function (tr) { body.appendChild(tr); });
      };
      th.addEventListener("click", go);
      th.addEventListener("keydown", function (ev) { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); go(); } });
    });
  });

  // Objetos: filtro rapido sobre todas las tablas (nombre, id, habilidad, ranura...). Oculta secciones sin coincidencias.
  var iq = $("#items-q");
  if (iq) {
    var secs = $$("[data-isec]"), outN = $("#items-n");
    var esI = document.documentElement.lang === "es";
    var runQ = function () {
      var q = iq.value.trim().toLowerCase(), total = 0;
      secs.forEach(function (sec) {
        var shown = 0, all = !!q && (sec.getAttribute("data-k") || "").indexOf(q) > -1;
        $$("tbody tr", sec).forEach(function (tr) {
          if (tr.classList.contains("grp")) { tr.hidden = !!q && !all; return; }
          var ok = !q || all || (tr.getAttribute("data-q") || "").indexOf(q) > -1 || tr.textContent.toLowerCase().indexOf(q) > -1;
          tr.hidden = !ok;
          if (ok) shown++;
        });
        sec.hidden = !!q && !shown;
        total += shown;
      });
      if (outN) outN.textContent = q ? total + (esI ? (total === 1 ? " objeto" : " objetos") : (total === 1 ? " item" : " items")) : "";
    };
    iq.addEventListener("input", runQ);
    if (iq.value) runQ();
  }

  // Calculadora de daño (mismas formulas que el servidor: RpgRules.outgoing_damage y los rasgos en porcentaje de
  // WeaponSkills; src/combat_math.py). Muestra el golpe en regimen y el DPS sostenido, veneno incluido.
  var dataEl = $("#calc-data");
  if (dataEl) {
    var D = JSON.parse(dataEl.textContent);
    var es = D.lang === "es";
    var fmt = function (v, d) { var s = v.toFixed(d); return es ? s.replace(".", ",") : s; };
    var el = { cls: $("#c-class"), w: $("#c-weapon"), ammo: $("#c-ammo"), skill: $("#c-skill"), lvl: $("#c-lvl"),
      skillO: $("#c-skill-o"), lvlO: $("#c-lvl-o"), hit: $("#c-hit"), dps: $("#c-dps"), pow: $("#c-pow"), powL: $("#c-pow-l"), note: $("#c-note") };
    var byId = function (arr, id) { for (var i = 0; i < arr.length; i++) if (arr[i].id === id) return arr[i]; };
    var statMult = function (v) { return Math.min(1.25, Math.max(0.75, 1 + (v - 10) * D.statStep)); };
    var powLabel = el.powL.textContent;
    var ammoOpts = $$("option", el.ammo);
    var lastW = null;
    function syncAmmo(w) {
      // Solo la municion de la familia del arma; por defecto la suya.
      var any = false;
      ammoOpts.forEach(function (o) {
        var a = byId(D.ammo, o.value), ok = !!w.ammoFamily && a.family === w.ammoFamily;
        o.hidden = !ok; o.disabled = !ok; any = any || ok;
      });
      el.ammo.disabled = !any;
      if (any) el.ammo.value = w.ammoId; else el.ammo.selectedIndex = -1;
    }
    function calc() {
      var c = byId(D.classes, el.cls.value), w = byId(D.weapons, el.w.value);
      if (w !== lastW) { syncAmmo(w); lastW = w; }
      var skill = +el.skill.value, lvl = +el.lvl.value;
      el.skillO.textContent = skill; el.lvlO.textContent = lvl;
      var a = w.ammoFamily ? byId(D.ammo, el.ammo.value) : null;
      var ammo = a ? a.mult : 1, poison = a ? a.poison : 0;
      var attr = w.type === "melee" ? "might" : "precision";
      var coef = c.coef[w.type] || 1;
      var factor = 1 + D.skillStep * (skill - 1) + D.levelStep * (lvl - 1);
      var raw = w.base * coef * statMult(c.attributes[attr]) * ammo * factor;
      var tb = c.id === "class.drift" ? D.trailblazer : 0;
      var hitOf = function (bonus, mult) { return Math.max(1, Math.round(raw * (mult || 1) * (1 + bonus))); };
      var sustained, avg, bonus;
      if (w.ambush) {
        var amb = hitOf(D.ambushPct + tb), plain = hitOf(tb);
        sustained = amb; bonus = D.ambushPct + tb;
        avg = D.ambushUptime * amb + (1 - D.ambushUptime) * plain;
      } else {
        bonus = w.trait + tb; sustained = hitOf(bonus); avg = sustained;
      }
      el.hit.textContent = sustained;
      el.dps.textContent = fmt(avg / w.interval + poison, 1);
      el.pow.textContent = c.powerMult > 1 ? hitOf(bonus, c.powerMult) : "—";
      el.powL.textContent = c.power + (c.powerMult > 1 ? " ×" + fmt(c.powerMult, 1).replace(/[.,]0$/, "") : "") + " · " + powLabel;
      el.note.textContent = "Base " + w.base + " × " + "coef. " + fmt(coef, 2) + " (" + (w.type === "melee" ? (es ? "cuerpo a cuerpo" : "melee") : (es ? "a distancia" : "ranged")) + ")" +
        " × " + fmt(statMult(c.attributes[attr]), 3) + " (" + (D.attrNames[attr] || attr) + " " + c.attributes[attr] + ")" +
        (a ? " × " + fmt(ammo, 2) + (es ? " (munición)" : " (ammo)") : "") +
        " × " + fmt(factor, 3) + (es ? " (habilidad y nivel)" : " (skill & level)") +
        (bonus ? " × " + fmt(1 + bonus, 2) + (es ? " (rasgo" : " (trait") + (tb ? " + Trailblazer" : "") + ")" : "") +
        " · " + (es ? "apertura " : "opening ") + hitOf(w.opening) +
        (w.ambush ? (es ? " · Emboscada en la mitad de los golpes" : " · Ambush on half the hits") : "") +
        (poison ? (es ? " · veneno " : " · poison ") + poison + "/s" : "") + " · " + w.family;
      el.hit.parentNode.style.setProperty("--c", c.color);
    }
    ["cls", "w", "ammo", "skill", "lvl"].forEach(function (k) { el[k].addEventListener("input", calc); el[k].addEventListener("change", calc); });
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
