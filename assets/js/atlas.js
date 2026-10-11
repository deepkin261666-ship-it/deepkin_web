/* DEEPKIN — Field Archive: visor del atlas del mundo (pagina Mundo, 2026-10-11).
   Imagen SVG nitida a cualquier zoom: botones +/−, Ctrl/⌘ + rueda (o rueda si ya esta acercado), doble clic,
   arrastre y pellizco con dos dedos. Con un dedo la pagina scrollea normal; sin JS la imagen se ve igual. */
(function () {
  "use strict";
  var roots = document.querySelectorAll("[data-atlas]");
  Array.prototype.forEach.call(roots, function (root) {
    var vp = root.querySelector(".atlas-vp"), stage = root.querySelector(".atlas-stage");
    if (!vp || !stage) return;
    var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var s = 1, x = 0, y = 0, MIN = 1, MAX = 5, pts = {}, drag = null, pinch = null;

    function clamp() {
      var w = vp.clientWidth, h = vp.clientHeight;
      s = Math.min(MAX, Math.max(MIN, s));
      x = Math.min(0, Math.max(w - w * s, x));
      y = Math.min(0, Math.max(h - h * s, y));
    }
    function apply(animate) {
      clamp();
      stage.classList.toggle("anim", !!animate && !reduced);
      stage.style.transform = "translate(" + x.toFixed(1) + "px," + y.toFixed(1) + "px) scale(" + s.toFixed(4) + ")";
      root.classList.toggle("zoomed", s > 1.01);
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
    function center() { return { x: vp.clientWidth / 2, y: vp.clientHeight / 2 }; }

    vp.addEventListener("wheel", function (ev) {
      if (!(ev.ctrlKey || ev.metaKey || s > 1.01)) return; // sin modificador y sin zoom: la pagina scrollea
      var ns = Math.min(MAX, Math.max(MIN, s * Math.exp(-ev.deltaY * (ev.deltaMode === 1 ? 0.05 : 0.0018))));
      if (Math.abs(ns - s) < 1e-4) return;
      ev.preventDefault();
      var p = local(ev);
      zoomAt(p.x, p.y, ns);
    }, { passive: false });
    vp.addEventListener("dblclick", function (ev) {
      var p = local(ev);
      zoomAt(p.x, p.y, s > 2.5 ? 1 : s * 2, true);
    });
    vp.addEventListener("pointerdown", function (ev) {
      if (ev.button !== undefined && ev.button > 0) return;
      pts[ev.pointerId] = local(ev);
      var ids = Object.keys(pts);
      if (ids.length === 2) {
        var a = pts[ids[0]], b = pts[ids[1]];
        pinch = { d: Math.hypot(a.x - b.x, a.y - b.y) || 1, s0: s, mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2, x0: x, y0: y };
        drag = null;
      } else if (ids.length === 1 && (s > 1.01 || ev.pointerType === "mouse")) {
        drag = { sx: pts[ev.pointerId].x, sy: pts[ev.pointerId].y, x0: x, y0: y };
      }
      if (s > 1.01 || ids.length === 2) { try { vp.setPointerCapture(ev.pointerId); } catch (e) {} }
    });
    vp.addEventListener("pointermove", function (ev) {
      if (!pts[ev.pointerId]) return;
      pts[ev.pointerId] = local(ev);
      var ids = Object.keys(pts);
      if (pinch && ids.length >= 2) {
        ev.preventDefault();
        var a = pts[ids[0]], b = pts[ids[1]];
        var ns = Math.min(MAX, Math.max(MIN, pinch.s0 * Math.hypot(a.x - b.x, a.y - b.y) / pinch.d));
        var mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
        x = mx - (pinch.mx - pinch.x0) * (ns / pinch.s0);
        y = my - (pinch.my - pinch.y0) * (ns / pinch.s0);
        s = ns;
        apply();
      } else if (drag && s > 1.01) {
        var p = pts[ev.pointerId];
        x = drag.x0 + p.x - drag.sx;
        y = drag.y0 + p.y - drag.sy;
        root.classList.add("dragging");
        apply();
      }
    });
    function end(ev) {
      delete pts[ev.pointerId];
      if (Object.keys(pts).length < 2) pinch = null;
      if (!Object.keys(pts).length) { drag = null; root.classList.remove("dragging"); }
    }
    vp.addEventListener("pointerup", end);
    vp.addEventListener("pointercancel", end);
    vp.addEventListener("keydown", function (ev) {
      var c = center(), step = 60;
      if (ev.key === "+" || ev.key === "=") zoomAt(c.x, c.y, s * 1.5, true);
      else if (ev.key === "-") zoomAt(c.x, c.y, s / 1.5, true);
      else if (ev.key === "0") { s = 1; x = 0; y = 0; apply(true); }
      else if (s > 1.01 && /^Arrow/.test(ev.key)) {
        if (ev.key === "ArrowLeft") x += step;
        if (ev.key === "ArrowRight") x -= step;
        if (ev.key === "ArrowUp") y += step;
        if (ev.key === "ArrowDown") y -= step;
        apply(true);
      } else return;
      ev.preventDefault();
    });
    Array.prototype.forEach.call(root.querySelectorAll("[data-azoom]"), function (b) {
      b.addEventListener("click", function () {
        var c = center(), k = b.getAttribute("data-azoom");
        if (k === "in") zoomAt(c.x, c.y, s * 1.6, true);
        else if (k === "out") zoomAt(c.x, c.y, s / 1.6, true);
        else { s = 1; x = 0; y = 0; apply(true); }
      });
    });
    window.addEventListener("resize", function () { apply(); });
    apply();
  });
})();
