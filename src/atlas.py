# Atlas del mundo (pagina Mundo, 2026-10-11): imagen ilustrada generada de data/world/world_map.json y de las
# transiciones reales de data/starting_region.json. Dos laminas SVG por idioma: la ancha (escritorio) y una alta para
# telefono. Planta de la region jugable (superficie y subsuelo), corte de profundidades (el nivel de cada mapa es su piso
# en la pila, no una banda de metros; 2026-10-13), cada pasaje numerado con su tipo real (tunel, elevador de varias
# paradas, elevador, escaleras, camino, puerta) y su cartel del juego, la ruta
# recomendada Outpost -> Dustline y la bajada a The Cinder Deep. Lo planeado va desvaido como "sin cartografiar".
# No se toca el grafo del juego: las posiciones de etiquetas son de esta lamina.
import html
import json
import math
import os

from i18n import L
import worldmap as WMAP

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
TYPE_COLOR = {"tunnel": "#6fb3ac", "elevator": "#d39a4b", "lift": "#d39a4b", "stairs": "#e2c88f", "road": "#c6c0b0", "gate": "#d9614f"}

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
    "l_level": L("Level · floor in its stack", "Nivel · piso en su pila"),
    "route": L("RECOMMENDED ROUTE · OUTPOST → DUSTLINE", "RUTA RECOMENDADA · OUTPOST → DUSTLINE"),
    "route_short": L("Recommended route", "Ruta recomendada"),
    "cinder_route": L("To the Cinder Deep", "Hacia The Cinder Deep"),
    "c3_route": L("Into C-3", "Hacia C-3"),
    "start": L("START", "INICIO"), "first_city": L("FIRST CITY", "PRIMERA CIUDAD"),
    "locked": L("LOCKED · drill the Deep Seal", "CERRADO · perforá el Sello Profundo"),
    "one_way": L("one way", "sólo ida"),
    "t_tunnel": L("Tunnel", "Túnel"), "t_elevator": L("Elevator", "Elevador"), "t_lift": L("Lift", "Elevador"), "t_stairs": L("Stairs", "Escaleras"),
    "t_road": L("Road", "Camino"), "t_gate": L("Gate", "Puerta"),
    "down": L("down", "baja"), "up": L("up", "sube"),
    "i_city": L("City · safe", "Ciudad · segura"), "i_outpost": L("Outpost · start", "Outpost · inicio"),
    "i_hunt": L("Hunting ground", "Coto de caza"), "i_dungeon": L("Dungeon floor", "Piso de mazmorra"),
    "i_route": L("Road map", "Mapa de ruta"), "i_cave": L("Cavern", "Caverna"),
    "i_fuel": L("Gas station", "Estación de servicio"), "i_bank": L("Bank & depot terminal", "Terminal de banco y depósito"),
    "i_hub": L("Respawn hub", "Punto de reaparición"),
    "l_surface": L("Surface map", "Mapa de superficie"), "l_under": L("Underground map", "Mapa subterráneo"),
    "l_stack": L("Level stacked below", "Nivel apilado debajo"), "l_planned": L("Planned · uncharted", "Planeado · sin cartografiar"),
    "ride": L("bike: tunnels, elevators, gates ✓ · stairs ✕", "moto: túneles, elevadores, puertas ✓ · escaleras ✕"),
    "stops": L("{n} stops", "{n} paradas"),
    "north": L("N", "N"),
    "gate_fuel": L("GATE FUEL", "GATE FUEL"),
    "bank": L("BANK", "BANCO"),
    # 2026-10-23
    "floors": L("{n} FLOORS", "{n} PISOS"),
    "i_shop": L("Traders ×{n}", "Comerciantes ×{n}"), "i_bike": L("Bike shop · crane", "Taller de motos · grúa"),
    "i_vdi": L("VDI post", "Puesto VDI"), "i_house": L("Your house (Unit 7)", "Tu casa (Unit 7)"),
    "i_excavation": L("VDI excavation site", "Claro de excavación VDI"),
    "bore": L("VDI BORE", "PERFORACIÓN VDI"),
    "bore_sub": L("PLAYER-MADE", "LA HACE UN JUGADOR"),
    "bore_note": L("Excavation floors are player-made: a VDI drillship called out on open surface ground bores −1 … −15, generated per call-out — not fixed zones.",
                   "Los pisos de excavación los hace un jugador: una perforadora VDI llamada en terreno abierto de superficie baja de −1 a −15, generados en cada llamada; no son zonas fijas."),
    "l_bore": L("VDI excavation · player-made, generated per call-out", "Excavación VDI · la hace un jugador, se genera en cada llamada"),
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


def zlevel(zid):
    z = ZONES[zid]
    return z.get("level", 0 if z["layer"] == "surface" else -1)


# Elevadores de varias paradas (2026-10-13): pisos del dato de la region, de arriba hacia abajo, y sus conexiones del grafo.
ELEVATORS = {}
for _el in REGION.get("elevators", []):
    _cs = [c for c in WORLD["connections"] if c.get("elevator") == _el["id"]]
    if _cs:
        ELEVATORS[_el["id"]] = dict(_el, floors=sorted(_el["floors"], key=lambda f: -zlevel(f["zone"])), conns=_cs,
                                    status="playable" if all(c["status"] == "playable" for c in _cs) else "planned")


def passages():
    """Pasajes jugables numerados en orden de viaje: [(n, conn_id, a, b, type_a_to_b, type_b_to_a, sign_a, sign_b, extra)].
    Un elevador de varias paradas es un solo pasaje (id del elevador) con sus pisos en "floors"."""
    order = ["elevator.shaft3", "conn.scarp_saltpan_ne", "conn.scarp_saltpan_sw",
             "conn.saltpan_frontier_east", "conn.frontier_east_dustline", "conn.frontier_east_dragon_lair", "conn.threshold_shallows",
             "conn.shallows_c3", "conn.c3_f2", "conn.c3_f2_f3"]
    conns = {c["id"]: c for c in WORLD["connections"] if c["kind"] != "elevator"}
    out = []
    for cid in order + [c["id"] for c in WORLD["connections"] if c["status"] == "playable" and c["id"] not in order and c["kind"] != "elevator"] \
            + [k for k in ELEVATORS if k not in order]:
        el = ELEVATORS.get(cid)
        if el:
            if el["status"] != "playable":
                continue
            fl = el["floors"]
            out.append({"n": len(out) + 1, "id": cid, "a": fl[0]["zone"], "b": fl[-1]["zone"], "floors": [f["zone"] for f in fl],
                        "ta": "elevator", "tb": "elevator", "sa": el["label"], "sb": " / ".join(f["label"] for f in fl),
                        "locked": False, "kind": "elevator", "exit_at": None, "conns": [c["id"] for c in el["conns"]]})
            continue
        c = conns.get(cid)
        if not c or c["status"] != "playable":
            continue
        a, b = c["ends"]
        ta, tb = pres_of(a.get("transition")), pres_of(b.get("transition"))
        if c["kind"] == "road" and (ta == "tunnel" or tb == "tunnel"):
            ta = tb = "tunnel"
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
for _p in PASS:
    for _cid in _p.get("conns", []):
        PASS_BY[_cid] = _p


# Pilas de pisos (2026-10-23): las guaridas de cuatro pisos (Castoff Hideout, The Pump Works) van en la planta como una
# sola placa con su cantidad de pisos; el corte y la clave muestran cada piso. Un grupo = mismos padre y prefijo del
# nombre, 3 pisos o mas (C-3 F2/F3 siguen con placa propia).
def _stack_groups():
    by = {}
    for z in WORLD["zones"]:
        if z.get("stack") and z["status"] == "playable":
            by.setdefault((z["stack"]["parent"], z["name"].split(" · ")[0]), []).append(z["id"])
    out = {}
    for (_, prefix), ids in by.items():
        if len(ids) >= 3:
            ids = sorted(ids, key=lambda i: ZONES[i]["stack"]["depth"])
            for i in ids:
                out[i] = {"head": ids[0], "floors": ids, "name": prefix}
    return out


GROUP = _stack_groups()


def same_group(a, b):
    return a in GROUP and b in GROUP and GROUP[a]["head"] == GROUP[b]["head"]


SITES = WMAP.sites(REGION)


# --- Glifos (24x24, trazo) --------------------------------------------------------------------------------------
GLYPH = {
    "tunnel": '<path d="M4 20V11a8 8 0 0 1 16 0v9"/><path d="M9 20l1-6h4l1 6M8 17h8"/>',
    "elevator": '<rect x="5" y="2" width="14" height="20" rx="1.5"/><path d="M9 9.5l3-3 3 3M9 14.5l3 3 3-3"/>',
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
    # Fases 3-7 (2026-10-23): tiendas, taller de motos, puesto VDI, casa, excavacion VDI (perforadora llamada por un jugador).
    "shop": '<path d="M3 9h18l-2-5H5ZM3 9c0 2 4 2 4.5 0 .5 2 4.5 2 4.5 0 0 2 4 2 4.5 0 .5 2 4.5 2 4.5 0M5 11v9h14v-9M10 20v-5h4v5"/>',
    "bike": '<circle cx="5.5" cy="16" r="3.5"/><circle cx="18.5" cy="16" r="3.5"/><path d="M5.5 16 9 9h6l3.5 7M9 9 7.5 6H5M15 9l-1.5-3h3M12 16l3-7"/>',
    "vdi": '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
    "house": '<path d="M3 11 12 4l9 7M5 9.5V20h14V9.5M10 20v-6h4v6"/>',
    "excavation": '<rect x="6.5" y="2" width="11" height="12" rx="2"/><path d="M6.5 6h11M6.5 10h11M9 14l3 8 3-8M10.5 17h3"/>',
}
ZONE_ICON = {"zone.dustline": "city", "zone.outpost": "outpost", "zone.surface_scarp": "hunt", "zone.surface_saltpan": "route",
             "zone.frontier_road_east": "route", "zone.shallows": "hunt", "zone.threshold": "cave", "zone.excavation_c3": "dungeon",
             "zone.excavation_c3_f2": "dungeon", "zone.excavation_c3_f3": "dungeon", "zone.dragon_lair": "hunt"}
# Mapas nuevos (2026-10-23): el icono sale del tipo de mapa del dato.
KIND_GLYPH = {"city": "city", "settlement": "city", "outpost": "outpost", "wild": "hunt", "dungeon": "dungeon", "route": "route"}


def zone_icon(zid):
    return ZONE_ICON.get(zid) or KIND_GLYPH.get(ZONES[zid]["kind"], "cave")


def hunting(zid):
    """Coto de caza (2026-10-23): un bloque "hunting" en el mapa, o un mapa salvaje / "hunting spot" con grupos de aparicion."""
    return WMAP.is_hunting(ZONES[zid], REGION)


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
        self.used_h = (max(ys) - min(ys)) * self.k  # alto que ocupa la ventana en el marco
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
    if zid in GROUP and GROUP[zid]["head"] != zid:
        zid = GROUP[zid]["head"]
    if zid in layout["pos"]:
        return layout["pos"][zid]
    z = ZONES[zid]
    return z.get("stack", {}).get("marker") or z.get("marker") or z["cell"]["seed"]


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
    if p["kind"] == "elevator":
        # Un solo pozo: cada piso baja a su anclaje en el punto del pozo; la insignia va en el pozo.
        sx, sy = P.p(layout["elevator_at"][p["id"]])
        d = "".join("M%.1f,%.1fL%.1f,%.1f" % (*P.p(anchor_uv(z, layout)), sx, sy) for z in p["floors"])
        return d, sx, sy
    via = layout["via"].get(p["id"], p.get("exit_at"))
    return curve(P, p["a"], p["b"], layout, via)


def conn_geom(P, cid, layout):
    """Tramo de una conexion del grafo: si es de un elevador, de un piso al pozo y del pozo al otro piso."""
    p = PASS_BY.get(cid)
    if not p:
        return None
    if p["kind"] != "elevator":
        return passage_geom(P, p, layout)[0]
    c = next(c for c in WORLD["connections"] if c["id"] == cid)
    (ax, ay), (bx, by) = (P.p(anchor_uv(x["zone"], layout)) for x in c["ends"])
    sx, sy = P.p(layout["elevator_at"][p["id"]])
    return f"M{ax:.1f},{ay:.1f}L{sx:.1f},{sy:.1f}L{bx:.1f},{by:.1f}"


def stroke_for(p):
    t = p["ta"]
    col = TYPE_COLOR.get(t, C["soft"])
    if t == "road" or t == "gate":
        return f'stroke="{col}" stroke-width="3.2" stroke-opacity=".85"'
    if t == "tunnel":
        return f'stroke="{col}" stroke-width="2.6" stroke-dasharray="9 3"'
    if t == "elevator":
        return f'stroke="{col}" stroke-width="2.4" stroke-dasharray="1 4" stroke-linecap="round"'
    return f'stroke="{col}" stroke-width="2" stroke-dasharray="2 4" stroke-linecap="round"'


def passage_lines(P, lang, layout):
    o = []
    for p in PASS:
        if same_group(p["a"], p["b"]):
            continue
        d, _, _ = passage_geom(P, p, layout)
        if p["ta"] in ("road", "gate"):
            o.append(f'<path d="{d}" fill="none" stroke="#0b0d0c" stroke-width="6.5"/>')
        o.append(f'<path d="{d}" fill="none" {stroke_for(p)}/>')
        if p["kind"] == "elevator":
            # Boca del pozo: doble anillo en el punto del elevador.
            _, sx, sy = passage_geom(P, p, layout)
            r = layout["badge_r"] * 2.2
            o.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{r:.1f}" fill="{C["bg"]}" stroke="{TYPE_COLOR["elevator"]}" stroke-width="1.2" stroke-opacity=".7"/>'
                     f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{r * .78:.1f}" fill="none" stroke="{TYPE_COLOR["elevator"]}" stroke-width="1" stroke-dasharray="2 3"/>')
    return "".join(o)


def passage_badges(P, layout):
    o = []
    r = layout["badge_r"]
    for p in PASS:
        if same_group(p["a"], p["b"]) or (p.get("one_way") and p["a"] in GROUP):
            continue  # escaleras entre pisos de una guarida y su salida de un solo sentido: en el corte y en la clave
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
    segs = [d for d in (conn_geom(P, cid, layout) for cid in j["connections"]) if d]
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
    """Niveles apilados: una placa con su sombra en el punto del dato (el marcador apilado), unida al mapa padre. Los pisos
    que el dato pone en el mismo punto (pozo de Shaft 3: Outpost y Threshold; C-3 F2/F3; una guarida) son una sola pila de
    placas, una sombra por piso (2026-10-24: ninguna placa se corre a mano)."""
    o = []
    piles = {}
    for z in WORLD["zones"]:
        if not z.get("stack") or z["status"] != "playable":
            continue
        if z["id"] in GROUP and GROUP[z["id"]]["head"] != z["id"]:
            continue
        u, v = anchor_uv(z["id"], layout)
        piles.setdefault((round(u, 3), round(v, 3)), []).append(z["id"])
    for (u, v), ids in piles.items():
        ids.sort(key=lambda i: ZONES[i].get("depth_m", 0))
        x, y = P.p((u, v))
        for zid in ids:
            px, py = P.p(anchor_uv(ZONES[zid]["stack"]["parent"], layout))
            if math.hypot(px - x, py - y) > 2:
                o.append(f'<path d="M{px:.1f},{py:.1f}L{x:.1f},{y:.1f}" stroke="#7b8fb8" stroke-width="1" stroke-dasharray="3 3"/>')
        s = layout["plate"]
        nf = sum(len(GROUP[i]["floors"]) if i in GROUP else 1 for i in ids)
        nf = max(nf, 2)
        for k_, op in [(i, .35 + .5 * (nf - i) / nf) for i in range(nf, 0, -1)]:
            o.append(f'<rect x="{x - s + k_ * 3:.1f}" y="{y - s * .7 + k_ * 3:.1f}" width="{2 * s}" height="{1.4 * s}" rx="2" fill="{C["cave"]}" stroke="#7b8fb8" stroke-opacity="{op * .5}"/>')
        o.append(f'<rect x="{x - s:.1f}" y="{y - s * .7:.1f}" width="{2 * s}" height="{1.4 * s}" rx="2" fill="{C["cave2"]}" stroke="#9fb3d8" stroke-width="1.3"/>')
        o.append(glyph(zone_icon(ids[0]), x, y, s * 1.05, "#cfdcf5", 1.7, False))
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
            o.append(glyph(zone_icon(zid), x, y, r * 1.15, col, 1.8, False))
        lab = layout["labels"].get(zid)
        if not lab:
            continue
        lx, ly, anc = x + lab[0], y + lab[1], lab[2]
        if len(lab) > 3 and lab[3]:  # linea guia
            o.append(f'<path d="M{x:.1f},{y:.1f}L{lx:.1f},{ly - layout["fs_zone"] * .35:.1f}" stroke="{C["muted"]}" stroke-width=".8"/>')
        fs = layout["fs_zone"]
        name = layout.get("plan_name", {}).get(zid, z["name"]).upper()
        col = "#cfdcf5" if under else C["text"]
        depth = z.get("depth_m", 0)
        sub = (z.get("level_label", "") + " · " if z.get("level_label") else "") + (f"−{depth} m" if depth else ("SURFACE" if lang == "en" else "SUPERFICIE"))
        if zid == "zone.excavation_c3_f2" or zid == "zone.excavation_c3_f3":
            sub = z["subtitle"][lang].upper() + " · −" + str(depth) + " m"
        if zid in GROUP:
            fl = GROUP[zid]["floors"]
            name = GROUP[zid]["name"].upper()
            sub = tr("floors", lang).format(n=len(fl)) + f" · −{ZONES[fl[0]]['depth_m']}…{ZONES[fl[-1]]['depth_m']} m"
        elif z.get("stack") and z.get("subtitle") and not z.get("level_label") and zid not in ("zone.dragon_lair", "zone.threshold"):
            sub = f"−{depth} m"
        parts = name.split("\n")
        for i_, part in enumerate(parts):
            o.append(text(lx, ly + i_ * fs * 1.1, part, fs, col, anc, 600, MONO, .07))
        ly += (len(parts) - 1) * fs * 1.1
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
        # GATE FUEL (2026-10-12): al oeste de la ruta donde dobla al norte hacia la puerta de Dustline, antes de la puerta.
        x, y = P.p(layout["fuel_at"])
        o.append(glyph("fuel", x, y, sz, C["danger"], 1.8, True))
        lab = layout["fuel_label"]
        o.append(text(x + lab[0], y + lab[1], st["name"], layout["fs_zone"] * .72, C["danger"], lab[2], 600, MONO, .1))
    # Lugares del dato (2026-10-23): fila de iconos junto a su mapa (tiendas con su cantidad, motos, VDI, casa) y el claro de
    # excavaciones VDI; el coto de caza es una marca chica junto al mapa.
    for zid, (ox, oy) in layout.get("site_off", {}).items():
        kinds = []
        for k in ("house", "shop", "bike", "vdi", "excavation"):
            n_ = sum(1 for st in SITES if st["zone"] == zid and st["kind"] == k)
            if n_:
                kinds.append((k, n_))
        x, y = P.p(anchor_uv(zid, layout))
        x, y = x + ox, y + oy
        for i, (k, n_) in enumerate(kinds):
            gx = x + i * sz * 1.75
            o.append(glyph(k, gx, y, sz, SITE_COLOR[k], 1.7, True))
            if n_ > 1:
                o.append(badge(n_, gx + sz * .62, y - sz * .62, sz * .42, SITE_COLOR[k], sz * .5))
    for zid in [z["id"] for z in WORLD["zones"] if z["status"] == "playable" and hunting(z["id"])]:
        ox, oy = layout.get("hunt_off", {}).get(zid, (layout["mark_r"] * 1.15, layout["mark_r"] * 1.05))
        x, y = P.p(anchor_uv(zid, layout))
        if zone_icon(zid) == "hunt" and zid not in layout.get("hunt_off", {}):
            continue  # el propio icono del mapa ya es la mira
        o.append(glyph("hunt", x + ox, y + oy, sz * .8, C["danger"], 1.8, True))
    return "".join(o)


SITE_COLOR = {"shop": "#e2c88f", "bike": "#6fb3ac", "vdi": "#d39a4b", "house": "#00ff41", "excavation": "#d39a4b"}


# --- Corte de profundidades ----------------------------------------------------------------------------------------
# Columnas del corte (2026-10-12): de oeste a este como en la planta; el pozo del elevador Shaft 3 entre el Outpost y la
# columna Scarp/Threshold (2026-10-13); The Cinder Deep cuelga del acantilado oeste de
# Frontier Road (entre la Saltpan y la ruta), The Shallows va a la derecha porque solo la unen tuneles a −120 m.
# 2026-10-23: entran The Sump con The Pump Works debajo, la guarida Castoff bajo Frontier Road, The Floodlands con The
# Drowned Cellar y, a la derecha, la perforacion VDI (pisos hechos por jugadores, no zonas fijas). The Shallows pasa a la
# columna de C-3 (sus tuneles a −120/−140 m), The Cinder Deep cuelga debajo de Frontier Road.
# 2026-10-24: The Outpost esta apilado bajo la Scarp (pozo de Shaft 3): Scarp, Outpost y Threshold son una sola columna
# con el pozo del elevador al costado.
SEC_X = {"zone.outpost": .20, "elevator.shaft3": .125, "zone.surface_scarp": .20, "zone.threshold": .20, "zone.surface_saltpan": .36, "zone.shallows": .36,
         "zone.excavation_c3": .36, "zone.excavation_c3_f2": .36, "zone.excavation_c3_f3": .36,
         "zone.the_sump": .51, "zone.robot_hideout_f1": .51, "zone.robot_hideout_f2": .51, "zone.robot_hideout_f3": .51, "zone.robot_hideout_f4": .51,
         "zone.frontier_road_east": .67, "zone.dragon_lair": .685,
         "zone.castoff_hideout_f1": .775, "zone.castoff_hideout_f2": .775, "zone.castoff_hideout_f3": .775, "zone.castoff_hideout_f4": .775,
         "zone.dustline": .83, "zone.floodlands": .96, "zone.floodlands_cellar": .96, "bore": .905}


def section_svg(x0, y0, w, h, lang, L, live=False):
    """Corte de profundidades. Con live=True (SVG en linea de la pagina) cada placa es un grupo enfocable con data-zone y
    cada pasaje un grupo con data-a/data-b, para que el JS los resalte junto con el mapa interactivo."""
    o = []
    SX = L.get("sec_x", SEC_X)
    top = y0 + L["sec_top"]
    bottom = y0 + h - 18

    def Y(d):
        k1 = L["sec_k1"]
        if d <= 150:
            return top + d * k1
        return top + 150 * k1 + (d - 150) * (bottom - top - 150 * k1) / (560 - 150)

    def X(zid):
        return x0 + 26 + SX[zid] * (w - 52)
    o.append(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="{C["panel"]}"/>')
    o.append(f'<rect x="{x0}" y="{y0 + 4}" width="{w}" height="{top - y0 - 4}" fill="url(#sky)"/>')
    o.append(f'<rect x="{x0}" y="{top:.1f}" width="{w}" height="{bottom - top + 18:.1f}" fill="url(#earth)"/>')
    # Guias de profundidad (el nivel de cada mapa va en su placa: es el piso en su pila, no una banda de metros)
    fsb = L["fs_band"]
    for d0 in (0, 200, 400):
        yb = Y(d0)
        o.append(f'<path d="M{x0},{yb:.1f}h{w}" stroke="{C["amber"] if d0 == 0 else C["line2"]}" stroke-width="{1.6 if d0 == 0 else 1}"'
                 f'{"" if d0 == 0 else " stroke-dasharray=" + chr(34) + "6 5" + chr(34)}/>')
    o.append(text(x0 + 46, top - L["node_h"] / 2 - 8, tr("surface", lang), fsb, C["amber"], "start", 600, MONO, .12, False))
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
    for zid in (k for k in SX if k in ZONES):
        z = ZONES[zid]
        nodes[zid] = (X(zid), Y(z.get("depth_m", 0)))
    # Pisos poco profundos en la misma columna (la guarida a −15 m, el sotano a −12 m): se empujan hacia abajo hasta no
    # pisarse; la placa sigue diciendo su profundidad real.
    nh = L["node_h"]
    # Superficie escalonada (2026-10-23): seis mapas de superficie no entran en una fila; los de "sec_lift" suben un renglon.
    for zid in L.get("sec_lift", ()):
        if zid in nodes:
            nodes[zid] = (nodes[zid][0], nodes[zid][1] - nh - 6)
    cols = {}
    for zid, (x, y) in nodes.items():
        cols.setdefault(round(x), []).append(zid)
    for ids in cols.values():
        ids.sort(key=lambda i: nodes[i][1])
        for a, b in zip(ids, ids[1:]):
            if nodes[b][1] < nodes[a][1] + nh + 6:
                nodes[b] = (nodes[b][0], nodes[a][1] + nh + 6)
    # Perforacion VDI (2026-10-23): un pozo fantasma con pisos −1 … −15, sin zona fija.
    if "bore" in SX:
        o.append(bore_svg(X("bore"), Y(165), Y(540), lang, L))
    # Conexiones
    for p in PASS:
        a, b = p["a"], p["b"]
        if p["kind"] == "elevator":
            # Elevador de varias paradas: un pozo vertical (dos rieles) con un rellano hacia cada piso que sirve. Un grupo por
            # tramo del grafo (data-a/data-b) para que el resaltado del mapa encienda solo lo que toca a la zona elegida.
            if not all(z in nodes for z in p["floors"]):
                continue
            col = TYPE_COLOR["elevator"]
            sx = X_of(L, p["id"], x0, w)
            for cid in p["conns"]:
                c = next(c for c in WORLD["connections"] if c["id"] == cid)
                za, zb = (x["zone"] for x in c["ends"])
                (ax, ay), (bx, by) = nodes[za], nodes[zb]
                o.append(f'<g class="at-pass" data-conn="{e(cid)}" data-a="{za}" data-b="{zb}">'
                         f'<path d="M{sx - 3:.1f},{ay:.1f}V{by:.1f}M{sx + 3:.1f},{ay:.1f}V{by:.1f}" stroke="{col}" stroke-width="1.6"/>'
                         f'<path d="M{ax:.1f},{ay:.1f}H{sx:.1f}M{bx:.1f},{by:.1f}H{sx:.1f}" stroke="{col}" stroke-width="2" stroke-dasharray="2 4" stroke-linecap="round"/></g>')
            for z in p["floors"]:
                o.append(f'<rect x="{sx - 6:.1f}" y="{nodes[z][1] - 4:.1f}" width="12" height="8" rx="1.5" fill="{C["bg"]}" stroke="{col}" stroke-width="1.4"/>')
            ys = [nodes[z][1] for z in p["floors"]]
            p["_sec"] = (sx, (min(ys) + sorted(ys)[1]) / 2 if len(ys) > 2 else sum(ys) / len(ys))
            continue
        if a not in nodes or b not in nodes:
            continue
        (ax, ay), (bx, by) = nodes[a], nodes[b]
        col = TYPE_COLOR.get(p["ta"], C["soft"])
        off = L["sec_off"].get(p["id"], 0)
        o.append(f'<g class="at-pass" data-conn="{e(p["id"])}" data-a="{a}" data-b="{b}">')
        if p.get("one_way"):
            ax += L.get("sec_oneway_dx", {}).get(p["id"], 34)
            bx = ax  # sube derecho hasta el nivel de llegada
            o.append(f'<path d="M{ax:.1f},{ay:.1f}L{bx:.1f},{by:.1f}" stroke="{col}" stroke-width="1.8" stroke-dasharray="2 4" stroke-linecap="round"/>')
            o.append(f'<path d="M{bx - 6:.1f},{by + 12:.1f}L{bx:.1f},{by + 2:.1f}L{bx + 6:.1f},{by + 12:.1f}" fill="none" stroke="{col}" stroke-width="2"/>')
        else:
            if abs(ay - by) < 1:
                ay += off
                by += off
            else:
                ax += off
                bx += off
            dash = "" if p["ta"] in ("road", "gate") else (' stroke-dasharray="9 3"' if p["ta"] == "tunnel" else ' stroke-dasharray="2 4" stroke-linecap="round"')
            o.append(f'<path d="M{ax:.1f},{ay:.1f}L{bx:.1f},{by:.1f}" stroke="{col}" stroke-width="{2.6 if p["ta"] in ("road", "gate") else 2}"{dash}/>')
        o.append("</g>")
        p["_sec"] = ((ax + bx) / 2, (ay + by) / 2)
    # Ruta recomendada en el corte
    j = next(r for r in WORLD["routes"] if r["id"] == "route.first_journey")
    pts = []
    for i, zid in enumerate(j["zones"]):
        if zid not in nodes:
            continue
        p = PASS_BY.get(j["connections"][i - 1]) if 0 < i <= len(j["connections"]) else None
        if p and p["kind"] == "elevator" and pts:
            # Por el pozo: rellano del piso de salida, pozo, rellano del de llegada.
            sx = X_of(L, p["id"], x0, w)
            pts += [(sx, pts[-1][1]), (sx, nodes[zid][1])]
        pts.append(nodes[zid])
    rp = " ".join("%.1f,%.1f" % q for q in pts)
    o.append(f'<polyline points="{rp}" fill="none" stroke="{C["amber"]}" stroke-width="9" stroke-opacity=".22" filter="url(#glow)"/>')
    # Nodos
    nw, nh, fs = L["node_w"], L["node_h"], L["fs_node"]
    for zid, (x, y) in nodes.items():
        z = ZONES[zid]
        under = z["layer"] == "underground"
        col = "#9fb3d8" if under else C["warm"]
        ww = max(nw, tw(L["short"].get(zid, z["name"].replace("The ", "")).upper(), fs, .04) + 12)
        sub = (z.get("level_label") + " · " if z.get("level_label") else "") + (f"−{z['depth_m']} m" if z.get("depth_m") else "0 m")
        lv = zlevel(zid)
        if tw(sub, fs * .78, .06) > ww - 8:  # placa angosta: solo la profundidad
            sub = f"−{z['depth_m']} m"
        extra = f' tabindex="0" role="button" aria-label="{e(z["name"])} · {e(sub)}"' if live else ""
        o.append(f'<g class="at-node{" under" if under else ""}" data-zone="{zid}"{extra}>')
        if live:
            o.append(f'<rect class="at-hit" x="{x - ww / 2 - 6:.1f}" y="{y - nh / 2 - 6:.1f}" width="{ww + 12:.1f}" height="{nh + 12}" fill="transparent"/>')
        o.append(f'<rect class="at-plate" x="{x - ww / 2:.1f}" y="{y - nh / 2:.1f}" width="{ww:.1f}" height="{nh}" rx="3" fill="{C["cave2"] if under else "#2a241a"}" stroke="{col}" stroke-width="1.4"/>')
        name = L["short"].get(zid, z["name"].replace("The ", "")).upper()
        o.append(text(x, y - 1, name, fs, C["text"], "middle", 600, MONO, .04, False, extra=' class="at-name"'))
        o.append(text(x, y + fs * 1.05, sub, fs * .78, col, "middle", 500, MONO, .06, False, extra=' class="at-depth"'))
        if lv:
            # Nivel (piso en su pila) en la esquina de la placa
            o.append(level_tag(x - ww / 2, y - nh / 2, lv, fs))
        o.append("</g>")
    # Insignias de pasajes
    r = L["badge_r"]
    for p in PASS:
        if "_sec" not in p:
            continue
        x, y = p["_sec"]
        if p["id"] in L["sec_badge"]:
            dx, dy = L["sec_badge"][p["id"]]
        elif same_group(p["a"], p["b"]):
            # Escaleras entre pisos de una guarida: la insignia a la izquierda de la columna, no entre las placas.
            dx, dy = -(max(L["node_w"], tw(L["short"].get(p["a"], zname(p["a"])).upper(), L["fs_node"], .04) + 12) / 2 + r * 2.8), 0
        else:
            dx, dy = 0, 0
        x, y = x + dx, y + dy
        col = TYPE_COLOR.get(p["ta"], C["soft"])
        zs = f' data-zones="{" ".join(p["floors"])}"' if p.get("floors") else ""
        o.append(f'<g class="at-badge" data-conn="{e(p["id"])}" data-a="{p["a"]}" data-b="{p["b"]}"{zs}>')
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r * 1.5:.1f}" fill="{C["bg"]}" stroke="{col}" stroke-width="1.3"/>')
        o.append(glyph(p["ta"], x - r * .55, y, r * 1.2, col, 1.7, False))
        o.append(text(x + r * .62, y + r * .4, str(p["n"]), r * 1.05, col, "middle", 600, MONO, 0, False))
        if p["locked"]:
            o.append(text(x, y + r * 3, "■ " + tr("locked", lang), r * .95, C["danger"], "middle", 500, MONO, .02))
        if p.get("one_way"):
            o.append(text(x + r * 1.9, y + r * .4, "↑ " + tr("one_way", lang), r * .95, C["amber"], "start", 500, MONO, .02))
        o.append("</g>")
    o.append(frame(x0, y0, w, h, tr("section", lang), L, grid=False))
    return "".join(o)


def bore_svg(x, y0, y1, lang, L):
    """Pozo de una excavacion VDI: carcasa punteada, pisos genericos y la nota "lo hace un jugador"."""
    fs = L["fs_node"]
    col = C["amber"]
    o = [f'<g class="at-bore" opacity=".85">',
         f'<path d="M{x - 9:.1f},{y0:.1f}V{y1:.1f}M{x + 9:.1f},{y0:.1f}V{y1:.1f}" stroke="{col}" stroke-width="1.2" stroke-dasharray="5 4" fill="none"/>']
    n = 6
    for i in range(n):
        yy = y0 + 26 + (y1 - y0 - 40) * i / (n - 1)
        lab = "−15" if i == n - 1 else ("…" if i == n - 2 else f"−{i + 1}")
        o.append(f'<rect x="{x - 15:.1f}" y="{yy - 5:.1f}" width="30" height="10" rx="2" fill="{C["bg"]}" stroke="{col}" stroke-width="1" stroke-dasharray="2 2"/>')
        o.append(text(x, yy + fs * .3, lab, fs * .72, col, "middle", 600, MONO, 0, False))
    o.append(glyph("excavation", x, y0 - fs * 3.2, fs * 1.3, col, 1.7, True))
    o.append(text(x, y0 - fs * 1.2, tr("bore", lang), fs * .8, col, "middle", 600, MONO, .06))
    o.append(text(x, y0 - fs * .1, tr("bore_sub", lang), fs * .66, C["soft"], "middle", 500, MONO, .06))
    o.append("</g>")
    return "".join(o)


def X_of(L, key, x0, w):
    """Columna del corte de un pozo (elevador) o de una zona."""
    return x0 + 26 + L.get("sec_x", SEC_X)[key] * (w - 52)


def level_tag(x, y, lv, fs):
    r = fs * .62
    s = str(lv).replace("-", "−")
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{C["bg"]}" stroke="#9fb3d8" stroke-width="1"/>'
            f'<text x="{x:.1f}" y="{y + r * .38:.1f}" font-family="{MONO}" font-size="{r * 1.02:.1f}" font-weight="600" fill="#cfdcf5" text-anchor="middle">{s}</text>')


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
        elif p["kind"] == "elevator":
            kind = tr("t_elevator", lang) + " · " + tr("stops", lang).format(n=len(p["floors"]))
        elif p["ta"] == p["tb"]:
            kind = tr("t_" + p["ta"], lang)
        elif ZONES[p["b"]].get("depth_m", 0) == ZONES[p["a"]].get("depth_m", 0):
            kind = f'{tr("t_" + p["ta"], lang)} → · {tr("t_" + p["tb"], lang).lower()} ←'
        else:
            dn = ZONES[p["b"]].get("depth_m", 0) > ZONES[p["a"]].get("depth_m", 0)
            kind = f'{tr("t_" + p["ta"], lang)} ({tr("down" if dn else "up", lang)}) · {tr("t_" + p["tb"], lang).lower()} ({tr("up" if dn else "down", lang)})'
        head = f'{L["short"].get(p["a"], zname(p["a"]).replace("The ", ""))} {"→" if p.get("one_way") else "⇄"} {L["short"].get(p["b"], zname(p["b"]).replace("The ", ""))}'
        if p.get("floors"):
            head = " · ".join(L["short"].get(z, zname(z).replace("The ", "")) for z in p["floors"])
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
             ("hub", C["green"], "i_hub"), ("house", SITE_COLOR["house"], "i_house"), ("shop", SITE_COLOR["shop"], "i_shop"),
             ("bike", SITE_COLOR["bike"], "i_bike"), ("vdi", SITE_COLOR["vdi"], "i_vdi"), ("excavation", SITE_COLOR["excavation"], "i_excavation")]
    n_shops = sum(1 for st in SITES if st["kind"] == "shop" and st["zone"] == "zone.dustline")
    lines = [("road", "t_road"), ("tunnel", "t_tunnel"), ("elevator", "t_elevator"), ("lift", "t_lift"), ("stairs", "t_stairs"), ("gate", "t_gate")]
    o = [text(x0, y0, tr("legend", lang), L["fs_title"], C["amber"], "start", 600, MONO, .14, False)]
    y = y0 + L["fs_title"] * 1.4
    colw = w / cols
    lh = fs * 1.9
    for i, (g_, col, key) in enumerate(items):
        cx = x0 + (i % cols) * colw
        cy = y + (i // cols) * lh
        o.append(glyph(g_, cx + fs * .8, cy, fs * 1.15, col, 1.8, True))
        o.append(text(cx + fs * 2.1, cy + fs * .36, tr(key, lang).format(n=n_shops), fs, C["soft"], "start", 400, MONO, .02, False))
    y += math.ceil(len(items) / cols) * lh + fs * .4
    for i, (k, key) in enumerate(lines):
        cx = x0 + (i % cols) * colw
        cy = y + (i // cols) * lh
        p = {"ta": k}
        o.append(f'<path d="M{cx:.1f},{cy:.1f}h{fs * 2.6:.1f}" fill="none" {stroke_for(p)}/>')
        o.append(text(cx + fs * 3.2, cy + fs * .36, tr(key, lang), fs, TYPE_COLOR[k], "start", 500, MONO, .02, False))
    y += math.ceil(len(lines) / cols) * lh + fs * .4
    extra = [("surf", "l_surface"), ("under", "l_under"), ("stack", "l_stack"), ("lvl", "l_level"), ("plan", "l_planned"), ("route", "route_short"), ("cinder", "cinder_route"),
             ("bore", "l_bore")]
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
        elif k == "lvl":
            sw = level_tag(cx + fs * 1.3, cy, -2, fs * 1.2)
        elif k == "plan":
            sw = f'<rect x="{cx:.1f}" y="{cy - fs * .6:.1f}" width="{fs * 2.6:.1f}" height="{fs * 1.2:.1f}" fill="url(#hatch)" stroke="#3a3f3a" stroke-dasharray="4 4"/>'
        elif k == "bore":
            sw = (f'<path d="M{cx + fs * .9:.1f},{cy - fs * .7:.1f}v{fs * 1.4:.1f}M{cx + fs * 1.7:.1f},{cy - fs * .7:.1f}v{fs * 1.4:.1f}" stroke="{C["amber"]}" stroke-width="1.2" stroke-dasharray="3 2"/>'
                  f'<rect x="{cx + fs * .55:.1f}" y="{cy - fs * .25:.1f}" width="{fs * 1.5:.1f}" height="{fs * .5:.1f}" rx="1" fill="{C["bg"]}" stroke="{C["amber"]}" stroke-dasharray="2 2"/>')
        elif k == "route":
            sw = f'<path d="M{cx:.1f},{cy:.1f}h{fs * 2.6:.1f}" stroke="{C["amber"]}" stroke-width="7" stroke-opacity=".3"/><path d="M{cx:.1f},{cy:.1f}h{fs * 2.6:.1f}" stroke="{C["amber"]}" stroke-width="2.2"/>'
        else:
            sw = f'<path d="M{cx:.1f},{cy:.1f}h{fs * 2.6:.1f}" stroke="{C["danger"]}" stroke-width="2" stroke-dasharray="6 4"/>'
        o.append(sw)
        o.append(text(cx + fs * 3.2, cy + fs * .36, tr(key, lang), fs, C["soft"], "start", 400, MONO, .02, False))
    y += math.ceil(len(extra) / cols) * lh
    o.append(text(x0, y + fs * .6, tr("ride", lang), fs * .9, C["muted"], "start", 400, MONO, .02, False))
    # Nota de excavaciones (2026-10-23), partida en renglones al ancho de la lamina.
    per = max(20, int(w / (fs * .9 * .64)))
    words, line, lines = tr("bore_note", lang).split(), "", []
    for wd in words:
        if len(line) + len(wd) + 1 > per:
            lines.append(line)
            line = wd
        else:
            line = (line + " " + wd).strip()
    lines.append(line)
    for i, ln in enumerate(lines):
        y += fs * 1.3
        o.append(text(x0, y + fs * .6, ln, fs * .9, C["amber"], "start", 400, MONO, .02, False))
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


# Pintura 2026-10-12: el corredor ya ocupa buena parte del arte, la lupa solo lo realza un poco.
LENS = (0.60, 0.52, 520, 1.3)


# --- Laminas ------------------------------------------------------------------------------------------------------
def common_layout():
    return {
        # The Cinder Deep usa el marcador apilado del dato (pozo de escaleras en el acantilado oeste de Frontier Road).
        # 2026-10-24: ninguna marca se corre a mano; cada mapa va en el punto del dato (marcador, marcador apilado) por la misma
        # proyeccion que el mapa interactivo. Solo las etiquetas se acomodan (con linea guia si hace falta).
        "pos": {},
        "via": {"conn.threshold_shallows": (0.445, 0.36), "conn.shallows_c3": (0.315, 0.50), "conn.frontier_east_dragon_lair": None,
                "conn.c3_f2": None, "conn.c3_f2_f3": None, "extraction.zone.excavation_c3_f3": None},
        # Pozo del elevador Shaft 3: el mismo punto que en el mapa interactivo (el castillete pintado en la Scarp).
        "elevator_at": {k: v for k, v in WMAP.VLINK_AT.items() if k.startswith("elevator.")},
        "short": {"zone.excavation_c3": "C-3 F1", "zone.excavation_c3_f2": "C-3 F2", "zone.excavation_c3_f3": "C-3 F3",
                  "zone.frontier_road_east": "Frontier Rd", "zone.dragon_lair": "Cinder Deep", "zone.surface_scarp": "Scarp",
                  "zone.surface_saltpan": "Saltpan", "zone.floodlands_cellar": "Cellar",
                  **{f"zone.robot_hideout_f{i}": f"Pump F{i}" for i in range(1, 5)},
                  **{f"zone.castoff_hideout_f{i}": f"Castoff F{i}" for i in range(1, 5)}},
        "city_at": (0.73, 0.43), "city_size": (0.085, 0.07),
        "fuel_at": (0.712, 0.484),
        "svc_off": {"zone.outpost": (-34, 42), "zone.dustline": (-50, -40)},
        "site_off": {"zone.dustline": (-4, -40), "zone.frontier_road_east": (40, -30)},
        "sec_lift": ("zone.the_sump", "zone.dustline"),
        "plan_name": {"zone.floodlands_cellar": "Drowned Cellar"},
        "sec_oneway_dx": {"extraction.zone.castoff_hideout_f4": 58},
    }


def wide(lang, layout_only=False, section=True):
    win = (0.22, 0.22, 0.97, 0.82)
    L = common_layout()
    L.update({"id": "w", "fs_zone": 15, "fs_planned": 11.5, "fs_grid": 11, "fs_title": 14, "fs_band": 11, "fs_node": 11.5, "fs_key": 12.5,
              "mark_r": 13, "plate": 15, "badge_r": 8, "step_r": 11, "svc": 13,
              "labels": {"zone.outpost": (-26, -4, "end"), "zone.shallows": (0, -34, "middle"), "zone.excavation_c3": (18, -8, "start"),
                         "zone.surface_scarp": (22, -26, "start"), "zone.surface_saltpan": (-4, 34, "middle"),
                         "zone.frontier_road_east": (26, -6, "start"), "zone.dustline": (26, 34, "start"),
                         "zone.threshold": (26, 14, "start"), "zone.dragon_lair": (-30, 32, "middle"),
                         "zone.excavation_c3_f2": (26, 4, "start"), "zone.excavation_c3_f3": (26, 38, "start"),
                         "zone.the_sump": (0, 34, "middle"), "zone.floodlands": (-20, 40, "middle"), "zone.robot_hideout_f1": (0, -34, "middle"),
                         "zone.castoff_hideout_f1": (24, 5, "start"), "zone.floodlands_cellar": (-10, -34, "middle")},
              "step_off": {"zone.outpost": (-14, -30), "zone.threshold": (14, -30), "zone.surface_scarp": (-26, -18),
                           "zone.surface_saltpan": (-26, 4), "zone.frontier_road_east": (-16, -28), "zone.dustline": (-30, -8)},
              "badge_off": {"elevator.shaft3": (0, 2.9), "conn.scarp_saltpan_ne": (1.6, -1.6),
                            "conn.scarp_saltpan_sw": (-1.4, 1.6), "conn.frontier_east_dragon_lair": (-2.6, -0.2), "conn.dustline_floodlands": (0, -1.4), "conn.sump_hideout": (-2.6, 1.0), "conn.frontier_east_castoff_hideout": (1.8, -0.6), "conn.floodlands_cellar": (3.8, 3.2),
                            "conn.c3_f2": (-3.4, -1.6), "conn.c3_f2_f3": (-3.4, 0), "extraction.zone.excavation_c3_f3": (-3.4, 4.9),
                            "conn.saltpan_frontier_east": (0, 1.8), "conn.frontier_east_dustline": (2.0, 0.4), "conn.threshold_shallows": (-1.2, 0), "conn.shallows_c3": (-1.8, 0),
                            "conn.sump_frontier_east": (-1.2, 1.4)},
              "fuel_label": (-14, 4, "end"), "svc_off": {"zone.outpost": (-40, 46), "zone.dustline": (-50, -40)},
              "sec_top": 84, "sec_k1": 4.1, "node_w": 54, "node_h": 36,
              "sec_off": {"conn.scarp_saltpan_ne": -6, "conn.scarp_saltpan_sw": 6},
              "sec_badge": {"elevator.shaft3": (0, 0), "conn.scarp_saltpan_ne": (0, -16), "conn.scarp_saltpan_sw": (0, 18), "conn.saltpan_frontier_east": (-30, 18), "conn.floodlands_cellar": (-46, -4),
                            "conn.frontier_east_dustline": (0, -16), "conn.frontier_east_dragon_lair": (-20, 0), "conn.threshold_shallows": (0, -16),
                            "conn.shallows_c3": (-58, 0), "conn.c3_f2": (-18, 0), "conn.c3_f2_f3": (-18, 0),
                            "extraction.zone.excavation_c3_f3": (0, -30)}})
    if layout_only:
        return L
    pf = (24, 150, 960, 1040)
    P = Plan(*pf, *win, lens=LENS)
    W_, H_ = 1600, 1800
    o = [DEFS, f'<rect width="{W_}" height="{H_}" fill="{C["bg"]}"/>', header(24, 56, lang, 15)]
    o.append(plan_svg(P, lang, L))
    o.append(compass(pf[0] + pf[2] - 48, pf[1] + 62, 22))
    o.append(locator(pf[0] + 26, pf[1] + pf[3] - 186, 150, lang, win, L))
    o.append(route_card(pf[0] + pf[2] - 300, pf[1] + pf[3] - 150, 280, lang, L))
    if section:
        o.append(section_svg(1010, 150, 566, 1040, lang, L))
        k, ky = key_svg(24, 1250, 1552, lang, L, cols=3)
        o.append(k)
        lg, ly = legend_svg(24, ky + 40, 1552, lang, L, cols=5)
    else:
        # Lamina para la pagina (2026-10-13): el corte vive en linea arriba, asi que la columna derecha lleva la
        # clave de pasajes y la leyenda va debajo de la planta.
        k, ky = key_svg(1010, 150, 566, lang, L, cols=1)
        o.append(k)
        lg, ly = legend_svg(24, max(ky, 1250) + 40, 1552, lang, L, cols=5)
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


def tall(lang, layout_only=False, section=True):
    W_ = 640
    # Telefono (2026-10-12): ventana mas cerrada sobre el corredor y tipos mas chicos; las etiquetas del corredor
    # Scarp-Threshold-Saltpan-Frontier-Dustline se reparten arriba/abajo para no pisarse.
    win = (0.30, 0.25, 0.955, 0.76)
    L = common_layout()
    L.update({"id": "t", "fs_zone": 14.5, "fs_planned": 11, "fs_grid": 12, "fs_title": 16, "fs_band": 12, "fs_node": 12, "fs_key": 16,
              "mark_r": 13, "plate": 14, "badge_r": 9, "step_r": 10.5, "svc": 13,
              "labels": {"zone.outpost": (-22, -2, "end", True), "zone.shallows": (-10, -35, "middle"), "zone.excavation_c3": (18, -8, "start"),
                         "zone.surface_scarp": (-20, 12, "end"), "zone.surface_saltpan": (0, 34, "middle"),
                         "zone.frontier_road_east": (30, 14, "start"), "zone.dustline": (24, 48, "start"),
                         "zone.threshold": (-26, 40, "end", True), "zone.dragon_lair": (-40, 34, "middle"),
                         "zone.excavation_c3_f2": (26, 22, "start"), "zone.excavation_c3_f3": (26, 56, "start", True),
                         "zone.the_sump": (0, 34, "middle"), "zone.floodlands": (-44, -32, "middle"), "zone.robot_hideout_f1": (-20, -30, "middle"),
                         "zone.castoff_hideout_f1": (24, 5, "start"), "zone.floodlands_cellar": (0, 32, "middle")},
              "step_off": {"zone.outpost": (20, -26), "zone.threshold": (44, -14), "zone.surface_scarp": (-6, -30),
                           "zone.surface_saltpan": (-26, 6), "zone.frontier_road_east": (20, -24), "zone.dustline": (-28, 10)},
              "badge_off": {"elevator.shaft3": (3.4, 1.4), "conn.sump_hideout": (-3.0, 2.2), "conn.dustline_floodlands": (0, 0.6), "conn.floodlands_cellar": (4.0, -2.4), "conn.scarp_saltpan_ne": (1.4, -1.8),
                            "conn.scarp_saltpan_sw": (-1.6, 1.4), "conn.frontier_east_dragon_lair": (-2.8, -0.8),
                            "conn.c3_f2": (-3.4, -2.0), "conn.c3_f2_f3": (-3.4, 0.4), "extraction.zone.excavation_c3_f3": (-3.4, 4.6),
                            "conn.saltpan_frontier_east": (0, -1.8), "conn.frontier_east_dustline": (2.4, 1.2), "conn.threshold_shallows": (-0.2, -1.2), "conn.shallows_c3": (0.6, 0),
                            "conn.sump_frontier_east": (1.4, -1.6)},
              "fuel_label": (-14, 4, "end"),
              "sec_top": 84, "sec_k1": 3.3, "node_w": 56, "node_h": 36,
              "sec_off": {"conn.scarp_saltpan_ne": -6, "conn.scarp_saltpan_sw": 6},
              "sec_badge": {"elevator.shaft3": (0, 0), "conn.scarp_saltpan_ne": (0, -16), "conn.scarp_saltpan_sw": (0, 18), "conn.saltpan_frontier_east": (-30, 18), "conn.floodlands_cellar": (-46, -4),
                            "conn.frontier_east_dustline": (0, -16), "conn.frontier_east_dragon_lair": (-20, 0), "conn.threshold_shallows": (0, -16),
                            "conn.shallows_c3": (-58, 0), "conn.c3_f2": (-18, 0), "conn.c3_f2_f3": (-18, 0),
                            "extraction.zone.excavation_c3_f3": (0, -30)}})
    L["labels"]["zone.floodlands_cellar"] = (12, 42, "middle")
    L["plan_name"] = dict(L["plan_name"], **{"zone.floodlands_cellar": "Drowned\nCellar"})
    L["fuel_label"] = (0, -16, "middle")
    L["svc_off"] = dict(L["svc_off"], **{"zone.outpost": (34, 40)})
    L["plan_name"] = dict(L["plan_name"], **{"zone.outpost": "Outpost", "zone.threshold": "Threshold"})
    L["site_off"] = dict(L["site_off"], **{"zone.frontier_road_east": (24, -46)})
    if layout_only:
        return L
    pf = (12, 128, W_ - 24, 780)
    lens = (0.60, 0.52, 440, 1.4)
    # 2026-10-24: el marco toma el alto que la ventana ocupa de verdad (la ventana es mas ancha que alta).
    pf = (pf[0], pf[1], pf[2], min(pf[3], round(Plan(*pf, *win, lens=lens).used_h) + 24))
    P = Plan(*pf, *win, lens=lens)
    sec_y = pf[1] + pf[3] + 40
    sec_h = 760 if section else 0
    key_y = sec_y + sec_h + (46 if section else 6)
    o = [DEFS, f'<rect width="{W_}" height="99999" fill="{C["bg"]}"/>', header(14, 48, lang, 14)]
    o.append(plan_svg(P, lang, L))
    o.append(compass(pf[0] + pf[2] - 40, pf[1] + 56, 20))
    if section:
        o.append(section_svg(12, sec_y, W_ - 24, sec_h, lang, L))
    k, ky = key_svg(14, key_y, W_ - 28, lang, L)
    o.append(k)
    lg, ly = legend_svg(14, ky + 30, W_ - 28, lang, L, cols=2)
    o.append(lg)
    o.append(route_card(14, ly + 20, W_ - 28, lang, L))
    H_ = int(ly + 20 + 16 * .9 * 1.5 * (len(next(r for r in WORLD["routes"] if r["id"] == "route.first_journey")["zones"]) + 2.2) + 24)
    head = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W_} {H_}" width="{W_}" height="{H_}" role="img" aria-label="DEEPKIN {e(tr("title", lang))}">'
    return head + "".join(o) + "</svg>", (W_, H_)


# --- Corte en linea para la pagina (2026-10-12) ---------------------------------------------------------------------
INLINE_IDS = ("sea", "sand", "plains", "rock", "wet", "hatch", "city", "sky", "earth", "glow", "soft")


def section_inline(lang):
    """Dos SVG del corte para incrustar en la pagina Mundo (ancho de escritorio y alto de telefono), con data-zone en cada
    placa y data-a/data-b en cada pasaje. Los ids de <defs> llevan prefijo para no chocar con el mapa interactivo."""
    out = {}
    for variant, (W_, H_, L) in {"w": (1180, 700, None), "t": (616, 760, None)}.items():
        base = wide if variant == "w" else tall
        L = base(lang, layout_only=True)
        if variant == "w":
            L.update({"sec_top": 66, "sec_k1": 2.5, "node_w": 96, "node_h": 34, "fs_node": 13.5, "fs_band": 11.5, "badge_r": 8.5,
                      "sec_badge": dict(L["sec_badge"], **{"conn.frontier_east_dragon_lair": (-18, 0), "conn.shallows_c3": (-74, 0),
                                                         "extraction.zone.excavation_c3_f3": (0, 66), "conn.saltpan_frontier_east": (-70, 18)})})
        else:
            L.update({"sec_top": 76, "sec_k1": 3.0, "sec_badge": dict(L["sec_badge"], **{"extraction.zone.excavation_c3_f3": (0, 62)})})
        svg = section_svg(0, 0, W_, H_, lang, L, live=True)
        defs = DEFS
        for i in INLINE_IDS:
            defs = defs.replace(f'id="{i}"', f'id="at{variant}-{i}"')
            svg = svg.replace(f'url(#{i})', f'url(#at{variant}-{i})')
        label = tr("section", lang)
        out[variant] = (f'<svg class="at-sec at-sec-{variant}" viewBox="0 0 {W_} {H_}" role="group" aria-label="{e(label)}">{defs}{svg}</svg>')
    return out


def write_all():
    """Escribe assets/img/world/atlas_<lang>.svg y atlas_<lang>_m.svg (laminas completas, con corte) y
    atlas_<lang>_page.svg / atlas_<lang>_page_m.svg (para la pagina, sin corte: el corte va en linea);
    devuelve {lang: {"wide", "tall", "page_wide", "page_tall": (w, h)}}."""
    out = {}
    d = os.path.join(ROOT, "assets", "img", "world")
    os.makedirs(d, exist_ok=True)
    for lang in ("en", "es"):
        sw, size_w = wide(lang)
        st, size_t = tall(lang)
        open(os.path.join(d, f"atlas_{lang}.svg"), "w").write(sw)
        open(os.path.join(d, f"atlas_{lang}_m.svg"), "w").write(st)
        pw, size_pw = wide(lang, section=False)
        pt, size_pt = tall(lang, section=False)
        open(os.path.join(d, f"atlas_{lang}_page.svg"), "w").write(pw)
        open(os.path.join(d, f"atlas_{lang}_page_m.svg"), "w").write(pt)
        out[lang] = {"wide": size_w, "tall": size_t, "page_wide": size_pw, "page_tall": size_pt}
    return out


if __name__ == "__main__":
    print(write_all())
