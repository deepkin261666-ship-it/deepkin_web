# Atlas del mundo (pagina Mundo, 2026-10-11): imagen ilustrada generada de data/world/world_map.json y de las
# transiciones reales de data/starting_region.json. Dos laminas SVG por idioma: la ancha (escritorio) y una alta para
# telefono. Planta de la region jugable (superficie y subsuelo), corte de profundidades con las bandas -1/-2/-3, cada
# pasaje numerado con su tipo real (metro, elevador, escaleras, camino, puerta) y su cartel del juego, la ruta
# recomendada Outpost -> Dustline y la bajada a The Cinder Deep. Lo planeado va desvaido como "sin cartografiar".
# No se toca el grafo del juego: las posiciones de etiquetas son de esta lamina.
import html
import json
import math
import os

from i18n import L

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORLD = json.load(open(os.path.join(ROOT, "data", "world", "world_map.json")))
REGION = json.load(open(os.path.join(ROOT, "data", "starting_region.json")))
HUBS = json.load(open(os.path.join(ROOT, "data", "world", "respawn_hubs.json")))
ZONES = {z["id"]: z for z in WORLD["zones"]}
TRANS = {t["entity_id"]: t for t in REGION["transitions"]}
FLOORS = {f["zone_id"]: f for f in REGION["floors"]}
IW, IH = WORLD["image"]["width"], WORLD["image"]["height"]

MONO = "'IBM Plex Mono','SFMono-Regular',Menlo,Consolas,'DejaVu Sans Mono',monospace"
COND = "'Saira Condensed','Arial Narrow','Roboto Condensed','DejaVu Sans Condensed',sans-serif"
C = {"bg": "#0b0d0c", "panel": "#111513", "line": "#262c28", "line2": "#363d38", "text": "#e8e3d5", "soft": "#c6c0b0",
     "muted": "#9a958a", "dim": "#5f5d56", "amber": "#d39a4b", "warm": "#e2c88f", "danger": "#d9614f", "teal": "#6fb3ac",
     "green": "#00ff41", "sand": "#b9a688", "rock": "#4a5568", "cave": "#1a2230", "cave2": "#243044"}
TYPE_COLOR = {"metro": "#6fb3ac", "lift": "#d39a4b", "stairs": "#e2c88f", "road": "#c6c0b0", "gate": "#d9614f"}

T = {
    "title": L("FIELD ATLAS", "ATLAS DE CAMPO"),
    "sub": L("The shaft country & the Frontier — how the maps connect", "El país del pozo y la Frontera — cómo se conectan los mapas"),
    "survey": L("SURVEY 2026-10 · SCHEMATIC, NOT TO SCALE", "RELEVAMIENTO 2026-10 · ESQUEMA, SIN ESCALA"),
    "plan": L("PLAN · SURFACE AND WORKINGS", "PLANTA · SUPERFICIE Y GALERÍAS"),
    "section": L("CROSS-SECTION · DEPTH", "CORTE · PROFUNDIDAD"),
    "passages": L("PASSAGES · IN-GAME SIGNS", "PASAJES · CARTELES DEL JUEGO"),
    "legend": L("LEGEND", "REFERENCIAS"),
    "uncharted": L("UNCHARTED", "SIN CARTOGRAFIAR"),
    "surface": L("SURFACE · 0 m", "SUPERFICIE · 0 m"),
    "band1": L("−1 · 1–200 m", "−1 · 1–200 m"), "band2": L("−2 · 201–400 m", "−2 · 201–400 m"), "band3": L("−3 · 401–600 m", "−3 · 401–600 m"),
    "route": L("RECOMMENDED ROUTE · OUTPOST → DUSTLINE", "RUTA RECOMENDADA · OUTPOST → DUSTLINE"),
    "route_short": L("Recommended route", "Ruta recomendada"),
    "cinder_route": L("To the Cinder Deep", "Hacia The Cinder Deep"),
    "c3_route": L("Into C-3", "Hacia C-3"),
    "start": L("START", "INICIO"), "first_city": L("FIRST CITY", "PRIMERA CIUDAD"),
    "locked": L("LOCKED · drill the Deep Seal", "CERRADO · perforá el Sello Profundo"),
    "one_way": L("one way", "sólo ida"),
    "t_metro": L("Metro tunnel", "Túnel de metro"), "t_lift": L("Lift", "Elevador"), "t_stairs": L("Stairs", "Escaleras"),
    "t_road": L("Road", "Camino"), "t_gate": L("Gate", "Puerta"),
    "down": L("down", "baja"), "up": L("up", "sube"),
    "i_city": L("City · safe", "Ciudad · segura"), "i_outpost": L("Outpost · start", "Outpost · inicio"),
    "i_hunt": L("Hunting ground", "Coto de caza"), "i_dungeon": L("Dungeon floor", "Piso de mazmorra"),
    "i_route": L("Road map", "Mapa de ruta"), "i_cave": L("Cavern", "Caverna"),
    "i_fuel": L("Gas station", "Estación de servicio"), "i_bank": L("Bank & depot terminal", "Terminal de banco y depósito"),
    "i_hub": L("Respawn hub", "Punto de reaparición"),
    "l_surface": L("Surface map", "Mapa de superficie"), "l_under": L("Underground map", "Mapa subterráneo"),
    "l_stack": L("Level stacked below", "Nivel apilado debajo"), "l_planned": L("Planned · uncharted", "Planeado · sin cartografiar"),
    "ride": L("bike: metro, lifts, gates ✓ · stairs ✕", "moto: metro, elevadores, puertas ✓ · escaleras ✕"),
    "north": L("N", "N"),
    "gate_fuel": L("GATE FUEL", "GATE FUEL"),
    "bank": L("BANK", "BANCO"),
}


def tr(key, lang):
    return T[key][lang]


def e(s):
    return html.escape(str(s), quote=True)


def zname(zid):
    return ZONES[zid]["name"]


# --- Pasajes ---------------------------------------------------------------------------------------------------
def pres_of(tid):
    t = TRANS.get(tid)
    if not t:
        return None
    return t.get("presentation") or "road"


def passages():
    """Pasajes jugables numerados en orden de viaje: [(n, conn_id, a, b, type_a_to_b, type_b_to_a, sign_a, sign_b, extra)]."""
    order = ["conn.outpost_threshold", "conn.threshold_scarp", "conn.outpost_scarp", "conn.scarp_saltpan_ne", "conn.scarp_saltpan_sw",
             "conn.saltpan_frontier_east", "conn.frontier_east_dustline", "conn.frontier_east_dragon_lair", "conn.threshold_shallows",
             "conn.shallows_c3", "conn.threshold_c3", "conn.c3_f2", "conn.c3_f2_f3"]
    conns = {c["id"]: c for c in WORLD["connections"]}
    out = []
    for cid in order + [c["id"] for c in WORLD["connections"] if c["status"] == "playable" and c["id"] not in order]:
        c = conns.get(cid)
        if not c or c["status"] != "playable":
            continue
        a, b = c["ends"]
        # El primer extremo es el de "ida" segun el orden del viaje; para el pozo de la Scarp se lee desde la superficie.
        if cid == "conn.threshold_scarp":
            a, b = b, a
        ta, tb = pres_of(a.get("transition")), pres_of(b.get("transition"))
        if c["kind"] == "road" and (ta == "metro" or tb == "metro"):
            ta = tb = "metro"
        locked = bool(TRANS.get(a.get("transition"), {}).get("requires_drill_site_cleared"))
        out.append({"n": len(out) + 1, "id": cid, "a": a["zone"], "b": b["zone"], "ta": ta or "road", "tb": tb or ta or "road",
                    "sa": a["exit"], "sb": b["exit"], "locked": locked, "kind": c["kind"], "exit_at": c.get("exit_at")})
    for z in WORLD["zones"]:
        ex = z.get("extraction")
        if ex and z["status"] == "playable":
            out.append({"n": len(out) + 1, "id": "extraction." + z["id"], "a": z["id"], "b": ex["zone"], "ta": pres_of(ex.get("transition")) or "lift",
                        "tb": None, "sa": ex["exit"], "sb": None, "locked": False, "kind": "lift", "one_way": True, "exit_at": None})
    return out


PASS = passages()
PASS_BY = {p["id"]: p for p in PASS}


# --- Glifos (24x24, trazo) --------------------------------------------------------------------------------------
GLYPH = {
    "metro": '<path d="M4 20V11a8 8 0 0 1 16 0v9"/><path d="M9 20l1-6h4l1 6M8 17h8"/>',
    "lift": '<rect x="6" y="6" width="12" height="15" rx="1"/><path d="M12 2v4M9.5 11.5 12 9l2.5 2.5M9.5 15.5 12 18l2.5-2.5"/>',
    "stairs": '<path d="M3 20h5v-5h5v-5h5V5h3"/>',
    "road": '<path d="M8 21 10 3M16 21 14 3M12 6v2M12 11v2M12 16v2"/>',
    "gate": '<path d="M5 21V5M19 21V5M5 10h14M3 21h4M17 21h4"/>',
    "city": '<path d="M4 20V10l3-2 3 2v10M10 20V6l2-3 2 3v14M14 20v-9l3-2 3 2v9M3 20h18"/>',
    "outpost": '<path d="M8 20 12 4l4 16M9.5 14h5M10.6 9.5h2.8M5 20h14M12 4V2"/>',
    "hunt": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4"/><circle cx="12" cy="12" r="5"/>',
    "dungeon": '<path d="M5 20V11a7 7 0 0 1 14 0v9M9 20v-6a3 3 0 0 1 6 0v6M3 20h18"/>',
    "route": '<path d="M9 21 11 3M15 21 13 3M12 6v2M12 11v2M12 16v2"/>',
    "cave": '<path d="M3 19c2-7 5-11 9-11s7 4 9 11M3 19h18M10 19c0-2 1-4 2-4s2 2 2 4"/>',
    "fuel": '<rect x="4" y="4" width="10" height="17" rx="1"/><path d="M6 8h6M14 9h2l3 3v6a2 2 0 0 1-4 0v-4h-1"/>',
    "bank": '<rect x="3" y="5" width="18" height="12" rx="1"/><path d="M7 21h10M12 17v4M6 9h3M6 12h7"/>',
    "hub": '<path d="M12 21s-7-6-7-11a7 7 0 0 1 14 0c0 5-7 11-7 11Z"/><circle cx="12" cy="10" r="2.5"/>',
}
ZONE_ICON = {"zone.dustline": "city", "zone.outpost": "outpost", "zone.surface_scarp": "hunt", "zone.surface_saltpan": "route",
             "zone.frontier_road_east": "route", "zone.shallows": "hunt", "zone.threshold": "cave", "zone.excavation_c3": "dungeon",
             "zone.excavation_c3_f2": "dungeon", "zone.excavation_c3_f3": "dungeon", "zone.dragon_lair": "hunt"}


def glyph(name, x, y, size=16, color=None, sw=1.8, bg=True):
    k = size / 24
    col = color or C["text"]
    disc = (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{size * .72:.1f}" fill="{C["bg"]}" stroke="{col}" stroke-width="1.2" stroke-opacity=".7"/>' if bg else "")
    return (f'{disc}<g transform="translate({x - size / 2:.1f},{y - size / 2:.1f}) scale({k:.4f})" fill="none" stroke="{col}" '
            f'stroke-width="{sw / k:.2f}" stroke-linecap="round" stroke-linejoin="round">{GLYPH[name]}</g>')


def text(x, y, s, size=12, color=None, anchor="start", weight=500, font=MONO, ls=0.06, halo=True, extra=""):
    col = color or C["soft"]
    h = f' stroke="{C["bg"]}" stroke-width="{size * .32:.1f}" stroke-linejoin="round" paint-order="stroke"' if halo else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size}" font-weight="{weight}" fill="{col}" '
            f'text-anchor="{anchor}" letter-spacing="{ls}em"{h}{extra}>{e(s)}</text>')


def tw(s, size, ls=0.06):
    """Ancho aproximado de un texto monoespaciado."""
    return len(s) * size * (0.6 + ls)


def badge(n, x, y, r=9, col=None, fs=None):
    col = col or C["amber"]
    fs = fs or r * 1.15
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{C["bg"]}" stroke="{col}" stroke-width="1.6"/>'
            f'<text x="{x:.1f}" y="{y + fs * .36:.1f}" font-family="{MONO}" font-size="{fs:.1f}" font-weight="600" fill="{col}" text-anchor="middle">{n}</text>')


# --- Planta -----------------------------------------------------------------------------------------------------
class Plan:
    """Proyeccion de la planta: ventana (u0..u1, v0..v1) del arte de 1312x1199 dentro de un marco."""

    def __init__(self, fx, fy, fw, fh, u0, v0, u1, v1, lens=None):
        self.fx, self.fy, self.fw, self.fh = fx, fy, fw, fh
        # Lupa (2026-10-11): agranda el corredor Scarp-Saltpan-Frontier-Dustline, que en el arte es diminuto al lado de las
        # cavernas. (u, v, radio en px del arte, aumento en el centro). Esquema, no escala.
        self.lens = lens
        # Encaje: la ventana (u0..u1, v0..v1) ya deformada por la lupa entra en el marco.
        border = [(u0 + (u1 - u0) * i / 20, v) for i in range(21) for v in (v0, v1)] + [(u, v0 + (v1 - v0) * i / 20) for i in range(21) for u in (u0, u1)]
        ws = [self.warp(u * IW, v * IH) for u, v in border]
        xs, ys = [w[0] for w in ws], [w[1] for w in ws]
        self.k = min(fw / (max(xs) - min(xs)), fh / (max(ys) - min(ys)))
        self.ox = fx + fw / 2 - (max(xs) + min(xs)) / 2 * self.k
        self.oy = fy + fh / 2 - (max(ys) + min(ys)) / 2 * self.k

    def warp(self, x, y):
        if not self.lens:
            return x, y
        lu, lv, R, m = self.lens
        cx, cy = lu * IW, lv * IH
        dx, dy = x - cx, y - cy
        d = math.hypot(dx, dy)
        if d >= R or d == 0:
            return x, y
        f = m / (1 + (m - 1) * d / R)
        return cx + dx * f, cy + dy * f

    def p(self, uv):
        x, y = self.warp(uv[0] * IW, uv[1] * IH)
        return self.ox + x * self.k, self.oy + y * self.k

    def poly(self, pts):
        return "M" + "L".join("%.1f,%.1f" % self.p(q) for q in densify(pts)) + "Z"


def densify(pts, step=0.012):
    """Subdivide los bordes para que la lupa los curve con suavidad."""
    out = []
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
        out += [(a[0] + (b[0] - a[0]) * t / n, a[1] + (b[1] - a[1]) * t / n) for t in range(n)]
    return out


def shrink(pts, f):
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    return [(cx + (x - cx) * f, cy + (y - cy) * f) for x, y in pts]


DEFS = f"""<defs>
<pattern id="sea" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M0 5h10" stroke="#1d2420" stroke-width="1"/></pattern>
<pattern id="sand" width="9" height="9" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r=".9" fill="#c99a62" fill-opacity=".45"/><circle cx="6.5" cy="6" r=".7" fill="#c99a62" fill-opacity=".3"/></pattern>
<pattern id="plains" width="12" height="10" patternUnits="userSpaceOnUse"><path d="M2 6h3M8 2h3" stroke="#b3ad5a" stroke-opacity=".45" stroke-width="1"/></pattern>
<pattern id="rock" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(30)"><path d="M0 0v14" stroke="#6b7fa8" stroke-opacity=".28" stroke-width="1.2"/></pattern>
<pattern id="wet" width="16" height="10" patternUnits="userSpaceOnUse"><path d="M1 6q3-3 6 0t6 0" fill="none" stroke="#3fa3a0" stroke-opacity=".4" stroke-width="1"/></pattern>
<pattern id="hatch" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><path d="M0 0v9" stroke="#3a403b" stroke-opacity=".55" stroke-width="1"/></pattern>
<pattern id="city" width="12" height="12" patternUnits="userSpaceOnUse"><rect x="1" y="1" width="6" height="5" fill="#d39a4b" fill-opacity=".22"/><rect x="8" y="7" width="3" height="4" fill="#d39a4b" fill-opacity=".16"/></pattern>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a2a22"/><stop offset="1" stop-color="#151712"/></linearGradient>
<linearGradient id="earth" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1c1a16"/><stop offset=".45" stop-color="#151a20"/><stop offset="1" stop-color="#0d1016"/></linearGradient>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3"/></filter>
<filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="1.4"/></filter>
</defs>"""

FILL = {"desert": "url(#sand)", "plains": "url(#plains)", "wetlands": "url(#wet)", "caves": "url(#rock)", "anomaly": "url(#rock)",
        "forest": "url(#plains)", "mountains": "url(#hatch)", "snow": "url(#hatch)"}
BASE = {"surface": "#1f1c16", "underground": "#141b26"}


def anchor_uv(zid, layout):
    if zid in layout["pos"]:
        return layout["pos"][zid]
    z = ZONES[zid]
    return z.get("marker") or z.get("stack", {}).get("marker") or z["cell"]["seed"]


def plan_svg(P, lang, layout):
    out = []
    fx, fy, fw, fh = P.fx, P.fy, P.fw, P.fh
    out.append(f'<clipPath id="pc{layout["id"]}"><rect x="{fx}" y="{fy}" width="{fw}" height="{fh}"/></clipPath>')
    g = [f'<rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" fill="{C["bg"]}"/><rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" fill="url(#sea)"/>']
    cont = P.poly(WORLD["continent"]["outline"])
    g.append(f'<path d="{cont}" fill="#121411" stroke="#3b3a32" stroke-width="5" stroke-opacity=".35"/><path d="{cont}" fill="none" stroke="#6a6352" stroke-width="1.2"/>')
    # Celdas planeadas (desvaidas, "sin cartografiar")
    for z in WORLD["zones"]:
        if z["status"] != "planned" or not z.get("cell"):
            continue
        d = P.poly(z["cell"]["polygon"])
        g.append(f'<path d="{d}" fill="url(#hatch)" stroke="#3a3f3a" stroke-width="1" stroke-dasharray="4 4"/>')
    # Celdas jugables: superficie arena / subsuelo roca
    for z in WORLD["zones"]:
        if z["status"] != "playable" or not z.get("cell"):
            continue
        pts = z["cell"]["polygon"]
        d = P.poly(pts)
        under = z["layer"] == "underground"
        base = BASE[z["layer"]]
        pat = "url(#city)" if z["kind"] == "city" else FILL.get(z["biome"], "url(#sand)")
        stroke = "#7b8fb8" if under else "#b98a52"
        g.append(f'<path d="{d}" fill="{base}"/><path d="{d}" fill="{pat}"/>')
        for f, op in ((0.82, .22), (0.62, .16), (0.42, .11)):  # curvas de nivel
            g.append(f'<path d="{P.poly(shrink(pts, f))}" fill="none" stroke="{stroke}" stroke-opacity="{op}" stroke-width="1"/>')
        g.append(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{1.6 if not under else 1.4}"'
                 f'{" stroke-dasharray=" + chr(34) + "7 4" + chr(34) if under else ""} stroke-opacity=".9"/>')
    # Dustline: muralla y calles dentro de su celda
    city = WORLD.get("dustline")
    if city:
        cx, cy = layout.get("city_at", (0.69, 0.70))
        sw_, sh_ = layout.get("city_size", (0.075, 0.06))
        tf = lambda q: (cx - sw_ / 2 + q[0] * sw_, cy - sh_ / 2 + q[1] * sh_)  # noqa: E731
        g.append(f'<path d="{P.poly([tf(q) for q in city["wall"]])}" fill="#2a2116" stroke="{C["amber"]}" stroke-width="1.6"/>')
        for st in city["streets"]:
            pts = " ".join("%.1f,%.1f" % P.p(tf(q)) for q in st["points"])
            g.append(f'<polyline points="{pts}" fill="none" stroke="{C["warm"]}" stroke-opacity=".55" stroke-width="1.4"/>')
        for d_ in city["districts"]:
            g.append(f'<path d="{P.poly([tf(q) for q in d_["polygon"]])}" fill="{C["amber"]}" fill-opacity=".10" stroke="{C["amber"]}" stroke-opacity=".35" stroke-width=".8"/>')
    # Conexiones planeadas
    for c in WORLD["connections"]:
        if c["status"] != "planned":
            continue
        a, b = c["ends"][0]["zone"], c["ends"][1]["zone"]
        ax, ay = P.p(anchor_uv(a, layout))
        bx, by = P.p(anchor_uv(b, layout))
        g.append(f'<path d="M{ax:.1f},{ay:.1f}L{bx:.1f},{by:.1f}" stroke="#4a4f48" stroke-width="1.2" stroke-dasharray="2 5" fill="none"/>')
    # Etiquetas planeadas
    for z in WORLD["zones"]:
        if z["status"] != "planned":
            continue
        u, v = z.get("label") or z.get("marker")
        x, y = P.p((u, v))
        if not (fx + 30 < x < fx + fw - 30 and fy + 20 < y < fy + fh - 20):
            continue
        fs = layout["fs_planned"]
        g.append(text(x, y, z["name"].upper(), fs, "#6d6a60", "middle", 500, MONO, .08))
        g.append(text(x, y + fs * 1.25, tr("uncharted", lang), fs * .78, "#545149", "middle", 400, MONO, .18))
    g.append(passage_lines(P, lang, layout))
    g.append(routes(P, lang, layout))
    g.append(stacks(P, lang, layout))
    g.append(zone_marks(P, lang, layout))
    g.append(services(P, lang, layout))
    g.append(passage_badges(P, layout))
    out.append(f'<g clip-path="url(#pc{layout["id"]})">{"".join(g)}</g>')
    out.append(frame(fx, fy, fw, fh, tr("plan", lang), layout))
    return "".join(out)


def frame(x, y, w, h, title, layout, grid=True):
    o = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{C["line2"]}" stroke-width="1.2"/>']
    o.append(f'<rect x="{x + 5}" y="{y + 5}" width="{w - 10}" height="{h - 10}" fill="none" stroke="{C["line"]}" stroke-width=".8"/>')
    if grid:
        n = 8
        for i in range(n):
            gx = x + w * (i + .5) / n
            gy = y + h * (i + .5) / n
            o.append(text(gx, y + 17, "ABCDEFGH"[i], layout["fs_grid"], C["dim"], "middle", 500, MONO, 0, False))
            o.append(text(x + 14, gy + 4, str(i + 1), layout["fs_grid"], C["dim"], "middle", 500, MONO, 0, False))
            if i:
                o.append(f'<path d="M{x + w * i / n:.1f},{y + 5}v8M{x + 5},{y + h * i / n:.1f}h8" stroke="{C["dim"]}" stroke-width="1"/>')
    fs = layout["fs_title"]
    o.append(f'<rect x="{x + 24}" y="{y - fs * .9:.1f}" width="{tw(title, fs, .14) + 16:.1f}" height="{fs * 1.5:.1f}" fill="{C["bg"]}"/>')
    o.append(text(x + 32, y + fs * .36, title, fs, C["amber"], "start", 600, MONO, .14, False))
    return "".join(o)


def curve(P, a, b, layout, via=None):
    ax, ay = P.p(anchor_uv(a, layout))
    bx, by = P.p(anchor_uv(b, layout))
    if via:
        ex, ey = P.p(via)
        cx, cy = 2 * ex - (ax + bx) / 2, 2 * ey - (ay + by) / 2
        return f"M{ax:.1f},{ay:.1f}Q{cx:.1f},{cy:.1f} {bx:.1f},{by:.1f}", ((ax + bx) / 2 + cx) / 2, ((ay + by) / 2 + cy) / 2
    return f"M{ax:.1f},{ay:.1f}L{bx:.1f},{by:.1f}", (ax + bx) / 2, (ay + by) / 2


def passage_geom(P, p, layout):
    via = layout["via"].get(p["id"], p.get("exit_at"))
    return curve(P, p["a"], p["b"], layout, via)


def stroke_for(p):
    t = p["ta"]
    col = TYPE_COLOR.get(t, C["soft"])
    if t == "road" or t == "gate":
        return f'stroke="{col}" stroke-width="3.2" stroke-opacity=".85"'
    if t == "metro":
        return f'stroke="{col}" stroke-width="2.6" stroke-dasharray="9 3"'
    return f'stroke="{col}" stroke-width="2" stroke-dasharray="2 4" stroke-linecap="round"'


def passage_lines(P, lang, layout):
    o = []
    for p in PASS:
        d, _, _ = passage_geom(P, p, layout)
        if p["ta"] in ("road", "gate"):
            o.append(f'<path d="{d}" fill="none" stroke="#0b0d0c" stroke-width="6.5"/>')
        o.append(f'<path d="{d}" fill="none" {stroke_for(p)}/>')
    return "".join(o)


def passage_badges(P, layout):
    o = []
    r = layout["badge_r"]
    for p in PASS:
        d, mx, my = passage_geom(P, p, layout)
        dx, dy = layout["badge_off"].get(p["id"], (0, 0))
        x, y = mx + dx * r, my + dy * r
        col = TYPE_COLOR.get(p["ta"], C["soft"])
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r * 1.55:.1f}" fill="{C["bg"]}" stroke="{col}" stroke-width="1.4"/>')
        o.append(glyph(p["ta"], x - r * .55, y, r * 1.25, col, 1.7, False))
        o.append(text(x + r * .62, y + r * .42, str(p["n"]), r * 1.1, col, "middle", 600, MONO, 0, False))
    return "".join(o)


def routes(P, lang, layout):
    j = next(r for r in WORLD["routes"] if r["id"] == "route.first_journey")
    segs = []
    for cid in j["connections"]:
        p = PASS_BY.get(cid)
        if p:
            d, _, _ = passage_geom(P, p, layout)
            segs.append(d)
    d = " ".join(segs)
    o = [f'<path d="{d}" fill="none" stroke="{C["amber"]}" stroke-width="11" stroke-opacity=".28" filter="url(#glow)"/>',
         f'<path d="{d}" fill="none" stroke="{C["amber"]}" stroke-width="2.2" stroke-opacity=".95"/>']
    # Ramal a The Cinder Deep
    p = PASS_BY.get("conn.frontier_east_dragon_lair")
    if p:
        d2, _, _ = passage_geom(P, p, layout)
        o.append(f'<path d="{d2}" fill="none" stroke="{C["danger"]}" stroke-width="9" stroke-opacity=".25" filter="url(#glow)"/>')
        o.append(f'<path d="{d2}" fill="none" stroke="{C["danger"]}" stroke-width="2" stroke-dasharray="6 4"/>')
    # Pasos del viaje
    for i, zid in enumerate(j["zones"]):
        x, y = P.p(anchor_uv(zid, layout))
        dx, dy = layout["step_off"].get(zid, (14, -14))
        o.append(f'<path d="M{x:.1f},{y:.1f}L{x + dx:.1f},{y + dy:.1f}" stroke="{C["amber"]}" stroke-width="1"/>')
        o.append(badge(f"{i:02d}", x + dx, y + dy, layout["step_r"], C["amber"], layout["step_r"] * .95))
    return "".join(o)


def stacks(P, lang, layout):
    """Niveles apilados: una placa desplazada con su sombra, unida al mapa padre."""
    o = []
    for z in WORLD["zones"]:
        if not z.get("stack") or z["status"] != "playable":
            continue
        x, y = P.p(anchor_uv(z["id"], layout))
        px, py = P.p(anchor_uv(z["stack"]["parent"], layout))
        o.append(f'<path d="M{px:.1f},{py:.1f}L{x:.1f},{y:.1f}" stroke="#7b8fb8" stroke-width="1" stroke-dasharray="3 3"/>')
        s = layout["plate"]
        for k_, op in ((2, .5), (1, .8)):
            o.append(f'<rect x="{x - s + k_ * 3:.1f}" y="{y - s * .7 + k_ * 3:.1f}" width="{2 * s}" height="{1.4 * s}" rx="2" fill="{C["cave"]}" stroke="#7b8fb8" stroke-opacity="{op * .5}"/>')
        o.append(f'<rect x="{x - s:.1f}" y="{y - s * .7:.1f}" width="{2 * s}" height="{1.4 * s}" rx="2" fill="{C["cave2"]}" stroke="#9fb3d8" stroke-width="1.3"/>')
        o.append(glyph(ZONE_ICON.get(z["id"], "cave"), x, y, s * 1.05, "#cfdcf5", 1.7, False))
    return "".join(o)


def zone_marks(P, lang, layout):
    o = []
    for z in WORLD["zones"]:
        if z["status"] != "playable":
            continue
        zid = z["id"]
        x, y = P.p(anchor_uv(zid, layout))
        under = z["layer"] == "underground"
        if not z.get("stack"):
            r = layout["mark_r"] * (1.25 if z["kind"] == "city" else 1)
            col = "#9fb3d8" if under else C["warm"]
            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r + 4:.1f}" fill="{col}" fill-opacity=".12"/>')
            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{C["bg"]}" stroke="{col}" stroke-width="1.8"/>')
            o.append(glyph(ZONE_ICON.get(zid, "route"), x, y, r * 1.15, col, 1.8, False))
        lab = layout["labels"].get(zid)
        if not lab:
            continue
        lx, ly, anc = x + lab[0], y + lab[1], lab[2]
        if len(lab) > 3 and lab[3]:  # linea guia
            o.append(f'<path d="M{x:.1f},{y:.1f}L{lx:.1f},{ly - layout["fs_zone"] * .35:.1f}" stroke="{C["muted"]}" stroke-width=".8"/>')
        fs = layout["fs_zone"]
        name = z["name"].upper()
        col = "#cfdcf5" if under else C["text"]
        o.append(text(lx, ly, name, fs, col, anc, 600, MONO, .07))
        depth = z.get("depth_m", 0)
        sub = (z.get("level_label", "") + " · " if z.get("level_label") else "") + (f"−{depth} m" if depth else ("SURFACE" if lang == "en" else "SUPERFICIE"))
        if zid == "zone.excavation_c3_f2" or zid == "zone.excavation_c3_f3":
            sub = z["subtitle"][lang].upper() + " · −" + str(depth) + " m"
        o.append(text(lx, ly + fs * 1.2, sub, fs * .74, "#8ea2c8" if under else C["amber"], anc, 500, MONO, .1))
    return "".join(o)


def services(P, lang, layout):
    """Servicios: estacion de servicio, terminales de banco/deposito y puntos de reaparicion."""
    o = []
    sz = layout["svc"]
    hubs = {h["zone_id"] for h in HUBS["hubs"]}
    for zid, (ox, oy) in layout["svc_off"].items():
        x, y = P.p(anchor_uv(zid, layout))
        x, y = x + ox, y + oy
        icons = []
        if zid in hubs:
            icons.append(("hub", C["green"]))
        if FLOORS.get(zid, {}).get("computers"):
            icons.append(("bank", C["green"]))
        for i, (ic, col) in enumerate(icons):
            o.append(glyph(ic, x + i * sz * 1.7, y, sz, col, 1.7, True))
    for st in [s for f in REGION["floors"] for s in f.get("fuel_stations", [])]:
        x, y = P.p(anchor_uv("zone.frontier_road_east", layout))
        x, y = x + layout["fuel_off"][0], y + layout["fuel_off"][1]
        o.append(glyph("fuel", x, y, sz, C["danger"], 1.8, True))
        lab = layout["fuel_label"]
        o.append(text(x + lab[0], y + lab[1], st["name"], layout["fs_zone"] * .72, C["danger"], lab[2], 600, MONO, .1))
    return "".join(o)


# --- Corte de profundidades ----------------------------------------------------------------------------------------
SEC_X = {"zone.outpost": .09, "zone.surface_scarp": .29, "zone.threshold": .29, "zone.surface_saltpan": .50, "zone.shallows": .66,
         "zone.excavation_c3": .47, "zone.excavation_c3_f2": .47, "zone.excavation_c3_f3": .47, "zone.frontier_road_east": .705,
         "zone.dragon_lair": .87, "zone.dustline": .91}


def section_svg(x0, y0, w, h, lang, L):
    o = []
    top = y0 + L["sec_top"]
    bottom = y0 + h - 18

    def Y(d):
        k1 = L["sec_k1"]
        if d <= 150:
            return top + d * k1
        return top + 150 * k1 + (d - 150) * (bottom - top - 150 * k1) / (560 - 150)

    def X(zid):
        return x0 + 26 + SEC_X[zid] * (w - 52)
    o.append(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="{C["panel"]}"/>')
    o.append(f'<rect x="{x0}" y="{y0 + 4}" width="{w}" height="{top - y0 - 4}" fill="url(#sky)"/>')
    o.append(f'<rect x="{x0}" y="{top:.1f}" width="{w}" height="{bottom - top + 18:.1f}" fill="url(#earth)"/>')
    # Bandas
    fsb = L["fs_band"]
    for d0, d1, key in ((0, 200, "band1"), (200, 400, "band2"), (400, 560, "band3")):
        yb = Y(d0)
        o.append(f'<path d="M{x0},{yb:.1f}h{w}" stroke="{C["amber"] if d0 == 0 else C["line2"]}" stroke-width="{1.6 if d0 == 0 else 1}"'
                 f'{"" if d0 == 0 else " stroke-dasharray=" + chr(34) + "6 5" + chr(34)}/>')
        o.append(text(x0 + w - 10, yb + fsb * 1.35, tr(key, lang), fsb, C["dim"], "end", 500, MONO, .12, False))
    o.append(text(x0 + w - 10, top - 8, tr("surface", lang), fsb, C["amber"], "end", 600, MONO, .12, False))
    # Ruler
    for d in (0, 60, 90, 120, 140, 200, 340, 400, 520):
        yy = Y(d)
        o.append(f'<path d="M{x0},{yy:.1f}h8" stroke="{C["muted"]}" stroke-width="1"/>')
        o.append(text(x0 + 11, yy + fsb * .35, f"{d}", fsb * .9, C["muted"], "start", 500, MONO, 0, False))
    # Rugosidad del terreno en superficie
    pts = []
    for i in range(0, int(w) + 1, 12):
        pts.append(f"{x0 + i:.0f},{top - 3 - 3 * math.sin(i * .09) - 2 * math.sin(i * .23):.1f}")
    o.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#8a6a44" stroke-width="1.4"/>')
    # Estratos ilustrativos
    for i in range(7):
        yy = Y(25 + i * 70)
        o.append(f'<path d="M{x0},{yy:.1f}q{w * .25:.0f},{-6 + i % 3 * 4} {w * .5:.0f},0t{w * .5:.0f},0" fill="none" stroke="#2b3240" stroke-width="1"/>')
    nodes = {}
    for zid in SEC_X:
        z = ZONES[zid]
        nodes[zid] = (X(zid), Y(z.get("depth_m", 0)))
    # Conexiones
    for p in PASS:
        a, b = p["a"], p["b"]
        if a not in nodes or b not in nodes:
            continue
        (ax, ay), (bx, by) = nodes[a], nodes[b]
        col = TYPE_COLOR.get(p["ta"], C["soft"])
        off = L["sec_off"].get(p["id"], 0)
        if p.get("one_way"):
            ax += 34
            bx += 34
            o.append(f'<path d="M{ax:.1f},{ay:.1f}L{bx:.1f},{by:.1f}" stroke="{col}" stroke-width="1.8" stroke-dasharray="2 4" stroke-linecap="round"/>')
            o.append(f'<path d="M{bx - 6:.1f},{by + 12:.1f}L{bx:.1f},{by + 2:.1f}L{bx + 6:.1f},{by + 12:.1f}" fill="none" stroke="{col}" stroke-width="2"/>')
        else:
            if abs(ay - by) < 1:
                ay += off
                by += off
            else:
                ax += off
                bx += off
            dash = "" if p["ta"] in ("road", "gate") else (' stroke-dasharray="9 3"' if p["ta"] == "metro" else ' stroke-dasharray="2 4" stroke-linecap="round"')
            o.append(f'<path d="M{ax:.1f},{ay:.1f}L{bx:.1f},{by:.1f}" stroke="{col}" stroke-width="{2.6 if p["ta"] in ("road", "gate") else 2}"{dash}/>')
        p["_sec"] = ((ax + bx) / 2, (ay + by) / 2)
    # Ruta recomendada en el corte
    j = next(r for r in WORLD["routes"] if r["id"] == "route.first_journey")
    rp = " ".join("%.1f,%.1f" % nodes[zid] for zid in j["zones"] if zid in nodes)
    o.append(f'<polyline points="{rp}" fill="none" stroke="{C["amber"]}" stroke-width="9" stroke-opacity=".22" filter="url(#glow)"/>')
    # Nodos
    nw, nh, fs = L["node_w"], L["node_h"], L["fs_node"]
    for zid, (x, y) in nodes.items():
        z = ZONES[zid]
        under = z["layer"] == "underground"
        col = "#9fb3d8" if under else C["warm"]
        ww = nw
        o.append(f'<rect x="{x - ww / 2:.1f}" y="{y - nh / 2:.1f}" width="{ww:.1f}" height="{nh}" rx="3" fill="{C["cave2"] if under else "#2a241a"}" stroke="{col}" stroke-width="1.4"/>')
        name = L["short"].get(zid, z["name"].replace("The ", "")).upper()
        o.append(text(x, y - 1, name, fs, C["text"], "middle", 600, MONO, .04, False))
        sub = (z.get("level_label") + " · " if z.get("level_label") else "") + (f"−{z['depth_m']} m" if z.get("depth_m") else "0 m")
        o.append(text(x, y + fs * 1.05, sub, fs * .78, col, "middle", 500, MONO, .06, False))
    # Insignias de pasajes
    r = L["badge_r"]
    for p in PASS:
        if "_sec" not in p:
            continue
        x, y = p["_sec"]
        dx, dy = L["sec_badge"].get(p["id"], (0, 0))
        x, y = x + dx, y + dy
        col = TYPE_COLOR.get(p["ta"], C["soft"])
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r * 1.5:.1f}" fill="{C["bg"]}" stroke="{col}" stroke-width="1.3"/>')
        o.append(glyph(p["ta"], x - r * .55, y, r * 1.2, col, 1.7, False))
        o.append(text(x + r * .62, y + r * .4, str(p["n"]), r * 1.05, col, "middle", 600, MONO, 0, False))
        if p["locked"]:
            o.append(text(x - r * 1.9, y + r * .4, "■ " + tr("locked", lang), r * .95, C["danger"], "end", 500, MONO, .02))
        if p.get("one_way"):
            o.append(text(x + r * 1.9, y + r * .4, "↑ " + tr("one_way", lang), r * .95, C["amber"], "start", 500, MONO, .02))
    o.append(frame(x0, y0, w, h, tr("section", lang), L, grid=False))
    return "".join(o)


# --- Clave de pasajes y referencias ------------------------------------------------------------------------------
def key_svg(x0, y0, w, lang, L, cols=1):
    o = []
    fs = L["fs_key"]
    lh = fs * 1.42
    rowh = lh * 3 + fs * .5
    o.append(text(x0, y0, tr("passages", lang), L["fs_title"], C["amber"], "start", 600, MONO, .14, False))
    colw = w / cols
    per = math.ceil(len(PASS) / cols)
    for i, p in enumerate(PASS):
        cx = x0 + (i // per) * colw
        y = y0 + L["fs_title"] * 1.1 + (i % per) * rowh + fs
        col = TYPE_COLOR.get(p["ta"], C["soft"])
        r = fs * .78
        o.append(f'<circle cx="{cx + r * 1.3:.1f}" cy="{y + fs * .6:.1f}" r="{r * 1.45:.1f}" fill="{C["bg"]}" stroke="{col}" stroke-width="1.3"/>')
        o.append(glyph(p["ta"], cx + r * .75, y + fs * .6, r * 1.2, col, 1.7, False))
        o.append(text(cx + r * 1.9, y + fs * .6 + r * .4, str(p["n"]), r * 1.05, col, "middle", 600, MONO, 0, False))
        tx = cx + r * 3.4
        if p.get("one_way"):
            kind = tr("t_" + p["ta"], lang) + " · " + tr("one_way", lang)
        elif p["ta"] == p["tb"]:
            kind = tr("t_" + p["ta"], lang)
        elif ZONES[p["b"]].get("depth_m", 0) == ZONES[p["a"]].get("depth_m", 0):
            kind = f'{tr("t_" + p["ta"], lang)} → · {tr("t_" + p["tb"], lang).lower()} ←'
        else:
            dn = ZONES[p["b"]].get("depth_m", 0) > ZONES[p["a"]].get("depth_m", 0)
            kind = f'{tr("t_" + p["ta"], lang)} ({tr("down" if dn else "up", lang)}) · {tr("t_" + p["tb"], lang).lower()} ({tr("up" if dn else "down", lang)})'
        head = f'{L["short"].get(p["a"], zname(p["a"]).replace("The ", ""))} {"→" if p.get("one_way") else "⇄"} {L["short"].get(p["b"], zname(p["b"]).replace("The ", ""))}'
        o.append(text(tx, y + fs * .3, head.upper(), fs, C["text"], "start", 600, MONO, .04, False))
        o.append(text(tx + tw(head, fs, .04) + fs * .6, y + fs * .3, kind, fs * .86, col, "start", 500, MONO, .02, False))
        o.append(text(tx, y + fs * .3 + lh, "▸ " + p["sa"], fs * .86, C["green"], "start", 400, MONO, .02, False))
        if p["sb"]:
            o.append(text(tx, y + fs * .3 + 2 * lh, "◂ " + p["sb"], fs * .86, "#7fd99a", "start", 400, MONO, .02, False))
        if p["locked"]:
            o.append(text(tx + tw("▸ " + p["sa"], fs * .86, .02) + fs * .5, y + fs * .3 + lh, tr("locked", lang), fs * .8, C["danger"], "start", 500, MONO, 0, False))
    return "".join(o), y0 + L["fs_title"] * 1.1 + per * rowh + fs


def legend_svg(x0, y0, w, lang, L, cols=3):
    fs = L["fs_key"]
    items = [("city", C["warm"], "i_city"), ("outpost", C["warm"], "i_outpost"), ("hunt", C["warm"], "i_hunt"), ("route", C["warm"], "i_route"),
             ("cave", "#9fb3d8", "i_cave"), ("dungeon", "#9fb3d8", "i_dungeon"), ("fuel", C["danger"], "i_fuel"), ("bank", C["green"], "i_bank"),
             ("hub", C["green"], "i_hub")]
    lines = [("road", "t_road"), ("metro", "t_metro"), ("lift", "t_lift"), ("stairs", "t_stairs"), ("gate", "t_gate")]
    o = [text(x0, y0, tr("legend", lang), L["fs_title"], C["amber"], "start", 600, MONO, .14, False)]
    y = y0 + L["fs_title"] * 1.4
    colw = w / cols
    lh = fs * 1.9
    for i, (g_, col, key) in enumerate(items):
        cx = x0 + (i % cols) * colw
        cy = y + (i // cols) * lh
        o.append(glyph(g_, cx + fs * .8, cy, fs * 1.15, col, 1.8, True))
        o.append(text(cx + fs * 2.1, cy + fs * .36, tr(key, lang), fs, C["soft"], "start", 400, MONO, .02, False))
    y += math.ceil(len(items) / cols) * lh + fs * .4
    for i, (k, key) in enumerate(lines):
        cx = x0 + (i % cols) * colw
        cy = y + (i // cols) * lh
        p = {"ta": k}
        o.append(f'<path d="M{cx:.1f},{cy:.1f}h{fs * 2.6:.1f}" fill="none" {stroke_for(p)}/>')
        o.append(text(cx + fs * 3.2, cy + fs * .36, tr(key, lang), fs, TYPE_COLOR[k], "start", 500, MONO, .02, False))
    y += math.ceil(len(lines) / cols) * lh + fs * .4
    extra = [("surf", "l_surface"), ("under", "l_under"), ("stack", "l_stack"), ("plan", "l_planned"), ("route", "route_short"), ("cinder", "cinder_route")]
    for i, (k, key) in enumerate(extra):
        cx = x0 + (i % cols) * colw
        cy = y + (i // cols) * lh
        if k == "surf":
            sw = f'<rect x="{cx:.1f}" y="{cy - fs * .6:.1f}" width="{fs * 2.6:.1f}" height="{fs * 1.2:.1f}" fill="#1f1c16" stroke="#b98a52"/><rect x="{cx:.1f}" y="{cy - fs * .6:.1f}" width="{fs * 2.6:.1f}" height="{fs * 1.2:.1f}" fill="url(#sand)"/>'
        elif k == "under":
            sw = f'<rect x="{cx:.1f}" y="{cy - fs * .6:.1f}" width="{fs * 2.6:.1f}" height="{fs * 1.2:.1f}" fill="#141b26" stroke="#7b8fb8" stroke-dasharray="5 3"/><rect x="{cx:.1f}" y="{cy - fs * .6:.1f}" width="{fs * 2.6:.1f}" height="{fs * 1.2:.1f}" fill="url(#rock)"/>'
        elif k == "stack":
            sw = (f'<rect x="{cx + 6:.1f}" y="{cy - fs * .45:.1f}" width="{fs * 2:.1f}" height="{fs * 1.1:.1f}" rx="2" fill="{C["cave"]}" stroke="#7b8fb8" stroke-opacity=".4"/>'
                  f'<rect x="{cx + 2:.1f}" y="{cy - fs * .7:.1f}" width="{fs * 2:.1f}" height="{fs * 1.1:.1f}" rx="2" fill="{C["cave2"]}" stroke="#9fb3d8"/>')
        elif k == "plan":
            sw = f'<rect x="{cx:.1f}" y="{cy - fs * .6:.1f}" width="{fs * 2.6:.1f}" height="{fs * 1.2:.1f}" fill="url(#hatch)" stroke="#3a3f3a" stroke-dasharray="4 4"/>'
        elif k == "route":
            sw = f'<path d="M{cx:.1f},{cy:.1f}h{fs * 2.6:.1f}" stroke="{C["amber"]}" stroke-width="7" stroke-opacity=".3"/><path d="M{cx:.1f},{cy:.1f}h{fs * 2.6:.1f}" stroke="{C["amber"]}" stroke-width="2.2"/>'
        else:
            sw = f'<path d="M{cx:.1f},{cy:.1f}h{fs * 2.6:.1f}" stroke="{C["danger"]}" stroke-width="2" stroke-dasharray="6 4"/>'
        o.append(sw)
        o.append(text(cx + fs * 3.2, cy + fs * .36, tr(key, lang), fs, C["soft"], "start", 400, MONO, .02, False))
    y += math.ceil(len(extra) / cols) * lh
    o.append(text(x0, y + fs * .6, tr("ride", lang), fs * .9, C["muted"], "start", 400, MONO, .02, False))
    return "".join(o), y + fs * 1.2


def locator(x0, y0, w, lang, win, L):
    """Mini continente: la ventana de la planta y todo lo planeado alrededor."""
    k = w / IW
    h = IH * k
    P = lambda q: (x0 + q[0] * IW * k, y0 + q[1] * IH * k)  # noqa: E731
    d = "M" + "L".join("%.1f,%.1f" % P(q) for q in WORLD["continent"]["outline"]) + "Z"
    o = [f'<rect x="{x0 - 6}" y="{y0 - 6}" width="{w + 12}" height="{h + 12:.1f}" fill="{C["bg"]}" stroke="{C["line2"]}"/>',
         f'<path d="{d}" fill="#151815" stroke="#6a6352" stroke-width=".8"/>']
    for z in WORLD["zones"]:
        if not z.get("cell"):
            continue
        dd = "M" + "L".join("%.1f,%.1f" % P(q) for q in z["cell"]["polygon"]) + "Z"
        if z["status"] == "playable":
            o.append(f'<path d="{dd}" fill="{"#b98a52" if z["layer"] == "surface" else "#5a6e98"}" fill-opacity=".6" stroke="#0b0d0c" stroke-width=".5"/>')
        else:
            o.append(f'<path d="{dd}" fill="url(#hatch)" stroke="#2f342f" stroke-width=".5"/>')
    u0, v0, u1, v1 = win
    a, b = P((u0, v0)), P((u1, v1))
    o.append(f'<rect x="{a[0]:.1f}" y="{a[1]:.1f}" width="{b[0] - a[0]:.1f}" height="{b[1] - a[1]:.1f}" fill="none" stroke="{C["amber"]}" stroke-width="1.2"/>')
    o.append(text(x0 + w / 2, y0 + h + L["fs_grid"] * 1.9, ("THE CONTINENT" if lang == "en" else "EL CONTINENTE"), L["fs_grid"], C["muted"], "middle", 500, MONO, .14, False))
    return "".join(o)


def compass(x, y, r):
    return (f'<g transform="translate({x:.1f},{y:.1f})"><circle r="{r}" fill="{C["bg"]}" fill-opacity=".7" stroke="{C["line2"]}"/>'
            f'<path d="M0,{-r * .85:.1f}L{r * .22:.1f},0L0,{r * .85:.1f}L{-r * .22:.1f},0Z" fill="{C["dim"]}"/>'
            f'<path d="M0,{-r * .85:.1f}L{r * .22:.1f},0L{-r * .22:.1f},0Z" fill="{C["amber"]}"/>'
            f'<text y="{-r - 5:.1f}" font-family="{MONO}" font-size="{r * .55:.1f}" fill="{C["amber"]}" text-anchor="middle">N</text></g>')


def header(x, y, lang, fs):
    return (text(x, y, "DEEPKIN · " + tr("title", lang), fs * 1.9, C["text"], "start", 600, COND, .1, False)
            + text(x, y + fs * 1.55, tr("sub", lang), fs, C["soft"], "start", 400, MONO, .02, False)
            + text(x, y + fs * 2.85, tr("survey", lang) + "  ·  NET 261.6.66", fs * .78, C["dim"], "start", 500, MONO, .14, False))


LENS = (0.55, 0.672, 560, 2.0)


# --- Laminas ------------------------------------------------------------------------------------------------------
def common_layout():
    return {
        "pos": {"zone.dragon_lair": (0.552, 0.766), "zone.threshold": (0.432, 0.633), "zone.excavation_c3_f2": (0.428, 0.893),
                "zone.excavation_c3_f3": (0.428, 0.952)},
        "via": {"conn.outpost_threshold": None, "conn.threshold_scarp": None, "conn.threshold_shallows": (0.38, 0.55),
                "conn.shallows_c3": (0.335, 0.66), "conn.threshold_c3": None, "conn.frontier_east_dragon_lair": None,
                "conn.c3_f2": None, "conn.c3_f2_f3": None, "conn.outpost_scarp": (0.452, 0.556),
                "extraction.zone.excavation_c3_f3": (0.395, 0.905)},
        "short": {"zone.excavation_c3": "C-3 F1", "zone.excavation_c3_f2": "C-3 F2", "zone.excavation_c3_f3": "C-3 F3",
                  "zone.frontier_road_east": "Frontier Rd", "zone.dragon_lair": "Cinder Deep", "zone.surface_scarp": "Scarp",
                  "zone.surface_saltpan": "Saltpan"},
        "city_at": (0.676, 0.666), "city_size": (0.085, 0.066),
        "fuel_off": (44, -26),
        "svc_off": {"zone.outpost": (-34, 42), "zone.dustline": (-6, -40)},
    }


def wide(lang):
    win = (0.255, 0.355, 0.825, 0.985)
    L = common_layout()
    L.update({"id": "w", "fs_zone": 15, "fs_planned": 11.5, "fs_grid": 11, "fs_title": 14, "fs_band": 11, "fs_node": 12.5, "fs_key": 12.5,
              "mark_r": 13, "plate": 15, "badge_r": 8, "step_r": 11, "svc": 13,
              "labels": {"zone.outpost": (-20, -16, "end"), "zone.shallows": (0, -26, "middle"), "zone.excavation_c3": (-22, -6, "end"),
                         "zone.surface_scarp": (6, -24, "middle"), "zone.surface_saltpan": (-4, 34, "middle"),
                         "zone.frontier_road_east": (30, 8, "start"), "zone.dustline": (26, 34, "start"),
                         "zone.threshold": (-26, 44, "end", True), "zone.dragon_lair": (-24, 4, "end"),
                         "zone.excavation_c3_f2": (26, 5, "start"), "zone.excavation_c3_f3": (26, 5, "start")},
              "step_off": {"zone.outpost": (-24, 16), "zone.threshold": (22, 16), "zone.surface_scarp": (-26, -18),
                           "zone.surface_saltpan": (-24, 12), "zone.frontier_road_east": (-26, -14), "zone.dustline": (-30, -8)},
              "badge_off": {"conn.outpost_threshold": (-1.2, -1.6), "conn.threshold_scarp": (1.6, 0.4), "conn.scarp_saltpan_ne": (1.6, -1.6),
                            "conn.scarp_saltpan_sw": (-1.4, 1.6), "conn.frontier_east_dragon_lair": (1.9, 0.2),
                            "conn.c3_f2": (1.8, 0), "conn.c3_f2_f3": (1.8, 0), "extraction.zone.excavation_c3_f3": (-1.6, 0),
                            "conn.saltpan_frontier_east": (0, 1.8), "conn.frontier_east_dustline": (-2.2, 0.6), "conn.outpost_scarp": (0, -1.8),
                            "conn.threshold_c3": (1.8, 0.3), "conn.threshold_shallows": (-1.2, 0), "conn.shallows_c3": (-1.8, 0)},
              "fuel_label": (-14, 4, "end"),
              "sec_top": 84, "sec_k1": 4.1, "node_w": 94, "node_h": 36,
              "sec_off": {"conn.scarp_saltpan_ne": -6, "conn.scarp_saltpan_sw": 6, "conn.outpost_threshold": 0},
              "sec_badge": {"conn.scarp_saltpan_ne": (0, -16), "conn.scarp_saltpan_sw": (0, 18), "conn.threshold_scarp": (16, -40),
                            "conn.outpost_scarp": (-12, 0), "conn.outpost_threshold": (-14, 8), "conn.saltpan_frontier_east": (0, -16),
                            "conn.frontier_east_dustline": (0, -16), "conn.frontier_east_dragon_lair": (16, 0), "conn.threshold_shallows": (0, -16),
                            "conn.shallows_c3": (12, 8), "conn.threshold_c3": (-14, 10), "conn.c3_f2": (-18, 0), "conn.c3_f2_f3": (-18, 0),
                            "extraction.zone.excavation_c3_f3": (0, -30)}})
    pf = (24, 150, 960, 1040)
    P = Plan(*pf, *win, lens=LENS)
    W_, H_ = 1600, 1800
    o = [DEFS, f'<rect width="{W_}" height="{H_}" fill="{C["bg"]}"/>', header(24, 56, lang, 15)]
    o.append(plan_svg(P, lang, L))
    o.append(compass(pf[0] + pf[2] - 48, pf[1] + 62, 22))
    o.append(locator(pf[0] + 26, pf[1] + pf[3] - 186, 150, lang, win, L))
    o.append(route_card(pf[0] + pf[2] - 300, pf[1] + pf[3] - 150, 280, lang, L))
    o.append(section_svg(1010, 150, 566, 1040, lang, L))
    k, ky = key_svg(24, 1250, 1552, lang, L, cols=3)
    o.append(k)
    lg, ly = legend_svg(24, ky + 40, 1552, lang, L, cols=5)
    o.append(lg)
    H_ = int(ly + 30)
    head = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W_} {H_}" width="{W_}" height="{H_}" role="img" aria-label="DEEPKIN {e(tr("title", lang))}">'
    return head + "".join(o) + "</svg>", (W_, H_)


def route_card(x, y, w, lang, L):
    j = next(r for r in WORLD["routes"] if r["id"] == "route.first_journey")
    fs = L["fs_key"] * .9
    lines = [L["short"].get(z, zname(z).replace("The ", "")) for z in j["zones"]]
    h = fs * 1.5 * (len(lines) + 2.2)
    o = [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h:.1f}" fill="{C["bg"]}" fill-opacity=".88" stroke="{C["amber"]}" stroke-opacity=".6"/>',
         text(x + 12, y + fs * 1.6, tr("route", lang), fs * .85, C["amber"], "start", 600, MONO, .08, False)]
    for i, n in enumerate(lines):
        yy = y + fs * 1.6 + (i + 1) * fs * 1.5
        p = PASS_BY.get(j["connections"][i]) if i < len(j["connections"]) else None
        o.append(text(x + 12, yy, f"{i:02d}  {n.upper()}", fs, C["text"], "start", 500, MONO, .04, False))
        if p:
            o.append(text(x + w - 12, yy, f"→ {p['n']} {tr('t_' + p['ta'], lang).lower()}", fs * .85, TYPE_COLOR[p["ta"]], "end", 500, MONO, 0, False))
    m = j.get("target_minutes", {})
    if m:
        a, b = m["first_time"]
        o.append(text(x + 12, y + h - fs * .6, (f"≈ {a}–{b} min" if lang == "en" else f"≈ {a}–{b} min"), fs * .85, C["muted"], "start", 400, MONO, .04, False))
    return "".join(o)


def tall(lang):
    W_ = 640
    win = (0.335, 0.42, 0.745, 0.975)
    L = common_layout()
    L.update({"id": "t", "fs_zone": 16.5, "fs_planned": 11.5, "fs_grid": 12, "fs_title": 16, "fs_band": 13, "fs_node": 13.5, "fs_key": 16,
              "mark_r": 14, "plate": 15, "badge_r": 9.5, "step_r": 11.5, "svc": 14,
              "labels": {"zone.outpost": (16, -28, "start"), "zone.shallows": (20, -24, "middle"), "zone.excavation_c3": (-6, -28, "start"),
                         "zone.surface_scarp": (22, -22, "start"), "zone.surface_saltpan": (0, 36, "middle"),
                         "zone.frontier_road_east": (30, 8, "start"), "zone.dustline": (26, 36, "start"),
                         "zone.threshold": (-10, 92, "start", True), "zone.dragon_lair": (0, 32, "middle"),
                         "zone.excavation_c3_f2": (24, 5, "start"), "zone.excavation_c3_f3": (24, 5, "start")},
              "step_off": {"zone.outpost": (-26, 16), "zone.threshold": (22, 18), "zone.surface_scarp": (-24, -20),
                           "zone.surface_saltpan": (-22, 16), "zone.frontier_road_east": (-26, -16), "zone.dustline": (26, -26)},
              "badge_off": {"conn.outpost_threshold": (-1.2, -1.6), "conn.threshold_scarp": (1.6, 0.4), "conn.scarp_saltpan_ne": (1.6, -1.6),
                            "conn.scarp_saltpan_sw": (-1.6, -1.4), "conn.frontier_east_dragon_lair": (1.9, 0.2),
                            "conn.c3_f2": (1.8, 0), "conn.c3_f2_f3": (1.8, 0), "extraction.zone.excavation_c3_f3": (-1.6, 0),
                            "conn.saltpan_frontier_east": (0, -1.8), "conn.frontier_east_dustline": (-2.2, 0.6), "conn.outpost_scarp": (0, -1.8),
                            "conn.threshold_c3": (1.8, 0.3), "conn.threshold_shallows": (-1.2, 0), "conn.shallows_c3": (-1.8, 0)},
              "fuel_label": (-14, 4, "end"),
              "sec_top": 84, "sec_k1": 3.3, "node_w": 104, "node_h": 36,
              "sec_off": {"conn.scarp_saltpan_ne": -6, "conn.scarp_saltpan_sw": 6},
              "sec_badge": {"conn.scarp_saltpan_ne": (0, -16), "conn.scarp_saltpan_sw": (0, 18), "conn.threshold_scarp": (16, -40),
                            "conn.outpost_scarp": (-12, 0), "conn.outpost_threshold": (-14, 8), "conn.saltpan_frontier_east": (0, -16),
                            "conn.frontier_east_dustline": (0, -16), "conn.frontier_east_dragon_lair": (16, 0), "conn.threshold_shallows": (0, -16),
                            "conn.shallows_c3": (12, 8), "conn.threshold_c3": (-14, 10), "conn.c3_f2": (-18, 0), "conn.c3_f2_f3": (-18, 0),
                            "extraction.zone.excavation_c3_f3": (0, -30)}})
    L["pos"].update({"zone.excavation_c3_f2": (0.44, 0.868), "zone.excavation_c3_f3": (0.44, 0.958)})
    pf = (12, 128, W_ - 24, 780)
    P = Plan(*pf, *win, lens=(0.55, 0.672, 520, 2.6))
    sec_y = pf[1] + pf[3] + 40
    sec_h = 760
    key_y = sec_y + sec_h + 46
    o = [DEFS, f'<rect width="{W_}" height="99999" fill="{C["bg"]}"/>', header(14, 48, lang, 14)]
    o.append(plan_svg(P, lang, L))
    o.append(compass(pf[0] + pf[2] - 40, pf[1] + 56, 20))
    o.append(section_svg(12, sec_y, W_ - 24, sec_h, lang, L))
    k, ky = key_svg(14, key_y, W_ - 28, lang, L)
    o.append(k)
    lg, ly = legend_svg(14, ky + 30, W_ - 28, lang, L, cols=2)
    o.append(lg)
    o.append(route_card(14, ly + 20, W_ - 28, lang, L))
    H_ = int(ly + 20 + 16 * .9 * 1.5 * (len(next(r for r in WORLD["routes"] if r["id"] == "route.first_journey")["zones"]) + 2.2) + 24)
    head = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W_} {H_}" width="{W_}" height="{H_}" role="img" aria-label="DEEPKIN {e(tr("title", lang))}">'
    return head + "".join(o) + "</svg>", (W_, H_)


def write_all():
    """Escribe assets/img/world/atlas_<lang>.svg y atlas_<lang>_m.svg; devuelve {lang: {"wide": (w, h), "tall": (w, h)}}."""
    out = {}
    d = os.path.join(ROOT, "assets", "img", "world")
    os.makedirs(d, exist_ok=True)
    for lang in ("en", "es"):
        sw, size_w = wide(lang)
        st, size_t = tall(lang)
        open(os.path.join(d, f"atlas_{lang}.svg"), "w").write(sw)
        open(os.path.join(d, f"atlas_{lang}_m.svg"), "w").write(st)
        out[lang] = {"wide": size_w, "tall": size_t}
    return out


if __name__ == "__main__":
    print(write_all())
