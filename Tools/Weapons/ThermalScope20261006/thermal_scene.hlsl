// Main-camera thermal display, after tonemapping. The project's CustomDepth
// pass is unjittered (r.CustomDepthTemporalAAJitter=0); SceneDepth is not.
// Depth/stencil graph inputs declare the dependencies. Resample them below at
// explicit texel centres instead of comparing the two different raster grids.
float alpha=saturate(ThermalAlpha);
if(alpha<=0.0)return SceneColor.rgb;
float2 viewportUV=GetViewportUV(Parameters);
float4 buffer=GetSceneTextureBufferSize(13);
float4 raster=GetSceneTextureViewSize(13);
float2 targetUV=ViewportUVToSceneTextureUV(viewportUV,13);
float2 position=targetUV*buffer.xy-0.5;
float2 base=floor(position);
float2 fraction=frac(position);
const float2 corners[4]={float2(0,0),float2(1,0),float2(0,1),float2(1,1)};
float weights[4]={(1-fraction.x)*(1-fraction.y),fraction.x*(1-fraction.y),
    (1-fraction.x)*fraction.y,fraction.x*fraction.y};

float luminance=dot(max(SceneColor.rgb,0.0),float3(0.2126,0.7152,0.0722));
float cold=0.018+0.19*sqrt(saturate(luminance));
float3 color=float3(cold*0.90,cold*0.96,cold);

// Interpolate classified coverage, never stencil IDs or foreground/background
// depth values. This gives a subpixel contour without blurring the body image.
float coverage=0.0,fireCoverage=0.0,bestWeight=-1.0,anchorClass=0.0;
float2 anchorUV=targetUV;
[unroll]for(int i=0;i<4;++i)
{
    float2 sampleUV=ClampSceneTextureUV((base+corners[i]+0.5)*buffer.zw,13);
    float s=SceneTextureLookup(sampleUV,25,false).r;
    float isFire=abs(s-241.0)<0.25?1.0:0.0;
    float isHeat=(abs(s-240.0)<0.25 || isFire>0.5)?1.0:0.0;
    coverage+=weights[i]*isHeat;
    fireCoverage+=weights[i]*isFire;
    if(isHeat>0.5 && weights[i]>bestWeight)
    {
        bestWeight=weights[i];anchorUV=sampleUV;anchorClass=s;
    }
}
if(coverage<=0.0001)return lerp(SceneColor.rgb,color,alpha);

float targetZ=SceneTextureLookup(anchorUV,13,false).r;
float inverseZ=rcp(max(targetZ,0.01));
const float2 sides[4]={float2(1,0),float2(-1,0),float2(0,1),float2(0,-1)};
float inverseNeighbours[4]={inverseZ,inverseZ,inverseZ,inverseZ};
bool validNeighbours[4]={false,false,false,false};
float borderCoverage=0.0;
float surfaceDelta=clamp(targetZ*0.015,4.0,40.0);
[unroll]for(int i=0;i<4;++i)
{
    float2 sampleUV=ClampSceneTextureUV(anchorUV+sides[i]*buffer.zw,13);
    float s=SceneTextureLookup(sampleUV,25,false).r;
    borderCoverage+=(abs(s-240.0)<0.25 || abs(s-241.0)<0.25)?0.25:0.0;
    if(abs(s-anchorClass)<0.25)
    {
        float z=SceneTextureLookup(sampleUV,13,false).r;
        validNeighbours[i]=abs(z-targetZ)<=surfaceDelta;
        inverseNeighbours[i]=rcp(max(z,0.01));
    }
}

// Inverse depth is planar in screen space. Choose the closer one-sided surface
// on each axis, avoiding depth jumps between a limb and torso or another body.
float2 inverseSlope=0.0;
[unroll]for(int axis=0;axis<2;++axis)
{
    int p=axis*2,n=p+1;
    float positive=inverseNeighbours[p]-inverseZ;
    float negative=inverseZ-inverseNeighbours[n];
    inverseSlope[axis]=validNeighbours[p]
        ?(validNeighbours[n] && abs(negative)<abs(positive)?negative:positive)
        :(validNeighbours[n]?negative:0.0);
}
float2 depthSlope=-inverseSlope*targetZ*targetZ;
// Centimetres, bounded even at long range. Never widen tolerance to metres to
// hide self-occlusion: a wall in front of the target must still occlude it.
float tolerance=clamp(1.25+0.12*(abs(depthSlope.x)+abs(depthSlope.y)),1.25,3.0);

// Projection jitter is NDC, with opposite signs for screen Y. Quantise in the
// scene-depth raster, then compare each sample with the target plane at that
// SAME unjittered ray. Average visibility, not depths across wall boundaries.
float2 jitterUV=View.TemporalAAJitter.xy*float2(0.5,-0.5)*raster.xy*buffer.zw;
float2 scenePosition=(targetUV+jitterUV)*buffer.xy-0.5;
float2 sceneBase=floor(scenePosition),sceneFraction=frac(scenePosition);
float sceneWeights[4]={(1-sceneFraction.x)*(1-sceneFraction.y),sceneFraction.x*(1-sceneFraction.y),
    (1-sceneFraction.x)*sceneFraction.y,sceneFraction.x*sceneFraction.y};
float visibility=0.0;
[unroll]for(int i=0;i<4;++i)
{
    float2 sceneUV=ClampSceneTextureUV((sceneBase+corners[i]+0.5)*buffer.zw,1);
    float sceneZ=SceneTextureLookup(sceneUV,1,false).r;
    float2 offset=(sceneUV-jitterUV-anchorUV)*buffer.xy;
    float predictedZ=rcp(max(inverseZ*0.5,inverseZ+dot(inverseSlope,offset)));
    visibility+=sceneWeights[i]*(1.0-smoothstep(tolerance*0.35,tolerance,predictedZ-sceneZ));
}

// A gentle view-space relief comes from the heat geometry itself, including
// cloaked bodies. Do not borrow background lighting/normals through invisibility.
float2 projection=abs(float2(View.ViewToClip[0][0],View.ViewToClip[1][1]));
float2 pixelWorld=2.0*targetZ/max(projection*raster.xy,float2(0.01,0.01));
float3 normal=normalize(float3(-depthSlope/max(pixelWorld,float2(0.001,0.001)),1.0));
float bodyValue=0.73+0.18*normal.z+0.05*saturate(dot(normal,normalize(float3(-0.35,-0.25,1.0))));
float fire=saturate(fireCoverage/max(coverage,0.0001));
float3 core=lerp(float3(1.0,1.015,0.99)*bodyValue,float3(1.0,0.97,0.72),fire);
float3 rim=lerp(float3(0.94,0.59,0.20),float3(0.98,0.38,0.07),fire);
// Only the class boundary contributes a warm rim; visibility holes do not.
float edge=saturate((1.0-borderCoverage)*0.45+(1.0-coverage)*0.40);
float3 heat=lerp(core,rim,edge*lerp(0.65,1.0,fire));
color=lerp(color,heat,saturate(coverage*visibility));
return lerp(SceneColor.rgb,color,alpha);
