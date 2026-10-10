class_name CombatSkills
extends RefCounted

# Two skill buttons (2026-10-07, docs/design/COMBAT_ROLES_PROPOSAL.md §6):
#   Q — mobility slot: Dash for every class today; learnable alternatives (e.g. Grapple) come later and are swapped
#       from the loadout screen while out of combat.
#   C — class power: one per class, always available, its own cooldown.
#       Foundry  Bastion  — provokes nearby enemies onto the Foundry and takes 30% less damage for 4 s.
#       Drift    Long Shot — the next shot within 4 s deals x2.5 damage with +50% range.
#       Verdant  Bloom    — heals the Verdant and nearby allies over 6 s (with a Spores weapon: poisons nearby enemies).
#       Relay    Overload — the next hit within 3 s deals x3 damage, and the next Dash is ready at once.
# Greater skills, learned by level and bought in class cities, will slot into Q or C later.
# Grapple was removed (2026-10-09): it was wired to C but no class had it. A learnable Q mobility returns with the
# loadout screen's alternatives. ALL's order is the wire index for SELECT_SKILL / CharacterStatus.

const DASH := "skill.dash"
const ALL := [DASH, "ability.bastion", "ability.bloom", "ability.overload", "ability.long_shot"]
const MOBILITY := [DASH]
const NAMES := {
	DASH: "Dash", "ability.bastion": "Bastion", "ability.bloom": "Bloom",
	"ability.overload": "Overload", "ability.long_shot": "Long Shot",
}
const DESCRIPTIONS := {
	DASH: "Burst a few metres in the direction you are moving (or facing).",
	"ability.bastion": "Provoke nearby enemies onto you and take 30% less damage for 4 s (slower while braced).",
	"ability.bloom": "Heal yourself and nearby allies over 6 s (with a Spores weapon: poison nearby enemies instead).",
	"ability.overload": "Your next hit within 3 s deals triple damage, and your next Dash is ready at once.",
	"ability.long_shot": "Your next shot within 4 s deals x2.5 damage with 50% more range.",
}
const POWER_COOLDOWNS := {
	"ability.bastion": 14.0, "ability.long_shot": 12.0, "ability.bloom": 16.0, "ability.overload": 12.0,
}
const DASH_COOLDOWN := 5.0
const DASH_ENERGY_COST := 6.0
const DASH_TICKS := 6
const DASH_SPEED := 15.0
const ABILITY_COOLDOWN := 12.0
const ABILITY_ENERGY_COST := 15.0
# Power tuning.
const BASTION_SECONDS := 4.0
const BASTION_DAMAGE_TAKEN := 0.7
const PROVOKE_RADIUS := 7.0
const LONG_SHOT_WINDOW := 4.0
const LONG_SHOT_DAMAGE := 2.5
const LONG_SHOT_RANGE := 1.5
const OVERLOAD_WINDOW := 3.0
const OVERLOAD_DAMAGE := 3.0
const BLOOM_SECONDS := 6.0
const BLOOM_RADIUS := 5.0
const BLOOM_HEAL_SELF := 6
const BLOOM_HEAL_ALLY := 5
const BLOOM_POISON := 3
# Class passives (2026-10-09): always on for the class, whatever weapon it holds. Momentum and Trailblazer live in
# CombatSystem, Relay in the server's Overload, Regrowth here.
const REGROWTH_HEAL := 2
const REGROWTH_INTERVAL := 2.0
# Seconds since the last hit dealt or taken before the Q slot can be changed.
const COMBAT_LOCK_SECONDS := 5.0

## Skills the Q (mobility) slot can hold for this class.
static func available_for(class_id: String) -> Array[String]:
	var result: Array[String] = []
	result.assign(MOBILITY)
	return result

static func is_available(class_id: String, skill_id: String) -> bool:
	return available_for(class_id).has(skill_id)

## The class power on C.
static func power_for(class_id: String) -> String:
	var ability_id := str(DeepkinClassCatalog.definition(class_id).get("ability_id", ""))
	return ability_id if ALL.has(ability_id) and ability_id != DASH else ""

static func display_name(skill_id: String) -> String:
	return str(NAMES.get(skill_id, skill_id))

static func index_of(skill_id: String) -> int:
	return ALL.find(skill_id)

static func from_index(index: int) -> String:
	return ALL[index] if index >= 0 and index < ALL.size() else ""

static func cooldown_for(skill_id: String) -> float:
	return DASH_COOLDOWN if skill_id == DASH else float(POWER_COOLDOWNS.get(skill_id, ABILITY_COOLDOWN))

static func energy_cost_for(skill_id: String) -> float:
	return DASH_ENERGY_COST if skill_id == DASH else ABILITY_ENERGY_COST
