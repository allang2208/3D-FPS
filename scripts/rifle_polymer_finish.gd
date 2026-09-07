extends RefCounted
## Final surface pass for the four rifles; shared meshes, rigs and optical materials stay intact.
const SHADER = preload("res://assets/materials/rifle_layered_polymer.gdshader")
const RIFLES := ["infima_ar", "hk416", "qbz191", "m16"]
static func _texture_channel(value: int) -> Vector4:
	match value:
		BaseMaterial3D.TEXTURE_CHANNEL_GREEN: return Vector4(0,1,0,0)
		BaseMaterial3D.TEXTURE_CHANNEL_BLUE: return Vector4(0,0,1,0)
		BaseMaterial3D.TEXTURE_CHANNEL_ALPHA: return Vector4(0,0,0,1)
		BaseMaterial3D.TEXTURE_CHANNEL_GRAYSCALE: return Vector4(1.0/3.0,1.0/3.0,1.0/3.0,0)
	return Vector4(1,0,0,0)
static func rifle_id(model: Node3D) -> String:
	if not "model_resource" in model: return ""
	var id: String = model.model_resource.resource_path.get_file().get_basename()
	if id == "m16_modular_v2": id = "m16"
	return id if id in RIFLES else ""

static func _protected(material: Material) -> bool:
	if material is StandardMaterial3D:
		return material.transparency != BaseMaterial3D.TRANSPARENCY_DISABLED or material.shading_mode == BaseMaterial3D.SHADING_MODE_UNSHADED or material.emission_enabled
	return material is ShaderMaterial and material.shader.resource_path not in ["res://assets/materials/weapon_finish.gdshader", "res://assets/materials/rifle_clean_textured.gdshader"] and not material.shader.resource_path.contains("hk416/materials_") and material.shader != SHADER

static func _make(source: Material, label: String) -> ShaderMaterial:
	var material := ShaderMaterial.new()
	material.shader = SHADER
	material.resource_name = "Layered_polymer_" + label
	var grip := "grip" in label or "rubber" in label or "pad" in label or "magazine" in label
	var detail := "bolt" in label or "trigger" in label or "screw" in label or "button" in label or "lever" in label
	material.set_shader_parameter("tint", Color(.32,.37,.40) if detail else (Color(.11,.14,.17) if grip else Color(.19,.23,.26)))
	material.set_shader_parameter("roughness", .34 if detail else (.58 if grip else .44))
	if source is StandardMaterial3D:
		var patterned_grip: bool = source.normal_texture != null and source.normal_texture.resource_path.contains("reargrips/textures/")
		material.set_shader_parameter("has_normal", source.normal_enabled and source.normal_texture != null and not patterned_grip)
		material.set_shader_parameter("source_normal", source.normal_texture)
	return material

static func _paint_coordinates(mesh: MeshInstance3D, rig: Skeleton3D) -> void:
	if mesh.mesh.has_meta("polymer_coordinates"): return
	var rear := rig.global_transform * rig.get_bone_global_rest(rig.find_bone("RearSight")).origin
	var front := rig.global_transform * rig.get_bone_global_rest(rig.find_bone("FrontSight")).origin
	var muzzle := rig.global_transform * rig.get_bone_global_rest(rig.find_bone("SOCKET_Muzzle")).origin
	var forward := (front-rear).normalized()
	var up := front-muzzle; up=(up-forward*up.dot(forward)).normalized()
	var painted := ArrayMesh.new()
	for surface in mesh.mesh.get_surface_count():
		var a := mesh.mesh.surface_get_arrays(surface)
		var colors := PackedColorArray()
		var points: PackedVector3Array = a[Mesh.ARRAY_VERTEX]
		for i in points.size():
			var world: Vector3 = mesh.global_transform * points[i]
			if mesh.skin != null:
				var skin_rig: Skeleton3D = mesh.get_node(mesh.skeleton)
				var stride: int = a[Mesh.ARRAY_BONES].size()/points.size()
				world=Vector3.ZERO
				for influence in stride:
					var weight: float = a[Mesh.ARRAY_WEIGHTS][i*stride+influence]
					if weight == 0: continue
					var bind: int = a[Mesh.ARRAY_BONES][i*stride+influence]
					var bone := skin_rig.find_bone(mesh.skin.get_bind_name(bind))
					if bone < 0: bone = mesh.skin.get_bind_bone(bind)
					world += (skin_rig.global_transform * skin_rig.get_bone_global_rest(bone) * mesh.skin.get_bind_pose(bind) * points[i])*weight
			var delta := world-rear
			var original_red: float = a[Mesh.ARRAY_COLOR][i].r if a[Mesh.ARRAY_COLOR] != null else 0.0
			colors.append(Color(original_red,clampf((delta.dot(forward)+1.0)*.5,0,1),clampf(delta.dot(up)+.5,0,1),1))
		a[Mesh.ARRAY_COLOR]=colors
		painted.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,a,[],{},mesh.mesh.surface_get_format(surface)&Mesh.ARRAY_FLAG_USE_8_BONE_WEIGHTS)
		painted.surface_set_material(surface,mesh.mesh.surface_get_material(surface))
	mesh.mesh=painted
	painted.set_meta("polymer_coordinates",true)

static func apply(model: Node3D, parts: Dictionary) -> void:
	var id := rifle_id(model)
	if id.is_empty(): return
	var rig: Skeleton3D = model.skeleton
	for mesh in model.find_children("*", "MeshInstance3D", true, false):
		var name: String = str(mesh.name).to_lower()
		if "arms" in name or "sk_fp_ch" in name or ("hand" in name and not "handle" in name and not "handguard" in name and not "handstop" in name): continue
		var attachment := false
		for part in parts.values():
			if part.is_ancestor_of(mesh): attachment=true; break
		if not attachment and not (name.begins_with("sm_ar") or name.begins_with("upper_reciever") or name.begins_with("qbz191") or name.begins_with("m16")): continue
		if attachment:
			var source: Material = mesh.material_override
			if source == null:
				for surface in mesh.mesh.get_surface_count():
					var current: Material = mesh.get_active_material(surface)
					if current == null or _protected(current) or "bullets" in current.resource_name.to_lower(): continue
					if current is ShaderMaterial and current.shader == SHADER and not current.get_shader_parameter("body_regions"): continue
					var authored: Material = mesh.mesh.surface_get_material(surface)
					mesh.set_surface_override_material(surface,_make(authored,name))
				mesh.set_meta("layered_polymer",true)
				continue
			if _protected(source) or source is ShaderMaterial and source.shader == SHADER: continue
			if source is ShaderMaterial and source.get_shader_parameter("surface_metallic") != null and source.get_shader_parameter("surface_metallic") < .1 and source.get_shader_parameter("surface_roughness") >= .85: continue
			var finish := _make(source,name)
			mesh.material_override=finish
			mesh.set_meta("layered_polymer",true)
		else:
			_paint_coordinates(mesh,rig)
			for surface in mesh.mesh.get_surface_count():
				var current: Material = mesh.get_active_material(surface)
				if current is ShaderMaterial and current.shader == SHADER: continue
				var source: Material = mesh.mesh.surface_get_material(surface)
				if source == null or _protected(source) or "bullets" in source.resource_name.to_lower(): continue
				var label := name+"_"+source.resource_name.to_lower()
				var finish := _make(source,label)
				finish.set_shader_parameter("body_regions",true)
				finish.set_shader_parameter("furniture", "grip" in label or "stock" in label or "foreend" in label)
				finish.set_shader_parameter("magazine", "magazine" in name and not "bodymagazine" in name)
				finish.set_shader_parameter("stock", "stock" in label)
				finish.set_shader_parameter("mask_from_vertices",id=="hk416")
				finish.set_shader_parameter("foreend_band", {"infima_ar":.23,"hk416":.25,"qbz191":.27,"m16":.30}[id])
				if source is StandardMaterial3D:
					finish.set_shader_parameter("has_region_map",source.metallic_texture != null)
					finish.set_shader_parameter("region_map",source.metallic_texture)
					finish.set_shader_parameter("region_channel",_texture_channel(source.metallic_texture_channel))
				mesh.set_surface_override_material(surface,finish)
