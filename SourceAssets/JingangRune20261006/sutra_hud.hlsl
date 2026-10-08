// Jingang Flames V2: stable calligraphy, glyph-rooted gold fire and soft falloff.
// Existing one-quad UI material; Age and the state transition remain owner-driven.
struct JingangFire
{
    float Hash(float2 p)
    {
        float3 q=frac(float3(p.xyx)*.1031);
        q+=dot(q,q.yzx+33.33);
        return frac((q.x+q.y)*q.z);
    }
    float Noise(float2 p)
    {
        float2 cell=floor(p), f=frac(p);
        f=f*f*(3.-2.*f);
        return lerp(lerp(Hash(cell),Hash(cell+float2(1,0)),f.x),
                    lerp(Hash(cell+float2(0,1)),Hash(cell+float2(1,1)),f.x),f.y);
    }
    float Ink(Texture2D tex,SamplerState texSampler,float2 uv,float state,float previous,float blend)
    {
        // Keep displaced taps within the selected atlas panel.
        float2 local=float2(.065+uv.x*.87,.075+uv.y*.84);
        float inside=step(0.,local.x)*step(local.x,1.)*step(0.,local.y)*step(local.y,1.);
        local=clamp(local,.002,.998);
        float current=Texture2DSampleLevel(tex,texSampler,float2((local.x+state)/3.,local.y),0).r;
        [branch] if(blend<.9999 && abs(state-previous)>.5)
        {
            float old=Texture2DSampleLevel(tex,texSampler,float2((local.x+previous)/3.,local.y),0).r;
            current=lerp(old,current,blend);
        }
        return current*inside;
    }
};
JingangFire fire;
float state=clamp(floor(State+.5),0.,2.);
float previous=clamp(floor(PreviousState+.5),0.,2.);
float blend=saturate(Blend);
float ink=fire.Ink(Sutra,SutraSampler,UV,state,previous,blend);

// Texture motion goes upward (UI +Y points down). The glyph itself never warps.
float2 flow=UV*float2(31.,19.)+float2(Age*.21,Age*2.55);
float broad=fire.Noise(flow);
float fine=fire.Noise(flow*2.13+float2(-Age*.4,Age*.9));
float turbulence=broad*.68+fine*.32;
float curl=sin(UV.y*36.+Age*3.7+broad*4.5);
float plume=0.;
[unroll] for(int tap=0;tap<8;++tap)
{
    float height=(float(tap)+.5)/8.;
    float lift=.003+height*.071;
    float bend=(curl*.60+sin(UV.y*69.+Age*5.1+height*3.)*.40)*.025*height;
    float root=fire.Ink(Sutra,SutraSampler,UV+float2(bend,lift),state,previous,blend);
    float tongues=smoothstep(.14+height*.39,.65+height*.24,turbulence);
    plume=max(plume,root*pow(1.-height,1.25)*tongues);
}

// Narrow warm edge joins the moving tongues to actual brush strokes.
float rim=max(fire.Ink(Sutra,SutraSampler,UV+float2(.008,0),state,previous,blend),
              fire.Ink(Sutra,SutraSampler,UV-float2(.008,0),state,previous,blend));
rim=max(rim,fire.Ink(Sutra,SutraSampler,UV+float2(0,.005),state,previous,blend));
float edge=max(0.,rim-ink);
float breathing=.90+.065*sin(Age*1.05);
float burning=.90+.07*sin(Age*6.9+UV.y*27.)+.03*sin(Age*11.7+UV.x*41.);
float border=min(min(UV.x,1.-UV.x),min(UV.y,1.-UV.y));
float feather=smoothstep(.002,.033,border);
float fireAlpha=saturate(plume*.88*burning+edge*.27)*feather;

// Champagne / amber / warm gold retain pale hot tips; never red lettering.
float gradient=.5+.5*sin(UV.y*7.8-Age*.66+UV.x*1.8);
float3 amber=float3(.90,.55,.18), pale=float3(1.,.88,.57), deep=float3(.61,.32,.085);
float3 coreColor=lerp(deep,amber,.42+.58*gradient);
coreColor=lerp(coreColor,pale,pow(gradient,3)*.72);
float visualState=lerp(previous,state,blend);
coreColor=lerp(coreColor,pale,.20*saturate(1.-visualState));
coreColor*=1.+.12*saturate(visualState-1.);
float glint=pow(saturate(.5+.5*cos(UV.y*12.-Age*1.9)),14)*(.10+.09*Leech);
coreColor=saturate(coreColor*(breathing+glint)+pale*ink*turbulence*.10);
float heat=saturate(plume*1.5+edge*.40);
float3 flameColor=lerp(float3(1.,.46,.055),float3(1.,.86,.36),heat);
flameColor=lerp(flameColor,float3(1.,.97,.74),pow(heat,3.)*.60);

// Straight-alpha UI output: stable ink over flames, with no background fill.
float coreAlpha=ink*.95;
float alpha=coreAlpha+fireAlpha*(1.-coreAlpha);
float3 rgb=(coreColor*coreAlpha+flameColor*fireAlpha*(1.-coreAlpha))/max(alpha,.0001);
return float4(rgb,alpha);
