extends Node3D
## Cosmetic debris only; voxel_world.mine owns the single material reward.
var pieces: Array[RigidBody3D]=[]
var age:=0.0
var crack: MeshInstance3D

static func shard_mesh(seed_value: int, size: float, ore: bool) -> ArrayMesh:
	var rng:=RandomNumberGenerator.new()
	rng.seed=seed_value
	var points: Array[Vector3]=[]
	for p in [Vector3.UP,Vector3.DOWN,Vector3.LEFT,Vector3.RIGHT,Vector3.FORWARD,Vector3.BACK]:
		points.append(p*size*rng.randf_range(0.7,1.3))
	var st:=SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for face in [[0,3,4],[0,5,3],[0,2,5],[0,4,2],[1,4,3],[1,3,5],[1,5,2],[1,2,4]]:
		var tint:=Color(0.32,0.49,0.53) if ore else Color(0.32,0.34,0.35)
		if ore and rng.randf()<0.32: tint=Color(0.47,0.65,0.66)
		tint=tint.darkened(rng.randf_range(0,0.2))
		for index in [face[0],face[2],face[1]]:
			st.set_color(tint)
			st.add_vertex(points[index])
	st.generate_normals()
	var mat:=StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo=true
	mat.roughness=0.78
	mat.metallic=0.18 if ore else 0.0
	st.set_material(mat)
	return st.commit()

func fracture(shards: Array, origin: Vector3, at: Vector3, normal: Vector3) -> void:
	strike(at,normal,3,false,true,0)
	for part in shards:
		var body:=RigidBody3D.new()
		body.collision_layer=0
		body.collision_mask=1
		body.continuous_cd=true
		body.mass=0.5
		body.physics_material_override=PhysicsMaterial.new()
		body.physics_material_override.bounce=0.22
		body.physics_material_override.friction=0.85
		add_child(body)
		body.global_position=origin+part.center
		var mesh:=MeshInstance3D.new()
		mesh.mesh=part.mesh
		body.add_child(mesh)
		mesh.basis=part.get("basis",Basis.IDENTITY)
		var shape:=CollisionShape3D.new()
		var hull:=ConvexPolygonShape3D.new()
		var points:=PackedVector3Array()
		var baked_hull: PackedVector3Array = part.get("hull", PackedVector3Array())
		if not baked_hull.is_empty():
			for p in baked_hull: points.append(mesh.basis*p)
		else:
			for surface in mesh.mesh.get_surface_count():
				for p in mesh.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]: points.append(mesh.basis*p)
		hull.points=points
		shape.shape=hull
		body.add_child(shape)
		var direction: Vector3=(body.global_position-at).normalized()
		body.linear_velocity=direction*1.8+Vector3.UP*2.5+normal*0.4
		body.angular_velocity=Vector3(direction.z*3.0,1.5,-direction.x*3.0)
		pieces.append(body)

func strike(at: Vector3, normal: Vector3, count: int, ore: bool, complete: bool, override_count: int=-1) -> void:
	global_position=at
	var rng:=RandomNumberGenerator.new()
	rng.seed=731+count*91
	var number:=14 if complete else 4
	if override_count>=0: number=override_count
	for i in number:
		var radius:=rng.randf_range(0.08,0.17) if complete else rng.randf_range(0.015,0.035)
		var body:=RigidBody3D.new()
		body.collision_layer=0
		body.collision_mask=1
		body.mass=0.2
		body.continuous_cd=true
		body.physics_material_override=PhysicsMaterial.new()
		body.physics_material_override.bounce=0.28
		body.physics_material_override.friction=0.85
		add_child(body)
		body.position=normal*(radius+0.06)+Vector3(rng.randf_range(-0.08,0.08),0,rng.randf_range(-0.08,0.08))
		var mesh:=MeshInstance3D.new()
		mesh.mesh=shard_mesh(i+count*29,radius,ore)
		body.add_child(mesh)
		var shape:=CollisionShape3D.new()
		shape.shape=mesh.mesh.create_convex_shape()
		body.add_child(shape)
		var outward:=Vector3(rng.randf_range(-1,1),rng.randf_range(0.4,1.0),rng.randf_range(-1,1)).normalized()
		body.linear_velocity=outward*rng.randf_range(1.3,3.4)+normal*1.2+Vector3.UP*1.1
		body.angular_velocity=Vector3(rng.randf_range(-7,7),rng.randf_range(-7,7),rng.randf_range(-7,7))
		pieces.append(body)
	if not complete: make_crack(normal,count)
	var sound:=AudioStreamPlayer3D.new()
	sound.stream=preload("res://assets/sfx/kenney_impact/impactMining_000.ogg")
	sound.pitch_scale=0.7 if complete else 1.0+count*0.04
	sound.volume_db=-7 if complete else -12
	add_child(sound)
	sound.play()
	var dust:=CPUParticles3D.new()
	add_child(dust)
	dust.one_shot=true
	dust.explosiveness=1.0
	dust.amount=24 if complete else 8
	dust.lifetime=0.55
	dust.direction=normal
	dust.spread=80
	dust.initial_velocity_min=0.5
	dust.initial_velocity_max=2.2
	dust.gravity=Vector3(0,-2,0)
	var particle:=SphereMesh.new()
	particle.radius=0.025
	particle.height=0.05
	var material:=StandardMaterial3D.new()
	material.albedo_color=Color(0.34,0.38,0.38)
	particle.material=material
	dust.mesh=particle
	dust.emitting=true

func make_crack(normal: Vector3, count: int) -> void:
	crack=MeshInstance3D.new()
	var st:=SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in count+2:
		var direction:=Vector3(cos(i*2.4),0,sin(i*2.4))
		var side:=Vector3(-direction.z,0,direction.x)*0.008
		var end:=direction*(0.10+count*0.055)
		for p in [side,-side,end,side,end,end+side*0.5]:
			st.set_normal(Vector3.UP)
			st.add_vertex(p)
	var mat:=StandardMaterial3D.new()
	mat.albedo_color=Color(0.025,0.04,0.04)
	mat.cull_mode=BaseMaterial3D.CULL_DISABLED
	st.set_material(mat)
	crack.mesh=st.commit()
	add_child(crack)
	crack.position=normal*0.008
	crack.basis=Basis(Quaternion(Vector3.UP,normal.normalized()))

func _process(delta: float) -> void:
	age+=delta
	if age>1.0 and is_instance_valid(crack): crack.hide()
	if age>6.0:
		for body in pieces:
			for mesh in body.get_children():
				if mesh is MeshInstance3D: mesh.transparency=clampf((age-6.0)/1.0,0,1)
	if age>7.0: queue_free()
