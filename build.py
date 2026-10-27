#!/usr/bin/env python3
"""Genera el sitio de DEEPKIN (en/ y es/) a partir de data/ y src/.

    python3 build.py           # genera en/ es/ index.html
    python3 build.py --sync    # antes copia data/entities del repo del juego (../deepkin)

Los numeros de clases y armas usan las mismas formulas que el servidor
(shared/gameplay/rpg_rules.gd, weapon_skills.gd, combat_skills.gd del juego).
"""
import glob
import html
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from i18n import (ATTR_DESC, ATTRS, CLASSES, DASH, FACTION, FAMILIES, FAMILY_DESC, FOUND_IN, ITEM_EN_FALLBACK,  # noqa: E402
                  ITEM_ES, MATERIAL_NAMES_ES, MOBS, NAV, SLOTS, TRAITS, UI, L)
from story import STORY  # noqa: E402
import gdconst as GD  # noqa: E402
import combat_math as CM  # noqa: E402
import slugs as SL  # noqa: E402
import texts as TX  # noqa: E402
import worldmap as WM  # noqa: E402
import atlas as AT  # noqa: E402
import lore as LO  # noqa: E402
from wiki_i18n import MOB_ES, MOB_SHOTS  # noqa: E402
from wiki_es_p8 import ITEM_ES_P8, MOB_ES_P8  # noqa: E402

ITEM_ES.update(ITEM_ES_P8)  # Fase 8 (2026-10-23): textos en español del contenido nuevo, tambien para Arsenal/Equipo/Bestiario
MOB_ES.update(MOB_ES_P8)

LANGS = ("en", "es")
GAME_REPO = os.path.join(os.path.dirname(ROOT), "deepkin")

# --- Reglas del juego (copiadas de shared/gameplay/*.gd) -------------------
BASE_HEALTH, HEALTH_PER_END, STAMINA_PER_END = 76, 4, 5
GEAR_TIER_LEVELS = GD.RPG.get("GEAR_TIER_MIN_LEVELS", [1, 8, 15, 22, 29, 36])
# Sin tope de nivel desde 2026-10-10 (curva de Tibia): el deslizador de la calculadora llega a 100.
MAX_LEVEL = 100
POWER_COOLDOWNS = {"ability.bastion": 14, "ability.long_shot": 12, "ability.bloom": 16, "ability.overload": 12}
POWER_MULT = {"ability.long_shot": 2.5, "ability.overload": 3.0}
DASH_COOLDOWN, DASH_COST, POWER_COST = 5, 6, 15
SKILL_MAX = 100


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def stat_mult(v):
    return clamp(1 + (v - 10) * 0.015, 0.75, 1.25)


def class_damage(c, w, ammo=None, skill=1, level=1):
    """Golpe base (sin rasgo) con la municion propia del arma: src/combat_math.py."""
    return CM.hit(c, w, ITEMS, 0.0, skill, level)


def base_damage(w):
    return w.get("properties", {}).get("base_damage", 0)


def derived(c):
    a = c["attributes"]
    armor = c["base_armor"] * c["combat_coefficients"]["defense"]
    res = c["base_resistance"] + (a["endurance"] - 8) * 0.5
    return {
        "health": BASE_HEALTH + a["endurance"] * HEALTH_PER_END,
        "stamina": a["endurance"] * STAMINA_PER_END,
        "armor": round(armor, 1),
        "armor_pct": round(100 * min(0.75, armor / (armor + 100))),
        "res": round(res, 1),
        "res_pct": round(100 * min(0.75, res / (res + 100))),
        "speed": c["movement_speed"],
        "energy": int(c["energy_capacity"]),
        "carry": c["carry"]["base"],
        "carry_lvl": c["carry"]["per_level"],
        "accuracy": round(100 * clamp(0.85 + (a["precision"] - 10) * 0.01, 0.5, 1.0)),
        "weakpoint": round(clamp(1 + (a["precision"] - 10) * 0.03, 0.7, 1.3), 2),
        "stagger": round(clamp(1 + (a["might"] - 10) * 0.02, 0.7, 1.3), 2),
        "power_cost": round(max(POWER_COST * 0.7, POWER_COST * (1 - (a["technology"] - 10) * 0.015)), 1),
    }


def xp_to_next(level):
    return GD.xp_to_next(level)


def skill_xp_for(level):
    return round(30.0 * (level - 1) ** 1.7)


# --- Datos -------------------------------------------------------------------
def load():
    classes = json.load(open(os.path.join(ROOT, "data/classes/classes.json")))["classes"]
    items = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "data/items/*.json"))):
        d = json.load(open(f))
        if not d.get("retired"):
            items[d["id"]] = d
    npcs = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(ROOT, "data/npcs/*.json")))]
    mats = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(ROOT, "data/materials/*.json")))]
    factions = json.load(open(os.path.join(ROOT, "data/factions/factions.json")))["factions"]
    return classes, items, npcs, mats, factions


CLASSES_DATA, ITEMS, NPCS, MATS, FACTIONS = load()
ROLE_ES = {"swarm": "Enjambre", "brute": "Bruto", "skirmisher": "Hostigador"}
from wiki_i18n import ROLES as _ROLES  # noqa: E402  roles nuevos (Fases 2-3, 2026-10-23): a distancia, controlador, jefe...
ROLE_ES.update({k: v["es"] for k, v in _ROLES.items() if k not in ROLE_ES})


def merge_mob_texts():
    """Lore, habitat y reglas del bestiario: ingles desde data/npcs, español desde wiki_i18n.MOB_ES (2026-10-10)."""
    for n in NPCS:
        es = MOB_ES.get(n["id"])
        if not es or not n.get("lore"):
            continue
        M = MOBS.setdefault(n["id"], {})
        M["lore"] = L(n["lore"].replace("PROVISIONAL. ", ""), es["lore"])
        M["habitat"] = L(n["habitat"], es["habitat"])
        M["rules"] = L(n["rules"], es["rules"])
        if "role" not in M:
            M["role"] = L(n.get("role", "").title(), ROLE_ES.get(n.get("role"), n.get("role", "").title()))


merge_mob_texts()
CLASS_BY_ID = {c["id"]: c for c in CLASSES_DATA}
CLASS_KEY = {"class.foundry": "foundry", "class.drift": "drift", "class.verdant": "verdant", "class.relay": "relay"}
WEAPONS = [i for i in ITEMS.values() if i.get("equipment_slot") == "primary_weapon"]
STARTER_OF = {}
for _c in CLASSES_DATA:
    for _w in _c["starter_weapons"]:
        STARTER_OF.setdefault(_w, []).append(_c["id"])
STARTING_OF = {v["weapon_id"]: c["id"] for c in CLASSES_DATA for v in c["variants"]}


# --- Helpers de HTML ---------------------------------------------------------
def e(s):
    return html.escape(str(s), quote=True)


def t(d, lang):
    return d[lang] if isinstance(d, dict) and lang in d else d


def u(key, lang):
    return UI[key][lang]


def num(v, lang, digits=None):
    if digits is not None:
        s = f"{v:.{digits}f}"
    elif isinstance(v, float) and not v.is_integer():
        s = f"{v:g}"
    else:
        s = f"{int(v):,}" if isinstance(v, (int, float)) else str(v)
    if lang == "es":
        s = s.replace(",", " ").replace(".", ",")
    return s


def item_desc(item, lang):
    if lang == "es":
        return ITEM_ES.get(item["id"], item.get("description", ""))
    return item.get("description") or ITEM_EN_FALLBACK.get(item["id"], "")


def icon(item_id, cls="icon", alt=""):
    path = f"../assets/img/icons/{item_id}.png"
    return f'<img class="{cls}" src="{path}" alt="{e(alt)}" loading="lazy" width="160" height="160">'


def shot(base, alt="", cls="", eager=False):
    """Captura del juego en webp (2026-10-10): base sin extension, con variante _800 para pantallas chicas."""
    c = f' class="{cls}"' if cls else ""
    return (f'<picture><source media="(max-width: 720px)" srcset="../assets/img/{base}_800.webp" type="image/webp">'
            f'<img{c} src="../assets/img/{base}.webp" alt="{e(alt)}" width="1600" height="900"{"" if eager else " loading=" + chr(34) + "lazy" + chr(34)} decoding="async"></picture>')


def shot_strip(more, lang):
    """Tira de capturas extra de una region (miniaturas de 800 px con epigrafe)."""
    if not more:
        return ""
    figs = "".join(f'<figure><a href="../assets/img/{b}.webp"><img src="../assets/img/{b}_800.webp" alt="{e(c[lang])}" width="800" height="450" loading="lazy" decoding="async"></a>'
                   f'<figcaption>{e(c[lang])}</figcaption></figure>' for b, c in more)
    return f'<div class="region-shots">{figs}</div>'


def status_tag(item, lang):
    if item.get("planned"):
        return f'<span class="tag tag-soon">{u("planned", lang)}</span>'
    if item["id"] == "item.weapon.provisional_rivet_caster":
        return f'<span class="tag tag-proto">{u("prototype", lang)}</span>'
    return ""


def bar(value, maximum, color="var(--amber)"):
    pct = clamp(100 * value / maximum, 2, 100) if maximum else 0
    return f'<span class="bar"><span style="width:{pct:.1f}%;background:{color}"></span></span>'


def class_color(cid):
    return "#" + CLASS_BY_ID[cid]["visual_color"]


def class_chip(cid, lang, link=True):
    c = CLASS_BY_ID[cid]
    inner = f'<i style="background:{class_color(cid)}"></i>{e(c["name"])}'
    if link:
        return f'<a class="chip" href="classes.html#{CLASS_KEY[cid]}">{inner}</a>'
    return f'<span class="chip">{inner}</span>'


SVG_ICONS = {
    "explore": '<path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm3.5 6.5-2 5-5 2 2-5 5-2Z"/>',
    "drill": '<path d="M4 10h9l3-2v8l-3-2H4zM16 9l5 3-5 3"/>',
    "gear": '<path d="M12 3 4 6v6c0 4.5 3.4 8.2 8 9 4.6-.8 8-4.5 8-9V6l-8-3Z"/>',
    "crew": '<circle cx="8" cy="9" r="3"/><circle cx="16" cy="9" r="3"/><path d="M2.5 20c.8-3 3-5 5.5-5s4.7 2 5.5 5M10.5 20c.8-3 3-5 5.5-5s4.7 2 5.5 5"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "close": '<path d="M6 6l12 12M18 6 6 18"/>',
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.7 3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3Z"/>',
}


def svg(name, cls="ico"):
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{SVG_ICONS[name]}</svg>')


def radar(c, lang, size=180):
    """Radar de 4 atributos (maximo 20)."""
    order = ["might", "endurance", "precision", "technology"]
    cx = cy = size / 2
    r = size / 2 - 22
    pts_axis = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    rings = ""
    for k in (0.25, 0.5, 0.75, 1):
        p = " ".join(f"{cx + (x - cx) * k:.1f},{cy + (y - cy) * k:.1f}" for x, y in pts_axis)
        rings += f'<polygon points="{p}" class="ring"/>'
    axes = "".join(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" class="axis"/>' for x, y in pts_axis)
    vals = [c["attributes"][a] / 20 for a in order]
    p = " ".join(f"{cx + (x - cx) * v:.1f},{cy + (y - cy) * v:.1f}" for (x, y), v in zip(pts_axis, vals))
    col = class_color(c["id"])
    labels = ""
    pos = [(cx, 12, "middle"), (size - 2, cy + 4, "end"), (cx, size - 4, "middle"), (2, cy + 4, "start")]
    short = ["MIG", "END", "PRE", "TEC"] if lang == "en" else ["FUE", "VIG", "PRE", "TEC"]
    for (x, y, anchor), s, a in zip(pos, short, order):
        labels += f'<text x="{x}" y="{y}" text-anchor="{anchor}">{s} {c["attributes"][a]}</text>'
    return (f'<svg class="radar" viewBox="0 0 {size} {size}" role="img" aria-label="attributes">{rings}{axes}'
            f'<polygon points="{p}" fill="{col}33" stroke="{col}" stroke-width="2"/>{labels}</svg>')


# --- Intro de terminal (2026-10-11): sólo portada, primera visita; ver site.js ----------------
INTRO_HEAD = ('<script>try{if(!localStorage.getItem("dk-intro")&&!/[?&]nointro/.test(location.search))'
              'document.documentElement.classList.add("dk-intro-on")}catch(e){}</script>\n')


def intro_html(lang):
    skip = "Skip ▸" if lang == "en" else "Saltar ▸"
    return (f'<div class="dk-intro" id="dk-intro" role="dialog" aria-label="DEEPKIN"><canvas class="dki-rain" aria-hidden="true"></canvas>'
            f'<div class="dki-bar" aria-hidden="true"><i></i></div><div class="dki-in"><pre class="dki-log" aria-hidden="true"></pre>'
            f'<p class="dki-big" aria-live="polite"></p><img class="dki-logo" src="../assets/img/deepkin_logo.png" alt="DEEPKIN — What lies below" width="1356" height="559"></div>'
            f'<button type="button" class="dki-skip">{skip}</button><div class="dki-scan" aria-hidden="true"></div></div>\n')


# --- Layout ------------------------------------------------------------------
def page(lang, slug, title, body, desc=None, extra_head="", body_class="", alt=None):
    """slug puede llevar subcarpetas ("wiki/item-x"): las rutas relativas suben lo necesario (2026-10-10)."""
    other = "es" if lang == "en" else "en"
    up = "../" * slug.count("/")
    alt = alt or slug
    nav = ""
    for s, label in NAV:
        cur = ' aria-current="page"' if s == slug or (s == "wiki/index" and slug.startswith("wiki/")) else ""
        nav += f'<a href="{up}{s}.html"{cur}>{e(label[lang])}</a>'
    full_title = "DEEPKIN — " + u("what_lies_below", lang) if slug == "index" else f"{title} · DEEPKIN"
    search_btn = (f'<button class="searchbtn" type="button" data-search-open aria-label="{e(u("search", lang))}">'
                  f'{svg("search")}<span>{e(u("search", lang))}</span><kbd>/</kbd></button>')
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(full_title)}</title>
<meta name="description" content="{e(desc or u('site_desc', lang))}">
<meta property="og:title" content="{e(full_title)}">
<meta property="og:description" content="{e(desc or u('site_desc', lang))}">
<meta property="og:image" content="{up}../assets/img/concept/hero.jpg">
<meta name="theme-color" content="#0b0d0c">
<link rel="alternate" hreflang="{other}" href="{up}../{other}/{alt}.html">
<link rel="icon" href="{up}../assets/img/deepkin_mark.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&family=Newsreader:opsz,wght@6..72,300;6..72,400&family=Saira+Condensed:wght@500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{up}../assets/css/site.css">
<script>document.documentElement.classList.add("js")</script>
{INTRO_HEAD if slug == "index" else ""}{extra_head}
</head>
<body class="{body_class}" data-lang="{lang}" data-root="{up}">
{intro_html(lang) if slug == "index" else ""}<a class="skip" href="#main">{'Skip to content' if lang == 'en' else 'Saltar al contenido'}</a>
<header class="topbar">
  <a class="brand" href="{up}index.html" aria-label="DEEPKIN"><img src="{up}../assets/img/deepkin_mark.png" alt="" width="22" height="22"><span>DEEPKIN</span></a>
  <nav class="mainnav" id="mainnav">{nav}<a class="navlang" href="{up}../{other}/{alt}.html" hreflang="{other}" data-setlang="{other}">{svg('globe')}<span>{u('switch_lang', lang)}</span></a></nav>
  {search_btn}
  <a class="lang" href="{up}../{other}/{alt}.html" hreflang="{other}" data-setlang="{other}">{svg('globe')}<span>{u('switch_lang', lang)}</span></a>
  <button class="navtoggle" aria-controls="mainnav" aria-expanded="false" aria-label="{'Menu' if lang == 'en' else 'Menú'}">{svg('menu', 'ico ico-open')}{svg('close', 'ico ico-close')}</button>
</header>
<div class="depth" aria-hidden="true"><span class="depth-line"><span class="depth-fill"></span></span><span class="depth-val">0000 m</span></div>
<main id="main">
{body}
</main>
<footer class="foot">
  <div class="foot-in">
    <div class="foot-brand"><img src="{up}../assets/img/deepkin_logo.png" alt="DEEPKIN — What lies below" width="220" height="91" loading="lazy"></div>
    <p>{u('footer_note', lang)}</p>
    <nav>{nav}</nav>
    <p class="signal">261.6.66</p>
  </div>
</footer>
<div class="search" id="search" hidden role="dialog" aria-modal="true" aria-label="{e(u('search', lang))}">
  <div class="search-box">
    <div class="search-in">{svg('search')}<input type="search" id="search-q" placeholder="{e(u('search_ph', lang))}" autocomplete="off" spellcheck="false" aria-controls="search-res">
    <button type="button" class="search-x" data-search-close aria-label="{'Close' if lang == 'en' else 'Cerrar'}">Esc</button></div>
    <ul class="search-res" id="search-res" role="listbox"></ul>
    <p class="search-hint">{e(u('search_hint', lang))}</p>
  </div>
</div>
<script src="{up}../assets/js/site.js"></script>
</body>
</html>
"""


def wiki_header(lang, kicker, title, lead, img=None):
    bg = f'<div class="phead-img" style="background-image:url(../assets/img/{img})"></div>' if img else ""
    return f"""<section class="phead">{bg}
  <div class="wrap">
    <p class="kicker">{e(kicker)}</p>
    <h1>{e(title)}</h1>
    <p class="lead">{e(lead)}</p>
  </div>
</section>"""


def toc(lang, entries):
    links = "".join(f'<a href="#{a}">{e(label)}</a>' for a, label in entries)
    return f'<aside class="toc"><p>{u("on_this_page", lang)}</p><nav>{links}</nav></aside>'


def wiki(lang, entries, content, ghost_toc=False):
    # ghost_toc (2026-10-12): segunda grilla de la misma pagina; repite el indice solo como guia visual (sin foco ni lector).
    t = toc(lang, entries)
    if ghost_toc:
        t = t.replace('<aside class="toc">', '<aside class="toc toc-ghost" aria-hidden="true">', 1).replace("<a href=", '<a tabindex="-1" href=')
    return f'<div class="wrap wiki">{t}<div class="wiki-body">{content}</div></div>'


def section_title(anchor, kicker, title, lead=""):
    lead_html = f'<p class="sec-lead">{e(lead)}</p>' if lead else ""
    return f'<header class="sec-head" id="{anchor}"><p class="kicker">{e(kicker)}</p><h2>{e(title)}</h2>{lead_html}</header>'


# --- Paginas -----------------------------------------------------------------
def page_index(lang):
    S = STORY[lang]
    pillars = "".join(
        f'<article class="pillar reveal">{svg(k, "pico")}<h3>{e(n[lang])}</h3><p>{e(d[lang])}</p></article>'
        for k, n, d in TX.PILLARS)
    loop = "".join(
        f'<li class="reveal"><span class="loop-n">0{i + 1}</span><h3>{e(n[lang])}</h3><p>{e(d[lang])}</p></li>'
        for i, (n, d) in enumerate(TX.LOOP))
    cards = ""
    for c in CLASSES_DATA:
        k = CLASS_KEY[c["id"]]
        txt = CLASSES[c["id"]]
        dv = derived(c)
        cards += f"""<a class="ccard reveal" href="classes.html#{k}" style="--c:{class_color(c['id'])}">
  <picture><source media="(max-width: 720px)" srcset="../assets/img/classes/class_{k}_600.webp"><img src="../assets/img/classes/class_{k}.webp" alt="{e(c['name'])}" width="960" height="1200" loading="lazy" decoding="async"></picture>
  <div class="ccard-body">
    <p class="ccard-civ">{e(txt['title'][lang])}</p>
    <h3>{e(c['name'])}</h3>
    <p class="ccard-role">{e(txt['role'][lang])}</p>
    <p class="ccard-motto">{e(txt['motto'][lang])}</p>
    <dl class="ccard-stats"><div><dt>{u('hp', lang)}</dt><dd>{dv['health']}</dd></div><div><dt>{u('speed', lang)}</dt><dd>{num(dv['speed'], lang)}</dd></div><div><dt>{u('energy', lang)}</dt><dd>{dv['energy']}</dd></div></dl>
  </div>
</a>"""
    wlist = sorted([w for w in WEAPONS if not w.get("planned") and "provisional" not in w["id"] and has_icon(w["id"])], key=lambda w: -base_damage(w))[:8]
    weapons = "".join(
        f'<a class="wthumb reveal" href="items.html#{e(w["id"])}">{icon(w["id"], alt=w["display_name"])}<span>{e(w["display_name"])}</span><b>{base_damage(w)}</b></a>'
        for w in wlist)
    route = ""
    for r in TX.REGIONS:
        route += f'<li><a href="world.html#{r["id"]}"><span class="route-n">{r["depth"]}</span><span class="route-name">{e(r["name"])}</span><span class="route-kind">{e(r["kind"][lang])}</span></a></li>'
    # Galeria (2026-10-10): capturas actuales del mundo en webp; las de interfaz siguen siendo las jpg de la UI.
    gallery_imgs = ["shots/world_scarp", "shots/world_shallows", "shots/class_select_terminal.jpg",
                    "shots/world_dustline_gate", "shots/skill_tree.jpg", "shots/world_outpost"]
    gallery = "".join(f'<figure class="reveal"><img src="../assets/img/{g}" alt="" loading="lazy"></figure>' if g.endswith(".jpg")
                      else f'<figure class="reveal">{shot(g)}</figure>' for g in gallery_imgs)
    crawler = next(n for n in NPCS if n["id"] == "npc.burrowborn_crawler")
    ravager = next(n for n in NPCS if n["id"] == "npc.burrowborn_ravager")
    mobs = ""
    for m in (crawler, ravager):
        mobs += f'<a class="mthumb reveal" href="bestiary.html#{m["id"]}">{icon(m["id"], alt=m["display_name"])}<div><h3>{e(m["display_name"])}</h3><p>{e(MOBS[m["id"]]["lore"][lang])}</p></div></a>'
    intro_lines = [b[1] for ch in S["chapters"][:1] for b in ch[1] if b[0] in ("big", "beat")][:3]
    intro = "".join(f'<p class="reveal">{e(x)}</p>' for x in intro_lines)
    body = f"""
<section class="hero" data-lantern>
  <div class="hero-img" style="background-image:url(../assets/img/concept/hero.jpg)"></div>
  <div class="hero-dark"></div>
  <div class="hero-in">
    <p class="kicker hero-kicker">{e(u('early', lang))}</p>
    <h1 class="hero-logo"><img src="../assets/img/deepkin_logo.png" alt="DEEPKIN — What lies below" width="1356" height="559"></h1>
    <p class="hero-tag">{e(u('tagline', lang))}</p>
    <p class="hero-sub">{'A cooperative underground action RPG. Explore, drill, equip — and decide when to come back.' if lang == 'en' else 'Un RPG de acción cooperativo bajo tierra. Explorá, perforá, equipate… y decidí cuándo volver.'}</p>
    <div class="cta">
      <a class="btn btn-solid" href="story.html">{u('read_story', lang)} {svg('arrow')}</a>
      <a class="btn" href="classes.html">{u('meet_classes', lang)}</a>
    </div>
  </div>
  <p class="hero-hint">{'move your light' if lang == 'en' else 'mové tu luz'}</p>
</section>

<section class="intro wrap">
  <div class="intro-text">{intro}<a class="textlink reveal" href="story.html">{u('read_story', lang)} {svg('arrow')}</a></div>
</section>

<section class="wrap block">
  {section_title('pillars', '01', 'The expedition' if lang == 'en' else 'La expedición', 'Four ideas hold the whole game together.' if lang == 'en' else 'Cuatro ideas sostienen todo el juego.')}
  <div class="pillars">{pillars}</div>
  <ol class="loop">{loop}</ol>
</section>

<section class="block block-dark">
  <div class="wrap">
    {section_title('classes', '02', u('meet_classes', lang), 'Four civilisations survived the Collapse. Each one sends its own kind of operator below.' if lang == 'en' else 'Cuatro civilizaciones sobrevivieron al Colapso. Cada una manda abajo a su propio tipo de operador.')}
    <div class="ccards">{cards}</div>
  </div>
</section>

<section class="wrap block split">
  <div>
    {section_title('arsenal', '03', 'Arsenal', 'Hammers, scatterguns, spore projectors and relay blades. Any class can carry any of them.' if lang == 'en' else 'Martillos, escopetas, proyectores de esporas y cuchillas de La Red. Cualquier clase puede llevar cualquiera.')}
    <a class="btn" href="items.html#weapons">{u('open_archive', lang)} {svg('arrow')}</a>
  </div>
  <div class="wthumbs">{weapons}</div>
</section>

<section class="block block-dark">
  <div class="wrap split split-rev">
    <div>
      {section_title('world', '04', 'Every layer hides a history' if lang == 'en' else 'Cada estrato esconde una historia', 'From the Outpost down the shaft, through the Shallows to the Deep Survey — and up to an open, dangerous sky.' if lang == 'en' else 'Del Outpost por el pozo, a través de The Shallows hasta The Deep Survey… y arriba, a un cielo abierto y peligroso.')}
      <ol class="route">{route}</ol>
      <a class="btn" href="world.html">{u('explore', lang)} {svg('arrow')}</a>
    </div>
    <figure class="world-fig reveal"><img src="../assets/img/concept/city.jpg" alt="" loading="lazy"></figure>
  </div>
</section>

<section class="wrap block">
  {section_title('bestiary', '05', 'The Burrowborn', 'They feel your footsteps through the stone long before they see you.' if lang == 'en' else 'Sienten tus pasos a través de la piedra mucho antes de verte.')}
  <div class="mthumbs">{mobs}</div>
</section>

<section class="wrap block">
  {section_title('gallery', '06', 'From the field' if lang == 'en' else 'Desde el campo', 'Captures from the current build.' if lang == 'en' else 'Capturas de la versión actual.')}
  <div class="gallery">{gallery}</div>
</section>

<section class="closing">
  <div class="wrap">
    <p class="closing-q">{e(S['ending'])}</p>
    <a class="btn btn-solid" href="manual.html">{('Field Manual' if lang == 'en' else 'Manual de campo')} {svg('arrow')}</a>
  </div>
</section>
"""
    return page(lang, "index", "DEEPKIN", body, body_class="home")


def page_story(lang):
    S = STORY[lang]
    out = []
    chapters_nav = []
    for i, (title, blocks) in enumerate(S["chapters"]):
        anchor = f"ch{i + 1}"
        chapters_nav.append((anchor, title))
        parts = []
        for kind, val in blocks:
            if kind == "p":
                parts.append(f'<p class="reveal">{e(val)}</p>')
            elif kind == "beat":
                parts.append(f'<p class="beat reveal">{e(val)}</p>')
            elif kind == "big":
                parts.append(f'<p class="big reveal">{e(val)}</p>')
            elif kind == "q":
                parts.append('<div class="maybe reveal">' + "".join(f"<p>{e(x)}</p>" for x in val) + "</div>")
            elif kind == "signal":
                parts.append(f'<p class="signal-line reveal">{e(val)} <span class="scramble" data-text="261.6.66">261.6.66</span></p>')
            elif kind == "cities":
                cards = ""
                for cid, (city, line) in S["cities"].items():
                    c = CLASS_BY_ID[cid]
                    cards += (f'<a class="city reveal" href="classes.html#{CLASS_KEY[cid]}" style="--c:{class_color(cid)}">'
                              f'<span class="city-name">{e(city)}</span><span class="city-civ">{e(c["name"])} · {e(CLASSES[cid]["title"][lang])}</span>'
                              f'<span class="city-line">{e(line)}</span></a>')
                parts.append(f'<div class="cities">{cards}</div>')
        out.append(f'<section class="chapter" id="{anchor}"><p class="chapter-n">{u("chapter", lang)} {["I", "II", "III", "IV"][i]}</p>'
                   f'<h2 class="reveal">{e(title)}</h2>{"".join(parts)}</section>')
    chap_links = "".join(f'<a href="#{a}"><span>{["I", "II", "III", "IV"][i]}</span>{e(tt)}</a>' for i, (a, tt) in enumerate(chapters_nav))
    body = f"""
<section class="story-hero">
  <div class="story-hero-img" style="background-image:url(../assets/img/concept/tile_deep.jpg)"></div>
  <div class="wrap narrow">
    <p class="kicker">DEEPKIN · 2318</p>
    <h1>{e(S['title'])}</h1>
    <nav class="chapnav">{chap_links}</nav>
  </div>
</section>
<article class="story wrap narrow">
{''.join(out)}
<div class="story-end">
  <p class="big reveal">{e(S['ending'])}</p>
  <p class="decrypt reveal"><span class="scramble" data-text="261.6.66">261.6.66</span></p>
  <a class="btn reveal" href="classes.html">{u('meet_classes', lang)} {svg('arrow')}</a>
</div>
</article>
"""
    return page(lang, "story", S["title"], body, body_class="story-page")


def class_section(c, lang):
    k = CLASS_KEY[c["id"]]
    txt = CLASSES[c["id"]]
    dv = derived(c)
    col = class_color(c["id"])
    city = STORY[lang]["cities"][c["id"]][0]
    attrs = ""
    for a in ("might", "endurance", "precision", "technology"):
        v = c["attributes"][a]
        attrs += f'<div class="attr"><span class="attr-n">{e(ATTRS[a][lang])}</span>{bar(v, 20, col)}<b>{v}</b><small>{e(ATTR_DESC[a][lang])}</small></div>'
    stats = [
        (u("health", lang), dv["health"], ""), (u("stamina", lang), dv["stamina"], ""),
        (u("armor", lang), num(dv["armor"], lang), f'−{dv["armor_pct"]}%'),
        (u("resistance", lang), num(dv["res"], lang), f'−{dv["res_pct"]}%'),
        (u("move_speed", lang), num(dv["speed"], lang), "m/s"), (u("energy", lang), dv["energy"], ""),
        (u("carry", lang), f'{num(dv["carry"], lang)} kg', f'+{num(dv["carry_lvl"], lang)}/{u("level", lang).lower()}'),
        ("Accuracy" if lang == "en" else "Puntería", f'{dv["accuracy"]}%', ""),
    ]
    stat_html = "".join(f'<div class="st"><dt>{e(n)}</dt><dd>{v}<small>{e(s)}</small></dd></div>' for n, v, s in stats)
    power_id = c["ability_id"]
    variants = ""
    for v in c["variants"]:
        w = ITEMS[v["weapon_id"]]
        variants += f"""<div class="variant">
  <a href="items.html#{e(w['id'])}" class="variant-w">{icon(w['id'], alt=w['display_name'])}</a>
  <div><p class="kicker">{u('starting_weapon', lang)} · {e(FAMILIES[w['weapon_family']][lang])}</p><h4>{e(w['display_name'])}</h4><p>{e(FAMILY_DESC[w['weapon_family']][lang])}</p>
  <p class="variant-meta"><a href="items.html#{e(w['id'])}">{e(w['display_name'])}</a> · {class_damage(c, w)} {u('damage', lang).lower()}</p></div>
</div>"""
    aff = ""
    for fam in sorted(FAMILIES, key=lambda f: -c["skill_affinity"].get(f, 0.5)):
        val = c["skill_affinity"].get(fam, 0.5)
        hot = " hot" if val >= 1.4 else (" cold" if val < 0.9 else "")
        aff += f'<li class="aff{hot}"><span>{e(FAMILIES[fam][lang])}</span>{bar(val, 1.5, col if val >= 1 else "var(--dim)")}<b>×{num(val, lang)}</b></li>'
    starters = "".join(
        f'<a class="mini" href="items.html#{e(wid)}">{icon(wid, alt=ITEMS[wid]["display_name"])}<span>{e(ITEMS[wid]["display_name"])}</span></a>'
        for wid in c["starter_weapons"] if wid in ITEMS)
    power_mult = POWER_MULT.get(power_id)
    return f"""<section class="cls" id="{k}" style="--c:{col}">
  <div class="cls-top">
    <figure class="cls-art"><picture><source media="(max-width: 720px)" srcset="../assets/img/classes/class_{k}_600.webp"><img src="../assets/img/classes/class_{k}.webp" alt="{e(c['name'])} · {e(ITEMS[c['variants'][0]['weapon_id']]['display_name'])}" width="960" height="1200" loading="lazy" decoding="async"></picture></figure>
    <div class="cls-intro">
      <p class="kicker">{e(txt['title'][lang])} · {u('home', lang)}: {e(city)}</p>
      <h2>{e(c['name'])}</h2>
      <p class="cls-fantasy">{e(txt['fantasy'][lang])}</p>
      <p>{e(txt['pitch'][lang])}</p>
      <p class="cls-role"><span>{u('role', lang)}</span>{e(txt['role'][lang])}</p>
    </div>
    <div class="cls-radar">{radar(c, lang)}</div>
  </div>
  <div class="cls-grid">
    <div class="panel"><h3>{u('attributes', lang)}</h3>{attrs}</div>
    <div class="panel"><h3>{'Field profile' if lang == 'en' else 'Perfil de campo'}</h3><dl class="stats">{stat_html}</dl></div>
  </div>
  <div class="cls-grid three">
    <div class="panel skill"><p class="key">C</p><p class="kicker">{u('power', lang)}</p><h4>{e(c['ability_name'])}</h4><p>{e(txt['power_desc'][lang])}</p>
      <p class="skill-meta">{u('cooldown', lang)} {POWER_COOLDOWNS[power_id]} s · {num(dv['power_cost'], lang)} {u('energy', lang).lower()}{f' · ×{num(power_mult, lang)}' if power_mult else ''}</p></div>
    <div class="panel skill"><p class="key">Q</p><p class="kicker">{u('mobility', lang)}</p><h4>{e(DASH['name'][lang])}</h4><p>{e(DASH['desc'][lang])}</p>
      <p class="skill-meta">{u('cooldown', lang)} {DASH_COOLDOWN} s · {DASH_COST} {u('energy', lang).lower()}</p></div>
    <div class="panel skill"><p class="key key-p">P</p><p class="kicker">{u('passive', lang)}</p><h4>{e(c['passive_name'])}</h4><p>{e(txt['passive_desc'][lang])}</p></div>
  </div>
  <figure class="cls-power"><picture><source media="(max-width: 720px)" srcset="../assets/img/classes/class_{k}_power_600.webp"><img src="../assets/img/classes/class_{k}_power.webp" alt="{e(c['ability_name'])}" width="1200" height="675" loading="lazy" decoding="async"></picture>
    <figcaption><b>{e(c['ability_name'])}</b> · {e(txt['power_desc'][lang])}</figcaption></figure>
  <div class="cls-kit"><figure class="cls-concept"><img src="../assets/img/concept/class_{k}.jpg" alt="" loading="lazy"><figcaption>{'Concept art' if lang == 'en' else 'Arte conceptual'}</figcaption></figure>
    <div><p class="kicker">{'Headgear & emblem' if lang == 'en' else 'Equipo de cabeza y emblema'}</p><p>{e(HEADGEAR[k][lang])}</p></div></div>
  <h3 class="sub">{u('starting_weapons', lang)}</h3>
  <div class="variants">{variants}</div>
  <div class="cls-grid">
    <div class="panel"><h3>{u('skill_affinity', lang)}</h3><ul class="affs">{aff}</ul></div>
    <div class="panel"><h3>{'Starter weapons' if lang == 'en' else 'Armas iniciales'}</h3><div class="minis">{starters}</div></div>
  </div>
</section>"""


def page_classes(lang):
    entries = [("compare", "Compare" if lang == "en" else "Comparar"), ("choose", "Two steps" if lang == "en" else "Dos pasos")] + [(CLASS_KEY[c["id"]], c["name"]) for c in CLASSES_DATA]
    dvs = {c["id"]: derived(c) for c in CLASSES_DATA}
    rows = [
        (u("health", lang), "health", ""), (u("armor", lang), "armor", ""), (u("resistance", lang), "res", ""),
        (u("move_speed", lang), "speed", " m/s"), (u("energy", lang), "energy", ""), (u("carry", lang), "carry", " kg"),
    ]
    thead = "".join(f'<th style="--c:{class_color(c["id"])}"><a href="#{CLASS_KEY[c["id"]]}">{e(c["name"])}</a></th>' for c in CLASSES_DATA)
    tbody = ""
    for label, key, suf in rows:
        mx = max(dvs[c["id"]][key] for c in CLASSES_DATA)
        cells = "".join(
            f'<td>{bar(dvs[c["id"]][key], mx, class_color(c["id"]))}<b>{num(dvs[c["id"]][key], lang)}{suf}</b></td>' for c in CLASSES_DATA)
        tbody += f"<tr><th>{e(label)}</th>{cells}</tr>"
    tbody += "<tr><th>" + u("power", lang) + "</th>" + "".join(f"<td><b>{e(c['ability_name'])}</b></td>" for c in CLASSES_DATA) + "</tr>"
    compare = f"""{section_title('compare', 'Four disciplines' if lang == 'en' else 'Cuatro disciplinas', 'Compare' if lang == 'en' else 'Comparar', u('variants_note', lang))}
<div class="tablewrap"><table class="cmp"><thead><tr><th></th>{thead}</tr></thead><tbody>{tbody}</tbody></table></div>"""
    # Eleccion en dos pasos y armas iniciales (2026-10-11, docs/CLASSES.md "Class screen").
    en = lang == "en"
    starters = []
    for c in CLASSES_DATA:
        for wid in c.get("starter_weapons", [v["weapon_id"] for v in c["variants"]]):
            if wid in ITEMS and wid not in starters:
                starters.append(wid)
    best = {c["id"]: max(c["skill_affinity"].get(ITEMS[w].get("weapon_family"), 0.5) for w in starters) for c in CLASSES_DATA}
    srows = ""
    for w in starters:
        fam = ITEMS[w].get("weapon_family")
        cells = ""
        for c in CLASSES_DATA:
            v = c["skill_affinity"].get(fam, 0.5)
            rec = v >= best[c["id"]]
            cells += f'<td class="{"rec" if rec else ("off" if v < 0.9 else "")}">{"★ " if rec else ""}×{num(v, lang)}</td>'
        srows += (f'<tr><th><a class="mini-w" href="items.html#{e(w)}">{icon(w, alt=ITEMS[w]["display_name"])}<span>{e(ITEMS[w]["display_name"])}</span></a>'
                  f'<small>{e(FAMILIES[fam][lang])}</small></th>{cells}</tr>')
    steps = [("01", "Choose your discipline" if en else "Elegí tu disciplina",
              "Four cards with a playstyle fingerprint — durability, melee, ranged, mobility, tech — the class power, the passive and the skills it trains fast. Hold Tab to compare all four; D opens the full dossier."
              if en else "Cuatro tarjetas con la huella de cada estilo (resistencia, cuerpo a cuerpo, distancia, movilidad, tecnología), el poder, la pasiva y las habilidades que entrena rápido. Mantené Tab para comparar las cuatro; D abre la ficha completa."),
             ("02", "Choose your starting weapon" if en else "Elegí tu arma inicial",
              "Every class's starter is on offer. ★ RECOMMENDED ones train at your discipline's best rate and the first is pre-selected; the others say OFF-DISCIPLINE and train at ×0.5. It waits for you in the Outpost gear crate."
              if en else "Se ofrecen las iniciales de todas las clases. Las ★ RECOMENDADAS entrenan al mejor ritmo de tu disciplina y la primera viene elegida; las otras dicen OFF-DISCIPLINE y entrenan a ×0.5. Te espera en el cajón de equipo del Outpost.")]
    steps_html = "".join(f'<li><span class="loop-n">{n_}</span><h3>{e(a)}</h3><p>{e(b)}</p></li>' for n_, a, b in steps)
    choose = (section_title("choose", "Class screen" if en else "Pantalla de clase", "Two steps" if en else "Dos pasos",
                            "Role first, then tool. Weapons are never locked: the class only sets how fast you train each one." if en
                            else "Primero el rol, después la herramienta. Las armas nunca se bloquean: la clase sólo define qué tan rápido entrenás cada una.")
              + f'<ol class="loop loop-2">{steps_html}</ol>'
              + f'<div class="tablewrap"><table class="cmp starters"><thead><tr><th>{"Starting weapon · skill" if en else "Arma inicial · habilidad"}</th>{thead}</tr></thead><tbody>{srows}</tbody></table></div>'
              + f'<p class="note">{"★ recommended for that discipline · the number is how fast it trains the weapon's skill." if en else "★ recomendada para esa disciplina · el número es qué tan rápido entrena la habilidad del arma."}</p>')
    compare += choose
    sections = "".join(class_section(c, lang) for c in CLASSES_DATA)
    body = wiki_header(lang, "Classes" if lang == "en" else "Clases", "Choose your discipline" if lang == "en" else "Elegí tu disciplina",
                       "Your class sets your body, your power and how fast you learn each weapon. Your gear does the rest." if lang == "en"
                       else "Tu clase define tu cuerpo, tu poder y qué tan rápido aprendés cada arma. Tu equipo hace el resto.",
                       "shots/class_select_terminal.jpg")
    body += wiki(lang, entries, compare + sections)
    return page(lang, "classes", u("meet_classes", lang), body)


# --- Objetos (2026-10-24): Arsenal y Equipo unificados en una sola pagina con tablas por categoria -----------------
# Las categorias salen de los ids de los objetos (wiki.item_cat); una categoria nueva sin seccion propia cae en "Otros".
# Numeros de armas: src/combat_math.py (formulas del servidor, docs/design/WEAPON_BALANCE.md del juego, seccion 8).
ITEM_SECTIONS = [
    ("weapons", ("weapon",)), ("shields", ("shield",)), ("armor", ("armor",)), ("ammunition", ("ammunition",)),
    ("lights", ("light",)), ("drones", ("drone",)), ("power", ("battery", "backpack")), ("tools", ("tool", "fuel")),
    ("consumables", ("consumable", "food")), ("crates", ("container",)),
    ("resources", ("ore", "mineral", "salvage", "component", "currency")), ("records", ("log", "contract", "service")),
]
ITEM_SEC_TEXT = {
    "weapons": (L("Weapons", "Armas"),
                L("Any class can carry any weapon; the class sets how hard it hits and how fast it trains. Hit and DPS are for the weapon's home class (the one that trains its skill fastest) at skill 1 and level 1, sustained, with its own ammunition. Open a weapon for every class, or try the calculator below.",
                  "Cualquier clase puede llevar cualquier arma; la clase define cuánto pega y qué tan rápido la entrena. Golpe y DPS son de la clase natural del arma (la que entrena su habilidad más rápido) con habilidad 1 y nivel 1, en régimen, con su propia munición. Abrí un arma para ver todas las clases, o probá la calculadora de abajo.")),
    "shields": (L("Shields", "Escudos"),
                L("Off-hand gear pairs with any one-handed weapon. Taking hits with a shield up trains Shielding: 8% less damage, up to 40%.",
                  "El equipo de mano secundaria combina con cualquier arma de una mano. Recibir golpes con el escudo en alto entrena Escudos: 8% menos daño, hasta 40%.")),
    "armor": (L("Armor", "Armadura"),
              L("Head, chest, legs and boots are equipped separately. Armor reduces physical damage, resistance reduces everything else: reduction = rating ÷ (rating + 100), at most 75%.",
                "Cabeza, torso, piernas y botas se equipan por separado. La armadura reduce el daño físico; la resistencia, todo lo demás: reducción = valor ÷ (valor + 100), como máximo 75%.")),
    "ammunition": (L("Ammunition", "Munición"),
                   L("A ranged weapon fires any ammunition of its family, the first stack in your cargo. Rounds feed the rifles and shotguns, spore cartridges poison, synapse darts wound enemies and heal operators. Tech weapons spend energy from the worn cell instead, and chainsaws burn gas from a can.",
                     "Un arma a distancia dispara cualquier munición de su familia, la primera pila de tu inventario. Las balas alimentan rifles y escopetas, los cartuchos de esporas envenenan y los dardos sinápticos hieren enemigos y curan operadores. Las armas de Tecnología gastan energía de la celda equipada, y las motosierras queman combustible de un bidón.")),
    "lights": (L("Lights", "Luces"),
               L("Your light is the difference between reading a cavern and guessing it. Brighter lights drain your battery faster; T toggles the lantern.",
                 "Tu luz es la diferencia entre leer una caverna y adivinarla. Las luces más potentes vacían la batería más rápido; T prende y apaga la linterna.")),
    "drones": (L("Drones", "Drones"),
               L("Launched from the cargo: a lamp, a gun, a scout you pilot or a bomb you fly in. They draw from your battery while they fly.",
                 "Se lanzan desde el inventario: una lámpara, un arma, un explorador que pilotás o una bomba que volás. Sacan energía de tu batería mientras vuelan.")),
    "power": (L("Batteries & backpacks", "Baterías y mochilas"),
              L("The battery feeds your light, drones, energy weapons and powers. Spare cells refill it between fights; Vesko recharges an empty one. A backpack adds cells and carry, and stays with what it holds when you drop it.",
                "La batería alimenta tu luz, tus drones, las armas de energía y tus poderes. Las celdas de repuesto la recargan entre peleas; Vesko recarga una vacía. Una mochila suma celdas y carga, y se queda con lo que tiene si la soltás.")),
    "tools": (L("Tools & fuel", "Herramientas y combustible"),
              L("The drill goes in the tool slot: hold F at a drill site. Gas cans fill at the pumps and feed bikes, the crane and the Foundry chainsaws.",
                "El taladro va en la ranura de herramienta: mantené F en un punto de perforación. Los bidones se llenan en los surtidores y alimentan motos, la grúa y las motosierras de La Forja.")),
    "consumables": (L("Consumables & food", "Consumibles y comida"),
                    L("Capsules heal at once, food heals over time. Both stack in the cargo.",
                      "Las cápsulas curan al instante; la comida cura con el tiempo. Las dos se apilan en el inventario.")),
    "crates": (L("Crates & cases", "Cajones y estuches"),
               L("Your first kit comes from personal crates in the Outpost; Document Cases hold Reading Logs, and boss strongboxes open once per operator.",
                 "Tu primer equipo sale de cajones personales en el Outpost; los Document Cases guardan registros y los cofres de jefes se abren una vez por operador.")),
    "resources": (L("Resources & salvage", "Recursos y chatarra"),
                  L("Ore, crystal, salvage and coin: what you dig, find and carry home. Everything you haul weighs something.",
                    "Mineral, cristal, chatarra y moneda: lo que excavás, encontrás y llevás a casa. Todo lo que acarreás pesa algo.")),
    "records": (L("Logs, contracts & services", "Registros, contratos y servicios"),
                L("Tablets to read, contract drives to cash in and the VDI excavation service.",
                  "Tablets para leer, drives de contratos para cobrar y el servicio de excavación de VDI.")),
    "other": (L("Other items", "Otros objetos"), L("", "")),
}


def _wk():
    import wiki as WK  # noqa: E402  (tarde: el wiki carga sus propios datos al importarse)
    import wiki_mech as MX  # noqa: E402
    return WK, MX


def has_icon(iid):
    return os.path.exists(os.path.join(ROOT, "assets/img/icons", iid + ".png"))


def td(html_, v=None, numeric=False):
    dv = f' data-v="{e(v)}"' if v is not None else ""
    return f'<td{" class=" + chr(34) + "n" + chr(34) if numeric else ""}{dv}>{html_}</td>'


def name_td(i, lang):
    art = icon(i["id"], "ticon", "") if has_icon(i["id"]) else '<span class="ticon icon-ph" aria-hidden="true"></span>'
    return (f'<td class="tn" data-v="{e(i["display_name"].lower())}"><span class="tn-in">{art}<span class="tn-t">'
            f'<a href="{SL.item(i["id"])}">{e(i["display_name"])}</a>{status_tag(i, lang)}</span></span></td>')


def pct_txt(ch, lang):
    return num(round(ch * 100, 1), lang) + "%"


def where_to_get(i, lang, limit=3):
    """Tiendas (con precio), cajones, lugares, perforacion y criaturas que lo sueltan; enlazados al wiki."""
    if i.get("planned"):
        return "—"
    WK, MX = _wk()
    iid = i["id"]
    out = []
    for b, npc in sorted(((b, npc) for npc, b, _s, _st in MX.shop_rows_for(iid) if b is not None), key=lambda x: x[0]):
        out.append(f'{WK.lk(npc, here="")} <small>{num(b, lang)} Metal</small>')
    for kind, a, _q, extra in WK.FOUND.get(iid, []):
        lab = WK.lk(a, here="")
        if kind == "crate" and isinstance(extra, tuple):
            lab += f' <small>{"start" if lang == "en" else "inicio"}</small>'
        out.append(lab)
    for m, ch, _a, _b in sorted(WK.DROPPED.get(iid, []), key=lambda x: -x[1]):
        out.append(f'{WK.lk(m, here="")} <small>{pct_txt(ch, lang)}</small>')
    seen, uniq = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    if not uniq:
        return "—"
    s = ", ".join(uniq[:limit])
    if len(uniq) > limit:
        s += f' <a class="more" href="{SL.item(iid)}" title="{"More sources" if lang == "en" else "Más fuentes"}">+{len(uniq) - limit}</a>'
    return s


def tier_td(i, lang):
    tier = int(i.get("gear_tier", 1) or 1)
    if i.get("weapon_family") and i.get("equipment_slot") == "primary_weapon":
        lv, sk = CM.tier_requirement(i)
    else:
        req = i.get("requirements") or {}
        lv = max(GEAR_TIER_LEVELS[min(tier, len(GEAR_TIER_LEVELS)) - 1], req.get("minimum_level", 1))
        sk = None
    bits = [f"T{tier}", f'{"Lv" if lang == "en" else "Nv"} {lv}']
    req = i.get("requirements") or {}
    for f, v in (req.get("minimum_skills") or {}).items():
        if f != i.get("weapon_family"):
            bits.append(f"{FAMILIES.get(f, {}).get(lang, f)} {v}")
    if sk and sk > 1:
        bits.append(f'{FAMILIES[i["weapon_family"]][lang]} {sk}')
    return td(" · ".join(bits), tier * 1000 + lv)


def weight_td(i, lang):
    w = i.get("weight", 0)
    return td(num(w, lang) if w else "—", w, True)


def item_row(i, cells, q=""):
    hay = " ".join([i["display_name"], i["id"], q]).lower()
    return f'<tr id="{e(i["id"])}" data-q="{e(hay)}">{"".join(cells)}</tr>'


def group_row(label, cols):
    return f'<tr class="grp"><th colspan="{cols}" scope="rowgroup">{label}</th></tr>'


def itable(tid, head, body):
    th = "".join(f'<th scope="col" data-sort="{k}">{e(h)}</th>' for h, k in head)
    return (f'<div class="tablewrap itable"><table class="data sortable" id="{tid}"><thead><tr>{th}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


def upkeep_html(w, lang):
    WK, _MX = _wk()
    p = w.get("properties", {})
    if CM.uses_fuel(w):
        return WK.lk("item.fuel.gas_can", here="") + " <small>" + e(TRAITS["per_cut"][lang].format(v=num(p["fuel_per_attack"], lang))) + "</small>", p["fuel_per_attack"]
    if p.get("energy_per_shot"):
        return e(TRAITS["energy_shot"][lang].format(v=num(p["energy_per_shot"], lang))), p["energy_per_shot"]
    if w.get("ammo_item_id"):
        return WK.lk(w["ammo_item_id"], here=""), 1
    return "—", 0


def sec_weapons(lang):
    en = lang == "en"
    fams = list(FAMILIES)
    ws = sorted(WEAPONS, key=lambda w: (fams.index(w["weapon_family"]) if w.get("weapon_family") in fams else 99, bool(w.get("planned")),
                                        -CM.row(CM.home_class(w["weapon_family"], CLASSES_DATA), w, ITEMS)["dps"]))
    head = [(u("weapon", lang), "text"), ("Skill" if en else "Habilidad", "text"), (u("hands", lang), "num"), (u("damage", lang), "num"),
            (u("interval", lang) + " (s)", "num"), ("Reach (m)" if en else "Alcance (m)", "num"),
            ("Hit · opening / sustained" if en else "Golpe · apertura / régimen", "num"), ("DPS · home class" if en else "DPS · clase natural", "num"),
            ("Feeds on" if en else "Consume", "text"), ("Trait & specials" if en else "Rasgo y especiales", "text"),
            ("Tier · requires" if en else "Rango · requiere", "num"), (u("weight", lang) + " (kg)", "num"), ("Where to get" if en else "Dónde conseguirla", "text")]
    body, last = "", None
    for w in ws:
        fam = w["weapon_family"]
        home = CM.home_class(fam, CLASSES_DATA)
        if fam != last:
            body += group_row(f'<a href="wiki/skills.html#{SL.skill_anchor(fam)}">{e(FAMILIES[fam][lang])}</a>'
                              f'<span class="grp-sub">{"home" if en else "clase natural"}: {class_chip(home["id"], lang)}</span>', len(head))
            last = fam
        r = CM.row(home, w, ITEMS)
        p = w["properties"]
        up, upv = upkeep_html(w, lang)
        cells = [name_td(w, lang),
                 td(f'<a href="wiki/skills.html#{SL.skill_anchor(fam)}">{e(FAMILIES[fam][lang])}</a>', FAMILIES[fam][lang]),
                 td(f'{w.get("hands", 1)}H', w.get("hands", 1), True),
                 td(num(CM.base(w), lang), CM.base(w), True), td(num(r["interval"], lang), r["interval"], True),
                 td(num(p.get("attack_range", 0), lang), p.get("attack_range", 0), True),
                 td(f'{r["opening"]} / {r["sustained"]}', r["sustained"], True),
                 td(f'<span class="dps" style="--c:{class_color(home["id"])}">{num(r["dps"], lang, 1)}</span>', round(r["dps"], 2), True),
                 td(up, upv), td(e(CM.trait_text(w, ITEMS, lang, TRAITS)) or "—"), tier_td(w, lang), weight_td(w, lang), td(where_to_get(w, lang))]
        body += item_row(w, cells, f'{FAMILIES[fam]["en"]} {FAMILIES[fam]["es"]} {home["name"]} {u(w.get("weapon_type", "melee"), lang)}')
    traits = "".join(f'<li><b>{e(FAMILIES[f][lang])}</b><span>{e(FAMILY_DESC[f][lang])}</span></li>'
                     for f in fams if any(w.get("weapon_family") == f for w in WEAPONS))
    tb = num(round(CM.TRAILBLAZER * 100), lang)
    notes = (f'<details class="panel traitbox"><summary>{"How the numbers work" if en else "Cómo se calculan los números"}</summary>'
             f'<p class="eq">{"hit = base × class coefficient × attribute bonus × skill & level bonus × ammo × (1 + trait %)" if en else "golpe = base × coeficiente de clase × bono de atributo × bono de habilidad y nivel × munición × (1 + rasgo %)"}</p>'
             f'<p>{"Opening is the first hit; sustained is the steady state (Heat and Suppression at their cap, Range at 6 m+, Overcharge with the cell above half). Ambush counts on half the hits; the Drift adds Trailblazer +" + tb + "% on the same target; spore poison is added per second. Crush only applies to elites and bosses, so it is left out of DPS." if en else "Apertura es el primer golpe; régimen es el estado estable (Calor y Supresión al máximo, Alcance a 6 m o más, Sobrecarga con la celda sobre la mitad). La Emboscada cuenta en la mitad de los golpes; La Deriva suma Trailblazer +" + tb + "% al mismo blanco; el veneno de esporas se suma por segundo. Aplastar sólo aplica a élites y jefes, así que no entra en el DPS."}</p>'
             f'<p>{"Every weapon trains its skill at the same rate per second of fighting: " if en else "Toda arma entrena su habilidad al mismo ritmo por segundo de pelea: "}{num(CM.XP_PER_ATTACK_SECOND, lang)} XP/s × {"class affinity" if en else "afinidad de clase"}. '
             f'{"Tier 2 and up also ask for your skill: " if en else "Desde el rango 2 también piden tu habilidad: "}'
             f'{", ".join(f"T{t_ + 1} {s}" for t_, s in enumerate(CM.TIER_SKILL) if t_ > 0)}.</p>'
             f'<ul class="fams">{traits}</ul></details>')
    return notes + itable("t-weapons", head, body)


def simple_section(cat_items, lang, anchor, head, cells_fn, group=None):
    body, last = "", None
    for i in cat_items:
        if group:
            g = group(i)
            if g != last:
                body += group_row(e(g), len(head))
                last = g
        cells, q = cells_fn(i)
        body += item_row(i, cells, q)
    return itable("t-" + anchor, head, body)


def sec_generic(anchor, its, lang):
    """Tablas de las demas categorias: columnas propias por seccion."""
    WK, MX = _wk()
    en = lang == "en"
    name_h, wt_h, where_h = (u("name", lang), "text"), (u("weight", lang) + " (kg)", "num"), ("Where to get" if en else "Dónde conseguirlo", "text")
    tier_h = ("Tier · requires" if en else "Rango · requiere", "num")
    cap = ITEMS.get("item.battery.provisional_relay_cell", {}).get("properties", {}).get("battery_capacity", 100)
    slot_order = {"head": 0, "chest": 1, "legs": 2, "boots": 3, "arms": 4}
    if anchor in ("armor", "shields"):
        its = sorted(its, key=lambda i: (slot_order.get(i.get("equipment_slot"), 9), bool(i.get("planned")), -i.get("properties", {}).get("armor_defense", 0), i["display_name"]))

        def cells(i):
            p = i.get("properties", {})
            slot = SLOTS.get(i.get("equipment_slot"), {}).get(lang, "—")
            return [name_td(i, lang), td(e(slot), slot_order.get(i.get("equipment_slot"), 9)), td("+" + num(p.get("armor_defense", 0), lang), p.get("armor_defense", 0), True),
                    td("+" + num(p.get("resistance_bonus", 0), lang), p.get("resistance_bonus", 0), True), tier_td(i, lang), weight_td(i, lang), td(where_to_get(i, lang))], slot
        head = [name_h, (u("slot", lang), "text"), (u("armor", lang), "num"), (u("resistance", lang), "num"), tier_h, wt_h, where_h]
        grp = (lambda i: SLOTS.get(i.get("equipment_slot"), {}).get(lang, "—")) if anchor == "armor" else None
        return simple_section(its, lang, anchor, head, cells, grp)
    if anchor == "ammunition":
        its = sorted(its, key=lambda a: (a.get("ammo_family", "rounds"), a.get("properties", {}).get("ammo_multiplier", 1), a["display_name"]))
        ranged = [w for w in WEAPONS if w.get("weapon_type") == "ranged" and not w.get("planned")]

        def cells(a):
            p = a.get("properties", {})
            fam = a.get("ammo_family", "rounds")
            fired = ", ".join(WK.lk(w["id"], here="") for w in ranged if MX.weapon_family(w) == fam) or "—"
            return [name_td(a, lang), td(e(MX.t("fam_" + fam, lang))),
                    td("×" + num(p.get("ammo_multiplier", 1), lang), p.get("ammo_multiplier", 1), True), td(e(MX.ammo_effect(a, lang))),
                    td(fired), td(num(p.get("stack_size", 1), lang), p.get("stack_size", 1), True), weight_td(a, lang), td(where_to_get(a, lang))], fam
        head = [name_h, ("Family" if en else "Familia", "text"), (u("damage", lang), "num"), ("Effect" if en else "Efecto", "text"),
                ("Fired by" if en else "La disparan", "text"), (u("stack", lang), "num"), wt_h, where_h]
        return simple_section(its, lang, anchor, head, cells)
    if anchor == "lights":
        its = sorted(its, key=lambda i: (bool(i.get("planned")), i.get("properties", {}).get("illumination_radius", 0)))

        def cells(i):
            p = i.get("properties", {})
            dr = p.get("light_energy_per_second", 0)
            mins = cap / dr / 60 if dr else 0
            return [name_td(i, lang), td(num(p.get("illumination_radius", 0), lang), p.get("illumination_radius", 0), True),
                    td(num(dr, lang) + "/s", dr, True), td("≈ " + num(mins, lang, 1) + " min" if dr else "—", round(mins, 2), True),
                    tier_td(i, lang), weight_td(i, lang), td(where_to_get(i, lang))], ""
        head = [name_h, (u("light_radius", lang) + " (m)", "num"), (u("drain", lang), "num"), (u("runtime", lang), "num"), tier_h, wt_h, where_h]
        return simple_section(its, lang, anchor, head, cells)
    if anchor == "drones":
        order = {"light": 0, "assault": 1, "scan": 2, "kamikaze": 3}
        its = sorted(its, key=lambda i: (order.get(i.get("drone", {}).get("function"), 9), i.get("drone", {}).get("energy_per_second", 0)))

        def cells(i):
            d = i.get("drone", {})
            fn = d.get("function", "")
            dur = d.get("duration", 0)
            tech = (i.get("requirements") or {}).get("minimum_skills", {}).get("skill.tech")
            return [name_td(i, lang), td(e(MX.t("fn_" + fn, lang)), order.get(fn, 9)), td(num(tech, lang) if tech else "—", tech or 0, True),
                    td(num(d.get("energy_per_second", 0), lang) + " E/s", d.get("energy_per_second", 0), True),
                    td(f"{int(dur // 60)}:{int(dur % 60):02d}", dur, True), td(e(MX.drone_stats(d, lang))), weight_td(i, lang), td(where_to_get(i, lang))], fn
        head = [name_h, ("Function" if en else "Función", "text"), ("Tech skill" if en else "Tecnología", "num"), (u("drain", lang), "num"),
                ("Flight" if en else "Vuelo", "num"), ("Stats" if en else "Datos", "text"), wt_h, where_h]
        return simple_section(its, lang, anchor, head, cells)
    if anchor == "power":
        def cells(i):
            p = i.get("properties", {})
            if i.get("container"):
                capv, capt = i["container"]["cells"], f'{i["container"]["cells"]} {u("cells", lang)}'
            else:
                capv, capt = p.get("battery_capacity", 0), f'{p.get("battery_capacity", 0)} {u("energy", lang).lower()}'
            cb = p.get("carry_bonus", 0)
            slot = SLOTS.get(i.get("equipment_slot"), {}).get(lang, "—")
            return [name_td(i, lang), td(e(slot)), td(capt, capv, True), td("+" + num(cb, lang) + " kg" if cb else "—", cb, True),
                    weight_td(i, lang), td(where_to_get(i, lang))], slot
        head = [name_h, (u("slot", lang), "text"), (u("capacity", lang), "num"), (u("carry", lang), "num"), wt_h, where_h]
        return simple_section(sorted(its, key=lambda i: (i.get("equipment_slot", ""), i["display_name"])), lang, anchor, head, cells)
    if anchor == "tools":
        def cells(i):
            p = i.get("properties", {})
            if p.get("drill_power"):
                use, v = ("Drill power ×" if en else "Potencia ×") + num(p["drill_power"], lang), p["drill_power"]
            elif p.get("fuel_capacity"):
                use, v = num(p["fuel_capacity"], lang) + (" L of gas" if en else " L de combustible"), p["fuel_capacity"]
            else:
                use, v = "—", 0
            slot = SLOTS.get(i.get("equipment_slot"), {}).get(lang, "Cargo" if en else "Inventario")
            return [name_td(i, lang), td(e(slot)), td(e(use), v, True), weight_td(i, lang), td(where_to_get(i, lang))], ""
        head = [name_h, (u("slot", lang), "text"), ("Use" if en else "Uso", "num"), wt_h, where_h]
        return simple_section(its, lang, anchor, head, cells)
    if anchor == "consumables":
        def cells(i):
            p = i.get("properties", {})
            h = p.get("heal_amount", 0)
            how = (("over " if en else "en ") + num(p["heal_seconds"], lang) + " s") if p.get("heal_seconds") else (
                ("at once · " if en else "al instante · ") + num(p.get("use_cooldown", 0), lang) + (" s cooldown" if en else " s de espera"))
            return [name_td(i, lang), td("+" + num(h, lang) + " " + u("hp", lang), h, True), td(e(how)),
                    td(num(p.get("stack_size", 1), lang), p.get("stack_size", 1), True), weight_td(i, lang), td(where_to_get(i, lang))], ""
        head = [name_h, ("Heals" if en else "Cura", "num"), ("How" if en else "Cómo", "text"), (u("stack", lang), "num"), wt_h, where_h]
        return simple_section(its, lang, anchor, head, cells)
    if anchor == "crates":
        def cells(i):
            cl = i.get("container", {}).get("cells", 0)
            kind = ("Fixed in place" if en else "Fijo en su lugar") if i.get("fixed") else ("Portable" if en else "Se puede llevar")
            return [name_td(i, lang), td(f'{cl} {u("cells", lang)}', cl, True), td(e(kind)), td(where_to_get(i, lang))], ""
        head = [name_h, (u("capacity", lang), "num"), ("Kind" if en else "Tipo", "text"), ("Where" if en else "Dónde", "text")]
        return simple_section(sorted(its, key=lambda i: i["display_name"]), lang, anchor, head, cells)
    # Recursos, registros y cualquier categoria nueva: nombre, tipo, dato clave, peso, fuentes.
    order = list(WK.CATS)

    def cells(i):
        cat = WK.item_cat(i["id"])
        p = i.get("properties", {})
        if p.get("currency_value"):
            key, v = num(p["currency_value"], lang) + " Metal", p["currency_value"]
        elif p.get("drive_value"):
            key, v = num(p["drive_value"], lang) + " Metal", p["drive_value"]
        elif i.get("log"):
            key, v = e(i["log"].get("title", "")), 0
        else:
            key, v = WK.key_stat(i, lang), 0
        return [name_td(i, lang), td(e(WK.CATS.get(cat, {}).get(lang, cat)), order.index(cat) if cat in order else 99), td(key, v),
                weight_td(i, lang), td(where_to_get(i, lang))], WK.CATS.get(cat, {}).get(lang, cat)
    head = [name_h, ("Kind" if en else "Tipo", "text"), ("Value / note" if en else "Valor / nota", "text"), wt_h, where_h]
    its = sorted(its, key=lambda i: (order.index(WK.item_cat(i["id"])) if WK.item_cat(i["id"]) in order else 99, i.get("properties", {}).get("currency_value", 0), i["display_name"]))
    return simple_section(its, lang, anchor, head, cells)


def calculator(lang):
    WK, MX = _wk()
    ws = sorted(WEAPONS, key=lambda w: (list(FAMILIES).index(w["weapon_family"]) if w.get("weapon_family") in FAMILIES else 99, w["display_name"]))
    ammo = sorted([a for a in ITEMS.values() if WK.item_cat(a["id"]) == "ammunition"], key=lambda a: (a.get("ammo_family", "rounds"), a["display_name"]))
    calc_data = {
        "classes": [{"id": c["id"], "name": c["name"], "color": class_color(c["id"]), "attributes": c["attributes"],
                     "coef": c["combat_coefficients"], "power": c["ability_name"], "powerMult": POWER_MULT.get(c["ability_id"], 1)}
                    for c in CLASSES_DATA],
        "weapons": [{"id": w["id"], "name": w["display_name"], "type": w.get("weapon_type"), "base": CM.base(w), "interval": CM.interval(w),
                     "ammoFamily": MX.weapon_family(w) if w.get("ammo_item_id") else None, "ammoId": w.get("ammo_item_id"),
                     "trait": CM.trait_percent(w, "sustained"), "opening": CM.trait_percent(w, "opening"),
                     "ambush": w.get("weapon_family") == "skill.blades",
                     "family": FAMILIES[w["weapon_family"]][lang]} for w in ws],
        "ammo": [{"id": a["id"], "name": a["display_name"], "family": a.get("ammo_family", "rounds"), "mult": a["properties"]["ammo_multiplier"],
                  "poison": a["properties"].get("poison_per_second", 0)} for a in ammo],
        "trailblazer": CM.TRAILBLAZER, "ambushPct": CM.AMBUSH, "ambushUptime": CM.AMBUSH_UPTIME,
        "skillStep": CM.k("DAMAGE_PER_SKILL_LEVEL", 0.01), "levelStep": CM.k("DAMAGE_PER_CHARACTER_LEVEL", 0.006),
        "statStep": GD.RPG.get("STAT_DAMAGE_STEP", 0.015),
        "lang": lang,
        "attrNames": {a: ATTRS[a][lang] for a in ATTRS},
    }
    cls_opts = "".join(f'<option value="{c["id"]}">{e(c["name"])}</option>' for c in CLASSES_DATA)
    w_opts = "".join(f'<option value="{w["id"]}">{e(w["display_name"])}</option>' for w in ws)
    ammo_opts = "".join(f'<option value="{a["id"]}">{e(a["display_name"])}</option>' for a in ammo)
    return f"""{section_title('calculator', 'Tool' if lang == 'en' else 'Herramienta', u('calc_title', lang), u('calc_lead', lang))}
<div class="calc panel" id="calc">
  <div class="calc-in">
    <label>{u('class', lang)}<select id="c-class">{cls_opts}</select></label>
    <label>{u('weapon', lang)}<select id="c-weapon">{w_opts}</select></label>
    <label>{u('ammo', lang)}<select id="c-ammo">{ammo_opts}</select></label>
    <label>{u('skill_level', lang)} <output id="c-skill-o">1</output><input type="range" id="c-skill" min="1" max="{SKILL_MAX}" value="1"></label>
    <label>{u('char_level', lang)} <output id="c-lvl-o">1</output><input type="range" id="c-lvl" min="1" max="{MAX_LEVEL}" value="1"></label>
  </div>
  <div class="calc-out">
    <div><span class="calc-big" id="c-hit">0</span><small>{u('per_hit', lang)}</small></div>
    <div><span class="calc-big" id="c-dps">0</span><small>{u('per_second', lang)}</small></div>
    <div><span class="calc-big alt" id="c-pow">0</span><small id="c-pow-l">{u('power_hit', lang)}</small></div>
  </div>
  <p class="calc-note" id="c-note"></p>
</div>
<script type="application/json" id="calc-data">{json.dumps(calc_data, ensure_ascii=False)}</script>"""


def page_items(lang):
    WK, _MX = _wk()
    en = lang == "en"
    by_cat = {}
    for i in ITEMS.values():
        by_cat.setdefault(WK.item_cat(i["id"]), []).append(i)
    covered = {c for _a, cats in ITEM_SECTIONS for c in cats}
    sections = list(ITEM_SECTIONS) + [("other", tuple(sorted(c for c in by_cat if c not in covered)))]
    content, entries = "", [("slots", "Loadout" if en else "Tu equipo")]
    for anchor, cats in sections:
        its = [i for c in cats for i in by_cat.get(c, [])]
        if not its:
            continue
        title, lead = ITEM_SEC_TEXT[anchor]
        entries.append((anchor, title[lang]))
        kicker = f'{len(its)} {"items" if en else "objetos"}'
        keys = " ".join([title["en"], title["es"]] + [WK.CATS[c][x] for c in cats if c in WK.CATS for x in ("en", "es")]).lower()
        content += f'<section class="isec" data-isec data-k="{e(keys)}">{section_title(anchor, kicker, title[lang], lead[lang])}'
        content += sec_weapons(lang) if anchor == "weapons" else sec_generic(anchor, its, lang)
        content += '</section>'
    entries.append(("calculator", u("calc_title", lang)))
    content += calculator(lang)
    slots = ["head", "chest", "legs", "boots", "primary_weapon", "secondary_weapon", "tool_special", "backpack", "battery", "light"]
    slot_html = "".join(f"<li>{e(SLOTS[s][lang])}</li>" for s in slots)
    intro = f"""<div id="slots" class="panel slots"><h3>{'Your loadout' if en else 'Tu equipo'}</h3>
<p>{'Ten slots you fill from the inventory (I). Your class never locks gear: only level, attribute and skill requirements do. Civilization + Weapon + Armor + Battery + Light = Build.' if en
     else 'Diez ranuras que llenás desde el inventario (I). Tu clase nunca bloquea equipo: sólo los requisitos de nivel, atributo y habilidad. Civilización + Arma + Armadura + Batería + Luz = Build.'}</p>
<ul class="slotlist">{slot_html}</ul></div>
<div class="ifilter" role="search"><label>{svg('search')}<span class="sr">{'Filter items' if en else 'Filtrar objetos'}</span>
<input type="search" id="items-q" placeholder="{'Filter by name, skill, slot…' if en else 'Filtrá por nombre, habilidad, ranura…'}" autocomplete="off" spellcheck="false"></label>
<output id="items-n" aria-live="polite"></output></div>
<p class="note">{'Tap or click a column to sort. Wide tables scroll sideways.' if en else 'Tocá o hacé clic en una columna para ordenar. Las tablas anchas se desplazan de costado.'}</p>"""
    body = wiki_header(lang, "Items" if en else "Objetos", "Everything you carry below" if en else "Todo lo que llevás abajo",
                       "Weapons, armor, ammunition, light, drones and the rest of your kit, with real numbers from the current build." if en
                       else "Armas, armadura, munición, luz, drones y el resto de tu equipo, con números reales de la versión actual.",
                       "shots/phase13_10-armory.jpg")
    body += wiki(lang, entries, intro + content)
    return page(lang, "items", "Items" if en else "Objetos", body)


# Las paginas viejas (Arsenal, Equipo) redirigen a su seccion en Objetos; las anclas por id de objeto se conservan.
OLD_PAGES = {
    "arsenal": ("weapons", {"weapons": "weapons", "compare-table": "weapons", "offhand": "shields", "ammunition": "ammunition", "calculator": "calculator"}),
    "gear": ("armor", {"slots": "slots", "armor": "armor", "lights": "lights", "power": "power", "tools": "tools", "drones": "drones",
                       "field": "consumables", "crates": "crates"}),
}


def redirect_page(lang, slug):
    default, mapping = OLD_PAGES[slug]
    title = "Items" if lang == "en" else "Objetos"
    msg = "This page moved to" if lang == "en" else "Esta página se mudó a"
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · DEEPKIN</title>
<meta name="robots" content="noindex">
<link rel="canonical" href="items.html">
<script>(function(){{var m={json.dumps(mapping)},h=decodeURIComponent(location.hash.slice(1));location.replace("items.html#"+(m[h]||h||"{default}"));}})();</script>
<meta http-equiv="refresh" content="0; url=items.html#{default}">
<link rel="stylesheet" href="../assets/css/site.css">
</head>
<body class="gate"><main class="gate-in"><p>{msg} <a href="items.html#{default}">{title}</a>.</p></main></body>
</html>
"""


def page_resources(lang):
    ores = [i for i in ITEMS.values() if i["id"].startswith(("item.ore", "item.mineral"))]
    loot = [ITEMS[k] for k in ("item.ferrous_sample", "item.relic_fragment", "item.scrap_component", "item.component.servo_core") if k in ITEMS]
    cur = sorted([i for i in ITEMS.values() if i["id"].startswith("item.currency")], key=lambda i: i["properties"]["currency_value"])

    def rcard(i):
        found = FOUND_IN.get(i["id"])
        f = f'<p class="found"><span>{u("found_in", lang)}</span>{e(found[lang])}</p>' if found else ""
        art = icon(i["id"], alt=i["display_name"]) if os.path.exists(os.path.join(ROOT, "assets/img/icons", i["id"] + ".png")) else '<span class="icon icon-ph"></span>'
        return (f'<article class="gcard" id="{e(i["id"])}">{art}<div><p class="kicker">{status_tag(i, lang)}</p>'
                f'<h3><a href="{SL.item(i["id"])}">{e(i["display_name"])}</a></h3><p>{e(item_desc(i, lang))}</p>{f}</div></article>')

    coins = ""
    for i in cur:
        coins += (f'<article class="coin">{icon(i["id"], alt=i["display_name"])}<h3><a href="{SL.item(i["id"])}">{e(i["display_name"])}</a></h3>'
                  f'<p class="coin-v">{num(i["properties"]["currency_value"], lang)} <small>Metal</small></p><p>{e(item_desc(i, lang))}</p></article>')
    mats = sorted(MATS, key=lambda m: m["durability"] / m["drill_effectiveness"])
    mx = max(m["durability"] / m["drill_effectiveness"] for m in mats)
    mrows = ""
    for m in mats:
        name = MATERIAL_NAMES_ES.get(m["id"], m["display_name"]) if lang == "es" else m["display_name"]
        effort = m["durability"] / m["drill_effectiveness"]
        mrows += (f'<tr><td>{e(name)}</td><td class="n">{num(m["hardness"], lang)}</td><td class="n">{m["durability"]}</td>'
                  f'<td class="n">{round(m["drill_effectiveness"] * 100)}%</td><td class="effort">{bar(effort, mx)}<b>{num(effort, lang, 0)}</b></td></tr>')
    content = (section_title("ores", "Mining" if lang == "en" else "Minería", "Ores & minerals" if lang == "en" else "Minerales",
                             "Hold F at a deposit to bore it out. Everything you mine weighs something." if lang == "en"
                             else "Mantené F frente a un depósito para extraerlo. Todo lo que minás pesa algo.")
               + f'<div class="ggrid">{"".join(rcard(i) for i in ores)}</div>'
               + section_title("finds", "Salvage" if lang == "en" else "Rescate", "Finds & salvage" if lang == "en" else "Hallazgos y chatarra")
               + f'<div class="ggrid">{"".join(rcard(i) for i in loot)}</div>'
               + section_title("rock", "Geology" if lang == "en" else "Geología", "What the drill meets" if lang == "en" else "Contra qué choca el taladro",
                               "Harder rock with low drill effectiveness takes longer. Effort = durability ÷ effectiveness." if lang == "en"
                               else "La roca más dura con poca eficacia de perforación tarda más. Esfuerzo = durabilidad ÷ eficacia.")
               + f"""<div class="tablewrap"><table class="data"><thead><tr><th>{'Material' if lang == 'en' else 'Material'}</th><th>{u('hardness', lang)}</th>
<th>{u('durability', lang)}</th><th>{u('drill_eff', lang)}</th><th>{u('effort', lang)}</th></tr></thead><tbody>{mrows}</tbody></table></div>"""
               + section_title("currency", "Economy" if lang == "en" else "Economía", "Currency" if lang == "en" else "Moneda",
                               "Three coins, one stamp. Traders take the coins you carry; the bank keeps the rest." if lang == "en"
                               else "Tres monedas, un sello. Los comerciantes cobran con las monedas que llevás; el banco guarda el resto.")
               + f'<div class="coins">{coins}</div>')
    entries = [("ores", "Ores" if lang == "en" else "Minerales"), ("finds", "Finds" if lang == "en" else "Hallazgos"),
               ("rock", "Geology" if lang == "en" else "Geología"), ("currency", "Currency" if lang == "en" else "Moneda")]
    body = wiki_header(lang, "Resources" if lang == "en" else "Recursos", "Everything we need comes from below" if lang == "en" else "Todo lo que necesitamos viene de abajo",
                       "Ore, crystal, salvage and coin: what you dig, find and carry home." if lang == "en"
                       else "Mineral, cristal, chatarra y moneda: lo que excavás, encontrás y llevás a casa.",
                       "shots/world_c3.webp")
    body += wiki(lang, entries, content)
    return page(lang, "resources", "Resources" if lang == "en" else "Recursos", body)


def page_bestiary(lang):
    fac = {f["id"]: f for f in FACTIONS}
    bb = fac["faction.burrowborn"]
    F = FACTION["faction.burrowborn"]
    traits = "".join(f"<li>{e(x)}</li>" for x in F["traits"][lang])
    hier_es = {"Swarm": "Enjambre", "Brute": "Bruto", "Alpha": "Alfa"}
    hier = " → ".join(f"<span>{e(hier_es.get(x, x) if lang == 'es' else x)}</span>" for x in bb["hierarchy"].split(" → "))
    faction_html = f"""{section_title('burrowborn', 'Faction' if lang == 'en' else 'Facción', 'The Burrowborn', F['identity'][lang])}
<div class="cls-grid"><div class="panel"><p>{e(F['visual'][lang])}</p><ul class="traits">{traits}</ul></div>
<div class="panel"><dl class="kv kv-col"><div><dt>{'Communication' if lang == 'en' else 'Comunicación'}</dt><dd>{e(F['communication'][lang])}</dd></div>
<div><dt>{'Territory' if lang == 'en' else 'Territorio'}</dt><dd>{e(F['territory'][lang])}</dd></div>
<div><dt>{'Hierarchy' if lang == 'en' else 'Jerarquía'}</dt><dd class="hier">{hier}</dd></div></dl></div></div>"""

    def mob(n):
        M = MOBS[n["id"]]
        dps = n["attack_damage"] / n["attack_cooldown"]
        rules = "".join(f"<li>{e(r)}</li>" for r in M["rules"][lang])
        verbs = "".join(f"<span>{e(v)}</span>" for v in n.get("verbs", []))
        abil = ""
        for a in n.get("abilities", []):
            # Formas de habilidad (2026-10-10, dragones): golpe, cono, linea, mordida, curacion. Solo lo que trae el dato.
            bits = []
            if a.get("damage"):
                bits.append(f'{a["damage"]} {u("damage", lang).lower()}')
            if a.get("heal"):
                bits.append(f'+{round(a["heal"] * 100)}% {u("hp", lang)}')
            if a.get("radius"):
                bits.append(f'{"radius" if lang == "en" else "radio"} {num(a["radius"], lang)} m')
            if a.get("range"):
                bits.append(f'{num(a.get("min_range", 0), lang)}–{num(a["range"], lang)} m')
            if a.get("width"):
                bits.append(f'{"width" if lang == "en" else "ancho"} {num(a["width"], lang)} m')
            if a.get("half_angle") and a.get("shape") == "cone":
                bits.append(f'{num(a["half_angle"] * 2, lang)}°')
            bits.append(f'{"wind-up" if lang == "en" else "carga"} {num(a["windup"], lang)} s')
            bits.append(f'{u("cooldown", lang).lower()} {num(a["cooldown"], lang)} s')
            abil += (f'<div class="mob-ab"><p class="kicker">{"Telegraphed attack" if lang == "en" else "Ataque anunciado"}</p><h4>{e(a["name"])}</h4>'
                     f'<p>{" · ".join(bits)}</p></div>')
        faction = fac[n["faction"]]["name"] if n.get("faction") in fac else M.get("faction", L("", ""))[lang]
        has_icon = os.path.exists(os.path.join(ROOT, "assets/img/icons", n["id"] + ".png"))
        # Retrato renderizado del juego (assets/img/mobs, 2026-10-10) antes que el icono viejo de 160 px.
        if os.path.exists(os.path.join(ROOT, "assets/img/mobs", n["id"] + ".webp")):
            art = f'<img class="mob-img" src="../assets/img/mobs/{e(n["id"])}.webp" alt="{e(n["display_name"])}" loading="lazy" width="320" height="320">'
        elif has_icon:
            art = icon(n["id"], "mob-img", n["display_name"])
        else:
            art = f'<span class="mob-img mob-ph">{e(n["display_name"][0])}</span>'
        # Botin completo en la ficha (2026-10-10): chatarra + monedas + tabla "loot" del juego, cada item enlazado al wiki.
        def item_name(iid):
            return ITEMS[iid]["display_name"] if iid in ITEMS else iid
        drops = [f'<a href="{SL.item("item.scrap_component")}">Scrap Component</a> 100%']
        if n.get("coins"):
            drops.append(f'<a href="wiki/currency.html">{"Metal Coins" if lang == "en" else "Monedas de metal"}</a> {n["coins"][0]}–{n["coins"][1]}')
        for x in n.get("loot", []):
            q = x.get("quantity", [1, 1])
            qty = f" ×{q[0]}" if q[0] == q[1] and q[0] > 1 else (f" ×{q[0]}–{q[1]}" if q[0] != q[1] else "")
            drops.append(f'<a href="{SL.item(x["item"])}">{e(item_name(x["item"]))}</a>{qty} {num(round(x.get("chance", 1) * 100), lang)}%')
        drops_html = f'<p class="found"><span>{"Drops" if lang == "en" else "Botín"}</span>{" · ".join(drops)}</p>'
        threat = n.get("threat")
        threat_html = f'<div><dt>{u("threat", lang)}</dt><dd>{"◆" * min(5, max(1, round(threat / 2)))}<small>{threat}</small></dd></div>' if threat else ""
        xp_html = f'<div><dt>{u("xp", lang)}</dt><dd>{n["xp"]}</dd></div>' if n.get("xp") else ""
        return f"""<article class="mob" id="{e(n['id'])}">
  <div class="mob-art">{art}<div class="verbs">{verbs}</div></div>
  <div class="mob-main">
    <p class="kicker">{e(faction)} · {e(M['role'][lang])}</p>
    <h3><a href="{SL.mob(n['id'])}">{e(n['display_name'])}</a></h3>
    <p class="mob-lore">{e(M['lore'][lang])}</p>
    <dl class="mob-stats">
      <div><dt>{u('hp', lang)}</dt><dd>{n['max_health']}</dd></div>
      <div><dt>{u('attack', lang)}</dt><dd>{n['attack_damage']}<small>/{num(n['attack_cooldown'], lang)}s</small></dd></div>
      <div><dt>{u('dps', lang)}</dt><dd>{num(dps, lang, 1)}</dd></div>
      <div><dt>{u('speed', lang)}</dt><dd>{num(n['movement_speed'], lang)}<small>m/s</small></dd></div>
      <div><dt>{u('detection', lang)}</dt><dd>{num(n['detection_range'], lang)}<small>m</small></dd></div>
      {threat_html}{xp_html}
    </dl>
    {abil}
    <div class="mob-how"><p class="kicker">{u('how_to_fight', lang)}</p><ul>{rules}</ul></div>
    <p class="found"><span>{u('habitat', lang)}</span>{e(M['habitat'][lang])}</p>
    {drops_html}
  </div>
</article>"""

    # Todas las criaturas del juego por faccion (2026-10-23): Burrowborn, Castoffs, Mutantes, Rustbound, Wyrms; en cada
    # faccion, de menor a mayor tier (el orden de los datos desempata).
    by_id = {n["id"]: n for n in NPCS}

    def of(fid):
        ms = [n for n in NPCS if n.get("faction") == fid and n["id"] in MOBS and MOBS[n["id"]].get("lore")]
        # El tier del dato es texto (normal / elite / boss): se ordena por rango, no alfabeticamente (2026-10-27).
        rank = {"normal": 0, "elite": 1, "boss": 2}
        return "".join(mob(n) for n in sorted(ms, key=lambda n: (rank.get(n.get("tier"), 0), n.get("max_health", 0))))
    burrow = of("faction.burrowborn")
    human = of("faction.castoffs")
    mutants = of("faction.mutants")
    rust = of("faction.rustbound")
    wyrms = of("faction.wyrms")
    # Capturas de los dragones en The Cinder Deep (2026-10-10): reposo y aviso de la ola de fuego.
    wyrm_shots = '<div class="wyrm-shots">' + "".join(
        f'<figure><a href="../assets/img/{b}.webp"><img src="../assets/img/{b}_800.webp" srcset="../assets/img/{b}_800.webp 800w, ../assets/img/{b}.webp 1600w" '
        f'sizes="(max-width: 680px) 100vw, 50vw" alt="{e(c[lang])}" width="800" height="450" loading="lazy" decoding="async"></a><figcaption>{e(c[lang])}</figcaption></figure>'
        for mid in ("npc.dragon", "npc.greater_dragon") for b, c in MOB_SHOTS.get(mid, [])) + "</div>"
    rumours = ""
    for fid in [f["id"] for f in FACTIONS if f.get("status") == "planned" and f["id"] in FACTION]:
        f = fac[fid]
        rumours += (f'<article class="rumour"><p class="kicker">{e(FACTION[fid]["identity"][lang])}</p><h3>{e(f["name"])}</h3>'
                    f'<p>{e(FACTION[fid]["rumour"][lang])}</p><span class="tag tag-soon">{u("planned", lang)}</span></article>')
    content = (faction_html + f'<div class="mobs">{burrow}</div>'
               + section_title("humans", "Faction" if lang == "en" else "Facción", "People" if lang == "en" else "Gente",
                               "Not everything down here is an animal." if lang == "en" else "No todo lo que hay acá abajo es un animal.")
               + f'<div class="mobs">{human}</div>'
               + section_title("mutants", "Faction" if lang == "en" else "Facción", fac["faction.mutants"]["name"] if "faction.mutants" in fac else "The Mutants",
                               "The Saltpan's edges belong to something that used to be people." if lang == "en" else "Los bordes del Saltpan son de algo que antes era gente.")
               + f'<div class="mobs">{mutants}</div>'
               + section_title("rustbound", "Faction" if lang == "en" else "Facción", fac["faction.rustbound"]["name"],
                               "Under the Sump, VDI's machines still receive instructions." if lang == "en" else "Bajo el Sump, las máquinas de VDI todavía reciben instrucciones.")
               + f'<div class="mobs">{rust}</div>'
               + section_title("wyrms", "Faction" if lang == "en" else "Facción", "The Wyrms",
                               "Below Frontier Road east, something keeps a nest." if lang == "en" else "Bajo Frontier Road este, algo cuida un nido.")
               + wyrm_shots
               + f'<div class="mobs">{wyrms}</div>'
               + section_title("rumours", "Field reports" if lang == "en" else "Informes de campo", "Rumours from below" if lang == "en" else "Rumores de abajo",
                               "Operators come back with stories. Some of them are true." if lang == "en" else "Los operadores vuelven con historias. Algunas son ciertas.")
               + f'<div class="rumours">{rumours}</div>')
    entries = [("burrowborn", "Burrowborn"), ("humans", "People" if lang == "en" else "Gente"), ("mutants", "Mutants" if lang == "en" else "Mutantes"),
               ("rustbound", "Rustbound"), ("wyrms", "Wyrms"),
               ("rumours", "Rumours" if lang == "en" else "Rumores")]
    body = wiki_header(lang, "Bestiary" if lang == "en" else "Bestiario", "What hunts below" if lang == "en" else "Lo que caza abajo",
                       "Know what you are fighting before it knows you are there." if lang == "en" else "Conocé contra qué peleás antes de que sepa que estás ahí.",
                       "concept/tile_wilds.jpg")
    body += wiki(lang, entries, content)
    return page(lang, "bestiary", "Bestiary" if lang == "en" else "Bestiario", body)


# Equipo de cabeza por clase (2026-10-11, docs/CLASSES.md "Class visual identity"). Sólo apariencia.
HEADGEAR = {
    "foundry": L("A heavy welder's cap with a flipped-up welding lens glowing amber and a twin-filter respirator; anvil-and-hammer patch on the shoulder.",
                 "Una gorra pesada de soldador con la lente levantada que brilla ámbar y un respirador de doble filtro; parche de yunque y martillo en el hombro."),
    "drift": L("Expedition goggles with blue lenses over the cap and a sand scarf trailing over the left shoulder; chevron emblem.",
               "Antiparras de expedición con lentes azules sobre la gorra y una bufanda de arena que cae sobre el hombro izquierdo; emblema de galón."),
    "verdant": L("An organic filter mask with two seed-pod filters, fungal caps on the temple and two leaves at the crown; leaf emblem.",
                 "Una máscara de filtro orgánica con dos filtros de vaina, hongos en la sien y dos hojas en la coronilla; emblema de hoja."),
    "relay": L("A wrap-around violet visor and a headset with a mic boom and a glowing antenna tip; three-node network emblem.",
               "Un visor violeta envolvente y un auricular con micrófono y la punta de la antena encendida; emblema de red de tres nodos."),
}

ATLAS_SIZES = {}


def atlas_section(lang):
    """Atlas ilustrado del mundo (2026-10-11): lamina generada por src/atlas.py. Desde 2026-10-12 va despues del mapa
    interactivo y su corte de profundidad se incrusta en linea (data-zone por placa) para resaltarse junto con el mapa."""
    sz = ATLAS_SIZES.get(lang) or {"wide": (1600, 1808), "tall": (640, 3400)}
    # En la pagina va la lamina SIN corte (el corte vive en linea arriba); los enlaces abren la lamina completa.
    (w, h), (tw_, th) = sz.get("page_wide", sz["wide"]), sz.get("page_tall", sz["tall"])
    base = f"../assets/img/world/atlas_{lang}"
    en = lang == "en"
    alt = ("Field atlas: plan of the playable region with every map, passage and service, a depth cross-section from the surface "
           "to the Deep Survey's floor 3 (520 m), the recommended route from the Outpost to Dustline and the stairs down to the Cinder Deep."
           if en else "Atlas de campo: planta de la región jugable con cada mapa, pasaje y servicio, un corte de profundidad desde la "
           "superficie hasta el piso 3 de The Deep Survey (520 m), la ruta recomendada del Outpost a Dustline y la escalera a The Cinder Deep.")
    hint = ("Ctrl / ⌘ + scroll, double-click or pinch to zoom · drag to move" if en
            else "Ctrl / ⌘ + rueda, doble clic o pellizco para hacer zoom · arrastrá para moverte")
    ctrl = (f'<div class="atlas-ctrl"><button type="button" data-azoom="in" aria-label="{"Zoom in" if en else "Acercar"}">+</button>'
            f'<button type="button" data-azoom="out" aria-label="{"Zoom out" if en else "Alejar"}">−</button>'
            f'<button type="button" data-azoom="reset" aria-label="{"Reset view" if en else "Restablecer vista"}">⤢</button></div>')
    sec = AT.section_inline(lang)
    sec_cap = ("Live with the map above: the zone you pick lights up here. Hover a plate to find it on the map, click it to open it on its level."
               if en else "Vive con el mapa de arriba: la zona que elegís se enciende acá. Pasá por una placa para ubicarla en el mapa, hacé clic para abrirla en su nivel.")
    sec_fig = (f'<figure class="atlas-sec" data-atlas-sec>{sec["w"]}{sec["t"]}<figcaption>{e(sec_cap)}</figcaption></figure>')
    return (section_title("atlas", "Field atlas" if en else "Atlas de campo", "How the maps connect" if en else "Cómo se conectan los mapas",
                          "The same world as a surveyor's sheet: the depth cross-section first, then the plan with surface and workings and every passage with the sign you will read in the game. Follow the amber line from the Outpost to Dustline; the full-size links open the complete sheet."
                          if en else "El mismo mundo como lámina de relevamiento: primero el corte de profundidad, después la planta con superficie y galerías y cada pasaje con el cartel que vas a leer en el juego. Seguí la línea ámbar del Outpost a Dustline; los enlaces de tamaño completo abren la lámina entera.")
            + sec_fig
            + f'<figure class="atlas" data-atlas><div class="atlas-vp" tabindex="0" aria-label="{e(alt)}"><div class="atlas-stage">'
            f'<picture><source media="(max-width: 720px)" srcset="{base}_page_m.svg" width="{tw_}" height="{th}">'
            f'<img src="{base}_page.svg" width="{w}" height="{h}" alt="{e(alt)}" decoding="async" draggable="false"></picture></div></div>{ctrl}'
            f'<figcaption><span class="atlas-hint">{e(hint)}</span><span class="atlas-links"><a href="{base}.svg" target="_blank" rel="noopener">'
            f'{"Open full size" if en else "Abrir en tamaño completo"} ↗</a><a href="{base}_m.svg" target="_blank" rel="noopener">{"Phone version" if en else "Versión para teléfono"} ↗</a></span></figcaption></figure>')


def lore_section(lang):
    def entry(eid, kicker, title, body, link, _col=None, extra=""):
        more = f'<a class="textlink" href="{link}">{"Read more" if lang == "en" else "Leer más"} {svg("arrow")}</a>' if link else ""
        return (f'<article class="lore-e reveal" id="lore-{eid}"><p class="kicker">{e(kicker[lang])}</p><h3>{e(title[lang])}</h3>'
                f'<p>{e(body[lang])}</p>{extra}{more}</article>')
    civs = "".join(f'<a class="lore-civ" href="classes.html#{CLASS_KEY[cid]}" style="--c:{class_color(cid)}"><b>{e(name[lang])}</b>'
                   f'<span>{e(CLASS_BY_ID[cid]["name"])} · {e(city)}</span><small>{e(line[lang])}</small></a>' for cid, name, city, line in LO.CIVS)
    first = entry(*LO.ENTRIES[0])
    second = entry(*LO.ENTRIES[1], extra=f'<div class="lore-civs">{civs}</div>')
    rest = "".join(entry(*m) for m in LO.MORE)
    return (section_title("lore", "Lore" if lang == "en" else "Historia", LO.TITLE[lang], LO.LEAD[lang])
            + f'<div class="lore">{first}{second}{rest}</div>')


def page_world(lang):
    route = ""
    for r in TX.REGIONS:
        pts = "".join(f"<li>{e(p)}</li>" for p in r["points"][lang])
        route += f"""<article class="region" id="{r['id']}">
  <figure>{shot(r['img'], r['cap'][lang])}<figcaption>{e(r['cap'][lang])}</figcaption></figure>
  <div class="region-body">
    <p class="kicker"><span class="stratum">{r['depth']}</span>{e(r['kind'][lang])}</p>
    <h3>{e(r['name'])}</h3>
    <p class="region-lead">{e(r['lead'][lang])}</p>
    <p>{e(r['body'][lang])}</p>
    <ul class="points">{pts}</ul>
  </div>
  {shot_strip(r.get('more'), lang)}
</article>"""
    surface = ""
    for r in TX.SURFACE:
        surface += f"""<article class="region region-wide" id="{r['id']}">
  <figure>{shot(r['img'], r['cap'][lang])}<figcaption>{e(r['cap'][lang])}</figcaption></figure>
  <div class="region-body"><p class="kicker">{e(r['kind'][lang])}</p><h3>{e(r['name'])}</h3><p class="region-lead">{e(r['lead'][lang])}</p><p>{e(r['body'][lang])}</p></div>
  {shot_strip(r.get('more'), lang)}
</article>"""
    # El camino al este (2026-10-10): Frontier Road, Dustline y The Cinder Deep, con capturas actuales.
    east = ""
    for r in TX.EAST:
        # Tarjetas sin captura todavia (2026-10-23): solo el texto, a todo el ancho.
        has_shot = os.path.exists(os.path.join(ROOT, "assets", "img", r["img"] + ".webp"))
        fig = f"<figure>{shot(r['img'], r['cap'][lang])}<figcaption>{e(r['cap'][lang])}</figcaption></figure>" if has_shot else ""
        east += f"""<article class="region region-wide" id="{r['id']}"{'' if has_shot else ' style="grid-template-columns: 1fr"'}>
  {fig}
  <div class="region-body"><p class="kicker">{e(r['kind'][lang])}</p><h3>{e(r['name'])}</h3><p class="region-lead">{e(r['lead'][lang])}</p><p>{e(r['body'][lang])}</p></div>
  {shot_strip(r.get('more'), lang)}
</article>"""
    tiles = "".join(f'<figure class="tile"><img src="../assets/img/concept/{img}.jpg" alt="" loading="lazy"><figcaption><b>{e(n[lang])}</b><span>{e(d[lang])}</span></figcaption></figure>'
                    for img, n, d in TX.CONCEPT_REGIONS)
    cities = ""
    for cid, (city, line) in STORY[lang]["cities"].items():
        cities += (f'<a class="city" href="classes.html#{CLASS_KEY[cid]}" style="--c:{class_color(cid)}"><span class="city-name">{e(city)}</span>'
                   f'<span class="city-civ">{e(CLASS_BY_ID[cid]["name"])} · {e(CLASSES[cid]["title"][lang])}</span><span class="city-line">{e(line)}</span></a>')
    machines = "".join(f'<figure class="machine" style="--c:{class_color(cid)}"><img src="../assets/img/concept/{img}.jpg" alt="{n}" loading="lazy"><figcaption><b>{n}</b><span>{e(CLASS_BY_ID[cid]["name"])} · {e(d[lang])}</span></figcaption></figure>'
                       for img, n, cid, d in TX.MACHINES)
    content = (lore_section(lang)
               + section_title("route", "The way down" if lang == "en" else "El camino hacia abajo", "The starting region" if lang == "en" else "La región inicial",
                             "The Outpost → shaft lift → The Threshold → The Shallows → The Deep Survey.")
               + f'<div class="regions">{route}</div>'
               + section_title("surface", "Open sky" if lang == "en" else "Cielo abierto", "The surface" if lang == "en" else "La superficie",
                               "The surface was never completely abandoned. A shaft on The Scarp drops straight to The Threshold." if lang == "en"
                               else "La superficie nunca fue completamente abandonada. Un pozo en The Scarp baja directo a The Threshold.")
               + f'<div class="regions">{surface}</div>'
               + section_title("east", "Frontier Road" if lang == "en" else "Frontier Road", "The road east" if lang == "en" else "El camino al este",
                               "From The Saltpan the old road runs east to Dustline. A cleft on the way drops into The Cinder Deep." if lang == "en"
                               else "Desde The Saltpan la vieja ruta sigue al este hasta Dustline. Una grieta en el camino baja a The Cinder Deep.")
               + f'<div class="regions">{east}</div>'
               + section_title("civilisations", "Beyond the region" if lang == "en" else "Más allá de la región", "The four cities" if lang == "en" else "Las cuatro ciudades",
                               "Home of each civilisation. You will hear of them long before you reach them." if lang == "en" else "El hogar de cada civilización. Vas a oír de ellas mucho antes de llegar.")
               + f'<div class="cities">{cities}</div>'
               + section_title("regions", "The wider world" if lang == "en" else "El mundo", "Five kinds of place" if lang == "en" else "Cinco tipos de lugar")
               + f'<div class="tiles">{tiles}</div>'
               + section_title("machines", u("planned", lang), "Excavators" if lang == "en" else "Excavadoras",
                               "One day the drill becomes a machine you ride: your mount, your cargo and your way through the hardest rock." if lang == "en"
                               else "Algún día el taladro será una máquina que manejás: tu montura, tu carga y tu camino a través de la roca más dura.")
               + f'<div class="machines">{machines}</div>')
    entries = [("map", "Interactive map" if lang == "en" else "Mapa interactivo"), ("atlas", "Field atlas" if lang == "en" else "Atlas de campo"),
               ("lore", "Lore" if lang == "en" else "Historia"),
               ("route", "Starting region" if lang == "en" else "Región inicial"), ("surface", "Surface" if lang == "en" else "Superficie"),
               ("east", "The road east" if lang == "en" else "El camino al este"),
               ("civilisations", "Cities" if lang == "en" else "Ciudades"), ("regions", "The wider world" if lang == "en" else "El mundo"),
               ("machines", "Excavators" if lang == "en" else "Excavadoras")]
    body = wiki_header(lang, "World" if lang == "en" else "Mundo", "Every layer hides a history" if lang == "en" else "Cada estrato esconde una historia",
                       "Depth is not the only danger. A shallow flooded tunnel can be worse than a deep, dry cavern." if lang == "en"
                       else "La profundidad no es el único peligro. Un túnel inundado poco profundo puede ser peor que una caverna profunda y seca.",
                       "concept/city.jpg")
    # Orden (2026-10-12): primero el mapa interactivo con su leyenda y el viaje, despues el atlas de campo a todo el
    # ancho, y recien entonces el resto con el indice repetido como guia visual.
    body += wiki(lang, entries, WM.section(lang, section_title)).replace('class="wrap wiki"', 'class="wrap wiki wiki-first"', 1)
    body += f'<div class="wrap atlas-wrap">{atlas_section(lang)}</div>'
    body += wiki(lang, entries, content, ghost_toc=True)
    head = ('<link rel="stylesheet" href="../assets/css/worldmap.css">\n<script defer src="../assets/js/worldmap.js"></script>\n'
            '<script defer src="../assets/js/atlas.js"></script>')
    return page(lang, "world", "World" if lang == "en" else "Mundo", body, extra_head=head)


def page_manual(lang):
    steps = "".join(f'<li><h3>{e(a[lang])}</h3><p>{e(b[lang])}</p></li>' for a, b in TX.FIRST_STEPS)
    keys = "".join(f'<div class="kb"><kbd>{e(k)}</kbd><span>{e(d[lang])}</span></div>' for k, d in TX.CONTROLS)
    tiers = "".join(f'<div class="tierc"><b>T{i + 1}</b><span>{u("level", lang)} {lv}+</span></div>' for i, lv in enumerate(GEAR_TIER_LEVELS))
    xp_rows = "".join(f'<tr><td>{lv}</td><td class="n">{num(xp_to_next(lv), lang)}</td><td class="n">{num(GD.total_xp(lv + 1), lang)}</td></tr>'
                      for lv in (1, 2, 5, 10, 15, 20, 30, 40, 60, 100))
    mob_xp = {n["id"]: n.get("xp", 0) for n in NPCS}
    xps = num(CM.XP_PER_ATTACK_SECOND, lang)
    fc = CLASS_BY_ID["class.foundry"]["combat_coefficients"]
    skill_rows = "".join(f'<tr><td>{lv}</td><td class="n">{num(skill_xp_for(lv), lang)}</td><td class="n">{num(skill_xp_for(lv) / CM.XP_PER_ATTACK_SECOND, lang, 0)}</td><td class="n">+{lv - 1}%</td></tr>'
                         for lv in (2, 5, 10, 25, 50, 75, 100))
    fam_list = "".join(f'<li><b>{e(FAMILIES[f][lang])}</b><span>{e(FAMILY_DESC[f][lang])}</span></li>' for f in FAMILIES)
    en = lang == "en"
    content = f"""
{section_title('first', 'Newcomers' if en else 'Recién llegados', 'Your first descent' if en else 'Tu primer descenso')}
<ol class="steps">{steps}</ol>

{section_title('controls', 'Keyboard & mouse' if en else 'Teclado y mouse', 'Controls' if en else 'Controles')}
<div class="keys">{keys}</div>

{section_title('attributes', 'Character' if en else 'Personaje', 'Attributes' if en else 'Atributos',
               'Four attributes, set by your class. Level does not inflate them: your gear and your training do the growing.' if en
               else 'Cuatro atributos, definidos por tu clase. El nivel no los infla: crecen tu equipo y tu entrenamiento.')}
<div class="cls-grid">
  <div class="panel"><dl class="kv kv-col">{''.join(f'<div><dt>{e(ATTRS[a][lang])}</dt><dd>{e(ATTR_DESC[a][lang])}</dd></div>' for a in ATTRS)}</dl></div>
  <div class="panel formula">
    <p class="kicker">{'How it adds up' if en else 'Cómo se calcula'}</p>
    <p><b>{u('health', lang)}</b> = 76 + 4 × {ATTRS['endurance'][lang]}</p>
    <p><b>{u('stamina', lang)}</b> = 5 × {ATTRS['endurance'][lang]}</p>
    <p><b>{'Attribute bonus' if en else 'Bono de atributo'}</b> = +1.5% {'per point above 10 (−25% … +25%)' if en else 'por punto sobre 10 (−25% … +25%)'}</p>
    <p><b>{'Melee' if en else 'Cuerpo a cuerpo'}</b> {'uses' if en else 'usa'} {ATTRS['might'][lang]} · <b>{'Ranged' if en else 'A distancia'}</b> {'uses' if en else 'usa'} {ATTRS['precision'][lang]}</p>
    <p><b>{'Power cost' if en else 'Costo de poderes'}</b> −1.5% {'per' if en else 'por'} {ATTRS['technology'][lang]} {'above 10 (max −30%)' if en else 'sobre 10 (máx. −30%)'}</p>
  </div>
</div>

{section_title('combat', 'Combat' if en else 'Combate', 'Damage & defense' if en else 'Daño y defensa')}
<div class="cls-grid">
  <div class="panel formula">
    <p class="kicker">{'Your hit' if en else 'Tu golpe'}</p>
    <p class="eq">{'weapon base × class coefficient × attribute bonus × skill bonus × ammo × (1 + trait %)' if en else 'base del arma × coeficiente de clase × bono de atributo × bono de habilidad × munición × (1 + rasgo %)'}</p>
    <p>{f'Each class has a melee, ranged, ability and defense coefficient. Foundry swings at ×{num(fc["melee"], lang)} but shoots at ×{num(fc["ranged"], lang)}; Drift is the reverse. Each weapon skill adds its trait as a percentage (Heat, Ambush, Range, Suppression, Overcharge, Crush).' if en
        else f'Cada clase tiene un coeficiente cuerpo a cuerpo, a distancia, de habilidad y de defensa. La Forja golpea a ×{num(fc["melee"], lang)} pero dispara a ×{num(fc["ranged"], lang)}; La Deriva, al revés. Cada habilidad de arma suma su rasgo como porcentaje (Calor, Emboscada, Alcance, Supresión, Sobrecarga, Aplastar).'}</p>
    <a class="textlink" href="items.html#calculator">{u('calc_title', lang)} {svg('arrow')}</a>
  </div>
  <div class="panel formula">
    <p class="kicker">{'Their hit' if en else 'Su golpe'}</p>
    <p class="eq">{'reduction = rating ÷ (rating + 100), max 75%' if en else 'reducción = valor ÷ (valor + 100), máx. 75%'}</p>
    <p>{'Armor counts against physical damage, resistance against everything else. 100 armor halves a physical hit.' if en
        else 'La armadura cuenta contra el daño físico y la resistencia contra todo lo demás. 100 de armadura reduce un golpe físico a la mitad.'}</p>
    <p>{'Foundry starts at 63 armor (−39%). Relay starts at 3.' if en else 'La Forja empieza con 63 de armadura (−39%). La Red empieza con 3.'}</p>
  </div>
</div>

{section_title('skills', 'Training' if en else 'Entrenamiento', 'Weapon skills' if en else 'Habilidades de arma',
               'Skills belong to weapon families, not classes. Every hit that lands trains the family of the weapon that dealt it.' if en
               else 'Las habilidades pertenecen a familias de armas, no a clases. Cada golpe que conectás entrena la familia del arma que lo dio.')}
<div class="cls-grid">
  <div class="panel"><ul class="fams">{fam_list}</ul></div>
  <div class="panel">
    <p>{f'Skills train by time, not by hits: every weapon earns {xps} skill XP per second of attacking (a slow hammer blow is worth more than a quick knife cut), 8 per hit blocked with a shield. Your class affinity multiplies it (×1.5 for its specialties, ×0.5 for families it has no feel for). Each skill level adds +1% damage with that family, up to level 100.' if en
        else f'Las habilidades se entrenan por tiempo, no por golpes: toda arma da {xps} XP de habilidad por segundo de ataque (un golpe lento de martillo vale más que un corte rápido de cuchillo), 8 por golpe bloqueado con escudo. La afinidad de tu clase lo multiplica (×1,5 en sus especialidades, ×0,5 en las familias que no domina). Cada nivel suma +1% de daño con esa familia, hasta el nivel 100.'}</p>
    <div class="tablewrap"><table class="data compact"><thead><tr><th>{'Skill' if en else 'Nivel'}</th><th>{'Total XP' if en else 'XP total'}</th><th>{'Seconds of attacking (×1)' if en else 'Segundos de ataque (×1)'}</th><th>{u('damage', lang)}</th></tr></thead><tbody>{skill_rows}</tbody></table></div>
    <p class="note">{'Shielding: 8% damage reduction with a shield, +0.2% per level, up to 40%.' if en else 'Escudos: 8% de reducción con escudo, +0,2% por nivel, hasta 40%.'}</p>
  </div>
</div>

{section_title('levels', 'Progression' if en else 'Progresión', 'Levels & gear tiers' if en else 'Niveles y rangos de equipo',
               'There is no level cap, and every level costs more than the last. Creatures award XP when they fall; each level adds +0.6% to all your damage and unlocks better gear tiers.' if en
               else 'No hay tope de nivel, y cada nivel cuesta más que el anterior. Las criaturas dan XP al caer; cada nivel suma +0,6% a todo tu daño y desbloquea mejores rangos de equipo.')}
<div class="tiers">{tiers}</div>
<div class="cls-grid">
  <div class="tablewrap"><table class="data compact"><thead><tr><th>{u('level', lang)}</th><th>{'XP to next' if en else 'XP al siguiente'}</th><th>{'Total to reach next' if en else 'Total para el siguiente'}</th></tr></thead><tbody>{xp_rows}</tbody></table></div>
  <div class="panel"><p class="eq">{'total XP for level L = 50/3 · (L³ − 6L² + 17L − 12)' if en else 'XP total para el nivel L = 50/3 · (L³ − 6L² + 17L − 12)'}</p>
  <p>{f'Level 40 takes {num(GD.total_xp(40), lang)} XP in total. A Crawler is worth {mob_xp.get("npc.burrowborn_crawler")}, a Ravager {mob_xp.get("npc.burrowborn_ravager")}, a Dragon {mob_xp.get("npc.dragon")}.' if en else f'El nivel 40 requiere {num(GD.total_xp(40), lang)} XP en total. Un Crawler vale {mob_xp.get("npc.burrowborn_crawler")}; un Ravager, {mob_xp.get("npc.burrowborn_ravager")}; un Dragon, {mob_xp.get("npc.dragon")}.'}</p>
  <a class="textlink" href="wiki/experience.html">{'XP calculator & kill XP' if en else 'Calculadora de XP y XP por criatura'} {svg('arrow')}</a>
  <p>{'Gear can also ask for a minimum level or attribute. The class never locks an item.' if en else 'El equipo también puede pedir un nivel o atributo mínimo. La clase nunca bloquea un objeto.'}</p></div>
</div>

{section_title('light', 'Survival' if en else 'Supervivencia', 'Light & energy' if en else 'Luz y energía')}
<div class="cls-grid">
  <div class="panel"><p>{'Your battery sets your energy. The lantern drains it every second it is on, and abilities spend it too. There is no recharging on an expedition: when it hits zero, the light goes out.' if en
      else 'Tu batería define tu energía. La linterna la consume cada segundo que está encendida, y las habilidades también gastan. No hay recarga durante una expedición: cuando llega a cero, la luz se apaga.'}</p>
      <p>{'Toggle the lantern with T. Unequipping the battery empties your energy; equipping it again does not refill it.' if en else 'Prendé o apagá la linterna con T. Quitar la batería vacía tu energía; volver a equiparla no la recarga.'}</p></div>
  <div class="panel"><p class="eq">{'Simple Lantern: 9 m radius · 0.15/s · ≈ 11 min on Battery Cell I' if en else 'Simple Lantern: radio 9 m · 0,15/s · ≈ 11 min con Battery Cell I'}</p>
      <a class="textlink" href="items.html#lights">{'Compare lights' if en else 'Comparar luces'} {svg('arrow')}</a></div>
</div>

{section_title('drilling', 'Excavation' if en else 'Excavación', 'Drilling' if en else 'Perforación')}
<div class="cls-grid">
  <div class="panel"><p>{'Equip the Big Daddy Drill in the tool slot and hold F at a drill site. Ore seams give up resources; sealed walls of basalt open new routes. Some routes only exist once you drill them.' if en
      else 'Equipá el Big Daddy Drill en la ranura de herramienta y mantené F en un punto de perforación. Las vetas sueltan recursos; los muros sellados de basalto abren rutas nuevas. Algunas rutas sólo existen cuando las perforás.'}</p></div>
  <div class="panel"><p>{'Every material has hardness, durability and a drill effectiveness. Soft rock gives way at once; reinforced relic material fights back.' if en
      else 'Cada material tiene dureza, durabilidad y eficacia de perforación. La roca blanda cede enseguida; el material reliquia reforzado se resiste.'}</p>
      <a class="textlink" href="resources.html#rock">{'See the rock table' if en else 'Ver la tabla de rocas'} {svg('arrow')}</a></div>
</div>

{section_title('carry', 'Logistics' if en else 'Logística', 'Carry weight' if en else 'Peso de carga')}
<div class="panel"><p>{'Everything has weight: what you wear and what you haul. Foundry starts with 80 kg of carry and gains 2.5 per level; Relay starts with 45. A backpack adds 20 cells that travel with it and +15 kg. Drop the pack, and everything in it stays with the pack.' if en
     else 'Todo pesa: lo que vestís y lo que acarreás. La Forja empieza con 80 kg de carga y suma 2,5 por nivel; La Red empieza con 45. Una mochila suma 20 celdas que viajan con ella y +15 kg. Si soltás la mochila, todo lo que tiene se queda con ella.'}</p></div>
"""
    entries = [("first", "First descent" if en else "Primer descenso"), ("controls", "Controls" if en else "Controles"),
               ("attributes", "Attributes" if en else "Atributos"), ("combat", "Combat" if en else "Combate"),
               ("skills", "Weapon skills" if en else "Habilidades"), ("levels", "Levels" if en else "Niveles"),
               ("light", "Light" if en else "Luz"), ("drilling", "Drilling" if en else "Perforación"), ("carry", "Carry" if en else "Carga")]
    body = wiki_header(lang, "Field Manual" if en else "Manual de campo", "How the deep works" if en else "Cómo funciona lo profundo",
                       "Controls, numbers and the rules the server plays by. Read it once; it will save your light." if en
                       else "Controles, números y las reglas con las que juega el servidor. Leelo una vez; te va a ahorrar luz.",
                       "shots/field_hud.jpg")
    body += wiki(lang, entries, content)
    return page(lang, "manual", "Field Manual" if en else "Manual de campo", body)


def root_index():
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>DEEPKIN — What lies below</title>
<meta name="description" content="DEEPKIN — a cooperative underground action RPG. Choose your language · Elige tu idioma.">
<link rel="icon" href="assets/img/deepkin_mark.png">
<link rel="alternate" hreflang="en" href="en/index.html">
<link rel="alternate" hreflang="es" href="es/index.html">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400&family=Saira+Condensed:wght@600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/css/site.css">
<script>
(function(){
  var p=null; try{p=localStorage.getItem('deepkin-lang')}catch(e){}
  if(location.search.indexOf('choose')>-1) return;
  var l=p||((navigator.language||'en').toLowerCase().indexOf('es')===0?'es':'en');
  location.replace(l+'/index.html');
})();
</script>
</head>
<body class="gate">
<main class="gate-in">
  <img src="assets/img/deepkin_logo.png" alt="DEEPKIN — What lies below" width="1356" height="559">
  <div class="cta">
    <a class="btn btn-solid" href="en/index.html" data-setlang="en">English</a>
    <a class="btn" href="es/index.html" data-setlang="es">Español</a>
  </div>
  <p class="signal">261.6.66</p>
</main>
<script src="assets/js/site.js"></script>
</body>
</html>
"""


# Lo que --sync copia del repo del juego (2026-10-10): entidades, mundo, dialogos, misiones y las reglas en .gd
# (se leen las constantes, nunca se copian a mano).
SYNC_ENTITIES = ("classes", "items", "npcs", "materials", "factions", "discoveries", "vehicles")
SYNC_FILES = {
    "data/world/world_map.json": "world/world_map.json",
    "data/world/respawn_hubs.json": "world/respawn_hubs.json",
    "data/world/zone_banners.json": "world/zone_banners.json",
    "data/starting_region.json": "starting_region.json",
    "shared/gameplay/rpg_rules.gd": "rules/rpg_rules.gd",
    "shared/gameplay/weapon_skills.gd": "rules/weapon_skills.gd",
    "shared/gameplay/combat_skills.gd": "rules/combat_skills.gd",
    # Rasgos en porcentaje, Trailblazer e intervalo por defecto (pase de balance 2026-10-24, src/combat_math.py).
    "shared/gameplay/combat_system.gd": "rules/combat_system.gd",
    "server/death_penalty.gd": "rules/death_penalty.gd",
}
# Tiendas, casas y plantillas de excavacion (Fases 3-7, 2026-10-23): los lee el wiki (comercio, casas, excavaciones).
SYNC_DIRS = {"data/world/sets": "world/sets", "data/dialog": "dialog", "data/quests": "quests",
             "data/shops": "shops", "data/houses": "houses", "data/excavation": "excavation"}
# Constantes sueltas de archivos grandes del juego: (archivo, nombre) -> se guardan en data/rules/constants.json.
SYNC_CONSTANTS = [
    ("server/server_world.gd", "SCRAP_COMPONENT_ID"), ("server/server_world.gd", "COIN_ITEM_ID"),
    ("server/server_world.gd", "STARTER_AMMUNITION_ID"), ("shared/gameplay/player_inventory.gd", "POUCH_CELLS"),
    ("shared/networking/messages/depot_view.gd", "CELLS"), ("shared/networking/messages/computer_command.gd", "REACH"),
    ("client/terminal_commands.gd", "NETWORK_ADDRESS"),
    # Banco y combustible (2026-10-11): tope del saldo y alcances del surtidor.
    ("shared/gameplay/bank_rules.gd", "MAX_BALANCE"), ("world/fuel_station.gd", "COMPUTER_REACH"),
    ("world/fuel_station.gd", "PUMP_REACH"),
    # Fases 2-7 (2026-10-23): grupos, drones, regeneracion de bateria, ejecuciones, vehiculos y excavaciones (wiki_mech.py).
    ("shared/gameplay/party_rules.gd", "MAX_MEMBERS"), ("shared/gameplay/party_rules.gd", "SHARE_RANGE"),
    ("shared/gameplay/party_rules.gd", "INVITE_SECONDS"), ("shared/gameplay/party_rules.gd", "INVITE_RANGE"),
    ("shared/gameplay/drone_rules.gd", "MAX_PER_OWNER"), ("shared/gameplay/drone_rules.gd", "MIN_LAUNCH_SECONDS"),
    ("shared/gameplay/drone_rules.gd", "ASSAULT_HARD_DAMAGE_CAP"), ("shared/gameplay/drone_rules.gd", "ASSAULT_TIER_FACTOR"),
    ("shared/gameplay/drone_rules.gd", "KAMIKAZE_HARD_DAMAGE_CAP"), ("shared/gameplay/drone_rules.gd", "KAMIKAZE_TIER_FACTOR"),
    ("shared/gameplay/drone_rules.gd", "BLAST_EDGE_FACTOR"), ("shared/gameplay/drone_rules.gd", "TARGET_MEMORY"),
    ("shared/gameplay/battery_regen.gd", "RATE"), ("shared/gameplay/execution_rules.gd", "EXECUTE_HEALTH_RATIO"),
    ("shared/gameplay/vehicle_rules.gd", "MAX_OWNED"),
    ("shared/gameplay/excavation_rules.gd", "CALL_OUT_AHEAD"), ("shared/gameplay/excavation_rules.gd", "SITE_SPACING"),
    ("shared/gameplay/excavation_rules.gd", "DROP_SECONDS"), ("shared/gameplay/excavation_rules.gd", "TRANSIT_SECONDS"),
    ("shared/gameplay/excavation_rules.gd", "MAX_ROSTER"), ("shared/gameplay/excavation_rules.gd", "ENERGY_MAX"),
    ("shared/gameplay/excavation_rules.gd", "FUEL_MAX"), ("shared/gameplay/excavation_rules.gd", "START_ENERGY"),
    ("shared/gameplay/excavation_rules.gd", "START_FUEL"), ("shared/gameplay/excavation_rules.gd", "ENERGY_PER_DEPTH"),
    ("shared/gameplay/excavation_rules.gd", "FUEL_PER_DEPTH"), ("shared/gameplay/excavation_rules.gd", "MAX_FLOORS"),
]


def sync():
    src = os.path.join(GAME_REPO, "data", "entities")
    for sub in SYNC_ENTITIES:
        dst = os.path.join(ROOT, "data", sub)
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(os.path.join(src, sub), dst)
    for a, b in SYNC_FILES.items():
        dst = os.path.join(ROOT, "data", b)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(os.path.join(GAME_REPO, a), dst)
    for a, b in SYNC_DIRS.items():
        dst = os.path.join(ROOT, "data", b)
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(os.path.join(GAME_REPO, a), dst, ignore=shutil.ignore_patterns("*.pyc", "__pycache__", "*.import"))
    consts = {}
    for path, name in SYNC_CONSTANTS:
        text = open(os.path.join(GAME_REPO, path)).read()
        m = re.search(r"^const " + name + r"\s*:?=\s*(.+)$", text, re.M)
        if m:
            raw = m.group(1).strip()
            consts[name] = json.loads(raw) if raw[:1] in ('"', "{", "[") else (float(raw) if "." in raw else int(raw))
    # Municion del cajon de equipo: la cantidad la fija _seed_crate (server_world.gd).
    sw = open(os.path.join(GAME_REPO, "server/server_world.gd")).read()
    m = re.search(r'"\$starting_ammo":\s*\n.*?\n\s*quantity = (\d+)', sw)
    if m:
        consts["STARTER_AMMUNITION_CRATE_QUANTITY"] = int(m.group(1))
    with open(os.path.join(ROOT, "data", "rules", "constants.json"), "w") as fh:
        json.dump(consts, fh, indent=1, sort_keys=True)
    icons = os.path.join(GAME_REPO, "docs", "items", "icons")
    for f in glob.glob(os.path.join(icons, "*.png")):
        shutil.copy(f, os.path.join(ROOT, "assets", "img", "icons"))
    print("synced from", GAME_REPO)


def main():
    if "--sync" in sys.argv:
        sync()
        global CLASSES_DATA, ITEMS, NPCS, MATS, FACTIONS
        CLASSES_DATA, ITEMS, NPCS, MATS, FACTIONS = load()
    ATLAS_SIZES.update(AT.write_all())
    builders = {"index": page_index, "story": page_story, "classes": page_classes, "items": page_items,
                "resources": page_resources, "bestiary": page_bestiary, "world": page_world, "manual": page_manual}
    for lang in LANGS:
        os.makedirs(os.path.join(ROOT, lang), exist_ok=True)
        for slug, fn in builders.items():
            with open(os.path.join(ROOT, lang, slug + ".html"), "w") as fh:
                fh.write(fn(lang))
        for old in OLD_PAGES:
            with open(os.path.join(ROOT, lang, old + ".html"), "w") as fh:
                fh.write(redirect_page(lang, old))
    with open(os.path.join(ROOT, "index.html"), "w") as fh:
        fh.write(root_index())
    import wiki as WK
    wiki_pages = WK.build(page)
    print(f"wiki: {wiki_pages} pages per language")
    if WK.GAPS:
        print(f"data gaps ({len(WK.GAPS)}):")
        for g in WK.GAPS:
            print("  -", g)
    print(f"built {len(builders) * len(LANGS)} pages · {len(WEAPONS)} weapons · {len(ITEMS)} items · {len(NPCS)} creatures")


if __name__ == "__main__":
    main()
