// ZHANMADAO_BLADE_CONTOUR_V1: private coordinates; original PBR UVs are unchanged.
if (RuneMode < -.5) return float4(0,0,0,0);
float ZhanZ = P.z;
float ZhanFaceCoverage = smoothstep(.25,.70,abs(normalize(N.xyz).y));
RuneOpacity *= ZhanFaceCoverage;
HaloOpacity *= ZhanFaceCoverage;
float ZhanCenter = 0.0;
if (ZhanZ <= 37.892637495) {
  float s = saturate((ZhanZ - 25.461004302) / 12.431633193);
  ZhanCenter = ((-0.095340786*s + 0.095340786)*s + 0.288711830)*s + 0.692817012;
}
else if (ZhanZ <= 50.324270688) {
  float s = saturate((ZhanZ - 37.892637495) / 12.431633193);
  ZhanCenter = ((-0.044537293*s + -0.003466930)*s + 0.193371045)*s + 0.981528843;
}
else if (ZhanZ <= 62.755903881) {
  float s = saturate((ZhanZ - 50.324270688) / 12.431633193);
  ZhanCenter = ((-0.011729362*s + -0.008818610)*s + 0.052825306)*s + 1.126895664;
}
else if (ZhanZ <= 75.187537074) {
  float s = saturate((ZhanZ - 62.755903881) / 12.431633193);
  ZhanCenter = ((0.036323871*s + -0.105903993)*s + 0.000000000)*s + 1.159172998;
}
else if (ZhanZ <= 87.619170267) {
  float s = saturate((ZhanZ - 75.187537074) / 12.431633193);
  ZhanCenter = ((0.023388726*s + -0.117540368)*s + -0.102836372)*s + 1.089592877;
}
else if (ZhanZ <= 100.050803460) {
  float s = saturate((ZhanZ - 87.619170267) / 12.431633193);
  ZhanCenter = ((0.025911362*s + -0.176014924)*s + -0.267750932)*s + 0.892604862;
}
else if (ZhanZ <= 112.482436653) {
  float s = saturate((ZhanZ - 100.050803460) / 12.431633193);
  ZhanCenter = ((-0.038570515*s + -0.190665494)*s + -0.542046695)*s + 0.474750367;
}
else if (true) {
  float s = saturate((ZhanZ - 112.482436653) / 12.431633193);
  ZhanCenter = ((0.552707131*s + -1.105414262)*s + -1.039089228)*s + -0.296532337;
}
float ZhanWidth = 0.0;
if (ZhanZ <= 37.892637495) {
  float s = saturate((ZhanZ - 25.461004302) / 12.431633193);
  ZhanWidth = ((-0.005596385*s + 0.005596385)*s + 0.061401228)*s + 4.944938178;
}
else if (ZhanZ <= 50.324270688) {
  float s = saturate((ZhanZ - 37.892637495) / 12.431633193);
  ZhanWidth = ((-0.003263502*s + -0.001397939)*s + 0.055804843)*s + 5.006339406;
}
else if (ZhanZ <= 62.755903881) {
  float s = saturate((ZhanZ - 50.324270688) / 12.431633193);
  ZhanWidth = ((0.002245563*s + -0.008043995)*s + 0.043218461)*s + 5.057482808;
}
else if (ZhanZ <= 75.187537074) {
  float s = saturate((ZhanZ - 62.755903881) / 12.431633193);
  ZhanWidth = ((-0.027993736*s + 0.025057024)*s + 0.033867159)*s + 5.094902837;
}
else if (ZhanZ <= 87.619170267) {
  float s = saturate((ZhanZ - 75.187537074) / 12.431633193);
  ZhanWidth = ((0.010346694*s + -0.032645185)*s + 0.000000000)*s + 5.125833285;
}
else if (ZhanZ <= 100.050803460) {
  float s = saturate((ZhanZ - 87.619170267) / 12.431633193);
  ZhanWidth = ((0.017025098*s + -0.056588708)*s + -0.034250290)*s + 5.103534793;
}
else if (ZhanZ <= 112.482436653) {
  float s = saturate((ZhanZ - 100.050803460) / 12.431633193);
  ZhanWidth = ((-0.043536137*s + 0.001183653)*s + -0.096352413)*s + 5.029720892;
}
else if (true) {
  float s = saturate((ZhanZ - 112.482436653) / 12.431633193);
  ZhanWidth = ((0.365228856*s + -0.730457712)*s + -0.224593520)*s + 4.891015995;
}
float ZhanAlong = (ZhanZ - 25.461004302) / 99.453065544;
P = float3((P.x-ZhanCenter)*Dimensions.x/max(ZhanWidth,.1),0,Dimensions.y+ZhanAlong*Dimensions.z);
N = float3(0,N.y>=0?1:-1,0);
BladeOrigin = float3(0,0,0);
BladeAxis = float3(0,0,1);
// END_ZHANMADAO_BLADE_CONTOUR_V1
