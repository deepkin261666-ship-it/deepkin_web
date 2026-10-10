extends RefCounted

# Death penalty (2026-10-10, docs/PROGRESSION.md "Death"). Pure rules: the server builds the post-death character
# from copies with apply(), saves it, and only then drops the remains and changes the live session.
#
#   - Experience: lose XP_LOSS_FRACTION of the current total XP (Tibia-like; can cost a level), never below 0 (the
#     floor of level 1).
#   - Weapon skills: each family loses SKILL_XP_LOSS_FRACTION of its XP (can cost a skill level), never below 0.
#   - The worn backpack ALWAYS drops, with everything in it, into the remains at the death spot.
#   - Extra drops: with EXTRA_DROP_CHANCE one more item, then with SECOND_DROP_CHANCE a second, each picked uniformly
#     from the worn items in EXTRA_DROP_SLOTS and the non-empty, non-bag pouch cells (a whole stack). The battery and
#     the tool (drill) never drop: they are what gets an operator back on their feet.

const XP_LOSS_FRACTION := 0.10
const SKILL_XP_LOSS_FRACTION := 0.05
const EXTRA_DROP_CHANCE := 0.5
const SECOND_DROP_CHANCE := 0.25
const EXTRA_DROP_SLOTS := [
	EquipmentLoadout.SLOT_HEAD, EquipmentLoadout.SLOT_CHEST, EquipmentLoadout.SLOT_ARMS, EquipmentLoadout.SLOT_LEGS,
	EquipmentLoadout.SLOT_BOOTS, EquipmentLoadout.SLOT_PRIMARY_WEAPON, EquipmentLoadout.SLOT_SECONDARY_WEAPON,
	EquipmentLoadout.SLOT_LIGHT, EquipmentLoadout.SLOT_MODIFICATION_1, EquipmentLoadout.SLOT_MODIFICATION_2,
]
## Seconds the remains stay in the world before they (and whatever is still in them) crumble away.
const CORPSE_DECAY_SECONDS := 1800.0
## Seconds between death and the server respawning the operator at their bound hub.
const RESPAWN_DELAY_SECONDS := 4.0
const REMAINS_ITEM_ID := "item.container.operator_remains"

static func xp_after_death(total_xp: int) -> int:
	var xp := maxi(0, total_xp)
	return maxi(0, xp - floori(float(xp) * XP_LOSS_FRACTION))

static func skills_after_death(skills: Dictionary) -> Dictionary:
	var result := {}
	for family in skills:
		var xp := maxi(0, int(skills[family]))
		result[family] = maxi(0, xp - floori(float(xp) * SKILL_XP_LOSS_FRACTION))
	return result

## The character after a death, built on copies: {inventory, equipment, experience, skills, corpse_cells, items,
## skill_losses, xp_lost}. corpse_cells go into the remains (the backpack first, as a bag cell with its contents);
## items/skill_losses feed the DeathReport. rng decides the extra drops (seed it for tests).
static func apply(inventory: PlayerInventory, equipment: EquipmentLoadout, total_xp: int, skills: Dictionary, rng: RandomNumberGenerator, class_id: String = "class.foundry") -> Dictionary:
	var next_inventory := inventory.copy()
	var next_equipment := equipment.copy()
	var corpse_cells: Array = []
	var items: Array = []
	var backpack := next_equipment.get_item(EquipmentLoadout.SLOT_BACKPACK)
	if not backpack.is_empty():
		var contents := next_inventory.take_cells_from(PlayerInventory.POUCH_CELLS)
		next_equipment.slots.erase(EquipmentLoadout.SLOT_BACKPACK)
		corpse_cells.append({"item_id": backpack, "quantity": 1, "contents": contents})
		items.append({"item_id": backpack, "quantity": 1, "contents": contents.filter(func(cell): return not cell.is_empty()).size(), "worn": true})
	next_inventory.capacity = PlayerInventory.capacity_for(next_equipment)
	var candidates: Array = []
	for slot in EXTRA_DROP_SLOTS:
		if not next_equipment.get_item(slot).is_empty():
			candidates.append({"slot": slot})
	for index in range(mini(PlayerInventory.POUCH_CELLS, next_inventory.slots.size())):
		var cell := next_inventory.item_at(index)
		if not cell.is_empty() and not cell.has("contents"):
			candidates.append({"cell": index})
	var extra := 0
	if rng.randf() < EXTRA_DROP_CHANCE:
		extra = 1
		if rng.randf() < SECOND_DROP_CHANCE:
			extra = 2
	for _drop in extra:
		if candidates.is_empty():
			break
		var picked: Dictionary = candidates.pop_at(rng.randi_range(0, candidates.size() - 1))
		var cell: Dictionary
		if picked.has("slot"):
			cell = {"item_id": next_equipment.get_item(picked.slot), "quantity": 1}
			next_equipment.slots.erase(picked.slot)
		else:
			cell = next_inventory.slots[picked.cell].duplicate(true)
			next_inventory.slots[picked.cell] = {}
		corpse_cells.append(cell)
		items.append({"item_id": str(cell.item_id), "quantity": int(cell.quantity), "contents": 0, "worn": picked.has("slot")})
	var next_xp := xp_after_death(total_xp)
	var next_skills := skills_after_death(skills)
	# Worn gear the operator no longer qualifies for after losing a level or skill level comes off (saves require
	# a valid loadout): into a free pouch cell, else into the remains with the rest.
	var next_level := RpgRules.level_for_total_xp(next_xp)
	for slot in EquipmentLoadout.SLOT_ORDER:
		var worn_id := next_equipment.get_item(slot)
		if worn_id.is_empty() or RpgRules.meets_requirements(ItemDefinition.load_by_id(worn_id), class_id, next_level, next_skills):
			continue
		next_equipment.slots.erase(slot)
		var cell := {"item_id": worn_id, "quantity": 1}
		if next_inventory.put_cell(cell) < 0:
			corpse_cells.append(cell)
			items.append({"item_id": worn_id, "quantity": 1, "contents": 0, "worn": true})
	next_inventory._trim()
	var skill_losses: Array = []
	for family in WeaponSkills.FAMILIES:
		var before := int(skills.get(family, 0))
		var after := int(next_skills.get(family, 0))
		if before > after:
			skill_losses.append({"family": family, "xp_lost": before - after, "level_before": WeaponSkills.level_for_xp(before), "level_after": WeaponSkills.level_for_xp(after)})
	return {
		"inventory": next_inventory,
		"equipment": next_equipment,
		"experience": next_xp,
		"xp_lost": maxi(0, total_xp) - next_xp,
		"skills": next_skills,
		"skill_losses": skill_losses,
		"corpse_cells": corpse_cells,
		"items": items,
	}
