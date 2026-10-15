float r=saturate(UV.y),theta=UV.x*6.2831853;
float broken=.5+.5*sin(theta*9+sin(theta*4)*2+Phase*13);
float ridge=exp(-pow((r-.66-.12*sin(theta*7+Phase*8))/.16,2));
float ripples=.5+.5*sin(r*39-Phase*28+theta*3);
float edge=smoothstep(0,.12,r)*(1-smoothstep(.88,1,r));
return float4(lerp(float3(.33,.35,.36),float3(1.15,1.18,1.20),ridge),
    saturate((.13+.60*ridge*(.35+.65*broken)+.16*ripples)*edge*Alpha));
