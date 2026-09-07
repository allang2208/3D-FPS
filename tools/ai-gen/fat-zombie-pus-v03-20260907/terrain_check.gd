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
	env.environment.ambient_light_energy=.7
	world.add_child(env)
	var light:=DirectionalLight3D.new()
	world.add_child(light)
	light.rotation_degrees=Vector3(-50,-35,0)
	light.light_energy=1.6
	light.shadow_enabled=true
	light.shadow_bias=.12
	light.shadow_normal_bias=2.0
	var pools:Array[Area3D]=[]
	for i in 6:
		var terrain:=make_terrain(i)
		world.add_child(terrain)
		terrain.position=Vector3((i%3-1)*3.0,0,(i/3)*3.2)
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

	var camera:=Camera3D.new()
	world.add_child(camera)
	camera.position=Vector3(0,6.5,8.5)
	camera.look_at(Vector3(0,0,1.4))
	camera.projection=Camera3D.PROJECTION_ORTHOGONAL
	camera.size=6.8
	camera.current=true
	DirAccess.make_dir_recursive_absolute(OUT.path_join("terrain-frames"))
	var report:={}
	for i in 6:
		var p:Area3D=pools[i]
		var gap:=0.0
		var penetration:=0.0
		var missed:=0
		# Check vertices and triangle interiors against the real collision surface.
		for tri in p._triangles:
			var a:Vector3=p._samples[tri.x];var b:Vector3=p._samples[tri.y];var c:Vector3=p._samples[tri.z]
			for v in [a,b,c,(a+b+c)/3.0]:
				var pos:Vector3=p.to_global(v)
				var query:=PhysicsRayQueryParameters3D.create(pos+Vector3.UP*.1,pos-Vector3.UP*.2,1)
				var hit:=world.get_world_3d().direct_space_state.intersect_ray(query)
				assert(not hit.is_empty(),"mesh spanning a hole")
				var error:float=pos.y+.01-hit.position.y
				gap=maxf(gap,error);penetration=maxf(penetration,-error)
				if not p.contains_point(hit.position):missed+=1
		assert(gap<.022 and penetration<.002,"surface clearance")
		assert(missed==0,"damage surface differs")
		if i==3:assert(not p.contains_point(p.position+Vector3(.5,.35,0)),"step clipped")
		if i==4:assert(not p.contains_point(p.position+Vector3(.5,0,0)),"cliff clipped")
		if i==5:
			assert(p.contains_point(p.position),"upper floor contact")
			assert(not p.contains_point(p.position-Vector3.UP),"lower floor excluded")
		assert(not p.contains_point(p.position+Vector3.UP*.4),"jump excluded")
		var rays:int=p.sample_ray_count
		p.set_visual_age(.1)
		assert(not p.contains_point(p.position+Vector3(.65,0,0)),"unrevealed area")
		p.set_visual_age(1)
		assert(rays==p.sample_ray_count,"no continuing terrain rays")
		report[["flat","slope","undulating","step","cliff","two_floors"][i]]={"max_gap":gap,"max_penetration":penetration,"missed_contacts":missed,"rays":rays,"triangles":p._triangles.size()}
	for frame in 31:
		for p in pools:p.set_visual_age(frame/30.0)
		await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(OUT.path_join("terrain-frames/%03d.png"%frame))
	root.get_texture().get_image().save_png(OUT.path_join("terrain-v03.png"))
	var file:=FileAccess.open(OUT.path_join("terrain-validation.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"  "))
	print("TERRAIN_V02_COMPLETE ",JSON.stringify(report))
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
