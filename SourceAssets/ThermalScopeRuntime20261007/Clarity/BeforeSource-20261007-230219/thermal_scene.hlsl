// Post-tonemap main-camera presentation; no second scene capture.
// Only our depth-only proxy classes are heat. Every pixel must be in front of
// the opaque scene depth, including invisible monsters' opaque proxy geometry.
float2 uv=GetViewportUV(Parameters);
float2 pixel=View.ViewSizeAndInvSize.zw;
float stencil=TargetClass.r;
float heatClass=(abs(stencil-240.0)<0.25 || abs(stencil-241.0)<0.25)?1.0:0.0;
float visible=heatClass*step(TargetDepth.r,WorldDepth.r+1.0);
float fire=abs(stencil-241.0)<0.25?1.0:0.0;
float luminance=dot(max(SceneColor.rgb,0.0),float3(0.2126,0.7152,0.0722));
float cold=0.018+0.19*sqrt(saturate(luminance));
float3 color=float3(cold*0.90,cold*0.96,cold);
if(visible>0.5)
{
    float inside=0.0;
    const float2 offsets[4]={float2(1.5,0),float2(-1.5,0),float2(0,1.5),float2(0,-1.5)};
    [unroll]for(int i=0;i<4;++i)
    {
        float2 p=saturate(uv+offsets[i]*pixel);
        float s=SceneTextureLookup(ViewportUVToSceneTextureUV(p,25),25,false).r;
        float d=SceneTextureLookup(ViewportUVToSceneTextureUV(p,13),13,false).r;
        float w=SceneTextureLookup(ViewportUVToSceneTextureUV(p,1),1,false).r;
        inside+=(abs(s-stencil)<0.25 && d<=w+1.0)?0.25:0.0;
    }
    float edge=saturate((1.0-inside)*2.0);
    float3 core=lerp(float3(.92,.94,.91),float3(1.0,.97,.72),fire);
    float3 rim=lerp(float3(1.0,.64,.17),float3(1.0,.27,.035),fire);
    color=lerp(core,rim,edge);
}
// Electronic panel texture is deliberately slight; it never moves the reticle.
float scan=0.994+0.006*cos(uv.y*View.ViewSizeAndInvSize.y*3.14159265);
return lerp(SceneColor.rgb,color*scan,saturate(ThermalAlpha));
