shader_type sky;
#include "res://assets/environment/day_night_atmosphere.gdshaderinc"
// No TIME: the controller refreshes sky lighting at 10 Hz, independently of FPS.
uniform vec3 sun_direction = vec3(0.0, 1.0, 0.0);
uniform vec3 zenith : source_color = vec3(0.16, 0.38, 0.68);
uniform vec3 horizon : source_color = vec3(0.68, 0.77, 0.85);
uniform float daylight = 1.0;
uniform float twilight = 0.0;

void sky() {
 vec3 d = normalize(EYEDIR);
 float height = max(d.y, 0.0);
 vec3 color = atmosphere_color(d,sun_direction,zenith,horizon,twilight);
 float sun_dot = max(dot(d, sun_direction), 0.0);
 float moon_dot = max(dot(d, -sun_direction), 0.0);
 // Broad atmospheric glow and a small, antialiased solar disc.
 float sun_visible = smoothstep(-0.035,0.015,sun_direction.y);
 // Compact forward scattering; less haze overhead, a little more near sunset.
 float air_mass = 1.0-smoothstep(0.0,0.6,sun_direction.y);
 float solar_scatter = pow(sun_dot,1800.0)*0.055 + pow(sun_dot,260.0)*0.012*air_mass;
 color += vec3(1.0,0.72,0.44)*solar_scatter*sun_visible;
 color += vec3(5.0,3.9,2.6) * smoothstep(0.99992,0.99997,sun_dot) * sun_visible;
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
 // Clear-night halo: faint and confined to the immediate lunar surroundings.
 color += vec3(0.72,0.78,0.90) * pow(moon_dot, 5000.0) * 0.012 * moon_visible;
 color = mix(color, vec3(1.05,1.18,1.40)*lunar_detail,
   smoothstep(0.99982,0.99990,moon_dot)*moon_visible);
 // Stars use a separate instanced mesh so twinkling never invalidates radiance.
 COLOR = mix(horizon*0.35,color,smoothstep(-0.16,0.0,d.y));
}
