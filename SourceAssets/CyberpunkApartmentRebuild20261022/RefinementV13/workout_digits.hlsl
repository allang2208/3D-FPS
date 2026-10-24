// Four digits display actual active-session minutes/seconds, never a fabricated pulse.
float2 p=(UV-float2(.06,.39))/float2(.56,.34);
if(any(p<0)||any(p>1))return Base;
float cell=floor(p.x*4);float2 q=float2(frac(p.x*4),p.y);
int elapsed=(int)min(Elapsed,5999.0);int value=cell<.5?(elapsed/600)%10:cell<1.5?(elapsed/60)%10:cell<2.5?(elapsed/10)%6:elapsed%10;
int masks[10]={63,6,91,79,102,109,125,7,127,111};int mask=masks[value];float shape=0;
float2 centers[7]={float2(.5,.08),float2(.82,.28),float2(.82,.72),float2(.5,.92),float2(.18,.72),float2(.18,.28),float2(.5,.5)};
for(int i=0;i<7;++i){float2 size=(i==0||i==3||i==6)?float2(.28,.035):float2(.035,.17);float2 dist=abs(q-centers[i])-size;float sd=max(dist.x,dist.y);float aa=max(fwidth(sd),.004);shape=max(shape,(1-smoothstep(-aa,aa,sd))*float((mask>>i)&1));}
return lerp(Base,float3(.59,.82,.86),shape*.9);
