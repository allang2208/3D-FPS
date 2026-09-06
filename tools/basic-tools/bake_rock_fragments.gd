extends SceneTree
func _initialize() -> void:
	call_deferred("run")
func run() -> void:
	var out:="res://assets/models/basic_tools/rock_fragments/"
	DirAccess.make_dir_recursive_absolute(out)
	for name in ["rock_09","boulder_01"]:
		var path: String="res://assets/models/polyhaven/%s/%s_2k.gltf" % [name,name]
		var model: Node3D=load(path).instantiate()
		root.add_child(model)
		var parts: Array=[]
		for source in model.find_children("","MeshInstance3D",true,false):
			var mesh: Mesh=source.mesh.duplicate()
			for s in mesh.get_surface_count():
				var mat: StandardMaterial3D=source.get_active_material(s).duplicate()
				if mat.albedo_texture==null: mat.albedo_texture=load(path.get_base_dir()+"/textures/"+name+"_diff_2k.jpg")
				mat.metallic_specular=0.15
				mat.roughness=0.9
				mesh.surface_set_material(s,mat)
			parts.append({"mesh":mesh,"transform":model.global_transform.affine_inverse()*source.global_transform})
		var shards: Array=load("res://scripts/tools/rock_fracture_mesh.gd").fracture(parts)
		assert(shards.size()==8)
		var resource:=Resource.new()
		resource.set_meta("pieces",shards)
		assert(ResourceSaver.save(resource,out+name+".res")==OK)
		model.free()
		print("BAKED ",name," 8 fragments")
	quit()
