float face=abs(dot(normalize(Normal),normalize(View)));
float core=pow(face,8);
return float3(.035,1,.19)*3.8+float3(.46,1,.62)*core*1.9;
