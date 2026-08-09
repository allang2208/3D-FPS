extends Area3D
## 友好 NPC 交互（旷野/基地共用）：立绘 billboard + 名字 + 按 E 对话提示。
## 用法：var n = load("res://scripts/npc_interact.gd").new()
##       n.setup(npc_data)   # {name, npc_type, portrait, greetings, ...}
##       n.interacted.connect(func(data): ...)
##       add_child(n)
## 触发：玩家（name == "Player"）进入范围后按 E -> interacted.emit(data)。

signal interacted(data: Dictionary)

var _data := {}
var _player_near: Node3D
var _e_prev := false

var _sprite: Sprite3D
var _name_label: Label3D
var _prompt: Label3D

func setup(data: Dictionary) -> void:
	_data = data
	if is_node_ready():
		_refresh_visual()

func _ready() -> void:
	collision_mask = 0xFFFFFFFF
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)
	_build_visual()
	_refresh_visual()

func _process(_delta: float) -> void:
	var pressed := _player_near != null and Input.is_key_pressed(KEY_E)
	if pressed and not _e_prev:
		if _prompt != null:
			_prompt.text = "对话中…"
		interacted.emit(_data.duplicate(true))
	_e_prev = pressed

func _build_visual() -> void:
	var col := CollisionShape3D.new()
	col.name = "Collision"
	var shape := CylinderShape3D.new()
	shape.radius = 1.8
	shape.height = 3.4
	col.shape = shape
	add_child(col)

	_sprite = Sprite3D.new()
	_sprite.name = "Portrait"
	_sprite.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	_sprite.pixel_size = 0.002
	_sprite.position = Vector3(0, 1.3, 0)
	add_child(_sprite)

	_name_label = Label3D.new()
	_name_label.name = "Name"
	_name_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	_name_label.position = Vector3(0, 2.25, 0)
	_name_label.font_size = 56
	_name_label.outline_size = 10
	_name_label.modulate = Color(1.0, 0.85, 0.4)
	add_child(_name_label)

	_prompt = Label3D.new()
	_prompt.name = "Prompt"
	_prompt.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	_prompt.position = Vector3(0, 2.85, 0)
	_prompt.font_size = 42
	_prompt.outline_size = 8
	_prompt.visible = false
	add_child(_prompt)

func _refresh_visual() -> void:
	var portrait := String(_data.get("portrait", ""))
	if portrait != "" and ResourceLoader.exists(portrait):
		_sprite.texture = load(portrait)
	else:
		_sprite.texture = null
	_name_label.text = String(_data.get("name", "NPC"))

func _on_body_entered(body: Node3D) -> void:
	if body is CharacterBody3D and body.name == "Player":
		_player_near = body
		if _prompt != null:
			_prompt.text = "按 E 对话"
			_prompt.visible = true

func _on_body_exited(body: Node3D) -> void:
	if body == _player_near:
		_player_near = null
		if _prompt != null:
			_prompt.visible = false
