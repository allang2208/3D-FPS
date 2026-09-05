extends Node3D
## An inventory instance on the ground, with the original item icon.
var record: Dictionary
var inventory_host: Node
var _label: Label3D

func _ready() -> void:
	var item: Dictionary = record.item
	var sprite := Sprite3D.new()
	var path := str(item.get("icon", ""))
	if ResourceLoader.exists(path):
		sprite.texture = load(path)
		sprite.pixel_size = 0.35 / maxf(1, sprite.texture.get_width())
	sprite.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	sprite.position.y = 0.3
	add_child(sprite)
	_label = Label3D.new()
	_label.text = "%s × %d\n[F] 拾取" % [item.get("name", "物品"), int(item.get("stack", 1))]
	_label.font_size = 32
	_label.pixel_size = 0.004
	_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	_label.position.y = 0.65
	add_child(_label)

func _process(_delta: float) -> void:
	var player: Node3D = inventory_host._bound_player
	_label.visible = is_instance_valid(player) and player.global_position.distance_to(global_position) < 2.5

func _unhandled_input(event: InputEvent) -> void:
	if _label.visible and event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_F:
		get_viewport().set_input_as_handled()
		if inventory_host.pickup_inventory_item(record):
			queue_free()
