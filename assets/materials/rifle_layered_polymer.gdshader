shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;
uniform vec4 tint : source_color = vec4(.19,.23,.26,1.0);
uniform float roughness = .46;
uniform bool body_regions = false;
uniform bool mask_from_vertices = false;
uniform bool has_region_map = false;
uniform sampler2D region_map : filter_linear_mipmap, repeat_enable;
uniform vec4 region_channel = vec4(1,0,0,0);
uniform bool has_normal = false;
uniform sampler2D source_normal : hint_normal, filter_linear_mipmap, repeat_enable;
uniform float grain_scale = 260.0;
uniform bool furniture = false;
uniform bool magazine = false;
uniform bool stock = false;
uniform float foreend_band = .25;
float random_value(vec2 p) { return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453); }
float grain(vec2 p) {
	vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
	return mix(mix(random_value(i),random_value(i+vec2(1,0)),f.x),mix(random_value(i+vec2(0,1)),random_value(i+vec2(1,1)),f.x),f.y);
}
void fragment() {
	vec3 color=tint.rgb;
	float response=roughness;
	float along=COLOR.g*2.0-1.0, height=COLOR.b-0.5;
	float plastic=mask_from_vertices ? COLOR.r : 0.0;
	if (has_region_map) plastic=max(plastic,1.0-smoothstep(.15,.65,dot(texture(region_map,UV),region_channel)));
	if (body_regions) {
		color=mix(vec3(.16,.19,.22),vec3(.09,.115,.14),plastic*.8);
		response=mix(.44,.58,plastic);
		if (height > -.015 && !furniture && !magazine) { color=vec3(.26,.30,.33); response=.36; }
		if (furniture) { color=vec3(.095,.12,.15); response=.56; }
		if (magazine || height < -.13) { color=vec3(.12,.145,.17); response=.58; }
		if (stock && height > -.025 && along < -.14) { color=vec3(.56,.61,.63); response=.42; }
		if (along > foreend_band && along < foreend_band+.009 && height > -.085 && height < .005 && !magazine) { color=vec3(.82,.23,.025); response=.38; }
		if (stock && along > -.13 && along < -.12) { color=vec3(.82,.23,.025); response=.38; }
	}
	vec2 p=UV*grain_scale;
	float footprint=max(length(dFdx(p)),length(dFdy(p)));
	float detail=(grain(p)-.5)*(1.0-smoothstep(.4,1.4,footprint));
	ALBEDO=color*(1.0+detail*.05);
	ROUGHNESS=response+detail*.12;
	METALLIC=0.0; SPECULAR=.36; CLEARCOAT=.04; CLEARCOAT_ROUGHNESS=.55;
	if (has_normal) { NORMAL_MAP=texture(source_normal,UV).rgb; NORMAL_MAP_DEPTH=.30; }
}
