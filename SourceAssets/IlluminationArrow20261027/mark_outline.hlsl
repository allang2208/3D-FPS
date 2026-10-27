// Only the scoped mark stencil 236 is consumed. Marking itself respects solid cover.
// A marked silhouette remains readable behind cover for the remaining debuff time.
float3 scene=ColorInput.rgb;
float2 uv=GetViewportUV(Parameters);
float2 pixel=GetSceneTextureViewSize(14).zw;
if(abs(StencilInput.r-236)<.5)return scene;
float edge=0;
float2 directions[8]={float2(1,0),float2(-1,0),float2(0,1),float2(0,-1),
    float2(.707,.707),float2(-.707,.707),float2(.707,-.707),float2(-.707,-.707)};
[unroll]for(int i=0;i<8;i++)
{
    float2 tap=uv+directions[i]*pixel*2.0;
    if(any(tap<pixel*.5)||any(tap>1-pixel*.5))continue;
    float stencil=SceneTextureLookup(ClampSceneTextureUV(ViewportUVToSceneTextureUV(tap,25),25),25,false).r;
    edge=max(edge,abs(stencil-236)<.5?1:0);
}
return lerp(scene,float3(1,.035,.018),edge*.95);
