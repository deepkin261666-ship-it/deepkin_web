# Numeros de combate de las armas con las mismas formulas que el servidor (2026-10-24, pase de balance del juego:
# docs/design/WEAPON_BALANCE.md seccion 8). Fuente: CombatSystem.resolve_attack -> RpgRules.outgoing_damage, los rasgos
# en porcentaje de WeaponSkills (Calor, Emboscada, Precision, Supresion, Sobrecarga, Aplastar) y Trailblazer de la Deriva,
# y tools/weapon_balance.gd (golpe de apertura, golpe sostenido, DPS sostenido con veneno). Las constantes salen de
# data/rules/*.gd (build.py --sync); los valores por defecto son los del juego al 2026-10-24.
import math

import gdconst as G

SK, RPG = G.SKILLS, G.RPG
CS = G.parse("combat_system.gd")


def k(name, default, src=None):
    return (src if src is not None else SK).get(name, default)


HEAT_STEP, HEAT_MAX = k("HEAT_PERCENT_PER_STACK", 0.05), k("HEAT_MAX_STACKS", 3)
AMBUSH, AMBUSH_UPTIME = k("AMBUSH_PERCENT", 0.30), k("AMBUSH_EXPECTED_UPTIME", 0.5)
PRECISION, PRECISION_DIST = k("PRECISION_PERCENT", 0.15), k("PRECISION_DISTANCE", 6.0)
SUPPRESS_STEP, SUPPRESS_MAX = k("SUPPRESSION_PERCENT_PER_STACK", 0.05), k("SUPPRESSION_MAX_STACKS", 3)
OVERCHARGE, OVERCHARGE_MIN = k("OVERCHARGE_PERCENT", 0.15), k("OVERCHARGE_MIN_FRACTION", 0.5)
STAGGER_PER_POINT, STAGGER_IMMUNITY = k("STAGGER_SECONDS_PER_POINT", 3.0), k("STAGGER_IMMUNITY", 1.5)
TRAILBLAZER = k("TRAILBLAZER_PERCENT", 0.08, CS)
TRAILBLAZER_WINDOW = k("TRAILBLAZER_WINDOW", 4.0, CS)
XP_PER_ATTACK_SECOND = k("XP_PER_ATTACK_SECOND", 10.0)
TIER_SKILL = k("TIER_SKILL_MINIMUMS", [1, 10, 20, 35, 50, 70])
TIER_LEVEL = RPG.get("GEAR_TIER_MIN_LEVELS", [1, 8, 15, 22, 29, 36])
DEFAULT_INTERVAL = k("PLAYER_ATTACK_COOLDOWN", 0.75, CS)


def roundi(x):
    """roundi de Godot: redondea la mitad hacia afuera (Python round() redondea al par)."""
    return int(math.floor(x + 0.5)) if x >= 0 else -int(math.floor(-x + 0.5))


def stat_mult(v):
    return max(0.75, min(1.25, 1 + (v - 10) * RPG.get("STAT_DAMAGE_STEP", 0.015)))


def damage_factor(skill=1, level=1):
    return 1 + k("DAMAGE_PER_SKILL_LEVEL", 0.01) * (max(skill, 1) - 1) + k("DAMAGE_PER_CHARACTER_LEVEL", 0.006) * (max(level, 1) - 1)


def base(w):
    return w.get("properties", {}).get("base_damage", 0)


def interval(w):
    v = w.get("properties", {}).get("attack_interval", 0)
    return v if v and v > 0 else DEFAULT_INTERVAL


def uses_fuel(w):
    return w.get("weapon_type") == "melee" and w.get("properties", {}).get("fuel_per_attack", 0) > 0


def ammo_of(w, items):
    return items.get(w.get("ammo_item_id") or "")


def ammo_mult(w, items):
    a = ammo_of(w, items)
    return a.get("properties", {}).get("ammo_multiplier", 1.0) if a else 1.0


def poison_dps(w, items):
    a = ammo_of(w, items)
    return a.get("properties", {}).get("poison_per_second", 0) if a else 0


def stagger_seconds(w):
    return w.get("properties", {}).get("stagger_bonus", 0) * STAGGER_PER_POINT if w.get("weapon_type") else 0


def crush(w):
    return w.get("properties", {}).get("armored_damage_bonus", 0) if w.get("weapon_type") else 0


def trait_percent(w, mode):
    """Porcentaje del rasgo de habilidad: "opening" (primer golpe), "sustained" (en regimen) o "expected" (promedio)."""
    fam = w.get("weapon_family")
    if fam == "skill.edge":
        return HEAT_STEP * (HEAT_MAX if mode != "opening" or uses_fuel(w) else 1)
    if fam == "skill.firearms":
        return SUPPRESS_STEP * (SUPPRESS_MAX if mode != "opening" else 1)
    if fam == "skill.precision":
        return PRECISION
    if fam == "skill.tech":
        return OVERCHARGE
    if fam == "skill.blades":
        if mode == "expected":
            return AMBUSH * AMBUSH_UPTIME
        return AMBUSH if mode == "opening" else 0.0
    return 0.0


def hit(c, w, items, bonus=0.0, skill=1, level=1):
    """Un golpe como lo redondea el servidor (RpgRules.outgoing_damage)."""
    wtype = w.get("weapon_type") or "melee"
    attr = {"melee": "might", "ranged": "precision"}.get(wtype, "technology")
    coef = max(0.0, c["combat_coefficients"].get(wtype, 1.0))
    scale = damage_factor(skill, level) * ammo_mult(w, items) * (1 + bonus)
    return max(1, roundi(base(w) * coef * stat_mult(c["attributes"][attr]) * scale))


def row(c, w, items, skill=1, level=1):
    """Golpe de apertura, golpe sostenido y DPS sostenido (tools/weapon_balance.gd row_for)."""
    itv = interval(w)
    tb = TRAILBLAZER if c["id"] == "class.drift" else 0.0
    opening = hit(c, w, items, trait_percent(w, "opening"), skill, level)
    sustained = hit(c, w, items, trait_percent(w, "sustained") + tb, skill, level)
    avg = float(sustained)
    if w.get("weapon_family") == "skill.blades":
        amb = hit(c, w, items, AMBUSH + tb, skill, level)
        plain = hit(c, w, items, tb, skill, level)
        avg = AMBUSH_UPTIME * amb + (1 - AMBUSH_UPTIME) * plain
        sustained = amb
    pz = poison_dps(w, items)
    return {"opening": opening, "sustained": sustained, "dps": avg / itv + pz, "poison": pz, "interval": itv}


def home_class(fam, classes):
    """La clase con mayor afinidad por la familia (empates: orden de ids, como DeepkinClassCatalog.class_ids)."""
    best, aff = None, -1.0
    for c in sorted(classes, key=lambda x: x["id"]):
        a = c.get("skill_affinity", {}).get(fam, k("DEFAULT_AFFINITY", 0.5))
        if a > aff:
            best, aff = c, a
    return best


def tier_requirement(w):
    """(nivel, nivel de habilidad) que pide el arma: el rango abre el nivel, la habilidad lo gana (WeaponSkills 5.5)."""
    tier = max(1, min(int(w.get("gear_tier", 1) or 1), len(TIER_LEVEL)))
    req = w.get("requirements") or {}
    lv = max(TIER_LEVEL[tier - 1], req.get("minimum_level", 1))
    sk = TIER_SKILL[min(tier, len(TIER_SKILL)) - 1] if w.get("weapon_family") else 1
    sk = max(sk, (req.get("minimum_skills") or {}).get(w.get("weapon_family"), 1))
    return lv, sk


def xp_per_second(c, w):
    return XP_PER_ATTACK_SECOND * c.get("skill_affinity", {}).get(w.get("weapon_family"), k("DEFAULT_AFFINITY", 0.5))


def _p(v):
    """Porcentaje entero o con un decimal (0.15 -> "15")."""
    x = round(v * 100, 1)
    return f"{x:g}"


def trait_bits(w, items):
    """Rasgo de la habilidad y especiales del arma: lista de (clave de i18n.TRAITS, parametros)."""
    fam, p = w.get("weapon_family"), w.get("properties", {})
    out = []
    if fam == "skill.edge":
        if uses_fuel(w):
            out.append(("revved", {"c": _p(HEAT_STEP * HEAT_MAX)}))
        else:
            out.append(("heat", {"a": _p(HEAT_STEP), "b": _p(HEAT_STEP * 2), "c": _p(HEAT_STEP * HEAT_MAX)}))
    elif fam == "skill.blades":
        out.append(("ambush", {"p": _p(AMBUSH), "d": f'{k("AMBUSH_DISTANCE", 2.0):g}'}))
        if w.get("weapon_type") == "melee":
            out.append(("executions", {}))
    elif fam == "skill.precision":
        out.append(("precision", {"p": _p(PRECISION), "d": f"{PRECISION_DIST:g}"}))
    elif fam == "skill.firearms":
        out.append(("suppression", {"s": _p(SUPPRESS_STEP), "m": _p(SUPPRESS_STEP * SUPPRESS_MAX)}))
    elif fam == "skill.tech":
        out.append(("overcharge", {"p": _p(OVERCHARGE), "f": _p(OVERCHARGE_MIN)}))
    if stagger_seconds(w):
        out.append(("stagger", {"s": f"{round(stagger_seconds(w), 2):g}"}))
    if crush(w):
        out.append(("crush", {"p": _p(crush(w))}))
    if w.get("weapon_type") == "ranged" and p.get("spread_targets", 0) > 0:
        out.append(("spread", {"n": p["spread_targets"], "a": f'{p.get("spread_half_angle", 15) * 2:g}', "p": _p(p.get("spread_damage", 0))}))
    a = ammo_of(w, items)
    if a:
        ap = a.get("properties", {})
        if ap.get("poison_per_second"):
            out.append(("poison", {"p": ap["poison_per_second"]}))
        if ap.get("ally_heal"):
            out.append(("heals", {"h": ap["ally_heal"]}))
    return out


def trait_text(w, items, lang, traits):
    s = " · ".join(traits[key][lang].format(**kw) for key, kw in trait_bits(w, items))
    return s.replace(".", ",") if lang == "es" and any(ch.isdigit() for ch in s) and "." in s else s
