// Thunder Lance iris veil — converging charge bloom at the muzzle and a
// directional bloom at the beam head.
float2 p=UV*2-1;
float radius=length(p),angle=atan2(p.y,p.x);
float feather=1-smoothstep(.30,1.,radius);
float fibers=.64+.13*sin(angle*19+radius*15-Clock*3)+.08*sin(angle*31-radius*23);
float pupil=.30+.70*smoothstep(.035,.23,radius);
float3 tint=lerp(float3(.10,.26,.85),float3(.60,.92,1.0),saturate(1-radius));
return float4(tint*(2.4+.9*FirePower)/max(Exposure,.25),Strength*InstanceAlpha*.66*feather*fibers*pupil);
