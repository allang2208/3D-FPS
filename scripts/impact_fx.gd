class_name ImpactFx
extends Node3D
## 命中火花：一次性粒子爆发，随后自毁

const LIFETIME := 0.5

static func spawn(scene_root: Node, pos: Vector3, normal: Vector3, color := Color(1.0, 0.75, 0.4)) -> void:
	var fx := ImpactFx.new()
	scene_root.add_child(fx)
	fx.global_position = pos
	var p := CPUParticles3D.new()
	p.one_shot = true
	p.emitting = true
	p.amount = 14
	p.lifetime = 0.35
	p.explosiveness = 0.9
	p.direction = normal
	p.spread = 45.0
	p.gravity = Vector3(0, -6, 0)
	p.initial_velocity_min = 2.0
	p.initial_velocity_max = 4.5
	p.scale_amount_min = 0.02
	p.scale_amount_max = 0.05
	p.color = color
	fx.add_child(p)
	fx.get_tree().create_timer(LIFETIME).timeout.connect(fx.queue_free)
