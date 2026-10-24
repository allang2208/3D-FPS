// Pixel shader only: remove waves smaller than the visible pixel footprint.
float2 p=Position.xy*.01; float2 px=ddx(p), py=ddy(p);
float2 slope=0;
{
 float2 k=float2(2.5952287092,1.7756828176);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-0.9828446400)-5.5501470200*Clock;
 slope+=float2(0.0272441660,0.0186407453)*cos(ph)*resolved;
}
{
 float2 k=float2(2.1854557571,1.7756828167);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-0.3103890500)-5.2359877600*Clock;
 slope+=float2(0.0188139111,0.0152863029)*cos(ph)*resolved;
}
{
 float2 k=float2(2.8684106967,0.5463639464);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(1.0816826500)-5.3407075100*Clock;
 slope+=float2(0.0246810391,0.0047011503)*cos(ph)*resolved;
}
{
 float2 k=float2(1.7756827952,2.4586377374);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-0.8812377300)-5.4454272700*Clock;
 slope+=float2(0.0151655385,0.0209984382)*cos(ph)*resolved;
}
{
 float2 k=float2(3.2781836464,1.2293188586);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(0.9175480600)-5.7595865300*Clock;
 slope+=float2(0.0279672009,0.0104877003)*cos(ph)*resolved;
}
{
 float2 k=float2(2.0488647854,2.3220467609);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(0.2010292600)-5.4454272700*Clock;
 slope+=float2(0.0169961939,0.0192623531)*cos(ph)*resolved;
}
{
 float2 k=float2(2.7318197126,1.6390918339);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-1.0816126600)-5.5501470200*Clock;
 slope+=float2(0.0210593523,0.0126356114)*cos(ph)*resolved;
}
{
 float2 k=float2(1.3659098645,3.4147746246);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(2.1167774300)-5.9690260400*Clock;
 slope+=float2(0.0103414265,0.0258535660)*cos(ph)*resolved;
}
{
 float2 k=float2(2.3220467416,2.3220467416);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(0.0605280800)-5.6548667800*Clock;
 slope+=float2(0.0170543187,0.0170543187)*cos(ph)*resolved;
}
{
 float2 k=float2(1.9122737816,1.0927278815);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(1.3582346600)-4.6076692300*Clock;
 slope+=float2(0.0129924853,0.0074242773)*cos(ph)*resolved;
}
{
 float2 k=float2(0.4097729623,2.4586377238);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-1.1634212200)-4.9218284900*Clock;
 slope+=float2(0.0027421802,0.0164530807)*cos(ph)*resolved;
}
{
 float2 k=float2(1.7756827943,0.8195459141);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(1.4564111500)-4.2935099600*Clock;
 slope+=float2(0.0110685234,0.0051085493)*cos(ph)*resolved;
}
{
 float2 k=float2(3.2781836368,2.3220467427);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-1.0919098100)-6.1784655500*Clock;
 slope+=float2(0.0197515481,0.0139906799)*cos(ph)*resolved;
}
{
 float2 k=float2(0.6829549149,1.6390918099);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-0.2520113400)-4.0840704500*Clock;
 slope+=float2(0.0032135214,0.0077124515)*cos(ph)*resolved;
}
{
 float2 k=float2(3.9611385667,2.3220467476);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-1.6029799000)-6.7020643300*Clock;
 slope+=float2(0.0177848388,0.0104255951)*cos(ph)*resolved;
}
{
 float2 k=float2(3.9611385578,3.0050016611);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(1.5541090800)-6.9115038400*Clock;
 slope+=float2(0.0169016237,0.0128219214)*cos(ph)*resolved;
}
{
 float2 k=float2(5.6002303704,4.2343204965);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(1.0289946800)-8.2728606500*Clock;
 slope+=float2(0.0189650681,0.0143394417)*cos(ph)*resolved;
}
{
 float2 k=float2(1.6390918184,0.1365909849);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-0.5454479700)-3.9793506900*Clock;
 slope+=float2(0.0052946272,0.0004412189)*cos(ph)*resolved;
}
{
 float2 k=float2(3.4147746336,4.5075025118);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(0.9914444500)-7.4351026100*Clock;
 slope+=float2(0.0109845446,0.0144995989)*cos(ph)*resolved;
}
{
 float2 k=float2(5.4636393832,2.8684106916);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(1.5352025800)-7.7492618800*Clock;
 slope+=float2(0.0171176915,0.0089867881)*cos(ph)*resolved;
}
{
 float2 k=float2(1.2293188581,0.8195459153);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-2.3846708400)-3.7699111800*Clock;
 slope+=float2(0.0036474874,0.0024316583)*cos(ph)*resolved;
}
{
 float2 k=float2(7.6490951441,2.7318197233);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-0.5190133400)-8.9011791900*Clock;
 slope+=float2(0.0187439547,0.0066942696)*cos(ph)*resolved;
}
{
 float2 k=float2(7.9222770882,3.5513655733);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-0.5816598200)-9.2153384500*Clock;
 slope+=float2(0.0191498866,0.0085844319)*cos(ph)*resolved;
}
{
 float2 k=float2(9.4247779155,1.5025007911);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-0.1173169400)-9.6342174700*Clock;
 slope+=float2(0.0190783894,0.0030414823)*cos(ph)*resolved;
}
{
 float2 k=float2(0.9561368930,0.8195459065);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(1.4373442800)-3.4557519200*Clock;
 slope+=float2(0.0016922476,0.0014504979)*cos(ph)*resolved;
}
{
 float2 k=float2(9.8345509066,4.9172755083);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-0.2236435800)-10.3672557600*Clock;
 slope+=float2(0.0146378439,0.0073189220)*cos(ph)*resolved;
}
{
 float2 k=float2(11.4736426828,2.7318197313);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-1.0362330500)-10.6814150200*Clock;
 slope+=float2(0.0160061905,0.0038109978)*cos(ph)*resolved;
}
{
 float2 k=float2(1.0927278853,0.4097729541);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-0.5842376700)-3.3510321600*Clock;
 slope+=float2(0.0011439659,0.0004289872)*cos(ph)*resolved;
}
{
 float2 k=float2(9.1515960375,9.9711418422);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-1.0061830400)-11.5191730600*Clock;
 slope+=float2(0.0085883153,0.0093574181)*cos(ph)*resolved;
}
{
 float2 k=float2(12.1565976912,7.9222771210);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-1.5867384700)-11.9380520800*Clock;
 slope+=float2(0.0085791541,0.0055909094)*cos(ph)*resolved;
}
{
 float2 k=float2(14.8884173285,6.0100032811);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-0.8949471000)-12.4616508600*Clock;
 slope+=float2(0.0080191993,0.0032371080)*cos(ph)*resolved;
}
{
 float2 k=float2(0.8195459133,0.6829549277);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-0.8613851900)-3.1415926500*Clock;
 slope+=float2(0.0003049612,0.0002541344)*cos(ph)*resolved;
}
{
 float2 k=float2(11.8834156525,13.3859164368);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-0.6370127700)-13.1946891500*Clock;
 slope+=float2(0.0038044755,0.0042855011)*cos(ph)*resolved;
}
{
 float2 k=float2(17.2104640102,10.2443238728);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(1.6925929600)-14.0324471900*Clock;
 slope+=float2(0.0043000344,0.0025595443)*cos(ph)*resolved;
}
{
 float2 k=float2(0.0000000000,0.9561368900);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-1.5262558000)-3.0368729000*Clock;
 slope+=float2(0.0000000000,0.0002141651)*cos(ph)*resolved;
}
{
 float2 k=float2(16.5275092211,15.8445543343);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-1.2418008100)-14.9749249800*Clock;
 slope+=float2(0.0020168520,0.0019335110)*cos(ph)*resolved;
}
{
 float2 k=float2(0.6829549260,0.4097729572);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-0.5620945200)-2.7227136300*Clock;
 slope+=float2(0.0000574775,0.0000344865)*cos(ph)*resolved;
}
{
 float2 k=float2(0.6829549286,0.2731819744);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(1.4127576800)-2.6179938800*Clock;
 slope+=float2(0.0000279807,0.0000111923)*cos(ph)*resolved;
}
{
 float2 k=float2(0.4097729520,0.5463639360);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-0.7662293500)-2.5132741200*Clock;
 slope+=float2(0.0000095641,0.0000127521)*cos(ph)*resolved;
}
{
 float2 k=float2(-0.5463639348,0.2731819704);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(2.1804430700)-2.4085543700*Clock;
 slope+=float2(-0.0000035186,0.0000017593)*cos(ph)*resolved;
}
{
 float2 k=float2(0.0000000000,0.5463639400);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-0.2687667100)-2.3038346100*Clock;
 slope+=float2(0.0000000000,0.0000015080)*cos(ph)*resolved;
}
{
 float2 k=float2(0.2731819718,0.4097729527);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(1.7678373800)-2.0943951000*Clock;
 slope+=float2(0.0000003469,0.0000005204)*cos(ph)*resolved;
}
{
 float2 k=float2(0.1365909866,0.4097729554);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-1.7038033500)-1.9896753500*Clock;
 slope+=float2(0.0000000601,0.0000001803)*cos(ph)*resolved;
}
{
 float2 k=float2(0.2731819717,0.2731819717);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(-0.8154491500)-1.8849555900*Clock;
 slope+=float2(0.0000000273,0.0000000273)*cos(ph)*resolved;
}
{
 float2 k=float2(0.1365909875,0.2731819719);
 float footprint=max(abs(dot(k,px)),abs(dot(k,py)));
 float resolved=1.0-smoothstep(.65,2.4,footprint);
 float ph=dot(k,p)+(0.2081521800)-1.6755160800*Clock;
 slope+=float2(0.0000000014,0.0000000027)*cos(ph)*resolved;
}
return float3(0,slope)*WaveHeightScale;
