// Post-tonemap foreground-safe yaw blur; no temporal history is accumulated.
// Inputs wire PostProcessInput0 and CustomStencil into the material compiler.
float3 center = ColorInput.rgb;
if (Strength < 0.0001 || abs(StencilInput.r - 231.0) < 0.5) return center;
float2 uv = GetViewportUV(Parameters);
float2 pixel = GetSceneTextureViewSize(14).zw;
// Protect antialiased hand/shoulder edges as well as their solid interiors.
const float2 edges[8] = {float2(1,0),float2(-1,0),float2(0,1),float2(0,-1),
    float2(1,1),float2(-1,1),float2(1,-1),float2(-1,-1)};
[unroll] for (int e=0; e<8; ++e)
{
    float2 edgeUV = saturate(uv + edges[e]*pixel*2.0);
    float mask = SceneTextureLookup(ViewportUVToSceneTextureUV(edgeUV,25),25,false).r;
    if (abs(mask-231.0)<0.5) return center;
}
float2 p=uv*2.0-1.0;
// A yaw turn flows mainly horizontally, with perspective curvature at edges.
// Maximum one-sided spread is 1.17% width at the authored 0.65 peak strength.
float2 flow=float2(1.0+0.35*p.x*p.x,0.35*p.x*p.y);
flow*=0.018*saturate(Strength)/1.35;
float3 sum=center;
float weight=1.0;
[unroll] for(int i=-4;i<=4;++i)
{
    if(i==0)continue;
    float a=i/4.0;
    float2 sampleUV=clamp(uv+flow*a,pixel*0.5,1.0-pixel*0.5);
    float mask=SceneTextureLookup(ViewportUVToSceneTextureUV(sampleUV,25),25,false).r;
    // Never pull foreground colors into the blurred background.
    if(abs(mask-231.0)<0.5)continue;
    float w=1.0-0.75*abs(a);
    sum+=SceneTextureLookup(ViewportUVToSceneTextureUV(sampleUV,14),14,true).rgb*w;
    weight+=w;
}
return sum/weight;
