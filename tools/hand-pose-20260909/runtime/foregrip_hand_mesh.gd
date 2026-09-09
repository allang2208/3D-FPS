extends RefCounted
## Instance-local replacement: original right hand, palm, sleeves, UVs and bind table stay intact.
const REFINED = preload("res://assets/models/attachments/angled_foregrip/left_hand_polish_v3.res")
static func set_enabled(model:Node,enabled:bool)->void:
	var node=model.find_child("SK_FP_CH_Default_Cubic",true,false) as MeshInstance3D
	if node==null:return
	# A fitted hand supplies its own geometry for every attachment pose.
	if node.mesh != null and node.mesh.get_meta("preserve_fitted_hand", false):return
	if enabled:
		if node.has_meta("foregrip_original_mesh"):return
		var names:PackedStringArray=REFINED.get_meta("source_bind_names")
		assert(node.skin!=null and node.skin.get_bind_count()==names.size())
		for i in names.size():assert(str(node.skin.get_bind_name(i))==names[i])
		var materials:Array[Material]=[]
		for i in node.mesh.get_surface_count():materials.append(node.get_active_material(i))
		node.set_meta("foregrip_original_mesh",node.mesh)
		node.mesh=REFINED
		for i in materials.size():node.set_surface_override_material(i,materials[i])
	elif node.has_meta("foregrip_original_mesh"):
		node.mesh=node.get_meta("foregrip_original_mesh")
		node.remove_meta("foregrip_original_mesh")
