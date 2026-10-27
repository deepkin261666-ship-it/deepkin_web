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
## One line each: what the skill covers and what it does today (the trait numbers below; 2026-10-24 balance pass).
const DESCRIPTIONS := {
	"skill.edge": "Swords, axes and chainsaws. Heat: chained hits within 3 s deal +5 / +10 / +15% damage (a running chainsaw starts at +15%).",
	"skill.blunt": "Hammers and maces. Stagger: a blow delays the enemy's next attack. Crush: extra damage against elites and bosses.",
	"skill.blades": "Knives and daggers. Ambush: +30% damage after moving 2 m since your last hit; finishing blows on wounded humanoids.",
	"skill.firearms": "Shotguns, carbines and rifles. Suppression: each consecutive hit on the same target within 2 s adds +5% damage, up to +15%.",
	"skill.precision": "Precision rifles. +15% damage on targets 6 m or more away.",
	"skill.spores": "Spore projectors. Fire spore cartridges that poison what they hit; with one in hand, Bloom poisons enemies instead of healing.",
	"skill.vitalism": "Living weapons that fire synapse darts: they wound enemies and heal the operators they strike.",
	"skill.tech": "Energy weapons and field electronics. Each shot draws energy from the worn cell. Overcharge: +15% damage while the cell is above half.",
	"skill.shielding": "Shields. Always up while equipped (no need to raise it): 8% less damage, up to 40%; trains on every hit it blocks.",
}
## Planned uses beyond combat (presentation only; nothing reads these yet).
const LATER := {
	"skill.blunt": "Later: breaking rock.",
	"skill.blades": "Later: silent takedowns.",
	"skill.precision": "Later: weak points.",
	"skill.spores": "Later: fungal growth and area denial.",
	"skill.vitalism": "Later: stronger healing and tending the living.",
	"skill.tech": "Later: hacking terminals, doors, turrets and drones.",
	"skill.shielding": "Later: active block and parry.",
}
const MAX_LEVEL := 100
## Base XP of one training event that is not a weapon hit (a heal, a drone hit): × class affinity.
const XP_PER_HIT := 10
## Weapon hits train by time, not by count (2026-10-24, docs/design/WEAPON_BALANCE.md 5.4): a landed hit is worth
## XP_PER_ATTACK_SECOND × the weapon's attack interval × class affinity, so every weapon trains its skill at the same
## XP per second of fighting. Fractions carry over between hits on the server (PlayerSession.skill_xp_carry).
const XP_PER_ATTACK_SECOND := 10.0
const XP_PER_BLOCKED_HIT := 8
const DEFAULT_AFFINITY := 0.5
const DAMAGE_PER_SKILL_LEVEL := 0.01
const DAMAGE_PER_CHARACTER_LEVEL := 0.006
# Shielding: armor-style mitigation of incoming damage while a shield is equipped.
const SHIELD_REDUCTION_BASE := 0.08
const SHIELD_REDUCTION_PER_LEVEL := 0.002
## Skill level a weapon of each gear tier requires in its own family (2026-10-24, WEAPON_BALANCE.md 5.5): character
## level opens the tier (RpgRules.GEAR_TIER_MIN_LEVELS), the skill earns it. Enforced by RpgRules.meets_requirements
## and required in the item data (ItemDefinition validation) for every Tier-2+ weapon.
const TIER_SKILL_MINIMUMS := [1, 10, 20, 35, 50, 70]

# Weapon-skill traits (2026-10-24 balance pass: percentages, so they are interval-neutral and keep their weight at
# every tier). CombatSystem applies them; tools/weapon_balance.gd prices them. Each is worth about +15 % at its
# expected uptime.
## Blades Heat: +5 % per chained hit within HEAT_WINDOW s, up to HEAT_MAX_STACKS (a chainsaw starts at the cap).
const HEAT_PERCENT_PER_STACK := 0.05
const HEAT_MAX_STACKS := 3
const HEAT_WINDOW := 3.0
## Short Blades Ambush: +30 % on a hit after moving AMBUSH_DISTANCE m since the last one (about half the hits).
const AMBUSH_PERCENT := 0.30
const AMBUSH_DISTANCE := 2.0
const AMBUSH_EXPECTED_UPTIME := 0.5
## Precision Range: +15 % at PRECISION_DISTANCE m or more.
const PRECISION_PERCENT := 0.15
const PRECISION_DISTANCE := 6.0
## Firearms Suppression: +5 % per consecutive hit on the same target within SUPPRESSION_WINDOW s, up to 3 stacks.
const SUPPRESSION_PERCENT_PER_STACK := 0.05
const SUPPRESSION_MAX_STACKS := 3
const SUPPRESSION_WINDOW := 2.0
## Tech Overcharge: +15 % while the worn cell holds more than OVERCHARGE_MIN_FRACTION of its capacity.
const OVERCHARGE_PERCENT := 0.15
const OVERCHARGE_MIN_FRACTION := 0.5
## Blunt Stagger: a hit pushes the struck mob's next attack back by stagger_bonus × STAGGER_SECONDS_PER_POINT s; a
## staggered mob cannot be staggered again for STAGGER_IMMUNITY s (no stun-lock). Crush: + armored_damage_bonus
## (a fraction) against elite and boss mobs.
const STAGGER_SECONDS_PER_POINT := 3.0
const STAGGER_IMMUNITY := 1.5

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
## Skill XP one landed weapon hit is worth (a fraction; the server carries the remainder): equal XP per second of
## attacking for every weapon, XP_PER_ATTACK_SECOND × affinity.
static func hit_xp(class_id: String, family: String, attack_interval: float) -> float:
	return XP_PER_ATTACK_SECOND * maxf(attack_interval, 0.0) * affinity(class_id, family)

## Adds xp (fractional) to carry[family] and returns the whole XP to grant now; the fraction stays in carry.
static func take_whole_xp(carry: Dictionary, family: String, xp: float) -> int:
	var total := float(carry.get(family, 0.0)) + maxf(xp, 0.0)
	var whole := floori(total + 0.000001)
	carry[family] = maxf(0.0, total - float(whole))
	return whole

## Skill level a weapon of this gear tier requires in its family (1 = none).
static func tier_skill_minimum(tier: int) -> int:
	return int(TIER_SKILL_MINIMUMS[clampi(tier, 1, TIER_SKILL_MINIMUMS.size()) - 1])

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
