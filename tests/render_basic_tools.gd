extends SceneTree
var frames:=0
func _initialize() -> void:
	call_deferred("start")
func start() -> void:
	var hud: Node=root.get_node("HUD")
	hud.set_process(false)
	for child in hud.get_children():
		if child is CanvasLayer: child.hide()
	var scene:=Node3D.new()
	root.add_child(scene)
	current_scene=scene
	var environment:=WorldEnvironment.new()
	environment.environment=Environment.new()
	environment.environment.background_mode=Environment.BG_COLOR
	environment.environment.background_color=Color("202a32")
	environment.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
	environment.environment.ambient_light_color=Color("b5c5d1")
	environment.environment.ambient_light_energy=0.6
	scene.add_child(environment)
	var light:=DirectionalLight3D.new()
	light.rotation_degrees=Vector3(-35,-25,0)
	light.light_energy=2
	scene.add_child(light)
	for kind in ["axe","pickaxe"]:
		var model: Node3D=load("res://assets/models/basic_tools/"+kind+"_v1.glb").instantiate()
		scene.add_child(model)
		model.position=Vector3(-0.48 if kind=="axe" else 0.48,0,0)
		model.rotation_degrees.y=-15
	var cam:=Camera3D.new()
	scene.add_child(cam)
	cam.position=Vector3(0,0.6,2.5)
	cam.look_at(Vector3(0,0.25,0))
	cam.projection=Camera3D.PROJECTION_ORTHOGONAL
	cam.size=1.9
	cam.current=true

func _process(_delta: float) -> bool:
	frames+=1
	if frames==30:
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("E:/3d/3-dfps/tools/basic-tools/tools-preview.png")
		quit()
	return false
