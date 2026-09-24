// Small analytic eddies and bubbles: no new texture, collision or simulation.
float wet=1-saturate(Dryness);
float2 p=UV*13+float2(Variation*17.3,Variation*7.9);
float t=Clock*.29;
float sx=sin(p.x+sin(p.y*.71+t)+t*.61);
float sy=cos(p.y-sin(p.x*.67-t*.73)-t*.41);
float2 advected=p+float2(sy,sx)*.38;
float cloud=sin(advected.x)*cos(advected.y*.87);
float bubble=smoothstep(.89,.99,sin(advected.x*2.71+t)*sin(advected.y*2.17-t*.63));
return float4(float2(sx,sy)*.017*wet,bubble*wet,cloud*wet);
