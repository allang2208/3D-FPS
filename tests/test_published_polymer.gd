extends SceneTree
## Run in a minimal project with the helper and both shaders copied at their res:// paths.
const Finish = preload("res://scripts/rifle_polymer_finish.gd")
class Model extends Node3D:
	var model_resource := Resource.new()
	var skeleton := Skeleton3D.new()

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var model := Model.new()
	model.model_resource.take_over_path("res://infima_ar.glb")
	root.add_child(model)
	model.add_child(model.skeleton)
	for label in ["RearSight", "FrontSight", "SOCKET_Muzzle"]:
		model.skeleton.add_bone(label)
	model.skeleton.set_bone_rest(1,Transform3D(Basis.IDENTITY,Vector3(0,0,-.4)))
	model.skeleton.set_bone_rest(2,Transform3D(Basis.IDENTITY,Vector3(0,-.05,-.5)))
	var body := MeshInstance3D.new()
	body.name = "SM_AR_receiver"
	var box := BoxMesh.new()
	box.size = Vector3(.3,.2,.8)
	var source := StandardMaterial3D.new()
	source.metallic_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_BLUE
	box.material = source
	var source_mesh := ArrayMesh.new()
	source_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,box.surface_get_arrays(0))
	source_mesh.surface_set_material(0,source)
	body.mesh = source_mesh
	model.add_child(body)
	var original := box.surface_get_arrays(0)
	var part := Node3D.new()
	model.add_child(part)
	var housing := MeshInstance3D.new()
	housing.name = "optic_housing"
	housing.mesh = BoxMesh.new()
	housing.mesh.size = Vector3(.2,.2,.2)
	housing.position = Vector3(.6,0,0)
	housing.material_override = StandardMaterial3D.new()
	part.add_child(housing)
	var lens := MeshInstance3D.new()
	lens.mesh = BoxMesh.new()
	lens.mesh.size = Vector3(.2,.2,.02)
	lens.position = Vector3(.6,.3,0)
	var glass := StandardMaterial3D.new()
	glass.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	lens.material_override = glass
	part.add_child(lens)
	Finish.apply(model,{"optic":part})
	var painted := body.mesh
	var material := body.get_active_material(0)
	assert(material is ShaderMaterial)
	assert(material.get_shader_parameter("region_channel") == Vector4(0,0,1,0))
	assert(housing.material_override is ShaderMaterial)
	assert(lens.material_override == glass)
	for channel in [Mesh.ARRAY_VERTEX,Mesh.ARRAY_NORMAL,Mesh.ARRAY_TEX_UV,Mesh.ARRAY_INDEX]:
		assert(original[channel] == painted.surface_get_arrays(0)[channel])
	Finish.apply(model,{"optic":part})
	assert(body.mesh == painted and body.get_active_material(0) == material)
	assert(Finish.rifle_id(model) == "infima_ar")
	var camera := Camera3D.new()
	root.add_child(camera)
	camera.position = Vector3(1,.6,2)
	camera.look_at(Vector3.ZERO)
	var light := DirectionalLight3D.new()
	root.add_child(light)
	light.rotation_degrees = Vector3(-30,-35,0)
	var classic := MeshInstance3D.new()
	classic.mesh = SphereMesh.new()
	classic.position.x = -.6
	var classic_material := ShaderMaterial.new()
	classic_material.shader = load("res://assets/materials/akm_clean_polymer.gdshader")
	classic.material_override = classic_material
	root.add_child(classic)
	for frame in 12: await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("user://polymer-support.png")
	print("PASS polymer support: geometry, channels, repeated apply, housing, glass; both shaders rendered")
	model.queue_free(); classic.queue_free(); camera.queue_free(); light.queue_free()
	await process_frame
	quit()
