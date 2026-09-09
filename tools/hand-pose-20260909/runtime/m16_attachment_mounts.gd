extends RefCounted
## M16 source-rest coordinates. Seats are sampled from triangles by build_modular.py.
const Fitted := preload("res://assets/models/attachments/m16/fitted_parts.glb")
const Stocks := preload("res://scripts/stock_variants.gd")
const Optics := preload("res://scripts/optic_variants.gd")
const Finish := preload("res://scripts/weapon_surface_materials.gd")
const FORWARD := Basis(Vector3(-1, 0, 0), Vector3.UP, Vector3(0, 0, -1))
const FACTORY := {"stock": "M16FactoryStock", "reargrip": "M16FactoryGrip", "foregrip": "M16FactoryForeend", "muzzle": "M16FactoryMuzzle", "magazine": "M16Mesh_magazine"}

static func source_point(p: Array) -> Vector3:
	return Vector3(p[0], p[2], -p[1])

static func restore(model: Node3D) -> void:
	for name in FACTORY.values():
		var mesh := model.find_child(name, true, false)
		if mesh != null:
			mesh.show()

static func _mesh(name: String) -> MeshInstance3D:
	var source := Fitted.instantiate()
	var original := source.find_child(name, true, false) as MeshInstance3D
	assert(original != null, name)
	var result := original.duplicate() as MeshInstance3D
	result.visible = true
	source.free()
	return result

static func _seat(part: Node3D, name: String, source_transform: Transform3D) -> void:
	var mesh := _mesh(name)
	part.add_child(mesh)
	mesh.transform = source_transform.affine_inverse() * mesh.transform
	mesh.material_override = Finish.make_finish(Color(0.19, 0.20, 0.21), 0.76, 0.18, 0.22)

static func _marker(part: Node3D, name: String, position: Vector3) -> void:
	if part.has_node(name):
		return
	var marker := Marker3D.new()
	marker.name = name
	marker.position = position
	part.add_child(marker)

static func mount(model: Node3D, selected: Dictionary) -> Dictionary:
	var rig: Skeleton3D = model.skeleton
	var fit: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/attachments/m16/fit.json"))
	var result := {}
	for slot in ["optic", "muzzle", "magazine", "foregrip", "reargrip", "stock", "trigger", "tactical"]:
		if not Stocks.enabled(selected.get(slot, false)):
			continue
		var part: Node3D
		var placement := Transform3D.IDENTITY
		var bone_name := "m16a2_base"
		match slot:
			"optic":
				part = load(Optics.scene_path(selected[slot])).instantiate()
				placement = Transform3D(FORWARD, source_point(fit.optic.blender_origin))
				for name in ["CarryHandleSeat", "CarryHandleFoot0", "CarryHandleFoot1"]:
					_seat(part, name, placement)
			"muzzle":
				part = load(preload("res://scripts/muzzle_variants.gd").scene_path(selected[slot])).instantiate()
				placement = Transform3D(FORWARD, source_point(fit.muzzle.blender_origin))
			"stock":
				var stock_id := Stocks.variant(selected[slot])
				var stock_path := Stocks.scene_path(stock_id)
				part = load(stock_path).instantiate()
				placement = Transform3D(FORWARD, source_point(fit.stock.blender_origin))
				_seat(part, "StockTransition", placement)
			"tactical":
				part = load("res://assets/models/attachments/tactical/%s.tscn" % selected[slot]).instantiate()
				placement = Transform3D(FORWARD, source_point(fit.tactical.blender_origin))
				_seat(part, "TacticalSaddle", placement)
				preload("res://scripts/tactical_variants.gd")._finish(part)
			_:
				part = Node3D.new()
				part.name = "M16_" + slot
				if slot == "trigger":
					# Internal tuning keeps the authored trigger and finger contact unchanged.
					bone_name = "m16a2_trigger"
				elif slot == "reargrip" and selected[slot] is String and selected[slot] == "wood":
					part.free()
					part = load("res://assets/models/attachments/hollow_grip/m16/hollow_grip.tscn").instantiate()
				else:
					var mesh := _mesh({"magazine": "ExtendedMagazine", "foregrip": "ReplacementForeend", "reargrip": "ReplacementGrip"}[slot])
					part.add_child(mesh)
					var original := model.find_child(FACTORY[slot], true, false) as MeshInstance3D
					if slot == "magazine":
						for surface in mesh.mesh.get_surface_count():
							mesh.set_surface_override_material(surface, original.get_active_material(surface))
						bone_name = "magazine"
					else:
						var kind: String = str(selected[slot]) if slot == "reargrip" and selected[slot] is String else "rubber"
						var material := StandardMaterial3D.new()
						material.albedo_texture = load("res://assets/models/attachments/reargrips/textures/%s_albedo.png" % kind)
						material.normal_enabled = true
						material.normal_texture = load("res://assets/models/attachments/reargrips/textures/%s_normal.png" % kind)
						material.roughness_texture = load("res://assets/models/attachments/reargrips/textures/%s_roughness.png" % kind)
						material.roughness = 0.90
						material.metallic_specular = 0.15
						material.uv1_triplanar = true
						material.uv1_scale = Vector3.ONE * 16.0
						mesh.material_override = material
				_marker(part, "Anchor", source_point({"magazine": [0,-0.10,-0.06], "foregrip": [0,-0.36,0.13], "reargrip": [0,0.025,0.025], "trigger": [0,-0.03,0.08]}[slot]))
		# Grip variants already carry shared authored textures; generic tint conversion
		# would discard their albedo maps and turn a default-white material white.
		if slot not in ["foregrip", "reargrip"]:
			Finish.prepare_attachment(part)
		var bone := rig.find_bone(bone_name)
		assert(bone >= 0, bone_name)
		var holder := BoneAttachment3D.new()
		holder.name = "Gunsmith_" + slot
		rig.add_child(holder)
		holder.bone_idx = bone
		holder.add_child(part)
		part.transform = rig.get_bone_global_rest(bone).affine_inverse() * placement
		holder.global_transform = rig.global_transform * rig.get_bone_global_pose(bone)
		if FACTORY.has(slot):
			model.find_child(FACTORY[slot], true, false).hide()
		if slot == "muzzle" and str(selected.get(slot,false)) == "titanium_brake":
			preload("res://scripts/titanium_muzzle_fit.gd").apply(part,"m16")
		result[slot] = part
	# Calibrate in source rest space, then carry the complete seat with the
	# animated weapon bone. Global UP during a rolled reload changes the seat.
	var base=rig.find_bone("m16a2_base")
	var motion=rig.global_transform*rig.get_bone_global_pose(base)*rig.get_bone_global_rest(base).affine_inverse()*rig.global_transform.affine_inverse()
	var front=rig.to_global(rig.get_bone_global_rest(rig.find_bone("FrontSight")).origin)
	var rear=rig.to_global(rig.get_bone_global_rest(rig.find_bone("RearSight")).origin)
	var forward=(front-rear).normalized()
	var up=Vector3.UP;up=(up-forward*up.dot(forward)).normalized()
	result.merge(preload("res://scripts/angled_foregrip.gd").mount(model,selected,rig,motion.basis*Basis(up.cross(-forward),up,-forward),motion*front,"m16"))
	return result
