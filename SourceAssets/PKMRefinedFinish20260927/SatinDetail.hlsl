// SVD-style physical satin grain, carried in undeformed local centimeters.
// Keep sparse PKM handling marks; never replace UV0 structural normals.
__SCRATCH_HELPER__
FinishNoise f;
float3 weights=pow(abs(normalize(N)),float3(6,6,6));
weights/=max(dot(weights,float3(1,1,1)),.0001);
float scratch=dot(weights,float3(f.marks(P.yz,2),f.marks(P.xz,11),f.marks(P.xy,23)));
float3 q=P/5.0;
float grain=dot(weights,float3(
    Texture2DSample(FinishTex,FinishTexSampler,q.yz*float2(2.4,1)).r,
    Texture2DSample(FinishTex,FinishTexSampler,q.xz*float2(2.4,1)).r,
    Texture2DSample(FinishTex,FinishTexSampler,q.xy*float2(2.4,1)).r));
return float4(saturate(scratch),grain,0,.5);
