shader_type spatial;
render_mode cull_disabled;
uniform float spread=0.0;
uniform float clock=0.0;
uniform float seed_phase=0.0;
uniform float opacity=1.0;
varying vec2 p;
float hash(vec2 v){
 vec3 q=fract(vec3(v.xyx)*.1031);
 q+=dot(q,q.yzx+33.33);
 return fract((q.x+q.y)*q.z);
}
float noise(vec2 v){
 vec2 i=floor(v),f=fract(v);
 f=f*f*f*(f*(f*6.0-15.0)+10.0);
 return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x),f.y);
}
float fbm(vec2 v){
 float a=noise(v)*.57;
 v=mat2(vec2(.80,.60),vec2(-.60,.80))*v*2.07;
 a+=noise(v+7.4)*.28;
 a+=noise(v*2.03+18.1)*.15;
 return a;
}
void vertex(){p=VERTEX.xz;}
void fragment(){
 if(UV.x>spread)discard;
 float t=clock;
 vec2 offset=vec2(seed_phase*.73,seed_phase*.31);
 vec2 flow=vec2(t*.009,-t*.006);
 vec2 q=p*3.0+offset;
 vec2 warp=vec2(fbm(q*.67+flow),fbm(q*.71+4.8-flow));
 float body=fbm(q+warp*1.7+flow);
 float sediment=fbm(q*2.8+warp*.7);
 float grain=noise(p*155.0+offset);
 float edge=smoothstep(.88,1.0,UV.x);
 vec3 olive=vec3(.066,.079,.017);
 vec3 ochre=vec3(.145,.139,.046);
 vec3 col=mix(olive,ochre,smoothstep(.25,.79,body));
 col*=.88+.19*sediment;
 // Sparse pale suspended matter, not repeated outlined bubbles.
 float speck=smoothstep(.84,.95,grain)*smoothstep(.57,.77,sediment);
 col=mix(col,vec3(.25,.235,.12),speck*.27);
 col=mix(col,vec3(.052,.059,.021),edge*.52);
 float h=.0022*fbm(q*3.0+flow)+.00022*grain;
 // Bump gradient in the actual surface tangent plane, including sloped terrain.
 vec3 dpdx=dFdx(VERTEX);
 vec3 dpdy=dFdy(VERTEX);
 vec3 r1=cross(dpdy,NORMAL);
 vec3 r2=cross(NORMAL,dpdx);
 float det=dot(dpdx,r1);
 vec3 gradient=sign(det)*(dFdx(h)*r1+dFdy(h)*r2);
 NORMAL=normalize(abs(det)*NORMAL-gradient);
 ALBEDO=col;
 ROUGHNESS=mix(.20,.32,sediment)+edge*.08;
 SPECULAR=.5;
 METALLIC=0.0;
 CLEARCOAT=.42;
 CLEARCOAT_ROUGHNESS=.19;
 ALPHA=opacity*(1.0-edge*.42);
}
