extends CharacterBody3D
## 第一人称控制器：WASD 移动 + 鼠标视角 + 空格跳 + Shift 疾跑 + Esc 释放鼠标
## 持有 BuffSystem（旧版 damageable-entity 状态系统）：受击修正 / DoT / HoT / 移速倍率

signal damaged(hp: int)
signal died
signal healed(hp: int)

const BuffSystemScript := preload("res://scripts/buff_system.gd")

@export var walk_speed := 5.0
@export var sprint_speed := 8.5
@export var jump_velocity := 4.8
@export var mouse_sensitivity := 0.0022
@export var max_hp := 100

const GRAVITY := 18.0

var hp := 100
var is_dead := false
var _buffs: BuffSystem = BuffSystem.new()

func _ready() -> void:
	_disable_player_shadows(self)
	get_tree().node_added.connect(_on_player_visual_added)
	hp = max_hp
	_buffs = BuffSystem.new()
	collision_layer = 4
	collision_mask = 5  # 1 墙体 + 2 敌人
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _disable_player_shadows(node: Node) -> void:
	if node is GeometryInstance3D:
		node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	for child in node.get_children():
		_disable_player_shadows(child)

func _on_player_visual_added(node: Node) -> void:
	# Also cover weapons and attachments installed after the player is ready.
	if node is GeometryInstance3D and is_ancestor_of(node):
		node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

func take_damage(d: int, damage_type := "physical", _src: Node3D = null) -> void:
	if is_dead:
		return
	var final_d := maxi(1, floori(d * _buffs.incoming_damage_mul(damage_type)))
	hp = maxi(0, hp - final_d)
	damaged.emit(hp)
	if hp <= 0:
		is_dead = true
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		died.emit()

## 恢复生命（背包药水使用；加法式接口，不改动既有契约）
func heal(amount: int) -> void:
	if is_dead or amount <= 0:
		return
	var before := hp
	hp = mini(max_hp, hp + amount)
	if hp != before:
		healed.emit(hp)

## 通用状态入口（技能/物品给玩家挂 buff 用，如灼锋焰甲）
func apply_buff(type: String, duration_ms: int, opts := {}) -> void:
	if is_dead:
		return
	_buffs.add(type, duration_ms, opts)

func has_buff(type: String) -> bool:
	return _buffs.has(type)

func buff_snapshot() -> Array[Dictionary]:
	return _buffs.effect_snapshot()

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		rotate_y(-event.relative.x * mouse_sensitivity)
		var cam := get_node_or_null("Camera3D") as Camera3D
		if cam:
			cam.rotate_x(-event.relative.y * mouse_sensitivity)
			cam.rotation.x = clampf(cam.rotation.x, -1.45, 1.45)
	elif event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	elif event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _physics_process(delta: float) -> void:
	_buffs.tick(delta, self)
	if not is_on_floor():
		velocity.y -= GRAVITY * delta
	if Input.is_key_pressed(KEY_SPACE) and is_on_floor():
		velocity.y = jump_velocity
	var input := Vector3(
		float(Input.is_key_pressed(KEY_D)) - float(Input.is_key_pressed(KEY_A)),
		0.0,
		float(Input.is_key_pressed(KEY_S)) - float(Input.is_key_pressed(KEY_W))
	)
	if input.length() > 1.0:
		input = input.normalized()
	var spd := (sprint_speed if Input.is_key_pressed(KEY_SHIFT) else walk_speed) * _buffs.speed_mul()
	var dir := (transform.basis * input).normalized()
	velocity.x = dir.x * spd
	velocity.z = dir.z * spd
	move_and_slide()
