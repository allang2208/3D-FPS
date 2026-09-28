// Generated from the active fountain native-water spectrum. Do not hand-edit.
// Same phase / sincos / slope evaluation as ClearwaterNative WaveField.hlsl.
float2 p=(P.xy-float2(-2400,-1300))*.01;
float height=0; float2 slope=0; float crest=0;
{ // original spectrum term 0
 float ph=dot(p,float2(0.025952287092,0.017756828176))+(-0.982844640000)-Clock*0.749269847700;
 float s,c; sincos(ph,s,c);
 height+=149.153951244404*s;
 slope+=float2(0.059937165180,0.041009639716)*c;
 crest+=smoothstep(.68,1,s)*0.091356944938;
}
{ // original spectrum term 1
 float ph=dot(p,float2(0.021854557571,0.017756828167))+(-0.310389050000)-Clock*0.706858347600;
 float s,c; sincos(ph,s,c);
 height+=166.903767147574*s;
 slope+=float2(0.041390604468,0.033629866397)*c;
 crest+=smoothstep(.68,1,s)*0.074917065241;
}
{ // original spectrum term 2
 float ph=dot(p,float2(0.028684106967,0.005463639464))+(1.081682650000)-Clock*0.720995513850;
 float s,c; sincos(ph,s,c);
 height+=153.412851870668*s;
 slope+=float2(0.054298285913,0.010342530729)*c;
 crest+=smoothstep(.68,1,s)*0.074879992620;
}
{ // original spectrum term 3
 float ph=dot(p,float2(0.017756827952,0.024586377374))+(-0.881237730000)-Clock*0.735132681450;
 float s,c; sincos(ph,s,c);
 height+=136.841187083350*s;
 slope+=float2(0.033364184778,0.046196563933)*c;
 crest+=smoothstep(.68,1,s)*0.074325208686;
}
{ // original spectrum term 4
 float ph=dot(p,float2(0.032781836464,0.012293188586))+(0.917548060000)-Clock*0.777544181550;
 float s,c; sincos(ph,s,c);
 height+=75.842927888108*s;
 slope+=float2(0.061527842034,0.023072940598)*c;
 crest+=smoothstep(.68,1,s)*0.074243666326;
}
{ // original spectrum term 5
 float ph=dot(p,float2(0.020488647854,0.023220467609))+(0.201029260000)-Clock*0.735132681450;
 float s,c; sincos(ph,s,c);
 height+=124.287397368096*s;
 slope+=float2(0.037391626620,0.042377176911)*c;
 crest+=smoothstep(.68,1,s)*0.072190835230;
}
{ // original spectrum term 6
 float ph=dot(p,float2(0.027318197126,0.016390918339))+(-1.081612660000)-Clock*0.749269847700;
 float s,c; sincos(ph,s,c);
 height+=104.426905249905*s;
 slope+=float2(0.046330575062,0.027798345145)*c;
 crest+=smoothstep(.68,1,s)*0.067086736008;
}
{ // original spectrum term 7
 float ph=dot(p,float2(0.013659098645,0.034147746246))+(2.116777430000)-Clock*0.805818515400;
 float s,c; sincos(ph,s,c);
 height+=50.770671980199*s;
 slope+=float2(0.022751138336,0.056877845227)*c;
 crest+=smoothstep(.68,1,s)*0.065887358410;
}
{ // original spectrum term 8
 float ph=dot(p,float2(0.023220467416,0.023220467416))+(0.060528080000)-Clock*0.763407015300;
 float s,c; sincos(ph,s,c);
 height+=88.215840978772*s;
 slope+=float2(0.037519501217,0.037519501217)*c;
 crest+=smoothstep(.68,1,s)*0.063915634551;
}
{ // original spectrum term 9
 float ph=dot(p,float2(0.019122737816,0.010927278815))+(1.358234660000)-Clock*0.622035346050;
 float s,c; sincos(ph,s,c);
 height+=149.473720000000*s;
 slope+=float2(0.028583467579,0.016333410139)*c;
 crest+=smoothstep(.68,1,s)*0.059127000703;
}
{ // original spectrum term 10
 float ph=dot(p,float2(0.004097729623,0.024586377238))+(-1.163421220000)-Clock*0.664446846150;
 float s,c; sincos(ph,s,c);
 height+=147.222900000000*s;
 slope+=float2(0.006032796385,0.036196777575)*c;
 crest+=smoothstep(.68,1,s)*0.058236648635;
}
{ // original spectrum term 11
 float ph=dot(p,float2(0.017756827943,0.008195459141))+(1.456411150000)-Clock*0.579623844600;
 float s,c; sincos(ph,s,c);
 height+=137.134580000000*s;
 slope+=float2(0.024350751421,0.011238808472)*c;
 crest+=smoothstep(.68,1,s)*0.054246033404;
}
{ // original spectrum term 12
 float ph=dot(p,float2(0.032781836368,0.023220467427))+(-1.091909810000)-Clock*0.834092849250;
 float s,c; sincos(ph,s,c);
 height+=20.896301545445*s;
 slope+=float2(0.043453405906,0.030779495850)*c;
 crest+=smoothstep(.68,1,s)*0.052433826243;
}
{ // original spectrum term 13
 float ph=dot(p,float2(0.006829549149,0.016390918099))+(-0.252011340000)-Clock*0.551349510750;
 float s,c; sincos(ph,s,c);
 height+=103.517040000000*s;
 slope+=float2(0.007069747124,0.016967393245)*c;
 crest+=smoothstep(.68,1,s)*0.040948014787;
}
{ // original spectrum term 14
 float ph=dot(p,float2(0.039611385667,0.023220467476))+(-1.602979900000)-Clock*0.904778684550;
 float s,c; sincos(ph,s,c);
 height+=2.491452721691*s;
 slope+=float2(0.039126645296,0.022936309327)*c;
 crest+=smoothstep(.68,1,s)*0.039072714551;
}
{ // original spectrum term 15
 float ph=dot(p,float2(0.039611385578,0.030050016611))+(1.554109080000)-Clock*0.933053018400;
 float s,c; sincos(ph,s,c);
 height+=0.033664619156*s;
 slope+=float2(0.037183572067,0.028208227053)*c;
 crest+=smoothstep(.68,1,s)*0.037132319667;
}
return float4(height,slope,crest);
