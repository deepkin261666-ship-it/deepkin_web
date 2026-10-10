class_name RpgRules
extends RefCounted

# Experience (2026-10-10): no level cap, every level harder (Tibia's cubic curve). Total XP to reach level L is
# XP_CURVE_NUMERATOR / XP_CURVE_DENOMINATOR · (L³ − 6L² + 17L − 12) = 50/3 · (L − 1)(L² − 5L + 12), always a whole
# number: 0 at level 1, 100 at 2 (the old first threshold, so early pacing is unchanged), 9,300 at 10, 917,800 at 40.
# LEVEL_LIMIT is only the representation bound (u16 level on the wire; total XP stays below 2^53 so JSON saves keep
# it exact); nobody reaches it.
const XP_CURVE_NUMERATOR := 50
const XP_CURVE_DENOMINATOR := 3
const LEVEL_LIMIT := 65535
# The capped linear curve used before 2026-10-10 (save schema < 12): 100 + 25 · (level − 1) XP per level up to 40.
# Only legacy_level_progress() reads these, to migrate saved XP.
const LEGACY_MAX_LEVEL := 40
const LEGACY_XP_BASE_TO_NEXT_LEVEL := 100
const LEGACY_XP_INCREMENT_PER_LEVEL := 25
# Fallback kill XP for a mob whose data has no "xp" (every authored mob has one).
const XP_PER_NPC_KILL := 35
const NPC_KILL_REWARD_ID := "reward.npc_kill"
const BASE_HEALTH := 76
const HEALTH_PER_ENDURANCE := 4
const STAMINA_PER_ENDURANCE := 5
const CARRY_CAPACITY_PER_MIGHT := 5
const STAT_DAMAGE_STEP := 0.015
const MAX_DAMAGE_REDUCTION := 0.75
const GEAR_TIER_MIN_LEVELS := [1, 8, 15, 22, 29, 36]

enum DamageType { PHYSICAL, ENERGY, BIOLOGICAL, ENVIRONMENTAL }

static func attributes_for(class_id: String) -> Dictionary:
	var definition := DeepkinClassCatalog.definition(class_id)
	var attributes: Variant = definition.get("attributes", {})
	return attributes.duplicate(true) if attributes is Dictionary else {}

static func attribute_for(class_id: String, attribute: String) -> int:
	var attributes := attributes_for(class_id)
	return clampi(int(attributes.get(attribute, 10)), 1, 20)

static func max_health_for(class_id: String) -> int:
	return BASE_HEALTH + attribute_for(class_id, "endurance") * HEALTH_PER_ENDURANCE

static func stamina_for(class_id: String) -> int:
	return attribute_for(class_id, "endurance") * STAMINA_PER_ENDURANCE

# Carry cap in kg (2026-10-05): each class has its own base and growth per level (classes.json "carry");
# heavy Foundry carries the most, light Relay the least. Classes without data fall back to Might.
# Equipped items with carry_bonus (backpacks) add to it.
static func carry_capacity_for(class_id: String, level: int = 1, equipment: EquipmentLoadout = null) -> float:
	var carry: Variant = DeepkinClassCatalog.definition(class_id).get("carry", {})
	var base := float(attribute_for(class_id, "might") * CARRY_CAPACITY_PER_MIGHT)
	if carry is Dictionary and not carry.is_empty():
		base = float(carry.get("base", 50.0)) + float(carry.get("per_level", 0.0)) * float(maxi(level, 1) - 1)
	return base + _equipment_property_total(equipment, "carry_bonus")

## Weight carried in the inventory plus everything equipped (kg).
static func carried_weight(inventory: PlayerInventory, equipment: EquipmentLoadout) -> float:
	var total := inventory.weight() if inventory != null else 0.0
	if equipment != null:
		for item_id in equipment.slots.values():
			var definition := ItemDefinition.load_by_id(str(item_id))
			if definition != null:
				total += definition.weight
	return total

static func stat_multiplier(value: int) -> float:
	return clampf(1.0 + float(value - 10) * STAT_DAMAGE_STEP, 0.75, 1.25)

static func ranged_accuracy_for(class_id: String) -> float:
	return clampf(0.85 + float(attribute_for(class_id, "precision") - 10) * 0.01, 0.5, 1.0)

static func weakpoint_multiplier_for(class_id: String) -> float:
	return clampf(1.0 + float(attribute_for(class_id, "precision") - 10) * 0.03, 0.7, 1.3)

static func stagger_multiplier_for(class_id: String) -> float:
	return clampf(1.0 + float(attribute_for(class_id, "might") - 10) * 0.02, 0.7, 1.3)

static func ability_cost_for(class_id: String, base_cost: float) -> float:
	var technology := attribute_for(class_id, "technology")
	return maxf(base_cost * 0.7, base_cost * (1.0 - float(technology - 10) * 0.015))

static func combat_coefficient_for(class_id: String, coefficient: String) -> float:
	var definition := DeepkinClassCatalog.definition(class_id)
	var coefficients: Variant = definition.get("combat_coefficients", {})
	return maxf(0.0, float(coefficients.get(coefficient, 1.0))) if coefficients is Dictionary else 1.0

static func outgoing_damage(
	class_id: String,
	weapon_type: String,
	base_damage: int,
	modifier: float = 1.0
) -> int:
	var coefficient := combat_coefficient_for(class_id, weapon_type)
	var attribute := "technology"
	match weapon_type:
		"melee":
			attribute = "might"
		"ranged":
			attribute = "precision"
		"ability":
			attribute = "technology"
	var scaled := float(base_damage) * coefficient * stat_multiplier(attribute_for(class_id, attribute)) * maxf(modifier, 0.0)
	return maxi(1, roundi(scaled))

static func armor_rating_for(class_id: String, equipment: EquipmentLoadout = null) -> float:
	var definition := DeepkinClassCatalog.definition(class_id)
	var rating := maxf(0.0, float(definition.get("base_armor", 0.0)))
	rating += _equipment_property_total(equipment, "armor_defense")
	return rating * combat_coefficient_for(class_id, "defense")

static func resistance_rating_for(class_id: String, equipment: EquipmentLoadout = null) -> float:
	var definition := DeepkinClassCatalog.definition(class_id)
	var rating := maxf(0.0, float(definition.get("base_resistance", 0.0)))
	rating += _equipment_property_total(equipment, "resistance_bonus")
	rating += float(attribute_for(class_id, "endurance") - 8) * 0.5
	return maxf(0.0, rating)

static func mitigated_damage(
	class_id: String,
	equipment: EquipmentLoadout,
	damage_type: int,
	incoming_damage: int
) -> int:
	if incoming_damage <= 0:
		return 0
	var rating := armor_rating_for(class_id, equipment) if damage_type == DamageType.PHYSICAL else resistance_rating_for(class_id, equipment)
	var reduction := minf(MAX_DAMAGE_REDUCTION, rating / (rating + 100.0))
	return maxi(1, roundi(float(incoming_damage) * (1.0 - reduction)))

static func tier_for_level(level: int) -> int:
	# Six gear tiers; every level past 36 stays T6.
	return clampi(floori(float(maxi(level, 1) - 1) / 7.0) + 1, 1, 6)

static func minimum_level_for_tier(tier: int) -> int:
	return GEAR_TIER_MIN_LEVELS[tier - 1] if tier >= 1 and tier <= GEAR_TIER_MIN_LEVELS.size() else 0

## Total XP needed to reach level (level 1 = 0). Uncapped cubic; see XP_CURVE_*.
static func total_xp_for_level(level: int) -> int:
	var bounded := clampi(level, 1, LEVEL_LIMIT)
	@warning_ignore("integer_division")
	return XP_CURVE_NUMERATOR * (bounded - 1) * (bounded * bounded - 5 * bounded + 12) / XP_CURVE_DENOMINATOR

## XP from level to level + 1 (0 at the representation limit).
static func xp_to_next_level(level: int) -> int:
	if level < 1 or level >= LEVEL_LIMIT:
		return 0
	return total_xp_for_level(level + 1) - total_xp_for_level(level)

## Largest total XP a character can hold (the representation bound, not a design cap).
static func max_total_xp() -> int:
	return total_xp_for_level(LEVEL_LIMIT)

static func level_for_total_xp(total_xp: int) -> int:
	var bounded_xp := clampi(total_xp, 0, max_total_xp())
	var low := 1
	var high := LEVEL_LIMIT
	while low < high:
		@warning_ignore("integer_division")
		var middle := (low + high + 1) / 2
		if total_xp_for_level(middle) <= bounded_xp:
			low = middle
		else:
			high = middle - 1
	return low

## Progress from the current level to the next, 0..1 (the HUD XP bar).
static func level_progress(total_xp: int) -> float:
	var level := level_for_total_xp(total_xp)
	var span := xp_to_next_level(level)
	return clampf(float(total_xp - total_xp_for_level(level)) / float(span), 0.0, 1.0) if span > 0 else 1.0

static func award_xp(current_total_xp: int, amount: int) -> Dictionary:
	var old_xp := clampi(current_total_xp, 0, max_total_xp())
	var new_xp := mini(max_total_xp(), old_xp + maxi(0, amount))
	var old_level := level_for_total_xp(old_xp)
	var new_level := level_for_total_xp(new_xp)
	return {
		"total_xp": new_xp,
		"level": new_level,
		"levels_gained": new_level - old_level,
		"xp_gained": new_xp - old_xp,
	}

## Kill XP split (2026-10-10): every player who damaged the mob gets XP in proportion to the damage they dealt
## ({player entity id: damage}); shares are floored and the remainder goes to the top contributor (lowest id on a
## tie), so the shares always sum to exactly xp. Shares of players no longer online are forfeited by the caller.
static func split_kill_xp(xp: int, contributions: Dictionary) -> Dictionary:
	var shares := {}
	var total := 0
	var top_id := 0
	for player_id in contributions:
		var damage := maxi(0, int(contributions[player_id]))
		if damage <= 0:
			continue
		total += damage
		if top_id == 0 or damage > int(contributions[top_id]) or (damage == int(contributions[top_id]) and int(player_id) < top_id):
			top_id = int(player_id)
	if xp <= 0 or total <= 0:
		return shares
	var given := 0
	for player_id in contributions:
		var damage := maxi(0, int(contributions[player_id]))
		if damage <= 0:
			continue
		var share := floori(float(xp) * float(damage) / float(total))
		shares[int(player_id)] = share
		given += share
	shares[top_id] = int(shares.get(top_id, 0)) + xp - given
	return shares

## Saved XP from before the uncapped curve (schema < 12) mapped onto it: the character keeps its level and the same
## fraction of the way to the next one, so nobody jumps or drops a level on load. Old level-40 (capped) XP maps to
## exactly level 40. Monotonic: more old XP never gives less new XP.
static func migrate_legacy_xp(legacy_xp: int) -> int:
	var xp := maxi(0, legacy_xp)
	var level := 1
	var start := 0
	while level < LEGACY_MAX_LEVEL:
		var span := LEGACY_XP_BASE_TO_NEXT_LEVEL + (level - 1) * LEGACY_XP_INCREMENT_PER_LEVEL
		if xp < start + span:
			var fraction := float(xp - start) / float(span)
			return total_xp_for_level(level) + floori(fraction * float(xp_to_next_level(level)))
		start += span
		level += 1
	return total_xp_for_level(LEGACY_MAX_LEVEL)

## Legacy total XP of the capped curve at a level (tests and migration notes).
static func legacy_total_xp_for_level(level: int) -> int:
	var total := 0
	for current in range(1, clampi(level, 1, LEGACY_MAX_LEVEL)):
		total += LEGACY_XP_BASE_TO_NEXT_LEVEL + (current - 1) * LEGACY_XP_INCREMENT_PER_LEVEL
	return total

static func meets_requirements(
	item: ItemDefinition,
	class_id: String,
	level: int,
	skills: Dictionary = {}
) -> bool:
	if item == null or level < item.minimum_level or item.gear_tier > tier_for_level(level):
		return false
	var class_requirements: Array = item.requirements.get("class_ids", [])
	if not class_requirements.is_empty() and not class_requirements.has(class_id):
		return false
	var required_skills: Variant = item.requirements.get("minimum_skills", {})
	if required_skills is Dictionary:
		for family in required_skills:
			if WeaponSkills.level_of(skills, str(family)) < int(required_skills[family]):
				return false
	var required_attributes: Variant = item.requirements.get("minimum_attributes", {})
	if required_attributes is Dictionary:
		var attributes := attributes_for(class_id)
		for attribute in required_attributes:
			if int(attributes.get(attribute, 0)) < int(required_attributes[attribute]):
				return false
	return true

static func _equipment_property_total(equipment: EquipmentLoadout, property_name: String) -> float:
	if equipment == null:
		return 0.0
	var total := 0.0
	for item_id in equipment.slots.values():
		var item := ItemDefinition.load_by_id(str(item_id))
		if item != null:
			total += float(item.properties.get(property_name, 0.0))
	return total
