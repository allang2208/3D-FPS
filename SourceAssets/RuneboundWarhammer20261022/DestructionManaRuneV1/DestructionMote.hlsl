// Bounded blue-violet fragments with a hard diamond core and a soft blue halo.
float2 d=(UV-.5)*2.;
float diamond=abs(d.x)+abs(d.y);
float core=1.-smoothstep(.13,.4,diamond);
float halo=exp(-dot(d,d)*5.)-exp(-5.);
float alpha=saturate(core*.9+halo*.4)*Strength;
float3 rgb=lerp(float3(.42,.2,1.3),float3(1.2,1.9,3.8),core);
return float4(rgb,alpha);
