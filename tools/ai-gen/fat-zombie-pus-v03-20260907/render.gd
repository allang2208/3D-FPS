extends SceneTree
const OUT := "user://"
func _initialize() -> void:call_deferred("run")
func run() -> void:
	var world:=Node3D.new()
	root.add_child(world)
	current_scene=world
	var env:=WorldEnvironment.new()
	env.environment=Environment.new()
	env.environment.background_mode=Environment.BG_COLOR
	env.environment.background_color=Color(.09,.11,.14)
	env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color=Color(.8,.88,1)
	env.environment.ambient_light_energy=.45
	env.environment.sky=Sky.new()
	var sky_mat:=ProceduralSkyMaterial.new()
	sky_mat.sky_top_color=Color(.31,.40,.52)
	sky_mat.sky_horizon_color=Color(.72,.73,.69)
	sky_mat.ground_horizon_color=Color(.54,.51,.44)
	sky_mat.ground_bottom_color=Color(.12,.10,.085)
	env.environment.sky.sky_material=sky_mat
	env.environment.reflected_light_source=Environment.REFLECTION_SOURCE_SKY
	world.add_child(env)
	var light:=DirectionalLight3D.new()
	world.add_child(light)
	light.rotation_degrees=Vector3(-50,-35,0)
	light.light_energy=1.6
	light.shadow_enabled=true
	light.shadow_bias=.12
	light.shadow_normal_bias=2.0
	var reflection_light:=DirectionalLight3D.new()
	world.add_child(reflection_light)
	reflection_light.rotation_degrees=Vector3(-38,180,0)
	reflection_light.light_energy=.65
	var pools:Array[Area3D]=[]
	for i in 2:
		var terrain:=make_terrain(0)
		world.add_child(terrain)
		terrain.position=Vector3((i-.5)*2.9,0,0)
		var p:Area3D=load("res://pus_pool.gd").new()
		p.random_seed=17
		p.position=terrain.position
		world.add_child(p)


		pools.append(p)
	for tick in 150:
		await physics_frame
		var complete:=true
		for p in pools:
			if not p.surface_ready:complete=false
		if complete:break
	for p in pools:
		assert(p.surface_ready)
		p.set_physics_process(false)
		p.set_visual_age(1)
		if p==pools[0]:p._mat.shader=load("res://previous.gdshader")

	var camera:=Camera3D.new()
	world.add_child(camera)
	camera.position=Vector3(0,3.2,4.2)
	camera.look_at(Vector3.ZERO)
	camera.projection=Camera3D.PROJECTION_ORTHOGONAL
	camera.size=3.5
	camera.current=true
	DirAccess.make_dir_recursive_absolute(OUT.path_join("frames"))
	for frame in 61:
		for p in pools:p.set_visual_age(1.0+frame/20.0)
		await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(OUT.path_join("frames/%03d.png"%frame))
	root.get_texture().get_image().save_png(OUT.path_join("comparison.png"))
	print("PUS_V03_RENDER_COMPLETE old_left_new_right")
	quit()

func height_at(x:float,z:float,kind:int)->float:
	if kind==1:return x*.5
	if kind==2:return .34*sin(x*3.0)*cos(z*2.5)
	if kind==3:return .35 if x>=.18 else 0.0
	return 0.0

func make_terrain(kind:int)->StaticBody3D:
	var body:=StaticBody3D.new()
	body.collision_layer=1
	var st:=SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for x in 30:
		for z in 30:
			var x0:float=(x-15)*.09
			var z0:float=(z-15)*.09
			if kind==4 and x0>=.18:continue
			for point in [Vector2(x0,z0),Vector2(x0+.09,z0),Vector2(x0+.09,z0+.09),Vector2(x0,z0),Vector2(x0+.09,z0+.09),Vector2(x0,z0+.09)]:
				st.add_vertex(Vector3(point.x,(.35 if x0>=.18 else 0.0) if kind==3 else height_at(point.x,point.y,kind),point.y))
	if kind==5:
		for point in [Vector2(-1.35,-1.35),Vector2(1.35,-1.35),Vector2(1.35,1.35),Vector2(-1.35,-1.35),Vector2(1.35,1.35),Vector2(-1.35,1.35)]:
			st.add_vertex(Vector3(point.x,-1,point.y))
	st.generate_normals()
	var mesh:=MeshInstance3D.new()
	mesh.mesh=st.commit()
	var mat:=StandardMaterial3D.new()
	mat.albedo_color=Color(.28,.26,.23)
	mat.cull_mode=BaseMaterial3D.CULL_DISABLED
	mesh.material_override=mat
	body.add_child(mesh)
	var collision:=CollisionShape3D.new()
	collision.shape=mesh.mesh.create_trimesh_shape()
	body.add_child(collision)
	return body
