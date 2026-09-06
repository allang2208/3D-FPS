extends SceneTree
## 资产格式适配：统一 Terrain3D 纹理数组尺寸并将 alpha 设置为中性高度。
func _initialize() -> void:
	var reference:=Image.load_from_file("res://assets/textures/terrain_prepared/grass004_alb_ht.png")
	for kind in ["turf","loam"]:
		var image:=Image.load_from_file("res://assets/textures/wilderness_generated/"+kind+"_albedo_v1.png")
		image.resize(reference.get_width(),reference.get_height(),Image.INTERPOLATE_LANCZOS)
		image.convert(Image.FORMAT_RGBA8)
		var bytes:=image.get_data()
		for offset in range(3,bytes.size(),4): bytes[offset]=128
		image=Image.create_from_data(image.get_width(),image.get_height(),false,Image.FORMAT_RGBA8,bytes)
		assert(image.save_png("res://assets/textures/wilderness_generated/"+kind+"_alb_ht_v1.png")==OK)
	print("WILDERNESS_TEXTURES_PREPARED ",reference.get_size())
	quit()
