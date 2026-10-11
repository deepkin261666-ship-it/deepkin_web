# Mapa interactivo del mundo (pagina Mundo). Lee data/world/world_map.json, el mismo grafo que usa el juego
# (copiado de deepkin/data/world/world_map.json), y genera la capa SVG sobre el arte del prototipo y el plano
# de Dustline. La interaccion (pan/zoom, panel, vistas) vive en assets/js/worldmap.js (2026-10-09).
import html
import json
import math
import os
import random

from i18n import L
import slugs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "world", "world_map.json")

KIND = {"city": L("City", "Ciudad"), "settlement": L("Settlement", "Asentamiento"), "outpost": L("Outpost", "Puesto avanzado"),
        "wild": L("Wilds", "Zona salvaje"), "dungeon": L("Dungeon", "Mazmorra"), "route": L("Route", "Ruta")}
BIOME = {"mountains": L("Mountains", "Montañas"), "forest": L("Forest", "Bosque"), "plains": L("Plains", "Llanuras"),
         "desert": L("Desert / wasteland", "Desierto / páramo"), "wetlands": L("Wetlands", "Humedales"),
         "snow": L("Snow / ice", "Nieve / hielo"), "caves": L("Caves / underground", "Cuevas / subterráneo"),
         "anomaly": L("Special / anomaly", "Especial / anomalía")}
BIOME_COLOR = {"mountains": "#9a958a", "forest": "#5f9a45", "plains": "#b3ad5a", "desert": "#c97c3c", "wetlands": "#3fa3a0",
               "snow": "#a9c9e0", "caves": "#5468c0", "anomaly": "#9a62d0"}
DANGER = {"safe": L("Safe", "Segura"), "low": L("Low", "Baja"), "medium": L("Medium", "Media"), "high": L("High", "Alta"),
          "deadly": L("Deadly", "Mortal")}
DANGER_ORDER = ["safe", "low", "medium", "high", "deadly"]
STATUS = {"playable": L("Playable now", "Jugable hoy"), "planned": L("Planned", "Planeada")}
LAYER = {"surface": L("Surface", "Superficie"), "underground": L("Underground", "Subterránea")}
CONN = {"road": L("Road", "Camino"), "shaft": L("Shaft", "Pozo"), "tunnel": L("Tunnel", "Túnel"), "lift": L("Lift", "Elevador")}
SERVICES = {
    "service.vendor_consumables": L("Consumables vendor", "Vendedor de consumibles"),
    "service.contract_board": L("Contract board", "Tablero de contratos"),
    "service.notice_board": L("Notice board", "Tablero de avisos"),
    "service.caravan_departures": L("Caravan departures", "Salidas de caravanas"),
    "service.route_maps": L("Route maps", "Mapas de rutas"),
    "service.repair": L("Repair", "Reparación"),
    "service.crafting_station": L("Crafting station", "Estación de fabricación"),
    "service.salvage_buyer": L("Sell loot", "Venta de botín"),
    "service.currency_exchange": L("Bank & currency exchange", "Banco y cambio de moneda"),
    "service.depot": L("Depot computer (storage)", "Computadora del depósito"),
    "service.lodging": L("Cheap rooms · respawn", "Cuartos baratos · reaparición"),
    "service.fence": L("Informal traders", "Comerciantes informales"),
    "service.rumours": L("Rumours", "Rumores"),
}
T = {
    "kicker": L("Interactive map", "Mapa interactivo"),
    "title": L("The world map", "El mapa del mundo"),
    "lead": L("A continent of connected maps. Each cell is one map with exits on its borders; cities are the hubs. Drag to pan, scroll or pinch to zoom, and tap a zone.",
              "Un continente de mapas conectados. Cada celda es un mapa con salidas en sus bordes; las ciudades son los centros. Arrastrá para moverte, usá la rueda o pellizcá para hacer zoom y tocá una zona."),
    "continent": L("Continent", "Continente"),
    "city": L("Dustline", "Dustline"),
    "zoom_in": L("Zoom in", "Acercar"), "zoom_out": L("Zoom out", "Alejar"), "reset": L("Reset view", "Restablecer vista"),
    "close": L("Close", "Cerrar"),
    "biome": L("Biome", "Bioma"), "danger": L("Danger", "Peligro"), "tier": L("Tier", "Rango"), "status": L("Status", "Estado"),
    "layer": L("Layer", "Capa"), "exits": L("Exits", "Salidas"), "below": L("Below", "Debajo"), "floor": L("Floor", "Piso"),
    "services": L("Planned services", "Servicios planeados"), "open_city": L("Open the city plan", "Abrir el plano de la ciudad"),
    "back_map": L("Back to the continent", "Volver al continente"),
    "journey": L("Your first journey", "Tu primer viaje"),
    "journey_lead": L("Four maps from the Outpost to the first city. The highlighted line on the map is this route.",
                      "Cuatro mapas del Outpost a la primera ciudad. La línea resaltada en el mapa es esta ruta."),
    "step": L("Step", "Paso"), "minutes": L("first time {a}–{b} min · then {c}–{d} min", "la primera vez {a}–{b} min · después {c}–{d} min"),
    "legend": L("Legend", "Referencias"), "kinds": L("Places", "Lugares"), "biomes": L("Biomes", "Biomas"),
    "lines": L("Routes & borders", "Rutas y bordes"),
    "l_playable": L("Playable map", "Mapa jugable"), "l_planned": L("Planned map", "Mapa planeado"),
    "l_road": L("Road (border exit)", "Camino (salida en el borde)"), "l_under": L("Tunnel, shaft or lift", "Túnel, pozo o elevador"),
    "l_journey": L("Your first journey", "Tu primer viaje"), "l_exit": L("Exit on a border", "Salida en un borde"),
    "l_stack": L("Level below a map", "Nivel debajo de un mapa"),
    "district": L("District", "Distrito"), "gate": L("Gate", "Puerta"), "landmark": L("Landmark", "Punto de referencia"),
    "city_kicker": L("Dustline · district plan", "Dustline · plano de distritos"),
    "city_lead": L("One compact map: in through the Frontier Gate, out through the East Gate. Tap a district.",
                   "Un solo mapa compacto: se entra por la Puerta de la Frontera y se sale por la Puerta Este. Tocá un distrito."),
    "art_note": L("Base layer: prototype map art, not final. Zone borders and routes come from the game's world graph.",
                  "Capa base: arte del mapa prototipo, no definitivo. Los bordes de zona y las rutas salen del grafo del mundo del juego."),
    "hint": L("Tap a zone", "Tocá una zona"),
    "planned_city": L("Planned map", "Mapa planeado"),
    "wiki_page": L("Open the wiki page", "Abrir la página del wiki"),
    "here": L("Here", "Acá"),
}

KIND_ICON = {  # 24x24, trazos
    "city": '<path d="M4 20V10l3-2 3 2v10M10 20V6l2-3 2 3v14M14 20v-9l3-2 3 2v9M3 20h18"/>',
    "settlement": '<path d="M4 20v-8l8-6 8 6v8M9 20v-5h6v5M3 20h18"/>',
    "outpost": '<path d="M8 20 12 4l4 16M9.5 14h5M10.6 9.5h2.8M5 20h14M12 4V2"/>',
    "wild": '<path d="M3 19 9 9l3 5 3-3 6 8ZM9 9l1.6 2.6"/>',
    "dungeon": '<path d="M5 20V11a7 7 0 0 1 14 0v9M9 20v-6a3 3 0 0 1 6 0v6M3 20h18"/>',
    "route": '<path d="M9 21 11 3M15 21 13 3M12 6v2M12 11v2M12 16v2"/>',
}


def L_(d, lang):
    return d[lang] if isinstance(d, dict) else d


def e(s):
    return html.escape(str(s), quote=True)


def load():
    if not os.path.exists(PATH):
        return None
    return json.load(open(PATH))


def icon_svg(kind, cls="wm-ico"):
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{KIND_ICON[kind]}</svg>')


# --- Continente --------------------------------------------------------------------------------
def anchor(z, W, H):
    p = z.get("marker") or (z["stack"]["marker"] if z.get("stack") else z["cell"]["seed"])
    return p[0] * W, p[1] * H


def continent_svg(data, lang):
    W, H = data["image"]["width"], data["image"]["height"]
    zones = {z["id"]: z for z in data["zones"]}
    journey = next((r for r in data.get("routes", []) if r["id"] == "route.first_journey"), None)
    jconns = set(journey["connections"]) if journey else set()
    cells = []
    for z in sorted((z for z in data["zones"] if z.get("cell")), key=lambda z: z["status"] == "playable"):
        d = "M" + "L".join(f"{x * W:.1f},{y * H:.1f}" for x, y in z["cell"]["polygon"]) + "Z"
        cells.append(f'<path class="wm-cell s-{z["status"]}" d="{d}" data-id="{z["id"]}" style="--tint:{BIOME_COLOR[z["biome"]]}">'
                     f'<title>{e(z["name"])}</title></path>')
    links, pips = [], []
    for c in data["connections"]:
        a, b = zones[c["ends"][0]["zone"]], zones[c["ends"][1]["zone"]]
        ax, ay = anchor(a, W, H)
        bx, by = anchor(b, W, H)
        if "exit_at" in c:
            ex, ey = c["exit_at"][0] * W, c["exit_at"][1] * H
            cx, cy = 2 * ex - (ax + bx) / 2, 2 * ey - (ay + by) / 2
            d = f"M{ax:.1f},{ay:.1f}Q{cx:.1f},{cy:.1f} {bx:.1f},{by:.1f}"
            if c["kind"] == "road":
                pips.append(f'<g class="wm-sc wm-pip s-{c["status"]}" data-x="{ex:.1f}" data-y="{ey:.1f}" transform="translate({ex:.1f},{ey:.1f})">'
                            '<rect x="-3.5" y="-3.5" width="7" height="7" transform="rotate(45)"/></g>')
        else:
            d = f"M{ax:.1f},{ay:.1f}L{bx:.1f},{by:.1f}"
        cls = f'wm-link k-{c["kind"]} s-{c["status"]}' + (" is-journey" if c["id"] in jconns else "")
        links.append(f'<path class="{cls}" d="{d}" data-conn="{c["id"]}"/>')
    jpath = ""
    if journey:
        segs = [l for l in links if 'is-journey' in l]
        jd = " ".join(s.split(' d="')[1].split('"')[0] for s in segs)
        jpath = f'<path class="wm-journey-glow" d="{jd}"/><path class="wm-journey" d="{jd}"/>'
    marks, badges = [], []
    steps = {zid: i for i, zid in enumerate(journey["zones"])} if journey else {}
    for z in data["zones"]:
        x, y = anchor(z, W, H)
        step = steps.get(z["id"])
        # Las marcas propias, insignias y pips se dibujan en px de pantalla: el JS les aplica scale(1/zoom) (wm-sc).
        if step:
            badges.append(f'<g class="wm-sc wm-step" data-x="{x:.1f}" data-y="{y:.1f}" transform="translate({x:.1f},{y:.1f})">'
                          f'<g transform="translate(13,-15)"><circle r="8"/><text y="3.5">{step}</text></g></g>')
        if z.get("art_icon"):
            marks.append(f'<g class="wm-mark art s-{z["status"]}" data-id="{z["id"]}" transform="translate({x:.1f},{y:.1f})">'
                         f'<circle class="wm-hit" r="22"/><circle class="wm-ring" r="19"/></g>')
            continue
        stacked = bool(z.get("stack"))
        r = 7 if stacked else 11
        shape = (f'<rect class="wm-badge" x="-{r}" y="-{r}" width="{2 * r}" height="{2 * r}" transform="rotate(45)"/>' if stacked
                 else f'<circle class="wm-badge" r="{r}"/>')
        ico = "" if stacked else f'<g transform="translate(-7,-7) scale(.5833)">{KIND_ICON[z["kind"]].replace("<path", "<path class=wm-glyph")}</g>'
        depth = f'<tspan class="wm-depth"> −{z["stack"]["depth"]}</tspan>' if stacked else ""
        label = (f'<text class="wm-label" x="-{r + 6}" y="4" text-anchor="end">{e(z["name"])}{depth}</text>' if stacked
                 else f'<text class="wm-label" y="{r + 15}" text-anchor="middle">{e(z["name"])}</text>')
        marks.append(f'<g class="wm-mark own wm-sc s-{z["status"]}{" stacked" if stacked else ""}" data-id="{z["id"]}" data-x="{x:.1f}" data-y="{y:.1f}" '
                     f'transform="translate({x:.1f},{y:.1f})"><circle class="wm-hit" r="{r + 9}"/>{shape}{ico}{label}</g>')
    return (f'<svg class="wm-svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet" role="group" aria-label="{e(L_(T["title"], lang))}">'
            f'<g class="wm-cells">{"".join(cells)}</g><g class="wm-links">{"".join(links)}</g>{jpath}'
            f'<g class="wm-pips">{"".join(pips)}</g><g class="wm-marks">{"".join(marks)}</g><g class="wm-badges">{"".join(badges)}</g></svg>')


# --- Dustline ----------------------------------------------------------------------------------
CW, CH = 1600, 1100
DISTRICT_FILL = {"district.central_market": "#6e5530", "district.caravan_yard": "#5d4231", "district.scrappers_row": "#5f3a2a",
                 "district.the_exchange": "#4b4a46", "district.lower_warrens": "#2f2b26"}


def inside(pt, poly):
    x, y = pt
    c = False
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy or 1)))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def blocks(d, streets, rnd):
    """Huellas de edificios dentro del distrito, sin pisar calles ni el centro de la plaza."""
    poly = [(x * CW, y * CH) for x, y in d["polygon"]]
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    did = d["id"]
    step = {"district.lower_warrens": 30, "district.central_market": 34, "district.scrappers_row": 46,
            "district.caravan_yard": 58, "district.the_exchange": 52}[did]
    lx, ly = d["label"][0] * CW, d["label"][1] * CH
    out = []
    y = min(ys) + step / 2
    while y < max(ys):
        x = min(xs) + step / 2 + (step / 3 if int(y / step) % 2 else 0)
        while x < max(xs):
            w = step * rnd.uniform(.55, .85) * (1.6 if did == "district.scrappers_row" else 1)
            h = step * rnd.uniform(.5, .8)
            corners = [(x - w / 2, y - h / 2), (x + w / 2, y - h / 2), (x + w / 2, y + h / 2), (x - w / 2, y + h / 2)]
            ok = all(inside(c, poly) for c in corners)
            ok = ok and all(seg_dist((x, y), (s["points"][i][0] * CW, s["points"][i][1] * CH), (s["points"][i + 1][0] * CW, s["points"][i + 1][1] * CH)) > step * .75
                            for s in streets for i in range(len(s["points"]) - 1))
            if did == "district.central_market":
                ok = ok and math.hypot(x - lx, y - ly) > 95  # plaza abierta
            elif did == "district.the_exchange":
                ok = ok and math.hypot(x - 0.51 * CW, y - 0.15 * CH) > 70 and math.hypot(x - lx, y - ly - 40) > 60
            else:
                ok = ok and math.hypot(x - lx, y - ly) > 62
            if ok and rnd.random() > .12:
                out.append(f'<rect x="{x - w / 2:.0f}" y="{y - h / 2:.0f}" width="{w:.0f}" height="{h:.0f}"/>')
            x += step
        y += step * .92
    return "".join(out)


def city_svg(data, lang):
    city = data["dustline"]
    rnd = random.Random(7)
    P = lambda pts: " ".join(f"{x * CW:.0f},{y * CH:.0f}" for x, y in pts)  # noqa: E731
    wall = P(city["wall"])
    streets = city["streets"]
    street_paths = "".join(f'<polyline class="dl-street" points="{P(s["points"])}"/>' for s in streets)
    dist = ""
    for d in city["districts"]:
        lx, ly = d["label"][0] * CW, d["label"][1] * CH
        dist += (f'<g class="dl-district" data-id="{d["id"]}" style="--f:{DISTRICT_FILL.get(d["id"], "#3a3530")}">'
                 f'<polygon class="dl-area" points="{P(d["polygon"])}"/><g class="dl-blocks">{blocks(d, streets, rnd)}</g>'
                 f'<g class="dl-tag wm-sc" data-x="{lx:.0f}" data-y="{ly:.0f}" transform="translate({lx:.0f},{ly:.0f})"><circle r="14"/>'
                 f'<text class="dl-num" y="4.5">{d["number"]}</text><text class="dl-name" y="31">{e(L_(d["name"], lang).upper())}</text></g></g>')
    # Plaza del mercado, patio de caravanas, torre del Exchange: piezas a mano.
    mk = city["districts"][0]
    mx, my = mk["label"][0] * CW, mk["label"][1] * CH
    stalls = "".join(f'<rect class="dl-stall" x="{mx + 80 * math.cos(a) - 9:.0f}" y="{my + 62 * math.sin(a) - 7:.0f}" width="18" height="14"/>'
                     for a in [i * math.pi / 7 for i in range(14)])
    extras = (f'<g class="dl-pe">{stalls}</g>'
              # caravana: plataformas y vehiculo
              f'<g class="dl-pe"><rect class="dl-platform" x="{0.13 * CW:.0f}" y="{0.75 * CH:.0f}" width="170" height="50"/>'
              f'<rect class="dl-platform" x="{0.27 * CW:.0f}" y="{0.79 * CH:.0f}" width="110" height="40"/>'
              f'<g class="dl-vehicle" transform="translate({0.21 * CW:.0f},{0.66 * CH:.0f})"><rect x="-70" y="-17" width="104" height="34" rx="3"/>'
              '<rect x="38" y="-14" width="34" height="28" rx="4"/><circle cx="-50" cy="20" r="7"/><circle cx="-10" cy="20" r="7"/><circle cx="52" cy="20" r="7"/></g></g>'
              # torre del Exchange con linea de vista al mercado
              f'<line class="dl-sight" x1="{0.51 * CW:.0f}" y1="{0.15 * CH:.0f}" x2="{mx:.0f}" y2="{my:.0f}"/>'
              f'<g class="dl-tower" transform="translate({0.51 * CW:.0f},{0.15 * CH:.0f})"><circle class="dl-glow" r="64"/><rect x="-26" y="-26" width="52" height="52"/>'
              '<rect x="-14" y="-14" width="28" height="28"/><circle r="5"/></g>'
              # grua del Row
              f'<g class="dl-crane" transform="translate({0.86 * CW:.0f},{0.30 * CH:.0f})"><line x1="-60" y1="0" x2="60" y2="0"/><line x1="-60" y1="-10" x2="-60" y2="10"/>'
              '<line x1="60" y1="-10" x2="60" y2="10"/><line x1="20" y1="0" x2="20" y2="28"/></g>')
    gates = ""
    for g in city["entrances"]:
        gx, gy = g["position"][0] * CW, g["position"][1] * CH
        guards = "".join(f'<circle class="dl-guard" cx="{gx + dx}" cy="{gy + dy}" r="5"/>' for dx, dy in ((28, -30), (40, -26), (28, 30))) if g["kind"] == "main_gate" else ""
        gates += (f'<g class="dl-gate" data-id="{g["id"]}"><rect class="dl-gate-hit" x="{gx - 46:.0f}" y="{gy - 50:.0f}" width="92" height="100"/>'
                  f'<rect class="dl-gatehouse" x="{gx - 16:.0f}" y="{gy - 42:.0f}" width="32" height="22"/><rect class="dl-gatehouse" x="{gx - 16:.0f}" y="{gy + 20:.0f}" width="32" height="22"/>'
                  f'<line class="dl-barrier" x1="{gx:.0f}" y1="{gy - 20:.0f}" x2="{gx:.0f}" y2="{gy + 20:.0f}"/>{guards}'
                  f'<g class="wm-sc" data-x="{gx:.0f}" data-y="{gy - 50:.0f}" transform="translate({gx:.0f},{gy - 50:.0f})">'
                  f'<text class="dl-gname" y="-8">{e(L_(g["name"], lang).upper())}</text></g></g>')
    lms = ""
    for lm in city["landmarks"]:
        x, y = lm["position"][0] * CW, lm["position"][1] * CH
        lms += (f'<g class="dl-lm wm-sc" data-id="{lm["id"]}" data-x="{x:.0f}" data-y="{y:.0f}" transform="translate({x:.0f},{y:.0f})"><circle class="dl-lm-hit" r="14"/>'
                f'<path class="dl-lm-pin" d="M0-7 5.5 0 0 7-5.5 0Z"/><title>{e(L_(lm["name"], lang))}</title></g>')
    roads = (f'<polyline class="dl-road" points="0,{0.40 * CH:.0f} {0.03 * CW:.0f},{0.50 * CH:.0f} {0.07 * CW:.0f},{0.52 * CH:.0f}"/>'
             f'<polyline class="dl-road" points="{0.95 * CW:.0f},{0.62 * CH:.0f} {CW},{0.66 * CH:.0f}"/>')
    road_labels = (f'<text class="dl-roadname" x="{0.012 * CW:.0f}" y="{0.33 * CH:.0f}">← FRONTIER ROAD</text>'
                   f'<text class="dl-roadname end" x="{0.99 * CW:.0f}" y="{0.75 * CH:.0f}">{"FLOODLANDS" if lang == "en" else "FLOODLANDS"} →</text>')
    compass = (f'<g class="dl-compass" transform="translate({CW - 70},{80})"><circle r="30"/><path d="M0-26 6 0 0 26-6 0Z"/><text y="-36">N</text></g>'
               f'<g class="dl-scale" transform="translate({CW - 250},{CH - 46})"><line x1="0" y1="0" x2="200" y2="0"/><line x1="0" y1="-6" x2="0" y2="6"/>'
               f'<line x1="200" y1="-6" x2="200" y2="6"/><text x="100" y="-12">≈ 20 m</text></g>')
    return (f'<svg class="dl-svg" viewBox="0 0 {CW} {CH}" role="group" aria-label="Dustline">'
            '<defs><pattern id="dl-hatch" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(35)">'
            '<line x1="0" y1="0" x2="0" y2="14" class="dl-hatch"/></pattern>'
            '<radialGradient id="dl-amber"><stop offset="0" stop-color="#d39a4b" stop-opacity=".55"/><stop offset="1" stop-color="#d39a4b" stop-opacity="0"/></radialGradient></defs>'
            f'<rect class="dl-ground" width="{CW}" height="{CH}"/><rect width="{CW}" height="{CH}" fill="url(#dl-hatch)"/>{roads}'
            f'<polygon class="dl-wall" points="{wall}"/>{dist}{street_paths}{extras}{gates}{lms}{road_labels}{compass}</svg>')


# --- Datos para el JS y HTML de la seccion ------------------------------------------------------
PRES = {"metro": L("Metro tunnel", "Túnel de metro"), "lift": L("Lift", "Elevador"), "stairs": L("Stairs", "Escaleras"),
        "gate": L("Gate", "Puerta"), "road": L("Road", "Camino")}


def _region():
    p = os.path.join(ROOT, "data", "starting_region.json")
    return json.load(open(p)) if os.path.exists(p) else {"transitions": [], "floors": []}


def zone_services(zid, region, hubs, lang):
    """Servicios reales de una zona jugable (2026-10-11): reaparicion, terminal 261.6.66 (banco y deposito), surtidor."""
    out = []
    fl = next((f for f in region["floors"] if f["zone_id"] == zid), {})
    if zid in hubs:
        out.append(L_(L("Respawn hub", "Punto de reaparición"), lang))
    if fl.get("computers"):
        out.append(L_(L("261.6.66 terminal: bank & depot", "Terminal 261.6.66: banco y depósito"), lang))
    for st in fl.get("fuel_stations", []):
        out.append(f'{st["name"]} · ' + L_(L("gas station, {p} Metal/L, gas can {c}", "estación de servicio, {p} Metal/L, bidón {c}"), lang).format(p=st["price_per_litre"], c=st["can_price"]))
    return out


def client_data(data, lang):
    zones = {z["id"]: z for z in data["zones"]}
    region = _region()
    trans = {t["entity_id"]: t for t in region["transitions"]}
    hp = os.path.join(ROOT, "data", "world", "respawn_hubs.json")
    hubs = {h["zone_id"] for h in json.load(open(hp))["hubs"]} if os.path.exists(hp) else set()
    journey = next((r for r in data.get("routes", []) if r["id"] == "route.first_journey"), None)
    steps = {zid: i for i, zid in enumerate(journey["zones"])} if journey else {}
    out = {"zones": {}, "districts": {}, "t": {k: L_(v, lang) for k, v in T.items() if k in (
        "biome", "danger", "tier", "status", "layer", "exits", "below", "floor", "services", "open_city", "back_map", "step", "close",
        "district", "gate", "landmark", "planned_city", "wiki_page", "here")}}
    for z in data["zones"]:
        conns = []
        for c in data["connections"]:
            ends = c["ends"]
            mine = next((x for x in ends if x["zone"] == z["id"]), None)
            if not mine:
                continue
            other = ends[1] if ends[0] is mine else ends[0]
            tr = trans.get(mine.get("transition"))
            kind = L_(CONN[c["kind"]], lang)
            if c["status"] == "playable":
                kind = L_(PRES[(tr or {}).get("presentation") or "road"], lang)
            if tr and tr.get("requires_drill_site_cleared"):
                kind += " · " + L_(L("locked: drill the Deep Seal", "cerrado: perforá el Sello Profundo"), lang)
            conns.append({"to": other["zone"], "name": zones[other["zone"]]["name"], "kind": kind, "k": c["kind"],
                          "exit": mine["exit"], "edge": mine.get("edge", ""), "status": c["status"]})
        ex = z.get("extraction")
        if ex:
            conns.append({"to": ex["zone"], "name": zones[ex["zone"]]["name"], "kind": L_(L("Lift · one way", "Elevador · sólo ida"), lang), "k": "lift",
                          "exit": ex["exit"], "edge": "UP", "status": "playable"})
        below = sorted((o["id"] for o in data["zones"] if o.get("stack", {}).get("parent") == z["id"]), key=lambda i: zones[i]["stack"]["depth"])
        out["zones"][z["id"]] = {
            "name": z["name"], "sub": L_(z.get("subtitle", ""), lang) if z.get("subtitle") else "",
            "kind": L_(KIND[z["kind"]], lang), "k": z["kind"], "biome": L_(BIOME[z["biome"]], lang), "b": BIOME_COLOR[z["biome"]],
            "danger": L_(DANGER[z["danger"]], lang), "d": DANGER_ORDER.index(z["danger"]), "tier": z["tier"],
            "status": L_(STATUS[z["status"]], lang), "s": z["status"], "layer": L_(LAYER[z["layer"]], lang),
            "summary": L_(z["summary"], lang), "conns": conns, "below": below,
            "parent": z.get("stack", {}).get("parent"), "depth": z.get("stack", {}).get("depth"),
            "step": steps.get(z["id"]), "city": z["id"] == data.get("dustline", {}).get("zone"),
            "wiki": slugs.zone(z["id"]),
            "svc": zone_services(z["id"], region, hubs, lang) if z["status"] == "playable" else [],
        }
    city = data.get("dustline")
    if city:
        for d in city["districts"]:
            out["districts"][d["id"]] = {"name": L_(d["name"], lang), "num": d["number"], "kind": out["t"]["district"],
                                         "summary": L_(d["purpose"], lang), "services": [L_(SERVICES.get(s, s), lang) for s in d["services"]],
                                         "landmarks": [L_(lm["name"], lang) for lm in city["landmarks"] if lm["id"] in d.get("landmarks", [])],
                                         "wiki": slugs.zone(city["zone"]) + "#" + slugs.district_anchor(d["id"])}
        for g in city["entrances"]:
            out["districts"][g["id"]] = {"name": L_(g["name"], lang), "kind": out["t"]["gate"], "summary": L_(g["purpose"], lang),
                                         "services": [], "landmarks": [L_(lm["name"], lang) for lm in city["landmarks"] if lm.get("district") == g["id"]]}
        for lm in city["landmarks"]:
            out["districts"][lm["id"]] = {"name": L_(lm["name"], lang), "kind": out["t"]["landmark"], "summary": L_(lm["note"], lang),
                                          "services": [], "landmarks": [], "in": lm.get("district")}
    return out


def legend(data, lang, view):
    if view == "city":
        sw = "".join(f'<li><i class="sw" style="background:{DISTRICT_FILL[d["id"]]}"></i>{d["number"]} · {e(L_(d["name"], lang))}</li>'
                     for d in data["dustline"]["districts"])
        return (f'<div class="wm-legend" data-for="city"><div><p class="kicker">{e(L_(T["district"], lang))}</p><ul>{sw}</ul></div>'
                f'<div><p class="kicker">{e(L_(T["lines"], lang))}</p><ul><li><i class="ln ln-gate"></i>{e(L_(T["gate"], lang))}</li>'
                f'<li><i class="ln ln-lm"></i>{e(L_(T["landmark"], lang))}</li><li><i class="ln ln-sight"></i>{"Sightline to the Exchange" if lang == "en" else "Línea de vista al Exchange"}</li></ul></div></div>')
    kinds = "".join(f'<li>{icon_svg(k)}{e(L_(KIND[k], lang))}</li>' for k in KIND)
    biomes = "".join(f'<li><i class="sw" style="background:{BIOME_COLOR[b]}"></i>{e(L_(BIOME[b], lang))}</li>' for b in BIOME)
    danger = "".join(f'<li><i class="dg dg-{i}"></i>{e(L_(DANGER[k], lang))}</li>' for i, k in enumerate(DANGER_ORDER))
    lines = (f'<li><i class="ln ln-play"></i>{e(L_(T["l_playable"], lang))}</li><li><i class="ln ln-plan"></i>{e(L_(T["l_planned"], lang))}</li>'
             f'<li><i class="ln ln-road"></i>{e(L_(T["l_road"], lang))}</li><li><i class="ln ln-under"></i>{e(L_(T["l_under"], lang))}</li>'
             f'<li><i class="ln ln-journey"></i>{e(L_(T["l_journey"], lang))}</li><li><i class="ln ln-pip"></i>{e(L_(T["l_exit"], lang))}</li>'
             f'<li><i class="ln ln-stack"></i>{e(L_(T["l_stack"], lang))}</li>')
    return (f'<div class="wm-legend" data-for="map"><div><p class="kicker">{e(L_(T["kinds"], lang))}</p><ul>{kinds}</ul></div>'
            f'<div><p class="kicker">{e(L_(T["biomes"], lang))}</p><ul>{biomes}</ul></div>'
            f'<div><p class="kicker">{e(L_(T["danger"], lang))}</p><ul>{danger}</ul></div>'
            f'<div><p class="kicker">{e(L_(T["lines"], lang))}</p><ul>{lines}</ul></div></div>')


def journey_html(data, lang):
    j = next((r for r in data.get("routes", []) if r["id"] == "route.first_journey"), None)
    if not j:
        return ""
    zones = {z["id"]: z for z in data["zones"]}
    items = ""
    for i, s in enumerate(j["steps"]):
        z = zones[s["zone"]]
        n = f'<span class="jn">{i:02d}</span>'
        tag = f'<span class="tag tag-soon">{e(L_(STATUS["planned"], lang))}</span>' if z["status"] == "planned" else ""
        items += (f'<li><button type="button" data-goto="{z["id"]}">{n}<span class="jb"><b>{e(z["name"])}{tag}</b>'
                  f'<span>{e(L_(s["text"], lang))}</span></span></button></li>')
    m = j.get("target_minutes", {})
    mins = ""
    if m:
        a, b = m["first_time"]
        c, d = m["repeat"]
        mins = f'<p class="note">{e(L_(T["minutes"], lang).format(a=a, b=b, c=c, d=d))}</p>'
    return (f'<div class="wm-journey-list"><p class="kicker">{e(L_(T["journey"], lang))}</p><p class="sec-lead">{e(L_(T["journey_lead"], lang))}</p>'
            f'<ol>{items}</ol>{mins}</div>')


def section(lang, section_title):
    data = load()
    if not data:
        return ""
    img = "../assets/img/world/worldmap_proto"
    W, H = data["image"]["width"], data["image"]["height"]
    ctrl = (f'<div class="wm-ctrl"><button type="button" data-zoom="in" aria-label="{e(L_(T["zoom_in"], lang))}">+</button>'
            f'<button type="button" data-zoom="out" aria-label="{e(L_(T["zoom_out"], lang))}">−</button>'
            f'<button type="button" data-zoom="reset" aria-label="{e(L_(T["reset"], lang))}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 9V4h5M20 15v5h-5M4 4l6 6M20 20l-6-6"/></svg></button></div>')
    panel = (f'<aside class="wm-panel" aria-live="polite" hidden><button type="button" class="wm-close" aria-label="{e(L_(T["close"], lang))}">'
             '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg></button>'
             '<div class="wm-panel-in"></div></aside>')
    blob = json.dumps(client_data(data, lang), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f"""{section_title("map", L_(T["kicker"], lang), L_(T["title"], lang), L_(T["lead"], lang))}
<div class="wm" data-worldmap>
  <div class="wm-tabs" role="tablist">
    <button type="button" role="tab" aria-selected="true" data-view="map">{e(L_(T["continent"], lang))}</button>
    <button type="button" role="tab" aria-selected="false" data-view="city">{e(L_(T["city"], lang))}</button>
    <span class="wm-hint">{e(L_(T["hint"], lang))}</span>
  </div>
  <div class="wm-body">
  <div class="wm-frame" data-pane="map">
    <div class="wm-viewport" tabindex="0" aria-label="{e(L_(T["title"], lang))}">
      <div class="wm-stage" style="aspect-ratio:{W}/{H}">
        <picture><source media="(max-width: 720px)" srcset="{img}_800.webp" type="image/webp"><source srcset="{img}.webp" type="image/webp">
        <img class="wm-art" src="{img}.jpg" alt="" width="{W}" height="{H}" decoding="async" draggable="false"></picture>
        {continent_svg(data, lang)}
      </div>
    </div>
    {ctrl}
    <div class="wm-tip" hidden></div>
  </div>
  <div class="wm-frame wm-frame-city" data-pane="city" hidden>
    <div class="wm-viewport" tabindex="0" aria-label="Dustline">
      <div class="wm-stage" style="aspect-ratio:{CW}/{CH}">{city_svg(data, lang)}</div>
    </div>
    {ctrl}
    <div class="wm-citycap"><p class="kicker">{e(L_(T["city_kicker"], lang))}</p><p>{e(L_(T["city_lead"], lang))}</p></div>
  </div>
  {panel}
  </div>
  {legend(data, lang, "map")}
  {legend(data, lang, "city").replace('class="wm-legend"', 'class="wm-legend" hidden', 1)}
  <p class="wm-note" data-for="map">{e(L_(T["art_note"], lang))}</p>
  {journey_html(data, lang)}
  <script type="application/json" id="worldmap-data">{blob}</script>
</div>"""
