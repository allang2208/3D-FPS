// Shared by the sky and distant scenery, in linear color space.
vec3 atmosphere_color(vec3 direction, vec3 sun, vec3 top, vec3 rim, float dusk) {
 float elevation = max(direction.y, 0.0);
 float gradient = 1.0-exp(-elevation*3.2);
 vec3 color = mix(rim,top,gradient);
 float facing = max(dot(direction,sun),0.0);
 color += vec3(0.30,0.075,0.012)*dusk*pow(facing,8.0)*exp(-elevation*7.0);
 return color;
}
