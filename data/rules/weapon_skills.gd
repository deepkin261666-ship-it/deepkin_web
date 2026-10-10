class_name WeaponSkills
extends RefCounted

# Weapon-use skills (D-01/D-02, 2026-10-05): skills belong to weapon families, not to classes. Every landed hit
# trains the family of the weapon that dealt it; taking a hit with a shield equipped trains Shielding. The class
# sets how fast each family trains (skill_affinity in classes.json; untrained families learn at 0.5x). Skill level
# and character level both feed the shared damage formula, and items may require a family level.

const FAMILIES := [
	"skill.edge", "skill.blunt", "skill.blades", "skill.firearms", "skill.precision",
	"skill.spores", "skill.vitalism", "skill.tech", "skill.shielding",
]
# Display names (2026-10-09): Edge became "Blades" and the old Blades became "Short Blades". The IDs stay stable
# (saves, items and the wire refer to them), so skill.edge reads "Blades" and skill.blades reads "Short Blades".
const NAMES := {
	"skill.edge": "Blades", "skill.blunt": "Blunt", "skill.blades": "Short Blades", "skill.firearms": "Firearms",
	"skill.precision": "Precision", "skill.spores": "Spores", "skill.vitalism": "Vitalism", "skill.tech": "Tech",
	"skill.shielding": "Shielding",
}
## One line each: what the skill covers and what it does today.
const DESCRIPTIONS := {
	"skill.edge": "Swords and axes. Chained hits build Heat: +2, +4, +6 damage within 3 s.",
	"skill.blunt": "Hammers and maces. Slow, heavy blows that hit hardest per swing.",
	"skill.blades": "Knives and daggers. Ambush: +4 damage after moving 2 m since your last hit.",
	"skill.firearms": "Shotguns, carbines and rifles. Steady fire at mid range.",
	"skill.precision": "Precision rifles. +3 damage on targets 6 m or more away.",
	"skill.spores": "Spore projectors. With one in hand, Bloom poisons enemies instead of healing.",
	"skill.vitalism": "Living weapons that grow with their bearer.",
	"skill.tech": "Energy weapons and field electronics.",
	"skill.shielding": "Shields. Trains when you are hit with a shield up; 8% less damage, up to 40%.",
}
## Planned uses beyond combat (presentation only; nothing reads these yet).
const LATER := {
	"skill.blunt": "Later: staggering and breaking armour and rock.",
	"skill.blades": "Later: silent takedowns.",
	"skill.precision": "Later: weak points.",
	"skill.spores": "Later: fungal growth and area denial.",
	"skill.vitalism": "Later: stronger healing and tending the living.",
	"skill.tech": "Later: hacking terminals, doors, turrets and drones.",
	"skill.shielding": "Later: active block and parry.",
}
const MAX_LEVEL := 100
const XP_PER_HIT := 10
const XP_PER_BLOCKED_HIT := 8
const DEFAULT_AFFINITY := 0.5
const DAMAGE_PER_SKILL_LEVEL := 0.01
const DAMAGE_PER_CHARACTER_LEVEL := 0.006
# Shielding: armor-style mitigation of incoming damage while a shield is equipped.
const SHIELD_REDUCTION_BASE := 0.08
const SHIELD_REDUCTION_PER_LEVEL := 0.002

static func is_family(family: String) -> bool:
	return FAMILIES.has(family)

static func display_name(family: String) -> String:
	return str(NAMES.get(family, family.trim_prefix("skill.").capitalize()))

static func description(family: String) -> String:
	return str(DESCRIPTIONS.get(family, ""))

## Total skill XP needed to reach level (level 1 = 0 XP). Grows ~level^1.7 so early levels come in minutes.
static func xp_for_level(level: int) -> int:
	level = clampi(level, 1, MAX_LEVEL)
	return roundi(30.0 * pow(float(level - 1), 1.7))

static func level_for_xp(xp: int) -> int:
	var level := 1
	while level < MAX_LEVEL and xp >= xp_for_level(level + 1):
		level += 1
	return level

static func max_xp() -> int:
	return xp_for_level(MAX_LEVEL)

## Progress to the next level, 0..1.
static func progress(xp: int) -> float:
	var level := level_for_xp(xp)
	if level >= MAX_LEVEL:
		return 1.0
	var start := xp_for_level(level)
	return clampf(float(xp - start) / float(maxi(1, xp_for_level(level + 1) - start)), 0.0, 1.0)

static func affinity(class_id: String, family: String) -> float:
	var table: Variant = DeepkinClassCatalog.definition(class_id).get("skill_affinity", {})
	return maxf(0.0, float(table.get(family, DEFAULT_AFFINITY))) if table is Dictionary else DEFAULT_AFFINITY

## XP a class earns in family for one training event of base_xp.
static func gain(class_id: String, family: String, base_xp: int = XP_PER_HIT) -> int:
	return maxi(1, roundi(float(base_xp) * affinity(class_id, family)))

## Returns a copy of skills with xp added to family (capped).
static func with_gain(skills: Dictionary, family: String, xp: int) -> Dictionary:
	var result := skills.duplicate()
	if is_family(family) and xp > 0:
		result[family] = mini(max_xp(), int(result.get(family, 0)) + xp)
	return result

static func level_of(skills: Dictionary, family: String) -> int:
	return level_for_xp(int(skills.get(family, 0)))

## Damage multiplier from the weapon family's skill level and the character level.
static func damage_factor(skill_level: int, character_level: int) -> float:
	return 1.0 + DAMAGE_PER_SKILL_LEVEL * float(maxi(skill_level, 1) - 1) + DAMAGE_PER_CHARACTER_LEVEL * float(maxi(character_level, 1) - 1)

static func shield_reduction(shielding_level: int) -> float:
	return clampf(SHIELD_REDUCTION_BASE + SHIELD_REDUCTION_PER_LEVEL * float(maxi(shielding_level, 1) - 1), 0.0, 0.4)

static func is_valid(skills: Variant) -> bool:
	if not skills is Dictionary:
		return false
	for family in skills:
		var value: Variant = skills[family]
		if not family is String or not is_family(family) or typeof(value) not in [TYPE_INT, TYPE_FLOAT]:
			return false
		if not is_finite(float(value)) or float(value) < 0.0 or float(value) > float(max_xp()) or float(value) != floorf(float(value)):
			return false
	return true
