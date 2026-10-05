// Surface-aligned transient film; exact zero coverage beyond its wet silhouette.
float2 p=(UV-.5)*2;
float angle=atan2(p.y,p.x),r=length(p),phase=Seed*6.283185;
float rim=.73+.046*sin(angle*5+phase)+.032*sin(angle*9-phase*1.7);
float body=1-smoothstep(rim-.075,rim+.025,r);
float fingers=pow(saturate(.5+.5*sin(angle*11+phase)),7);
float corona=(1-smoothstep(rim+.015,rim+.15*fingers+.04,r))*smoothstep(.48,.64,r);
float tear=smoothstep(.59,.90,r)*smoothstep(.35,.85,Age);
float holes=smoothstep(.65,.94,sin(p.x*19+phase)*sin(p.y*17-phase));
float mask=max(body,corona)*(1-tear*holes);
mask*=1-smoothstep(.94,.99,max(abs(p.x),abs(p.y)));
float ripple=sin(r*33-Age*15+sin(angle*3+phase)*.7)*exp(-2.1*Age);
float patches=.5+.5*sin(p.x*8+phase)*cos(p.y*11-phase*.6);
float thickness=lerp(.14,.022,saturate(Age))*(.42+.58*(1-saturate(r)));
thickness*=lerp(.7,1.3,patches)+ripple*.10;
float coverage=saturate(mask*Opacity);
coverage=coverage<.003?0:coverage;
return float4(coverage,thickness,saturate(patches),ripple);
