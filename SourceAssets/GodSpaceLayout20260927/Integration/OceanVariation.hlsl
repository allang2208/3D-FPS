// Common to both material sections: no ring-shaped changes at their boundary.
float2 p = (P.xy-float2(-2400,-1300))*.01;
GodSpaceOceanNoise noise;
float a = noise.value_gradient(p/1370 + float2(7.13,2.31) - Clock*float2(.0008,.00023)).x;
float b = noise.value_gradient(p/2710 + float2(1.97,9.43) - Clock*float2(-.00019,.00051)).x;
return float2(a,b);
