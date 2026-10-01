// The geometry bake uses the same UV0 tangent basis as the source detail.
float3 detail = normalize(float3(N.xy * SourceStrength, N.z));
float3 bevel = normalize(float3(Edge.xy * EdgeStrength, Edge.z));
float3 t = bevel + float3(0,0,1);
float3 u = detail * float3(-1,-1,1);
return normalize(t * dot(t,u) / max(t.z,.001) - u);
