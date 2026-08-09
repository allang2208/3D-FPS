extends SceneTree

# 探针：验证新下载的热带林下 glTF 可加载、AABB 正常、材质带贴图

var paths := [
	"res://assets/models/polyhaven/fern_02/fern_02_2k.gltf",
	"res://assets/models/polyhaven/leafy_grass/leafy_grass_2k.gltf",
	"res://assets/models/polyhaven/nettle_plant/nettle_plant_2k.gltf",
	"res://assets/models/polyhaven/weed_plant_02/weed_plant_02_2k.gltf",
]


func _init() -> void:
	var bad := 0
	for p in paths:
		var scn: PackedScene = load(p)
		if scn == null:
			print("[probe] FAIL load: ", p)
			bad += 1
			continue
		var inst: Node = scn.instantiate()
		root.add_child(inst)
		var aabb := _scene_aabb(inst)
		var meshes := inst.find_children("", "MeshInstance3D", true, false)
		var tex_count := 0
		for m in meshes:
			var mi := m as MeshInstance3D
			for s in mi.mesh.get_surface_count():
				var mat := mi.mesh.surface_get_material(s)
				if mat == null:
					mat = mi.get_surface_override_material(s)
				if mat is BaseMaterial3D and (mat as BaseMaterial3D).albedo_texture != null:
					tex_count += 1
		print("[probe] OK ", p.get_file(), " aabb=", aabb, " size=", aabb.size,
			" meshes=", meshes.size(), " textured_surfaces=", tex_count)
		inst.queue_free()
	quit(0 if bad == 0 else 1)


func _scene_aabb(node: Node) -> AABB:
	var aabb := AABB()
	var first := true
	for m in node.find_children("", "MeshInstance3D", true, false):
		if m is MeshInstance3D and m.mesh != null:
			var b := (m as Node3D).global_transform * (m as MeshInstance3D).mesh.get_aabb()
			if first:
				aabb = b
				first = false
			else:
				aabb = aabb.merge(b)
	return aabb
