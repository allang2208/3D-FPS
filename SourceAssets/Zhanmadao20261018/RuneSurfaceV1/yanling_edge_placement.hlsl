// ZHANMADAO_BLADE_CONTOUR_V1: private coordinates; original PBR UVs are unchanged.
if (RuneMode < -.5) return float4(0,0,0,0);
float ZhanZ = P.z;
float ZhanFaceCoverage = smoothstep(.25,.70,abs(normalize(N.xyz).y));
RuneOpacity *= ZhanFaceCoverage;
HaloOpacity *= ZhanFaceCoverage;
float ZhanCenter = 0.0;
if (ZhanZ <= 33.616738521) {
  float s = saturate((ZhanZ - 22.889404804) / 10.727333717);
  ZhanCenter = ((-0.074458138*s + 0.074458138)*s + 0.074458138)*s + 0.071191509;
}
else if (ZhanZ <= 44.344072238) {
  float s = saturate((ZhanZ - 33.616738521) / 10.727333717);
  ZhanCenter = ((0.112028716*s + -0.257349970)*s + 0.000000000)*s + 0.145649647;
}
else if (ZhanZ <= 55.071405955) {
  float s = saturate((ZhanZ - 44.344072238) / 10.727333717);
  ZhanCenter = ((-0.035157094*s + -0.017923104)*s + -0.178613792)*s + 0.000328393;
}
else if (ZhanZ <= 65.798739672) {
  float s = saturate((ZhanZ - 55.071405955) / 10.727333717);
  ZhanCenter = ((0.187917786*s + -0.384701000)*s + -0.319931282)*s + -0.231365596;
}
else if (ZhanZ <= 76.526073389) {
  float s = saturate((ZhanZ - 65.798739672) / 10.727333717);
  ZhanCenter = ((-0.120347081*s + 0.111172129)*s + -0.525579924)*s + -0.748080092;
}
else if (ZhanZ <= 87.253407106) {
  float s = saturate((ZhanZ - 76.526073389) / 10.727333717);
  ZhanCenter = ((0.141471358*s + -0.353790022)*s + -0.664276909)*s + -1.282834968;
}
else if (ZhanZ <= 97.980740823) {
  float s = saturate((ZhanZ - 87.253407106) / 10.727333717);
  ZhanCenter = ((-0.235882595*s + 0.152576458)*s + -0.947442879)*s + -2.159430542;
}
else if (true) {
  float s = saturate((ZhanZ - 97.980740823) / 10.727333717);
  ZhanCenter = ((0.605549420*s + -1.211098839)*s + -1.349937747)*s + -3.190179557;
}
float ZhanWidth = 0.0;
if (ZhanZ <= 33.616738521) {
  float s = saturate((ZhanZ - 22.889404804) / 10.727333717);
  ZhanWidth = ((-0.062291406*s + 0.062291406)*s + 0.132889978)*s + 4.829623582;
}
else if (ZhanZ <= 44.344072238) {
  float s = saturate((ZhanZ - 33.616738521) / 10.727333717);
  ZhanWidth = ((-0.001723387*s + -0.020807882)*s + 0.070598572)*s + 4.962513560;
}
else if (ZhanZ <= 55.071405955) {
  float s = saturate((ZhanZ - 44.344072238) / 10.727333717);
  ZhanWidth = ((0.015957628*s + -0.023943689)*s + 0.023812647)*s + 5.010580863;
}
else if (ZhanZ <= 65.798739672) {
  float s = saturate((ZhanZ - 55.071405955) / 10.727333717);
  ZhanWidth = ((-0.022863438*s + 0.047014696)*s + 0.023798154)*s + 5.026407450;
}
else if (ZhanZ <= 76.526073389) {
  float s = saturate((ZhanZ - 65.798739672) / 10.727333717);
  ZhanWidth = ((0.025549069*s + -0.024190164)*s + 0.049237231)*s + 5.074356861;
}
else if (ZhanZ <= 87.253407106) {
  float s = saturate((ZhanZ - 76.526073389) / 10.727333717);
  ZhanWidth = ((-0.072841270*s + 0.160880118)*s + 0.077504109)*s + 5.124952997;
}
else if (ZhanZ <= 97.980740823) {
  float s = saturate((ZhanZ - 87.253407106) / 10.727333717);
  ZhanWidth = ((-0.217280647*s + 0.235550703)*s + 0.180740536)*s + 5.290495954;
}
else if (true) {
  float s = saturate((ZhanZ - 97.980740823) / 10.727333717);
  ZhanWidth = ((0.067119850*s + -0.134239699)*s + 0.000000000)*s + 5.489506545;
}
float ZhanAlong = (ZhanZ - 22.889404804) / 85.818669736;
P = float3((P.x-ZhanCenter)*Dimensions.x/max(ZhanWidth,.1),0,Dimensions.y+ZhanAlong*Dimensions.z);
N = float3(0,N.y>=0?1:-1,0);
BladeOrigin = float3(0,0,0);
BladeAxis = float3(0,0,1);
// END_ZHANMADAO_BLADE_CONTOUR_V1
