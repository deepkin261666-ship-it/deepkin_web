# Wiki de referencia (estilo Tibia/Medivia, 2026-10-10): una pagina por entidad con ficha (infobox), todo
# enlazado entre si, "lo sueltan", "se encuentra en", tablas ordenables, migas de pan y un indice de busqueda.
# Todo sale de data/ (copiado del juego con build.py --sync) y de las constantes de data/rules/*.gd.
# Salida: en/wiki/*.html y es/wiki/*.html, mas wiki/search.js por idioma.
import glob
import html
import json
import math
import os
import re

import gdconst as G
import slugs as S
import worldmap as WM
from i18n import ATTRS, CLASSES as CLASS_TXT, FACTION as FACTION_TXT, FAMILIES, FAMILY_DESC, ITEM_EN_FALLBACK, ITEM_ES, SLOTS, L
from i18n import MOBS as MOB_TXT
from wiki_i18n import (ABILITY_SHAPE, CATS, FACTION_ES, LURE, MOB_ES, POSE, QUEST_ES, ROLES, SERVICE_STALL, SIGN_DISTRICT, W)


def role_name(r, lang):
    return ROLES[r][lang] if r in ROLES else (r or "—").title()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAPS = []  # huecos de datos encontrados al generar (se informan al final del build)


def gap(msg):
    if msg not in GAPS:
        GAPS.append(msg)


def jload(rel):
    path = os.path.join(ROOT, "data", rel)
    return json.load(open(path)) if os.path.exists(path) else None


# --- Datos ----------------------------------------------------------------------------------------------------
def _load_dir(rel):
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "data", rel, "*.json"))):
        out.append(json.load(open(f)))
    return out


ALL_ITEMS = {d["id"]: d for d in _load_dir("items")}
ITEMS = {k: v for k, v in ALL_ITEMS.items() if not v.get("retired")}
MOBS = {d["id"]: d for d in _load_dir("npcs")}
MATS = {d["id"]: d for d in _load_dir("materials")}
DISCS = {d["id"]: d for d in _load_dir("discoveries")}
VEHICLES = _load_dir("vehicles")
FACTIONS = {f["id"]: f for f in (jload("factions/factions.json") or {"factions": []})["factions"]}
CLASSES = (jload("classes/classes.json") or {"classes": []})["classes"]
CLASS_BY_ID = {c["id"]: c for c in CLASSES}
CLASS_KEY = {c["id"]: c["id"].split(".")[-1] for c in CLASSES}
WORLD = jload("world/world_map.json") or {"zones": [], "connections": []}
ZONES = {z["id"]: z for z in WORLD["zones"]}
REGIONS = {r["id"]: r for r in WORLD.get("regions", [])}
REGION = jload("starting_region.json") or {"floors": [], "transitions": [], "entities": [], "spawn_groups": [], "discoveries": []}
FLOORS = {f["zone_id"]: f for f in REGION["floors"]}
HUBS = jload("world/respawn_hubs.json") or {"hubs": []}
BANNERS = (jload("world/zone_banners.json") or {}).get("zones", {})
CONST = jload("rules/constants.json") or {}
QUESTS = _load_dir("quests")
SPEAKERS = {}
for _f in sorted(glob.glob(os.path.join(ROOT, "data", "dialog", "*.json"))):
    SPEAKERS.update(json.load(open(_f)).get("speakers", {}))
SETS = {}
for _zid, _fl in FLOORS.items():
    if _fl.get("set"):
        SETS[_zid] = jload("world/sets/" + os.path.basename(_fl["set"]))

ICON_DIR = os.path.join(ROOT, "assets", "img", "icons")


def has_icon(content_id):
    return os.path.exists(os.path.join(ICON_DIR, content_id + ".png"))


def item_cat(item_id):
    p = item_id.split(".")
    return p[1] if len(p) == 3 else "salvage"


# --- Personas: lugar y nombre --------------------------------------------------------------------------------
def split_name(raw):
    """"HESK  ·  ROCK DRILLER" -> ("Hesk", "Rock Driller")."""
    parts = [p.strip() for p in raw.split("·")]

    def tc(s):
        return " ".join(w if w in ("&",) else (w[:1] + w[1:].lower()) for w in s.split()).replace("Ms.", "Ms.")
    name = tc(parts[0]) if parts else raw
    name = re.sub(r"-([a-z])", lambda m: "-" + m.group(1).upper(), name)
    role = tc(parts[1]) if len(parts) > 1 else ""
    return name, role


def zone_signs(zone_id):
    """Carteles de la zona en coordenadas locales: (x, z, texto, subtitulo)."""
    out = []
    fl = FLOORS.get(zone_id, {})
    for s in fl.get("signs", []):
        p = s["position"]
        lines = s["text"].split("\n")
        out.append((p[0], p[2], lines[0], " ".join(lines[1:])))
    st = SETS.get(zone_id) or {}
    for s in st.get("signs", []):
        p = s["p"]
        out.append((p[0], p[2], s["text"].split("\n")[0], s.get("sub", "")))
    return out


PEOPLE = {}  # id -> {id, name, role, zone, pos, class, pose, lines, dialog}
for _zid, _fl in FLOORS.items():
    for _w in _fl.get("workers", []):
        PEOPLE[_w["id"]] = {"id": _w["id"], "zone": _zid, "pos": _w["position"], "class": _w.get("class"), "pose": _w.get("pose"), "kind": "worker"}
    for _n in _fl.get("npcs", []):
        PEOPLE[_n["id"]] = {"id": _n["id"], "zone": _zid, "pos": _n["position"], "class": _n.get("class"), "pose": _n.get("pose"),
                            "kind": "npc", "raw_name": _n.get("name", ""), "dialog": _n.get("dialog")}
for _sid, _sp in SPEAKERS.items():
    p = PEOPLE.setdefault(_sid, {"id": _sid, "zone": None, "pos": None, "class": None, "pose": None, "kind": "speaker"})
    p["raw_name"] = _sp.get("name", p.get("raw_name", ""))
    p["lines"] = _sp.get("lines", [])
for _pid, _p in PEOPLE.items():
    _p["name"], _p["role"] = split_name(_p.get("raw_name") or _pid.split(".")[-1].replace("_", " ").upper())
    if not _p.get("lines") and not _p.get("dialog"):
        gap(f"Person {_pid} is placed in {_p['zone']} but has no dialog lines (data/dialog/*.json).")
    if not _p.get("zone"):
        gap(f"Person {_pid} has dialog lines but no placement in data/starting_region.json.")


def person_place(p):
    """Cartel mas cercano (y distrito de Dustline si aplica)."""
    if not p.get("pos") or not p.get("zone"):
        return None, None, None
    x, z = p["pos"]
    best = None
    for sx, sz, text, sub in zone_signs(p["zone"]):
        d = math.hypot(sx - x, sz - z)
        if best is None or d < best[0]:
            best = (d, text, sub)
    if not best:
        return None, None, None
    d, text, sub = best
    district = SIGN_DISTRICT.get(text) if p["zone"] == WORLD.get("dustline", {}).get("zone") else None
    return (text if d <= 14 else None), (sub if d <= 14 else None), district


# --- Registro de entidades y enlazado automatico --------------------------------------------------------------
class Ent:
    def __init__(self, kind, cid, name, url, sort=None):
        self.kind, self.id, self.name, self.url, self.sort = kind, cid, name, url, sort


REG = {}


def reg(kind, cid, name, url):
    if cid in REG:
        return REG[cid]
    REG[cid] = Ent(kind, cid, name, url)
    return REG[cid]


for _i in ITEMS.values():
    reg("item", _i["id"], _i["display_name"], S.item(_i["id"]))
for _m in MOBS.values():
    reg("mob", _m["id"], _m["display_name"], S.mob(_m["id"]))
for _p in PEOPLE.values():
    reg("npc", _p["id"], _p["name"], S.person(_p["id"]))
for _z in WORLD["zones"]:
    reg("zone", _z["id"], _z["name"], S.zone(_z["id"]))
for _f in FACTIONS.values():
    reg("faction", _f["id"], _f["name"], S.faction(_f["id"]))
for _m in MATS.values():
    reg("material", _m["id"], _m["display_name"], S.material(_m["id"]))
for _q in QUESTS:
    reg("quest", _q["id"], _q["title"].title(), S.quest(_q["id"]))
_urls = [e.url for e in REG.values()]
assert len(_urls) == len(set(_urls)), "duplicate wiki slugs"

MECH = {  # paginas de mecanicas: slug -> clave de titulo
    "experience": "m_experience", "death": "m_death", "skills": "m_skills", "classes": "m_classes",
    "vehicles": "m_vehicles", "currency": "m_currency", "computers": "m_computers",
}


def _aliases():
    """(texto, url) para el enlazado automatico. Los nombres quedan como en el juego en ambos idiomas."""
    out = []
    for e in REG.values():
        if e.kind == "npc":
            out.append((e.name, e.url))
            first = e.name.split()
            if len(first) > 1 and first[0] in ("Old", "Doc", "Auntie", "Ms."):
                out.append((" ".join(first[1:]), e.url))
            continue
        out.append((e.name, e.url))
        if e.kind == "mob":
            out.append((e.name + "s", e.url))
        if e.kind == "zone" and e.name.startswith("The ") and ZONES[e.id]["status"] == "playable":
            out.append((e.name[4:], e.url))
        if e.kind == "faction" and e.name.startswith("The "):
            out.append((e.name[4:], e.url))
    out += [("C-3", S.zone("zone.excavation_c3")), ("Castoff", S.faction("faction.castoffs")),
            ("Limonite", S.item("item.ore.limonite")), ("Hematite", S.item("item.ore.hematite")),
            ("Magnetite", S.item("item.ore.magnetite")), ("Lumenita", S.item("item.mineral.lumenita"))]
    city = WORLD.get("dustline")
    if city:
        for d in city["districts"]:
            url = S.zone(city["zone"]) + "#" + S.district_anchor(d["id"])
            out.append((d["name"]["en"], url))
            if d["name"]["en"].startswith("The "):
                out.append((d["name"]["en"][4:], url))
    for c in CLASSES:
        out.append((c["name"].title(), "classes.html#" + CLASS_KEY[c["id"]]))
    seen, uniq = set(), []
    for a, u in sorted(out, key=lambda x: -len(x[0])):
        if a and a not in seen and len(a) > 2:
            seen.add(a)
            uniq.append((a, u))
    return uniq


ALIASES = _aliases()
_ALIAS_URL = dict(ALIASES)
_ALIAS_RE = re.compile(r"(?<![\w\-])(" + "|".join(re.escape(a) for a, _ in ALIASES) + r")(?![\w\-])")


def rel(url, here="wiki/"):
    """URL relativa a la carpeta de idioma -> relativa a la pagina actual (todas las del wiki viven en wiki/)."""
    if here == "wiki/":
        return url[5:] if url.startswith("wiki/") else "../" + url
    return url


class Linker:
    """Enlaza la primera mencion de cada entidad por pagina (como un wiki); nunca a la pagina actual."""

    def __init__(self, self_url):
        self.self_url = self_url
        self.done = set()

    def __call__(self, text):
        out, last = [], 0
        for m in _ALIAS_RE.finditer(text):
            url = _ALIAS_URL[m.group(1)]
            if url.split("#")[0] == self.self_url or url in self.done:
                continue
            out.append(html.escape(text[last:m.start()]))
            out.append(f'<a href="{rel(url)}">{html.escape(m.group(1))}</a>')
            self.done.add(url)
            last = m.end()
        out.append(html.escape(text[last:]))
        return "".join(out)


def mentions(text):
    return {_ALIAS_URL[m.group(1)].split("#")[0] for m in _ALIAS_RE.finditer(text)}


MENTIONED_BY = {}  # url -> [person ids] (dialogos que nombran la entidad)
for _p in PEOPLE.values():
    texts = list(_p.get("lines", []))
    for node in ((_p.get("dialog") or {}).get("nodes") or {}).values():
        texts.append(node.get("text", ""))
    for _t in texts:
        for _u in mentions(_t):
            if S.person(_p["id"]) != _u:
                MENTIONED_BY.setdefault(_u, [])
                if _p["id"] not in MENTIONED_BY[_u]:
                    MENTIONED_BY[_u].append(_p["id"])


# --- Indices derivados: donde aparece cada cosa ------------------------------------------------------------------
def _derive():
    found = {}    # item id -> list of (kind, data)
    dropped = {}  # item id -> list of (mob id, chance, qmin, qmax)
    zone_mobs = {}  # zone id -> list of dict(mob, count, respawn, safe, group)
    scrap = CONST.get("SCRAP_COMPONENT_ID", "item.scrap_component")
    coin = CONST.get("COIN_ITEM_ID", "item.currency.metal_coin")
    for m in MOBS.values():
        dropped.setdefault(scrap, []).append((m["id"], 1.0, 1, 1))
        if m.get("coins") and m["coins"][1] > 0:
            dropped.setdefault(coin, []).append((m["id"], 1.0, m["coins"][0], m["coins"][1]))
        for entry in m.get("loot", []):
            q = entry.get("quantity", [1, 1])
            dropped.setdefault(entry["item"], []).append((m["id"], float(entry.get("chance", 1.0)), q[0], q[1]))
            if entry["item"] not in ITEMS:
                gap(f"{m['id']} loot references unknown item {entry['item']}.")
    for g in REGION.get("spawn_groups", []):
        for mem in g["members"]:
            zone_mobs.setdefault(g["zone_id"], []).append({"mob": mem["content_id"], "count": mem["count"], "respawn": g.get("respawn_seconds"),
                                                           "safe": g.get("safe_radius"), "group": g["id"]})
    static = {}
    for en in REGION.get("entities", []):
        if en["entity_type"] == 2:
            static[(en["zone_id"], en["content_id"])] = static.get((en["zone_id"], en["content_id"]), 0) + 1
        elif en["entity_type"] == 4:
            if en["content_id"].startswith("item.container."):
                found.setdefault(en["content_id"], []).append(("placed", en["zone_id"], en.get("quantity", 1), None))
            else:
                found.setdefault(en["content_id"], []).append(("ground", en["zone_id"], en.get("quantity", 1), None))
    for (zid, mid), n in static.items():
        zone_mobs.setdefault(zid, []).append({"mob": mid, "count": n, "respawn": None, "safe": None, "group": None})
    drill = {}  # zone -> list of sites
    for zid, fl in FLOORS.items():
        for s in fl.get("drill_sites", []):
            drill.setdefault(zid, []).append(s)
            y = s.get("yield")
            if y:
                found.setdefault(y["item_id"], []).append(("drill", zid, y.get("quantity", 1), s["content_id"]))
    for c in ITEMS.values():
        for entry in c.get("crate_loot", []):
            iid = entry["item"] if isinstance(entry, dict) else entry
            qty = entry.get("quantity", 1) if isinstance(entry, dict) else 1
            if iid == "$starting_weapon":
                for cl in CLASSES:
                    for v in cl["variants"]:
                        found.setdefault(v["weapon_id"], []).append(("crate", c["id"], 1, (cl["id"], v["id"])))
            elif iid == "$starting_ammo":
                ammo = CONST.get("STARTER_AMMUNITION_ID")
                if ammo:
                    found.setdefault(ammo, []).append(("crate", c["id"], CONST.get("STARTER_AMMUNITION_CRATE_QUANTITY", 1), "ranged"))
            else:
                found.setdefault(iid, []).append(("crate", c["id"], qty, None))
    return found, dropped, zone_mobs, drill


FOUND, DROPPED, ZONE_MOBS, DRILL = _derive()


# --- Helpers HTML -------------------------------------------------------------------------------------------------
def e(s):
    return html.escape(str(s), quote=True)


def t(key, lang, **kw):
    v = W[key][lang] if isinstance(W[key], dict) else W[key]
    return v.format(**kw) if kw else v


def n(v, lang, d=None):
    if d is not None:
        s = f"{v:,.{d}f}"
    elif isinstance(v, float) and not v.is_integer():
        s = f"{v:,g}" if abs(v) < 1e6 else f"{v:,.0f}"
    else:
        s = f"{int(v):,}"
    if lang == "es":
        s = s.replace(",", " ").replace(".", ",")
    return s


def pct(v, lang, d=0):
    return n(v * 100, lang, d) + "%"


def lk(cid, lang=None, label=None, here="wiki/"):
    en = REG.get(cid)
    if not en:
        return e(label or cid)
    return f'<a href="{rel(en.url, here)}">{e(label or en.name)}</a>'


def img(cid, cls="wk-icon", size=160):
    if has_icon(cid):
        return f'<img class="{cls}" src="../../assets/img/icons/{cid}.png" alt="" width="{size}" height="{size}" loading="lazy">'
    en = REG.get(cid)
    letter = (en.name if en else cid.split(".")[-1])[:1].upper()
    return f'<span class="{cls} wk-ph" aria-hidden="true">{e(letter)}</span>'


def tag_status(planned, lang):
    return f'<span class="tag tag-soon">{e(t("soon", lang))}</span>' if planned else ""


def crumbs(lang, trail):
    parts = [f'<a href="../index.html">{e(t("home", lang))}</a>', f'<a href="index.html">Wiki</a>']
    for label, url in trail:
        parts.append(f'<a href="{url}">{e(label)}</a>' if url else f'<span aria-current="page">{e(label)}</span>')
    return '<nav class="crumbs" aria-label="breadcrumb">' + '<span aria-hidden="true">›</span>'.join(parts) + "</nav>"


def infobox(title, art, rows, extra=""):
    body = "".join(f'<div><dt>{e(k)}</dt><dd>{v}</dd></div>' for k, v in rows if v not in (None, ""))
    return f'<aside class="infobox"><div class="ib-art">{art}</div><p class="ib-title">{e(title)}</p><dl>{body}</dl>{extra}</aside>'


def sec(anchor, title, inner):
    return f'<section class="wk-sec" id="{anchor}"><h2>{e(title)}</h2>{inner}</section>' if inner else ""


def table(head, rows, sortable=True, cls=""):
    th = "".join(f'<th{" data-sort=" + chr(34) + k + chr(34) if sortable and k else ""}>{e(h)}</th>' for h, k in head)
    tb = "".join("<tr>" + "".join(f"<td{' class=n' if (head[i][1] == 'num') else ''}>{c}</td>" for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="tablewrap"><table class="data{" sortable" if sortable else ""} {cls}"><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></div>'


def ul(items, cls="wk-list"):
    items = [i for i in items if i]
    return f'<ul class="{cls}">' + "".join(f"<li>{i}</li>" for i in items) + "</ul>" if items else ""


def seealso(lang, links):
    links = [x for x in links if x]
    return sec("see-also", t("see_also", lang), '<p class="wk-see">' + " · ".join(links) + "</p>") if links else ""


def article(lang, trail, kicker, title, lead, box, body, toc=None):
    toc_html = ""
    if toc:
        toc_html = '<nav class="wk-toc" aria-label="' + e(t("contents", lang)) + '">' + "".join(f'<a href="#{a}">{e(l)}</a>' for a, l in toc) + "</nav>"
    lead_html = f'<p class="lead">{lead}</p>' if lead else ""
    return f"""<div class="wrap wk">
{crumbs(lang, trail)}
<header class="wk-head"><p class="kicker">{kicker}</p><h1>{e(title)}</h1>{lead_html}</header>
<div class="wk-grid{' no-box' if not box else ''}">{box}<div class="wk-body">{toc_html}{body}</div></div>
</div>"""


def secs_toc(body):
    return [(m.group(1), html.unescape(m.group(2))) for m in re.finditer(r'<section class="wk-sec" id="([^"]+)"><h2>([^<]+)</h2>', body)]


def map_link(lang, zone_id=None, district=None):
    q = f"zone={zone_id}" if zone_id else f"district={district}"
    return f'<a class="btn wk-map" href="../world.html?{q}#map">{e(t("open_map", lang))}</a>'


def secs(v, lang):
    return n(v, lang) + " s"


def rng(a, b, lang, unit=""):
    return (n(a, lang) if a == b else f"{n(a, lang)}–{n(b, lang)}") + unit


def class_chip(cid, lang):
    c = CLASS_BY_ID.get(cid)
    if not c:
        return ""
    return f'<a class="chip" href="../classes.html#{CLASS_KEY[cid]}"><i style="background:#{c["visual_color"]}"></i>{e(c["name"])}</a>'


def item_desc(it, lang):
    if lang == "es":
        return ITEM_ES.get(it["id"]) or it.get("description") or ITEM_EN_FALLBACK.get(it["id"], "")
    return it.get("description") or ITEM_EN_FALLBACK.get(it["id"], "")


def mob_text(m, key, lang):
    """lore/habitat/rules: ingles desde los datos; español desde la traduccion del sitio."""
    if lang == "en":
        v = m.get(key)
        if v:
            return v
        old = MOB_TXT.get(m["id"], {}).get(key)
        return old["en"] if old else ([] if key == "rules" else "")
    v = MOB_ES.get(m["id"], {}).get(key)
    if v:
        return v
    old = MOB_TXT.get(m["id"], {}).get(key)
    return old["es"] if old else ([] if key == "rules" else "")


# --- Calculos de juego -----------------------------------------------------------------------------------------
def base_damage(w):
    return w.get("properties", {}).get("base_damage", 0)


def class_damage(c, w):
    wtype = w.get("weapon_type", "melee")
    attr = "might" if wtype == "melee" else "precision"
    coef = c["combat_coefficients"].get(wtype, 1.0)
    mult = max(0.75, min(1.25, 1 + (c["attributes"][attr] - 10) * G.RPG.get("STAT_DAMAGE_STEP", 0.015)))
    return max(1, round(base_damage(w) * coef * mult))


def stack_of(it):
    return it.get("properties", {}).get("stack_size", 1)


# =================================================================================================================
# Paginas de objetos
# =================================================================================================================
def item_page(it, lang):
    iid = it["id"]
    url = S.item(iid)
    L_ = Linker(url)
    p = it.get("properties", {})
    cat = item_cat(iid)
    slot = it.get("equipment_slot")
    rows = [(t("category", lang), f'<a href="items.html#cat-{cat}">{e(CATS[cat][lang])}</a>')]
    if slot:
        rows.append((t("slot", lang), e(SLOTS.get(slot, {}).get(lang, slot))))
    status = t("soon", lang) if it.get("planned") else (t("prototype", lang) if "provisional_rivet" in iid else t("in_game", lang))
    rows.append((t("status", lang), e(status)))
    if it.get("weapon_type"):
        w_t = t("melee", lang) if it["weapon_type"] == "melee" else t("ranged", lang)
        rows.append((t("type", lang), e(w_t)))
    fam = it.get("weapon_family")
    if fam:
        rows.append((t("skill", lang), f'<a href="skills.html#{S.skill_anchor(fam)}">{e(FAMILIES[fam][lang])}</a>'))
    if base_damage(it):
        itv = p.get("attack_interval", 1)
        rows += [(t("damage", lang), n(base_damage(it), lang)), (t("interval", lang), secs(itv, lang)),
                 (t("dps", lang), n(base_damage(it) / itv, lang, 1)), (t("range", lang), n(p.get("attack_range", 0), lang) + " m")]
    if it.get("damage_type"):
        rows.append((t("damage_type", lang), e(t("dt_" + it["damage_type"], lang))))
    if it.get("hands"):
        rows.append((t("hands", lang), e(t("two_hand", lang) if it["hands"] == 2 else t("one_hand", lang))))
    if it.get("ammo_item_id"):
        rows.append((t("ammo", lang), lk(it["ammo_item_id"]) + f' <small>{e(t("any_ammo", lang))}</small>'))
    if "ammo_multiplier" in p:
        rows.append((t("damage", lang), "×" + n(p["ammo_multiplier"], lang)))
    if slot in ("head", "chest", "legs", "boots", "arms", "secondary_weapon") and "armor_defense" in p:
        rows.append((t("armor", lang), "+" + n(p["armor_defense"], lang)))
        rows.append((t("resistance", lang), "+" + n(p.get("resistance_bonus", 0), lang)))
    if p.get("illumination_radius"):
        rows.append((t("light_radius", lang), n(p["illumination_radius"], lang) + " m"))
    if p.get("light_energy_per_second"):
        rows.append((t("drain", lang), n(p["light_energy_per_second"], lang) + "/s"))
        cell = ITEMS.get("item.battery.provisional_relay_cell", {}).get("properties", {}).get("battery_capacity")
        if cell:
            rows.append((t("runtime", lang), "≈ " + n(cell / p["light_energy_per_second"] / 60, lang, 1) + " min"))
    if p.get("battery_capacity"):
        rows.append((t("capacity", lang), n(p["battery_capacity"], lang) + " " + t("energy", lang).lower()))
    if it.get("container"):
        rows.append((t("capacity", lang), n(it["container"]["cells"], lang) + " " + t("cells", lang)))
    if p.get("carry_bonus"):
        rows.append((t("carry", lang), "+" + n(p["carry_bonus"], lang) + " kg"))
    if p.get("drill_power"):
        rows.append((t("drill_power", lang), "×" + n(p["drill_power"], lang)))
    if p.get("heal_amount"):
        rows.append((t("heals", lang), "+" + n(p["heal_amount"], lang) + " " + t("health", lang).lower()))
        rows.append((t("use_cooldown", lang), secs(p.get("use_cooldown", 0), lang)))
    if p.get("currency_value"):
        rows.append((t("value", lang), n(p["currency_value"], lang) + " Metal"))
    if p.get("stagger_bonus"):
        rows.append((t("stagger", lang), "+" + pct(p["stagger_bonus"], lang)))
    if "weight" in it:
        rows.append((t("weight", lang), n(it["weight"], lang) + " kg"))
    else:
        # Sin "weight" el juego usa 0 (ItemDefinition: "0 until items are weighed").
        gap(f"{iid} has no weight in its item definition (the game treats it as 0 kg).")
        rows.append((t("weight", lang), f'0 kg <small>{e(t("not_weighed", lang))}</small>'))
    st = stack_of(it)
    rows.append((t("stack", lang), n(st, lang) if st > 1 else e(t("no_stack", lang))))
    if it.get("gear_tier"):
        rows.append((t("tier", lang), f'<a href="experience.html#tiers">T{it["gear_tier"]}</a>'))
    req = it.get("requirements") or {}
    reqs = []
    if req.get("minimum_level"):
        reqs.append(f'{t("level", lang)} {req["minimum_level"]}')
    for a, v in (req.get("minimum_attributes") or {}).items():
        reqs.append(f'{ATTRS[a][lang]} {v}')
    for f, v in (req.get("minimum_skills") or {}).items():
        reqs.append(f'{FAMILIES[f][lang]} {v}')
    if req.get("class_ids"):
        reqs.append(", ".join(CLASS_BY_ID[c]["name"] for c in req["class_ids"] if c in CLASS_BY_ID))
    rows.append((t("requires", lang), e(" · ".join(reqs)) if reqs else e(t("none_req", lang))))
    if it.get("fixed"):
        rows.append((t("pickup", lang), e(t("fixed", lang))))
    rows.append(("ID", f'<code>{e(iid)}</code>'))
    if not it.get("description"):
        gap(f"{iid} has no description in its item definition" + (" (the site uses its own fallback text)." if item_desc(it, "en") else "."))
    box = infobox(it["display_name"], img(iid, "wk-icon"), rows)

    body = sec("description", t("description", lang), f'<p class="wk-lead2">{L_(item_desc(it, lang))}</p>' if item_desc(it, lang) else "")
    if it.get("planned"):
        body += f'<p class="wk-note">{e(t("planned_item", lang))}</p>'
    # Armas: daño por clase
    if base_damage(it) and it.get("equipment_slot") == "primary_weapon":
        rows_c = []
        for c in CLASSES:
            d = class_damage(c, it)
            rows_c.append([class_chip(c["id"], lang), n(c["combat_coefficients"].get(it.get("weapon_type", "melee"), 1), lang),
                           n(d, lang), n(d / p.get("attack_interval", 1), lang, 1),
                           "×" + n(c["skill_affinity"].get(fam, G.SKILLS.get("DEFAULT_AFFINITY", 0.5)), lang)])
        body += sec("by-class", t("damage_by_class", lang),
                    f'<p>{e(t("by_class_lead", lang))} <a href="../arsenal.html#calculator">{e(t("calc", lang))}</a>.</p>'
                    + table([(t("class", lang), "text"), (t("coef", lang), "num"), (t("damage", lang), "num"), (t("dps", lang), "num"),
                             (t("skill_train", lang), "num")], rows_c))
        starts = [(cl, v) for cl in CLASSES for v in cl["variants"] if v["weapon_id"] == iid]
        starters = [cl for cl in CLASSES if iid in cl.get("starter_weapons", [])]
        lis = [t("starting_of", lang, cls=class_chip(cl["id"], lang), variant=e(v["id"].split(".")[-1].title())) for cl, v in starts]
        lis += [t("starter_of", lang, cls=class_chip(cl["id"], lang)) for cl in starters]
        body += sec("starting", t("starting_title", lang), ul(lis))
    # Lo sueltan
    drops = DROPPED.get(iid, [])
    if drops:
        rows_d = [[lk(mid), pct(ch, lang), rng(a, b, lang), f'<a href="{rel(S.zone(z))}">{e(ZONES[z]["name"])}</a>' if (z := mob_zone(mid)) else "—"]
                  for mid, ch, a, b in sorted(drops, key=lambda x: -x[1])]
        body += sec("dropped-by", t("dropped_by", lang), table([(t("creature", lang), "text"), (t("chance", lang), "num"),
                                                                (t("quantity", lang), "text"), (t("where", lang), "text")], rows_d))
    # Se encuentra en
    lis = []
    for kind, a, q, extra in FOUND.get(iid, []):
        if kind == "crate":
            who = ""
            if isinstance(extra, tuple):
                who = " — " + t("for_variant", lang, cls=CLASS_BY_ID[extra[0]]["name"], variant=extra[1].split(".")[-1].title())
            elif extra == "ranged":
                who = " — " + t("if_ranged", lang)
            where = [x[1] for x in FOUND.get(a, []) if x[0] == "placed"]
            lis.append(f'{lk(a)} ×{n(q, lang)}{e(who)}' + (" · " + ", ".join(lk(z) for z in where) if where else ""))
        elif kind == "ground":
            lis.append(t("on_ground", lang, zone=lk(a), q=n(q, lang)))
        elif kind == "placed":
            lis.append(t("placed_in", lang, zone=lk(a)))
        elif kind == "drill":
            lis.append(t("drilled_in", lang, site=lk(extra), zone=lk(a), q=n(q, lang)))
    if iid == G.DEATH.get("REMAINS_ITEM_ID"):
        lis.append(t("remains_found", lang))
    body += sec("found-in", t("found_in", lang), ul(lis))
    # Contenido (cajones)
    if it.get("crate_loot"):
        lis = []
        for entry in it["crate_loot"]:
            cid = entry["item"] if isinstance(entry, dict) else entry
            q = entry.get("quantity", 1) if isinstance(entry, dict) else 1
            if cid == "$starting_weapon":
                vs = ", ".join(f'{lk(v["weapon_id"])} ({e(cl["name"])})' for cl in CLASSES for v in cl["variants"])
                lis.append(f'<b>{e(t("your_weapon", lang))}</b>: {vs}')
            elif cid == "$starting_ammo":
                a = CONST.get("STARTER_AMMUNITION_ID")
                lis.append(f'<b>{e(t("your_ammo", lang))}</b>: {lk(a)} ×{n(CONST.get("STARTER_AMMUNITION_CRATE_QUANTITY", 1), lang)}')
            else:
                lis.append(f'{img(cid, "wk-ticon", 40)}{lk(cid)}' + (f" ×{n(q, lang)}" if q > 1 else ""))
        body += sec("contents", t("contents", lang), f'<p>{e(t("crate_note", lang))}</p>' + ul(lis, "wk-list wk-items"))
    # Para que sirve
    body += sec("used-for", t("used_for", lang), ul(used_for(it, lang)))
    # Mencionado por
    who = MENTIONED_BY.get(url, [])
    if who:
        body += sec("mentioned", t("mentioned_by", lang), '<p class="wk-see">' + " · ".join(lk(p) for p in who) + "</p>")
    same = [lk(o["id"]) for o in sorted(ITEMS.values(), key=lambda x: x["display_name"]) if item_cat(o["id"]) == cat and o["id"] != iid]
    extra = [f'<a href="items.html">{e(t("all_items", lang))}</a>']
    if fam:
        extra.append(f'<a href="skills.html#{S.skill_anchor(fam)}">{e(FAMILIES[fam][lang])}</a>')
    if cat in ("weapon", "ammunition", "shield"):
        extra.append(f'<a href="../arsenal.html">Arsenal</a>')
    if cat == "currency":
        extra.append(f'<a href="currency.html">{e(t("m_currency", lang))}</a>')
    if iid == G.DEATH.get("REMAINS_ITEM_ID") or cat == "backpack":
        extra.append(f'<a href="death.html">{e(t("m_death", lang))}</a>')
    body += seealso(lang, same + extra)
    trail = [(t("items", lang), "items.html"), (CATS[cat][lang], f"items.html#cat-{cat}"), (it["display_name"], None)]
    kicker = e(CATS[cat][lang]) + (" · " + e(SLOTS[slot][lang]) if slot in SLOTS else "") + tag_status(it.get("planned"), lang)
    return article(lang, trail, kicker, it["display_name"], "", box, body, secs_toc(body))


def mob_zone(mid):
    for zid, lst in ZONE_MOBS.items():
        if any(x["mob"] == mid for x in lst):
            return zid
    return None


def used_for(it, lang):
    iid = it["id"]
    cat = item_cat(iid)
    out = []
    if cat == "ammunition":
        ws = [w for w in ITEMS.values() if w.get("weapon_type") == "ranged"]
        out.append(t("ammo_used", lang) + " " + ", ".join(lk(w["id"]) for w in ws))
    if cat == "battery":
        out.append(t("battery_used", lang, cost=n(G.COMBAT.get("ABILITY_ENERGY_COST", 15), lang), dash=n(G.COMBAT.get("DASH_ENERGY_COST", 6), lang))
                   + " " + ", ".join(lk(i["id"]) for i in ITEMS.values() if i.get("equipment_slot") == "light"))
    if cat == "light":
        out.append(t("light_used", lang, battery=lk("item.battery.provisional_relay_cell")))
    if cat == "tool":
        out.append(t("drill_used", lang) + " " + ", ".join(lk(m) for m in MATS))
    if cat == "backpack":
        out.append(t("backpack_used", lang, cells=n(it.get("container", {}).get("cells", 0), lang), pouch=n(CONST.get("POUCH_CELLS", 4), lang)))
    if cat == "consumable":
        out.append(t("capsule_used", lang))
    if cat == "currency":
        out.append(t("coin_used", lang) if not it.get("planned") else t("coin_planned", lang))
    if cat in ("ore", "mineral", "salvage"):
        out.append(t("salvage_used", lang))
    if it.get("equipment_slot") == "secondary_weapon":
        out.append(t("shield_used", lang))
    for q in QUESTS:
        for i, step in enumerate(q["steps"]):
            goal = step.get("goal", {})
            hit = (goal.get("type") == "open_container" and iid in goal.get("targets", [])) or \
                  (goal.get("type") == "equip_slot" and it.get("equipment_slot") in goal.get("slots", []) and
                   any(iid in [(x["item"] if isinstance(x, dict) else x) for x in c.get("crate_loot", [])] or
                       (it.get("equipment_slot") == "primary_weapon" and any(v["weapon_id"] == iid for cl in CLASSES for v in cl["variants"]))
                       for c in ITEMS.values() if c.get("crate_loot")))
            if hit:
                out.append(t("quest_step", lang, quest=lk(q["id"]), n=i + 1))
                break
    if iid == G.DEATH.get("REMAINS_ITEM_ID"):
        out.append(t("remains_used", lang, cells=n(it["container"]["cells"], lang), mins=n(G.DEATH.get("CORPSE_DECAY_SECONDS", 1800) / 60, lang)))
    return out


def items_index(lang):
    order = list(CATS)
    groups = ""
    rows = []
    for cat in order:
        its = sorted([i for i in ITEMS.values() if item_cat(i["id"]) == cat], key=lambda i: (bool(i.get("planned")), i["display_name"]))
        if not its:
            continue
        cards = "".join(f'<a class="wk-card{" soon" if i.get("planned") else ""}" href="{rel(S.item(i["id"]))}">{img(i["id"], "wk-cicon", 64)}'
                        f'<span><b>{e(i["display_name"])}</b><small>{e(SLOTS.get(i.get("equipment_slot"), {}).get(lang, CATS[cat][lang]))}'
                        f'{" · " + e(t("soon", lang)) if i.get("planned") else ""}</small></span></a>' for i in its)
        groups += f'<section class="wk-sec" id="cat-{cat}"><h2>{e(CATS[cat][lang])} <small>{len(its)}</small></h2><div class="wk-cards">{cards}</div></section>'
        for i in its:
            key = key_stat(i, lang)
            rows.append([f'<span class="tn-in">{img(i["id"], "wk-ticon", 40)}<a href="{rel(S.item(i["id"]))}">{e(i["display_name"])}</a></span>',
                         e(CATS[cat][lang]), e(SLOTS.get(i.get("equipment_slot"), {}).get(lang, "—")),
                         n(i.get("weight", 0), lang), n(stack_of(i), lang), key,
                         e(t("soon", lang)) if i.get("planned") else e(t("in_game", lang))])
    tbl = sec("all", t("all_items", lang), table([(t("name", lang), "text"), (t("category", lang), "text"), (t("slot", lang), "text"),
                                                  (t("weight", lang) + " (kg)", "num"), (t("stack", lang), "num"), (t("key_stat", lang), "text"),
                                                  (t("status", lang), "text")], rows))
    body = groups + tbl
    return article(lang, [(t("items", lang), None)], e(t("category_k", lang)), t("items", lang), e(t("items_lead", lang, n=len(ITEMS))),
                   "", body, secs_toc(body))


def key_stat(i, lang):
    p = i.get("properties", {})
    if base_damage(i):
        return f'{n(base_damage(i), lang)} {t("damage", lang).lower()}'
    if i.get("equipment_slot") in ("head", "chest", "legs", "boots", "secondary_weapon"):
        return f'+{p.get("armor_defense", 0)} {t("armor", lang).lower()}'
    if p.get("illumination_radius"):
        return f'{n(p["illumination_radius"], lang)} m'
    if p.get("battery_capacity"):
        return f'{p["battery_capacity"]} {t("energy", lang).lower()}'
    if p.get("heal_amount"):
        return f'+{p["heal_amount"]} {t("health", lang).lower()}'
    if p.get("currency_value"):
        return f'{n(p["currency_value"], lang)} Metal'
    if "ammo_multiplier" in p:
        return f'×{n(p["ammo_multiplier"], lang)}'
    if i.get("container"):
        return f'{i["container"]["cells"]} {t("cells", lang)}'
    if p.get("drill_power"):
        return f'×{n(p["drill_power"], lang)}'
    return "—"


# =================================================================================================================
# Criaturas
# =================================================================================================================
def ability_rows(m, lang):
    out = []
    tips = []
    for a in m.get("abilities", []):
        shape = a.get("shape") or ("position" if a.get("target") == "position" else "position")
        S_ = ABILITY_SHAPE[shape]
        dmg = n(a["damage"], lang) if a.get("damage") else ("+" + pct(a["heal"], lang) if a.get("heal") else "—")
        dt = a.get("damage_type", "physical" if a.get("damage") else "")
        area = []
        if a.get("radius"):
            area.append(f'{t("radius", lang)} {n(a["radius"], lang)} m')
        if a.get("half_angle"):
            area.append(f'{n(a["half_angle"] * 2, lang)}°')
        if a.get("reach"):
            area.append(f'{t("reach", lang)} {n(a["reach"], lang)} m')
        if a.get("range"):
            area.append(f'{n(a.get("min_range", 0), lang)}–{n(a["range"], lang)} m')
        if a.get("width"):
            area.append(f'{t("width", lang)} {n(a["width"], lang)} m')
        out.append([f'<b>{e(a.get("name", a["id"]))}</b>', e(S_["name"][lang]), dmg, e(t("dt_" + dt, lang)) if dt else "—",
                    secs(a.get("windup", 0), lang), e(" · ".join(area)) or "—", secs(a.get("cooldown", 0), lang),
                    secs(a.get("recovery", 0), lang) if a.get("recovery") else "—"])
        hp = round(m["max_health"] * a.get("heal", 0))
        tip = S_["tip"][lang].format(radius=n(a.get("radius", 0), lang), windup=n(a.get("windup", 0), lang), arc=n(a.get("half_angle", 0) * 2, lang),
                                     reach=n(a.get("reach", 0), lang), range=n(a.get("range", 0), lang), min=n(a.get("min_range", 0), lang),
                                     width=n(a.get("width", 0), lang), pct=pct(a.get("heal", 0), lang), hp=n(hp, lang),
                                     below=pct(a.get("below_health", 0), lang), quiet=n(a.get("quiet_seconds", 0), lang),
                                     retreat=n(a.get("retreat", 0), lang))
        if a.get("retreat"):
            tip += " " + t("then_retreat", lang, s=n(a["retreat"], lang))
        if a.get("los"):
            tip += " " + t("needs_los", lang)
        if dt and dt != "physical":
            tip += " " + t("mitigated_res", lang)
        elif a.get("damage"):
            tip += " " + t("mitigated_arm", lang)
        tips.append(f'<b>{e(a.get("name", a["id"]))}</b> — {e(tip)}')
    return out, tips


def mob_page(m, lang):
    mid = m["id"]
    url = S.mob(mid)
    L_ = Linker(url)
    per, mov = m.get("perception", {}), m.get("movement", {})
    fac = m.get("faction")
    rows = [(t("faction", lang), lk(fac) if fac else "—"), (t("species", lang), e(m.get("species", "—"))),
            (t("role", lang), e(role_name(m.get("role"), lang))), (t("archetype", lang), e(role_name(m.get("archetype"), lang))),
            (t("threat", lang), n(m["threat"], lang) if m.get("threat") else "—"),
            (t("hp", lang), n(m["max_health"], lang)), (t("speed", lang), n(m["movement_speed"], lang) + " m/s"),
            (t("xp", lang), f'<a href="experience.html#kill-xp">{n(m.get("xp", G.RPG.get("XP_PER_NPC_KILL", 35)), lang)}</a>'),
            (t("coins", lang), f'<a href="currency.html">{rng(m["coins"][0], m["coins"][1], lang)}</a>' if m.get("coins") else "—"),
            (t("attack", lang), f'{n(m["attack_damage"], lang)} / {secs(m["attack_cooldown"], lang)} · {n(m["attack_range"], lang)} m'),
            (t("dps", lang), n(m["attack_damage"] / m["attack_cooldown"], lang, 1)),
            (t("detection", lang), n(m["detection_range"], lang) + " m"),
            (t("aggro", lang), n(per["aggro_radius"], lang) + " m" if per.get("aggro_radius") else "—"),
            (t("memory", lang), secs(per["memory_seconds"], lang) if per.get("memory_seconds") else "—"),
            (t("call", lang), n(per["call_radius"], lang) + " m" if per.get("call_radius") else "—"),
            (t("leash", lang), n(mov["leash_radius"], lang) + " m" if mov.get("leash_radius") else "—"),
            (t("lure", lang), e(LURE[mov["lure"]]["name"][lang]) if mov.get("lure") in LURE else "—"),
            (t("resistances", lang), e(t("none_data", lang))),
            ("ID", f"<code>{e(mid)}</code>")]
    for k in ("faction", "perception", "movement", "lore", "habitat", "rules", "threat"):
        if k not in m:
            gap(f"{mid} has no '{k}' in its definition (data/entities/npcs).")
    box = infobox(m["display_name"], img(mid, "wk-icon"), rows)
    lore = mob_text(m, "lore", lang)
    body = sec("lore", t("lore", lang), f'<p class="wk-lead2">{L_(lore.replace("PROVISIONAL. ", ""))}</p>' if lore else "")
    # Comportamiento
    beh = []
    if per.get("aggro_radius"):
        beh.append(t("b_aggro", lang, a=n(per["aggro_radius"], lang), d=n(m["detection_range"], lang), mem=n(per.get("memory_seconds", 0), lang)))
    else:
        beh.append(t("b_detect", lang, d=n(m["detection_range"], lang)))
    if mov.get("lure") in LURE:
        beh.append(LURE[mov["lure"]]["text"][lang].format(leash=n(mov.get("leash_radius", 0), lang), call=n(per.get("call_radius", 0), lang)))
    if per.get("call_radius"):
        beh.append(t("b_call", lang, r=n(per["call_radius"], lang)))
    if mov.get("retreat_health"):
        beh.append(t("b_retreat", lang, p=pct(mov["retreat_health"], lang), s=n(mov.get("retreat_seconds", 0), lang)))
    if mov.get("preferred_range"):
        a, b = mov["preferred_range"]
        beh.append(t("b_range", lang, a=n(a, lang), b=n(b, lang)))
    verbs = " ".join(f"<span>{e(v)}</span>" for v in m.get("verbs", []))
    body += sec("behaviour", t("behaviour", lang), (f'<p class="verbs wk-verbs">{verbs}</p>' if verbs else "") + ul([e(x) for x in beh]))
    ab_rows, tips = ability_rows(m, lang)
    basic = [f'<b>{e(t("basic_attack", lang))}</b>', e(t("melee", lang)), n(m["attack_damage"], lang), e(t("dt_physical", lang)), "—",
             e(t("reach", lang) + " " + n(m["attack_range"], lang) + " m"), secs(m["attack_cooldown"], lang), "—"]
    body += sec("attacks", t("attacks", lang),
                table([(t("attack", lang), ""), (t("shape", lang), ""), (t("damage", lang), ""), (t("damage_type", lang), ""), (t("windup", lang), ""),
                       (t("area", lang), ""), (t("cooldown", lang), ""), (t("recovery", lang), "")], [basic] + ab_rows, sortable=False)
                + (f'<p class="wk-sub">{e(t("telegraphs", lang))}</p>' + ul(tips) if tips else f'<p class="wk-note">{e(t("no_telegraphs", lang))}</p>'))
    rules = mob_text(m, "rules", lang)
    tactics = [L_(r) for r in rules]
    if any(a.get("shape") == "cone" for a in m.get("abilities", [])):
        tactics.append(e(t("tac_cover", lang)))
    if any(a.get("shape") == "heal" for a in m.get("abilities", [])):
        tactics.append(e(t("tac_pressure", lang)))
    if mov.get("lure") == "territorial":
        tactics.append(e(t("tac_leash", lang, leash=n(mov.get("leash_radius", 0), lang))))
    body += sec("tactics", t("how_to_fight", lang), ul(tactics))
    # Botin
    loot = [[lk(CONST.get("SCRAP_COMPONENT_ID", "item.scrap_component")), "100%", "1"]]
    if m.get("coins"):
        loot.append([lk(CONST.get("COIN_ITEM_ID", "item.currency.metal_coin")), "100%", rng(m["coins"][0], m["coins"][1], lang)])
    for entry in m.get("loot", []):
        q = entry.get("quantity", [1, 1])
        loot.append([f'{img(entry["item"], "wk-ticon", 40)}{lk(entry["item"])}', pct(entry.get("chance", 1), lang), rng(q[0], q[1], lang)])
    body += sec("loot", t("loot", lang), f'<p>{e(t("loot_note", lang))}</p>' + table([(t("item", lang), "text"), (t("chance", lang), "num"), (t("quantity", lang), "text")], loot))
    # Donde
    rows_w = []
    for zid, lst in ZONE_MOBS.items():
        for x in lst:
            if x["mob"] != mid:
                continue
            resp = rng(x["respawn"][0], x["respawn"][1], lang, " s") if x["respawn"] else e(t("fixed_spawn", lang))
            rows_w.append([lk(zid), n(x["count"], lang), resp, n(x["safe"], lang) + " m" if x["safe"] else "—",
                           f'<code>{e(x["group"])}</code>' if x["group"] else "—"])
    hab = mob_text(m, "habitat", lang)
    where = (f'<p>{L_(hab)}</p>' if hab else "") + (table([(t("zone", lang), "text"), (t("count", lang), "num"), (t("respawn", lang), "text"),
                                                           (t("safe_radius", lang), "text"), (t("spawn_group", lang), "text")], rows_w) if rows_w else "")
    if not rows_w:
        gap(f"{mid} is not placed anywhere in data/starting_region.json (no spawn group or entity).")
        where += f'<p class="wk-note">{e(t("not_placed", lang))}</p>'
    body += sec("where", t("where_to_find", lang), where)
    # XP
    xp = m.get("xp", G.RPG.get("XP_PER_NPC_KILL", 35))
    xp_rows = [[f"{lv} → {lv + 1}", n(G.xp_to_next(lv), lang), n(math.ceil(G.xp_to_next(lv) / xp), lang)] for lv in (1, 5, 10, 20, 40)]
    body += sec("xp", t("xp_value", lang), f'<p>{e(t("xp_share", lang, xp=n(xp, lang)))}</p>'
                + table([(t("level", lang), ""), (t("xp_needed", lang), ""), (t("kills", lang), "")], xp_rows, sortable=False))
    who = MENTIONED_BY.get(url, [])
    if who:
        body += sec("mentioned", t("mentioned_by", lang), '<p class="wk-see">' + " · ".join(lk(p) for p in who) + "</p>")
    kin = [lk(o["id"]) for o in MOBS.values() if o.get("faction") == fac and o["id"] != mid and fac]
    body += seealso(lang, kin + [f'<a href="creatures.html">{e(t("creatures", lang))}</a>', f'<a href="../bestiary.html">{e(t("bestiary", lang))}</a>'])
    kicker = e(FACTIONS[fac]["name"] if fac in FACTIONS else t("creature", lang)) + (" · " + e(role_name(m["role"], lang)) if m.get("role") else "")
    return article(lang, [(t("creatures", lang), "creatures.html"), (m["display_name"], None)], kicker, m["display_name"], "", box, body, secs_toc(body))


def creatures_index(lang):
    rows = []
    for m in sorted(MOBS.values(), key=lambda x: x["max_health"]):
        zs = sorted({z for z, lst in ZONE_MOBS.items() for x in lst if x["mob"] == m["id"]})
        rows.append([f'<span class="tn-in">{img(m["id"], "wk-ticon", 40)}<a href="{rel(S.mob(m["id"]))}">{e(m["display_name"])}</a></span>',
                     lk(m["faction"]) if m.get("faction") else "—", n(m["max_health"], lang), n(m.get("xp", 0), lang),
                     rng(m["coins"][0], m["coins"][1], lang) if m.get("coins") else "—", n(m["attack_damage"] / m["attack_cooldown"], lang, 1),
                     n(m["movement_speed"], lang), n(len(m.get("abilities", [])), lang), ", ".join(lk(z) for z in zs) or "—"])
    body = sec("list", t("creatures", lang), table([(t("name", lang), "text"), (t("faction", lang), "text"), (t("hp", lang), "num"),
                                                    (t("xp", lang), "num"), (t("coins", lang), "text"), (t("dps", lang), "num"),
                                                    (t("speed", lang), "num"), (t("abilities", lang), "num"), (t("where", lang), "text")], rows))
    fac = "".join(f'<a class="wk-card" href="{rel(S.faction(f["id"]))}"><span><b>{e(f["name"])}</b><small>{e(t("st_" + f.get("status", "planned"), lang))}</small></span></a>'
                  for f in FACTIONS.values())
    body += sec("factions", t("factions", lang), f'<div class="wk-cards">{fac}</div>')
    return article(lang, [(t("creatures", lang), None)], e(t("category_k", lang)), t("creatures", lang), e(t("creatures_lead", lang)), "", body, secs_toc(body))


# =================================================================================================================
# Facciones
# =================================================================================================================
def faction_page(f, lang):
    fid = f["id"]
    url = S.faction(fid)
    L_ = Linker(url)
    es = FACTION_ES.get(fid, {})
    old = FACTION_TXT.get(fid, {})

    def tx(key):
        if lang == "es":
            if key in es:
                return es[key]
            if key in old and isinstance(old[key], dict):
                return old[key]["es"]
        return f.get(key, "")
    rows = [(t("category", lang), e(t("fc_" + f.get("category", ""), lang)) if ("fc_" + f.get("category", "")) in W else e(f.get("category", ""))),
            (t("status", lang), e(t("st_" + f.get("status", "planned"), lang))), (t("identity", lang), e(tx("identity"))),
            (t("hierarchy", lang), e(tx("hierarchy"))), ("ID", f"<code>{e(fid)}</code>")]
    box = infobox(f["name"], f'<span class="wk-icon wk-ph">{e(f["name"].replace("The ", "")[:1])}</span>', rows)
    traits = tx("traits")
    if isinstance(traits, dict):
        traits = traits[lang]
    body = sec("traits", t("traits", lang), ul([L_(x[:1].upper() + x[1:]) for x in (traits or [])]))
    kv = [(t("communication", lang), tx("communication")), (t("territory", lang), tx("territory")), (t("look", lang), tx("visual"))]
    if f.get("status") == "planned" and old.get("rumour"):
        kv.append((t("rumour", lang), old["rumour"][lang]))
    body += sec("about", t("about", lang), '<dl class="kv kv-col">' + "".join(f"<div><dt>{e(a)}</dt><dd>{L_(b)}</dd></div>" for a, b in kv if b) + "</dl>")
    members = [m for m in MOBS.values() if m.get("faction") == fid]
    if members:
        body += sec("members", t("members", lang), '<div class="wk-cards">' + "".join(
            f'<a class="wk-card" href="{rel(S.mob(m["id"]))}">{img(m["id"], "wk-cicon", 64)}<span><b>{e(m["display_name"])}</b><small>{e(role_name(m.get("role"), lang))} · {n(m["max_health"], lang)} {e(t("hp", lang))}</small></span></a>'
            for m in members) + "</div>")
    elif f.get("status") == "planned":
        body += f'<p class="wk-note">{e(t("faction_planned", lang))}</p>'
    body += seealso(lang, [lk(o) for o in FACTIONS if o != fid] + [f'<a href="creatures.html">{e(t("creatures", lang))}</a>'])
    return article(lang, [(t("creatures", lang), "creatures.html"), (t("factions", lang), "creatures.html#factions"), (f["name"], None)],
                   e(t("faction", lang)) + tag_status(f.get("status") == "planned", lang), f["name"], "", box, body, secs_toc(body))


# =================================================================================================================
# Gente
# =================================================================================================================
def person_page(p, lang):
    pid = p["id"]
    url = S.person(pid)
    L_ = Linker(url)
    sign, sub, district = person_place(p)
    city = WORLD.get("dustline", {})
    dname = None
    if district:
        d = next((x for x in city.get("districts", []) + city.get("entrances", []) if x["id"] == district), None)
        dname = d["name"][lang] if d else None
    gives = [q for q in QUESTS if q.get("giver") == pid]
    services = []
    if sign and sign in SERVICE_STALL:
        services.append(e(SERVICE_STALL[sign][lang]) + (f' <small>({e(sub)})</small>' if sub else ""))
    if p.get("zone") and p.get("pos"):
        for comp in FLOORS.get(p["zone"], {}).get("computers", []):
            if math.hypot(comp["position"][0] - p["pos"][0], comp["position"][1] - p["pos"][1]) < 6:
                services.append(f'<a href="computers.html">{e(t("svc_depot", lang))}</a> <span class="tag tag-live">{e(t("works", lang))}</span>')
    rows = [(t("role", lang), e(p["role"] or "—")), (t("zone", lang), lk(p["zone"]) if p.get("zone") else "—"),
            (t("district", lang), f'<a href="{rel(S.zone(city["zone"]))}#{S.district_anchor(district)}">{e(dname)}</a>' if dname and district.startswith("district.") else (e(dname) if dname else "")),
            (t("location", lang), e(t("near_sign", lang, sign=sign)) if sign else ""),
            (t("civilisation", lang), class_chip(p["class"], lang) if p.get("class") else ""),
            (t("pose", lang), e(POSE.get(p.get("pose"), {}).get(lang, p.get("pose") or "")) if p.get("pose") else ""),
            (t("talk", lang), e(t("talk_e", lang))),
            (t("quests", lang), ", ".join(lk(q["id"]) for q in gives) if gives else ""),
            ("ID", f"<code>{e(pid)}</code>")]
    col = "#" + CLASS_BY_ID[p["class"]]["visual_color"] if p.get("class") in CLASS_BY_ID else "var(--amber)"
    art = f'<span class="wk-icon wk-ph wk-person" style="--c:{col}">{e(p["name"][:1])}</span>'
    box = infobox(p["name"], art, rows)
    # Donde
    where = []
    if p.get("zone"):
        z = ZONES.get(p["zone"], {})
        txt = t("lives_in", lang, zone=lk(p["zone"]))
        if dname:
            txt += " " + t("in_district", lang, d=e(dname))
        if sign:
            txt += " " + t("by_sign", lang, sign=e(sign)) + (f' <small>({e(sub)})</small>' if sub else "")
        where.append(f"<p>{txt}.</p>")
        if district and district.startswith("district."):
            where.append(map_link(lang, district=district))
        elif z:
            where.append(map_link(lang, zone_id=p["zone"]))
    else:
        where.append(f'<p class="wk-note">{e(t("unplaced", lang))}</p>')
    body = sec("where", t("where_to_find", lang), "".join(where))
    # Lo que dice
    lines = p.get("lines") or []
    note = f'<p class="wk-sub">{e(t("lines_note", lang))}</p>'
    if lines:
        body += sec("lines", t("what_they_say", lang), note + "".join(f'<blockquote class="wk-quote">{L_(x)}</blockquote>' for x in lines))
    dlg = p.get("dialog")
    if dlg:
        nodes = dlg.get("nodes", {})
        tree = ""
        for nid, node in nodes.items():
            opts = "".join(f'<li>{"<a href=" + chr(34) + "#dlg-" + to + chr(34) + ">" if to else ""}{e(lab)}{"</a>" if to else ""}'
                           f'{"" if to else " <small>" + e(t("ends", lang)) + "</small>"}</li>' for lab, to in node.get("options", []))
            tree += f'<div class="wk-dlg" id="dlg-{e(nid)}"><p class="kicker">{e(nid)}{" · " + e(t("start", lang)) if nid == dlg.get("start") else ""}</p><blockquote class="wk-quote">{L_(node["text"])}</blockquote><ul class="wk-opts">{opts}</ul></div>'
        body += sec("dialog", t("conversation", lang), note + tree)
    # Misiones
    if gives:
        q_html = "".join(f'<p>{lk(q["id"])} — {e(t("reward_xp", lang, xp=n(q.get("reward", {}).get("xp", 0), lang)))}</p>' for q in gives)
        body += sec("quests", t("quests", lang), q_html)
    # Servicios
    svc = list(services)
    if p.get("zone") == city.get("zone") and district and district.startswith("district."):
        d = next(x for x in city["districts"] if x["id"] == district)
        svc += [f'{e(WM.SERVICES[s][lang] if s in WM.SERVICES else s)} <span class="tag tag-soon">{e(t("soon", lang))}</span>' for s in d["services"]
                if not (s == "service.depot" and any("computers.html" in x for x in services))]
    if svc:
        body += sec("services", t("services", lang), ul(svc) + (f'<p class="wk-note">{e(t("services_note", lang))}</p>' if p.get("zone") == city.get("zone") else ""))
    # Menciona
    ment = sorted({u_ for x in lines for u_ in mentions(x)} - {url})
    if ment:
        names = [f'<a href="{rel(u_)}">{e(next((en.name for en in REG.values() if en.url == u_), u_))}</a>' for u_ in ment if u_.startswith("wiki/")]
        if names:
            body += sec("mentions", t("mentions", lang), '<p class="wk-see">' + " · ".join(names) + "</p>")
    others = [lk(o["id"]) for o in PEOPLE.values() if o.get("zone") == p.get("zone") and o["id"] != pid]
    body += seealso(lang, others + [f'<a href="people.html">{e(t("people", lang))}</a>'])
    kicker = e(p["role"] or t("person", lang)) + (" · " + e(ZONES[p["zone"]]["name"]) if p.get("zone") in ZONES else "")
    return article(lang, [(t("people", lang), "people.html"), (p["name"], None)], kicker, p["name"], "", box, body, secs_toc(body))


def people_index(lang):
    body = ""
    order = [z["id"] for z in WORLD["zones"]]
    by_zone = {}
    for p in PEOPLE.values():
        by_zone.setdefault(p.get("zone"), []).append(p)
    for zid in sorted(by_zone, key=lambda z: order.index(z) if z in order else 99):
        ps = by_zone[zid]
        rows = []
        for p in sorted(ps, key=lambda x: x["name"]):
            sign, _, district = person_place(p)
            dn = ""
            if district:
                city = WORLD["dustline"]
                d = next((x for x in city["districts"] + city["entrances"] if x["id"] == district), None)
                dn = d["name"][lang] if d else ""
            rows.append([f'<a href="{rel(S.person(p["id"]))}">{e(p["name"])}</a>', e(p["role"] or "—"), e(dn or sign or "—"),
                         class_chip(p["class"], lang) if p.get("class") else "—",
                         ", ".join(lk(q["id"]) for q in QUESTS if q.get("giver") == p["id"]) or "—"])
        title = ZONES[zid]["name"] if zid in ZONES else t("unplaced_t", lang)
        body += sec("z-" + (S.tail(zid) if zid else "none"), title + f" ({len(ps)})",
                    (f'<p>{lk(zid)}</p>' if zid else "") + table([(t("name", lang), "text"), (t("role", lang), "text"), (t("location", lang), "text"),
                                                                  (t("civilisation", lang), "text"), (t("quests", lang), "text")], rows))
    return article(lang, [(t("people", lang), None)], e(t("category_k", lang)), t("people", lang), e(t("people_lead", lang, n=len(PEOPLE))), "", body, secs_toc(body))


# =================================================================================================================
# Zonas
# =================================================================================================================
def zone_page(z, lang):
    zid = z["id"]
    url = S.zone(zid)
    L_ = Linker(url)
    fl = FLOORS.get(zid, {})
    hub = next((h for h in HUBS.get("hubs", []) if h["zone_id"] == zid), None)
    ban = BANNERS.get(zid)
    danger_i = WM.DANGER_ORDER.index(z["danger"])
    meter = '<span class="wm-meter" aria-hidden="true">' + "".join(f'<i class="{"on dg-" + str(danger_i) if i <= danger_i else ""}"></i>' for i in range(5)) + "</span>"
    depth = z.get("depth_m")
    rows = [(t("kind", lang), e(WM.KIND[z["kind"]][lang])),
            (t("biome", lang), f'<i class="sw" style="background:{WM.BIOME_COLOR[z["biome"]]}"></i>{e(WM.BIOME[z["biome"]][lang])}'),
            (t("layer", lang), e(WM.LAYER[z["layer"]][lang])),
            (t("depth", lang), (f"{n(depth, lang)} m" + (" " + e(t("below_surface", lang)) if depth else "")) if depth is not None else "—"),
            (t("map_level", lang), (n(z["level"], lang) + (f' · {e(z["level_label"])}' if z.get("level_label") else "")) if "level" in z else "—"),
            (t("tier", lang), f'<a href="experience.html#tiers">T{z["tier"]}</a>'), (t("danger", lang), meter + e(WM.DANGER[z["danger"]][lang])),
            (t("status", lang), e(WM.STATUS[z["status"]][lang])), (t("region", lang), e(REGIONS[z["region"]]["name"][lang]) if z.get("region") in REGIONS else "—"),
            (t("size", lang), f'{z["size_m"][0]} × {z["size_m"][1]} m' if z.get("size_m") else ""),
            (t("floors", lang), n(z["floors"], lang) if z.get("floors") else ""),
            (t("respawn_hub", lang), f'<a href="death.html#hubs">{e(t("yes", lang))}</a>' if hub else e(t("no", lang))),
            ("ID", f"<code>{e(zid)}</code>")]
    if z["status"] == "playable" and zid not in FLOORS:
        gap(f"{zid} is playable in world_map.json but has no floor in data/starting_region.json.")
    banner = ""
    if ban:
        banner = f'<div class="wk-banner"><b>{e(ban["title"])}</b><span>{e(ban.get("subtitle", ""))}</span><small>{e(ban.get("objective", ""))}</small></div>'
    elif z["status"] == "playable":
        gap(f"{zid} has no banner in data/world/zone_banners.json.")
    box = infobox(z["name"], banner or f'<span class="wk-icon wk-ph">{e(z["name"].replace("The ", "")[:1])}</span>', rows,
                  f'<p class="ib-map">{map_link(lang, zone_id=zid)}</p>')
    body = sec("overview", t("overview", lang), f'<p class="wk-lead2">{L_(z["summary"][lang])}</p>'
               + (f'<p class="wk-note">{e(t("zone_planned", lang))}</p>' if z["status"] == "planned" else ""))
    # Primer viaje
    for r in WORLD.get("routes", []):
        for i, st in enumerate(r.get("steps", [])):
            if st["zone"] == zid:
                body += f'<p class="wk-step"><span>{e(r["name"][lang])} · {e(t("step", lang))} {i + 1}/{len(r["steps"])}</span>{L_(st["text"][lang])}</p>'
    # Salidas
    rows_x = []
    for c in WORLD["connections"]:
        mine = next((x for x in c["ends"] if x["zone"] == zid), None)
        if not mine:
            continue
        other = c["ends"][1] if c["ends"][0] is mine else c["ends"][0]
        o = ZONES[other["zone"]]
        pres = ""
        if mine.get("transition"):
            tr = next((x for x in REGION["transitions"] if x["entity_id"] == mine["transition"]), None)
            if tr and tr.get("presentation"):
                pres = t("pr_" + tr["presentation"], lang)
        rows_x.append([lk(o["id"]), e(WM.CONN[c["kind"]][lang]) + (f" · {e(pres)}" if pres else ""), f'<span class="wk-sign">{e(mine["exit"])}</span>',
                       e(mine.get("edge", "")), e(WM.STATUS[c["status"]][lang])])
    parent = z.get("stack", {}).get("parent")
    below = [o for o in WORLD["zones"] if o.get("stack", {}).get("parent") == zid]
    stack = ""
    if parent:
        stack += f'<p>{e(t("stacked_under", lang))} {lk(parent)}.</p>'
    if below:
        stack += f'<p>{e(t("levels_below", lang))} ' + ", ".join(f'{lk(o["id"])} ({o.get("level_label", o.get("stack", {}).get("depth"))})' for o in below) + ".</p>"
    body += sec("exits", t("exits", lang), stack + (table([(t("to", lang), "text"), (t("kind", lang), "text"), (t("exit_sign", lang), "text"),
                                                           (t("edge", lang), "text"), (t("status", lang), "text")], rows_x) if rows_x else ""))
    # Criaturas
    mobs = ZONE_MOBS.get(zid, [])
    if mobs:
        rows_m = [[f'<span class="tn-in">{img(x["mob"], "wk-ticon", 40)}{lk(x["mob"])}</span>', n(x["count"], lang),
                   rng(x["respawn"][0], x["respawn"][1], lang, " s") if x["respawn"] else e(t("fixed_spawn", lang)),
                   n(MOBS[x["mob"]].get("xp", 0), lang), n(MOBS[x["mob"]]["max_health"], lang)] for x in mobs if x["mob"] in MOBS]
        total = sum(x["count"] for x in mobs)
        body += sec("creatures", t("creatures", lang), f'<p>{e(t("creature_total", lang, n=total))}</p>'
                    + table([(t("creature", lang), "text"), (t("count", lang), "num"), (t("respawn", lang), "text"), (t("xp", lang), "num"), (t("hp", lang), "num")], rows_m))
    # Gente
    ppl = [p for p in PEOPLE.values() if p.get("zone") == zid]
    if ppl:
        cards = ""
        for p in sorted(ppl, key=lambda x: x["name"]):
            sign, _, _ = person_place(p)
            col = "#" + CLASS_BY_ID[p["class"]]["visual_color"] if p.get("class") in CLASS_BY_ID else "var(--amber)"
            cards += (f'<a class="wk-card" href="{rel(S.person(p["id"]))}"><span class="wk-cicon wk-ph wk-person" style="--c:{col}">{e(p["name"][:1])}</span>'
                      f'<span><b>{e(p["name"])}</b><small>{e(" · ".join(x for x in (p["role"], sign) if x) or "—")}</small></span></a>')
        body += sec("people", t("people", lang), f'<div class="wk-cards">{cards}</div>')
    # Distritos de Dustline
    city = WORLD.get("dustline")
    if city and city.get("zone") == zid:
        body += districts_html(city, lang, L_)
    # Recursos
    sites = DRILL.get(zid, [])
    if sites:
        agg = {}
        for s in sites:
            y = s.get("yield")
            key = (s["content_id"], y["item_id"] if y else None, y.get("quantity", 1) if y else 0, s.get("reveal_discovery_id"))
            agg[key] = agg.get(key, 0) + 1
        rows_r = []
        for (mat, yi, q, disc), cnt in agg.items():
            res = f'{lk(yi)} ×{n(q, lang)}' if yi else (e(t("reveals", lang)) + " " + e(DISCS[disc]["display_name"]) if disc in DISCS else "—")
            rows_r.append([lk(mat), n(cnt, lang), res])
        body += sec("resources", t("drill_sites", lang), f'<p>{e(t("drill_hint", lang))} <a href="{rel(S.item("item.tool.big_daddy_drill"))}">Big Daddy Drill</a>.</p>'
                    + table([(t("material", lang), "text"), (t("sites", lang), "num"), (t("yield", lang), "text")], rows_r))
    agg = {}
    for x in REGION.get("entities", []):
        if x["zone_id"] == zid and x["entity_type"] == 4:
            agg[x["content_id"]] = agg.get(x["content_id"], 0) + x.get("quantity", 1)
    if agg:
        body += sec("finds", t("finds", lang), ul([f'{img(i, "wk-ticon", 40)}{lk(i)} ×{n(q, lang)}' for i, q in agg.items()], "wk-list wk-items"))
    comps = fl.get("computers", [])
    if comps:
        body += sec("computers", t("computers", lang), ul([f'<a href="computers.html">{e(t("depot_booth", lang))}</a> <code>{e(c["id"])}</code>' for c in comps]))
    discs = [d for d in REGION.get("discoveries", []) if d["zone_id"] == zid]
    if discs:
        body += sec("discoveries", t("discoveries", lang), ul([f'<b>{e(DISCS[d["content_id"]]["display_name"])}</b> — {e(t("hidden_disc", lang))}' for d in discs if d["content_id"] in DISCS]))
    signs = zone_signs(zid)
    if signs:
        body += sec("signs", t("signs", lang), '<div class="wk-signs">' + "".join(
            f'<span class="wk-sign"><b>{e(a)}</b>{"<small>" + e(b) + "</small>" if b else ""}</span>' for _, _, a, b in signs) + "</div>")
    who = MENTIONED_BY.get(url, [])
    if who:
        body += sec("mentioned", t("mentioned_by", lang), '<p class="wk-see">' + " · ".join(lk(p) for p in who) + "</p>")
    nb = []
    for c in WORLD["connections"]:
        ids = [x["zone"] for x in c["ends"]]
        if zid in ids:
            nb += [lk(x) for x in ids if x != zid]
    body += seealso(lang, list(dict.fromkeys(nb)) + [f'<a href="zones.html">{e(t("zones", lang))}</a>', f'<a href="../world.html?zone={zid}#map">{e(t("world_map", lang))}</a>'])
    kicker = e(WM.KIND[z["kind"]][lang]) + " · " + e(WM.LAYER[z["layer"]][lang]) + (" · " + e(z["subtitle"][lang]) if z.get("subtitle") else "") + tag_status(z["status"] == "planned", lang)
    return article(lang, [(t("zones", lang), "zones.html"), (z["name"], None)], kicker, z["name"], "", box, body, secs_toc(body))


def districts_html(city, lang, L_):
    out = ""
    by_d = {}
    for p in PEOPLE.values():
        if p.get("zone") == city["zone"]:
            _, _, d = person_place(p)
            by_d.setdefault(d, []).append(p)
    for d in city["districts"] + city["entrances"]:
        svc = [f'{e(WM.SERVICES[s][lang])} <span class="tag tag-soon">{e(t("soon", lang))}</span>' if s != "service.depot" else
               f'<a href="computers.html">{e(WM.SERVICES[s][lang])}</a> <span class="tag tag-live">{e(t("works", lang))}</span>' for s in d.get("services", [])]
        lms = [lm for lm in city["landmarks"] if lm["id"] in d.get("landmarks", []) or lm.get("district") == d["id"]]
        lm_html = "".join(f'<p class="wk-lm"><b>{e(lm["name"][lang])}</b> — {L_(lm["note"][lang])}</p>' for lm in lms)
        ppl = ", ".join(f'<a href="{rel(S.person(p["id"]))}">{e(p["name"])}</a>' for p in sorted(by_d.get(d["id"], []), key=lambda x: x["name"]))
        num = f'<span class="wk-dnum">{e(d.get("number", "→"))}</span>'
        out += (f'<article class="wk-district" id="{S.district_anchor(d["id"])}">{num}<div><h3>{e(d["name"][lang])}</h3><p>{L_(d["purpose"][lang])}</p>'
                + (ul(svc) if svc else "") + lm_html + (f'<p class="wk-sub">{e(t("people", lang))}: {ppl}</p>' if ppl else "")
                + (f'<p>{map_link(lang, district=d["id"])}</p>' if d["id"].startswith("district.") else "") + "</div></article>")
    loose = by_d.get(None, [])
    if loose:
        out += f'<p class="wk-sub">{e(t("streets", lang))}: ' + ", ".join(f'<a href="{rel(S.person(p["id"]))}">{e(p["name"])}</a>' for p in loose) + "</p>"
    return sec("districts", t("districts", lang), f'<p>{e(t("services_note", lang))}</p>' + out)


def zones_index(lang):
    body = ""
    for status in ("playable", "planned"):
        rows = []
        for z in sorted((z for z in WORLD["zones"] if z["status"] == status), key=lambda z: (z["tier"], z["name"])):
            rows.append([f'<a href="{rel(S.zone(z["id"]))}">{e(z["name"])}</a>', e(WM.KIND[z["kind"]][lang]),
                         f'<i class="sw" style="background:{WM.BIOME_COLOR[z["biome"]]}"></i>{e(WM.BIOME[z["biome"]][lang])}',
                         e(WM.LAYER[z["layer"]][lang]), n(z.get("depth_m", 0), lang), f'T{z["tier"]}',
                         f'<span data-v="{WM.DANGER_ORDER.index(z["danger"])}">{e(WM.DANGER[z["danger"]][lang])}</span>',
                         n(sum(x["count"] for x in ZONE_MOBS.get(z["id"], [])), lang), n(len([p for p in PEOPLE.values() if p.get("zone") == z["id"]]), lang)])
        body += sec(status, t("zones_" + status, lang), table([(t("name", lang), "text"), (t("kind", lang), "text"), (t("biome", lang), "text"),
                                                              (t("layer", lang), "text"), (t("depth", lang) + " (m)", "num"), (t("tier", lang), "text"),
                                                              (t("danger", lang), "text"), (t("creatures", lang), "num"), (t("people", lang), "num")], rows))
    body += f'<p><a class="btn" href="../world.html#map">{e(t("world_map", lang))}</a></p>'
    return article(lang, [(t("zones", lang), None)], e(t("category_k", lang)), t("zones", lang), e(t("zones_lead", lang)), "", body, secs_toc(body))


# =================================================================================================================
# Materiales (puntos de perforacion)
# =================================================================================================================
def material_page(m, lang):
    mid = m["id"]
    url = S.material(mid)
    effort = m["durability"] / m["drill_effectiveness"]
    rows = [(t("hardness", lang), n(m["hardness"], lang)), (t("durability", lang), n(m["durability"], lang)),
            (t("drill_eff", lang), pct(m["drill_effectiveness"], lang)), (t("effort", lang), n(effort, lang, 0)),
            (t("disc_cat", lang), e(m.get("discovery_category", "").split(".")[-1].replace("_", " "))), ("ID", f"<code>{e(mid)}</code>")]
    box = infobox(m["display_name"], f'<span class="wk-icon wk-ph">{e(m["display_name"][:1])}</span>', rows)
    body = sec("about", t("about", lang), f'<p>{e(t("mat_lead", lang, eff=n(effort, lang, 0)))}</p>')
    rows_s = []
    for zid, sites in DRILL.items():
        for s in sites:
            if s["content_id"] != mid:
                continue
            y = s.get("yield")
            res = f'{lk(y["item_id"])} ×{n(y.get("quantity", 1), lang)}' if y else (e(t("reveals", lang)) + " " + e(DISCS.get(s.get("reveal_discovery_id"), {}).get("display_name", "—")))
            rows_s.append([lk(zid), res])
    body += sec("sites", t("drill_sites", lang), table([(t("zone", lang), "text"), (t("yield", lang), "text")], rows_s) if rows_s else f'<p class="wk-note">{e(t("no_sites", lang))}</p>')
    body += seealso(lang, [lk(o) for o in MATS if o != mid] + [f'<a href="../resources.html#rock">{e(t("rock_table", lang))}</a>', lk("item.tool.big_daddy_drill")])
    return article(lang, [(t("geology", lang), "geology.html"), (m["display_name"], None)], e(t("material", lang)), m["display_name"], "", box, body, secs_toc(body))


def geology_index(lang):
    rows = []
    for m in sorted(MATS.values(), key=lambda m: m["durability"] / m["drill_effectiveness"]):
        cnt = sum(1 for s in sum(DRILL.values(), []) if s["content_id"] == m["id"])
        ys = sorted({s["yield"]["item_id"] for s in sum(DRILL.values(), []) if s["content_id"] == m["id"] and s.get("yield")})
        rows.append([f'<a href="{rel(S.material(m["id"]))}">{e(m["display_name"])}</a>', n(m["hardness"], lang), n(m["durability"], lang),
                     pct(m["drill_effectiveness"], lang), n(m["durability"] / m["drill_effectiveness"], lang, 0), n(cnt, lang), ", ".join(lk(y) for y in ys) or "—"])
    body = sec("materials", t("materials", lang), table([(t("material", lang), "text"), (t("hardness", lang), "num"), (t("durability", lang), "num"),
                                                         (t("drill_eff", lang), "num"), (t("effort", lang), "num"), (t("sites", lang), "num"), (t("yield", lang), "text")], rows))
    drows = []
    placed = {d["content_id"]: d["zone_id"] for d in REGION.get("discoveries", [])}
    for d in DISCS.values():
        drows.append([e(d["display_name"]), e(d.get("category", "").split(".")[-1].replace("_", " ")), lk(placed[d["id"]]) if d["id"] in placed else e(t("not_placed_short", lang))])
    body += sec("discoveries", t("discoveries", lang), f'<p>{e(t("disc_lead", lang))}</p>' + table([(t("name", lang), "text"), (t("category", lang), "text"), (t("zone", lang), "text")], drows))
    return article(lang, [(t("geology", lang), None)], e(t("category_k", lang)), t("geology", lang), e(t("geology_lead", lang)), "", body, secs_toc(body))


# =================================================================================================================
# Misiones
# =================================================================================================================
def goal_html(goal, lang):
    gt = goal.get("type")
    if gt == "open_container":
        return t("g_open", lang) + " " + ", ".join(lk(x) for x in goal.get("targets", []))
    if gt == "equip_slot":
        return t("g_equip", lang) + " " + ", ".join(e(SLOTS.get(s, {}).get(lang, s)) for s in goal.get("slots", []))
    if gt == "light_on":
        return t("g_light", lang)
    if gt == "talk_to":
        return t("g_talk", lang) + " " + lk(goal.get("target"))
    if gt == "enter_zone":
        return t("g_enter", lang) + " " + lk(goal.get("target"))
    return e(gt or "—")


def quest_page(q, lang):
    url = S.quest(q["id"])
    L_ = Linker(url)
    giver = PEOPLE.get(q.get("giver"))
    xp = q.get("reward", {}).get("xp", 0)
    rows = [(t("giver", lang), lk(q.get("giver")) if giver else e(q.get("giver", "—"))),
            (t("zone", lang), lk(giver["zone"]) if giver and giver.get("zone") else "—"),
            (t("steps", lang), n(len(q["steps"]), lang)), (t("reward", lang), f'{n(xp, lang)} XP'),
            ("ID", f'<code>{e(q["id"])}</code>')]
    if giver is None:
        gap(f"{q['id']} giver {q.get('giver')} is not placed anywhere.")
    box = infobox(q["title"].title(), f'<span class="wk-icon wk-ph">!</span>', rows)
    off = q.get("offer", {})
    body = sec("offer", t("offer", lang), (f'<p class="wk-sub">{e(t("lines_note", lang))}</p>' if lang == "es" else "")
               + f'<blockquote class="wk-quote">{L_(off.get("text", ""))}</blockquote>'
               + f'<p class="wk-opts-inline"><span>“{e(off.get("accept", ""))}”</span> / <span>“{e(off.get("decline", ""))}”</span></p>')
    steps = ""
    es = QUEST_ES.get(q["id"], {})
    for i, st in enumerate(q["steps"]):
        obj = es.get(st["id"], st["objective"]) if lang == "es" else st["objective"]
        hl = st.get("highlight", {})
        hl_txt = (t("hl_sign", lang, s=hl["sign"]) if hl.get("sign") else (t("hl_npc", lang, p=REG[hl["npc"]].name) if hl.get("npc") in REG else ""))
        steps += (f'<li><p class="wk-step-t"><b>{e(obj)}</b></p><p class="wk-sub">{goal_html(st.get("goal", {}), lang)}'
                  f'{" · " + e(hl_txt) if hl_txt else ""}</p><blockquote class="wk-quote">{L_(st.get("lines", ""))}</blockquote>'
                  + (f'<p class="wk-opts-inline"><span>“{e(st["reply"])}”</span></p>' if st.get("reply") else "") + "</li>")
    body += sec("steps", t("steps", lang), f'<ol class="wk-steps">{steps}</ol>')
    body += sec("rewards", t("rewards", lang), f'<p>{t("reward_line", lang, xp=n(xp, lang), pct=pct(xp / max(1, G.xp_to_next(1)), lang))}</p>')
    body += seealso(lang, [lk(q.get("giver")), lk("item.container.supply_crate"), lk("item.container.gear_crate"), lk("zone.threshold"),
                           f'<a href="quests.html">{e(t("quests", lang))}</a>'])
    return article(lang, [(t("quests", lang), "quests.html"), (q["title"].title(), None)], e(t("quest", lang)), q["title"].title(), "", box, body, secs_toc(body))


def quests_index(lang):
    rows = [[lk(q["id"]), lk(q.get("giver")), lk(PEOPLE[q["giver"]]["zone"]) if q.get("giver") in PEOPLE and PEOPLE[q["giver"]].get("zone") else "—",
             n(len(q["steps"]), lang), n(q.get("reward", {}).get("xp", 0), lang)] for q in QUESTS]
    body = sec("list", t("quests", lang), table([(t("quest", lang), "text"), (t("giver", lang), "text"), (t("zone", lang), "text"),
                                                 (t("steps", lang), "num"), (t("reward", lang) + " (XP)", "num")], rows))
    return article(lang, [(t("quests", lang), None)], e(t("category_k", lang)), t("quests", lang), e(t("quests_lead", lang)), "", body, secs_toc(body))


# =================================================================================================================
# Mecanicas
# =================================================================================================================
def mech_article(lang, slug, lead, body, box=""):
    return article(lang, [(t("mechanics", lang), "index.html#mechanics"), (t(MECH[slug], lang), None)], e(t("mechanics", lang)),
                   t(MECH[slug], lang), e(lead), box, body, secs_toc(body))


def page_experience(lang):
    num_, den = G.RPG.get("XP_CURVE_NUMERATOR", 50), G.RPG.get("XP_CURVE_DENOMINATOR", 3)
    body = sec("curve", t("xp_curve", lang),
               f'<p class="eq">total_xp(L) = {num_}/{den} · (L³ − 6L² + 17L − 12)</p><p>{e(t("xp_curve_lead", lang, limit=n(G.RPG.get("LEVEL_LIMIT", 65535), lang)))}</p>')
    calc = f"""<div class="panel wk-calc" id="xpcalc" data-num="{num_}" data-den="{den}" data-lang="{lang}">
<label>{e(t("level", lang))} <input type="number" id="xp-l" min="1" max="65535" value="10" inputmode="numeric"></label>
<p class="wk-calc-out"><span><b id="xp-tot">—</b><small>{e(t("total_xp", lang))}</small></span><span><b id="xp-next">—</b><small>{e(t("xp_next", lang))}</small></span></p>
<label>{e(t("have_xp", lang))} <input type="number" id="xp-x" min="0" value="5000" inputmode="numeric"></label>
<p class="wk-calc-out"><span><b id="xp-lv">—</b><small>{e(t("level", lang))}</small></span><span><b id="xp-pct">—</b><small>{e(t("progress", lang))}</small></span></p>
</div>"""
    body += sec("calculator", t("xp_calc", lang), calc)
    levels = list(range(1, 21)) + [25, 30, 35, 40, 50, 60, 70, 80, 90, 100]
    rows = [[n(lv, lang), n(G.total_xp(lv), lang), n(G.xp_to_next(lv), lang), f'T{min(6, (lv - 1) // 7 + 1)}'] for lv in levels]
    body += sec("table", t("xp_table", lang), table([(t("level", lang), "num"), (t("total_xp", lang), "num"), (t("xp_next", lang), "num"), (t("tier", lang), "text")], rows))
    krows = []
    for m in sorted(MOBS.values(), key=lambda m: m.get("xp", 0)):
        xp = m.get("xp", G.RPG.get("XP_PER_NPC_KILL", 35))
        krows.append([lk(m["id"]), n(xp, lang), n(math.ceil(G.total_xp(2) / xp), lang), n(math.ceil(G.total_xp(10) / xp), lang),
                      n(math.ceil(G.total_xp(20) / xp), lang), n(math.ceil(G.total_xp(40) / xp), lang)])
    for q in QUESTS:
        krows.append([lk(q["id"]) + f' <small>({e(t("quest", lang))})</small>', n(q.get("reward", {}).get("xp", 0), lang), "—", "—", "—", "—"])
    body += sec("kill-xp", t("kill_xp", lang), f'<p>{e(t("kill_xp_lead", lang))}</p>'
                + table([(t("source", lang), "text"), (t("xp", lang), "num"), (t("kills_to", lang, l=2), "num"), (t("kills_to", lang, l=10), "num"),
                         (t("kills_to", lang, l=20), "num"), (t("kills_to", lang, l=40), "num")], krows))
    tiers = G.RPG.get("GEAR_TIER_MIN_LEVELS", [])
    trows = [[f"T{i + 1}", n(lv, lang), ", ".join(lk(it["id"]) for it in ITEMS.values() if it.get("gear_tier") == i + 1 and not it.get("planned")) or "—"]
             for i, lv in enumerate(tiers)]
    body += sec("tiers", t("gear_tiers", lang), f'<p>{e(t("tiers_lead", lang))}</p>' + table([(t("tier", lang), "text"), (t("from_level", lang), "num"), (t("items", lang), "text")], trows, sortable=False))
    per_lvl = G.SKILLS.get("DAMAGE_PER_CHARACTER_LEVEL", 0.006)
    crow = [[class_chip(c["id"], lang), n(c["carry"]["base"], lang) + " kg", "+" + n(c["carry"]["per_level"], lang) + " kg",
             n(c["carry"]["base"] + c["carry"]["per_level"] * 19, lang) + " kg"] for c in CLASSES]
    body += sec("per-level", t("per_level_t", lang), f'<p>{e(t("per_level_lead", lang, p=pct(per_lvl, lang, 1)))}</p>'
                + table([(t("class", lang), "text"), (t("carry", lang), "text"), (t("per_level", lang), "text"), (t("at_level", lang, l=20), "text")], crow, sortable=False))
    body += seealso(lang, [f'<a href="death.html">{e(t("m_death", lang))}</a>', f'<a href="skills.html">{e(t("m_skills", lang))}</a>', f'<a href="creatures.html">{e(t("creatures", lang))}</a>'])
    return mech_article(lang, "experience", t("xp_lead", lang), body)


def page_death(lang):
    D = G.DEATH
    xl, sl = D.get("XP_LOSS_FRACTION", 0.1), D.get("SKILL_XP_LOSS_FRACTION", 0.05)
    p1, p2 = D.get("EXTRA_DROP_CHANCE", 0.5), D.get("SECOND_DROP_CHANCE", 0.25)
    slots = D.get("EXTRA_DROP_SLOTS", [])
    all_slots = ["head", "chest", "arms", "legs", "boots", "primary_weapon", "secondary_weapon", "tool_special", "backpack", "battery", "light"]
    protected = [s for s in all_slots if s not in slots and s != "backpack"]
    remains = ITEMS.get(D.get("REMAINS_ITEM_ID"), {})
    lis = [t("d_xp", lang, p=pct(xl, lang)), t("d_skill", lang, p=pct(sl, lang)),
           t("d_backpack", lang, bp=lk("item.backpack.provisional_drift_pack")),
           t("d_extra", lang, a=pct(p1, lang), b=pct(p2, lang), both=pct(p1 * p2, lang, 1)),
           t("d_slots", lang, slots=", ".join(SLOTS.get(s, {}).get(lang, s.replace("_", " ").title()) for s in slots)),
           t("d_protected", lang, slots=", ".join(SLOTS[s][lang] for s in protected if s in SLOTS)),
           t("d_unqualified", lang),
           t("d_remains", lang, r=lk(D.get("REMAINS_ITEM_ID")), cells=n(remains.get("container", {}).get("cells", 0), lang), mins=n(D.get("CORPSE_DECAY_SECONDS", 1800) / 60, lang)),
           t("d_respawn", lang, s=n(D.get("RESPAWN_DELAY_SECONDS", 4), lang))]
    body = sec("rules", t("death_rules", lang), '<ol class="wk-steps wk-plain">' + "".join(f"<li>{x}</li>" for x in lis) + "</ol>")
    prob = [[n(0, lang), pct(1 - p1, lang, 1)], [n(1, lang), pct(p1 * (1 - p2), lang, 1)], [n(2, lang), pct(p1 * p2, lang, 1)]]
    body += sec("odds", t("drop_odds", lang), f'<p>{e(t("odds_lead", lang))}</p>' + table([(t("extra_items", lang), ""), (t("chance", lang), "")], prob, sortable=False))
    rows = []
    for lv in (2, 5, 10, 20, 40, 100):
        xp = G.total_xp(lv)
        after = xp - math.floor(xp * xl)
        rows.append([n(lv, lang), n(xp, lang), n(xp - after, lang), n(G.level_for_xp(after), lang)])
    body += sec("examples", t("death_examples", lang), f'<p>{e(t("examples_lead", lang))}</p>'
                + table([(t("level", lang), "num"), (t("total_xp", lang), "num"), (t("xp_lost", lang), "num"), (t("level_after", lang), "num")], rows, sortable=False))
    hrows = [[e(h["name"]), lk(h["zone_id"]), e(t("yes", lang)) if h["id"] == HUBS.get("default_hub") else "—"] for h in HUBS.get("hubs", [])]
    body += sec("hubs", t("respawn_hubs", lang), f'<p>{e(t("hubs_lead", lang))}</p>' + table([(t("hub", lang), "text"), (t("zone", lang), "text"), (t("default", lang), "text")], hrows, sortable=False))
    body += seealso(lang, [lk(D.get("REMAINS_ITEM_ID")), f'<a href="experience.html">{e(t("m_experience", lang))}</a>', f'<a href="skills.html">{e(t("m_skills", lang))}</a>'])
    return mech_article(lang, "death", t("death_lead", lang), body)


def page_skills(lang):
    K = G.SKILLS
    fams = K.get("FAMILIES", list(FAMILIES))
    rows = []
    for f in fams:
        desc = K.get("DESCRIPTIONS", {}).get(f, "") if lang == "en" else FAMILY_DESC[f]["es"]
        later = K.get("LATER", {}).get(f, "") if lang == "en" else ""
        ws = [lk(w["id"]) for w in ITEMS.values() if w.get("weapon_family") == f]
        best = max(CLASSES, key=lambda c: c["skill_affinity"].get(f, K.get("DEFAULT_AFFINITY", 0.5)))
        rows.append(f'<article class="wk-skill" id="{S.skill_anchor(f)}"><h3>{e(FAMILIES[f][lang])} <small>{e(K.get("NAMES", {}).get(f, ""))}</small></h3>'
                    f'<p>{e(desc)}</p>{"<p class=wk-sub>" + e(later) + "</p>" if later else ""}'
                    f'<p class="wk-sub">{e(t("weapons", lang))}: {", ".join(ws) or "—"} · {e(t("trains_best", lang))} {class_chip(best["id"], lang)}</p></article>')
    body = sec("families", t("families", lang), f'<p>{e(t("skills_lead2", lang, hit=K.get("XP_PER_HIT", 10), block=K.get("XP_PER_BLOCKED_HIT", 8), d=K.get("DEFAULT_AFFINITY", 0.5), max=K.get("MAX_LEVEL", 100), dmg=pct(K.get("DAMAGE_PER_SKILL_LEVEL", 0.01), lang)))}</p>' + "".join(rows))
    head = [(t("skill", lang), "text")] + [(c["name"], "num") for c in CLASSES]
    arows = []
    for f in fams:
        cells = []
        for c in CLASSES:
            v = c["skill_affinity"].get(f, K.get("DEFAULT_AFFINITY", 0.5))
            cls = "hot" if v >= 1.4 else ("cold" if v < 0.9 else "")
            cells.append(f'<span class="aff-v {cls}">×{n(v, lang)}</span>')
        arows.append([f'<a href="#{S.skill_anchor(f)}">{e(FAMILIES[f][lang])}</a>'] + cells)
    body += sec("affinity", t("affinity", lang), f'<p>{e(t("affinity_lead", lang))}</p>' + table(head, arows))
    srows = [[n(lv, lang), n(G.skill_xp_for(lv), lang), n(math.ceil(G.skill_xp_for(lv) / K.get("XP_PER_HIT", 10)), lang), "+" + pct(K.get("DAMAGE_PER_SKILL_LEVEL", 0.01) * (lv - 1), lang)]
             for lv in (2, 5, 10, 20, 30, 50, 75, 100)]
    body += sec("curve", t("skill_curve", lang), table([(t("skill_level", lang), "num"), (t("total_xp", lang), "num"), (t("hits", lang), "num"), (t("damage", lang), "text")], srows, sortable=False)
                + f'<p class="note">{e(t("shield_note", lang, base=pct(K.get("SHIELD_REDUCTION_BASE", 0.08), lang), per=pct(K.get("SHIELD_REDUCTION_PER_LEVEL", 0.002), lang, 1)))}</p>')
    C = G.COMBAT
    prow = []
    for sid in C.get("ALL", []):
        owner = [c for c in CLASSES if c.get("ability_id") == sid]
        prow.append([f'<b>{e(C["NAMES"].get(sid, sid))}</b>', ", ".join(class_chip(c["id"], lang) for c in owner) or e(t("every_class", lang)),
                     e("Q" if sid in C.get("MOBILITY", []) else "C"), secs(C.get("DASH_COOLDOWN") if sid == C.get("DASH") else C.get("POWER_COOLDOWNS", {}).get(sid, C.get("ABILITY_COOLDOWN", 12)), lang),
                     n(C.get("DASH_ENERGY_COST") if sid == C.get("DASH") else C.get("ABILITY_ENERGY_COST", 15), lang),
                     e(C.get("DESCRIPTIONS", {}).get(sid, "")) if lang == "en" else e(power_es(sid))])
    body += sec("powers", t("powers", lang), f'<p>{e(t("powers_lead", lang))}</p>' + table([(t("name", lang), ""), (t("class", lang), ""), (t("key", lang), ""), (t("cooldown", lang), ""), (t("energy", lang), ""), (t("description", lang), "")], prow, sortable=False, cls="wrap-cells"))
    pas = [[class_chip(c["id"], lang), f'<b>{e(c["passive_name"])}</b>', e(c.get("passive_description", "")) if lang == "en" else e(CLASS_TXT[c["id"]]["passive_desc"]["es"])] for c in CLASSES]
    body += sec("passives", t("passives", lang), table([(t("class", lang), ""), (t("name", lang), ""), (t("description", lang), "")], pas, sortable=False, cls="wrap-cells"))
    body += seealso(lang, [f'<a href="classes.html">{e(t("m_classes", lang))}</a>', f'<a href="../arsenal.html#calculator">{e(t("calc", lang))}</a>', f'<a href="death.html">{e(t("m_death", lang))}</a>'])
    return mech_article(lang, "skills", t("skills_lead", lang), body)


def power_es(sid):
    m = {c["ability_id"]: CLASS_TXT[c["id"]]["power_desc"]["es"] for c in CLASSES}
    if sid in m:
        return m[sid]
    return "Te impulsás unos metros en la dirección en la que te movés (o mirás)." if sid == G.COMBAT.get("DASH") else ""


def page_classes(lang):
    cards = ""
    for c in CLASSES:
        k = CLASS_KEY[c["id"]]
        top = sorted(c["skill_affinity"].items(), key=lambda x: -x[1])[:3]
        starts = ", ".join(lk(v["weapon_id"]) for v in c["variants"])
        cards += (f'<article class="wk-class" style="--c:#{c["visual_color"]}" id="{k}"><img src="../../assets/img/concept/class_{k}.jpg" alt="" loading="lazy">'
                  f'<div><p class="kicker">{e(CLASS_TXT[c["id"]]["title"][lang])} · {e(CLASS_TXT[c["id"]]["role"][lang])}</p><h3><a href="../classes.html#{k}">{e(c["name"])}</a></h3>'
                  f'<p>{e(CLASS_TXT[c["id"]]["fantasy"][lang])}</p>'
                  f'<dl class="kv"><div><dt>{e(t("power", lang))}</dt><dd><a href="skills.html#powers">{e(c["ability_name"])}</a></dd></div>'
                  f'<div><dt>{e(t("passive", lang))}</dt><dd><a href="skills.html#passives">{e(c["passive_name"])}</a></dd></div>'
                  f'<div><dt>{e(t("carry", lang))}</dt><dd>{n(c["carry"]["base"], lang)} kg</dd></div></dl>'
                  f'<p class="wk-sub">{e(t("starting_title", lang))}: {starts}</p>'
                  f'<p class="wk-sub">{e(t("trains_fast", lang))}: ' + ", ".join(f'<a href="skills.html#{S.skill_anchor(f)}">{e(FAMILIES[f][lang])}</a> ×{n(v, lang)}' for f, v in top) + "</p></div></article>")
    body = sec("classes", t("m_classes", lang), f'<div class="wk-classes">{cards}</div><p><a class="btn" href="../classes.html">{e(t("full_classes", lang))}</a></p>')
    return mech_article(lang, "classes", t("classes_lead", lang), body)


def page_vehicles(lang):
    body = ""
    box = ""
    for v in VEHICLES:
        rows = [(t("seats", lang), n(v["seats"], lang)), (t("max_speed", lang), n(v["max_speed"], lang) + " m/s"),
                (t("accel", lang), n(v["acceleration"], lang) + " m/s²"), (t("decel", lang), n(v["deceleration"], lang) + " m/s²"),
                (t("turn", lang), n(v["turn_rate"], lang) + " rad/s"), (t("fuel", lang), f'{n(v["starting_fuel"], lang)} / {n(v["max_fuel"], lang)}'),
                (t("fuel_per_m", lang), n(v["fuel_per_meter"], lang)), (t("range_start", lang), "≈ " + n(v["starting_fuel"] / v["fuel_per_meter"], lang) + " m"),
                (t("range_full", lang), "≈ " + n(v["max_fuel"] / v["fuel_per_meter"], lang) + " m"),
                (t("low_fuel", lang), pct(v["low_fuel_fraction"], lang)), (t("durability", lang), n(v["max_durability"], lang)),
                (t("mount_range", lang), n(v["mount_range"], lang) + " m"), ("ID", f'<code>{e(v["id"])}</code>')]
        box = infobox(v["display_name"], '<img class="wk-icon" src="../../assets/img/concept/machine_mule.jpg" alt="" loading="lazy">', rows)
        lis = [t("v_get", lang), t("v_controls", lang, r=n(v["mount_range"], lang)), t("v_fuel", lang, f=n(v["fuel_per_meter"], lang), m=n(1 / v["fuel_per_meter"], lang)),
               t("v_empty", lang, low=pct(v["low_fuel_fraction"], lang)), t("v_rules", lang), t("v_zone", lang), t("v_owner", lang)]
        body += sec("rules", t("v_rules_t", lang), ul([e(x) for x in lis]))
        body += sec("planned", t("soon", lang), ul([e(x) for x in W["v_planned"][lang]]))
    body += seealso(lang, [f'<a href="../world.html#machines">{e(t("excavators", lang))}</a>', lk("zone.frontier_road_east")])
    return mech_article(lang, "vehicles", t("vehicles_lead", lang), body, box)


def page_currency(lang):
    coins = sorted([i for i in ITEMS.values() if item_cat(i["id"]) == "currency"], key=lambda i: i["properties"]["currency_value"])
    rows = [[f'<span class="tn-in">{img(c["id"], "wk-ticon", 40)}{lk(c["id"])}</span>', n(c["properties"]["currency_value"], lang) + " Metal",
             n(c["properties"].get("stack_size", 1), lang), n(c.get("weight", 0), lang) + " kg",
             n(c.get("weight", 0) * c["properties"].get("stack_size", 1), lang) + " kg", e(t("soon", lang)) if c.get("planned") else e(t("in_game", lang))] for c in coins]
    body = sec("coins", t("coins_t", lang), table([(t("name", lang), "text"), (t("value", lang), "num"), (t("stack", lang), "num"), (t("weight", lang), "num"),
                                                   (t("full_stack", lang), "num"), (t("status", lang), "text")], rows))
    mrows = [[lk(m["id"]), rng(m["coins"][0], m["coins"][1], lang), n((m["coins"][0] + m["coins"][1]) / 2, lang, 1),
              n((m["coins"][0] + m["coins"][1]) / 2 / max(1, m.get("xp", 1)) * 100, lang, 1)] for m in sorted(MOBS.values(), key=lambda m: m.get("coins", [0, 0])[1]) if m.get("coins")]
    body += sec("sources", t("coin_sources", lang), f'<p>{e(t("coin_sources_lead", lang))}</p>'
                + table([(t("creature", lang), "text"), (t("coins", lang), "text"), (t("average", lang), "num"), (t("per_100xp", lang), "num")], mrows))
    body += sec("sinks", t("coin_sinks", lang), f'<p>{t("coin_sinks_lead", lang, death="death.html")}</p>')
    body += seealso(lang, [lk(c["id"]) for c in coins] + [lk("zone.dustline"), f'<a href="../resources.html#currency">{e(t("resources", lang))}</a>'])
    return mech_article(lang, "currency", t("currency_lead", lang), body)


def page_computers(lang):
    rows = []
    for zid, fl in FLOORS.items():
        for c in fl.get("computers", []):
            best = None
            for sx, sz, txt, sub in zone_signs(zid):
                d = math.hypot(sx - c["position"][0], sz - c["position"][1])
                if best is None or d < best[0]:
                    best = (d, txt)
            rows.append([lk(zid), f'<code>{e(c["id"])}</code>', e(t("near_sign", lang, sign=best[1])) if best and best[0] < 12 else "—"])
    body = sec("booths", t("booths", lang), table([(t("zone", lang), "text"), ("ID", "text"), (t("location", lang), "text")], rows))
    lis = [t("c_use", lang, r=n(CONST.get("REACH", 2.5), lang)), t("c_login", lang, addr=e(CONST.get("NETWORK_ADDRESS", "261.6.66"))),
           t("c_menu", lang), t("c_depot", lang, cells=n(CONST.get("CELLS", 40), lang)), t("c_shared", lang)]
    body += sec("how", t("how_it_works", lang), '<ol class="wk-steps wk-plain">' + "".join(f"<li>{x}</li>" for x in lis) + "</ol>"
                + f'<pre class="wk-term">guest@outpost-7:~$ connect {e(CONST.get("NETWORK_ADDRESS", "261.6.66"))}</pre>')
    body += seealso(lang, [lk("zone.outpost"), lk("zone.dustline"), lk("npc.dustline_exchange_clerk")])
    return mech_article(lang, "computers", t("computers_lead", lang), body)


# =================================================================================================================
# Portada del wiki
# =================================================================================================================
def wiki_index(lang):
    cats = [("items.html", t("items", lang), len(ITEMS), t("items_d", lang)), ("creatures.html", t("creatures", lang), len(MOBS), t("creatures_d", lang)),
            ("people.html", t("people", lang), len(PEOPLE), t("people_d", lang)), ("zones.html", t("zones", lang), len(ZONES), t("zones_d", lang)),
            ("quests.html", t("quests", lang), len(QUESTS), t("quests_d", lang)), ("creatures.html#factions", t("factions", lang), len(FACTIONS), t("factions_d", lang)),
            ("geology.html", t("geology", lang), len(MATS), t("geology_d", lang))]
    cards = "".join(f'<a class="wk-cat" href="{u_}"><b>{n(c, lang)}</b><h3>{e(a)}</h3><p>{e(d)}</p></a>' for u_, a, c, d in cats)
    mech = "".join(f'<a class="wk-card" href="{k}.html"><span><b>{e(t(v, lang))}</b><small>{e(t(v + "_d", lang))}</small></span></a>' for k, v in MECH.items())
    start = [lk("zone.outpost"), lk("npc.miner_guide"), lk(QUESTS[0]["id"]) if QUESTS else "", lk("item.container.gear_crate"), lk("zone.dustline"), lk("npc.dragon"), lk("zone.dragon_lair")]
    search = (f'<button type="button" class="wk-search" data-search-open><svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">'
              f'<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/></svg><span>{e(t("search_wiki", lang))}</span><kbd>/</kbd></button>')
    pages = len(REG) + len(MECH) + 7
    body = f"""<div class="wrap wk wk-home">
<nav class="crumbs" aria-label="breadcrumb"><a href="../index.html">{e(t("home", lang))}</a><span aria-hidden="true">›</span><span aria-current="page">Wiki</span></nav>
<header class="wk-head"><p class="kicker">{e(t("field_archive", lang))}</p><h1>{e(t("wiki_title", lang))}</h1><p class="lead">{e(t("wiki_lead", lang, n=pages))}</p>{search}</header>
<section class="wk-sec" id="categories"><h2>{e(t("categories", lang))}</h2><div class="wk-cats">{cards}</div></section>
<section class="wk-sec" id="mechanics"><h2>{e(t("mechanics", lang))}</h2><div class="wk-cards">{mech}</div></section>
<section class="wk-sec" id="start"><h2>{e(t("start_here", lang))}</h2><p class="wk-see">{" · ".join(x for x in start if x)}</p></section>
<section class="wk-sec" id="guides"><h2>{e(t("guides", lang))}</h2><p class="wk-see"><a href="../manual.html">{e(t("manual", lang))}</a> · <a href="../classes.html">{e(t("full_classes", lang))}</a> · <a href="../arsenal.html">Arsenal</a> · <a href="../gear.html">{e(t("gear", lang))}</a> · <a href="../bestiary.html">{e(t("bestiary", lang))}</a> · <a href="../world.html">{e(t("world_map", lang))}</a> · <a href="../story.html">{e(t("story", lang))}</a></p></section>
</div>"""
    return body


# =================================================================================================================
# Indice de busqueda
# =================================================================================================================
def search_index(lang):
    out = []
    for en in REG.values():
        if en.kind == "item":
            it = ITEMS[en.id]
            sub = CATS[item_cat(en.id)][lang] + (" · " + t("soon", lang) if it.get("planned") else "")
        elif en.kind == "mob":
            mm = MOBS[en.id]
            sub = " · ".join(x for x in (FACTIONS[mm["faction"]]["name"] if mm.get("faction") in FACTIONS else "", role_name(mm.get("role"), lang) if mm.get("role") else "") if x)
        elif en.kind == "npc":
            p = PEOPLE[en.id]
            sub = (p["role"] + " · " if p["role"] else "") + (ZONES[p["zone"]]["name"] if p.get("zone") in ZONES else "")
        elif en.kind == "zone":
            sub = t("zone", lang) + " · " + WM.STATUS[ZONES[en.id]["status"]][lang]
        else:
            sub = t(en.kind, lang)
        out.append({"n": en.name, "s": sub, "u": en.url, "k": en.kind, "i": ("../assets/img/icons/" + en.id + ".png") if has_icon(en.id) else ""})
    for k, v in MECH.items():
        out.append({"n": t(v, lang), "s": t("mechanics", lang), "u": f"wiki/{k}.html", "k": "mech", "i": ""})
    for f in FAMILIES:
        out.append({"n": FAMILIES[f][lang], "s": t("skill", lang), "u": f"wiki/skills.html#{S.skill_anchor(f)}", "k": "mech", "i": ""})
    for c in CLASSES:
        out.append({"n": c["name"].title(), "s": t("class", lang) + " · " + CLASS_TXT[c["id"]]["title"][lang], "u": f"classes.html#{CLASS_KEY[c['id']]}", "k": "class", "i": ""})
        out.append({"n": c["ability_name"], "s": t("power", lang) + " · " + c["name"].title(), "u": "wiki/skills.html#powers", "k": "mech", "i": ""})
    city = WORLD.get("dustline")
    if city:
        for d in city["districts"]:
            out.append({"n": d["name"][lang], "s": t("district", lang) + " · Dustline", "u": S.zone(city["zone"]) + "#" + S.district_anchor(d["id"]), "k": "zone", "i": ""})
    for slug, label in (("story", t("story", lang)), ("manual", t("manual", lang)), ("arsenal", "Arsenal"), ("gear", t("gear", lang)),
                        ("bestiary", t("bestiary", lang)), ("world", t("world_map", lang)), ("resources", t("resources", lang))):
        out.append({"n": label, "s": t("page", lang), "u": f"{slug}.html", "k": "page", "i": ""})
    return "window.DKS=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n"


# =================================================================================================================
def build(page):
    """page = build.page; escribe en/wiki y es/wiki. Devuelve la cantidad de paginas por idioma."""
    count = 0
    for lang in ("en", "es"):
        os.makedirs(os.path.join(ROOT, lang, "wiki"), exist_ok=True)
        out = {}
        out["index"] = (t("wiki_title", lang), wiki_index(lang), t("wiki_lead", lang, n=len(REG)))
        out["items"] = (t("items", lang), items_index(lang), None)
        out["creatures"] = (t("creatures", lang), creatures_index(lang), None)
        out["people"] = (t("people", lang), people_index(lang), None)
        out["zones"] = (t("zones", lang), zones_index(lang), None)
        out["quests"] = (t("quests", lang), quests_index(lang), None)
        out["geology"] = (t("geology", lang), geology_index(lang), None)
        for it in ITEMS.values():
            out[S.item(it["id"])[5:-5]] = (it["display_name"], item_page(it, lang), item_desc(it, lang)[:160] or None)
        for m in MOBS.values():
            out[S.mob(m["id"])[5:-5]] = (m["display_name"], mob_page(m, lang), None)
        for f in FACTIONS.values():
            out[S.faction(f["id"])[5:-5]] = (f["name"], faction_page(f, lang), None)
        for p in PEOPLE.values():
            out[S.person(p["id"])[5:-5]] = (p["name"], person_page(p, lang), None)
        for z in WORLD["zones"]:
            out[S.zone(z["id"])[5:-5]] = (z["name"], zone_page(z, lang), z["summary"][lang][:160])
        for m in MATS.values():
            out[S.material(m["id"])[5:-5]] = (m["display_name"], material_page(m, lang), None)
        for q in QUESTS:
            out[S.quest(q["id"])[5:-5]] = (q["title"].title(), quest_page(q, lang), None)
        builders = {"experience": page_experience, "death": page_death, "skills": page_skills, "classes": page_classes,
                    "vehicles": page_vehicles, "currency": page_currency, "computers": page_computers}
        for k, fn in builders.items():
            out[k] = (t(MECH[k], lang), fn(lang), None)
        for slug, (title, body, desc) in out.items():
            extra = '<script defer src="../../assets/js/wiki.js"></script>' if slug == "experience" else ""
            with open(os.path.join(ROOT, lang, "wiki", slug + ".html"), "w") as fh:
                fh.write(page(lang, "wiki/" + slug, title, body, desc=desc, extra_head=extra, body_class="wiki-page"))
        with open(os.path.join(ROOT, lang, "wiki", "search.js"), "w") as fh:
            fh.write(search_index(lang))
        count = len(out)
    return count
