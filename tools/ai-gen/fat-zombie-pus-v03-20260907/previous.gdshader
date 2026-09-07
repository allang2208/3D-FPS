shader_type spatial;
render_mode cull_disabled;
uniform float spread = 0.0;
uniform float clock = 0.0;
uniform float seed_phase = 0.0;
uniform float opacity = 1.0;
varying vec2 p;
float hash(vec2 v){return fract(sin(dot(v,vec2(127.1,311.7)))*43758.5453);}
float noise(vec2 v){
 vec2 i=floor(v), f=fract(v);f=f*f*(3.0-2.0*f);
 return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x),f.y);
}
void vertex(){p=VERTEX.xz;}
void fragment(){
 if(UV.x>spread)discard;
 float t=clock+seed_phase;
 vec2 q=p*3.3+vec2(sin(t*.23),cos(t*.19))*.25;
 float n=noise(q+vec2(noise(q*.7+t*.08),noise(q*.8-t*.06)));
 float fine=noise(q*5.0+vec2(t*.06,-t*.09));
 float veins=smoothstep(.38,.48,n)*(1.0-smoothstep(.50,.58,n));
 vec3 deep=vec3(.035,.06,.003);
 vec3 ochre=vec3(.19,.23,.014);
 vec3 col=mix(deep,ochre,smoothstep(.15,.82,n));
 col=mix(col,vec3(.30,.32,.04),veins*.22+smoothstep(.79,.92,fine)*.20);
 vec2 cell=floor(p*3.5);vec2 f=fract(p*3.5)-.5;
 float phase=fract(t*.36+hash(cell));
 float radius=phase*.32;
 float ring=(1.0-smoothstep(.012,.038,abs(length(f)-radius)))*(1.0-phase);
 col+=ring*.022;
 col=mix(col,vec3(.07,.09,.007),smoothstep(.93,1.0,UV.x)*.5);
 NORMAL=normalize(NORMAL+vec3(sin(p.x*16.0+t*.8)*.075,cos(p.y*14.0-t*.65)*.075,0.0));
 ALBEDO=col;ROUGHNESS=.23+.13*n;SPECULAR=.55;METALLIC=0.0;
 ALPHA=opacity;
}
