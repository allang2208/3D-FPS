float r=saturate(UV.y),theta=UV.x*6.2831853;
float across=r*cos(theta);
float strands=pow(.5+.5*sin(across*75+sin(theta*3)*.7),10);
float warning=exp(-pow((Phase-.48)/.20,2))+exp(-pow((Phase-1.15)/.22,2));
float edge=1-smoothstep(.82,1,r);
float opacity=(.34+.30*strands)*Alpha*edge;
float3 tissue=lerp(float3(.17,.04,.035),float3(.75,.40,.29),strands);
return float4(tissue*(.9+.7*warning),opacity);
