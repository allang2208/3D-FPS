// BEIWEI_RUNE_V1: runs after the existing per-blade contour placement.
if (RuneMode > 9.5 && RuneMode < 10.5)
{
    // Physical aspect: the four-character strip is 3:1; do not stretch it
    // across the entire long blade. The baseline follows its measured centre.
    float span = BEIWEI_WIDTH_CM / .58;
    float side = N.y >= 0 ? 1 : -1;
    float2 artUV = float2(.5 + (BEIWEI_CENTER_CM-ZhanZ)/(span*3.),
                         .5 - side*(BeiweiRawP.x-ZhanCenter)/span);
    float inside=smoothstep(0,.035,artUV.x)*(1-smoothstep(.965,1,artUV.x));
    inside*=smoothstep(0,.035,artUV.y)*(1-smoothstep(.965,1,artUV.y));
    inside*=smoothstep(.02,.08,ZhanAlong)*(1-smoothstep(.93,.99,ZhanAlong));
    float ink=Texture2DSample(RuneTexture,RuneTextureSampler,saturate(artUV)).r;
    float edge=Texture2DSample(RuneTexture,RuneTextureSampler,saturate(artUV+float2(.0008,-.0024))).r;
    float time=PreviewTime>=0?PreviewTime:T;
    float wave=.5+.5*sin(time*.85-artUV.x*7.0);
    float highlight=pow(wave,5.);
    float3 gold=lerp(float3(.40,.18,.035),float3(.96,.57,.12),.35+.65*wave);
    gold=lerp(gold,float3(1.,.87,.47),highlight*.55);
    gold+=saturate(ink-edge)*float3(.16,.10,.025);
    return float4(gold*(.72+.08*sin(time*.7)),ink*inside*RuneOpacity);
}
