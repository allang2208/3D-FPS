shader_type spatial;
uniform bool upright = false;
uniform vec3 surface_tint = vec3(1.32,1.30,1.28);
uniform vec2 roughness_range = vec2(.77,.60);
uniform float pattern_scale = .85;
uniform sampler2D wood_color : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
varying vec3 p_local;
varying vec3 n_local;
varying mat3 normal_to_view;
varying flat vec3 variation;
float hash(vec3 p) { return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453); }
float luminance(vec3 color) { return dot(color,vec3(.2126,.7152,.0722)); }
vec2 fiber_gradient(vec2 uv, vec3 center) {
 vec2 texel=1.0/vec2(textureSize(wood_color,0));
 float h=luminance(center);
 float x=luminance(texture(wood_color,uv+vec2(texel.x,0.0)).rgb)-h;
 float y=luminance(texture(wood_color,uv+vec2(0.0,texel.y)).rgb)-h;
 return clamp(vec2(x,y)*1.5,vec2(-.045),vec2(.045));
}
void vertex() {
 p_local=VERTEX;
 n_local=NORMAL;
 normal_to_view=mat3(MODELVIEW_MATRIX);
 vec3 cell=round(MODEL_MATRIX[3].xyz*2.0);
 variation=vec3(hash(cell),hash(cell+17.0),hash(cell+53.0));
}
void fragment() {
 vec3 p=upright?p_local.yxz:p_local;
 vec3 n=normalize(upright?n_local.yxz:n_local);
 vec3 w=pow(abs(n),vec3(6.0));
 w/=max(dot(w,vec3(1.0)),.0001);
 vec2 a=p.zy*pattern_scale+variation.xy;
 vec2 b=p.xz*pattern_scale+variation.xy;
 vec2 c=p.xy*pattern_scale+variation.xy;
 vec3 ca=texture(wood_color,a).rgb;
 vec3 cb=texture(wood_color,b).rgb;
 vec3 cc=texture(wood_color,c).rgb;
 vec3 wood=ca*w.x+cb*w.y+cc*w.z;
 // Keep the generated grain visible under the hub's shaded colonnades.
 ALBEDO=wood*surface_tint*mix(.97,1.03,variation.z);
 float pore=clamp(luminance(wood)*5.0,0.0,1.0);
 ROUGHNESS=mix(roughness_range.x,roughness_range.y,pore);
 SPECULAR=.28;
 // Shallow artistic relief derived from this very image, not unrelated scan maps.
 vec2 ga=fiber_gradient(a,ca);
 vec2 gb=fiber_gradient(b,cb);
 vec2 gc=fiber_gradient(c,cc);
 vec3 detail=vec3(0.0,-ga.y,-ga.x)*w.x+vec3(-gb.x,0.0,-gb.y)*w.y+vec3(-gc.x,-gc.y,0.0)*w.z;
 vec3 bumped=normalize(n+detail);
 if(upright) bumped=bumped.yxz;
 NORMAL=normalize(normal_to_view*bumped);
}
