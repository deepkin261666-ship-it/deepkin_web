# DEEPKIN — Field Archive (web)

Player-facing wiki and showcase for DEEPKIN, in English (`en/`) and Spanish (`es/`).
Static HTML/CSS/JS: no build tools, no dependencies beyond Python 3 for generation.

## Pages

Home · Story · Classes · Arsenal · Gear · Resources · Bestiary · World · Field Manual

## Generate

```bash
python3 build.py          # rebuild en/, es/ and index.html from data/ + src/
python3 build.py --sync   # first copy fresh game data + icons from ../deepkin
```

- `data/` — snapshot of `deepkin/data/entities` (classes, items, npcs, materials, factions). Retired items are skipped; `planned` items show as *Coming soon*.
- `src/i18n.py` — UI strings, class/creature copy and Spanish item descriptions.
- `src/story.py` — the story (Spanish original from `DEEPKIN_Historia_ES.html`, plus English translation).
- `src/texts.py` — world regions, controls, first steps, home page copy.
- `build.py` — derived stats use the same formulas as the game server (`shared/gameplay/rpg_rules.gd`, `weapon_skills.gd`, `combat_skills.gd`). Update the constants there if balance changes.

## View

Open `index.html` in a browser (it redirects to your language), or serve the folder:

```bash
python3 -m http.server 8611
```

Deploys as-is to any static host (GitHub Pages, Cloudflare Pages).
