// Surface-aligned thin splash. Fade well before the edges of its plane.
float2 p=(UV-.5)*2;
float angle=atan2(p.y,p.x),r=length(p);
float phase=Seed*6.283185;
float rim=.74+.055*sin(angle*5+phase)+.04*sin(angle*9-phase*1.7);
float body=1-smoothstep(rim-.065,rim+.035,r);
float fingers=pow(saturate(.5+.5*sin(angle*11+phase)),7);
float corona=(1-smoothstep(rim+.025,rim+.16*fingers+.045,r))*smoothstep(.48,.64,r);
float tear=smoothstep(.64,.92,r)*smoothstep(.4,.86,Age);
float ripple=sin(r*37-Age*18+sin(angle*4+phase)*1.2);
float holes=smoothstep(.67,.95,sin(p.x*19+phase)*sin(p.y*17-phase));
float mask=max(body,corona)*(1-tear*holes);
mask*=1-smoothstep(.94,.99,max(abs(p.x),abs(p.y)));
float alpha=saturate(mask*Opacity*(.69+.12*ripple));
return float4(alpha,.45+.3*ripple,smoothstep(rim-.09,rim,r),ripple);
