extends SceneTree
## 从已有颜色细节推导匹配的艺术近似材质图，不是摄影测量重建。
const DIR := "res://assets/textures/wilderness_generated/"
const SIZE := 1024
func _initialize() -> void:
	for kind in ["loam","turf"]: prepare(kind)
	quit()
func prepare(kind: String) -> void:
	var source:=Image.load_from_file(ProjectSettings.globalize_path(DIR+kind+"_albedo_v1.png"))
	source.resize(SIZE,SIZE,Image.INTERPOLATE_LANCZOS)
	source.convert(Image.FORMAT_RGBA8)
	# 两对边缘对称羽化，避免平铺出现颜色阶跃；保留未修改的原图。
	for axis in 2:
		for along in SIZE:
			for d in 24:
				var a:=Vector2i(d,along) if axis==0 else Vector2i(along,d)
				var b:=Vector2i(SIZE-1-d,along) if axis==0 else Vector2i(along,SIZE-1-d)
				var ca:=source.get_pixelv(a)
				var cb:=source.get_pixelv(b)
				var average:=ca.lerp(cb,0.5)
				var weight:=1.0-smoothstep(0,24,d)
				source.set_pixelv(a,ca.lerp(average,weight))
				source.set_pixelv(b,cb.lerp(average,weight))
	var color:=source.get_data()
	var luminance:=PackedFloat32Array()
	luminance.resize(SIZE*SIZE)
	for i in luminance.size(): luminance[i]=(color[i*4]*0.2126+color[i*4+1]*0.7152+color[i*4+2]*0.0722)/255.0
	var heights:=PackedFloat32Array()
	heights.resize(luminance.size())
	for y in SIZE:
		for x in SIZE:
			var index:=y*SIZE+x
			var broad: float=(luminance[y*SIZE+posmod(x-8,SIZE)]+luminance[y*SIZE+posmod(x+8,SIZE)]+luminance[posmod(y-8,SIZE)*SIZE+x]+luminance[posmod(y+8,SIZE)*SIZE+x])*0.25
			heights[index]=clampf(0.5+(luminance[index]-broad)*1.8,0.18,0.82)
	var normals:=PackedByteArray()
	normals.resize(color.size())
	for y in SIZE:
		for x in SIZE:
			var index:=y*SIZE+x
			var dx: float=heights[y*SIZE+posmod(x+1,SIZE)]-heights[y*SIZE+posmod(x-1,SIZE)]
			var dy: float=heights[posmod(y+1,SIZE)*SIZE+x]-heights[posmod(y-1,SIZE)*SIZE+x]
			var n:=Vector3(-dx*3.0,-dy*3.0,1.0).normalized()
			for axis in 3: normals[index*4+axis]=roundi((n[axis]*0.5+0.5)*255)
			normals[index*4+3]=roundi(clampf((0.86 if kind=="loam" else 0.78)+(0.5-heights[index])*0.16,0.65,0.96)*255)
			color[index*4+3]=roundi(heights[index]*255)
	var albedo:=Image.create_from_data(SIZE,SIZE,false,Image.FORMAT_RGBA8,color)
	var normal:=Image.create_from_data(SIZE,SIZE,false,Image.FORMAT_RGBA8,normals)
	for pair in [[albedo,"alb_ht"],[normal,"nrm_rgh"]]:
		var map: Image=pair[0]
		assert(map.save_png(DIR+kind+"_"+pair[1]+"_1k_v2.png")==OK)
		map.resize(4096,4096,Image.INTERPOLATE_LANCZOS)
		assert(map.save_png(DIR+kind+"_"+pair[1]+"_v2.png")==OK)
	print("REFINED_MAPS ",kind," source-aligned approximate height/normal/roughness, periodic color borders")
