// ZHANMADAO_BLADE_CONTOUR_V1: private coordinates; original PBR UVs are unchanged.
if (RuneMode < -.5) return float4(0,0,0,0);
float ZhanZ = P.z;
float ZhanFaceCoverage = smoothstep(.25,.70,abs(normalize(N.xyz).y));
RuneOpacity *= ZhanFaceCoverage;
HaloOpacity *= ZhanFaceCoverage;
float ZhanCenter = 0.0;
if (ZhanZ <= 33.616738521) {
  float s = saturate((ZhanZ - 22.889404804) / 10.727333717);
  ZhanCenter = ((-0.041444472*s + 0.041444472)*s + -0.258422154)*s + -0.094719073;
}
else if (ZhanZ <= 44.344072238) {
  float s = saturate((ZhanZ - 33.616738521) / 10.727333717);
  ZhanCenter = ((0.023337407*s + -0.080614330)*s + -0.299866626)*s + -0.353141227;
}
else if (ZhanZ <= 55.071405955) {
  float s = saturate((ZhanZ - 44.344072238) / 10.727333717);
  ZhanCenter = ((0.002169957*s + -0.043237421)*s + -0.391083066)*s + -0.710284776;
}
else if (ZhanZ <= 65.798739672) {
  float s = saturate((ZhanZ - 55.071405955) / 10.727333717);
  ZhanCenter = ((-0.006142411*s + -0.040449970)*s + -0.471048038)*s + -1.142435307;
}
else if (ZhanZ <= 76.526073389) {
  float s = saturate((ZhanZ - 65.798739672) / 10.727333717);
  ZhanCenter = ((-0.020638871*s + -0.044059460)*s + -0.570375211)*s + -1.660075726;
}
else if (ZhanZ <= 87.253407106) {
  float s = saturate((ZhanZ - 76.526073389) / 10.727333717);
  ZhanCenter = ((-0.046451874*s + -0.065379620)*s + -0.720410742)*s + -2.295149267;
}
else if (ZhanZ <= 97.980740823) {
  float s = saturate((ZhanZ - 87.253407106) / 10.727333717);
  ZhanCenter = ((0.008597028*s + -0.241228033)*s + -0.990525604)*s + -3.127391503;
}
else if (true) {
  float s = saturate((ZhanZ - 97.980740823) / 10.727333717);
  ZhanCenter = ((0.324504573*s + -0.649009146)*s + -1.447190587)*s + -4.350548112;
}
float ZhanWidth = 0.0;
if (ZhanZ <= 33.616738521) {
  float s = saturate((ZhanZ - 22.889404804) / 10.727333717);
  ZhanWidth = ((-0.004119150*s + 0.004119150)*s + 0.198535553)*s + 5.073463191;
}
else if (ZhanZ <= 44.344072238) {
  float s = saturate((ZhanZ - 33.616738521) / 10.727333717);
  ZhanWidth = ((-0.012196939*s + 0.008245241)*s + 0.194416403)*s + 5.271998744;
}
else if (ZhanZ <= 55.071405955) {
  float s = saturate((ZhanZ - 44.344072238) / 10.727333717);
  ZhanWidth = ((0.004029776*s + -0.017654100)*s + 0.174316067)*s + 5.462463449;
}
else if (ZhanZ <= 65.798739672) {
  float s = saturate((ZhanZ - 55.071405955) / 10.727333717);
  ZhanWidth = ((-0.018232548*s + 0.009719185)*s + 0.151097197)*s + 5.623155192;
}
else if (ZhanZ <= 76.526073389) {
  float s = saturate((ZhanZ - 65.798739672) / 10.727333717);
  ZhanWidth = ((-0.000273652*s + -0.018023138)*s + 0.115837921)*s + 5.765739025;
}
else if (ZhanZ <= 87.253407106) {
  float s = saturate((ZhanZ - 76.526073389) / 10.727333717);
  ZhanWidth = ((-0.053710146*s + 0.041079875)*s + 0.078970688)*s + 5.863280155;
}
else if (ZhanZ <= 97.980740823) {
  float s = saturate((ZhanZ - 87.253407106) / 10.727333717);
  ZhanWidth = ((0.022439866*s + -0.151207081)*s + 0.000000000)*s + 5.929620572;
}
else if (true) {
  float s = saturate((ZhanZ - 97.980740823) / 10.727333717);
  ZhanWidth = ((1.113954157*s + -2.227908313)*s + -0.235094565)*s + 5.800853357;
}
float ZhanAlong = (ZhanZ - 22.889404804) / 85.818669736;
P = float3((P.x-ZhanCenter)*Dimensions.x/max(ZhanWidth,.1),0,Dimensions.y+ZhanAlong*Dimensions.z);
N = float3(0,N.y>=0?1:-1,0);
BladeOrigin = float3(0,0,0);
BladeAxis = float3(0,0,1);
// END_ZHANMADAO_BLADE_CONTOUR_V1
