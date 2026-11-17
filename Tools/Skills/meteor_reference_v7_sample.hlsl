// Packed flame/heat/smoke/shading. V7 alone adds a soft, irregular domain edge.
float2 p=UV;
p.x=Dynamic.y>.5?1-p.x:p.x;
float frame=saturate(Dynamic.x)*63;
float f0=floor(frame),f1=min(f0+1,63);
float2 c0=float2(fmod(f0,8),floor(f0/8));
float2 c1=float2(fmod(f1,8),floor(f1/8));
float2 inset=(4.5+saturate(p)*247)/256;
float4 a=Texture2DSampleLevel(Atlas,AtlasSampler,(c0+inset)/8,0);
float4 b=Texture2DSampleLevel(Atlas,AtlasSampler,(c1+inset)/8,0);
float4 fields=lerp(a,b,frac(frame));
float edgeX=smoothstep(0,.07,p.x)*(1-smoothstep(.93,1,p.x));
float base=p.y+.018*sin(p.x*27+1.2)+.010*sin(p.x*65);
float edgeY=smoothstep(0,.045,p.y)*(1-smoothstep(.84,1.015,base));
edgeY*=1-smoothstep(.97,1,p.y);
fields.rgb*=edgeX*edgeY;
// Later smoke fills the cropped simulation domain. Taper density as a cloud,
// rather than displaying that domain as a translucent rectangular card.
float2 cloud=(p-float2(.5,.51))*float2(2.05,1.95);
cloud+=.055*float2(sin(p.y*16+Dynamic.y*6),sin(p.x*19+Dynamic.y*4));
fields.b*=1-smoothstep(.55,1.03,length(cloud));
fields.b*=smoothstep(.16,.32,Dynamic.x);
return fields;
