// ZHANMADAO_BLADE_CONTOUR_V1: private coordinates; original PBR UVs are unchanged.
if (RuneMode < -.5) return float4(0,0,0,0);
float ZhanZ = P.z;
float ZhanFaceCoverage = smoothstep(.25,.70,abs(normalize(N.xyz).y));
RuneOpacity *= ZhanFaceCoverage;
HaloOpacity *= ZhanFaceCoverage;
float ZhanCenter = 0.0;
if (ZhanZ <= 33.662638728) {
  float s = saturate((ZhanZ - 22.941005036) / 10.721633691);
  ZhanCenter = ((-0.068620784*s + 0.068620784)*s + 0.301585452)*s + 0.617353102;
}
else if (ZhanZ <= 44.384272419) {
  float s = saturate((ZhanZ - 33.662638728) / 10.721633691);
  ZhanCenter = ((-0.067365688*s + 0.024183763)*s + 0.232964668)*s + 0.918938554;
}
else if (ZhanZ <= 55.105906110) {
  float s = saturate((ZhanZ - 44.384272419) / 10.721633691);
  ZhanCenter = ((-0.020904332*s + -0.008261066)*s + 0.079235128)*s + 1.108721296;
}
else if (ZhanZ <= 65.827539802) {
  float s = saturate((ZhanZ - 55.105906110) / 10.721633691);
  ZhanCenter = ((0.038936878*s + -0.122797365)*s + 0.000000000)*s + 1.158791027;
}
else if (ZhanZ <= 76.549173493) {
  float s = saturate((ZhanZ - 65.827539802) / 10.721633691);
  ZhanCenter = ((0.057542872*s + -0.206128136)*s + -0.128784096)*s + 1.074930540;
}
else if (ZhanZ <= 87.270807184) {
  float s = saturate((ZhanZ - 76.549173493) / 10.721633691);
  ZhanCenter = ((0.056277642*s + -0.236289625)*s + -0.368411752)*s + 0.797561180;
}
else if (ZhanZ <= 97.992440876) {
  float s = saturate((ZhanZ - 87.270807184) / 10.721633691);
  ZhanCenter = ((-0.069542547*s + -0.126292428)*s + -0.672158076)*s + 0.249137445;
}
else if (true) {
  float s = saturate((ZhanZ - 97.992440876) / 10.721633691);
  ZhanCenter = ((0.499109398*s + -0.998218796)*s + -1.133370572)*s + -0.618855606;
}
float ZhanWidth = 0.0;
if (ZhanZ <= 33.662638728) {
  float s = saturate((ZhanZ - 22.941005036) / 10.721633691);
  ZhanWidth = ((0.004829097*s + -0.004829097)*s + 0.046098190)*s + 4.942081407;
}
else if (ZhanZ <= 44.384272419) {
  float s = saturate((ZhanZ - 33.662638728) / 10.721633691);
  ZhanWidth = ((-0.012231003*s + 0.018190253)*s + 0.050927287)*s + 4.988179597;
}
else if (ZhanZ <= 55.105906110) {
  float s = saturate((ZhanZ - 44.384272419) / 10.721633691);
  ZhanWidth = ((0.002831349*s + -0.007857506)*s + 0.050614783)*s + 5.045066133;
}
else if (ZhanZ <= 65.827539802) {
  float s = saturate((ZhanZ - 55.105906110) / 10.721633691);
  ZhanWidth = ((-0.039407455*s + 0.037414273)*s + 0.043393819)*s + 5.090654759;
}
else if (ZhanZ <= 76.549173493) {
  float s = saturate((ZhanZ - 65.827539802) / 10.721633691);
  ZhanWidth = ((0.040651608*s + -0.092316465)*s + 0.000000000)*s + 5.132055396;
}
else if (ZhanZ <= 87.270807184) {
  float s = saturate((ZhanZ - 76.549173493) / 10.721633691);
  ZhanWidth = ((-0.013185009*s + -0.003795613)*s + -0.062678106)*s + 5.080390539;
}
else if (ZhanZ <= 97.992440876) {
  float s = saturate((ZhanZ - 87.270807184) / 10.721633691);
  ZhanWidth = ((-0.040615775*s + -0.026321259)*s + -0.109824359)*s + 5.000731811;
}
else if (true) {
  float s = saturate((ZhanZ - 97.992440876) / 10.721633691);
  ZhanWidth = ((0.441835228*s + -0.883670456)*s + -0.284314200)*s + 4.823970419;
}
float ZhanAlong = (ZhanZ - 22.941005036) / 85.773069531;
P = float3((P.x-ZhanCenter)*Dimensions.x/max(ZhanWidth,.1),0,Dimensions.y+ZhanAlong*Dimensions.z);
N = float3(0,N.y>=0?1:-1,0);
BladeOrigin = float3(0,0,0);
BladeAxis = float3(0,0,1);
// END_ZHANMADAO_BLADE_CONTOUR_V1
