shader_type sky;
#include "res://assets/environment/day_night_atmosphere.gdshaderinc"
// No TIME: the controller refreshes sky lighting at 10 Hz, independently of FPS.
uniform vec3 sun_direction = vec3(0.0, 1.0, 0.0);
uniform vec3 zenith : source_color = vec3(0.16, 0.38, 0.68);
uniform vec3 horizon : source_color = vec3(0.68, 0.77, 0.85);
uniform float daylight = 1.0;
uniform float twilight = 0.0;
uniform float sun_transmission : hint_range(0.0, 1.0) = 1.0;
uniform float moon_transmission : hint_range(0.0, 1.0) = 1.0;

void sky() {
 vec3 d = normalize(EYEDIR);
 float height = max(d.y, 0.0);
 vec3 color = atmosphere_color(d,sun_direction,zenith,horizon,twilight);
 float sun_dot = max(dot(d, sun_direction), 0.0);
 float moon_dot = max(dot(d, -sun_direction), 0.0);
 // The disc is physically small, but the eye/camera cannot resolve it through
 // the surrounding HDR glare. Work from angular delta without an expensive acos.
 float sun_visible = smoothstep(-0.035,0.015,sun_direction.y);
 float sun_delta = 1.0-sun_dot;
 float sun_disc = 1.0-smoothstep(0.000010,0.000052,sun_delta);
 float sun_inner_glare = exp(-sun_delta*250.0);
 float sun_outer_glare = exp(-sun_delta*35.0);
 vec3 sun_warm = mix(vec3(1.0,0.48,0.17),vec3(1.0,0.86,0.62),smoothstep(0.0,0.32,sun_direction.y));
 float sun_gate = sun_visible*sun_transmission;
 color += sun_warm*(sun_outer_glare*0.20 + sun_inner_glare*2.8)*sun_gate;
 color += vec3(30.0,25.0,18.0)*sun_disc*sun_gate;
 float moon_visible = smoothstep(-0.035,0.025,-sun_direction.y);
 // Moon surface detail is procedural; no external texture/license dependency.
 vec3 moon_right = normalize(cross(-sun_direction,vec3(0.0,1.0,0.0)));
 vec3 moon_up = cross(moon_right,-sun_direction);
 vec2 lunar_uv = vec2(dot(d,moon_right),dot(d,moon_up))/0.018;
 float lunar_detail = 0.86;
 lunar_detail -= 0.25*(1.0-smoothstep(0.13,0.42,length(lunar_uv-vec2(-0.23,0.18))));
 lunar_detail -= 0.18*(1.0-smoothstep(0.09,0.28,length(lunar_uv-vec2(0.22,0.35))));
 lunar_detail -= 0.16*(1.0-smoothstep(0.04,0.18,length(lunar_uv-vec2(0.32,-0.30))));
 lunar_detail += 0.035*sin(lunar_uv.x*35.0)*sin(lunar_uv.y*27.0);
 // The moon remains readable while its HDR core feeds a cool photographic bloom.
 float moon_gate = moon_visible*moon_transmission;
 float moon_delta = 1.0-moon_dot;
 float moon_inner_halo = exp(-moon_delta*720.0);
 float moon_outer_halo = exp(-moon_delta*70.0);
 color += vec3(0.50,0.68,1.0)*(moon_inner_halo*0.24+moon_outer_halo*0.045)*moon_gate;
 float moon_disc = smoothstep(0.99982,0.99990,moon_dot)*moon_gate;
 color = mix(color,vec3(3.2,3.8,5.2)*lunar_detail,moon_disc);
 // Stars use a separate instanced mesh so twinkling never invalidates radiance.
 COLOR = mix(horizon*0.35,color,smoothstep(-0.16,0.0,d.y));
}
