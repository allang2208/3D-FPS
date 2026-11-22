// Screen coordinates belong exclusively to the image. FixedEtch comes from the mesh.
// @include ReticleInk.hlsl
float2 sceneUV=.5+(ScreenUV-.5)*ScreenToLens.xy;
float3 scene=Texture2DSample(Scene,SceneSampler,saturate(sceneUV)).rgb*float3(.985,.995,1.);
// A thermal screen emits its own image. Compensate the outer camera's eye
// adaptation once, just as for its red emitter, when compositing the display.
if (abs(ReticleStyle-6.)<.25)
    scene*=InkExposure;
if (abs(ReticleStyle-7.)<.25)
{
    // A faint green edge coating on the Peakwatch pane, with a clear central field.
    scene*=lerp(float3(.99,1.,.985),float3(.91,.99,.925),smoothstep(.47,.98,FixedEtch.w));
}
float3 ink=glassInk.Shade(FixedEtch,ReticleStyle,BowDrawState,BowRelease);
return scene*(1.-FixedEtch.y)+ink*InkExposure;
