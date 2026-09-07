shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;
uniform vec4 tint : source_color = vec4(0.19, 0.205, 0.22, 1.0);
uniform float position_scale = 1.0;
uniform mat4 surface_frame = mat4(1.0);
uniform bool use_vertex_color = false;
uniform float base_roughness = 0.46;
uniform float grain_depth = 0.000035;
uniform float grain_density = 1300.0;
uniform int design_region = 0;
uniform mat4 design_frame = mat4(1.0);
varying vec3 surface_position;
varying vec3 polymer_color;
varying vec3 design_position;
void vertex() {
	vec4 stable_position = surface_frame * vec4(VERTEX, 1.0);
	surface_position = stable_position.xyz * position_scale;
	design_position = (design_frame * stable_position).xyz;
	polymer_color = use_vertex_color ? COLOR.rgb : vec3(1.0);
}
float hash(vec3 p) {
	p = fract(p * 0.1031);
	p += dot(p, p.yzx + 33.33);
	return fract((p.x + p.y) * p.z);
}
float grain(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(mix(hash(i), hash(i+vec3(1,0,0)), f.x), mix(hash(i+vec3(0,1,0)), hash(i+vec3(1,1,0)), f.x), f.y),
		mix(mix(hash(i+vec3(0,0,1)), hash(i+vec3(1,0,1)), f.x), mix(hash(i+vec3(0,1,1)), hash(i+vec3(1,1,1)), f.x), f.y), f.z);
}
void fragment() {
	// Fine injection-molded grain, without weave, scratches or weathering.
	vec3 p = surface_position * grain_density;
	float footprint = max(length(dFdx(p)), length(dFdy(p)));
	float visibility = 1.0 - smoothstep(0.4, 1.4, footprint);
	float detail = (grain(p) - 0.5) * visibility;
	vec3 color = tint.rgb * polymer_color;
	float roughness = base_roughness;
	// Authored clean color blocking in the original source's meter coordinates.
	// Regions follow the receiver cover, furniture and controls; never a grid overlay.
	vec3 q = design_position;
	if (design_region == 1) {
		color = vec3(0.16, 0.19, 0.22);
		if (q.z > 0.028 && q.y < 0.03) { color = vec3(0.26, 0.30, 0.33); roughness = 0.35; }
		if (q.y > 0.22) { color = vec3(0.11, 0.14, 0.17); roughness = 0.40; }
	} else if (design_region == 2) {
		color = vec3(0.085, 0.11, 0.14); roughness = 0.58;
		if (q.y < -0.235) {
			if (q.y < -0.30 && q.y > -0.465 && q.z > -0.020) { color = vec3(0.60,0.65,0.66); roughness = 0.42; }
			if (q.y < -0.290 && q.y > -0.299) { color = vec3(0.82,0.23,0.025); roughness = 0.38; }
		} else if (q.y < -0.152 && q.z < -0.035) {
			if (q.z > -0.056) { color = vec3(0.82,0.23,0.025); roughness = 0.38; }
		} else {
			if (q.z > 0.011) { color = vec3(0.19,0.23,0.26); roughness = 0.44; }
			if (q.y > 0.188 && q.y < 0.197) { color = vec3(0.82,0.23,0.025); roughness = 0.38; }
		}
	}
	ALBEDO = color * (1.0 + detail * 0.055);
	ROUGHNESS = roughness + detail * 0.16;
	METALLIC = 0.0;
	SPECULAR = 0.36;
	CLEARCOAT = 0.04;
	CLEARCOAT_ROUGHNESS = 0.55;
	vec3 r1 = cross(dFdy(VERTEX), NORMAL);
	vec3 r2 = cross(NORMAL, dFdx(VERTEX));
	float determinant = dot(dFdx(VERTEX), r1);
	vec3 gradient = sign(determinant) * (dFdx(detail)*r1 + dFdy(detail)*r2);
	NORMAL = normalize(abs(determinant)*NORMAL - gradient*grain_depth);
}
