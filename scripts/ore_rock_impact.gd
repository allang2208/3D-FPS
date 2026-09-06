@static_unload
extends Node3D
## Short radial dust burst, heavier ballistic chips, then a fading rising cloud.

const LIFETIME := 1.1
var elapsed := 0.0
var dust: Array[MeshInstance3D] = []
var chips: Array[MeshInstance3D] = []
static var dust_shader: Shader

func _ready() -> void:
	add_to_group("ore_impact_fx")
	if not dust_shader:
		dust_shader = Shader.new()
		dust_shader.code = """shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never;
uniform float opacity = 1.0;
void vertex() {
    MODELVIEW_MATRIX = VIEW_MATRIX * mat4(INV_VIEW_MATRIX[0], INV_VIEW_MATRIX[1], INV_VIEW_MATRIX[2], MODEL_MATRIX[3]);
    MODELVIEW_MATRIX[0] *= length(MODEL_MATRIX[0].xyz);
    MODELVIEW_MATRIX[1] *= length(MODEL_MATRIX[1].xyz);
}
void fragment() {
    vec2 p = UV - vec2(0.5);
    float noise = 0.75 + 0.25 * sin(UV.x * 29.0 + sin(UV.y * 31.0) * 2.0) * sin(UV.y * 23.0);
    float edge = 1.0 - smoothstep(0.08, 0.48, length(p) + (1.0-noise)*0.09);
    ALBEDO = vec3(0.43, 0.37, 0.31) * (0.85 + noise * 0.15);
    ALPHA = edge * edge * opacity;
}"""
	for i in 18:
		var puff := MeshInstance3D.new()
		var quad := QuadMesh.new()
		quad.size = Vector2.ONE
		puff.mesh = quad
		var mat := ShaderMaterial.new()
		mat.shader = dust_shader
		puff.material_override = mat
		puff.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(puff)
		dust.append(puff)
	for i in 12:
		var chip: MeshInstance3D = load("res://scripts/ore_crystal_projectile.gd").make_crystal()
		chip.scale = Vector3.ONE * (.13 + .04 * (i % 4))
		add_child(chip)
		chips.append(chip)
	update_visuals()

func _process(delta: float) -> void:
	elapsed += delta
	if elapsed >= LIFETIME:
		queue_free()
		return
	update_visuals()

func update_visuals() -> void:
	var t := elapsed
	for i in dust.size():
		var low := i < 12
		var angle := i * 2.39996
		var spread := (1.0 - exp(-t * 8.0)) * (1.25 if low else .48)
		var height := .12 + t * (.16 if low else .85)
		dust[i].position = Vector3(cos(angle) * spread, height, sin(angle) * spread)
		var size := (.85 if low else .95) + t * (1.1 if low else 1.4)
		dust[i].scale = Vector3(size, size * (.65 if low else .95), size)
		var mat := dust[i].material_override as ShaderMaterial
		mat.set_shader_parameter("opacity", (.95 if low else .85) * (1.0 - smoothstep(.16, LIFETIME, t)))
	for i in chips.size():
		var angle := i * 2.39996
		var speed := 1.25 + .22 * (i % 5)
		var height := .09 + (1.9 + .3 * (i % 3)) * t - 4.9 * t * t
		var stop := minf(t, .46 + .05 * (i % 3))
		chips[i].position = Vector3(cos(angle) * speed * stop, maxf(.035, height), sin(angle) * speed * stop)
		chips[i].rotation = Vector3(stop * (5+i), stop * 4, float(i))
		chips[i].scale = Vector3.ONE * (.13 + .04 * (i % 4)) * (1.0 - smoothstep(.65, LIFETIME, t))
