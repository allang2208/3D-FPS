float3 flow=Texture2DSample(FlowTex,FlowTexSampler,float2(frac(UV.x+Phase*.04),UV.y)).rgb;
float rim=pow(saturate(sin(saturate(UV.y)*3.14159265)),.55);
float broken=smoothstep(.08+Phase*.55,.78,flow.r);
float flash=1-smoothstep(.025,.13,Phase);
float opacity=rim*(.47+.43*broken)*Alpha;
float3 color=lerp(float3(.18,.14,.10),float3(.88,.72,.50),flow.r)
    +float3(2.9,2.45,1.75)*flash;
return float4(color,saturate(opacity));
