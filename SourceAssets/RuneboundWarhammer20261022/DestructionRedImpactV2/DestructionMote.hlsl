// Crimson shards and thin radial streaks use the same bounded camera-facing pool.
float2 d=(UV-.5)*2.;
float diamond=abs(d.x)+abs(d.y);
float core=1.-smoothstep(.1,.38,diamond);
float body=1.-smoothstep(.22,.8,diamond);
float halo=max(0.,exp(-dot(d,d)*5.)-exp(-5.));
float alpha=saturate(core*.92+body*.44+halo*.28)*Strength;
float3 rgb=lerp(float3(2.5,.014,.006),float3(5.0,.24,.035),core);
return float4(rgb,alpha);
