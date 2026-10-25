class_name CombatSystem
extends RefCounted

const PLAYER_DAMAGE := 10
const PLAYER_ATTACK_RANGE := 1.8
const PLAYER_ATTACK_COOLDOWN := 0.75
const AIM_RAY_HALF_WIDTH := 0.9
const AIM_MELEE_HALF_ARC_DEGREES := 70.0
## Blades Heat cap (WeaponSkills.HEAT_MAX_STACKS); chainsaws start at the cap (Revved, 2026-10-24).
const HEAT_MAX_STACKS := WeaponSkills.HEAT_MAX_STACKS
## Drift passive Trailblazer: +8 % on the target the Drift hit within the last 4 s (2026-10-24: was +2 flat).
const TRAILBLAZER_PERCENT := 0.08
const TRAILBLAZER_WINDOW := 4.0
## Shotgun spread (2026-10-24): extra pellets never reach a mob farther than this past the weapon's reach.
const SPREAD_REACH_SLACK := 0.4

var _registry: EntityRegistry
var _zones: Dictionary[String, GameZone]
var _last_attack_time: Dictionary[int, float] = {}
# Timed damage-taken multipliers per entity (Bastion, Momentum): each window is kept on its own and the strongest
# active one applies, so a weaker buff never overwrites a stronger one (2026-10-09).
var _defense_windows: Dictionary[int, Array] = {}
var _bulwark_hits: Dictionary[int, int] = {}
var _breaker_heat: Dictionary[int, Dictionary] = {}
var _pathfinder_marks: Dictionary[int, Dictionary] = {}
var _infiltrator_position: Dictionary[int, Vector3] = {}
var _damage_reduction: Dictionary[int, float] = {}
# Firearms Suppression: shooter -> {"target", "stacks", "expires"} (2026-10-24).
var _suppression: Dictionary[int, Dictionary] = {}
# Tech Overcharge: worn-cell charge fraction per player, set by the server before each shot (2026-10-24).
var _energy_fraction: Dictionary[int, float] = {}
# Blunt Stagger: mob -> server time until which it cannot be staggered again (2026-10-24).
var _stagger_immune_until: Dictionary[int, float] = {}

func _init(p_registry: EntityRegistry, p_zones: Dictionary[String, GameZone]) -> void:
	_registry = p_registry
	_zones = p_zones

func resolve_attack(
	source_entity_id: int,
	target_entity_id: int,
	server_time: float,
	weapon_definition_id: String = "",
	ammo_available: int = 0,
	ammo_commit: Callable = Callable(),
	damage_scale: float = 1.0,
	range_scale: float = 1.0
) -> Dictionary:
	var source := _registry.get_entity(source_entity_id)
	var target := _registry.get_entity(target_entity_id)
	if source == null or source.lifecycle != WorldEntity.Lifecycle.ACTIVE or source.health == null or source.health.is_dead():
		return _rejected("invalid_source")
	if target == null or target.lifecycle != WorldEntity.Lifecycle.ACTIVE or target.health == null or target.health.is_dead():
		return _rejected("invalid_target")
	if not _is_valid_combat_pair(source, target):
		return _rejected("invalid_target_type")
	if source.state.zone_id != target.state.zone_id or not _zones.has(source.state.zone_id):
		return _rejected("invalid_zone")
	var zone: GameZone = _zones[source.state.zone_id]
	if not zone.entity_ids.has(source_entity_id) or not zone.entity_ids.has(target_entity_id):
		return _rejected("invalid_zone_membership")
	var range := _attack_range(source, weapon_definition_id) * range_scale
	if _horizontal_distance_squared(source.state.position, target.state.position) > range * range:
		return _rejected("out_of_range")
	var cooldown := _attack_cooldown(source, weapon_definition_id)
	if _last_attack_time.has(source_entity_id) and server_time - _last_attack_time[source_entity_id] < cooldown:
		return _rejected("cooldown")
	var weapon := _weapon_definition(source, weapon_definition_id)
	# Rounds, cartridges, darts and energy for ranged weapons; gas for fuel-fed melee weapons (chainsaws, 2026-10-24).
	if source.state.entity_type == EntityState.TYPE_PLAYER and weapon != null and (weapon.weapon_type == "ranged" or weapon.uses_fuel()):
		if ammo_available <= 0:
			return _rejected("insufficient_ammunition")
		if not ammo_commit.is_valid() or not bool(ammo_commit.call()):
			return _rejected("ammunition_commit_failed")
	var requested_damage := _attack_damage(source, weapon_definition_id)
	if source.state.entity_type == EntityState.TYPE_PLAYER:
		# Percent traits and passives (2026-10-24) add up and scale the hit once, with the class and skill factors.
		var bonus := _passive_damage_percent(source, target, server_time) + _weapon_trait_percent(source, target, weapon, server_time)
		requested_damage = RpgRules.outgoing_damage(
			source.state.class_id,
			weapon.weapon_type if weapon != null and not weapon.weapon_type.is_empty() else "melee",
			requested_damage,
			damage_scale * (1.0 + bonus)
		)
	var damage_type := RpgRules.DamageType.PHYSICAL if weapon == null else _damage_type(weapon.damage_type)
	if target.state.entity_type == EntityState.TYPE_PLAYER:
		var loadout := EquipmentLoadout.new()
		loadout.slots = target.state.equipment.duplicate(true)
		requested_damage = RpgRules.mitigated_damage(target.state.class_id, loadout, damage_type, requested_damage)
		requested_damage = maxi(1, roundi(float(requested_damage) * _damage_multiplier(target, server_time) * (1.0 - float(_damage_reduction.get(target.state.entity_id, 0.0)))))
	# Short Blades finishing blow on a low-health humanoid mob (ExecutionRules, Phase 2c): always kills.
	var execution := source.state.entity_type == EntityState.TYPE_PLAYER and ExecutionRules.can_execute(weapon, target)
	if execution:
		requested_damage = maxi(requested_damage, target.health.current_health)
	_last_attack_time[source_entity_id] = server_time
	var applied_damage := target.health.apply_damage(requested_damage)
	if applied_damage <= 0:
		return _rejected("target_dead")
	if target.state.entity_type == EntityState.TYPE_PLAYER:
		_record_bulwark_momentum(target, server_time)
	if source.state.entity_type == EntityState.TYPE_PLAYER and source.state.class_id == "class.drift":
		_pathfinder_marks[source.state.entity_id] = {"target": target.state.entity_id, "expires": server_time + TRAILBLAZER_WINDOW}
	var staggered := 0.0
	if source.state.entity_type == EntityState.TYPE_PLAYER and not target.health.is_dead():
		staggered = _stagger(target, weapon, server_time)
	target.sync_combat_state()
	if target.health.is_dead() and target.state.entity_type == EntityState.TYPE_NPC:
		target.state.npc_state = EntityState.NPC_STATE_DEAD
	target.state.target_entity_id = 0 if target.health.is_dead() else target.state.target_entity_id
	var event := DamageApplied.new(
		source_entity_id,
		target_entity_id,
		applied_damage,
		target.health.current_health,
		target.health.max_health,
		target.health.is_dead()
	)
	event.execution = execution and target.health.is_dead()
	return {"accepted": true, "event": event, "reason": "", "damage": requested_damage, "staggered": staggered}

## Shotgun spread (2026-10-24, docs/COMBAT.md): after an accepted hit with a weapon whose spread_targets > 0, up to
## that many other live mobs inside the cone (spread_half_angle either side of the line from the shooter to the
## primary target) and within the weapon's reach take spread_damage × the primary hit's damage, nearest first. No
## round, cooldown or trait is spent or built again: it is the same shot. Returns the DamageApplied events.
func apply_spread(source_entity_id: int, primary_target_id: int, weapon_definition_id: String, primary_damage: int, range_scale: float = 1.0) -> Array[DamageApplied]:
	var events: Array[DamageApplied] = []
	var source := _registry.get_entity(source_entity_id)
	var primary := _registry.get_entity(primary_target_id)
	var weapon := _weapon_definition(source, weapon_definition_id) if source != null else null
	if weapon == null or primary == null or primary_damage <= 0 or weapon.spread_targets() <= 0:
		return events
	var line := Vector2(primary.state.position.x - source.state.position.x, primary.state.position.z - source.state.position.z)
	if line.length_squared() < 0.0001:
		return events
	line = line.normalized()
	var reach := _attack_range(source, weapon_definition_id) * range_scale + SPREAD_REACH_SLACK
	var cosine := cos(deg_to_rad(weapon.spread_half_angle()))
	var candidates: Array = []
	for candidate in _registry.all_entities():
		if candidate.state.entity_id == primary_target_id or candidate.state.entity_type != EntityState.TYPE_NPC or candidate.state.zone_id != source.state.zone_id:
			continue
		if candidate.lifecycle != WorldEntity.Lifecycle.ACTIVE or candidate.health == null or candidate.health.is_dead():
			continue
		var offset := Vector2(candidate.state.position.x - source.state.position.x, candidate.state.position.z - source.state.position.z)
		var distance := offset.length()
		if distance > reach or distance < 0.001 or offset.dot(line) < distance * cosine:
			continue
		candidates.append({"entity": candidate, "distance": distance})
	candidates.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return float(a.distance) < float(b.distance) or (is_equal_approx(float(a.distance), float(b.distance)) and int(a.entity.state.entity_id) < int(b.entity.state.entity_id)))
	var damage := maxi(1, roundi(float(primary_damage) * weapon.spread_damage()))
	for entry in candidates.slice(0, weapon.spread_targets()):
		var struck: WorldEntity = entry.entity
		var applied := struck.health.apply_damage(damage)
		if applied <= 0:
			continue
		struck.sync_combat_state()
		if struck.health.is_dead():
			struck.state.npc_state = EntityState.NPC_STATE_DEAD
			struck.state.target_entity_id = 0
		events.append(DamageApplied.new(source_entity_id, struck.state.entity_id, applied, struck.health.current_health, struck.health.max_health, struck.health.is_dead()))
	return events

## Worn-cell charge of a player, 0..1, for Tech Overcharge (the server sets it before each attack).
func set_energy_fraction(entity_id: int, fraction: float) -> void:
	_energy_fraction[entity_id] = clampf(fraction, 0.0, 1.0) if is_finite(fraction) else 0.0

## Seconds until this mob may attack again (0 when it is ready); tests and the stagger rule read it.
func attack_ready_in(entity_id: int, server_time: float) -> float:
	var entity := _registry.get_entity(entity_id)
	if entity == null or not _last_attack_time.has(entity_id):
		return 0.0
	return maxf(0.0, float(_last_attack_time[entity_id]) + _attack_cooldown(entity) - server_time)

## Telegraphed area attack from an NPC (2026-10-07): every living player within radius of center takes damage,
## mitigated like a normal hit. Dodging out of the ring before it lands is the counterplay.
func apply_area_damage(source_entity_id: int, center: Vector3, radius: float, damage: int, zone_id: String, server_time: float) -> Array[DamageApplied]:
	var events: Array[DamageApplied] = []
	for target in _registry.all_entities():
		if target.state.entity_type != EntityState.TYPE_PLAYER or target.state.zone_id != zone_id or target.health == null or target.health.is_dead():
			continue
		if _horizontal_distance_squared(target.state.position, center) > radius * radius:
			continue
		var event := apply_npc_hit(source_entity_id, target, damage, RpgRules.DamageType.PHYSICAL, server_time)
		if event != null:
			events.append(event)
	return events

## One NPC ability hit on one player (2026-10-10, shared by the slam and the dragons' bite / fire bolt / fire wave):
## mitigated like a normal hit (Armor for physical, Resistance for fire = environmental), once per call. The NPC
## system picks the victims (shape, range, facing, line of sight); this only applies the damage. Null if nothing landed.
func apply_npc_hit(source_entity_id: int, target: WorldEntity, damage: int, damage_type: int, server_time: float) -> DamageApplied:
	var source := _registry.get_entity(source_entity_id)
	if source == null or source.state.entity_type != EntityState.TYPE_NPC or source.health == null or source.health.is_dead():
		return null
	if target == null or target.lifecycle != WorldEntity.Lifecycle.ACTIVE or target.state.entity_type != EntityState.TYPE_PLAYER or target.health == null or target.health.is_dead():
		return null
	if target.state.zone_id != source.state.zone_id or damage <= 0:
		return null
	var loadout := EquipmentLoadout.new()
	loadout.slots = target.state.equipment.duplicate(true)
	var amount := RpgRules.mitigated_damage(target.state.class_id, loadout, damage_type, damage)
	amount = maxi(1, roundi(float(amount) * _damage_multiplier(target, server_time) * (1.0 - float(_damage_reduction.get(target.state.entity_id, 0.0)))))
	var applied := target.health.apply_damage(amount)
	if applied <= 0:
		return null
	_record_bulwark_momentum(target, server_time)
	target.sync_combat_state()
	return DamageApplied.new(source_entity_id, target.state.entity_id, applied, target.health.current_health, target.health.max_health, target.health.is_dead())

## One assault-drone shot on a mob (2026-10-15, Phase 5, docs/DRONES.md). The drone system has already picked the
## target (the owner's), checked range and line of sight, spent the round and capped the damage (DroneRules); this
## checks the pair (a live drone entity, a live NPC in the same zone) and applies the hit. The event's source is the
## drone, so clients draw the shot from it; the server credits the owner (ServerDroneSystem.credit_owner). Null if
## nothing landed.
func apply_drone_hit(drone_entity_id: int, target: WorldEntity, damage: int) -> DamageApplied:
	var drone := _registry.get_entity(drone_entity_id)
	if drone == null or drone.lifecycle != WorldEntity.Lifecycle.ACTIVE or drone.state.entity_type != EntityState.TYPE_DRONE:
		return null
	if target == null or target.lifecycle != WorldEntity.Lifecycle.ACTIVE or target.state.entity_type != EntityState.TYPE_NPC or target.health == null or target.health.is_dead():
		return null
	if target.state.zone_id != drone.state.zone_id or damage <= 0:
		return null
	var applied := target.health.apply_damage(damage)
	if applied <= 0:
		return null
	target.sync_combat_state()
	if target.health.is_dead():
		target.state.npc_state = EntityState.NPC_STATE_DEAD
		target.state.target_entity_id = 0
	return DamageApplied.new(drone_entity_id, target.state.entity_id, applied, target.health.current_health, target.health.max_health, target.health.is_dead())

## Standing mitigation for a player (shield + Shielding skill), 0..1. Set by the server when it changes.
func set_damage_reduction(entity_id: int, reduction: float) -> void:
	if reduction <= 0.0:
		_damage_reduction.erase(entity_id)
	else:
		_damage_reduction[entity_id] = clampf(reduction, 0.0, 0.9)

## Mouse aim (2026-10-05): the live NPC this attack hits along aim from source, or 0. Melee sweeps a 70° arc;
## ranged weapons hit the nearest NPC whose body lies within 0.9 m of the line of fire. Players are never
## valid targets (no friendly fire).
func find_aim_target(source_entity_id: int, aim: Vector2, weapon_definition_id: String = "", range_scale: float = 1.0) -> int:
	var source := _registry.get_entity(source_entity_id)
	if source == null or aim.length_squared() < 0.0001:
		return 0
	var direction := aim.normalized()
	var weapon := _weapon_definition(source, weapon_definition_id)
	var ranged := weapon != null and weapon.weapon_type in ["ranged", "ability"]
	var reach := _attack_range(source, weapon_definition_id) * range_scale
	var best_id := 0
	var best_score := INF
	for candidate in _registry.all_entities():
		if candidate.state.entity_type != EntityState.TYPE_NPC or candidate.state.zone_id != source.state.zone_id:
			continue
		if candidate.health == null or candidate.health.is_dead() or candidate.lifecycle != WorldEntity.Lifecycle.ACTIVE:
			continue
		var offset := Vector2(candidate.state.position.x - source.state.position.x, candidate.state.position.z - source.state.position.z)
		var distance := offset.length()
		if distance > reach + 0.4:
			continue
		var along := offset.dot(direction)
		if ranged:
			var lateral := absf(offset.cross(direction))
			if along <= 0.0 or lateral > AIM_RAY_HALF_WIDTH:
				continue
			if along < best_score:
				best_score = along
				best_id = candidate.state.entity_id
		else:
			if distance > 0.6 and along < distance * cos(deg_to_rad(AIM_MELEE_HALF_ARC_DEGREES)):
				continue
			var score := distance + (1.0 - along / maxf(distance, 0.001))
			if score < best_score:
				best_score = score
				best_id = candidate.state.entity_id
	return best_id

func clear_cooldown(source_entity_id: int) -> void:
	_last_attack_time.erase(source_entity_id)

## A ranged shot that hits nothing (2026-10-09): misses are not free. Same gate as a hit — live player source, a
## ranged weapon, the attack interval elapsed, a round in the cargo and a successful commit — then the round is
## spent and the weapon's cooldown starts. Returns {accepted, reason}; nothing is damaged.
func fire_without_target(source_entity_id: int, server_time: float, weapon_definition_id: String, ammo_available: int, ammo_commit: Callable) -> Dictionary:
	var source := _registry.get_entity(source_entity_id)
	if source == null or source.lifecycle != WorldEntity.Lifecycle.ACTIVE or source.health == null or source.health.is_dead() or source.state.entity_type != EntityState.TYPE_PLAYER:
		return _rejected("invalid_source")
	var weapon := _weapon_definition(source, weapon_definition_id)
	if weapon == null or weapon.weapon_type != "ranged":
		return _rejected("not_ranged")
	if _last_attack_time.has(source_entity_id) and server_time - _last_attack_time[source_entity_id] < _attack_cooldown(source, weapon_definition_id):
		return _rejected("cooldown")
	if ammo_available <= 0:
		return _rejected("insufficient_ammunition")
	if not ammo_commit.is_valid() or not bool(ammo_commit.call()):
		return _rejected("ammunition_commit_failed")
	_last_attack_time[source_entity_id] = server_time
	return {"accepted": true, "event": null, "reason": ""}

func activate_defense(entity_id: int, damage_multiplier: float, until_time: float) -> void:
	if not EntityId.is_valid(entity_id) or not is_finite(damage_multiplier) or damage_multiplier < 0.0 or damage_multiplier > 1.0:
		return
	var windows: Array = _defense_windows.get(entity_id, [])
	windows.append({"multiplier": damage_multiplier, "until": until_time})
	_defense_windows[entity_id] = windows

func _damage_multiplier(target: WorldEntity, server_time: float) -> float:
	var multiplier := 1.0
	var active: Array = []
	for window in _defense_windows.get(target.state.entity_id, []):
		if float(window.until) > server_time:
			active.append(window)
			multiplier = minf(multiplier, float(window.multiplier))
	if active.is_empty():
		_defense_windows.erase(target.state.entity_id)
	else:
		_defense_windows[target.state.entity_id] = active
	return multiplier

# Foundry passive Momentum (2026-10-09: every Foundry, not only the old Bulwark start): every third hit taken
# braces the Foundry (x0.65 damage taken) and allies within 5 m (x0.8) for 2 s.
func _record_bulwark_momentum(target: WorldEntity, server_time: float) -> void:
	if target.state.class_id != "class.foundry":
		return
	var hits := int(_bulwark_hits.get(target.state.entity_id, 0)) + 1
	if hits >= 3:
		_bulwark_hits[target.state.entity_id] = 0
		activate_defense(target.state.entity_id, 0.65, server_time + 2.0)
		for ally in _registry.all_entities():
			if ally.state.entity_id == target.state.entity_id or ally.state.entity_type != EntityState.TYPE_PLAYER or ally.state.zone_id != target.state.zone_id:
				continue
			if _horizontal_distance_squared(ally.state.position, target.state.position) <= 25.0:
				activate_defense(ally.state.entity_id, 0.8, server_time + 2.0)
	else:
		_bulwark_hits[target.state.entity_id] = hits

# Drift passive Trailblazer: +8 % on the target the Drift hit within the last 4 s.
func _passive_damage_percent(source: WorldEntity, target: WorldEntity, server_time: float) -> float:
	if source.state.class_id == "class.drift":
		var mark: Dictionary = _pathfinder_marks.get(source.state.entity_id, {})
		return TRAILBLAZER_PERCENT if int(mark.get("target", 0)) == target.state.entity_id and float(mark.get("expires", 0.0)) >= server_time else 0.0
	return 0.0

# Weapon-skill traits (2026-10-09; percentages since 2026-10-24, numbers in WeaponSkills): they follow the family of
# the weapon in hand, for any class.
#   Blades (skill.edge)         Heat        — chained hits within 3 s: +5 / +10 / +15 %. A fuel-fed Blades weapon (a
#                                             chainsaw) is Revved: its running chain hits at full Heat from the first cut.
#   Short Blades (skill.blades) Ambush      — +30 % after moving 2 m or more since the last hit.
#   Precision                   Range       — +15 % at 6 m or more.
#   Firearms                    Suppression — +5 % per consecutive hit on the same target within 2 s, up to +15 %.
#   Tech                        Overcharge  — +15 % while the worn cell is above half charge.
#   Blunt                       Crush       — + the weapon's armored_damage_bonus against elite and boss mobs (its
#                                             Stagger is applied after the hit lands: _stagger).
func _weapon_trait_percent(source: WorldEntity, target: WorldEntity, weapon: ItemDefinition, server_time: float) -> float:
	var family := weapon.weapon_family if weapon != null else ""
	var source_id := source.state.entity_id
	match family:
		"skill.edge":
			var heat: Dictionary = _breaker_heat.get(source_id, {"stacks": 0, "expires": 0.0})
			var stacks := int(heat.stacks) + 1 if float(heat.expires) >= server_time else 1
			stacks = HEAT_MAX_STACKS if weapon.uses_fuel() else mini(stacks, HEAT_MAX_STACKS)
			_breaker_heat[source_id] = {"stacks": stacks, "expires": server_time + WeaponSkills.HEAT_WINDOW}
			return WeaponSkills.HEAT_PERCENT_PER_STACK * float(stacks)
		"skill.precision":
			var distance := sqrt(_horizontal_distance_squared(source.state.position, target.state.position))
			return WeaponSkills.PRECISION_PERCENT if distance >= WeaponSkills.PRECISION_DISTANCE else 0.0
		"skill.blades":
			var previous: Vector3 = _infiltrator_position.get(source_id, source.state.position)
			_infiltrator_position[source_id] = source.state.position
			var moved := _horizontal_distance_squared(previous, source.state.position) >= WeaponSkills.AMBUSH_DISTANCE * WeaponSkills.AMBUSH_DISTANCE
			return WeaponSkills.AMBUSH_PERCENT if moved else 0.0
		"skill.firearms":
			var chain: Dictionary = _suppression.get(source_id, {"target": 0, "stacks": 0, "expires": 0.0})
			var same := int(chain.target) == target.state.entity_id and float(chain.expires) >= server_time
			var stacks := mini(int(chain.stacks) + 1, WeaponSkills.SUPPRESSION_MAX_STACKS) if same else 1
			_suppression[source_id] = {"target": target.state.entity_id, "stacks": stacks, "expires": server_time + WeaponSkills.SUPPRESSION_WINDOW}
			return WeaponSkills.SUPPRESSION_PERCENT_PER_STACK * float(stacks)
		"skill.tech":
			return WeaponSkills.OVERCHARGE_PERCENT if float(_energy_fraction.get(source_id, 0.0)) > WeaponSkills.OVERCHARGE_MIN_FRACTION else 0.0
		"skill.blunt":
			var tier := target.npc_definition.tier if target.npc_definition != null else "normal"
			return weapon.armored_damage_bonus() if tier in ["elite", "boss"] else 0.0
	return 0.0

# Blunt Stagger (2026-10-24): a weapon with stagger_bonus pushes the struck mob's next basic attack back by
# stagger_bonus × WeaponSkills.STAGGER_SECONDS_PER_POINT s (from now if it was ready, else from when it would have been
# ready). The mob is then immune for STAGGER_IMMUNITY s, so several hammers cannot hold it forever. Returns the delay.
func _stagger(target: WorldEntity, weapon: ItemDefinition, server_time: float) -> float:
	var delay := weapon.stagger_seconds() if weapon != null else 0.0
	var target_id := target.state.entity_id
	if delay <= 0.0 or target.state.entity_type != EntityState.TYPE_NPC or target.npc_definition == null:
		return 0.0
	if float(_stagger_immune_until.get(target_id, -INF)) > server_time:
		return 0.0
	var cooldown := _attack_cooldown(target)
	var ready_at := maxf(server_time, float(_last_attack_time.get(target_id, -INF)) + cooldown)
	_last_attack_time[target_id] = ready_at + delay - cooldown
	_stagger_immune_until[target_id] = server_time + WeaponSkills.STAGGER_IMMUNITY
	return delay

func _is_valid_combat_pair(source: WorldEntity, target: WorldEntity) -> bool:
	if source.state.entity_type == EntityState.TYPE_PLAYER:
		return target.state.entity_type == EntityState.TYPE_NPC
	if source.state.entity_type == EntityState.TYPE_NPC:
		return target.state.entity_type == EntityState.TYPE_PLAYER
	return false

func _attack_range(source: WorldEntity, weapon_definition_id: String = "") -> float:
	if source.state.entity_type == EntityState.TYPE_NPC:
		return source.npc_definition.attack_range
	var weapon := _weapon_definition(source, weapon_definition_id)
	var weapon_range := float(weapon.properties.get("attack_range", 0.0)) if weapon != null else 0.0
	return weapon_range if weapon_range > 0.0 else PLAYER_ATTACK_RANGE

func _attack_damage(source: WorldEntity, weapon_definition_id: String = "") -> int:
	if source.state.entity_type == EntityState.TYPE_NPC:
		return source.npc_definition.attack_damage
	var weapon := _weapon_definition(source, weapon_definition_id)
	if weapon == null or not [
		EquipmentLoadout.SLOT_PRIMARY_WEAPON,
		EquipmentLoadout.SLOT_SECONDARY_WEAPON,
		EquipmentLoadout.SLOT_TOOL_SPECIAL,
	].has(weapon.equipment_slot):
		return PLAYER_DAMAGE
	var profile_damage := int(weapon.properties.base_damage)
	return profile_damage if profile_damage > 0 else PLAYER_DAMAGE

func _weapon_definition(source: WorldEntity, weapon_definition_id: String) -> ItemDefinition:
	if source.state.entity_type != EntityState.TYPE_PLAYER or weapon_definition_id.is_empty():
		return null
	var weapon := ItemDefinition.load_by_id(weapon_definition_id)
	if weapon == null or weapon.equipment_slot not in [
		EquipmentLoadout.SLOT_PRIMARY_WEAPON,
		EquipmentLoadout.SLOT_SECONDARY_WEAPON,
		EquipmentLoadout.SLOT_TOOL_SPECIAL,
	]:
		return null
	return weapon

func _damage_type(damage_type_name: String) -> int:
	match damage_type_name:
		"energy":
			return RpgRules.DamageType.ENERGY
		"biological":
			return RpgRules.DamageType.BIOLOGICAL
		"environmental":
			return RpgRules.DamageType.ENVIRONMENTAL
		_:
			return RpgRules.DamageType.PHYSICAL

func _attack_cooldown(source: WorldEntity, weapon_definition_id: String = "") -> float:
	if source.state.entity_type == EntityState.TYPE_NPC:
		return source.npc_definition.attack_cooldown
	return attack_interval_for(ItemDefinition.load_by_id(weapon_definition_id) if not weapon_definition_id.is_empty() else null)

## Seconds between a player's attacks with this weapon (its attack_interval, else the 0.75 s default).
static func attack_interval_for(weapon: ItemDefinition) -> float:
	var interval := float(weapon.properties.get("attack_interval", 0.0)) if weapon != null else 0.0
	return interval if interval > 0.0 else PLAYER_ATTACK_COOLDOWN

func _horizontal_distance_squared(first: Vector3, second: Vector3) -> float:
	return Vector2(first.x - second.x, first.z - second.z).length_squared()

func _rejected(reason: String) -> Dictionary:
	return {"accepted": false, "event": null, "reason": reason}
