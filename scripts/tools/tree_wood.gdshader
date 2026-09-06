shader_type spatial;
render_mode cull_disabled;
void fragment() {
	vec2 p=UV*2.0-1.0;
	float angle=atan(p.y,p.x);
	float radius=length(p)+0.014*sin(angle*5.0+length(p)*8.0);
	float ring=sin(radius*66.0+sin(angle*3.0)*0.45);
	float dark_ring=smoothstep(0.45,0.97,ring);
	float fibres=sin(p.x*157.0+sin(p.y*43.0)*0.5)*0.025;
	ALBEDO=vec3(0.34,0.225,0.13)*(1.0-dark_ring*0.18+fibres);
	ROUGHNESS=0.95;
}
