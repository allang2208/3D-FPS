// Same seeded Noise5/ellipse as TemperateForestHabitat::RainforestWeight.
if(Control.x<=0) return 0;
float2 q=(P.xy-Region.xy)/max(Region.zw,1);
float d=length(q); if(d>1.1) return 0;
float2 r=P.xy/3800; r=float2(r.x*.8-r.y*.6,r.x*.6+r.y*.8);
int2 cell=(int2)floor(r);float2 f=frac(r);f=f*f*f*(f*(f*6-15)+10);
uint4 x=(uint4)int4(cell.x,cell.x+1,cell.x,cell.x+1)*0x9e3779b9U;
uint4 y=(uint4)int4(cell.y,cell.y,cell.y+1,cell.y+1)*0x85ebca6bU+0x1b873593U;
uint s=((uint)Control.z|((uint)Control.w<<16))+3511U;
x^=x>>16;x*=0x7feb352dU;x^=x>>15;x*=0x846ca68bU;x^=x>>16;
y^=y>>16;y*=0x7feb352dU;y^=y>>15;y*=0x846ca68bU;y^=y>>16;
s^=s>>16;s*=0x7feb352dU;s^=s>>15;s*=0x846ca68bU;s^=s>>16;
uint4 k=x^y^s;
k^=k>>16;k*=0x7feb352dU;k^=k>>15;k*=0x846ca68bU;k^=k>>16;
k^=k>>16;k*=0x7feb352dU;k^=k>>15;k*=0x846ca68bU;k^=k>>16;
float4 v=float4(k&0x00ffffffU)/16777216.0*2-1;
float n=lerp(lerp(v.x,v.y,f.x),lerp(v.z,v.w,f.x),f.y);
return Control.x*(1-smoothstep(1-Control.y,1,d+n*.09));
