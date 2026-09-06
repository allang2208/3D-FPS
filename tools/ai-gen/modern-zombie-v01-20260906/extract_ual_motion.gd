extends SceneTree
func _initialize() -> void:
	ProjectSettings.load_resource_pack("E:/3d/3-dfps/tools/ai-gen/modern-zombie-v01-20260906/ual-official-viewer.pck",false)
	var lib=load("res://libraries/UAL1_Source.tres") as AnimationLibrary
	print("UAL_CLIPS ",lib.get_animation_list() if lib else [])
	var cfg=ConfigFile.new()
	cfg.load("res://models/Mannequin.glb.import")
	var scene=load(cfg.get_value("remap","path")) as PackedScene
	var model=scene.instantiate()
	root.add_child(model)
	model.print_tree_pretty()
	var sk=model.find_child("GeneralSkeleton",true,false) as Skeleton3D
	var mesh=model.find_child("Mannequin",true,false) as MeshInstance3D
	mesh.skeleton=mesh.get_path_to(sk)
	print("UAL_SKIN ",mesh.skin," skeleton path ",mesh.skeleton," bones ",sk.get_bone_count())
	print("UAL_TRACK ",lib.get_animation("Death01").track_get_path(0))
	var ap=model.find_child("AnimationPlayer",true,false) as AnimationPlayer
	if ap==null:
		ap=AnimationPlayer.new()
		model.add_child(ap)
		ap.owner=model
	for name in ap.get_animation_library_list():ap.remove_animation_library(name)
	var selected=AnimationLibrary.new()
	for clip in ["Death01","Death02","Hit_Chest"]:
		var anim=lib.get_animation(clip).duplicate(true)
		for track in anim.get_track_count():
			var path=anim.track_get_path(track)
			if path.get_subname_count()>0:anim.track_set_path(track,NodePath(str(model.get_path_to(sk))+":"+str(path.get_subname(0))))
		selected.add_animation(clip,anim)
	ap.add_animation_library("",selected)
	var doc=GLTFDocument.new()
	var state=GLTFState.new()
	var err=doc.append_from_scene(model,state)
	print("UAL_EXPORT ",err," ",doc.write_to_filesystem(state,"E:/3d/3-dfps/tools/ai-gen/modern-zombie-v01-20260906/ual-mannequin.glb"))
	quit()
