float2 d=(UV-.5)*2.;
float radius=dot(d,d);
float a=saturate(exp(-radius*5.)-exp(-5.))*Strength;
return float4(float3(.16,.48,1.0)*(1.0+exp(-radius*20.)*2.),a*.8);
