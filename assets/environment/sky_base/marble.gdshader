shader_type spatial;
uniform vec4 stone_color : source_color = vec4(0.86, 0.87, 0.85, 1.0);
uniform vec4 vein_color : source_color = vec4(0.35, 0.43, 0.49, 1.0);
uniform float stone_roughness = 0.40;
uniform bool individual_slab = false;
uniform bool masonry_courses = false;
// Defaults preserve the hub slabs; small voxel pieces need finer veining.
uniform float slab_pattern_scale = 0.7;
uniform float vein_strength = 0.20;
uniform bool fine_slab_detail = false;
varying vec3 stone_position;
varying vec3 local_stone_position;
varying flat float piece_seed;
float hash3(vec3 p) {
 p = fract(p * 0.1031); p += dot(p, p.yzx + 33.33);
 return fract((p.x + p.y) * p.z);
}
float noise3(vec3 p) {
 vec3 i = floor(p); vec3 f = fract(p); f = f*f*(3.0-2.0*f);
 return mix(mix(mix(hash3(i),hash3(i+vec3(1,0,0)),f.x),mix(hash3(i+vec3(0,1,0)),hash3(i+vec3(1,1,0)),f.x),f.y),mix(mix(hash3(i+vec3(0,0,1)),hash3(i+vec3(1,0,1)),f.x),mix(hash3(i+vec3(0,1,1)),hash3(i+vec3(1,1,1)),f.x),f.y),f.z);
}
void vertex() {
 stone_position = (MODEL_MATRIX * vec4(VERTEX,1.0)).xyz;
 local_stone_position = VERTEX;
 piece_seed = hash3(MODEL_MATRIX[3].xyz + vec3(4.1,7.8,1.3));
}
void fragment() {
 vec3 p = stone_position * 0.6;
 if (individual_slab) {
  float angle = piece_seed * 6.283185;
  vec2 rotated = mat2(vec2(cos(angle),sin(angle)),vec2(-sin(angle),cos(angle))) * local_stone_position.xz;
  p = vec3(rotated.x,local_stone_position.y,rotated.y)*slab_pattern_scale+vec3(piece_seed*37.0);
 }
 float cloud = noise3(p * 0.8) * 0.78 + noise3(p * 2.3) * 0.17 + noise3(p * 6.4) * 0.05;
 float warp = noise3(p*1.7+vec3(8.2,1.3,4.6));
 float fine_warp = fine_slab_detail ? noise3(p*7.0)*.65 + noise3(p*18.0)*.18 : 0.0;
 float wave = abs(sin(p.x * 2.4 + p.z * 0.65 + p.y * 0.4 + cloud * 5.5 + warp*1.6 + fine_warp));
 float aa = max(fwidth(wave), 0.006);
 float vein = 1.0 - smoothstep(0.016, 0.07 + aa, wave);
 float halo = 1.0 - smoothstep(0.04, 0.36, wave);
 float grain = noise3(p*44.0);
 float variation = individual_slab ? mix(.95,1.025,piece_seed) : 1.0;
 ALBEDO = mix(stone_color.rgb * (0.94 + cloud * 0.08)*variation, vein_color.rgb, vein * vein_strength + halo * 0.065);
 if (fine_slab_detail) {
  float branch_wave = abs(sin(p.x*5.3-p.y*2.1+p.z*3.4+cloud*12.0+warp*4.0));
  float branch = 1.0-smoothstep(.012,.045+fwidth(branch_wave),branch_wave);
  ALBEDO *= .91 + cloud*.14;
  ALBEDO = mix(ALBEDO,vein_color.rgb,branch*.12*smoothstep(.15,.65,warp));
 }
 ROUGHNESS = clamp(stone_roughness + vein * 0.06 + (grain-.5)*.045, .22,.65);
 if (masonry_courses) {
  float row = floor(stone_position.y/.4);
  vec2 joints = abs(fract(vec2(stone_position.x+stone_position.z+mod(row,2.0),stone_position.y)/vec2(2.0,.4))-.5);
  vec2 aa_joint = max(fwidth(joints),vec2(.001));
  float mortar = max(smoothstep(.496-aa_joint.x,.5,joints.x),smoothstep(.487-aa_joint.y,.5,joints.y));
  ALBEDO = mix(ALBEDO,stone_color.rgb*.60,mortar*.65);
  ROUGHNESS = mix(ROUGHNESS,.72,mortar);
 }
 SPECULAR = 0.38;
}
