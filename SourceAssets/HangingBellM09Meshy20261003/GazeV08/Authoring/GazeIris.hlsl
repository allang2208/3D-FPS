float2 p=UV*2-1;
float radius=length(p),angle=atan2(p.y,p.x);
float feather=1-smoothstep(.30,1.,radius);
float fibers=.64+.13*sin(angle*19+radius*15-Clock*2)+.08*sin(angle*31-radius*23);
float pupil=.30+.70*smoothstep(.035,.23,radius);
float3 tint=lerp(float3(.18,.13,.30),float3(.34,.40,.46),saturate(1-radius));
return float4(tint*(2.1+.8*FirePower)/max(Exposure,.25),Strength*InstanceAlpha*.62*feather*fibers*pupil);
