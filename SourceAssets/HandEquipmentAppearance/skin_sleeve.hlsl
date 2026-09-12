// Locally authored procedural skin and textile surface, not a downloaded scan.
struct SurfaceFields
{
    float hash(float2 p) { return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453); }
    float noise(float2 p)
    {
        float2 i=floor(p), f=frac(p); f=f*f*(3-2*f);
        return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),
                    lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);
    }
    float3 rnm(float3 base, float3 detail)
    {
        float3 t=normalize(base)+float3(0,0,1);
        float3 v=normalize(detail)*float3(-1,-1,1);
        return normalize(t*dot(t,v)/max(t.z,.0001)-v);
    }
};
SurfaceFields f;
float skin=saturate(Forearm.r)*(1-Glove.r);
float glove=saturate(Glove.r);
float pixelUV=max(length(ddx(UV)),length(ddy(UV)));

// A fine weave with mip-like attenuation before it becomes smaller than pixels.
float2 weave=sin(UV*6500.0);
float weaveVisibility=saturate(1-pixelUV*1600);
float clothValue=.9+.07*f.noise(UV*90)+.03*weave.x*weave.y*weaveVisibility;
float3 cloth=SleeveTint*clothValue;
cloth*=lerp(1,.66,Cuff);
float cuffLight=sin(saturate((Forearm.g-.245)/.075)*3.14159265);
cloth*=1+Cuff*cuffLight*.16;
float3 clothNormal=normalize(float3(SourceNormal.xy*.15+weave*.012*weaveVisibility,1));

// Low amplitude tone variation, a softer inner forearm, and a slightly warmer wrist.
float blotch=f.noise(UV*42)-.5;
float fine=f.noise(UV*170)-.5;
float wrist=smoothstep(.78,1,Forearm.g);
float3 skinColor=SkinTint*(1+blotch*.055+fine*.018);
skinColor+=float3(.016,.003,-.001)*Forearm.b;
skinColor+=float3(.012,-.003,-.003)*wrist;

// Smooth pore depressions, approximately 0.2 mm across on this original UV atlas.
float2 poreUV=UV*1800;
float2 cell=floor(poreUV);
float2 center=.36+.28*float2(f.hash(cell),f.hash(cell+67.3));
float2 offset=frac(poreUV)-center;
float shape=saturate(1-dot(offset,offset)/.055);
float poreVisibility=saturate(1-pixelUV*1800);
float2 poreGradient=(6.0/.055)*shape*shape*offset;
float2 poreNormal=-poreGradient*SkinDetailStrength*poreVisibility;
float3 skinNormal=normalize(float3(poreNormal,1));
float skinRough=clamp(.49+blotch*.045+fine*.025-Forearm.b*.035,.39,.58);

// Preserve the preceding Fab brown leather finish exactly in the glove mask.
float3 gloveColor=lerp(Leather,Leather*.72,Glove.b*.8);
float leatherAmount=LeatherNormalStrength*lerp(1,1.3,Glove.g)*glove;
float3 leatherDetail=normalize(float3(Grain.xy*leatherAmount,lerp(1,Grain.z,saturate(leatherAmount))));
float3 gloveNormal=f.rnm(SourceNormal,leatherDetail);
gloveNormal=f.rnm(gloveNormal,normalize(float3(Thread.xy*.55*glove,Thread.z)));
float gloveRough=clamp(lerp(.42,.63,Glove.g)+LeatherRough.r*.24,.35,.9);
gloveRough=lerp(gloveRough,.77,Glove.b);

OutNormal=normalize(lerp(lerp(clothNormal,skinNormal,skin),gloveNormal,glove));
OutRoughness=lerp(lerp(.79,skinRough,skin),gloveRough,glove);
OutScatter=skin*SkinScatterStrength;
return lerp(lerp(cloth,skinColor,skin),gloveColor,glove);
