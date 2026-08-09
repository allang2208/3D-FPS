extends CharacterBody3D
## 通用敌人：追击玩家 / 远处游荡 / 受击闪红 / 接触伤害 / 死亡倒地重生
## 子节点约定：Collision（CollisionShape3D）+ Model（GLB 或代码拼装，名字以 Leg 开头的子节点会摆动）
## 部位命中盒：_ready 自动从模型骨骼（head）生成 HitboxHead（×2），射线按 shape 索引结算

const HitboxShapeScript := preload("res://scripts/hitbox_shape.gd")

@export var max_hp := 50
@export var chase_speed := 3.0
@export var wander_speed := 1.2
@export var contact_damage := 10
@export var attack_cd := 0.8
@export var model_offset_y := 0.0
@export var walk_bob_amp := 0.03
@export var walk_bob_speed := 14.0

const CHASE_DIST := 14.0
const RESPAWN_TIME := 3.0

var _player: Node3D
var _kill_cb: Callable
var _model: Node3D
var _rig: Node3D  # 带骨骼动画的模型（有 rig_update 方法，如黑狼 WolfRig）
var _rig_t := 0.0
var _mat: StandardMaterial3D
var _legs: Array[Node3D] = []
var _hp: int
var _dead := false
var _dead_t := 0.0
var _walk_t := 0.0
var _moving := false
var _flash_t := 0.0
var _lunge_t := 0.0
var _attack_t := 0.0
var _wander_target := Vector3.ZERO
var _wander_timer := 0.0
var _shape_multipliers: Array[float] = []
var _stun_t := 0.0
var _electrified_stacks := 0
var _electrified_t := 0.0
var _overload_matk := 0
var _overload_intt := 0
var _knock_vel := Vector3.ZERO
static var _dot_tex: Texture2D

func setup(player: Node3D, kill_cb: Callable) -> void:
	_player = player
	_kill_cb = kill_cb
	_hp = max_hp

func _ready() -> void:
	collision_layer = 2
	collision_mask = 5  # 1 墙体 + 4 玩家
	for child in get_children():
		if child is Node3D and not (child is CollisionShape3D) and child.name != "Collision":
			_model = child
			_find_material(child)
			for c in child.get_children():
				if c.name.begins_with("Leg"):
					_legs.append(c)
	_wander_target = global_position
	if _model != null and _model.has_method("rig_update"):
		_rig = _model
	_build_head_hitbox()
	_rebuild_shape_multipliers()

func _find_material(n: Node) -> void:
	if n is MeshInstance3D and n.mesh and n.mesh.get_surface_count() > 0:
		var m := n.get_active_material(0) as StandardMaterial3D
		if m:
			_mat = m
	for c in n.get_children():
		_find_material(c)

# ---------- 部位命中盒（Hitbox） ----------

## 生成头部命中球（×2）：优先锚定模型骨骼 head，无骨骼时退化为碰撞盒顶端
func _build_head_hitbox() -> void:
	var col := get_node_or_null("Collision") as CollisionShape3D
	if col == null or not (col.shape is CapsuleShape3D):
		return
	var head_local := _find_head_local()
	if head_local == Vector3.ZERO:
		return
	var hb := CollisionShape3D.new()
	hb.name = "HitboxHead"
	hb.set_script(HitboxShapeScript)
	var sphere := SphereShape3D.new()
	sphere.radius = 0.22
	hb.shape = sphere
	hb.position = head_local
	hb.multiplier = 2.0
	add_child(hb)

## 头部本地坐标（模型骨骼 head 绑定姿势；无骨骼时取碰撞盒顶端）
func _find_head_local() -> Vector3:
	var skel := _find_skeleton(_model)
	if skel:
		var head_idx := skel.find_bone("head")
		if head_idx < 0:
			for b in skel.get_bone_count():
				if skel.get_bone_name(b).to_lower().contains("head"):
					head_idx = b
					break
		if head_idx >= 0:
			var rest: Transform3D = skel.get_bone_global_rest(head_idx)
			return to_local(skel.to_global(rest.origin))
	var col := get_node_or_null("Collision") as CollisionShape3D
	if col and col.shape is CapsuleShape3D:
		var cap := col.shape as CapsuleShape3D
		return col.position + Vector3(0, cap.height * 0.5 - 0.18, 0)
	return Vector3.ZERO

func _find_skeleton(n: Node) -> Skeleton3D:
	if n == null:
		return null
	if n is Skeleton3D:
		return n
	for c in n.get_children():
		var r := _find_skeleton(c)
		if r:
			return r
	return null

## 按 shape 索引建立倍率表（Collision 躯干=1.0，HitboxHead=2.0）
func _rebuild_shape_multipliers() -> void:
	_shape_multipliers = []
	for c in get_children():
		if c is CollisionShape3D:
			var m := 1.0
			if c.get_script() == HitboxShapeScript:
				m = c.multiplier
			_shape_multipliers.append(m)

## 射线命中回调：按命中 shape 返回伤害倍率
func get_shape_multiplier(shape_idx: int) -> float:
	if shape_idx >= 0 and shape_idx < _shape_multipliers.size():
		return _shape_multipliers[shape_idx]
	return 1.0

## 测试/调试：头部命中盒全局坐标
func get_head_center_global() -> Vector3:
	var hb := get_node_or_null("HitboxHead") as CollisionShape3D
	if hb:
		return hb.global_position
	return Vector3.ZERO

func take_damage(d: int, damage_type := "physical", _src: Node3D = null) -> bool:
	if _dead:
		return false
	var final_d := d
	# 感电：电系伤害每层 +3%（旧版 damageable-entity）
	if damage_type == "electric" and _electrified_stacks > 0:
		final_d = maxi(1, floori(final_d * (1.0 + _electrified_stacks * 0.03)))
	_hp -= final_d
	_flash_t = 0.12
	if _hp <= 0:
		_die()
		return true
	return false

## 眩晕（旧版 applyStun）：冻结 AI、打断攻击动作；眩晕期间静止
func apply_stun(duration_ms: int) -> void:
	if _dead:
		return
	_stun_t = maxf(_stun_t, duration_ms / 1000.0)
	_attack_t = 0.0
	_lunge_t = 0.0
	_moving = false
	velocity = Vector3.ZERO

## 感电（旧版 applyElectrified）：叠加层数与时长，叠满 5 层触发过载
func apply_electrified(stacks: int, duration_ms: int, matk: int = 0, intt: int = 0) -> void:
	if _dead:
		return
	_overload_matk = matk
	_overload_intt = intt
	_electrified_stacks += stacks
	_electrified_t += duration_ms / 1000.0
	if _electrified_stacks >= 5:
		_electrified_stacks = 0
		_electrified_t = 0.0
		_trigger_overload()

## 击退（旧版 applyKnockback）：沿方向短程位移，速度随时间衰减
func apply_knockback(dir: Vector3, dist_m: float) -> void:
	if _dead:
		return
	if dir.length_squared() < 0.0001:
		return
	_knock_vel = dir.normalized() * clampf(dist_m * 6.0, 1.0, 12.0)

## 过载（旧版 _triggerElectrifiedOverload）：眩晕 1.2s + 对周围 150px 敌人电击传导
func _trigger_overload() -> void:
	apply_stun(1200)
	var dmg := maxi(1, floori(20.0 + _overload_matk * 1.2 + _overload_intt * 1.2))
	var scene_root: Node = get_tree().current_scene
	if scene_root == null:
		scene_root = get_parent()
	if scene_root == null:
		return
	var radius := 150.0 * 0.014  # 2.1m
	for c in scene_root.get_children():
		if c == null or c == self or not c.has_method("take_damage") or String(c.name) == "Player":
			continue
		if (c.global_position - global_position).length() > radius:
			continue
		_spawn_overload_bolt(c)
		c.take_damage(dmg, "electric")

func _die() -> void:
	_dead = true
	_dead_t = 0.0
	collision_layer = 0
	if _kill_cb.is_valid():
		_kill_cb.call()

func _physics_process(delta: float) -> void:
	_flash_t = maxf(0.0, _flash_t - delta)
	if _mat:
		if _flash_t > 0.0:
			_mat.emission_enabled = true
			_mat.emission = Color(1.0, 0.25, 0.2)
		elif _electrified_t > 0.0 and _electrified_stacks > 0:
			_mat.emission_enabled = true
			_mat.emission = Color(0.45, 0.35, 1.0) * (0.35 + 0.65 * absf(sin(_walk_t * 18.0)))
		else:
			_mat.emission_enabled = false
	if _dead:
		_dead_t += delta
		if _model and _model.get("no_death_flip") != true:
			_model.rotation.x = minf(PI / 2, _model.rotation.x + delta * 2.5)
			_model.position.y = maxf(0.0, _model.position.y - delta * 0.4)
		if _rig:
			_rig.rig_update(_dead_t, false, 0.0, true)
		if _dead_t >= RESPAWN_TIME:
			_respawn()
		return
	if _electrified_t > 0.0:
		_electrified_t -= delta
		if _electrified_t <= 0.0:
			_electrified_t = 0.0
			_electrified_stacks = 0
	if _stun_t > 0.0:
		_stun_t -= delta
		_moving = false
		velocity = Vector3.ZERO
		if _model:
			_model.position.y = model_offset_y
		return
	if _knock_vel.length_squared() > 0.01:
		velocity = _knock_vel
		move_and_slide()
		_knock_vel = _knock_vel.lerp(Vector3.ZERO, 8.0 * delta)
		if _knock_vel.length() < 0.15:
			_knock_vel = Vector3.ZERO
		return
	if _player == null:
		return
	_lunge_t = maxf(0.0, _lunge_t - delta)
	if _lunge_t > 0.0 and _model and _rig == null:
		_model.rotation.x = 0.3 * (_lunge_t / 0.25)
	_attack_t = maxf(0.0, _attack_t - delta)
	_contact_attack()
	var to_player := _player.global_position - global_position
	var dist := Vector2(to_player.x, to_player.z).length()
	if dist > CHASE_DIST:
		_wander(delta)
	else:
		_chase(delta, to_player, dist)
	_walk_t += delta
	_swing_legs()
	_idle_breath()
	if _rig:
		# 步频随实际移速缩放，减少滑步（约 3.3 rad/s 每 m/s，待机 4.0）
		var spd := Vector2(velocity.x, velocity.z).length()
		_rig_t += delta * (clampf(spd * 3.3, 4.0, 14.0) if _moving else 4.0)
		_rig.rig_update(_rig_t, _moving, _lunge_t, false, dist <= CHASE_DIST)

func _contact_attack() -> void:
	if _attack_t > 0.0 or _player == null or not _player.has_method("take_damage"):
		return
	var to_p := _player.global_position - global_position
	if Vector2(to_p.x, to_p.z).length() < 1.4:
		_attack_t = attack_cd
		_lunge_t = 0.25
		_player.take_damage(contact_damage)

func _chase(delta: float, to_player: Vector3, dist: float) -> void:
	_moving = true
	var dir := Vector3(to_player.x, 0, to_player.z)
	if dist > 0.01:
		dir = dir.normalized()
	velocity.x = dir.x * chase_speed
	velocity.z = dir.z * chase_speed
	_turn_to(dir, delta)
	move_and_slide()
	if _model:
		_model.position.y = model_offset_y + absf(sin(_walk_t * walk_bob_speed)) * walk_bob_amp

func _wander(delta: float) -> void:
	_wander_timer -= delta
	if _wander_timer <= 0.0 or global_position.distance_to(_wander_target) < 0.8:
		_wander_timer = 3.0 + randf() * 3.0
		_wander_target = Vector3(randf_range(-11.0, 11.0), 0, randf_range(-11.0, 11.0))
	var to_t := _wander_target - global_position
	var dist := Vector2(to_t.x, to_t.z).length()
	if dist < 0.4:
		_moving = false
		velocity.x = 0
		velocity.z = 0
	else:
		_moving = true
		var dir := Vector3(to_t.x, 0, to_t.z).normalized()
		velocity.x = dir.x * wander_speed
		velocity.z = dir.z * wander_speed
		_turn_to(dir, delta)
		if _model:
			_model.position.y = model_offset_y + absf(sin(_walk_t * walk_bob_speed * 0.6)) * walk_bob_amp * 0.6
	move_and_slide()

func _turn_to(dir: Vector3, delta: float) -> void:
	var yaw := atan2(dir.x, dir.z)
	rotation.y = lerp_angle(rotation.y, yaw, 8.0 * delta)

func _swing_legs() -> void:
	if _legs.is_empty():
		return
	var amp := 0.4 if _moving else 0.0
	for i in _legs.size():
		_legs[i].rotation.x = sin(_walk_t * walk_bob_speed * 0.7 + float(i) * PI) * amp * 0.4

func _idle_breath() -> void:
	if _moving or _model == null:
		return
	_model.position.y = model_offset_y + sin(_walk_t * 2.2) * 0.02

func _respawn() -> void:
	_hp = max_hp
	_dead = false
	_dead_t = 0.0
	_moving = false
	_stun_t = 0.0
	_electrified_stacks = 0
	_electrified_t = 0.0
	collision_layer = 2
	velocity = Vector3.ZERO
	global_position = Vector3(randf_range(-11.0, 11.0), 0, randf_range(-11.0, 11.0))
	_rig_t = 0.0
	if _rig:
		_rig.rig_reset()
	if _model:
		_model.rotation.x = 0.0
		_model.position.y = model_offset_y
		for l in _legs:
			l.rotation.x = 0.0

## 过载传导细闪电（旧版 uniform 细闪电 widthScale 0.45）：紫辉光 + 白芯
func _spawn_overload_bolt(target: Node3D) -> void:
	var node := Node3D.new()
	var scene_root: Node = get_tree().current_scene
	if scene_root == null:
		scene_root = get_parent()
	if scene_root == null:
		return
	scene_root.add_child(node)
	node.position = global_position + Vector3(0, 1.0, 0)
	var to := target.global_position + Vector3(0, 0.8, 0) - node.position
	var dist := to.length()
	if dist < 0.001:
		node.queue_free()
		return
	var n := to.cross(Vector3.UP)
	if n.length() < 0.001:
		n = Vector3.RIGHT
	n = n.normalized()
	var segs := 8
	var amp := maxf(0.12, dist * 0.11)
	var pts: Array = [Vector3.ZERO]
	for i in range(1, segs):
		var t := float(i) / float(segs)
		pts.append(to * t + n * (randf() * 2.0 - 1.0) * amp)
	pts.append(to)
	var dots: Array = []
	for i in range(pts.size() - 1):
		var a: Vector3 = pts[i]
		var b: Vector3 = pts[i + 1]
		for j in range(1, 5):
			var t := float(j) / 5.0
			var p := a.lerp(b, t)
			dots.append(_dot_sprite(node, p, 0.05, Color(0x6a / 255.0, 0x4b / 255.0, 1.0, 0.4)))
			dots.append(_dot_sprite(node, p, 0.028, Color(0xdc / 255.0, 0xd6 / 255.0, 1.0, 0.9)))
	var tw := node.create_tween()
	tw.tween_interval(0.2)
	tw.tween_method(func(v: float) -> void:
		for d in dots:
			var m := (d as Sprite3D).material_override as StandardMaterial3D
			var c2: Color = m.albedo_color
			c2.a = c2.a * v
			m.albedo_color = c2
		, 1.0, 0.0, 0.18)
	tw.tween_callback(func() -> void: node.queue_free())

func _dot_sprite(parent: Node3D, local_pos: Vector3, radius: float, color: Color) -> Sprite3D:
	if _dot_tex == null:
		var size := 64
		var img := Image.create(size, size, false, Image.FORMAT_RGBA8)
		for y in size:
			for x in size:
				var dx := (x + 0.5) / size * 2.0 - 1.0
				var dy := (y + 0.5) / size * 2.0 - 1.0
				var d := sqrt(dx * dx + dy * dy)
				var a := clampf(1.0 - d, 0.0, 1.0)
				img.set_pixel(x, y, Color(1, 1, 1, a * a))
		_dot_tex = ImageTexture.create_from_image(img)
	var sp := Sprite3D.new()
	sp.texture = _dot_tex
	sp.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	sp.pixel_size = 0.0025
	sp.position = local_pos
	sp.scale = Vector3.ONE * maxf(0.01, radius / 0.16)
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	m.albedo_texture = _dot_tex
	m.albedo_color = color
	sp.material_override = m
	parent.add_child(sp)
	return sp
