shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, fog_disabled;
uniform float animation_time = 0.0;
uniform float night_visibility = 0.0;
uniform vec3 moon_direction = vec3(0.0,1.0,0.0);
varying vec4 star_parameters;
varying vec3 direction;
void vertex() {
 star_parameters = INSTANCE_CUSTOM;
 direction = normalize((MODEL_MATRIX*vec4(VERTEX,1.0)).xyz-CAMERA_POSITION_WORLD);
}
void fragment() {
 vec2 p = UV*2.0-1.0;
 float radius2 = dot(p,p);
 float core = exp(-radius2*8.0)*(1.0-smoothstep(0.55,1.0,radius2));
 float phase = star_parameters.r*6.283185;
 float frequency = star_parameters.g;
 // Two independent periods prevent synchronized breathing or on/off blinking.
 float wave = sin(animation_time*frequency+phase)*0.65
   +sin(animation_time*frequency*1.731+phase*2.37)*0.35;
 float twinkle = 1.0+wave*star_parameters.b;
 float extinction = smoothstep(0.015,0.25,direction.y);
 float moon_dot = max(dot(direction,moon_direction),0.0);
 float moon_wash = (1.0-0.85*pow(moon_dot,100.0))
   *(1.0-smoothstep(0.99976,0.99982,moon_dot));
 ALBEDO = COLOR.rgb*star_parameters.a*twinkle;
 ALPHA = core*night_visibility*extinction*moon_wash;
}
