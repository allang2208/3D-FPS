// Bare skin surface rework 2026-10-10: original mesh, no parallax, bounded micro normal.
// V5: centimetre-scaled skin in the skeletal reference pose. Both material
// sections use this field, independently of the original atlas density.
struct SkinFields
{
    float hash(float2 p) { return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453); }
    float noise(float2 p)
    {
        float2 i=floor(p),f=frac(p); f=f*f*(3-2*f);
        return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),
                    lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);
    }
    float3 rnm(float3 base,float3 detail)
    {
        float3 t=normalize(base)+float3(0,0,1),r=detail*float3(-1,-1,1);
        return normalize(t*dot(t,r)/max(t.z,.01)-r);
    }
    float2 slope(float2 encoded)
    {
        float2 xy=encoded*2-1;
        return -xy/max(sqrt(saturate(1-dot(xy,xy))),.2);
    }
};
SkinFields f;
float3 restN=normalize(RestNormal);
float3 blend=pow(abs(restN),4);
blend/=max(blend.x+blend.y+blend.z,.00001);
float tile=max(MicroTileCm,.5);
float3 q=RestPosition/tile;
float3 dx=ddx(q),dy=ddy(q);
float footprint=max(length(dx),length(dy))*MicroTextureSize;
float fade=1-smoothstep(12,56,footprint);

// Same anatomical transition on each side of the forearm/hand material seam.
float side=RestPosition.x<0?-1:1;
float3 wrist=float3(side*WristOrigin.x,WristOrigin.y,WristOrigin.z);
float3 forward=normalize(float3(side*WristForward.x,WristForward.y,WristForward.z));
float3 dorsal=normalize(float3(side*WristDorsal.x,WristDorsal.y,WristDorsal.z));
float longitudinal=dot(RestPosition-wrist,forward);
float palmar=smoothstep(.15,.75,-dot(restN,dorsal));
float handAnatomy=smoothstep(-.8,1.5,longitudinal)*(1-ForearmMode);
float palmDetail=Surface.a*smoothstep(-2,2,longitudinal)*(1-ForearmMode);
float nail=Surface.r*(1-ForearmMode);
float skinDetail=(1-nail)*(1-.60*palmDetail);
float skinCoverage=lerp(1,saturate(Forearm.r),ForearmMode);

// Dual tangent basis maps reference-pose height derivatives through the actual
// animated surface; normals do not stay stuck to the undeformed arm axes.
float3 N=normalize(NormalWS),T=normalize(TangentWS),B=normalize(BitangentWS);
float3 px=ddx(PositionWS),py=ddy(PositionWS);
float3 rx=ddx(RestPosition),ry=ddy(RestPosition);
float denom=dot(px,cross(py,N));
float floorDenom=max(length(px)*length(py)*.0001,1e-10);
float safeDenom=(denom<0?-1:1)*max(abs(denom),floorDenom);
float3 dualX=cross(py,N)/safeDenom,dualY=cross(N,px)/safeDenom;

// Sample at the unchanged reference coordinate: no height/parallax offset.
float4 fieldX=Texture2DSampleGrad(MicroTexture,MicroTextureSampler,q.yz,dx.yz,dy.yz);
float4 fieldY=Texture2DSampleGrad(MicroTexture,MicroTextureSampler,q.xz,dx.xz,dy.xz);
float4 fieldZ=Texture2DSampleGrad(MicroTexture,MicroTextureSampler,q.xy,dx.xy,dy.xy);
float2 sx=f.slope(fieldX.rg),sy=f.slope(fieldY.rg),sz=f.slope(fieldZ.rg);
float3 restGradient=float3(0,sx.x,sx.y)*blend.x
                   +float3(sy.x,0,sy.y)*blend.y+float3(sz.x,sz.y,0)*blend.z;
restGradient*=MicroNormalStrength*.22*fade*skinDetail*(8/tile);
float3 gradient=dualX*dot(restGradient,rx)+dualY*dot(restGradient,ry);
float2 microSlope=float2(-dot(gradient,T),-dot(gradient,B));
microSlope*=min(1,.10/max(length(microSlope),.000001));
float3 detail=normalize(float3(microSlope,1));
AnatomicalNormal=normalize(float3(AnatomicalNormal.xy*lerp(.65,1,nail),AnatomicalNormal.z));
float3 skinNormal=f.rnm(normalize(float3(AnatomicalNormal.xy*lerp(1,.58,palmar*(1-nail)),AnatomicalNormal.z)),detail);

float3 toneX=Texture2DSampleGrad(ColourDetail,ColourDetailSampler,q.yz,dx.yz,dy.yz).rgb;
float3 toneY=Texture2DSampleGrad(ColourDetail,ColourDetailSampler,q.xz,dx.xz,dy.xz).rgb;
float3 toneZ=Texture2DSampleGrad(ColourDetail,ColourDetailSampler,q.xy,dx.xy,dy.xy).rgb;
float3 tone=2*(toneX*blend.x+toneY*blend.y+toneZ*blend.z);
float broad=f.noise(RestPosition.xy*.12+RestPosition.z*.07)-.5;
float forearmVariation=1-smoothstep(-12,-5,longitudinal);
float3 sharedColour=WristTint*float3(1.015,1,.99)*(1+broad*.018*forearmVariation);
float3 colour=lerp(sharedColour,BaseColour,handAnatomy);
colour*=lerp(float3(1,1,1),tone,ColourDetailStrength*.20*skinDetail*fade);
float sharedRough=.50-.02*palmar+.004*broad;
float rough=lerp(sharedRough,lerp(sharedRough,Surface.g,.65),handAnatomy);
rough+=(dot(float3(fieldX.a,fieldY.a,fieldZ.a),blend)-.48)*skinDetail*.12*fade;
rough=clamp(rough+RoughnessOffset,.30,.64);

// Bare skin only; original clothing uses separate materials.
OutColour=colour;
OutRoughness=rough;
OutScatter=SkinScatterStrength;
return normalize(skinNormal);
