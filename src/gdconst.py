# Lee las constantes ("const NOMBRE := valor") de los .gd del juego copiados por --sync en data/rules/.
# Asi las paginas de mecanicas usan los mismos numeros que el servidor sin copiarlos a mano (2026-10-10).
# Soporta enteros, floats, strings, listas y diccionarios literales; las referencias a otras constantes de clase
# (EquipmentLoadout.SLOT_HEAD, DASH) se resuelven a un string con su nombre ("head", o el valor de DASH si existe).
import ast
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(ROOT, "data", "rules")


def _expr_end(text, start):
    depth = 0
    i = start
    in_str = False
    while i < len(text):
        c = text[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c in "[{(":
            depth += 1
        elif c in "]})":
            depth -= 1
        elif c == "\n" and depth == 0:
            return i
        elif c == "#" and depth == 0:
            return i
        i += 1
    return i


def parse(name):
    path = os.path.join(RULES, name)
    if not os.path.exists(path):
        return {}
    text = open(path).read()
    out = {}
    for m in re.finditer(r"^const ([A-Z_0-9]+)\s*(?::\s*[A-Za-z\[\]]+)?\s*:?=\s*", text, re.M):
        end = _expr_end(text, m.end())
        raw = text[m.end():end].strip()
        # Comentarios dentro de listas/diccionarios multilinea.
        raw = re.sub(r"#[^\n\"]*\n", "\n", raw)
        # Referencias de clase: EquipmentLoadout.SLOT_HEAD -> "head".
        raw = re.sub(r"\b[A-Z][A-Za-z]+\.SLOT_([A-Z_0-9]+)\b", lambda k: '"' + k.group(1).lower() + '"', raw)

        def ref(k):
            v = out.get(k.group(0))
            return repr(v) if isinstance(v, (str, int, float)) else k.group(0)
        raw = re.sub(r"(?<![\"\w.])[A-Z][A-Z_0-9]+(?![\"\w])", ref, raw)
        raw = raw.replace("true", "True").replace("false", "False")
        try:
            out[m.group(1)] = ast.literal_eval(raw)
        except (ValueError, SyntaxError):
            pass
    return out


RPG = parse("rpg_rules.gd")
SKILLS = parse("weapon_skills.gd")
COMBAT = parse("combat_skills.gd")
DEATH = parse("death_penalty.gd")


def total_xp(level):
    """Total de XP para llegar a un nivel (RpgRules.total_xp_for_level)."""
    n, d = RPG.get("XP_CURVE_NUMERATOR", 50), RPG.get("XP_CURVE_DENOMINATOR", 3)
    lv = max(1, level)
    return n * (lv - 1) * (lv * lv - 5 * lv + 12) // d


def xp_to_next(level):
    return total_xp(level + 1) - total_xp(level)


def level_for_xp(xp):
    lo, hi = 1, RPG.get("LEVEL_LIMIT", 65535)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if total_xp(mid) <= xp:
            lo = mid
        else:
            hi = mid - 1
    return lo


def skill_xp_for(level):
    return round(30.0 * (max(1, min(level, SKILLS.get("MAX_LEVEL", 100))) - 1) ** 1.7)


def skill_level_for(xp):
    lv = 1
    while lv < SKILLS.get("MAX_LEVEL", 100) and xp >= skill_xp_for(lv + 1):
        lv += 1
    return lv
