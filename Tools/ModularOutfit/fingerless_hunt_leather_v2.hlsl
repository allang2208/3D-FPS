// Metric UV0 is also the mesh's tangent basis. Grain is an unpacked UE normal.
float palm=saturate(Fields.x);
float edgeCm=max(Fields.y,0);
float inside=saturate(Details.y);
float hem=exp(-pow((edgeCm-.13)/.085,2));
float stitchBand=exp(-pow((edgeCm-.25)/.045,2));
float thread=stitchBand*(1-smoothstep(.24,.44,abs(frac(Details.x/.26)-.5)))*(1-inside);
float contact=palm*.45+hem*.32;
float rough=clamp(.33+RoughScan.r*.38+palm*.055-contact*.09+inside*.16,.32,.82);
float3 col=Color.rgb*lerp(1,.86,contact)*lerp(1,Cavity.r,.14)*lerp(1,AO.r,.10);
col*=lerp(1,.62,inside);
col=lerp(col,float3(.21,.12,.054),thread*.66);
float strength=.85*lerp(1,.55,palm)*lerp(1,.38,hem)*lerp(1,.3,inside);
OutNormal=normalize(float3(Grain.xy*strength,max(Grain.z,.1)));
OutRoughness=lerp(rough,.76,thread);
OutSpecular=clamp(.28+(.12*(SpecScan.r-.20)),.24,.34)*(1-inside*.22);
return col;
