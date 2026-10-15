float2 p=float2(frac(UV.x+Phase*.028),.10+UV.y*.78);
float3 flow=Texture2DSample(FlowTex,FlowTexSampler,p).rgb;
float3 fine=Texture2DSample(FlowTex,FlowTexSampler,float2(frac(p.x+(flow.b-.5)*.025),saturate(p.y+(flow.r-.5)*.065))).rgb;
float profile=pow(saturate(sin(UV.y*3.14159265)),.55);
// A continuous readable pressure front with broken dusty shoulders behind it.
float front=exp(-pow((UV.y-.88)/.055,2));
float shoulder=exp(-pow((UV.y-.70)/.12,2));
float rubble=smoothstep(.18,.70,fine.r);
float erode=smoothstep(.65,1.10,Phase);
float fragments=smoothstep(erode*.64,erode*.64+.22,fine.r);
float dustAlpha=profile*(.40+.42*rubble)*fragments;
float edgeAlpha=(front*.92+shoulder*.18)*(1-erode*.6);
float opacity=max(dustAlpha,edgeAlpha)*Alpha*smoothstep(0,.018,Phase);
float3 dust=lerp(float3(.15,.12,.09),float3(.82,.68,.48),fine.r);
float3 color=dust+float3(3.4,2.95,2.15)*front*(.85+.15*flow.g)
    +float3(.70,.57,.38)*shoulder*(1-erode);
return float4(color,saturate(opacity));
