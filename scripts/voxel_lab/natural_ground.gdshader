shader_type spatial;
uniform sampler2D grass_color : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D soil_color : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D rock_color : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D grass_normal : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D soil_normal : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D rock_normal : hint_normal, filter_linear_mipmap, repeat_enable;
uniform float voxel_grass_scale = 0.5;
uniform float voxel_soil_scale = 0.32;
uniform float voxel_rock_scale = 0.12;
uniform bool voxel_detail_variation = false;
varying vec3 world_position;
varying vec3 world_normal;
uniform bool use_source_maps = false;
uniform sampler2D source_tint : source_color, filter_linear, repeat_disable;
uniform sampler2D source_mix : filter_linear, repeat_disable;
uniform vec2 source_origin = vec2(0.0);

vec4 soil_sample(sampler2D tex, vec2 uv) {
	vec4 sample_a=texture(tex,uv);
	if (!voxel_detail_variation) return sample_a;
	float blend=0.5+0.25*sin(uv.x*0.43+sin(uv.y*0.51));
	return mix(sample_a,texture(tex,uv+vec2(0.37,0.61)),blend);
}
float earth_noise(vec3 p) {
	vec3 cell = floor(p);
	vec3 f = fract(p);
	f = f*f*(3.0-2.0*f);
	// Trilinear value noise: world anchored so edits and chunk borders agree.
	vec4 a = fract(sin(vec4(dot(cell,vec3(127.1,311.7,74.7))) + vec4(0,127.1,311.7,438.8))*43758.5453);
	vec4 b = fract(sin(vec4(dot(cell,vec3(127.1,311.7,74.7))+74.7) + vec4(0,127.1,311.7,438.8))*43758.5453);
	return mix(mix(mix(a.x,a.y,f.x),mix(a.z,a.w,f.x),f.y),mix(mix(b.x,b.y,f.x),mix(b.z,b.w,f.x),f.y),f.z);
}
vec4 triplanar(sampler2D tex, vec3 p, vec3 w) {
	return soil_sample(tex,p.yz)*w.x + soil_sample(tex,p.xz)*w.y + soil_sample(tex,p.xy)*w.z;
}
vec3 tri_normal(sampler2D tex, vec3 p, vec3 w, vec3 n) {
	vec3 x = soil_sample(tex,p.yz).xyz*2.0-1.0;
	vec3 y = soil_sample(tex,p.xz).xyz*2.0-1.0;
	vec3 z = soil_sample(tex,p.xy).xyz*2.0-1.0;
	// 无凹凸的法线贴图必须还原原始曲面法线，不能被投射权重掰向坐标轴。
	vec3 nx = normalize(vec3(x.z*n.x,x.x+n.y,x.y+n.z));
	vec3 ny = normalize(vec3(y.x+n.x,y.z*n.y,y.y+n.z));
	vec3 nz = normalize(vec3(z.x+n.x,z.y+n.y,z.z*n.z));
	return normalize(nx*w.x + ny*w.y + nz*w.z);
}
void vertex() {
	world_position = (MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;
	world_normal = normalize(MODEL_NORMAL_MATRIX*NORMAL);
}
void fragment() {
	vec3 n = normalize(world_normal);
	vec3 w = pow(abs(n),vec3(4.0));
	w /= max(w.x+w.y+w.z,0.0001);
	vec3 p = world_position;
	float rock = smoothstep(0.12,0.85,COLOR.r);
	float grass = smoothstep(0.55,0.88,n.y)*(1.0-smoothstep(0.0,0.3,COLOR.r))*(1.0-COLOR.g);
	vec2 source_uv=(world_position.xz-source_origin)/27.5+vec2(0.5);
	if (use_source_maps) {
		vec3 weights=texture(source_mix,source_uv).rgb;
		float intact=(1.0-COLOR.g)*(1.0-smoothstep(0.0,0.15,COLOR.r));
		grass=mix(grass,weights.r,intact);
		rock=mix(rock,weights.g/max(1.0-weights.r,0.001),intact);
	}
	// 延续旷野 colormap 的土石/草地色调，避免原始浅色泥沙贴图泛白。
	vec3 soil_albedo = triplanar(soil_color,p*voxel_soil_scale,w).rgb * vec3(0.72,0.68,0.60);
	if (voxel_detail_variation) {
		float earth = earth_noise(p * vec3(2.1,3.5,2.1));
		soil_albedo *= mix(vec3(0.86,0.82,0.78),vec3(1.08,1.04,0.99),smoothstep(0.15,0.85,earth));
	}
	vec3 stone_albedo = triplanar(rock_color,p*voxel_rock_scale,w).rgb * vec3(0.72,0.74,0.70);
	vec3 turf_albedo = triplanar(grass_color,p*voxel_grass_scale,w).rgb * vec3(0.72,0.80,0.64);
	ALBEDO = mix(mix(soil_albedo,stone_albedo,rock),turf_albedo,grass);
	if (use_source_maps) {
		vec3 original_tint=mix(mix(vec3(0.72,0.68,0.60),vec3(0.72,0.74,0.70),rock),vec3(0.72,0.80,0.64),grass);
		ALBEDO=ALBEDO/original_tint*texture(source_tint,source_uv).rgb;
	}
	float variation = 0.92 + 0.08*sin(world_position.x*0.27+sin(world_position.z*0.32));
	ALBEDO *= variation;
	vec3 mapped = mix(mix(tri_normal(soil_normal,p*voxel_soil_scale,w,n),tri_normal(rock_normal,p*voxel_rock_scale,w,n),rock),tri_normal(grass_normal,p*voxel_grass_scale,w,n),grass);
	NORMAL = normalize((VIEW_MATRIX*vec4(normalize(mix(n,mapped,0.35)),0.0)).xyz);
	ROUGHNESS = clamp(mix(mix(triplanar(soil_normal,p*voxel_soil_scale,w).a,triplanar(rock_normal,p*voxel_rock_scale,w).a,rock),triplanar(grass_normal,p*voxel_grass_scale,w).a,grass),0.55,1.0);
}
