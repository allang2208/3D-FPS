float3 BeiweiRawP=P.xyz;
// ZHANMADAO_BLADE_CONTOUR_V1: Zhufeng central face; excludes the dorsal inlay.
if (RuneMode < -.5) return float4(0,0,0,0);
float ZhanZ=P.z;
float ZhanFaceCoverage=smoothstep(.25,.70,abs(normalize(N.xyz).y));
RuneOpacity*=ZhanFaceCoverage;HaloOpacity*=ZhanFaceCoverage;
float ZhanCenter=0.;
if (ZhanZ<=33.616739211) {
float s=saturate((ZhanZ-22.889405579)/10.727333631);
ZhanCenter=((-0.096857761*s+0.096857761)*s+0.096857761)*s+0.269727898;
}
else if (ZhanZ<=44.344072842) {
float s=saturate((ZhanZ-33.616739211)/10.727333631);
ZhanCenter=((0.003332378*s+-0.022440182)*s+0.000000000)*s+0.366585659;
}
else if (ZhanZ<=55.071406473) {
float s=saturate((ZhanZ-44.344072842)/10.727333631);
ZhanCenter=((0.131078705*s+-0.296215339)*s+-0.034883228)*s+0.347477855;
}
else if (ZhanZ<=65.798740105) {
float s=saturate((ZhanZ-55.071406473)/10.727333631);
ZhanCenter=((-0.017644935*s+-0.030391412)*s+-0.234077792)*s+0.147457992;
}
else if (ZhanZ<=76.526073736) {
float s=saturate((ZhanZ-65.798740105)/10.727333631);
ZhanCenter=((-0.021340243*s+-0.084205879)*s+-0.347795419)*s+-0.134656146;
}
else if (ZhanZ<=87.253407367) {
float s=saturate((ZhanZ-76.526073736)/10.727333631);
ZhanCenter=((0.048861192*s+-0.274383759)*s+-0.580227906)*s+-0.587997687;
}
else if (ZhanZ<=97.980740999) {
float s=saturate((ZhanZ-87.253407367)/10.727333631);
ZhanCenter=((-0.062597251*s+-0.213284542)*s+-0.982411848)*s+-1.393748160;
}
else if (true) {
float s=saturate((ZhanZ-97.980740999)/10.727333631);
ZhanCenter=((0.587590253*s+-1.175180506)*s+-1.596772685)*s+-2.652041801;
}
float ZhanWidth=0.;
if (ZhanZ<=33.616739211) {
float s=saturate((ZhanZ-22.889405579)/10.727333631);
ZhanWidth=((-0.030768338*s+0.030768338)*s+0.096402128)*s+4.496980184;
}
else if (ZhanZ<=44.344072842) {
float s=saturate((ZhanZ-33.616739211)/10.727333631);
ZhanWidth=((0.003644274*s+-0.019524083)*s+0.065633791)*s+4.593382313;
}
else if (ZhanZ<=55.071406473) {
float s=saturate((ZhanZ-44.344072842)/10.727333631);
ZhanWidth=((-0.022707613*s+0.015302195)*s+0.037518448)*s+4.643136295;
}
else if (ZhanZ<=65.798740105) {
float s=saturate((ZhanZ-55.071406473)/10.727333631);
ZhanWidth=((0.008167751*s+-0.028664610)*s+0.000000000)*s+4.673249325;
}
else if (ZhanZ<=76.526073736) {
float s=saturate((ZhanZ-65.798740105)/10.727333631);
ZhanWidth=((0.009400724*s+-0.058951065)*s+-0.032825966)*s+4.652752467;
}
else if (ZhanZ<=87.253407367) {
float s=saturate((ZhanZ-76.526073736)/10.727333631);
ZhanWidth=((0.037299901*s+-0.153798940)*s+-0.122525923)*s+4.570376160;
}
else if (ZhanZ<=97.980740999) {
float s=saturate((ZhanZ-87.253407367)/10.727333631);
ZhanWidth=((-0.007627061*s+-0.150063819)*s+-0.318224101)*s+4.331351198;
}
else if (true) {
float s=saturate((ZhanZ-97.980740999)/10.727333631);
ZhanWidth=((0.341301723*s+-0.682603447)*s+-0.641232920)*s+3.855436218;
}
float ZhanAlong=(ZhanZ-22.889405579)/85.818669051;
P=float3((P.x-ZhanCenter)*Dimensions.x/max(ZhanWidth,.1),0,Dimensions.y+ZhanAlong*Dimensions.z);
N=float3(0,N.y>=0?1:-1,0);BladeOrigin=float3(0,0,0);BladeAxis=float3(0,0,1);
// END_ZHANMADAO_BLADE_CONTOUR_V1
// BEIWEI_RUNE_V1: runs after the existing per-blade contour placement.
if (RuneMode > 9.5 && RuneMode < 10.5)
{
    // Physical aspect: the four-character strip is 3:1; do not stretch it
    // across the entire long blade. The baseline follows its measured centre.
    float span = 4.65275247 / .58;
    float side = N.y >= 0 ? 1 : -1;
    float2 artUV = float2(.5 + (67.51511349-ZhanZ)/(span*3.),
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
