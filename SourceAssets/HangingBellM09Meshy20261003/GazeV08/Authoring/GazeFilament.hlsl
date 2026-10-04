float edge=pow(saturate(1-abs(UV.x*2-1)),2.3);
float flow=.66+.34*sin(UV.y*13-Clock*14);
float tips=smoothstep(0.,.055,UV.y)*(1-smoothstep(.94,1.,UV.y));
float3 tint=lerp(float3(.25,.18,.38),float3(.37,.39,.46),flow);
return float4(tint*(1.6+.7*FirePower)/max(Exposure,.25),Strength*InstanceAlpha*edge*tips*.48);
