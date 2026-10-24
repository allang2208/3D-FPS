
struct AP19Shapes {
 float segment(float2 p,float2 a,float2 b,float width,float aa){float2 q=p-a,v=b-a;float d=length(q-v*saturate(dot(q,v)/dot(v,v)));return 1-smoothstep(max(0,width-aa),width+aa,d);}
}; AP19Shapes shape;
float2 Foot=max(abs(ddx(UV))+abs(ddy(UV)),.0001);float3 Color=0;
float aa=clamp(max(Foot.x,Foot.y)*1.25,.0015,.12);
float2 p=UV-float2(.5,.34);float r=length(p),angle=atan2(p.y,p.x);
float ring=(1-smoothstep(max(0,.005-aa),.005+aa,abs(r-.245)))*.005/max(.005,aa);
float gate=smoothstep(-.15,.15,sin(angle*3-T*.28));
ring*=.24+.76*gate;
float glyph=0;
if(Style<.5){
 glyph=max(shape.segment(p,float2(-.115,.105),float2(0,-.13),.009,aa),shape.segment(p,float2(0,-.13),float2(.115,.105),.009,aa));
 glyph=max(glyph,shape.segment(p,float2(-.069,.027),float2(.069,.027),.009,aa));
 float diamond=abs(abs(p.x)+abs(p.y)-.175);
 glyph=max(glyph,(1-smoothstep(max(0,.003-aa),.003+aa,diamond))*.20);
} else {
 for(int k=0;k<3;k++){
  float a=T*.095+k*1.04719755;float2 q=float2(cos(a)*p.x-sin(a)*p.y,sin(a)*p.x+cos(a)*p.y);
  float d=abs(length(q*float2(1,2.5))-.175);
  glyph=max(glyph,(1-smoothstep(max(0,.006-aa),.006+aa,d))*.006/max(.006,aa));
 }
 glyph=max(glyph,1-smoothstep(.023,.023+aa,r));
}
float text=Texture2DSampleGrad(Glyph,GlyphSampler,UV,ddx(UV),ddy(UV)).a;
float scan=.90+.10*exp(-pow((UV.y-(.48+.35*sin(T*.22)))/.08,2));
Color=(Tint*(glyph+ring*.55)+lerp(Tint,float3(1,1,1),.65)*text)*Gain*scan*Night;
return Color;