// V9: finite left-thumb appearance correction; all existing custom inputs/outputs retained.
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
    float thumbCapsule(float3 p,float3 head,float3 axis,float extent,float radius)
    {
        float3 v=p-head;
        float t=dot(v,axis);
        float3 radial=v-axis*clamp(t,0,extent);
        return (1-smoothstep(radius*.96,radius*1.32,length(radial)))
             * smoothstep(-.30,.12,t)
             * (1-smoothstep(extent+.04,extent+.32,t));
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
float fade=1-smoothstep(24,96,footprint);

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
// V9 local thumb surface; canonical M4 anatomy survives native M16 binding.
float thumbRegion=0;
thumbRegion=max(thumbRegion,f.thumbCapsule(RestPosition,float3(-45.5840047886,-20.1445536142,-60.8854981207),float3(0.2367750276,-0.8517202921,-0.4674507771),1.6636418320,1.4318613408));
thumbRegion=max(thumbRegion,f.thumbCapsule(RestPosition,float3(-45.1900959015,-21.5615108609,-61.6631686687),float3(0.0457417424,-0.6483685225,-0.7599512581),3.0859931607,1.0883509647));
thumbRegion=max(thumbRegion,f.thumbCapsule(RestPosition,float3(-45.0489372015,-23.5623717308,-64.0083730221),float3(-0.0378476194,-0.5249378737,-0.8502986282),3.5541651821,0.9845020715));
thumbRegion*=1-ForearmMode;
float thumbSkin=thumbRegion*(1-nail);
float skinDetail=(1-nail)*(1-lerp(.60,.38,thumbRegion)*palmDetail);
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

// One bounded micro-height offset, no POM ray march or vertex displacement.
float4 firstX=Texture2DSampleGrad(MicroTexture,MicroTextureSampler,q.yz,dx.yz,dy.yz);
float4 firstY=Texture2DSampleGrad(MicroTexture,MicroTextureSampler,q.xz,dx.xz,dy.xz);
float4 firstZ=Texture2DSampleGrad(MicroTexture,MicroTextureSampler,q.xy,dx.xy,dy.xy);
float height=(dot(float3(firstX.b,firstY.b,firstZ.b),blend)-MicroHeightZero)*MicroHeightCm;
float3 view=normalize(ViewWS);
float3 restView=rx*dot(dualX,view)+ry*dot(dualY,view);
float3 shift=restView/max(abs(dot(view,N)),.35)*height*fade*skinDetail;
shift*=min(1,.024/max(length(shift),.000001));
q+=shift/tile;
float4 fieldX=Texture2DSampleGrad(MicroTexture,MicroTextureSampler,q.yz,dx.yz,dy.yz);
float4 fieldY=Texture2DSampleGrad(MicroTexture,MicroTextureSampler,q.xz,dx.xz,dy.xz);
float4 fieldZ=Texture2DSampleGrad(MicroTexture,MicroTextureSampler,q.xy,dx.xy,dy.xy);
float2 sx=f.slope(fieldX.rg),sy=f.slope(fieldY.rg),sz=f.slope(fieldZ.rg);
float3 restGradient=float3(0,sx.x,sx.y)*blend.x
                   +float3(sy.x,0,sy.y)*blend.y+float3(sz.x,sz.y,0)*blend.z;
restGradient*=MicroNormalStrength*fade*skinDetail*(8/tile)*(MicroHeightCm/.009100000013);
float3 gradient=dualX*dot(restGradient,rx)+dualY*dot(restGradient,ry);
float3 detail=normalize(float3(-dot(gradient,T),-dot(gradient,B),1));
float baseNormalScale=(1-ForearmMode)*lerp(1,.58,palmar*(1-nail));
baseNormalScale*=lerp(1,.82,thumbSkin);
float3 skinNormal=f.rnm(normalize(float3(AnatomicalNormal.xy*baseNormalScale,AnatomicalNormal.z)),detail);

float3 toneX=Texture2DSampleGrad(ColourDetail,ColourDetailSampler,q.yz,dx.yz,dy.yz).rgb;
float3 toneY=Texture2DSampleGrad(ColourDetail,ColourDetailSampler,q.xz,dx.xz,dy.xz).rgb;
float3 toneZ=Texture2DSampleGrad(ColourDetail,ColourDetailSampler,q.xy,dx.xy,dy.xy).rgb;
float3 tone=2*(toneX*blend.x+toneY*blend.y+toneZ*blend.z);
float broad=.5*sin(RestPosition.x*2.3+RestPosition.y*1.8)*sin(RestPosition.z*2.7+RestPosition.x*.8);
float forearmVariation=1-smoothstep(-12,-5,longitudinal);
float3 sharedColour=WristTint*(1+broad*.035*forearmVariation);
float3 colour=lerp(sharedColour,BaseColour,handAnatomy);
// The atlas' dark painted fold is distinct from its normal relief. Locally
// reduce the painted term while retaining the fold normal and skin microfield.
colour*=lerp(1,(1-.035*Surface.b)/max(1-.10*Surface.b,.90),thumbSkin);
float localColourDetail=ColourDetailStrength*lerp(1,.58,thumbRegion);
colour*=lerp(float3(1,1,1),tone,localColourDetail*skinDetail*fade);
float sharedRough=.49-.04*palmar+.015*broad;
float rough=lerp(sharedRough,Surface.g,handAnatomy);
rough+=(dot(float3(fieldX.a,fieldY.a,fieldZ.a),blend)-.48)*skinDetail;
// Separate a translucent nail plate, a narrow free edge, and the adjacent
// living skin instead of the atlas' nearly uniform opaque pink/cream patch.
float3 thumbTip=RestPosition-float3(-45.0489372015,-23.5623717308,-64.0083730221);
float thumbAlong=dot(thumbTip,float3(-0.0378476194,-0.5249378737,-0.8502986282))/3.5541651821;
float thumbAcross=dot(thumbTip,float3(0.5852257367,-0.7013623137,0.4069420509))/0.9845020715;
float thumbNail=thumbRegion*saturate(nail);
float localFine=.5*sin(RestPosition.x*19+RestPosition.y*13)*sin(RestPosition.z*23-RestPosition.x*11);
float3 underNail=float3(.36,.235,.185)*(1+broad*.04+localFine*.012);
float rootPink=(1-smoothstep(.24,.52,thumbAlong))*.020;
float3 nailPlate=lerp(underNail,float3(.50,.345,.315),.30)+float3(rootPink,-rootPink*.18,-rootPink*.12);
float freeEdge=smoothstep(.80,.87,thumbAlong)*.13;
nailPlate=lerp(nailPlate,float3(.63,.56,.48),freeEdge);
// Subtle longitudinal plate variation changes highlight width, not skin hue.
float nailVariation=sin(thumbAcross*15)*.005;
colour=lerp(colour,nailPlate,thumbNail);
rough=lerp(rough,.385+nailVariation,thumbNail);
rough=clamp(rough+RoughnessOffset,.30,.64);

// Keep the established cloth response where the existing forearm mask says
// cloth. Slot zero's accepted sleeve material is kept verbatim on the mesh.
float pixelUV=max(length(ddx(UV)),length(ddy(UV)));
float2 weave=sin(UV*6500);
float weaveVisibility=saturate(1-pixelUV*1600);
float clothValue=.9+.07*f.noise(UV*90)+.03*weave.x*weave.y*weaveVisibility;
float3 cloth=SleeveTint*clothValue*lerp(1,.66,Forearm.a);
cloth*=1+Forearm.a*sin(saturate((Forearm.g-.245)/.075)*3.14159265)*.16;
float3 clothNormal=normalize(float3(SourceNormal.xy*.15+weave*.012*weaveVisibility,1));
OutColour=lerp(cloth,colour,skinCoverage);
OutRoughness=lerp(.79,rough,skinCoverage);
OutScatter=SkinScatterStrength*skinCoverage;
return normalize(lerp(clothNormal,skinNormal,skinCoverage));
