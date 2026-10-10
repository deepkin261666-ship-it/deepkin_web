# URLs estables del wiki: salen del id del juego (no del nombre visible, que puede cambiar). Las usan build.py,
# worldmap.py y wiki.py para enlazar entre si (2026-10-10). Todas relativas a la carpeta de idioma (en/, es/).


def tail(content_id):
    return content_id.split(".")[-1].replace("_", "-")


def item(content_id):
    return f"wiki/item-{tail(content_id)}.html"


def mob(content_id):
    return f"wiki/mob-{tail(content_id)}.html"


def person(content_id):
    return f"wiki/npc-{tail(content_id)}.html"


def zone(content_id):
    return f"wiki/zone-{tail(content_id)}.html"


def faction(content_id):
    return f"wiki/faction-{tail(content_id)}.html"


def material(content_id):
    return f"wiki/material-{tail(content_id)}.html"


def quest(content_id):
    return f"wiki/quest-{tail(content_id)}.html"


def district_anchor(district_id):
    return "district-" + tail(district_id)


def skill_anchor(family):
    return "skill-" + tail(family)
