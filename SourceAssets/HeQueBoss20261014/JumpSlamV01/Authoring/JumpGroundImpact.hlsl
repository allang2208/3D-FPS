float3 flow=Texture2DSample(FlowTex,FlowTexSampler,float2(frac(UV.x+Phase*.045),UV.y)).rgb;
float rim=sin(saturate(UV.y)*3.14159265);
float broken=smoothstep(.15+Phase*.45,.78,flow.r);
float flash=1-smoothstep(0,.12,Phase);
float opacity=pow(saturate(rim),.65)*(.35+.45*broken)*Alpha;
float3 color=lerp(float3(.28,.24,.19),float3(.72,.64,.52),flow.r)+float3(.9,.83,.70)*flash;
return float4(color,saturate(opacity));
