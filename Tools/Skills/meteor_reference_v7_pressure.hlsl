float2 p=UV-.5;
float r=length(p);
float a=atan2(p.y,p.x);
float phase=Dynamic.x;
// Dynamic.w is the sprite width in cm: keep the front physically thin as it expands.
float diameter=max(135,Dynamic.w);
float halfWidth=clamp(9/diameter,.0035,.025);
float ripple=(sin(a*9+phase*1.3)*8+sin(a*23-phase)*4)/diameter;
float front=.410+ripple;
float band=1-smoothstep(halfWidth*.35,halfWidth*1.7,abs(r-front));
float noise=saturate(.5+.24*sin(a*11+phase)+.20*sin(a*27-phase*2)+.16*sin(a*43));
float breakup=lerp(1,smoothstep(.26,.65,noise),smoothstep(.14,.86,phase));
float wakeWidth=clamp(55/diameter,.018,.13);
float wake=(1-smoothstep(halfWidth,wakeWidth,front-r))*step(r,front)*.26;
float grain=.52+.48*noise;
return saturate((band+wake)*grain*breakup*(1-smoothstep(.45,.49,r)));
