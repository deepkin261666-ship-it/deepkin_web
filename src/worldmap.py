# Mapa interactivo del mundo (pagina Mundo). Lee data/world/world_map.json, el mismo grafo que usa el juego
# (copiado de deepkin/data/world/world_map.json), y genera la capa SVG sobre el arte del prototipo y el plano
# de Dustline. La interaccion (pan/zoom, panel, vistas, niveles) vive en assets/js/worldmap.js (2026-10-09).
#
# Niveles (2026-10-12; pisos 2026-10-13): el mapa tiene una capa por nivel (`level` del dato: 0 superficie, -1 .. -4). Desde
# la decision 11 del juego el nivel es el ordinal del piso en cada pila vertical, no una banda de 200 m; depth_m no cambia.
# Cada capa dibuja solo sus mapas: las celdas de superficie sobre el arte, y bajo tierra las "camaras" (celda encogida
# o un poligono alrededor del marcador apilado) sobre la roca. Los pasajes verticales (pozo, escaleras, elevador)
# se marcan en las capas que unen (un elevador de varias paradas es un solo pozo con una marca por piso), en el mismo punto del plano; tocarlos cambia de nivel. Toda la geometria de
# presentacion propia de esta pagina (puntos de pozos, desvios de tuneles, radios de camaras) vive aca, no en el dato.
import glob
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
CONN = {"road": L("Road", "Camino"), "shaft": L("Shaft", "Pozo"), "tunnel": L("Tunnel", "Túnel"), "lift": L("Lift", "Elevador"),
        "elevator": L("Elevator", "Elevador")}
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
# Niveles: el piso de cada pila vertical (`level` del dato). El rango de metros de cada capa sale del depth_m de sus mapas.
LEVELS = [0, -1, -2, -3, -4]
LEVEL_NAME = {0: L("Surface", "Superficie"), **{lv: L(f"Level {lv}".replace("-", "−"), f"Nivel {lv}".replace("-", "−")) for lv in LEVELS[1:]}}
# Nombre en la pagina de cada elevador de varias paradas (el dato del juego trae solo el rotulo en ingles).
ELEVATOR_NAME = {"elevator.shaft3": L("Shaft 3 elevator", "Elevador del Pozo 3")}


def level_depths(data):
    """{nivel: (min, max)} de depth_m de los mapas de cada capa; la lectura por defecto del indicador es el minimo jugable."""
    out = {}
    for lv in LEVELS:
        ds = [z.get("depth_m", 0) for z in data["zones"] if z.get("level", 0 if z["layer"] == "surface" else -1) == lv]
        out[lv] = (min(ds), max(ds)) if ds else (0, 0)
    return out


def level_band(lv, depths, lang, short=False):
    if lv == 0:
        return "0 m" if short else L_(L("0 m · open sky", "0 m · cielo abierto"), lang)
    a, b = depths[lv]
    rng = f"{a}–{b}" if a != b else f"{a}"
    return f"{rng} m" if short else L_(L("{r} m down", "{r} m abajo"), lang).format(r=rng)


def level_m(lv, data):
    ds = [z.get("depth_m", 0) for z in data["zones"] if z.get("level", 0 if z["layer"] == "surface" else -1) == lv and z["status"] == "playable"]
    return min(ds) if ds else level_depths(data)[lv][0]

T = {
    "kicker": L("Interactive map", "Mapa interactivo"),
    "title": L("The world map", "El mapa del mundo"),
    "lead": L("A continent of connected maps, level by level. Each cell is one map with exits on its borders; the workings hang under the surface, one floor per level. Drag to pan, scroll or pinch to zoom, tap a zone, and use the depth rail (or PageDown) to go down.",
              "Un continente de mapas conectados, nivel por nivel. Cada celda es un mapa con salidas en sus bordes; las galerías cuelgan bajo la superficie, un piso por nivel. Arrastrá para moverte, usá la rueda o pellizcá para hacer zoom, tocá una zona y usá la barra de profundidad (o AvPág) para bajar."),
    "continent": L("Continent", "Continente"),
    "city": L("Dustline", "Dustline"),
    "zoom_in": L("Zoom in", "Acercar"), "zoom_out": L("Zoom out", "Alejar"), "reset": L("Reset view", "Restablecer vista"),
    "close": L("Close", "Cerrar"),
    "biome": L("Biome", "Bioma"), "danger": L("Danger", "Peligro"), "tier": L("Tier", "Rango"), "status": L("Status", "Estado"),
    "layer": L("Layer", "Capa"), "exits": L("Exits on this level", "Salidas en este nivel"), "floor": L("Floor", "Piso"),
    "above": L("Levels above", "Niveles arriba"), "below": L("Levels below", "Niveles abajo"), "depth": L("Depth", "Profundidad"),
    "services": L("Planned services", "Servicios planeados"), "open_city": L("Open the city plan", "Abrir el plano de la ciudad"),
    "back_map": L("Back to the continent", "Volver al continente"),
    "journey": L("Your first journey", "Tu primer viaje"),
    "journey_lead": L("Six maps from the Outpost to the first city. It starts underground on level −1 and climbs to the surface at Shaft 3; the highlighted line on each level is this route.",
                      "Seis mapas del Outpost a la primera ciudad. Empieza bajo tierra, en el nivel −1, y sube a la superficie por el Pozo 3; la línea resaltada en cada nivel es esta ruta."),
    "step": L("Step", "Paso"), "minutes": L("first time {a}–{b} min · then {c}–{d} min", "la primera vez {a}–{b} min · después {c}–{d} min"),
    "legend": L("Legend", "Referencias"), "kinds": L("Places", "Lugares"), "biomes": L("Biomes", "Biomas"),
    "lines": L("Routes & borders", "Rutas y bordes"), "passages": L("Levels & passages", "Niveles y pasajes"),
    "l_playable": L("Playable map", "Mapa jugable"), "l_planned": L("Planned · uncharted", "Planeado · sin cartografiar"),
    "l_road": L("Road (border exit)", "Camino (salida en el borde)"), "l_tunnel": L("Tunnel (same level)", "Túnel (mismo nivel)"),
    "l_journey": L("Your first journey", "Tu primer viaje"), "l_exit": L("Exit on a border", "Salida en un borde"),
    "l_gate": L("City gate · faint when closed", "Puerta de ciudad · tenue si está cerrada"),
    "l_lift": L("Lift", "Elevador"), "l_stairs": L("Stairs", "Escaleras"), "l_elevator": L("Elevator · one shaft, a stop on each floor", "Elevador · un solo pozo, una parada en cada piso"),
    "l_deep": L("Deep shaft · stair pit", "Pozo profundo · escalera en pozo"), "l_extract": L("Extraction lift · one way up", "Elevador de extracción · sólo sube"),
    "l_switch": L("Tap a passage to change level", "Tocá un pasaje para cambiar de nivel"),
    "l_ghost_below": L("Workings on the level below", "Galerías del nivel de abajo"),
    "l_ghost_above": L("Surface outline, for orientation", "Contorno de la superficie, para ubicarse"),
    "l_fuel": L("Gas station", "Estación de servicio"),
    "district": L("District", "Distrito"), "gate": L("Gate", "Puerta"), "landmark": L("Landmark", "Punto de referencia"),
    "city_kicker": L("Dustline · district plan", "Dustline · plano de distritos"),
    "city_lead": L("One compact map: in through the Frontier Gate; the East Gate opens on the Floodlands road. Tap a district; the small icons are the traders, the bike shop, the VDI post and your house.",
                   "Un solo mapa compacto: se entra por la Puerta de la Frontera; la Puerta Este sale al camino de las Floodlands. Tocá un distrito; los íconos chicos son los comerciantes, el taller de motos, el puesto VDI y tu casa."),
    "art_note": L("Base layer: prototype map art, not final. Zone borders, levels and passages come from the game's world graph.",
                  "Capa base: arte del mapa prototipo, no definitivo. Los bordes de zona, los niveles y los pasajes salen del grafo del mundo del juego."),
    "hint": L("Tap a zone · PgDn goes down", "Tocá una zona · AvPág baja"),
    "planned_city": L("Planned map", "Mapa planeado"),
    "wiki_page": L("Open the wiki page", "Abrir la página del wiki"),
    "here": L("Here", "Acá"),
    "rail": L("Depth", "Profundidad"), "go_down": L("Go down", "Bajar"), "go_up": L("Go up", "Subir"),
    "surface": L("Surface", "Superficie"), "to_surface": L("↑ SURFACE", "↑ SUPERFICIE"), "from_below": L("↓ FROM −1", "↓ DESDE −1"),
    "one_way": L("one way", "sólo ida"), "closed": L("closed", "cerrada"), "planned_passage": L("planned", "planeado"),
    "to_level": L("to the surface", "a la superficie"), "down_to": L("down to level {n}", "baja al nivel {n}"), "up_to": L("up to level {n}", "sube al nivel {n}"),
    "m_down": L("{m} m down", "{m} m abajo"), "level_short": L("level", "nivel"),
    "fuel": L("gas station", "estación de servicio"),
    "arrives": L("arrives here from", "llega acá desde"),
    "stops": L("stops", "paradas"),
    # 2026-10-23
    "l_sites": L("Places", "Lugares"),
    "l_bore": L("excavation floors are player-made: a VDI drillship called out on open surface ground bores −1 … −15, generated per call-out, not fixed zones",
                "los pisos de excavación los hace un jugador: una perforadora VDI llamada en terreno abierto de superficie baja de −1 a −15, generados en cada llamada; no son zonas fijas"),
    "l_bore_short": L("VDI excavation · player-made floors, generated per call-out", "Excavación VDI · pisos que hace un jugador, generados en cada llamada"),
    "l_hunt": L("Hunting ground", "Coto de caza"),
    "l_shop": L("Trader", "Comerciante"), "l_bike": L("Bike shop · crane", "Taller de motos · grúa"),
    "l_vdi": L("VDI post · Expedition Service", "Puesto VDI · Expedition Service"), "l_house": L("Your house (Unit 7)", "Tu casa (Unit 7)"),
}

KIND_ICON = {  # 24x24, trazos
    "city": '<path d="M4 20V10l3-2 3 2v10M10 20V6l2-3 2 3v14M14 20v-9l3-2 3 2v9M3 20h18"/>',
    "settlement": '<path d="M4 20v-8l8-6 8 6v8M9 20v-5h6v5M3 20h18"/>',
    "outpost": '<path d="M8 20 12 4l4 16M9.5 14h5M10.6 9.5h2.8M5 20h14M12 4V2"/>',
    "wild": '<path d="M3 19 9 9l3 5 3-3 6 8ZM9 9l1.6 2.6"/>',
    "dungeon": '<path d="M5 20V11a7 7 0 0 1 14 0v9M9 20v-6a3 3 0 0 1 6 0v6M3 20h18"/>',
    "route": '<path d="M9 21 11 3M15 21 13 3M12 6v2M12 11v2M12 16v2"/>',
}
# Pasajes verticales, 24x24: elevador (cabina y cable), elevador de varias paradas (cabina que sube y baja), escaleras,
# pozo profundo (escalera en pozo), elevador de extraccion (solo sube), pozo generico (planeado), surtidor.
PASS_ICON = {
    "lift": '<rect x="6" y="9" width="12" height="11" rx="1"/><path d="M12 2v7M9 5l3-3 3 3M9 14h6"/>',
    "elevator": '<rect x="5" y="2" width="14" height="20" rx="1.5"/><path d="M9 9.5l3-3 3 3M9 14.5l3 3 3-3"/>',
    "stairs": '<path d="M3 20h4v-4h4v-4h4v-4h4V4"/>',
    "deep": '<circle cx="12" cy="12" r="9"/><path d="M6 15h3v-3h3v-3h3V7"/>',
    "extract": '<rect x="6" y="11" width="12" height="9" rx="1"/><path d="M12 2v9M8 6l4-4 4 4M3 8l-1 1M21 8l1 1"/>',
    "shaft": '<circle cx="12" cy="12" r="9" stroke-dasharray="3 2.5"/><path d="M12 7v10M8.5 13.5 12 17l3.5-3.5"/>',
    "fuel": '<path d="M5 21V5a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v16M5 21h10M7 7h6v4H7zM15 9h2a2 2 0 0 1 2 2v6a1.5 1.5 0 0 0 3 0V9l-2.5-2.5"/>',
    "gate": '<path d="M4 20V9l8-5 8 5v11M9 20v-7h6v7M3 20h18"/>',
    # Lugares (2026-10-23): tiendas, taller de motos, puesto VDI, casa, excavacion VDI, coto de caza.
    "shop": '<path d="M3 9h18l-2-5H5ZM3 9c0 2 4 2 4.5 0 .5 2 4.5 2 4.5 0 0 2 4 2 4.5 0 .5 2 4.5 2 4.5 0M5 11v9h14v-9M10 20v-5h4v5"/>',
    "bike": '<circle cx="5.5" cy="16" r="3.5"/><circle cx="18.5" cy="16" r="3.5"/><path d="M5.5 16 9 9h6l3.5 7M9 9 7.5 6H5M15 9l-1.5-3h3M12 16l3-7"/>',
    "vdi": '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
    "house": '<path d="M3 11 12 4l9 7M5 9.5V20h14V9.5M10 20v-6h4v6"/>',
    "excavation": '<rect x="6.5" y="2" width="11" height="12" rx="2"/><path d="M6.5 6h11M6.5 10h11M9 14l3 8 3-8M10.5 17h3"/>',
    "hunt": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4"/><circle cx="12" cy="12" r="5"/>',
}
SITE_COLOR = {"shop": "#e2c88f", "bike": "#6fb3ac", "vdi": "#d39a4b", "house": "#00ff41", "excavation": "#d39a4b", "hunt": "#d9614f"}
# Geometria de presentacion de esta pagina (coordenadas 0..1 del arte): punto de cada pasaje vertical cuando el dato
# no lo fija (sin exit_at y sin apilado directo), desvios de tuneles del mismo nivel y radios de camara (px) de los
# mapas apilados. El dato del juego no cambia por esto.
# El elevador del Pozo 3 (2026-10-13) toma el punto del crater de Shaft 3 en el arte, el de la vieja escalera Threshold-Scarp.
# Punto del pozo del elevador Shaft 3: el castillete pintado en la Scarp (el dato no trae punto para un elevador). Ningun
# otro pasaje se fija aca (2026-10-24): todos salen del dato (exit_at, marcador apilado), igual en cada nivel que unen.
VLINK_AT = {"elevator.shaft3": (0.468, 0.392)}
# Un pasaje vertical que cae sobre la marca de un mapa de ese nivel (pisos apilados: el pozo baja justo debajo de la
# entrada) se dibuja al costado de la marca, en px de pantalla (no en el plano): el punto del dato no se mueve.
PASS_SLOTS = [(28, 0), (-28, 0), (24, -26), (-24, -26)]
# Rotulos bajo tierra (2026-10-24): cada mapa prueba debajo (o su `label` del dato), a la derecha, a la izquierda y arriba,
# y se queda con el primer lugar que no pisa otra marca, un pasaje u otro rotulo de su nivel, medido con el zoom de
# entrada en escritorio (LABEL_U px del plano por px de pantalla). Las marcas no se mueven.
LABEL_U = 1.45
# 2026-10-24: en un telefono de 375 px las marcas se ven mas grandes respecto del plano (0.6 de escala sobre un visor de
# 341 px: 0.6 * 1312 / 341 px del plano por px de pantalla); el rotulo busca un lugar libre en las dos escalas.
LABEL_U_PHONE = 2.31
# Entradas pintadas en el arte (2026-10-12, pintura sin rotulos): el pozo de C-3 se ve en la superficie pero el mapa
# vive bajo tierra; una marca chica "↓ nivel" sobre el pozo baja a esa capa. Shaft 3 ya es el elevador.
ENTRANCES = {"zone.excavation_c3": "left"}  # lado del rotulo
VIA = {"conn.threshold_shallows": (0.445, 0.36), "conn.shallows_c3": (0.325, 0.49),
       "conn.old_metro_shallows": None, "conn.abyss_c3_f3": (0.325, 0.80)}
# The Cinder Deep (2026-10-24): 22 deja su camara dentro de Frontier Road east, fuera de la celda de The Salt Pit.
CHAMBER_R = {"zone.threshold": 30, "zone.dragon_lair": 22, "zone.excavation_c3_f2": 52, "zone.excavation_c3_f3": 48,
             # 2026-10-23: el sotano inundado es chico; las guaridas de cuatro pisos, una camara por nivel.
             "zone.floodlands_cellar": 30, **{f"zone.castoff_hideout_f{i}": 36 for i in range(1, 5)},
             **{f"zone.robot_hideout_f{i}": 40 for i in range(1, 5)}}
CHAMBER_SHRINK = 0.6
UNDER_FILL = {-1: .10, -2: .14, -3: .18, -4: .21}


def L_(d, lang):
    return d[lang] if isinstance(d, dict) else d


def e(s):
    return html.escape(str(s), quote=True)


def load():
    if not os.path.exists(PATH):
        return None
    return json.load(open(PATH))


def icon_svg(kind, cls="wm-ico", table=None):
    table = table or KIND_ICON
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{table[kind]}</svg>')


def glyph(kind, size, table=None, cls="wm-glyph"):
    """Glifo de 24x24 escalado a `size` px, centrado en el origen."""
    k = size / 24
    paths = (table or KIND_ICON)[kind].replace("<path", f'<path class="{cls}"').replace("<rect", f'<rect class="{cls}"').replace("<circle", f'<circle class="{cls}"')
    return f'<g transform="translate({-size / 2:.1f},{-size / 2:.1f}) scale({k:.4f})">{paths}</g>'


def _region():
    p = os.path.join(ROOT, "data", "starting_region.json")
    return json.load(open(p)) if os.path.exists(p) else {"transitions": [], "floors": [], "elevators": []}


# --- Lugares de servicio (Fases 3-7, 2026-10-23) ---------------------------------------------------------------
# Todo sale del dato: tiendas (data/shops/*.json: el dueño y su posicion en el piso), taller de motos (la tienda que vende
# vehiculos), puesto VDI (la que vende el Expedition Service), la casa (la puerta con "house" en las transiciones) y el
# claro de excavaciones VDI (el cartel "VDI SURVEY CLEARING"). Posiciones locales del piso (x, z en metros).
SITE_KIND = {"shop": L("Trader", "Comerciante"), "bike": L("Bike shop · crane", "Taller de motos · grúa"),
             "vdi": L("VDI post · Expedition Service", "Puesto VDI · Expedition Service"), "house": L("Your house · container home", "Tu casa · contenedor"),
             "excavation": L("VDI excavation clearing · call-outs", "Claro de excavaciones VDI · llamadas")}
SITE_KIND_HUNT = L("Hunting ground", "Coto de caza")


def is_hunting(z, region=None):
    """Coto de caza: un bloque "hunting" en el mapa, o un mapa salvaje / "hunting spot" con grupos de aparicion."""
    if z.get("hunting"):
        return True
    region = region or _region()
    spawns = any(g.get("zone_id") == z["id"] for g in region.get("spawn_groups", []))
    return spawns and (z["kind"] == "wild" or "hunting" in (z.get("subtitle") or {}).get("en", "").lower())


def site_mark(kind, tip, extra=""):
    """Icono de un lugar en px de pantalla (dentro de un grupo wm-sc): disco, glifo del color del lugar y su tooltip."""
    col = SITE_COLOR[kind]
    return (f'<g class="wm-site k-{kind}" data-tip="{e(tip)}"{extra}><circle class="wm-hit" r="13"/>'
            f'<circle r="10.5" fill="rgba(11,13,12,.94)" stroke="{col}" stroke-width="1.4"/>'
            f'<g style="fill:none;stroke:{col};stroke-width:2.6;stroke-linecap:round;stroke-linejoin:round">{glyph(kind, 13, PASS_ICON, "wm-sg")}</g></g>')


def sites(region=None):
    region = region or _region()
    shops = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "shops", "*.json"))):
        shops.update(json.load(open(f)).get("shops", {}))
    speakers = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "dialog", "*.json"))):
        speakers.update(json.load(open(f)).get("speakers", {}))
    people = {w["id"]: (f["zone_id"], w["position"]) for f in region["floors"] for w in f.get("workers", []) + f.get("npcs", [])}
    out = []
    for sid, sh in shops.items():
        if sid not in people or sh.get("property"):
            continue  # el agente de casas no es una tienda: la casa se marca en su puerta
        goods = [g["item"] for g in sh.get("goods", [])]
        kind = "bike" if sh.get("vehicles") else ("vdi" if "item.service.expedition_service" in goods else "shop")
        raw = speakers.get(sid, {}).get("name", sid)
        name = " · ".join(" ".join(w if w in ("VDI",) else w[:1] + w[1:].lower() for w in part.split()) for part in raw.split("·") if part.strip())
        zid, pos = people[sid]
        out.append({"kind": kind, "zone": zid, "pos": pos, "id": sid, "name": name})
    anchors = {f["zone_id"]: f.get("anchor", [0, 0, 0]) for f in region["floors"]}
    for t in region.get("transitions", []):
        if t.get("house") and t["from_zone"] in anchors:
            a = anchors[t["from_zone"]]
            out.append({"kind": "house", "zone": t["from_zone"], "pos": [t["position"][0] - a[0], t["position"][2] - a[2]], "id": t["house"], "name": t["label"]})
    for f in region["floors"]:
        for sg in f.get("signs", []):
            if sg["text"].startswith("VDI SURVEY CLEARING"):
                out.append({"kind": "excavation", "zone": f["zone_id"], "pos": [sg["position"][0], sg["position"][2]], "id": "vdi.clearing." + f["zone_id"],
                            "name": sg["text"].split("\n")[0]})
    return out


SITES_ALL = sites()


# --- Continente, por niveles ---------------------------------------------------------------------
class World:
    """Vista del grafo preparada para dibujar: niveles, anclas, camaras, pasajes verticales."""

    def __init__(self, data, lang):
        self.d, self.lang = data, lang
        self.W, self.H = data["image"]["width"], data["image"]["height"]
        self.zones = {z["id"]: z for z in data["zones"]}
        self.conns = {c["id"]: c for c in data["connections"]}
        region = _region()
        self.trans = {t["entity_id"]: t for t in region["transitions"]}
        self.floors = {f["zone_id"]: f for f in region["floors"]}
        self.journey = next((r for r in data.get("routes", []) if r["id"] == "route.first_journey"), None)
        self.jconns = set(self.journey["connections"]) if self.journey else set()
        self.steps = {zid: i for i, zid in enumerate(self.journey["zones"])} if self.journey else {}
        self.entrances = {g["connection"]: g for g in data.get("dustline", {}).get("entrances", [])}
        # Elevadores de varias paradas: los pisos del dato de la region, en el orden del pozo (de arriba hacia abajo).
        used = {c.get("elevator") for c in data["connections"] if c["kind"] == "elevator"}
        self.elevators = [dict(el, floors=sorted(el["floors"], key=lambda f: -self.level(f["zone"])),
                               status="playable" if all(c["status"] == "playable" for c in data["connections"] if c.get("elevator") == el["id"]) else "planned")
                          for el in region.get("elevators", []) if el["id"] in used]

    def elevator_name(self, el):
        return L_(ELEVATOR_NAME.get(el["id"], el.get("label", el["id"]).capitalize()), self.lang)

    def level(self, zid):
        z = self.zones[zid]
        return z.get("level", 0 if z["layer"] == "surface" else -1)

    def anchor(self, z):
        # Un mapa apilado va en su marcador apilado (bajo la entrada), aunque traiga un `marker` suelto de antes.
        p = (z["stack"]["marker"] if z.get("stack") else None) or z.get("marker") or z["cell"]["seed"]
        return p[0] * self.W, p[1] * self.H

    def px(self, uv):
        return uv[0] * self.W, uv[1] * self.H

    def chamber(self, z):
        """Poligono (px) de un mapa subterraneo: su celda encogida hacia el ancla, o un poligono irregular alrededor del marcador apilado."""
        ax, ay = self.anchor(z)
        if z.get("cell"):
            return [(ax + (x * self.W - ax) * CHAMBER_SHRINK, ay + (y * self.H - ay) * CHAMBER_SHRINK) for x, y in z["cell"]["polygon"]]
        r = CHAMBER_R.get(z["id"], 40)
        rnd = random.Random(z["id"])
        n = 9
        return [(ax + r * rnd.uniform(.82, 1.12) * math.cos(2 * math.pi * i / n + rnd.uniform(-.12, .12)),
                 ay + r * .78 * rnd.uniform(.82, 1.12) * math.sin(2 * math.pi * i / n + rnd.uniform(-.12, .12))) for i in range(n)]

    def vlink_point(self, c):
        """Punto (px) de un pasaje vertical: la salida del borde si la hay, el marcador del mapa apilado bajo el otro, o un punto fijado aca."""
        if c["id"] in VLINK_AT:
            return self.px(VLINK_AT[c["id"]])
        if c.get("exit_at"):
            return self.px(c["exit_at"])
        a, b = (self.zones[x["zone"]] for x in c["ends"])
        for lower, upper in ((a, b), (b, a)):
            if lower.get("stack") and lower["stack"]["parent"] == upper["id"]:
                return self.anchor(lower)
        ax, ay = self.anchor(a)
        bx, by = self.anchor(b)
        return (ax + bx) / 2, (ay + by) / 2

    def vertical(self):
        """Pasajes que cambian de nivel: conexiones entre niveles distintos y la extraccion de solo ida (los elevadores aparte)."""
        out = []
        for c in self.d["connections"]:
            if c["kind"] == "elevator":
                continue
            la, lb = (self.level(x["zone"]) for x in c["ends"])
            if la != lb:
                out.append(("conn", c))
        for z in self.d["zones"]:
            ex = z.get("extraction")
            if ex and self.level(z["id"]) != self.level(ex["zone"]):
                out.append(("extraction", {"id": "extraction." + z["id"], "kind": "lift", "status": z["status"], "one_way": True,
                                           "ends": [{"zone": z["id"], "exit": ex["exit"], "transition": ex["transition"]},
                                                    {"zone": ex["zone"], "exit": ex["exit"], "arrival": True}]}))
        return out

    def pres(self, tid):
        t = self.trans.get(tid)
        return (t or {}).get("presentation") or ""

    def pass_kind(self, c, end):
        """Icono del pasaje visto desde `end`: galeria, pozo profundo, extraccion, o por la presentacion real del juego."""
        if c.get("one_way"):
            return "extract"
        if c["kind"] == "elevator":
            return "elevator"
        if c["id"] == "conn.c3_f2":
            return "deep"
        if c["status"] != "playable":
            return "shaft"
        p = self.pres(end.get("transition"))
        return p if p in ("lift", "stairs") else "lift"


def pres_name(p, lang):
    return L_({"tunnel": L("Tunnel", "Túnel"), "lift": L("Lift", "Elevador"), "stairs": L("Stairs", "Escaleras"),
               "gate": L("Gate", "Puerta"), "road": L("Road", "Camino"), "elevator": L("Elevator", "Elevador"),
               "deep": L("Deep shaft", "Pozo profundo"), "extract": L("Extraction lift", "Elevador de extracción"),
               "shaft": L("Shaft", "Pozo")}.get(p, L("Passage", "Pasaje")), lang)


def level_text(lv, lang, depth=None):
    if lv == 0:
        return L_(T["surface"], lang)
    return (f"−{depth} m" if depth else L_(LEVEL_NAME[lv], lang))


def poly_d(pts):
    return "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z"


def rock_defs(W, H):
    """Patrones: trama para lo planeado / lo de abajo, y una roca con vetas para el fondo subterraneo."""
    rnd = random.Random(31)
    veins = []
    for _ in range(9):
        x, y = rnd.uniform(0, 220), rnd.uniform(0, 220)
        d = f"M{x:.0f},{y:.0f}"
        for _ in range(5):
            x += rnd.uniform(-45, 45)
            y += rnd.uniform(-45, 45)
            d += f"L{x:.0f},{y:.0f}"
        veins.append(f'<path d="{d}" stroke-opacity="{rnd.uniform(.12, .3):.2f}"/>')
    dots = "".join(f'<circle cx="{rnd.uniform(0, 220):.0f}" cy="{rnd.uniform(0, 220):.0f}" r="{rnd.uniform(.6, 1.8):.1f}"/>' for _ in range(40))
    return ('<defs><pattern id="wm-hatch" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><path d="M0 0v9" class="wm-hatch-l"/></pattern>'
            '<pattern id="wm-hatch2" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(-35)"><path d="M0 0v7" class="wm-hatch-l2"/></pattern>'
            f'<pattern id="wm-rock" width="220" height="220" patternUnits="userSpaceOnUse"><g class="wm-veins">{"".join(veins)}</g><g class="wm-grains">{dots}</g></pattern>'
            '<filter id="wm-feather" x="-30%" y="-60%" width="160%" height="220%"><feGaussianBlur stdDeviation="7"/></filter>'
            '<radialGradient id="wm-cavelight"><stop offset="0" stop-color="#5468c0" stop-opacity=".16"/><stop offset="1" stop-color="#5468c0" stop-opacity="0"/></radialGradient></defs>')


def curve_d(ax, ay, bx, by, exit_pt=None, via=None):
    if exit_pt:
        ex, ey = exit_pt
        cx, cy = 2 * ex - (ax + bx) / 2, 2 * ey - (ay + by) / 2
        return f"M{ax:.1f},{ay:.1f}Q{cx:.1f},{cy:.1f} {bx:.1f},{by:.1f}"
    if via:
        vx, vy = via
        cx, cy = 2 * vx - (ax + bx) / 2, 2 * vy - (ay + by) / 2
        return f"M{ax:.1f},{ay:.1f}Q{cx:.1f},{cy:.1f} {bx:.1f},{by:.1f}"
    return f"M{ax:.1f},{ay:.1f}L{bx:.1f},{by:.1f}"


def sc(cls, x, y, inner, extra=""):
    """Grupo en px de pantalla: el JS le aplica scale(1/zoom) (wm-sc)."""
    return f'<g class="wm-sc {cls}" data-x="{x:.1f}" data-y="{y:.1f}" transform="translate({x:.1f},{y:.1f})"{extra}>{inner}</g>'


def layer_svg(w, lv, lang):
    """Una capa: fondo (bajo tierra), fantasmas de arriba y de abajo, celdas/camaras, enlaces del nivel, pasajes verticales, marcas."""
    W, H = w.W, w.H
    zs = [z for z in w.d["zones"] if w.level(z["id"]) == lv]
    under = lv < 0
    out = []
    # Fondo de roca con vetas y tinte de caverna (el arte se apaga por CSS).
    if under:
        out.append(f'<rect class="wm-dark" width="{W}" height="{H}"/><rect class="wm-rock" width="{W}" height="{H}" fill="url(#wm-rock)"/><rect class="wm-tint" width="{W}" height="{H}" fill="#5468c0" fill-opacity="{UNDER_FILL[lv]:.2f}"/>')
        for z in zs:
            if z["status"] == "playable":
                ax, ay = w.anchor(z)
                out.append(f'<circle cx="{ax:.0f}" cy="{ay:.0f}" r="150" fill="url(#wm-cavelight)"/>')
    # Fantasmas de arriba: la superficie siempre (contorno), y las camaras del nivel inmediatamente superior.
    ghosts_above = []
    if under:
        for z in w.d["zones"]:
            if w.level(z["id"]) == 0 and z.get("cell"):
                ghosts_above.append(f'<path class="wm-ghost up surface" d="{poly_d([w.px(p) for p in z["cell"]["polygon"]])}"/>')
        if lv < -1:
            for z in w.d["zones"]:
                if w.level(z["id"]) == lv + 1:
                    ghosts_above.append(f'<path class="wm-ghost up" d="{poly_d(w.chamber(z))}"/>')
    # Fantasmas de abajo: camaras del nivel siguiente, trama tenue; tocarlas baja.
    ghosts_below = []
    if lv > LEVELS[-1]:
        for z in w.d["zones"]:
            if w.level(z["id"]) == lv - 1:
                ghosts_below.append(f'<path class="wm-ghost down s-{z["status"]}" d="{poly_d(w.chamber(z))}" data-ghost="{z["id"]}" data-tip="{e(z["name"])} · {e(L_(LEVEL_NAME[lv - 1], lang))}"/>')
    covers = []
    if lv == 0:
        for zid, side in ENTRANCES.items():
            z = w.zones[zid]
            ax, ay = w.anchor(z)
            lvz = w.level(zid)
            txt = f"↓ {lvz}"
            lab = (f'<text class="wm-below-label" x="-17" y="4" text-anchor="end">{e(txt)}</text>' if side == "left"
                   else f'<text class="wm-below-label" x="17" y="4">{e(txt)}</text>')
            covers.append(sc("wm-below", ax, ay, f'<circle class="wm-hit" r="16"/><rect class="wm-vl-bg" x="-11" y="-11" width="22" height="22" rx="4"/>{glyph("dungeon", 14)}{lab}', f' data-ghost="{zid}" data-tip="{e(z["name"])} · {e(L_(LEVEL_NAME[lvz], lang))} · −{z.get("depth_m", 0)} m"'))
    out.append(f'<g class="wm-ghosts-up">{"".join(ghosts_above)}</g><g class="wm-entrances">{"".join(covers)}</g><g class="wm-ghosts-down">{"".join(ghosts_below)}</g>')
    # Celdas (superficie) o camaras (bajo tierra)
    cells = []
    for z in sorted(zs, key=lambda z: z["status"] == "playable"):
        pts = [w.px(p) for p in z["cell"]["polygon"]] if (z.get("cell") and not under) else w.chamber(z)
        cells.append(f'<path class="wm-cell s-{z["status"]}{" u-cell" if under else ""}" d="{poly_d(pts)}" data-id="{z["id"]}" style="--tint:{BIOME_COLOR[z["biome"]]}">'
                     f'<title>{e(z["name"])}</title></path>')
    out.append(f'<g class="wm-cells">{"".join(cells)}</g>')
    # Enlaces del mismo nivel
    links, pips, midicons, jsegs = [], [], [], []
    for c in w.d["connections"]:
        za, zb = (w.zones[x["zone"]] for x in c["ends"])
        if w.level(za["id"]) != lv or w.level(zb["id"]) != lv or c["kind"] == "elevator":
            continue
        ax, ay = w.anchor(za)
        bx, by = w.anchor(zb)
        ex = w.px(c["exit_at"]) if "exit_at" in c else None
        d = curve_d(ax, ay, bx, by, ex, VIA.get(c["id"]) and w.px(VIA[c["id"]]))
        kind = c["kind"]
        pres = w.pres(c["ends"][0].get("transition")) if c["status"] == "playable" else ""
        cls = f'wm-link k-{kind} s-{c["status"]}' + (" p-tunnel" if pres == "tunnel" else "") + (" is-journey" if c["id"] in w.jconns else "")
        links.append(f'<path class="{cls}" d="{d}" data-conn="{c["id"]}"/>')
        if c["id"] in w.jconns:
            jsegs.append(d)
        if ex and kind == "road":
            gate = w.entrances.get(c["id"])
            if gate:
                closed = gate["kind"] != "main_gate" and c["status"] != "playable"
                tip = L_(gate["name"], lang).upper() + (" · " + L_(T["closed"], lang) if closed else "")
                pips.append(sc(f'wm-pip wm-gate s-{c["status"]}{" closed" if closed else ""}', ex[0], ex[1],
                               f'<circle class="wm-gate-bg" r="10"/>{glyph("gate", 13, PASS_ICON)}' + ('<path class="wm-gate-x" d="M-4-4 4 4M4-4-4 4"/>' if closed else ""),
                               f' data-tip="{e(tip)}" data-id="{za["id"] if za["kind"] == "city" else zb["id"]}"'))
            else:
                pips.append(sc(f'wm-pip s-{c["status"]}', ex[0], ex[1], '<rect x="-3.5" y="-3.5" width="7" height="7" transform="rotate(45)"/>'))
        if kind in ("lift", "shaft") and not ex:
            # Elevador o pozo dentro del mismo nivel (hoy ninguno): icono en el medio del tramo.
            mx, my = ax + (bx - ax) * .62, ay + (by - ay) * .62
            if VIA.get(c["id"]):
                vx, vy = w.px(VIA[c["id"]])
                mx, my = (mx + vx) / 2, (my + vy) / 2
            k = w.pass_kind(c, c["ends"][0])
            end = c["ends"][0]
            tip = f'{end["exit"]} · {pres_name(k, lang)}'
            midicons.append(sc(f'wm-vl same k-{k} s-{c["status"]}', mx, my, f'<circle class="wm-vl-bg" r="11"/>{glyph(k, 14, PASS_ICON)}', f' data-tip="{e(tip)}"'))
    out.append(f'<g class="wm-links">{"".join(links)}</g>')
    if jsegs:
        jd = " ".join(jsegs)
        out.append(f'<path class="wm-journey-glow" d="{jd}"/><path class="wm-journey" d="{jd}"/>')
    # Pasajes verticales que tocan este nivel: marcados en ambos niveles en el mismo punto; tocar cambia de nivel.
    vls, stubs = [], []
    badges_here = [w.anchor(z) for z in zs]
    slot_used = {}
    pass_pts = []
    icons = []  # pasajes dibujados en este nivel: (x, y del punto en px del plano, ox, oy en px de pantalla)
    boxes = []  # otras cajas ocupadas (rotulos de pasajes): (x, y, x0, y0, x1, y1), caja en px de pantalla desde el punto

    def slot(x, y, first=0):
        """Desvio en px de pantalla si (x, y) cae sobre la marca de un mapa de este nivel; si no, ninguno. `first`: lado
        preferido (el elevador, a la izquierda: su rotulo corre hacia afuera)."""
        hit = next((i for i, (bx, by) in enumerate(badges_here) if math.hypot(bx - x, by - y) < 16), None)
        if hit is None:
            # Dos pasajes en el mismo punto sin marca (p. ej. el pozo de C-3 y la llegada de la extraccion): el primero
            # queda en el punto, los siguientes al costado.
            pt = next((i for i, (px_, py_) in enumerate(pass_pts) if math.hypot(px_ - x, py_ - y) < 16), None)
            if pt is None:
                pass_pts.append((x, y))
                return 0, 0
            n = slot_used.get(("p", pt), 0)
            slot_used[("p", pt)] = n + 1
            return PASS_SLOTS[(n + first) % len(PASS_SLOTS)]
        n = slot_used.get(hit, 0)
        slot_used[hit] = n + 1
        return PASS_SLOTS[(n + first) % len(PASS_SLOTS)]
    for src, c in w.vertical():
        for i, end in enumerate(c["ends"]):
            if w.level(end["zone"]) != lv:
                continue
            other = c["ends"][1 - i]
            to_lv = w.level(other["zone"])
            x, y = w.vlink_point(c)
            k = w.pass_kind(c, end)
            down = to_lv < lv
            oz = w.zones[other["zone"]]
            dep = oz.get("depth_m", 0)
            where = (L_(T["to_level"], lang) if to_lv == 0 else L_(T["m_down"], lang).format(m=dep))
            if end.get("arrival"):
                tip = f'{end["exit"]} · {L_(T["arrives"], lang)} {oz["name"]} · {L_(T["one_way"], lang)}'
            else:
                tip = f'{end["exit"]} · {pres_name(k, lang)} · {where}' + (f' · {L_(T["one_way"], lang)}' if c.get("one_way") else "") + \
                      (f' · {L_(T["planned_passage"], lang)}' if c["status"] != "playable" else "")
            journey = c["id"] in w.jconns
            label = ""
            if journey:
                txt = L_(T["to_surface"], lang) if to_lv > lv else L_(T["from_below"], lang)
                label = (f'<text class="wm-vl-label" x="-18" y="4" text-anchor="end">{e(txt)}</text>' if down
                         else f'<text class="wm-vl-label" x="18" y="4">{e(txt)}</text>')
            arrow = '<path class="wm-vl-arrow" d="M0-3v6M-2.2 1 0 3.2 2.2 1"/>' if down else '<path class="wm-vl-arrow" d="M0 3v-6M-2.2-1 0-3.2 2.2-1"/>'
            ox, oy = slot(x, y)
            icons.append((x, y, ox, oy))
            icon = (f'<circle class="wm-hit" r="18"/><rect class="wm-vl-bg" x="-12" y="-12" width="24" height="24" rx="4"/>{glyph(k, 15, PASS_ICON)}'
                    f'<g transform="translate(10,-10)"><circle class="wm-vl-dot" r="5.5"/>{arrow}</g>{label}')
            if ox or oy:
                icon = f'<path class="wm-vl-tie" d="M0,0L{ox * .55:.1f},{oy * .55:.1f}"/><g transform="translate({ox},{oy})">{icon}</g>'
            vls.append(sc(f'wm-vl k-{k} s-{c["status"]} dir-{"down" if down else "up"}{" is-journey" if journey else ""}', x, y, icon,
                          f' data-vlink="{c["id"]}" data-from="{end["zone"]}" data-to="{other["zone"]}" data-to-level="{to_lv}" data-tip="{e(tip)}"'))
            ax, ay = w.anchor(w.zones[end["zone"]])
            if math.hypot(ax - x, ay - y) > 16:
                stubs.append(f'<path class="wm-stub s-{c["status"]}" d="M{ax:.1f},{ay:.1f}L{x:.1f},{y:.1f}"/>')
    # Elevadores de varias paradas: un solo pozo en el mismo punto del plano, marcado en cada piso que sirve. La marca lleva
    # la columna de paradas (la de este piso encendida); tocar la marca va a la parada de abajo (o a la de arriba desde el
    # fondo) y tocar una parada de la columna va directo a ese piso.
    for el in w.elevators:
        floors = el["floors"]
        here = next((i for i, f in enumerate(floors) if w.level(f["zone"]) == lv), None)
        if here is None:
            continue
        x, y = w.px(VLINK_AT[el["id"]]) if el["id"] in VLINK_AT else w.anchor(w.zones[floors[0]["zone"]])
        name = w.elevator_name(el)
        cid = next((c["id"] for c in w.d["connections"] if c.get("elevator") == el["id"]), el["id"])
        journey = any(c["id"] in w.jconns for c in w.d["connections"] if c.get("elevator") == el["id"])

        def stop_txt(f):
            z = w.zones[f["zone"]]
            flv = w.level(f["zone"])
            return f'{z["name"]} ({L_(T["surface"], lang).lower() if flv == 0 else str(flv).replace("-", "−")})'
        stops = " · ".join(stop_txt(f) for f in floors)
        tip = f'{name.upper()} · {L_(T["stops"], lang)}: {stops}' + (f' · {L_(T["planned_passage"], lang)}' if el["status"] != "playable" else "")
        nxt = floors[here + 1] if here + 1 < len(floors) else floors[here - 1]
        to_lv = w.level(nxt["zone"])
        n = len(floors)
        gap = 9
        col = [f'<path class="wm-el-shaft" d="M22,{-(n - 1) * gap / 2:.1f}V{(n - 1) * gap / 2:.1f}"/>']
        for i, f in enumerate(floors):
            fy = -(n - 1) * gap / 2 + i * gap
            flv = w.level(f["zone"])
            if i == here:
                col.append(f'<circle class="wm-el-stop is-here" cx="22" cy="{fy:.1f}" r="3.6"/>')
            else:
                col.append(f'<g class="wm-el-go" data-vlink="{el["id"]}" data-from="{floors[here]["zone"]}" data-to="{f["zone"]}" data-to-level="{flv}" '
                           f'data-tip="{e(name.upper())} · {e(stop_txt(f))}"><circle class="wm-hit" cx="22" cy="{fy:.1f}" r="6"/>'
                           f'<circle class="wm-el-stop" cx="22" cy="{fy:.1f}" r="3.2"/></g>')
        label = f'<text class="wm-vl-label" x="-18" y="4" text-anchor="end">{e(name.upper())}</text>' if journey else ""
        icon = (f'<circle class="wm-hit" r="18"/><rect class="wm-vl-bg" x="-12" y="-12" width="24" height="24" rx="4"/>{glyph("elevator", 15, PASS_ICON)}'
                f'{"".join(col)}{label}')
        ox, oy = slot(x, y, first=1)
        icons.append((x, y, ox, oy))
        if journey:  # rotulo del elevador, a la izquierda del icono
            boxes.append((x, y, ox - (20 + len(name) * 7.2), oy - 8, ox - 16, oy + 6))
        if ox or oy:
            icon = f'<path class="wm-vl-tie" d="M0,0L{ox * .55:.1f},{oy * .55:.1f}"/><g transform="translate({ox},{oy})">{icon}</g>'
        vls.append(sc(f'wm-vl wm-elevator k-elevator s-{el["status"]} dir-{"down" if to_lv < lv else "up"}{" is-journey" if journey else ""}', x, y,
                      icon,
                      f' data-vlink="{el["id"]}" data-conn="{cid}" data-from="{floors[here]["zone"]}" data-to="{nxt["zone"]}" data-to-level="{to_lv}" data-tip="{e(tip)}"'))
        ax, ay = w.anchor(w.zones[floors[here]["zone"]])
        if math.hypot(ax - x, ay - y) > 16:
            stubs.append(f'<path class="wm-stub s-{el["status"]}" d="M{ax:.1f},{ay:.1f}L{x:.1f},{y:.1f}"/>')
    out.append(f'<g class="wm-stubs">{"".join(stubs)}</g>')
    # Surtidor de Frontier Road: sobre el camino, justo antes de la puerta.
    extras = []
    if lv == 0:
        for zid, fl in w.floors.items():
            for st in fl.get("fuel_stations", []):
                gate_c = next((c for c in w.d["connections"] if "exit_at" in c and w.entrances.get(c["id"]) and any(x["zone"] == zid for x in c["ends"])), None)
                if not gate_c:
                    continue
                gx, gy = w.px(gate_c["exit_at"])
                ax, ay = w.anchor(w.zones[zid])
                fx, fy = gx + (ax - gx) * .3, gy + (ay - gy) * .3
                tip = f'{st["name"]} · {L_(T["fuel"], lang)} · {st["price_per_litre"]} Metal/L'
                extras.append(sc("wm-fuel", fx, fy, f'<circle class="wm-hit" r="14"/><circle class="wm-vl-bg" r="10"/>{glyph("fuel", 13, PASS_ICON)}', f' data-tip="{e(tip)}" data-id="{zid}"'))
    # Lugares (2026-10-23): el claro de excavaciones VDI junto a su mapa y la mira de los cotos de caza.
    region = _region()
    for z in zs:
        if z["status"] != "playable":
            continue
        x, y = w.anchor(z)
        if is_hunting(z, region):
            note = L_(z["hunting"]["note"], lang) if z.get("hunting", {}).get("note") else L_(SITE_KIND_HUNT, lang)
            extras.append(sc("wm-sites", x, y, f'<g transform="translate(-21,-15)">{site_mark("hunt", note)}</g>'))
        for st in [t for t in SITES_ALL if t["zone"] == z["id"] and t["kind"] == "excavation"]:
            extras.append(sc("wm-sites", x, y, f'<g transform="translate(22,-16)">{site_mark("excavation", L_(SITE_KIND["excavation"], lang) + " · " + L_(T["l_bore"], lang))}</g>'))
    # Marcas propias y de arte, etiquetas, pasos del viaje
    marks, badges = [], []
    # Cajas ocupadas (x, y, x0, y0, x1, y1): punto en px del plano y caja en px de pantalla desde el punto; en el plano
    # miden U veces eso (LABEL_U en escritorio, LABEL_U_PHONE en un telefono).
    placed = []
    for z in zs:
        ax_, ay_ = w.anchor(z)
        placed.append((ax_, ay_, -11, -11, 11, 11))
    placed += [(ix, iy, ox - 12, oy - 12, ox + 12, oy + 12) for ix, iy, ox, oy in icons] + boxes
    for z in zs:  # pasos del viaje (insignia a 13,-15 de la marca)
        if z["id"] in w.steps:
            ax_, ay_ = w.anchor(z)
            placed.append((ax_, ay_, 4, -24, 22, -6))

    def place_label(z, x, y, r, sub, lab):
        """(x, y, text-anchor) del rotulo en unidades de la marca: el primer lugar libre (ver LABEL_U)."""
        wd = max(len(z["name"]) * 7.6, len(sub) * 6.9)  # dos renglones: nombre, y debajo piso y profundidad
        cands = []
        if lab and math.hypot(lab[0] * W - x, lab[1] * H - y) >= 18:
            cands.append(((lab[0] * W - x) / LABEL_U, (lab[1] * H - y) / LABEL_U + 4, "middle"))
        cands += [(0, r + 15, "middle"), (r + 7, 0, "start"), (-(r + 7), 0, "end"), (0, -(r + 19), "middle")]
        # Mas afuera (pasando la columna de pasajes al costado de la marca), por si los cuatro lados estan ocupados.
        cands += [(r + 33, 0, "start"), (-(r + 33), 0, "end"), (0, r + 41, "middle"), (0, -(r + 45), "middle")]

        def box(c):
            cx, cy, a = c
            x0 = cx - wd / 2 if a == "middle" else (cx if a == "start" else cx - wd)
            return (x, y, x0, cy - 10, x0 + wd, cy + 15)

        def px(q, U):
            return (q[0] + q[2] * U, q[1] + q[3] * U, q[0] + q[4] * U, q[1] + q[5] * U)

        def hits(b, U):
            b = px(b, U)
            out_ = (max(0, -b[0]) + max(0, b[2] - W)) * (b[3] - b[1]) + (max(0, -b[1]) + max(0, b[3] - H)) * (b[2] - b[0])  # fuera del mapa
            return out_ + sum(max(0, min(b[2], q[2]) - max(b[0], q[0])) * max(0, min(b[3], q[3]) - max(b[1], q[1]))
                       for q in (px(q_, U) for q_ in placed if not (q_[0] == x and q_[1] == y and q_[2:] == (-11, -11, 11, 11))))

        # Primero un lugar libre en escritorio y en telefono (en orden); si no hay, el que menos pisa sumando las dos
        # escalas en px de pantalla.
        def key(c):
            hd, hp = hits(box(c), LABEL_U), hits(box(c), LABEL_U_PHONE)
            return (hd + hp > 0, hd / LABEL_U ** 2 + hp / LABEL_U_PHONE ** 2, cands.index(c))
        best = min(cands, key=key)
        placed.append(box(best))
        return best
    for z in zs:
        x, y = w.anchor(z)
        step = w.steps.get(z["id"])
        if step is not None:
            badges.append(sc("wm-step", x, y, f'<g transform="translate(13,-15)"><circle r="8"/><text y="3.5">{step:02d}</text></g>'))
        # `art_icon` del dato ya no aplica (2026-10-12): la pintura nueva no trae iconos ni rotulos, todas las marcas son propias.
        r = 10 if under else 11
        shape = f'<circle class="wm-badge" r="{r}"/>'
        ico = glyph(z["kind"], 14)
        lab = None if z.get("stack") else z.get("label")  # un mapa apilado lleva el rotulo junto a su marca
        if lab and math.hypot(lab[0] * W - x, lab[1] * H - y) >= 18:
            lx, ly = lab[0] * W - x, lab[1] * H - y
            label = f'<text class="wm-label" x="{lx:.1f}" y="{ly + 4:.1f}" text-anchor="middle">{e(z["name"])}</text>'
        else:
            label = f'<text class="wm-label" y="{r + 15}" text-anchor="middle">{e(z["name"])}</text>'
        if under:
            dep = z.get("depth_m", 0)
            sub = (z.get("level_label", "") + " · " if z.get("level_label") else "") + f"−{dep} m"
            lx, ly, anchor = place_label(z, x, y, r, sub, lab)
            label = (f'<text class="wm-label" x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}">{e(z["name"])}'
                     f'<tspan class="wm-depth" x="{lx:.1f}" dy="12">{e(sub)}</tspan></text>')
        marks.append(sc(f'wm-mark own s-{z["status"]}{" under" if under else ""}', x, y, f'<circle class="wm-hit" r="{r + 9}"/>{shape}{ico}{label}', f' data-id="{z["id"]}"'))
    out.append(f'<g class="wm-pips">{"".join(pips)}</g><g class="wm-vlinks">{"".join(midicons)}{"".join(vls)}{"".join(extras)}</g>'
               f'<g class="wm-marks">{"".join(marks)}</g><g class="wm-badges">{"".join(badges)}</g>')
    return f'<g class="wm-layer{" is-active" if lv == 0 else ""}" data-level="{lv}"{"" if lv == 0 else " data-below"}>{"".join(out)}</g>'


def continent_svg(data, lang):
    w = World(data, lang)
    layers = "".join(layer_svg(w, lv, lang) for lv in LEVELS)
    return (f'<svg class="wm-svg" viewBox="0 0 {w.W} {w.H}" preserveAspectRatio="xMidYMid meet" role="group" aria-label="{e(L_(T["title"], lang))}">'
            f'{rock_defs(w.W, w.H)}{layers}</svg>')


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


# Lugares en el plano de Dustline (2026-10-23). El plano es estilizado y no coincide punto por punto con la ciudad
# construida (world_map.json "dustline.plan.note"), asi que cada lugar va al distrito o puerta cuyo cartel/paso esta mas
# cerca de su posicion en el piso, en una fila debajo del rotulo de ese distrito.
DISTRICT_SIGNS = {"CENTRAL MARKET": "district.central_market", "THE EXCHANGE": "district.the_exchange", "CARAVAN YARD": "district.caravan_yard",
                  "SCRAPPER'S ROW": "district.scrappers_row", "LOWER WARRENS": "district.lower_warrens"}
BILLBOARD_SUBS = {"your goods are safe with us"}


def city_anchors(data):
    """[(id, (x, z) local, (u, v) del plano, es_puerta)] para los distritos y las puertas de Dustline."""
    city = data["dustline"]
    region = _region()
    out = []
    st = os.path.join(ROOT, "data", "world", "sets", "dustline.json")
    signs = json.load(open(st)).get("signs", []) if os.path.exists(st) else []
    labels = {d["id"]: d["label"] for d in city["districts"]}
    for sg in signs:
        did = DISTRICT_SIGNS.get(sg["text"].split("\n")[0])
        if did and sg.get("sub") not in BILLBOARD_SUBS and did in labels:
            out.append((did, (sg["p"][0], sg["p"][2]), tuple(labels[did]), False))
    fl = next((f for f in region["floors"] if f["zone_id"] == city["zone"]), {})
    ax, _, az = fl.get("anchor", [0, 0, 0])
    conns = {c["id"]: c for c in data["connections"]}
    for g in city["entrances"]:
        c = conns.get(g["connection"])
        if not c:
            continue
        other = next(x["zone"] for x in c["ends"] if x["zone"] != city["zone"])
        t = next((t for t in region["transitions"] if t["from_zone"] == city["zone"] and t["to_zone"] == other), None)
        if t:
            out.append((g["id"], (t["position"][0] - ax, t["position"][2] - az), tuple(g["position"]), True))
    return out


def city_sites(data, lang):
    city = data["dustline"]
    anchors = city_anchors(data)
    if not anchors:
        return ""
    rows = {}
    for st in SITES_ALL:
        if st["zone"] != city["zone"]:
            continue
        best = min(anchors, key=lambda a: math.hypot(a[1][0] - st["pos"][0], a[1][1] - st["pos"][1]))
        rows.setdefault(best[0], (best, []))[1].append(st)
    out = []
    order = {"house": 0, "shop": 1, "bike": 2, "vdi": 3}
    for aid, (a, sts) in rows.items():
        sts.sort(key=lambda t: (order.get(t["kind"], 9), t["name"]))
        u, v = a[2]
        n = len(sts)
        gap = 25
        y0 = 58 if a[3] else 52  # debajo del rotulo del distrito (o de la puerta)
        extra = f' data-id="{aid}"'
        icons = "".join(f'<g transform="translate({(i - (n - 1) / 2) * gap:.1f},{y0})">'
                        f'{site_mark(t["kind"], t["name"] + " · " + L_(SITE_KIND[t["kind"]], lang), extra)}</g>'
                        for i, t in enumerate(sts))
        out.append(sc("wm-sites", u * CW, v * CH, icons))
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
            f'<polygon class="dl-wall" points="{wall}"/>{dist}{street_paths}{extras}{gates}{lms}{road_labels}{compass}{city_sites(data, lang)}</svg>')


# --- Datos para el JS y HTML de la seccion ------------------------------------------------------
PRES = {"tunnel": L("Tunnel", "Túnel"), "lift": L("Lift", "Elevador"), "stairs": L("Stairs", "Escaleras"),
        "gate": L("Gate", "Puerta"), "road": L("Road", "Camino")}


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
    # Lugares del dato (2026-10-23): tiendas, motos, VDI, casa, claro de excavaciones; y el coto de caza.
    here = [t for t in SITES_ALL if t["zone"] == zid]
    shops = [t["name"] for t in here if t["kind"] == "shop"]
    if shops:
        out.append(L_(L("Traders ({n}): ", "Comerciantes ({n}): "), lang).format(n=len(shops)) + ", ".join(shops))
    for t in here:
        if t["kind"] != "shop":
            out.append(f'{L_(SITE_KIND[t["kind"]], lang)} · {t["name"]}')
    z = next((z for z in load()["zones"] if z["id"] == zid), None)
    if z and is_hunting(z, region):
        out.append(L_(z["hunting"]["note"], lang) if z.get("hunting", {}).get("note") else L_(SITE_KIND_HUNT, lang))
    return out


def client_data(data, lang):
    w = World(data, lang)
    zones = w.zones
    region = _region()
    trans = w.trans
    hp = os.path.join(ROOT, "data", "world", "respawn_hubs.json")
    hubs = {h["zone_id"] for h in json.load(open(hp))["hubs"]} if os.path.exists(hp) else set()
    depths = level_depths(data)
    out = {"zones": {}, "districts": {}, "levels": {str(lv): {"name": L_(LEVEL_NAME[lv], lang), "band": level_band(lv, depths, lang), "m": level_m(lv, data)} for lv in LEVELS},
           "t": {k: L_(v, lang) for k, v in T.items() if k in (
               "biome", "danger", "tier", "status", "layer", "exits", "above", "below", "depth", "floor", "services", "open_city", "back_map", "step", "close",
               "district", "gate", "landmark", "planned_city", "wiki_page", "here", "surface", "one_way", "go_down", "go_up", "level_short", "m_down")}}
    for z in data["zones"]:
        lv = w.level(z["id"])
        conns = []
        for c in data["connections"]:
            ends = c["ends"]
            mine = next((x for x in ends if x["zone"] == z["id"]), None)
            if not mine:
                continue
            other = ends[1] if ends[0] is mine else ends[0]
            tr = trans.get(mine.get("transition"))
            kind = L_(CONN[c["kind"]], lang)
            el = next((x for x in w.elevators if x["id"] == c.get("elevator")), None)
            if c["status"] == "playable" and not el:
                kind = L_(PRES[(tr or {}).get("presentation") or "road"], lang)
            if tr and tr.get("requires_drill_site_cleared"):
                kind += " · " + L_(L("locked: drill the Deep Seal", "cerrado: perforá el Sello Profundo"), lang)
            olv = w.level(other["zone"])
            conns.append({"to": other["zone"], "name": zones[other["zone"]]["name"], "kind": kind, "k": c["kind"],
                          "exit": mine["exit"], "edge": mine.get("edge", ""), "status": c["status"],
                          "lv": olv, "dm": zones[other["zone"]].get("depth_m", 0), "dir": "same" if olv == lv else ("up" if olv > lv else "down"),
                          "conn": el["id"] if el else c["id"]})
        ex = z.get("extraction")
        if ex:
            olv = w.level(ex["zone"])
            conns.append({"to": ex["zone"], "name": zones[ex["zone"]]["name"], "kind": L_(L("Lift · one way", "Elevador · sólo ida"), lang), "k": "lift",
                          "exit": ex["exit"], "edge": "UP", "status": "playable", "lv": olv, "dm": zones[ex["zone"]].get("depth_m", 0),
                          "dir": "same" if olv == lv else ("up" if olv > lv else "down"), "conn": "extraction." + z["id"]})
        out["zones"][z["id"]] = {
            "name": z["name"], "sub": L_(z.get("subtitle", ""), lang) if z.get("subtitle") else "",
            "kind": L_(KIND[z["kind"]], lang), "k": z["kind"], "biome": L_(BIOME[z["biome"]], lang), "b": BIOME_COLOR[z["biome"]],
            "danger": L_(DANGER[z["danger"]], lang), "d": DANGER_ORDER.index(z["danger"]), "tier": z["tier"],
            "status": L_(STATUS[z["status"]], lang), "s": z["status"], "layer": L_(LAYER[z["layer"]], lang),
            "lv": lv, "lvname": L_(LEVEL_NAME[lv], lang), "dm": z.get("depth_m", 0), "floor": z.get("level_label", ""),
            "summary": L_(z["summary"], lang), "conns": conns,
            "step": w.steps.get(z["id"]), "city": z["id"] == data.get("dustline", {}).get("zone"),
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
                f'<li><i class="ln ln-lm"></i>{e(L_(T["landmark"], lang))}</li><li><i class="ln ln-sight"></i>{"Sightline to the Exchange" if lang == "en" else "Línea de vista al Exchange"}</li></ul></div>'
                f'<div><p class="kicker">{e(L_(T["l_sites"], lang))}</p><ul>'
                + "".join(f'<li><span style="color:{SITE_COLOR[k]};display:inline-flex">{icon_svg(k, "wm-ico", PASS_ICON)}</span>{e(L_(T[key], lang))}</li>'
                          for k, key in (("house", "l_house"), ("shop", "l_shop"), ("bike", "l_bike"), ("vdi", "l_vdi")))
                + '</ul></div></div>')
    kinds = "".join(f'<li>{icon_svg(k)}{e(L_(KIND[k], lang))}</li>' for k in KIND)
    biomes = "".join(f'<li><i class="sw" style="background:{BIOME_COLOR[b]}"></i>{e(L_(BIOME[b], lang))}</li>' for b in BIOME)
    danger = "".join(f'<li><i class="dg dg-{i}"></i>{e(L_(DANGER[k], lang))}</li>' for i, k in enumerate(DANGER_ORDER))
    lines = (f'<li><i class="ln ln-play"></i>{e(L_(T["l_playable"], lang))}</li><li><i class="ln ln-plan"></i>{e(L_(T["l_planned"], lang))}</li>'
             f'<li><i class="ln ln-road"></i>{e(L_(T["l_road"], lang))}</li><li><i class="ln ln-under"></i>{e(L_(T["l_tunnel"], lang))}</li>'
             f'<li><i class="ln ln-journey"></i>{e(L_(T["l_journey"], lang))}</li><li><i class="ln ln-pip"></i>{e(L_(T["l_exit"], lang))}</li>'
             f'<li>{icon_svg("gate", "wm-ico wm-ico-gate", PASS_ICON)}{e(L_(T["l_gate"], lang))}</li>'
             f'<li>{icon_svg("fuel", "wm-ico wm-ico-gate", PASS_ICON)}{e(L_(T["l_fuel"], lang))}</li>')
    passages = (f'<li>{icon_svg("elevator", "wm-ico wm-ico-vl", PASS_ICON)}{e(L_(T["l_elevator"], lang))}</li>'
                f'<li>{icon_svg("lift", "wm-ico wm-ico-vl", PASS_ICON)}{e(L_(T["l_lift"], lang))}</li>'
                f'<li>{icon_svg("stairs", "wm-ico wm-ico-vl", PASS_ICON)}{e(L_(T["l_stairs"], lang))}</li>'
                f'<li>{icon_svg("deep", "wm-ico wm-ico-vl", PASS_ICON)}{e(L_(T["l_deep"], lang))}</li>'
                f'<li>{icon_svg("extract", "wm-ico wm-ico-vl", PASS_ICON)}{e(L_(T["l_extract"], lang))}</li>'
                f'<li><i class="ln ln-ghost-below"></i>{e(L_(T["l_ghost_below"], lang))}</li>'
                f'<li><i class="ln ln-ghost-above"></i>{e(L_(T["l_ghost_above"], lang))}</li>'
                f'<li><i class="ln ln-switch">↕</i>{e(L_(T["l_switch"], lang))}</li>')
    places = "".join(f'<li><span style="color:{SITE_COLOR[k]};display:inline-flex">{icon_svg(k, "wm-ico", PASS_ICON)}</span>{e(L_(T[key], lang))}</li>'
                     for k, key in (("hunt", "l_hunt"), ("excavation", "l_bore_short"), ("house", "l_house"), ("shop", "l_shop"), ("bike", "l_bike"), ("vdi", "l_vdi")))
    return (f'<div class="wm-legend" data-for="map"><div><p class="kicker">{e(L_(T["kinds"], lang))}</p><ul>{kinds}</ul></div>'
            f'<div><p class="kicker">{e(L_(T["biomes"], lang))}</p><ul>{biomes}</ul></div>'
            f'<div><p class="kicker">{e(L_(T["danger"], lang))}</p><ul>{danger}</ul></div>'
            f'<div><p class="kicker">{e(L_(T["lines"], lang))}</p><ul>{lines}</ul></div>'
            f'<div><p class="kicker">{e(L_(T["passages"], lang))}</p><ul>{passages}</ul></div>'
            f'<div><p class="kicker">{e(L_(T["l_sites"], lang))}</p><ul>{places}</ul></div></div>')


def journey_html(data, lang):
    j = next((r for r in data.get("routes", []) if r["id"] == "route.first_journey"), None)
    if not j:
        return ""
    w = World(data, lang)
    zones = w.zones
    items = ""
    prev_lv = None
    for i, s in enumerate(j["steps"]):
        z = zones[s["zone"]]
        lv = w.level(z["id"])
        if prev_lv is not None and lv != prev_lv:
            # Cambio de nivel entre dos pasos: la fila cambia la capa del mapa y enfoca el paso siguiente.
            up = lv > prev_lv
            txt = (L_(L("Up to the surface · Shaft 3", "Sube a la superficie · Pozo 3"), lang) if lv == 0 and up
                   else (L_(T["up_to"], lang) if up else L_(T["down_to"], lang)).format(n=lv))
            items += f'<li class="jsw"><button type="button" data-goto="{z["id"]}" data-switch="{lv}"><span class="jsw-a">{"↑" if up else "↓"}</span><span>{e(txt)}</span></button></li>'
        prev_lv = lv
        n = f'<span class="jn">{i:02d}</span>'
        tag = f'<span class="tag tag-soon">{e(L_(STATUS["planned"], lang))}</span>' if z["status"] == "planned" else ""
        lvtxt = L_(T["surface"], lang) if lv == 0 else f'−{z.get("depth_m", 0)} m · {L_(LEVEL_NAME[lv], lang)}'
        items += (f'<li><button type="button" data-goto="{z["id"]}">{n}<span class="jb"><b>{e(z["name"])}{tag}<span class="jl l-{abs(lv)}">{e(lvtxt)}</span></b>'
                  f'<span>{e(L_(s["text"], lang))}</span></span></button></li>')
    m = j.get("target_minutes", {})
    mins = ""
    if m:
        a, b = m["first_time"]
        c, d = m["repeat"]
        mins = f'<p class="note">{e(L_(T["minutes"], lang).format(a=a, b=b, c=c, d=d))}</p>'
    return (f'<div class="wm-journey-list"><p class="kicker">{e(L_(T["journey"], lang))}</p><p class="sec-lead">{e(L_(T["journey_lead"], lang))}</p>'
            f'<ol>{items}</ol>{mins}</div>')


def rail_html(data, lang):
    """Barra de profundidad: subir, un boton por nivel (metros de sus mapas), bajar, y la lectura del indicador."""
    depths = level_depths(data)
    btns = "".join(f'<li><button type="button" data-level="{lv}" aria-pressed="{"true" if lv == 0 else "false"}">'
                   f'<b>{"0" if lv == 0 else str(lv).replace("-", "−")}</b><span>{e(L_(T["surface"], lang)) if lv == 0 else e(level_band(lv, depths, lang, short=True))}</span></button></li>' for lv in LEVELS)
    return (f'<div class="wm-rail" role="group" aria-label="{e(L_(T["rail"], lang))}">'
            f'<button type="button" class="wm-dive" data-dive="up" aria-label="{e(L_(T["go_up"], lang))}" disabled><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 15l6-6 6 6"/></svg><span>{e(L_(T["go_up"], lang))}</span></button>'
            f'<ol>{btns}</ol>'
            f'<button type="button" class="wm-dive" data-dive="down" aria-label="{e(L_(T["go_down"], lang))}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg><span>{e(L_(T["go_down"], lang))}</span></button>'
            f'<output class="wm-gauge" aria-live="polite"><b data-m>0</b><small>m</small><span data-band>{e(level_band(0, {}, lang))}</span></output></div>')


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
  <div class="wm-frame" data-pane="map" data-level="0">
    {rail_html(data, lang)}
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
