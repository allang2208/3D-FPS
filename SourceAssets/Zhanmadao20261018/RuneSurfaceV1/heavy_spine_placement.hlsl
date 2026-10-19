// ZHANMADAO_BLADE_CONTOUR_V1: private coordinates; original PBR UVs are unchanged.
if (RuneMode < -.5) return float4(0,0,0,0);
float ZhanZ = P.z;
float ZhanFaceCoverage = smoothstep(.25,.70,abs(normalize(N.xyz).y));
RuneOpacity *= ZhanFaceCoverage;
HaloOpacity *= ZhanFaceCoverage;
float ZhanCenter = 0.0;
if (ZhanZ <= 33.662638728) {
  float s = saturate((ZhanZ - 22.941005036) / 10.721633691);
  ZhanCenter = ((-0.110221146*s + 0.110221146)*s + 0.396428947)*s + 0.687918552;
}
else if (ZhanZ <= 44.384272419) {
  float s = saturate((ZhanZ - 33.662638728) / 10.721633691);
  ZhanCenter = ((-0.068182024*s + 0.005917846)*s + 0.286207802)*s + 1.084347499;
}
else if (ZhanZ <= 55.105906110) {
  float s = saturate((ZhanZ - 44.384272419) / 10.721633691);
  ZhanCenter = ((-0.024667095*s + -0.009748067)*s + 0.093497421)*s + 1.308291122;
}
else if (ZhanZ <= 65.827539802) {
  float s = saturate((ZhanZ - 55.105906110) / 10.721633691);
  ZhanCenter = ((0.045945449*s + -0.144900745)*s + 0.000000000)*s + 1.367373380;
}
else if (ZhanZ <= 76.549173493) {
  float s = saturate((ZhanZ - 65.827539802) / 10.721633691);
  ZhanCenter = ((0.067900707*s + -0.243231435)*s + -0.151965144)*s + 1.268418084;
}
else if (ZhanZ <= 87.270807184) {
  float s = saturate((ZhanZ - 76.549173493) / 10.721633691);
  ZhanCenter = ((0.066407607*s + -0.278821732)*s + -0.434725893)*s + 0.941122213;
}
else if (ZhanZ <= 97.992440876) {
  float s = saturate((ZhanZ - 87.270807184) / 10.721633691);
  ZhanCenter = ((-0.082060213*s + -0.149025043)*s + -0.793146535)*s + 0.293982195;
}
else if (true) {
  float s = saturate((ZhanZ - 97.992440876) / 10.721633691);
  ZhanCenter = ((0.588949070*s + -1.177898140)*s + -1.337377259)*s + -0.730249596;
}
float ZhanWidth = 0.0;
if (ZhanZ <= 33.662638728) {
  float s = saturate((ZhanZ - 22.941005036) / 10.721633691);
  ZhanWidth = ((-0.275883434*s + 0.275883434)*s + 0.390440407)*s + 5.495611599;
}
else if (ZhanZ <= 44.384272419) {
  float s = saturate((ZhanZ - 33.662638728) / 10.721633691);
  ZhanWidth = ((0.040030353*s + -0.087461301)*s + 0.114556973)*s + 5.886052006;
}
else if (ZhanZ <= 55.105906110) {
  float s = saturate((ZhanZ - 44.384272419) / 10.721633691);
  ZhanWidth = ((0.003340968*s + -0.009271784)*s + 0.059725431)*s + 5.953178032;
}
else if (ZhanZ <= 65.827539802) {
  float s = saturate((ZhanZ - 55.105906110) / 10.721633691);
  ZhanWidth = ((-0.046500897*s + 0.044148962)*s + 0.051204767)*s + 6.006972647;
}
else if (ZhanZ <= 76.549173493) {
  float s = saturate((ZhanZ - 65.827539802) / 10.721633691);
  ZhanWidth = ((0.047969113*s + -0.108933794)*s + 0.000000000)*s + 6.055825479;
}
else if (ZhanZ <= 87.270807184) {
  float s = saturate((ZhanZ - 76.549173493) / 10.721633691);
  ZhanWidth = ((-0.015558490*s + -0.004478474)*s + -0.073960248)*s + 5.994860798;
}
else if (ZhanZ <= 97.992440876) {
  float s = saturate((ZhanZ - 87.270807184) / 10.721633691);
  ZhanWidth = ((-0.047926525*s + -0.031059281)*s + -0.129592667)*s + 5.900863585;
}
else if (true) {
  float s = saturate((ZhanZ - 97.992440876) / 10.721633691);
  ZhanWidth = ((0.521365638*s + -1.042731276)*s + -0.335490805)*s + 5.692285112;
}
float ZhanAlong = (ZhanZ - 22.941005036) / 85.773069531;
P = float3((P.x-ZhanCenter)*Dimensions.x/max(ZhanWidth,.1),0,Dimensions.y+ZhanAlong*Dimensions.z);
N = float3(0,N.y>=0?1:-1,0);
BladeOrigin = float3(0,0,0);
BladeAxis = float3(0,0,1);
// END_ZHANMADAO_BLADE_CONTOUR_V1
