// Lens-capture thermal display; the surrounding main camera stays unchanged. The project's CustomDepth
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

// Give shaded surfaces a signal of their own. The scene's brightness still
// contributes detail, while albedo and surface direction separate a floor,
// a wall and a slope even when all three are in the same shadow.
const float3 luma=float3(.2126,.7152,.0722);
float luminance=dot(max(SceneColor.rgb,0.0),luma);
float incident=luminance/(luminance+.24);
float surface=sqrt(saturate(dot(TerrainBase.rgb,luma)));
float3 n=TerrainNormal.rgb;
float n2=dot(n,n);
float3 unitN=n*rsqrt(max(n2,.001));
float relief=.5+.5*dot(unitN,float3(-.65,-.40,.646));
// Side lighting alone gives some vertical faces the same signal as level ground.
float upward=smoothstep(.10,.92,unitN.z);
float tone=n2>.25 ? (.43*surface+.39*relief+.18*incident+.24*(upward-.4)) : incident;
float signal=smoothstep(.16,.90,tone);
float3 color=lerp(float3(.010,.017,.025),float3(.31,.35,.37),signal);
if(WorldDepth.r>1.e6)
    color=lerp(float3(.019,.029,.042),float3(.043,.060,.075),incident);

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
// Keep the limbs silver and the broad body surfaces ivory. Give the existing
// fire class its own amber hue so body contours stay neutral against the terrain.
float form=smoothstep(-.12,.93,dot(normal,normalize(float3(-.52,-.38,.76))));
// Use the opaque creature's surface detail only where both depths agree.
// A cloaked creature keeps its own depth relief without inheriting the wall behind it.
float sameSurface=(n2>.25)?1.-smoothstep(.6,2.5,abs(WorldDepth.r-targetZ)):0.;
form=lerp(form,.70*form+.30*smoothstep(.08,.94,relief),sameSurface);
float3 body=lerp(float3(.61,.67,.70),float3(1.68,1.61,1.48),form);
float edge=saturate((1.0-borderCoverage)*0.45+(1.0-coverage)*0.40);
body=lerp(body,float3(.80,.85,.87),edge);
float3 flame=lerp(float3(1.0,0.82,0.48),float3(0.98,0.38,0.07),edge);
float fire=saturate(fireCoverage/max(coverage,0.0001));
float3 heat=lerp(body,flame,fire);
color=lerp(color,heat,saturate(coverage*visibility));
return lerp(SceneColor.rgb,color,alpha);
