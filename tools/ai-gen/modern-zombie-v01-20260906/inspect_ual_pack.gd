extends SceneTree
func _initialize() -> void:
	print("UAL_PACK_LOADED ",ProjectSettings.load_resource_pack("E:/3d/3-dfps/tools/ai-gen/modern-zombie-v01-20260906/ual-official-viewer.pck",false))
	scan("res://")
	quit()
func scan(path: String) -> void:
	var d=DirAccess.open(path)
	if d==null:return
	for file in d.get_files():
		print("UAL_FILE ",path.path_join(file))
	for dir in d.get_directories():
		if dir not in [".",".."]:scan(path.path_join(dir))
