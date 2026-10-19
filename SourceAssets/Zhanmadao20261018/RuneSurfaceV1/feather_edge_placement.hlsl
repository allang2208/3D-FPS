// ZHANMADAO_BLADE_CONTOUR_V1: private coordinates; original PBR UVs are unchanged.
if (RuneMode < -.5) return float4(0,0,0,0);
float ZhanZ = P.z;
float ZhanFaceCoverage = smoothstep(.25,.70,abs(normalize(N.xyz).y));
RuneOpacity *= ZhanFaceCoverage;
HaloOpacity *= ZhanFaceCoverage;
float ZhanCenter = 0.0;
if (ZhanZ <= 33.662638728) {
  float s = saturate((ZhanZ - 22.941005036) / 10.721633691);
  ZhanCenter = ((-0.025018220*s + 0.025018220)*s + 0.196203882)*s + 0.538947042;
}
else if (ZhanZ <= 44.384272419) {
  float s = saturate((ZhanZ - 33.662638728) / 10.721633691);
  ZhanCenter = ((-0.069078533*s + 0.049718982)*s + 0.171185662)*s + 0.735150923;
}
else if (ZhanZ <= 55.105906110) {
  float s = saturate((ZhanZ - 44.384272419) / 10.721633691);
  ZhanCenter = ((-0.016723432*s + -0.006608865)*s + 0.063388027)*s + 0.886977034;
}
else if (ZhanZ <= 65.827539802) {
  float s = saturate((ZhanZ - 55.105906110) / 10.721633691);
  ZhanCenter = ((0.031149495*s + -0.098237872)*s + 0.000000000)*s + 0.927032764;
}
else if (ZhanZ <= 76.549173493) {
  float s = saturate((ZhanZ - 65.827539802) / 10.721633691);
  ZhanCenter = ((0.046034288*s + -0.164902487)*s + -0.103027258)*s + 0.859944388;
}
else if (ZhanZ <= 87.270807184) {
  float s = saturate((ZhanZ - 76.549173493) / 10.721633691);
  ZhanCenter = ((0.045022110*s + -0.189031702)*s + -0.294729367)*s + 0.638048931;
}
else if (ZhanZ <= 97.992440876) {
  float s = saturate((ZhanZ - 87.270807184) / 10.721633691);
  ZhanCenter = ((-0.055634008*s + -0.101033995)*s + -0.537726439)*s + 0.199309972;
}
else if (true) {
  float s = saturate((ZhanZ - 97.992440876) / 10.721633691);
  ZhanCenter = ((0.399287498*s + -0.798574995)*s + -0.906696453)*s + -0.495084470;
}
float ZhanWidth = 0.0;
if (ZhanZ <= 33.662638728) {
  float s = saturate((ZhanZ - 22.941005036) / 10.721633691);
  ZhanWidth = ((0.336504116*s + -0.336504116)*s + -0.336504116)*s + 4.327047906;
}
else if (ZhanZ <= 44.384272419) {
  float s = saturate((ZhanZ - 33.662638728) / 10.721633691);
  ZhanWidth = ((-0.050526415*s + 0.096035487)*s + 0.000000000)*s + 3.990543790;
}
else if (ZhanZ <= 55.105906110) {
  float s = saturate((ZhanZ - 44.384272419) / 10.721633691);
  ZhanWidth = ((0.002265112*s + -0.006285997)*s + 0.040491728)*s + 4.036052862;
}
else if (ZhanZ <= 65.827539802) {
  float s = saturate((ZhanZ - 55.105906110) / 10.721633691);
  ZhanWidth = ((-0.031526099*s + 0.029931613)*s + 0.034715070)*s + 4.072523705;
}
else if (ZhanZ <= 76.549173493) {
  float s = saturate((ZhanZ - 65.827539802) / 10.721633691);
  ZhanWidth = ((0.032521128*s + -0.073852906)*s + 0.000000000)*s + 4.105644290;
}
else if (ZhanZ <= 87.270807184) {
  float s = saturate((ZhanZ - 76.549173493) / 10.721633691);
  ZhanWidth = ((-0.010547880*s + -0.003036748)*s + -0.050142429)*s + 4.064312511;
}
else if (ZhanZ <= 97.992440876) {
  float s = saturate((ZhanZ - 87.270807184) / 10.721633691);
  ZhanWidth = ((-0.032492675*s + -0.021056909)*s + -0.087859564)*s + 4.000585455;
}
else if (true) {
  float s = saturate((ZhanZ - 97.992440876) / 10.721633691);
  ZhanWidth = ((0.353468166*s + -0.706936332)*s + -0.227451407)*s + 3.859176307;
}
float ZhanAlong = (ZhanZ - 22.941005036) / 85.773069531;
P = float3((P.x-ZhanCenter)*Dimensions.x/max(ZhanWidth,.1),0,Dimensions.y+ZhanAlong*Dimensions.z);
N = float3(0,N.y>=0?1:-1,0);
BladeOrigin = float3(0,0,0);
BladeAxis = float3(0,0,1);
// END_ZHANMADAO_BLADE_CONTOUR_V1
