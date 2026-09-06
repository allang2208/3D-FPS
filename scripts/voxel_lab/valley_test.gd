extends "res://scripts/voxel_lab/voxel_lab.gd"
const Backdrop := preload("res://scripts/voxel_lab/valley_backdrop.gd")
var backdrop: Node3D
var original_controls := {}
var control_pixels: Array = []

func _ready() -> void:
	save_path = "user://voxel-valley-test-v1.json"
	super._ready()
	status.text = "中央 18×18 米可挖 · 外围保护接缝"

func _build_ui() -> void:
	super._build_ui()
	info.get_parent().get_child(0).text="旷野体素接入测试 / 24×24 米"

func _build_world() -> void:
	backdrop = Backdrop.new()
	backdrop.name = "ValleyBackdrop"
	add_child(backdrop)
	var center := Backdrop.PATCH_CENTER
	var origin := Vector3(center.x,0,center.y)
	var low := INF
	var high := -INF
	for z in range(-27,28):
		for x in range(-27,28):
			var h: float = backdrop.terrain.data.get_height(origin+Vector3(x*0.5,0,z*0.5))
			low=minf(low,h)
			high=maxf(high,h)
	origin.y=(low+high)*0.5-4.0
	print("PATCH_HEIGHT_RANGE ",low," ",high)
	world = preload("res://scripts/voxel_lab/valley_patch.gd").new()
	var result: Error = world.configure_from_terrain(backdrop.terrain.data,origin,"valley_03_patch_245_65_half",0.5)
	assert(result==OK,"Selected valley patch exceeds voxel vertical range")
	world.name = "VoxelWorld"
	add_child(world)
	for z in range(-12,12):
		for x in range(-12,12):
			var p := origin+Vector3(x,0,z)
			original_controls[p] = backdrop.terrain.data.get_control(p)
			var region: Terrain3DRegion=backdrop.terrain.data.get_regionp(p)
			var image: Image=region.get_map(Terrain3DRegion.TYPE_CONTROL)
			var pixel:=Vector2i(posmod(floori(p.x),backdrop.terrain.region_size),posmod(floori(p.z),backdrop.terrain.region_size))
			control_pixels.append([image,pixel,image.get_pixelv(pixel)])
			backdrop.terrain.data.set_control_hole(p,true)
	backdrop.terrain.data.update_maps(Terrain3DRegion.TYPE_CONTROL)
	backdrop.terrain.collision.build()
	preload("res://scripts/voxel_lab/terrain_material_bridge.gd").bind_to_mesh(world.ground_material,backdrop.terrain.material)
	_build_transition_strip()

func _build_transition_strip() -> void:
	# Hole 标记作用于顶点，负侧相邻四边形也消失。补齐 [-13,-12] 米窄带。
	var st:=SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for z in range(-26,24,2):
		_transition_quad(st,-26,z)
	for x in range(-24,24,2):
		_transition_quad(st,x,-26)
	var mesh:=st.commit()
	mesh.surface_set_material(0,world.ground_material)
	var body:=StaticBody3D.new()
	body.name="TerrainTransition"
	body.collision_layer=1
	var mi:=MeshInstance3D.new()
	mi.mesh=mesh
	body.add_child(mi)
	var col:=CollisionShape3D.new()
	col.shape=mesh.create_trimesh_shape()
	body.add_child(col)
	world.add_child(body)

func _transition_quad(st: SurfaceTool, x: int,z: int) -> void:
	for corner in [Vector2(x,z),Vector2(x+2,z),Vector2(x,z+2),Vector2(x+2,z),Vector2(x+2,z+2),Vector2(x,z+2)]:
		var at:=Vector3(corner.x,world.natural_height(corner.x,corner.y),corner.y)
		st.set_normal(world.normal_at(at))
		st.set_color(Color(0,0,0,1))
		st.add_vertex(at)

func respawn() -> void:
	if world == null or player == null:
		return
	var local_pos := Vector3(-12.5,15,12.5)
	for y in range(15,-9,-1):
		if world.get_cell(Vector3i(-13,y,12))!=0:
			local_pos.y=y+1.1
			break
	player.global_position=world.to_global(local_pos)
	player.velocity=Vector3.ZERO
	player.look_at(world.to_global(Vector3(4,local_pos.y,0)))
	camera.rotation.x=-0.15

func _build_return_portal() -> void:
	var portal := preload("res://scripts/voxel_lab/lab_portal.gd").new()
	portal.name="ReturnPortal"
	portal.target_scene="res://scenes/voxel_lab.tscn"
	portal.label_text="返回体素试验场"
	portal.position=world.to_global(Vector3(-9,world.natural_height(-9,9)+1.4,9))
	add_child(portal)

func _exit_tree() -> void:
	# 恢复共享资源的原始 control 像素；从不把测试洞口写入地形缓存。
	for record in control_pixels:
		record[0].set_pixelv(record[1],record[2])
	control_pixels.clear()
	super._exit_tree()
