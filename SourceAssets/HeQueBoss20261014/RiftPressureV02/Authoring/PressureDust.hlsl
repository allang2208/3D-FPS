float r=saturate(UV.y),theta=UV.x*6.2831853;
float noise=.5+.5*sin(theta*7+r*19-Phase*9+sin(theta*13-r*27)*.8);
float wisps=smoothstep(.25,.75,noise);
float edge=smoothstep(0,.12,r)*(1-smoothstep(.60,1,r));
return float4(lerp(float3(.16,.14,.11),float3(.48,.45,.39),wisps),edge*(.12+.40*wisps)*Alpha);
