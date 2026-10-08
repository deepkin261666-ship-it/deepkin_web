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
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from i18n import (ATTR_DESC, ATTRS, CLASSES, DASH, FACTION, FAMILIES, FAMILY_DESC, FOUND_IN, ITEM_EN_FALLBACK,  # noqa: E402
                  ITEM_ES, MATERIAL_NAMES_ES, MOBS, NAV, SLOTS, UI, L)
from story import STORY  # noqa: E402
import texts as TX  # noqa: E402

LANGS = ("en", "es")
GAME_REPO = os.path.join(os.path.dirname(ROOT), "deepkin")

# --- Reglas del juego (copiadas de shared/gameplay/*.gd) -------------------
BASE_HEALTH, HEALTH_PER_END, STAMINA_PER_END = 76, 4, 5
GEAR_TIER_LEVELS = [1, 8, 15, 22, 29, 36]
MAX_LEVEL = 40
POWER_COOLDOWNS = {"ability.bastion": 14, "ability.long_shot": 12, "ability.bloom": 16, "ability.overload": 12}
POWER_MULT = {"ability.long_shot": 2.5, "ability.overload": 3.0}
DASH_COOLDOWN, DASH_COST, POWER_COST = 5, 6, 15
SKILL_MAX = 100


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def stat_mult(v):
    return clamp(1 + (v - 10) * 0.015, 0.75, 1.25)


def class_damage(c, w, ammo=1.0, skill=1, level=1):
    wtype = w.get("weapon_type", "melee")
    attr = "might" if wtype == "melee" else "precision"
    coef = c["combat_coefficients"].get(wtype, 1.0)
    factor = 1 + 0.01 * (skill - 1) + 0.006 * (level - 1)
    return max(1, round(base_damage(w) * coef * stat_mult(c["attributes"][attr]) * ammo * factor))


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
    return 100 + 25 * (level - 1)


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
CLASS_BY_ID = {c["id"]: c for c in CLASSES_DATA}
CLASS_KEY = {"class.foundry": "foundry", "class.drift": "drift", "class.verdant": "verdant", "class.relay": "relay"}
WEAPONS = [i for i in ITEMS.values() if i.get("equipment_slot") == "primary_weapon"]
STARTER_OF = {}
for _c in CLASSES_DATA:
    for _w in _c["starter_weapons"]:
        STARTER_OF.setdefault(_w, []).append(_c["id"])
DOCTRINE_OF = {v["weapon_id"]: (c["id"], v) for c in CLASSES_DATA for v in c["variants"]}


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


# --- Layout ------------------------------------------------------------------
def page(lang, slug, title, body, desc=None, extra_head="", body_class=""):
    other = "es" if lang == "en" else "en"
    nav = ""
    for s, label in NAV:
        cur = ' aria-current="page"' if s == slug else ""
        nav += f'<a href="{s}.html"{cur}>{e(label[lang])}</a>'
    full_title = "DEEPKIN — " + u("what_lies_below", lang) if slug == "index" else f"{title} · DEEPKIN"
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(desc or u('site_desc', lang))}">
<meta property="og:title" content="{e(full_title)}">
<meta property="og:description" content="{e(desc or u('site_desc', lang))}">
<meta property="og:image" content="../assets/img/concept/hero.jpg">
<meta name="theme-color" content="#0b0d0c">
<link rel="alternate" hreflang="{other}" href="../{other}/{slug}.html">
<link rel="icon" href="../assets/img/deepkin_mark.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&family=Newsreader:ital,opsz,wght@0,6..72,300;0,6..72,400;1,6..72,300;1,6..72,400&family=Saira+Condensed:wght@500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../assets/css/site.css">
<script>document.documentElement.classList.add("js")</script>
{extra_head}
</head>
<body class="{body_class}" data-lang="{lang}">
<a class="skip" href="#main">{'Skip to content' if lang == 'en' else 'Saltar al contenido'}</a>
<header class="topbar">
  <a class="brand" href="index.html" aria-label="DEEPKIN"><img src="../assets/img/deepkin_mark.png" alt="" width="22" height="22"><span>DEEPKIN</span></a>
  <nav class="mainnav" id="mainnav">{nav}</nav>
  <a class="lang" href="../{other}/{slug}.html" hreflang="{other}" data-setlang="{other}">{svg('globe')}<span>{u('switch_lang', lang)}</span></a>
  <button class="navtoggle" aria-controls="mainnav" aria-expanded="false" aria-label="Menu">{svg('menu')}</button>
</header>
<div class="depth" aria-hidden="true"><span class="depth-line"><span class="depth-fill"></span></span><span class="depth-val">0000 m</span></div>
<main id="main">
{body}
</main>
<footer class="foot">
  <div class="foot-in">
    <div class="foot-brand"><img src="../assets/img/deepkin_logo.png" alt="DEEPKIN — What lies below" width="220" height="91" loading="lazy"></div>
    <p>{u('footer_note', lang)}</p>
    <nav>{nav}</nav>
    <p class="signal">261.6.66</p>
  </div>
</footer>
<script src="../assets/js/site.js"></script>
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


def wiki(lang, entries, content):
    return f'<div class="wrap wiki">{toc(lang, entries)}<div class="wiki-body">{content}</div></div>'


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
  <img src="../assets/img/concept/class_{k}.jpg" alt="{e(c['name'])}" loading="lazy">
  <div class="ccard-body">
    <p class="ccard-civ">{e(txt['title'][lang])}</p>
    <h3>{e(c['name'])}</h3>
    <p class="ccard-role">{e(txt['role'][lang])}</p>
    <p class="ccard-motto">{e(txt['motto'][lang])}</p>
    <dl class="ccard-stats"><div><dt>{u('hp', lang)}</dt><dd>{dv['health']}</dd></div><div><dt>{u('speed', lang)}</dt><dd>{num(dv['speed'], lang)}</dd></div><div><dt>{u('energy', lang)}</dt><dd>{dv['energy']}</dd></div></dl>
  </div>
</a>"""
    wlist = sorted([w for w in WEAPONS if not w.get("planned") and "provisional" not in w["id"]], key=lambda w: -base_damage(w))[:8]
    weapons = "".join(
        f'<a class="wthumb reveal" href="arsenal.html#{e(w["id"])}">{icon(w["id"], alt=w["display_name"])}<span>{e(w["display_name"])}</span><b>{base_damage(w)}</b></a>'
        for w in wlist)
    route = ""
    for r in TX.REGIONS:
        route += f'<li><a href="world.html#{r["id"]}"><span class="route-n">{r["depth"]}</span><span class="route-name">{e(r["name"])}</span><span class="route-kind">{e(r["kind"][lang])}</span></a></li>'
    gallery_imgs = ["shots/surface_scarp.jpg", "shots/region_b_shallows_keystone.jpg", "shots/class_select_terminal.jpg",
                    "shots/surface_saltpan.jpg", "shots/skill_tree.jpg", "shots/phase13-outpost.jpg"]
    gallery = "".join(f'<figure class="reveal"><img src="../assets/img/{g}" alt="" loading="lazy"></figure>' for g in gallery_imgs)
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
    <a class="btn" href="arsenal.html">{u('open_archive', lang)} {svg('arrow')}</a>
  </div>
  <div class="wthumbs">{weapons}</div>
</section>

<section class="block block-dark">
  <div class="wrap split split-rev">
    <div>
      {section_title('world', '04', 'Every layer hides a history' if lang == 'en' else 'Cada estrato esconde una historia', 'From the Outpost down the shaft, through the Shallows to the dig at C-3 — and up to an open, dangerous sky.' if lang == 'en' else 'Del Outpost por el pozo, a través de The Shallows hasta la excavación C-3… y arriba, a un cielo abierto y peligroso.')}
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
  <a href="arsenal.html#{e(w['id'])}" class="variant-w">{icon(w['id'], alt=w['display_name'])}</a>
  <div><p class="kicker">{u('doctrine', lang)}</p><h4>{e(v['name'])}</h4><p>{e(txt['variants'][v['id']][lang])}</p>
  <p class="variant-meta"><a href="arsenal.html#{e(w['id'])}">{e(w['display_name'])}</a> · {class_damage(c, w)} {u('damage', lang).lower()}</p></div>
</div>"""
    aff = ""
    for fam in sorted(FAMILIES, key=lambda f: -c["skill_affinity"].get(f, 0.5)):
        val = c["skill_affinity"].get(fam, 0.5)
        hot = " hot" if val >= 1.4 else (" cold" if val < 0.9 else "")
        aff += f'<li class="aff{hot}"><span>{e(FAMILIES[fam][lang])}</span>{bar(val, 1.5, col if val >= 1 else "var(--dim)")}<b>×{num(val, lang)}</b></li>'
    starters = "".join(
        f'<a class="mini" href="arsenal.html#{e(wid)}">{icon(wid, alt=ITEMS[wid]["display_name"])}<span>{e(ITEMS[wid]["display_name"])}</span></a>'
        for wid in c["starter_weapons"] if wid in ITEMS)
    power_mult = POWER_MULT.get(power_id)
    return f"""<section class="cls" id="{k}" style="--c:{col}">
  <div class="cls-top">
    <figure class="cls-art"><img src="../assets/img/concept/class_{k}.jpg" alt="{e(c['name'])}" loading="lazy"></figure>
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
  <h3 class="sub">{u('doctrines', lang)}</h3>
  <div class="variants">{variants}</div>
  <div class="cls-grid">
    <div class="panel"><h3>{u('skill_affinity', lang)}</h3><ul class="affs">{aff}</ul></div>
    <div class="panel"><h3>{'Starter weapons' if lang == 'en' else 'Armas iniciales'}</h3><div class="minis">{starters}</div></div>
  </div>
</section>"""


def page_classes(lang):
    entries = [("compare", "Compare" if lang == "en" else "Comparar")] + [(CLASS_KEY[c["id"]], c["name"]) for c in CLASSES_DATA]
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
    sections = "".join(class_section(c, lang) for c in CLASSES_DATA)
    body = wiki_header(lang, "Classes" if lang == "en" else "Clases", "Choose your discipline" if lang == "en" else "Elegí tu disciplina",
                       "Your class sets your body, your power and how fast you learn each weapon. Your gear does the rest." if lang == "en"
                       else "Tu clase define tu cuerpo, tu poder y qué tan rápido aprendés cada arma. Tu equipo hace el resto.",
                       "shots/class_select_terminal.jpg")
    body += wiki(lang, entries, compare + sections)
    return page(lang, "classes", u("meet_classes", lang), body)


def weapon_card(w, lang):
    p = w.get("properties", {})
    dmg, rng, itv = base_damage(w), p.get("attack_range", 0), p.get("attack_interval", 1)
    dps = dmg / itv if itv else 0
    fam = w.get("weapon_family", "")
    wtype = w.get("weapon_type", "melee")
    by_class = ""
    best = max(CLASSES_DATA, key=lambda c: class_damage(c, w))
    mx = max(class_damage(c, w) for c in CLASSES_DATA)
    for c in CLASSES_DATA:
        d = class_damage(c, w)
        by_class += f'<li style="--c:{class_color(c["id"])}"><span>{e(c["name"])}</span>{bar(d, mx * 1.05, class_color(c["id"]))}<b>{d}</b></li>'
    doctrine = ""
    if w["id"] in DOCTRINE_OF:
        cid, v = DOCTRINE_OF[w["id"]]
        doctrine = f'<p class="wc-doc">{class_chip(cid, lang)} {u("doctrine", lang)} · {e(v["name"])}</p>'
    ammo = u("field_round", lang) if w.get("ammo_item_id") else u("none", lang)
    hands = u("two_hand", lang) if w.get("hands") == 2 else u("one_hand", lang)
    dtype = w.get("damage_type")
    dtype_html = f' · <span class="dtype dtype-{dtype}">{e(dtype)}</span>' if dtype else ""
    return f"""<article class="wcard" id="{e(w['id'])}" data-type="{wtype}" data-family="{e(fam)}" data-name="{e(w['display_name'])}"
  data-damage="{dmg}" data-dps="{dps:.2f}" data-range="{rng}" data-speed="{itv}" data-weight="{w.get('weight', 0)}">
  <div class="wc-icon">{icon(w['id'], alt=w['display_name'])}</div>
  <div class="wc-main">
    <p class="kicker">{e(u(wtype, lang))} · {e(FAMILIES.get(fam, {}).get(lang, fam))}{dtype_html} {status_tag(w, lang)}</p>
    <h3>{e(w['display_name'])}</h3>
    <p class="wc-desc">{e(item_desc(w, lang))}</p>
    {doctrine}
  </div>
  <dl class="wc-stats">
    <div><dt>{u('damage', lang)}</dt><dd>{dmg}</dd></div>
    <div><dt>{u('dps', lang)}</dt><dd>{num(dps, lang, 1)}</dd></div>
    <div><dt>{u('range', lang)}</dt><dd>{num(rng, lang)}<small>m</small></dd></div>
    <div><dt>{u('interval', lang)}</dt><dd>{num(itv, lang)}<small>s</small></dd></div>
    <div><dt>{u('hands', lang)}</dt><dd class="sm">{e(hands)}</dd></div>
    <div><dt>{u('weight', lang)}</dt><dd>{num(w.get('weight', 0), lang)}<small>kg</small></dd></div>
    <div><dt>{u('ammo', lang)}</dt><dd class="sm">{e(ammo)}</dd></div>
    <div><dt>{u('tier', lang)}</dt><dd>T{w.get('gear_tier', 1)}</dd></div>
  </dl>
  <details class="wc-class"><summary>{u('damage_by_class', lang)} · <span>{u('best_with', lang)} {e(best['name'])}</span></summary><ul class="byclass">{by_class}</ul></details>
</article>"""


def page_arsenal(lang):
    ws = sorted(WEAPONS, key=lambda w: (w.get("weapon_type") != "melee", -base_damage(w)))
    fams = sorted({w.get("weapon_family") for w in ws}, key=lambda f: list(FAMILIES).index(f))
    chips = f'<button class="fchip" aria-pressed="true" data-filter="all">{u("all", lang)}</button>'
    chips += f'<button class="fchip" aria-pressed="false" data-filter="type:melee">{u("melee", lang)}</button>'
    chips += f'<button class="fchip" aria-pressed="false" data-filter="type:ranged">{u("ranged", lang)}</button><span class="fsep"></span>'
    chips += "".join(f'<button class="fchip" aria-pressed="false" data-filter="family:{f}">{e(FAMILIES[f][lang])}</button>' for f in fams)
    sorts = "".join(f'<option value="{k}">{e(lbl)}</option>' for k, lbl in [
        ("default", "—"), ("damage", u("damage", lang)), ("dps", u("dps", lang)), ("range", u("range", lang)),
        ("speed", u("interval", lang)), ("weight", u("weight", lang)), ("name", u("name", lang))])
    cards = "".join(weapon_card(w, lang) for w in ws)
    rows = ""
    for w in ws:
        p = w.get("properties", {})
        itv = p.get("attack_interval", 1)
        rows += (f'<tr data-type="{w.get("weapon_type")}" data-family="{e(w.get("weapon_family", ""))}"><td class="tn">{icon(w["id"], "ticon", w["display_name"])}<a href="#{e(w["id"])}">{e(w["display_name"])}</a></td>'
                 f'<td>{e(u(w.get("weapon_type", "melee"), lang))}</td><td>{e(FAMILIES[w["weapon_family"]][lang])}</td>'
                 f'<td class="n">{base_damage(w)}</td><td class="n">{num(base_damage(w) / itv, lang, 1)}</td><td class="n">{num(p.get("attack_range", 0), lang)}</td>'
                 f'<td class="n">{num(itv, lang)}</td><td>{w.get("hands", 1)}</td><td class="n">{num(w.get("weight", 0), lang)}</td></tr>')
    table = f"""<div class="tablewrap"><table class="data sortable" id="wtable"><thead><tr>
<th data-sort="text">{u('weapon', lang)}</th><th data-sort="text">{'Type' if lang == 'en' else 'Tipo'}</th><th data-sort="text">{u('family', lang)}</th>
<th data-sort="num">{u('damage', lang)}</th><th data-sort="num">{u('dps', lang)}</th><th data-sort="num">{u('range', lang)} (m)</th>
<th data-sort="num">{u('interval', lang)} (s)</th><th data-sort="num">{u('hands', lang)}</th><th data-sort="num">{u('weight', lang)} (kg)</th></tr></thead><tbody>{rows}</tbody></table></div>"""

    off = [i for i in ITEMS.values() if i.get("equipment_slot") == "secondary_weapon"]
    off_html = "".join(gear_card(i, lang) for i in off)
    ammo = [i for i in ITEMS.values() if i["id"].startswith("item.ammunition")]
    ammo_html = ""
    for a in ammo:
        pr = a["properties"]
        ammo_html += f"""<article class="gcard">{icon(a['id'], alt=a['display_name'])}<div><p class="kicker">{u('ammo', lang)} {status_tag(a, lang)}</p><h3>{e(a['display_name'])}</h3><p>{e(item_desc(a, lang))}</p>
<dl class="kv"><div><dt>{u('damage', lang)}</dt><dd>×{num(pr['ammo_multiplier'], lang)}</dd></div><div><dt>{u('stack', lang)}</dt><dd>{pr['stack_size']}</dd></div><div><dt>{u('weight', lang)}</dt><dd>{num(a['weight'], lang)} kg</dd></div></dl></div></article>"""

    calc_data = {
        "classes": [{"id": c["id"], "name": c["name"], "color": class_color(c["id"]), "attributes": c["attributes"],
                     "coef": c["combat_coefficients"], "power": c["ability_name"], "powerMult": POWER_MULT.get(c["ability_id"], 1)}
                    for c in CLASSES_DATA],
        "weapons": [{"id": w["id"], "name": w["display_name"], "type": w.get("weapon_type"), "base": base_damage(w),
                     "interval": w["properties"].get("attack_interval", 1), "ammo": bool(w.get("ammo_item_id")),
                     "family": FAMILIES[w["weapon_family"]][lang]} for w in ws],
        "ammo": [{"name": a["display_name"], "mult": a["properties"]["ammo_multiplier"]} for a in ammo],
        "lang": lang,
        "attrNames": {a: ATTRS[a][lang] for a in ATTRS},
    }
    cls_opts = "".join(f'<option value="{c["id"]}">{e(c["name"])}</option>' for c in CLASSES_DATA)
    w_opts = "".join(f'<option value="{w["id"]}">{e(w["display_name"])}</option>' for w in ws)
    ammo_opts = "".join(f'<option value="{a["properties"]["ammo_multiplier"]}">{e(a["display_name"])}</option>' for a in ammo)
    calc = f"""{section_title('calculator', 'Tool' if lang == 'en' else 'Herramienta', u('calc_title', lang), u('calc_lead', lang))}
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

    entries = [("weapons", u("weapon", lang) + ("s" if lang == "en" else "s")), ("compare-table", u("table", lang)),
               ("offhand", SLOTS["secondary_weapon"][lang]), ("ammunition", u("ammo", lang)), ("calculator", u("calc_title", lang))]
    content = f"""{section_title('weapons', 'Primary weapons' if lang == 'en' else 'Armas principales', 'Weapons' if lang == 'en' else 'Armas',
                    'Base numbers before class scaling. Open “damage by class” on any card to see what each discipline actually deals.' if lang == 'en'
                    else 'Números base antes de la escala de clase. Abrí «daño por clase» en cualquier ficha para ver cuánto hace cada disciplina.')}
<div class="filters" data-target="#wgrid">
  <div class="fchips">{chips}</div>
  <label class="fsort">{u('sort_by', lang)} <select data-sort-select>{sorts}</select></label>
</div>
<div class="wgrid" id="wgrid">{cards}</div>
{section_title('compare-table', u('table', lang), 'Side by side' if lang == 'en' else 'Lado a lado', 'Click a column to sort.' if lang == 'en' else 'Hacé clic en una columna para ordenar.')}
{table}
{section_title('offhand', SLOTS['secondary_weapon'][lang], 'Shields' if lang == 'en' else 'Escudos', 'Off-hand gear pairs with any one-handed weapon. Blocking hits trains Shielding.' if lang == 'en' else 'El equipo de mano secundaria combina con cualquier arma de una mano. Bloquear golpes entrena Escudos.')}
<div class="ggrid">{off_html}</div>
{section_title('ammunition', u('ammo', lang), 'Rounds' if lang == 'en' else 'Munición', 'Every ranged weapon fires the first ammunition stack in your cargo.' if lang == 'en' else 'Toda arma a distancia dispara la primera pila de munición de tu inventario.')}
<div class="ggrid">{ammo_html}</div>
{calc}"""
    body = wiki_header(lang, "Arsenal", "Weapons of the deep" if lang == "en" else "Armas de las profundidades",
                       "Every weapon in the current build, with real numbers. No class locks: carry what fits your fight." if lang == "en"
                       else "Todas las armas de la versión actual, con números reales. Sin bloqueos de clase: llevá lo que sirva para tu pelea.",
                       "shots/phase13_10-armory.jpg")
    body += wiki(lang, entries, content)
    return page(lang, "arsenal", "Arsenal", body)


def gear_card(i, lang):
    p = i.get("properties", {})
    kv = []
    if "armor_defense" in p and i.get("equipment_slot") not in ("light", "battery", "backpack"):
        kv.append((u("armor", lang), f'+{p["armor_defense"]}'))
    if p.get("resistance_bonus") is not None and i.get("equipment_slot") not in ("light", "battery", "backpack"):
        kv.append((u("resistance", lang), f'+{p.get("resistance_bonus", 0)}'))
    if p.get("illumination_radius"):
        kv.append((u("light_radius", lang), f'{num(p["illumination_radius"], lang)} m'))
    if p.get("light_energy_per_second"):
        kv.append((u("drain", lang), f'{num(p["light_energy_per_second"], lang)}/s'))
        mins = 100 / p["light_energy_per_second"] / 60
        kv.append((u("runtime", lang), f'≈ {num(mins, lang, 1)} min'))
    if p.get("battery_capacity"):
        kv.append((u("capacity", lang), f'{p["battery_capacity"]} {u("energy", lang).lower()}'))
    if i.get("container"):
        kv.append((u("capacity", lang), f'{i["container"]["cells"]} {u("cells", lang)}'))
    if p.get("carry_bonus"):
        kv.append((u("carry", lang), f'+{num(p["carry_bonus"], lang)} kg'))
    if p.get("drill_power"):
        kv.append(("Drill power" if lang == "en" else "Potencia", f'×{num(p["drill_power"], lang)}'))
    if i.get("hands"):
        kv.append((u("hands", lang), str(i["hands"])))
    if i.get("weight"):
        kv.append((u("weight", lang), f'{num(i["weight"], lang)} kg'))
    if i.get("gear_tier"):
        kv.append((u("tier", lang), f'T{i["gear_tier"]}'))
    req = i.get("requirements")
    if req:
        kv.append((u("requires", lang), f'{u("level", lang)} {req.get("minimum_level", 1)}'))
    kv_html = "".join(f"<div><dt>{e(a)}</dt><dd>{e(b)}</dd></div>" for a, b in kv)
    slot = SLOTS.get(i.get("equipment_slot"), {}).get(lang, "")
    contents = ""
    if i.get("crate_loot"):
        lis = ""
        for cid in i["crate_loot"]:
            if cid.startswith("$"):
                label = ("Your doctrine's weapon" if lang == "en" else "El arma de tu doctrina") if cid == "$doctrine_weapon" else (
                    "Ammunition (if it shoots)" if lang == "en" else "Munición (si dispara)")
                lis += f'<li class="mini"><span class="mini-ph">?</span><span>{e(label)}</span></li>'
            elif cid in ITEMS:
                lis += f'<li class="mini">{icon(cid, alt=ITEMS[cid]["display_name"])}<span>{e(ITEMS[cid]["display_name"])}</span></li>'
        contents = f'<p class="kicker">{u("contents", lang)}</p><ul class="minis">{lis}</ul>'
    return f"""<article class="gcard{' soon' if i.get('planned') else ''}" id="{e(i['id'])}">{icon(i['id'], alt=i['display_name']) if os.path.exists(os.path.join(ROOT, 'assets/img/icons', i['id'] + '.png')) else '<span class="icon icon-ph"></span>'}
<div><p class="kicker">{e(slot)} {status_tag(i, lang)}</p><h3>{e(i['display_name'])}</h3><p>{e(item_desc(i, lang))}</p><dl class="kv">{kv_html}</dl>{contents}</div></article>"""


def page_gear(lang):
    groups = [
        ("armor", "Armor" if lang == "en" else "Armadura",
         "Head, chest, legs and boots are equipped separately. Armor reduces physical damage, resistance reduces everything else." if lang == "en"
         else "Cabeza, torso, piernas y botas se equipan por separado. La armadura reduce el daño físico; la resistencia, todo lo demás.",
         lambda i: i.get("equipment_slot") in ("head", "chest", "legs", "boots")),
        ("lights", "Lights" if lang == "en" else "Luces",
         "Your light is the difference between reading a cavern and guessing it. Brighter lights drain your battery faster." if lang == "en"
         else "Tu luz es la diferencia entre leer una caverna y adivinarla. Las luces más potentes vacían la batería más rápido.",
         lambda i: i.get("equipment_slot") == "light"),
        ("power", "Power & carry" if lang == "en" else "Energía y carga",
         "The battery feeds your light and abilities. Nothing recharges it on an expedition." if lang == "en"
         else "La batería alimenta tu luz y tus habilidades. Nada la recarga durante una expedición.",
         lambda i: i.get("equipment_slot") in ("battery", "backpack")),
        ("tools", "Tools" if lang == "en" else "Herramientas",
         "The drill goes in the tool slot. Hold F at a drill site." if lang == "en" else "El taladro va en la ranura de herramienta. Mantené F en un punto de perforación.",
         lambda i: i.get("equipment_slot") == "tool_special"),
        ("crates", "Newcomer crates" if lang == "en" else "Cajones de recién llegado",
         "Every new operator takes their first kit from two personal crates in the Outpost." if lang == "en"
         else "Todo operador nuevo toma su primer equipo de dos cajones personales en el Outpost.",
         lambda i: i["id"].startswith("item.container")),
    ]
    slot_order = {"head": 0, "chest": 1, "legs": 2, "boots": 3}
    content = ""
    entries = []
    for anchor, title, lead, pred in groups:
        its = sorted([i for i in ITEMS.values() if pred(i)],
                     key=lambda i: (bool(i.get("planned")), slot_order.get(i.get("equipment_slot"), 9), i["display_name"]))
        entries.append((anchor, title))
        content += section_title(anchor, ("Gear" if lang == "en" else "Equipo"), title, lead)
        content += f'<div class="ggrid">{"".join(gear_card(i, lang) for i in its)}</div>'
    slots = ["head", "chest", "legs", "boots", "primary_weapon", "secondary_weapon", "tool_special", "backpack", "battery", "light"]
    slot_html = "".join(f"<li>{e(SLOTS[s][lang])}</li>" for s in slots)
    intro = f"""<div class="panel slots"><h3>{'Your loadout' if lang == 'en' else 'Tu equipo'}</h3>
<p>{'Ten slots you fill from the inventory (I), plus two modification slots that are coming later. Your class never locks gear: only level and attribute requirements do.' if lang == 'en'
     else 'Diez ranuras que llenás desde el inventario (I), más dos de modificación que llegan después. Tu clase nunca bloquea equipo: sólo el nivel y los requisitos de atributos.'}</p>
<ul class="slotlist">{slot_html}</ul></div>"""
    body = wiki_header(lang, "Gear" if lang == "en" else "Equipo", "Armor, light & tools" if lang == "en" else "Armadura, luz y herramientas",
                       "Everything you wear and carry below. Civilization + Weapon + Armor + Battery + Light = Build." if lang == "en"
                       else "Todo lo que vestís y llevás abajo. Civilización + Arma + Armadura + Batería + Luz = Build.",
                       "shots/inventory_loadout.jpg")
    body += wiki(lang, [("slots", "Loadout" if lang == "en" else "Equipo")] + entries, f'<div id="slots">{intro}</div>' + content)
    return page(lang, "gear", "Gear" if lang == "en" else "Equipo", body)


def page_resources(lang):
    ores = [i for i in ITEMS.values() if i["id"].startswith(("item.ore", "item.mineral"))]
    loot = [ITEMS[k] for k in ("item.ferrous_sample", "item.relic_fragment", "item.scrap_component") if k in ITEMS]
    cur = sorted([i for i in ITEMS.values() if i["id"].startswith("item.currency")], key=lambda i: i["properties"]["currency_value"])

    def rcard(i):
        found = FOUND_IN.get(i["id"])
        f = f'<p class="found"><span>{u("found_in", lang)}</span>{e(found[lang])}</p>' if found else ""
        return (f'<article class="gcard" id="{e(i["id"])}">{icon(i["id"], alt=i["display_name"])}<div><p class="kicker">{status_tag(i, lang)}</p>'
                f'<h3>{e(i["display_name"])}</h3><p>{e(item_desc(i, lang))}</p>{f}</div></article>')

    coins = ""
    for i in cur:
        coins += (f'<article class="coin">{icon(i["id"], alt=i["display_name"])}<h3>{e(i["display_name"])}</h3>'
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
               + section_title("currency", u("planned", lang), "Currency" if lang == "en" else "Moneda",
                               "Three coins, one stamp. Trading is coming; here is what you will be counting." if lang == "en"
                               else "Tres monedas, un sello. El comercio está en camino; esto es lo que vas a contar.")
               + f'<div class="coins">{coins}</div>')
    entries = [("ores", "Ores" if lang == "en" else "Minerales"), ("finds", "Finds" if lang == "en" else "Hallazgos"),
               ("rock", "Geology" if lang == "en" else "Geología"), ("currency", "Currency" if lang == "en" else "Moneda")]
    body = wiki_header(lang, "Resources" if lang == "en" else "Recursos", "Everything we need comes from below" if lang == "en" else "Todo lo que necesitamos viene de abajo",
                       "Ore, crystal, salvage and coin: what you dig, find and carry home." if lang == "en"
                       else "Mineral, cristal, chatarra y moneda: lo que excavás, encontrás y llevás a casa.",
                       "shots/region_h_deposit_cracked.jpg")
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
            abil += (f'<div class="mob-ab"><p class="kicker">{"Telegraphed attack" if lang == "en" else "Ataque anunciado"}</p><h4>{e(a["name"])}</h4>'
                     f'<p>{a["damage"]} {u("damage", lang).lower()} · {"radius" if lang == "en" else "radio"} {num(a["radius"], lang)} m · '
                     f'{"wind-up" if lang == "en" else "carga"} {num(a["windup"], lang)} s · {u("cooldown", lang).lower()} {num(a["cooldown"], lang)} s</p></div>')
        faction = "Burrowborn" if n.get("faction") == "faction.burrowborn" else M.get("faction", L("", ""))[lang]
        has_icon = os.path.exists(os.path.join(ROOT, "assets/img/icons", n["id"] + ".png"))
        art = icon(n["id"], "mob-img", n["display_name"]) if has_icon else f'<span class="mob-img mob-ph">{e(n["display_name"][0])}</span>'
        threat = n.get("threat")
        threat_html = f'<div><dt>{u("threat", lang)}</dt><dd>{"◆" * min(5, max(1, round(threat / 2)))}<small>{threat}</small></dd></div>' if threat else ""
        xp_html = f'<div><dt>{u("xp", lang)}</dt><dd>{n["xp"]}</dd></div>' if n.get("xp") else ""
        return f"""<article class="mob" id="{e(n['id'])}">
  <div class="mob-art">{art}<div class="verbs">{verbs}</div></div>
  <div class="mob-main">
    <p class="kicker">{e(faction)} · {e(M['role'][lang])}</p>
    <h3>{e(n['display_name'])}</h3>
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
  </div>
</article>"""

    order = ["npc.burrowborn_crawler", "npc.burrowborn_ravager", "npc.scavenger", "npc.excavation_enforcer"]
    by_id = {n["id"]: n for n in NPCS}
    burrow = "".join(mob(by_id[i]) for i in order[:2] if i in by_id)
    human = "".join(mob(by_id[i]) for i in order[2:] if i in by_id)
    rumours = ""
    for fid in ("faction.rustbound", "faction.architects", "faction.hollow"):
        f = fac[fid]
        rumours += (f'<article class="rumour"><p class="kicker">{e(FACTION[fid]["identity"][lang])}</p><h3>{e(f["name"])}</h3>'
                    f'<p>{e(FACTION[fid]["rumour"][lang])}</p><span class="tag tag-soon">{u("planned", lang)}</span></article>')
    content = (faction_html + f'<div class="mobs">{burrow}</div>'
               + section_title("humans", "Faction" if lang == "en" else "Facción", "People" if lang == "en" else "Gente",
                               "Not everything down here is an animal." if lang == "en" else "No todo lo que hay acá abajo es un animal.")
               + f'<div class="mobs">{human}</div>'
               + section_title("rumours", "Field reports" if lang == "en" else "Informes de campo", "Rumours from below" if lang == "en" else "Rumores de abajo",
                               "Operators come back with stories. Some of them are true." if lang == "en" else "Los operadores vuelven con historias. Algunas son ciertas.")
               + f'<div class="rumours">{rumours}</div>')
    entries = [("burrowborn", "Burrowborn"), ("humans", "People" if lang == "en" else "Gente"), ("rumours", "Rumours" if lang == "en" else "Rumores")]
    body = wiki_header(lang, "Bestiary" if lang == "en" else "Bestiario", "What hunts below" if lang == "en" else "Lo que caza abajo",
                       "Know what you are fighting before it knows you are there." if lang == "en" else "Conocé contra qué peleás antes de que sepa que estás ahí.",
                       "concept/tile_wilds.jpg")
    body += wiki(lang, entries, content)
    return page(lang, "bestiary", "Bestiary" if lang == "en" else "Bestiario", body)


def page_world(lang):
    route = ""
    for r in TX.REGIONS:
        pts = "".join(f"<li>{e(p)}</li>" for p in r["points"][lang])
        route += f"""<article class="region" id="{r['id']}">
  <figure><img src="../assets/img/{r['img']}" alt="{e(r['name'])}" loading="lazy"></figure>
  <div class="region-body">
    <p class="kicker"><span class="stratum">{r['depth']}</span>{e(r['kind'][lang])}</p>
    <h3>{e(r['name'])}</h3>
    <p class="region-lead">{e(r['lead'][lang])}</p>
    <p>{e(r['body'][lang])}</p>
    <ul class="points">{pts}</ul>
  </div>
</article>"""
    surface = ""
    for r in TX.SURFACE:
        surface += f"""<article class="region region-wide" id="{r['id']}">
  <figure><img src="../assets/img/{r['img']}" alt="{e(r['name'])}" loading="lazy"></figure>
  <div class="region-body"><p class="kicker">{e(r['kind'][lang])}</p><h3>{e(r['name'])}</h3><p class="region-lead">{e(r['lead'][lang])}</p><p>{e(r['body'][lang])}</p></div>
</article>"""
    tiles = "".join(f'<figure class="tile"><img src="../assets/img/concept/{img}.jpg" alt="" loading="lazy"><figcaption><b>{e(n[lang])}</b><span>{e(d[lang])}</span></figcaption></figure>'
                    for img, n, d in TX.CONCEPT_REGIONS)
    cities = ""
    for cid, (city, line) in STORY[lang]["cities"].items():
        cities += (f'<a class="city" href="classes.html#{CLASS_KEY[cid]}" style="--c:{class_color(cid)}"><span class="city-name">{e(city)}</span>'
                   f'<span class="city-civ">{e(CLASS_BY_ID[cid]["name"])} · {e(CLASSES[cid]["title"][lang])}</span><span class="city-line">{e(line)}</span></a>')
    machines = "".join(f'<figure class="machine" style="--c:{class_color(cid)}"><img src="../assets/img/concept/{img}.jpg" alt="{n}" loading="lazy"><figcaption><b>{n}</b><span>{e(CLASS_BY_ID[cid]["name"])} · {e(d[lang])}</span></figcaption></figure>'
                       for img, n, cid, d in TX.MACHINES)
    content = (section_title("route", "The way down" if lang == "en" else "El camino hacia abajo", "The starting region" if lang == "en" else "La región inicial",
                             "The Outpost → shaft lift → The Threshold → The Shallows → Excavation C-3.")
               + f'<div class="regions">{route}</div>'
               + section_title("surface", "Open sky" if lang == "en" else "Cielo abierto", "The surface" if lang == "en" else "La superficie",
                               "The surface was never completely abandoned. A shaft on The Scarp drops straight to The Threshold." if lang == "en"
                               else "La superficie nunca fue completamente abandonada. Un pozo en The Scarp baja directo a The Threshold.")
               + f'<div class="regions">{surface}</div>'
               + section_title("civilisations", "Beyond the region" if lang == "en" else "Más allá de la región", "The four cities" if lang == "en" else "Las cuatro ciudades",
                               "Home of each civilisation. You will hear of them long before you reach them." if lang == "en" else "El hogar de cada civilización. Vas a oír de ellas mucho antes de llegar.")
               + f'<div class="cities">{cities}</div>'
               + section_title("regions", "The wider world" if lang == "en" else "El mundo", "Five kinds of place" if lang == "en" else "Cinco tipos de lugar")
               + f'<div class="tiles">{tiles}</div>'
               + section_title("machines", u("planned", lang), "Excavators" if lang == "en" else "Excavadoras",
                               "One day the drill becomes a machine you ride: your mount, your cargo and your way through the hardest rock." if lang == "en"
                               else "Algún día el taladro será una máquina que manejás: tu montura, tu carga y tu camino a través de la roca más dura.")
               + f'<div class="machines">{machines}</div>')
    entries = [("route", "Starting region" if lang == "en" else "Región inicial"), ("surface", "Surface" if lang == "en" else "Superficie"),
               ("civilisations", "Cities" if lang == "en" else "Ciudades"), ("regions", "The wider world" if lang == "en" else "El mundo"),
               ("machines", "Excavators" if lang == "en" else "Excavadoras")]
    body = wiki_header(lang, "World" if lang == "en" else "Mundo", "Every layer hides a history" if lang == "en" else "Cada estrato esconde una historia",
                       "Depth is not the only danger. A shallow flooded tunnel can be worse than a deep, dry cavern." if lang == "en"
                       else "La profundidad no es el único peligro. Un túnel inundado poco profundo puede ser peor que una caverna profunda y seca.",
                       "concept/city.jpg")
    body += wiki(lang, entries, content)
    return page(lang, "world", "World" if lang == "en" else "Mundo", body)


def page_manual(lang):
    steps = "".join(f'<li><h3>{e(a[lang])}</h3><p>{e(b[lang])}</p></li>' for a, b in TX.FIRST_STEPS)
    keys = "".join(f'<div class="kb"><kbd>{e(k)}</kbd><span>{e(d[lang])}</span></div>' for k, d in TX.CONTROLS)
    tiers = "".join(f'<div class="tierc"><b>T{i + 1}</b><span>{u("level", lang)} {lv}+</span></div>' for i, lv in enumerate(GEAR_TIER_LEVELS))
    total = sum(xp_to_next(level) for level in range(1, MAX_LEVEL))
    xp_rows = "".join(f'<tr><td>{lv}</td><td class="n">{num(xp_to_next(lv), lang)}</td><td class="n">{num(sum(xp_to_next(x) for x in range(1, lv + 1)), lang)}</td></tr>'
                      for lv in (1, 2, 5, 10, 15, 20, 25, 30, 35, 39))
    skill_rows = "".join(f'<tr><td>{lv}</td><td class="n">{num(skill_xp_for(lv), lang)}</td><td class="n">{num(skill_xp_for(lv) / 10, lang, 0)}</td><td class="n">+{lv - 1}%</td></tr>'
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
    <p class="eq">{'weapon base × class coefficient × attribute bonus × skill bonus × ammo' if en else 'base del arma × coeficiente de clase × bono de atributo × bono de habilidad × munición'}</p>
    <p>{'Each class has a melee, ranged, ability and defense coefficient. Foundry swings at ×1.2 but shoots at ×0.6; Drift is the reverse.' if en
        else 'Cada clase tiene un coeficiente cuerpo a cuerpo, a distancia, de habilidad y de defensa. La Forja golpea a ×1,2 pero dispara a ×0,6; La Deriva, al revés.'}</p>
    <a class="textlink" href="arsenal.html#calculator">{u('calc_title', lang)} {svg('arrow')}</a>
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
    <p>{'10 skill XP per hit, 8 per hit blocked with a shield. Your class affinity multiplies it (×1.5 for its specialties, ×0.5 for families it has no feel for). Each skill level adds +1% damage with that family, up to level 100.' if en
        else '10 XP de habilidad por golpe, 8 por golpe bloqueado con escudo. La afinidad de tu clase lo multiplica (×1,5 en sus especialidades, ×0,5 en las familias que no domina). Cada nivel suma +1% de daño con esa familia, hasta el nivel 100.'}</p>
    <div class="tablewrap"><table class="data compact"><thead><tr><th>{'Skill' if en else 'Nivel'}</th><th>{'Total XP' if en else 'XP total'}</th><th>{'Hits (×1)' if en else 'Golpes (×1)'}</th><th>{u('damage', lang)}</th></tr></thead><tbody>{skill_rows}</tbody></table></div>
    <p class="note">{'Shielding: 8% damage reduction with a shield, +0.2% per level, up to 40%.' if en else 'Escudos: 8% de reducción con escudo, +0,2% por nivel, hasta 40%.'}</p>
  </div>
</div>

{section_title('levels', 'Progression' if en else 'Progresión', 'Levels & gear tiers' if en else 'Niveles y rangos de equipo',
               'Character level caps at 40. Creatures award XP when they fall; each level adds +0.6% to all your damage and unlocks better gear tiers.' if en
               else 'El nivel de personaje llega hasta 40. Las criaturas dan XP al caer; cada nivel suma +0,6% a todo tu daño y desbloquea mejores rangos de equipo.')}
<div class="tiers">{tiers}</div>
<div class="cls-grid">
  <div class="tablewrap"><table class="data compact"><thead><tr><th>{u('level', lang)}</th><th>{'XP to next' if en else 'XP al siguiente'}</th><th>{'Total' if en else 'Total'}</th></tr></thead><tbody>{xp_rows}</tbody></table></div>
  <div class="panel"><p class="eq">{'XP to next level = 100 + 25 × (level − 1)' if en else 'XP al siguiente nivel = 100 + 25 × (nivel − 1)'}</p>
  <p>{f'Level 40 takes {num(total, lang)} XP in total. A Crawler is worth 14, a Ravager 80.' if en else f'El nivel 40 requiere {num(total, lang)} XP en total. Un Crawler vale 14; un Ravager, 80.'}</p>
  <p>{'Gear can also ask for a minimum level or attribute. The class never locks an item.' if en else 'El equipo también puede pedir un nivel o atributo mínimo. La clase nunca bloquea un objeto.'}</p></div>
</div>

{section_title('light', 'Survival' if en else 'Supervivencia', 'Light & energy' if en else 'Luz y energía')}
<div class="cls-grid">
  <div class="panel"><p>{'Your battery sets your energy. The lantern drains it every second it is on, and abilities spend it too. There is no recharging on an expedition: when it hits zero, the light goes out.' if en
      else 'Tu batería define tu energía. La linterna la consume cada segundo que está encendida, y las habilidades también gastan. No hay recarga durante una expedición: cuando llega a cero, la luz se apaga.'}</p>
      <p>{'Toggle the lantern with T. Unequipping the battery empties your energy; equipping it again does not refill it.' if en else 'Prendé o apagá la linterna con T. Quitar la batería vacía tu energía; volver a equiparla no la recarga.'}</p></div>
  <div class="panel"><p class="eq">{'Simple Lantern: 9 m radius · 0.15/s · ≈ 11 min on Battery Cell I' if en else 'Simple Lantern: radio 9 m · 0,15/s · ≈ 11 min con Battery Cell I'}</p>
      <a class="textlink" href="gear.html#lights">{'Compare lights' if en else 'Comparar luces'} {svg('arrow')}</a></div>
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
<meta name="viewport" content="width=device-width, initial-scale=1">
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


def sync():
    src = os.path.join(GAME_REPO, "data", "entities")
    for sub in ("classes", "items", "npcs", "materials", "factions"):
        dst = os.path.join(ROOT, "data", sub)
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(os.path.join(src, sub), dst)
    icons = os.path.join(GAME_REPO, "docs", "items", "icons")
    for f in glob.glob(os.path.join(icons, "*.png")):
        shutil.copy(f, os.path.join(ROOT, "assets", "img", "icons"))
    print("synced from", GAME_REPO)


def main():
    if "--sync" in sys.argv:
        sync()
        global CLASSES_DATA, ITEMS, NPCS, MATS, FACTIONS
        CLASSES_DATA, ITEMS, NPCS, MATS, FACTIONS = load()
    builders = {"index": page_index, "story": page_story, "classes": page_classes, "arsenal": page_arsenal, "gear": page_gear,
                "resources": page_resources, "bestiary": page_bestiary, "world": page_world, "manual": page_manual}
    for lang in LANGS:
        os.makedirs(os.path.join(ROOT, lang), exist_ok=True)
        for slug, fn in builders.items():
            with open(os.path.join(ROOT, lang, slug + ".html"), "w") as fh:
                fh.write(fn(lang))
    with open(os.path.join(ROOT, "index.html"), "w") as fh:
        fh.write(root_index())
    print(f"built {len(builders) * len(LANGS)} pages · {len(WEAPONS)} weapons · {len(ITEMS)} items · {len(NPCS)} creatures")


if __name__ == "__main__":
    main()
