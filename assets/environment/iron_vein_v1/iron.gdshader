shader_type spatial;
uniform sampler2D rock_color : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform vec3 projection_offset = vec3(0.0);
uniform float pattern_scale = 1.1;
uniform float mineral_metallic = .22;
uniform int mineral_mode = 0;
varying vec3 p_local;
varying vec3 n_local;
varying mat3 normal_to_view;
float luminance(vec3 c) { return dot(c,vec3(.2126,.7152,.0722)); }
float precious_mask(vec3 c) {
 if(mineral_mode==1) return smoothstep(.085,.28,luminance(c));
 return smoothstep(.018,.085,c.r-c.b)*smoothstep(.008,.04,c.g-c.b);
}
vec2 gradient(vec2 uv,vec3 center) {
 vec2 texel=1.0/vec2(textureSize(rock_color,0));
 float h=luminance(center);
 return clamp(vec2(luminance(texture(rock_color,uv+vec2(texel.x,0)).rgb)-h,
 luminance(texture(rock_color,uv+vec2(0,texel.y)).rgb)-h)*1.2,vec2(-.035),vec2(.035));
}
void vertex() {
 p_local=VERTEX+projection_offset;
 n_local=NORMAL;
 normal_to_view=mat3(MODELVIEW_MATRIX);
}
void fragment() {
 vec3 n=normalize(n_local);
 vec3 w=pow(abs(n),vec3(5.0));
 w/=max(dot(w,vec3(1)),.0001);
 vec3 p=p_local*pattern_scale;
 vec3 a=texture(rock_color,p.zy).rgb;
 vec3 b=texture(rock_color,p.xz).rgb;
 vec3 c=texture(rock_color,p.xy).rgb;
 vec3 rock=a*w.x+b*w.y+c*w.z;
 float iron=1.0-smoothstep(.055,.15,luminance(rock));
 float rust=smoothstep(.01,.07,rock.r-rock.b);
 ALBEDO=rock;
 METALLIC=iron*(1.0-rust)*mineral_metallic;
 ROUGHNESS=mix(.91,.67,iron*(1.0-rust));
 SPECULAR=.25;
 if(mineral_mode!=0) {
  // Classify each projection before blending, so narrow seams retain their metal response.
  float metal_mask=clamp(precious_mask(a)*w.x+precious_mask(b)*w.y+precious_mask(c)*w.z,0.0,1.0);
  float grain=mix(.78,1.0,smoothstep(.04,.55,luminance(rock)));
  vec3 metal_color=mineral_mode==1?vec3(.78,.84,.92):vec3(.95,.61,.095);
  ALBEDO=mix(rock,metal_color*grain,metal_mask*.82);
  METALLIC=metal_mask*mineral_metallic;
  ROUGHNESS=mix(.9,mineral_mode==1?.16:.20,metal_mask);
  SPECULAR=.5;
  CLEARCOAT=metal_mask*.25;
  CLEARCOAT_ROUGHNESS=.15;
 }
 // Artistic shallow relief derived from albedo, not a measured normal map.
 vec2 ga=gradient(p.zy,a), gb=gradient(p.xz,b), gc=gradient(p.xy,c);
 vec3 detail=vec3(0,-ga.y,-ga.x)*w.x+vec3(-gb.x,0,-gb.y)*w.y+vec3(-gc.x,-gc.y,0)*w.z;
 NORMAL=normalize(normal_to_view*normalize(n+detail));
}
