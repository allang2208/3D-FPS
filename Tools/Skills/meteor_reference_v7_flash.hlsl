float2 p=UV-.5;
float r=length(p*float2(1,1.12));
float angle=atan2(p.y,p.x);
float edge=.35+.018*sin(angle*9)+.012*sin(angle*17+1.2);
float core=1-smoothstep(.06,edge,r);
float rays=pow(saturate(.5+.5*cos(angle*8+.2)),18)*(1-smoothstep(.10,.49,r))*.30;
return saturate(core*core+rays);
