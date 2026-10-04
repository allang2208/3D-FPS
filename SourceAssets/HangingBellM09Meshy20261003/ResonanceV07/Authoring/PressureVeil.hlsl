// Continuous low-contrast pressure front. Polar coordinates close the UV seam.
float angle=UV.x*6.2831853;
float2 p=float2(cos(angle),sin(angle))*UV.y;
float cloud=0.52+0.20*sin(p.x*7.2+p.y*4.8-Phase*.65)
                +0.16*sin(p.y*11.3-p.x*3.1+Phase*.43)
                +0.09*sin(p.x*16.8+p.y*13.7-Phase*.31);
float drift=0.70+0.30*sin(UV.y*10.5-Phase*1.4+cloud*2.4);
float edge=1.0-smoothstep(.73,1.0,UV.y);
float density=saturate(cloud)*drift*edge;
float3 tint=lerp(float3(.035,.095,.12),float3(.22,.36,.34),density);
return float4(tint,0.26*density*Alpha);
