float3 BeiweiRawP=P.xyz;
// ZHANMADAO_BLADE_CONTOUR_V1: Chixiao central face; excludes the dorsal inlay.
if (RuneMode < -.5) return float4(0,0,0,0);
float ZhanZ=P.z;
float ZhanFaceCoverage=smoothstep(.25,.70,abs(normalize(N.xyz).y));
RuneOpacity*=ZhanFaceCoverage;HaloOpacity*=ZhanFaceCoverage;
float ZhanCenter=0.;
if (ZhanZ<=33.616739211) {
float s=saturate((ZhanZ-22.889405579)/10.727333631);
ZhanCenter=((-0.017189812*s+0.017189812)*s+0.017189812)*s+0.473051809;
}
else if (ZhanZ<=44.344072842) {
float s=saturate((ZhanZ-33.616739211)/10.727333631);
ZhanCenter=((0.013510808*s+-0.059402267)*s+0.000000000)*s+0.490241621;
}
else if (ZhanZ<=55.071406473) {
float s=saturate((ZhanZ-44.344072842)/10.727333631);
ZhanCenter=((0.134953103*s+-0.322543784)*s+-0.078272108)*s+0.444350163;
}
else if (ZhanZ<=65.798740105) {
float s=saturate((ZhanZ-55.071406473)/10.727333631);
ZhanCenter=((-0.017190612*s+-0.061435588)*s+-0.318500368)*s+0.178487373;
}
else if (ZhanZ<=76.526073736) {
float s=saturate((ZhanZ-65.798740105)/10.727333631);
ZhanCenter=((-0.003086000*s+-0.153670503)*s+-0.492943382)*s+-0.218639196;
}
else if (ZhanZ<=87.253407367) {
float s=saturate((ZhanZ-76.526073736)/10.727333631);
ZhanCenter=((0.009639529*s+-0.273796581)*s+-0.809542388)*s+-0.868339080;
}
else if (ZhanZ<=97.980740999) {
float s=saturate((ZhanZ-87.253407367)/10.727333631);
ZhanCenter=((-0.040794368*s+-0.371878916)*s+-1.328216963)*s+-1.942038520;
}
else if (true) {
float s=saturate((ZhanZ-97.980740999)/10.727333631);
ZhanCenter=((0.772916625*s+-1.545833250)*s+-2.194357901)*s+-3.682928768;
}
float ZhanWidth=0.;
if (ZhanZ<=33.616739211) {
float s=saturate((ZhanZ-22.889405579)/10.727333631);
ZhanWidth=((-0.176336526*s+0.176336526)*s+0.389491533)*s+4.573797622;
}
else if (ZhanZ<=44.344072842) {
float s=saturate((ZhanZ-33.616739211)/10.727333631);
ZhanWidth=((0.001758221*s+-0.068186551)*s+0.213155007)*s+4.963289155;
}
else if (ZhanZ<=55.071406473) {
float s=saturate((ZhanZ-44.344072842)/10.727333631);
ZhanWidth=((-0.031851383*s+0.006748792)*s+0.082056566)*s+5.110015831;
}
else if (ZhanZ<=65.798740105) {
float s=saturate((ZhanZ-55.071406473)/10.727333631);
ZhanWidth=((0.012095536*s+-0.042609055)*s+0.000000000)*s+5.166969805;
}
else if (ZhanZ<=76.526073736) {
float s=saturate((ZhanZ-65.798740105)/10.727333631);
ZhanWidth=((0.014441469*s+-0.088949912)*s+-0.048931501)*s+5.136456287;
}
else if (ZhanZ<=87.253407367) {
float s=saturate((ZhanZ-76.526073736)/10.727333631);
ZhanWidth=((0.076369512*s+-0.250303371)*s+-0.183506918)*s+5.013016342;
}
else if (ZhanZ<=97.980740999) {
float s=saturate((ZhanZ-87.253407367)/10.727333631);
ZhanWidth=((0.011221274*s+-0.182041987)*s+-0.455005122)*s+4.655575566;
}
else if (true) {
float s=saturate((ZhanZ-97.980740999)/10.727333631);
ZhanWidth=((0.268868159*s+-0.537736319)*s+-0.785425274)*s+4.029749731;
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
    float span = 5.13645629 / .58;
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
