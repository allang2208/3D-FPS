// Seeded impact lobes and satellites; all coverage stays inside the decal.
float age=max(0,Clock-ImpactTime);
float spread=lerp(.66,1,smoothstep(0,.24,age));
float2 p=(UV-.5)*2/spread;
float theta=atan2(p.y,p.x),seed=Seed*6.283185;
float boundary=.59+.085*sin(theta*5+seed)+.052*sin(theta*9-seed*1.7);
float drying=1-saturate(Life);
float grain=sin(p.x*45+sin(p.y*31)+seed)*sin(p.y*39-seed);
float radius=length(p);
float d=radius-boundary+.045*drying+grain*.017;
float coverage=1-smoothstep(-.02,.028,d);
for(int i=0;i<6;i++) {
 float h=frac(sin(float(i)*73.31+Seed*173.7)*43758.5453);
 float angle=float(i)*2.39996+seed;
 float2 center=float2(cos(angle),sin(angle))*(.68+h*.10);
 float r=.021+.040*frac(h*13.73);
 coverage=max(coverage,1-smoothstep(r*.60,r,length(p-center)));
}
float edge=min(min(UV.x,1-UV.x),min(UV.y,1-UV.y));
float flow=sin(p.x*10+sin(p.y*7+seed)+age*.8)*sin(p.y*11-age*.53+seed);
float bubbles=smoothstep(.88,.99,sin(p.x*27+seed)*sin(p.y*29-seed+age*.5));
return float4(saturate(coverage)*Life*.82*smoothstep(.012,.045,edge),
              flow*.5+.5,bubbles*(1-drying),drying);
