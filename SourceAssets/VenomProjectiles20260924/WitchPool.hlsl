// Landing footprint shared with CPU damage. World projection follows the visible ground.
float age=max(0,Clock-StartTime);
float spread=lerp(.025,1,smoothstep(0,.30,age));
float2 p=(Position.xy-Center.xy)/max(1,Radius);
float r=length(p),theta=atan2(p.y,p.x),seed=Seed*6.283185;
float sector=frac(theta/6.283185307+1)*16;
int i=(int)floor(sector);
float reach[16]={Reach0.x,Reach0.y,Reach0.z,Reach0.w,Reach1.x,Reach1.y,Reach1.z,Reach1.w,
                 Reach2.x,Reach2.y,Reach2.z,Reach2.w,Reach3.x,Reach3.y,Reach3.z,Reach3.w};
float boundary=lerp(reach[i],reach[(i+1)%16],frac(sector));
float edge=boundary*spread;
float rim=(1-smoothstep(max(0,edge-.025),max(.001,edge),r))*step(.001,boundary);
float body=.86+.035*sin(theta*5+seed)+.030*sin(theta*9-seed*.73);
float thick=1-smoothstep(body*edge-.04,body*edge+.025,r);
float2 q=p*8+float2(seed,-seed*.61);
float t=age*.45;
q+=float2(sin(q.y+t),cos(q.x-t*.71))*.32;
float flow=.5+.5*sin(q.x-t*.9)*cos(q.y+t*.63);
float2 cell=floor(q*1.6),f=frac(q*1.6)-.5;
float h=frac(sin(dot(cell,float2(127.1,311.7))+seed)*43758.5453);
float2 centerOffset=float2(frac(h*13.3),frac(h*37.9))*.48-.24;
float cycle=frac(age*.35+h);
float br=.06+.10*sin(cycle*3.14159);
float bd=length(f-centerOffset);
float bubble=exp(-pow((bd-br)/.032,2))*sin(cycle*3.14159)*step(.70,h);
float impact=exp(-pow((r-age*1.35)/.035,2))*exp(-age*3.3);
// Cosmetic fade begins only after the last scheduled damage pulse at 6 seconds.
float fade=1-smoothstep(6,6.6,age);
float3 surfaceNormal=normalize(cross(ddx(Position),ddy(Position)));
float facing=smoothstep(.6,.86,abs(dot(surfaceNormal,normalize(SurfaceNormal))));
float height=1-smoothstep(48,50,abs(Position.z-Center.z));
return float4(rim*(.40+.49*thick)*fade*facing*height,flow,
              saturate(bubble*.55+impact*.7)*thick,saturate((age-5.8)/.8));
