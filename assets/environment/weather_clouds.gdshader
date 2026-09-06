shader_type spatial;
render_mode unshaded, cull_front, depth_draw_never, fog_disabled;
uniform sampler2D cloud_texture : filter_linear, repeat_enable;
uniform vec2 drift = vec2(0.0);
uniform float coverage = 0.0;
uniform vec3 cloud_color : source_color = vec3(0.4);
uniform float flash = 0.0;
varying vec3 world_position;
void vertex() { world_position=(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz; }
void fragment() {
 vec3 d=normalize(world_position-CAMERA_POSITION_WORLD);
 vec2 uv=d.xz/max(d.y,0.12)*0.12+drift;
 float density=texture(cloud_texture,uv).r;
 float detail=texture(cloud_texture,uv*3.7+vec2(0.31,0.17)).r;
 float opacity=smoothstep(1.0-coverage,1.18-coverage,density);
 float relief=mix(0.55,1.25,density)*mix(0.75,1.12,detail);
 ALBEDO=cloud_color*relief+vec3(flash*0.5);
 ALPHA=opacity*smoothstep(-0.02,0.15,d.y);
}
