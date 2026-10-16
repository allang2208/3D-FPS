// 229: the currently actionable alchemy target. Visible gold exterior contour only.
float3 scene=ColorInput.rgb;
float2 uv=GetViewportUV(Parameters);
float2 pixel=GetSceneTextureViewSize(14).zw;
float centerStencil=StencilInput.r;
float centerMarked=(abs(centerStencil-229)<.5)?1:0;
// An exterior stroke preserves the actual object surface, including glass vessels.
if(centerMarked>.5)return scene;
float bestDepth=1e20;
float selected=0;
float2 directions[8]={float2(1,0),float2(-1,0),float2(0,1),float2(0,-1),
    float2(.707,.707),float2(-.707,.707),float2(.707,-.707),float2(-.707,-.707)};
[unroll]for(int i=0;i<8;i++)
{
    float2 tap=uv+directions[i]*pixel*Width;
    if(any(tap<pixel*.5)||any(tap>1-pixel*.5))continue;
    float s=SceneTextureLookup(ClampSceneTextureUV(ViewportUVToSceneTextureUV(tap,25),25),25,false).r;
    if(abs(s-229)>.5)continue;
    float d=SceneTextureLookup(ClampSceneTextureUV(ViewportUVToSceneTextureUV(tap,13),13),13,false).r;
    float visibleDepth=SceneTextureLookup(ClampSceneTextureUV(ViewportUVToSceneTextureUV(tap,1),1),1,false).r;
    // Do not highlight through walls or over the held gun/arms.
    if(d>visibleDepth+max(1.5,d*.0001)||d>SceneDepthInput.r+max(1.5,d*.0001))continue;
    if(d<bestDepth){bestDepth=d;selected=s;}
}
if(selected<1)return scene;
float3 color=Gold.rgb;
return lerp(scene,color,.88);
