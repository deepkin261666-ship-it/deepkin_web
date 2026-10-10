/* DEEPKIN — wiki: calculadora de experiencia (misma curva que RpgRules.total_xp_for_level, 2026-10-10). */
(function () {
  "use strict";
  var box = document.getElementById("xpcalc");
  if (!box) return;
  var N = +box.getAttribute("data-num"), D = +box.getAttribute("data-den"), es = box.getAttribute("data-lang") === "es";
  var LIMIT = 65535;
  function total(l) { l = Math.max(1, Math.min(LIMIT, Math.floor(l))); return N * (l - 1) * (l * l - 5 * l + 12) / D; }
  function level(xp) { var lo = 1, hi = LIMIT; while (lo < hi) { var m = Math.floor((lo + hi + 1) / 2); if (total(m) <= xp) lo = m; else hi = m - 1; } return lo; }
  function fmt(v) { var s = Math.round(v).toLocaleString("en-US"); return es ? s.replace(/,/g, " ") : s; }
  var L = document.getElementById("xp-l"), X = document.getElementById("xp-x");
  function run() {
    var l = Math.max(1, Math.min(LIMIT, parseInt(L.value, 10) || 1));
    document.getElementById("xp-tot").textContent = fmt(total(l));
    document.getElementById("xp-next").textContent = l < LIMIT ? fmt(total(l + 1) - total(l)) : "—";
    var x = Math.max(0, parseInt(X.value, 10) || 0), lv = level(x), span = total(lv + 1) - total(lv);
    document.getElementById("xp-lv").textContent = fmt(lv);
    var p = span > 0 ? (x - total(lv)) / span * 100 : 100;
    document.getElementById("xp-pct").textContent = (es ? p.toFixed(1).replace(".", ",") : p.toFixed(1)) + "%";
  }
  L.addEventListener("input", run); X.addEventListener("input", run);
  run();
})();
