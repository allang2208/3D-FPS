extends RefCounted
## Match attachment coating to the actual receiver material, in linear color.
## The result is lighting-independent and shared by live rigs and UI previews.
const RECEIVERS := ["AKM_Classic_Body","M16Mesh_m16a2_base","QBZ191_BodyMagazine","Upper_reciever_low_003","SM_AR_01","SM_Handgun_03"]

static func _image(texture: Texture2D) -> Image:
	if texture==null:return null
	var image:=texture.get_image()
	if image==null or image.is_empty():return null
	if image.is_compressed():image.decompress()
	image.resize(128,128,Image.INTERPOLATE_BILINEAR)
	return image

static func _pixel(image: Image, uv: Vector2) -> Color:
	if image==null:return Color.WHITE
	return image.get_pixel(posmod(floori(uv.x*image.get_width()),image.get_width()),posmod(floori(uv.y*image.get_height()),image.get_height()))

static func _channel(color: Color, channel: int) -> float:
	match channel:
		BaseMaterial3D.TEXTURE_CHANNEL_GREEN:return color.g
		BaseMaterial3D.TEXTURE_CHANNEL_BLUE:return color.b
		BaseMaterial3D.TEXTURE_CHANNEL_ALPHA:return color.a
		BaseMaterial3D.TEXTURE_CHANNEL_GRAYSCALE:return (color.r+color.g+color.b)/3.0
	return color.r

static func profile(model: Node3D) -> Dictionary:
	if model.has_meta("attachment_finish_profile"):return model.get_meta("attachment_finish_profile")
	var source: MeshInstance3D
	for name in RECEIVERS:
		source=model.find_child(name,true,false) as MeshInstance3D
		if source!=null:break
	if source==null:return {}
	var samples:Array=[]
	var response_scale:=1.0
	for surface in source.mesh.get_surface_count():
		var material:=source.get_active_material(surface)
		if material is ShaderMaterial:
			if material.has_meta("rifle_clean_profile"):
				var clean: Dictionary = material.get_meta("rifle_clean_profile").duplicate()
				clean["receiver"] = str(source.name)
				model.set_meta("attachment_finish_profile",clean)
				return clean
			if material.shader.resource_path=="res://assets/materials/weapon_finish.gdshader":
				if material.get_shader_parameter("surface_metallic")<.1:continue
				samples.append([material.get_shader_parameter("tint").srgb_to_linear(),material.get_shader_parameter("surface_roughness"),material.get_shader_parameter("surface_metallic"),material.get_shader_parameter("surface_specular")])
			elif material.shader.resource_path.ends_with("materials_v2/coating.gdshader"):
				# Same-light swatch calibration for this existing custom coating shader.
				# Its response differs from the shared tint shader; keep this bridge
				# tied to the shader, not a hard-coded weapon color.
				response_scale=.65
				var coating:=_image(material.get_shader_parameter("coating_albedo"))
				for y in 8:
					for x in 8:
						var color:=_pixel(coating,Vector2((x+.5)/8.0,(y+.5)/8.0)).srgb_to_linear()
						var base:=Color(.036,.036,.036).lerp(color,.5)*Color(.92,.96,1)
						samples.append([base,.62-clampf((color.r-.025)*2,0,.08),.16,.28])
		elif material is StandardMaterial3D:
			if material.transparency!=BaseMaterial3D.TRANSPARENCY_DISABLED or material.emission_enabled:continue
			var albedo:=_image(material.albedo_texture)
			var rough:=_image(material.roughness_texture)
			var metal:=_image(material.metallic_texture)
			var a:=source.mesh.surface_get_arrays(surface)
			var indices:PackedInt32Array=a[Mesh.ARRAY_INDEX]
			var uv:PackedVector2Array=a[Mesh.ARRAY_TEX_UV]
			if indices.is_empty() or uv.is_empty():continue
			var step:=maxi(1,floori(indices.size()/576.0))*3
			for t in range(0,indices.size()-2,step):
				var at:Vector2=(uv[indices[t]]+uv[indices[t+1]]+uv[indices[t+2]])/3.0
				var color:Color=_pixel(albedo,at).srgb_to_linear()*material.albedo_color.srgb_to_linear()
				var metallic:float=material.metallic*_channel(_pixel(metal,at),material.metallic_texture_channel)
				# Reject dark holes and polymer islands in combined weapon textures.
				if maxf(color.r,maxf(color.g,color.b))<.003 or metallic<.08:continue
				samples.append([color,material.roughness*_channel(_pixel(rough,at),material.roughness_texture_channel),metallic,material.metallic_specular])
	if samples.is_empty():return {}
	# Trim shadows and bright worn edges; do not let a silver screw set the coating.
	samples.sort_custom(func(a,b):return a[0].get_luminance()<b[0].get_luminance())
	var first:=floori(samples.size()/4.0);var last:=maxi(first+1,floori(samples.size()*3/4.0))
	var average_color:=Color(0,0,0,0);var roughness:=0.0;var average_metallic:=0.0;var specular:=0.0
	for i in range(first,last):
		average_color+=samples[i][0];roughness+=samples[i][1];average_metallic+=samples[i][2];specular+=samples[i][3]
	var count:float=last-first
	average_color/=count;average_color.a=1
	average_color=average_color.linear_to_srgb()*response_scale;average_color.a=1
	var result:Dictionary={"color":average_color,"roughness":clampf(roughness/count,.45,.85),"metallic":clampf(average_metallic/count,.1,.45),"specular":clampf(specular/count,.16,.3),"receiver":str(source.name)}
	model.set_meta("attachment_finish_profile",result)
	return result

static func apply(model: Node3D, parts: Dictionary) -> void:
	if OS.get_environment("ATTACHMENT_MATCH_PROFILE")=="legacy":return
	var target:=profile(model)
	if target.is_empty():return
	for part in parts.values():
		for node in part.find_children("*","MeshInstance3D",true,false):
			var source:Material=node.get_meta("attachment_authored_material",node.material_override)
			# Native textured magazines/grips keep their own masks and normal maps.
			# Lens, reticle, emitter and reflector shaders are never recolored.
			if not source is ShaderMaterial or source.shader.resource_path!="res://assets/materials/weapon_finish.gdshader":continue
			var metal:float=source.get_shader_parameter("surface_metallic")
			var rough:float=source.get_shader_parameter("surface_roughness")
			var tint:Color=source.get_shader_parameter("tint")
			if metal<.1 and (rough>=.9 or tint.get_luminance()<.08):continue
			node.set_meta("attachment_authored_material",source)
			var matched:=source.duplicate() as ShaderMaterial
			# Match the clean receiver response, including restrained coating variation.
			matched.set_shader_parameter("finish_strength",minf(float(source.get_shader_parameter("finish_strength")),.025 if metal>=.1 else .04))
			var body:Color=target.color
			if metal>=.1:
				# Preserve a restrained accent hierarchy instead of the old pale rims.
				var accent:=clampf(tint.get_luminance()/.22,.94,1.06)
				matched.set_shader_parameter("tint",Color(body.r*accent,body.g*accent,body.b*accent))
				matched.set_shader_parameter("surface_roughness",lerpf(rough,target.roughness,.9))
				matched.set_shader_parameter("surface_metallic",target.metallic)
				matched.set_shader_parameter("surface_specular",target.specular)
			else:
				# Polymer remains dark and non-metallic; only soften the hue mismatch.
				var neutral:=Color(body.r,body.g,body.b)*(.12/maxf(body.get_luminance(),.01))
				matched.set_shader_parameter("tint",tint.lerp(neutral,.25))
			node.material_override=matched
			node.set_meta("matched_receiver",target.receiver)
