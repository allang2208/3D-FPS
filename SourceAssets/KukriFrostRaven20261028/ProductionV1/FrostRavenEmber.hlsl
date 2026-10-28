float2 p=UV*2.0-1.0;
float radius=dot(p,p);
float crystal=1.0-smoothstep(.12,.52,abs(p.x)*1.3+abs(p.y));
float halo=max(0.0,exp(-radius*5.0)-exp(-5.0));
float boundary=(1.0-smoothstep(.76,.99,abs(p.x)))*(1.0-smoothstep(.76,.99,abs(p.y)));
float shape=lerp(crystal*.70+halo*.35,halo*.35,saturate(Kind));
float3 light=lerp(float3(.22,.85,1.8),float3(.85,1.75,2.5),crystal);
return float4(light,saturate(shape*boundary*Alpha*.65));
