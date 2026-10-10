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
      var wide = window.matchMedia("(min-width: 1101px)");
      var onWide = function () { if (wide.matches) setNav(false); };
      if (wide.addEventListener) wide.addEventListener("change", onWide); else if (wide.addListener) wide.addListener(onWide);
    }
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
