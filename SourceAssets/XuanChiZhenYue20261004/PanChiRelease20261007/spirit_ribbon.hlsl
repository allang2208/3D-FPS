// Geometry supplies the curved, rolling body. UV0 retains the original painted
// dragon silhouette; UV1 carries dragon identity and valid floor coverage.
float side = Meta.x;
float seconds = max(0,Seconds-.045*side);
float tail = 1-UV.x;
float reveal = smoothstep(.01,.12,seconds-.075*tail);
float dissolveAt = .57+.30*UV.x;
float noise = frac(sin(dot(floor(UV*float2(91,37)),float2(12.9898,78.233)))*43758.5453);
float gone = smoothstep(dissolveAt,dissolveAt+.22,seconds);
// Keep the painted body intact before its dissolve window. The old threshold
// already eroded bright scales at gone=0, then faded the remainder a second time.
float dissolve = 1-smoothstep(noise*.82,noise*.82+.18,gone);
float tailRipple = sin(UV.x*24-seconds*15+side*1.8)*.008*tail;
float2 sampleUV = float2(UV.x,saturate(UV.y+tailRipple));
float4 art = Texture2DSample(Dragon,DragonSampler,sampleUV);
float luma = dot(art.rgb,float3(.2126,.7152,.0722));
float scales = smoothstep(.32,.85,luma);
float head = smoothstep(.65,.95,UV.x);
float flow = pow(saturate(.5+.5*sin(UV.x*17-seconds*19+side*2)),5);
float3 amber = float3(.62,.23,.025);
float3 copper = float3(1,.50,.10);
float3 paleGold = float3(1,.81,.36);
float3 color = lerp(amber,copper,smoothstep(.02,.55,UV.x));
color = lerp(color,paleGold,head*.70+scales*.18);
float strength = 2.9+scales*1.6+flow*.55+head*.8;
float density = lerp(.82,.98,saturate((Charge-1)/2));
// Lift soft painted dragon detail without filling transparent gaps or the card.
float coverage = pow(saturate(art.a),.70)*smoothstep(.005,.035,art.a);
float alpha = coverage*reveal*dissolve*Meta.y*density*(.88+.12*head);
float border = smoothstep(0,.035,UV.x)*(1-smoothstep(.97,1,UV.x));
return float4(color*strength,alpha*border);
