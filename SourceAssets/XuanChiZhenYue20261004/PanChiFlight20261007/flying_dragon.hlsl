float u=UV.x;
float2 sampleUV=float2(u,saturate(UV.y+sin(u*24-Seconds*16)*.007*(1-u)));
float4 art=Texture2DSample(Dragon,DragonSampler,sampleUV);
float detail=smoothstep(.25,.88,dot(art.rgb,float3(.2126,.7152,.0722)));
float head=smoothstep(.68,.95,u);
float3 amber=float3(.56,.18,.022),gold=float3(1,.52,.10),pale=float3(1,.82,.36);
float3 color=lerp(amber,gold,smoothstep(.03,.54,u));
color=lerp(color,pale,head*.68+detail*.16);
float wave=pow(saturate(.5+.5*sin(u*20-Seconds*20)),5);
float brightness=2.8+detail*1.8+head*.85+wave*.45;
float noise=frac(sin(dot(floor(UV*float2(97,43)),float2(12.9898,78.233)))*43758.5453);
float dissolve=1-smoothstep(noise*.80,noise*.80+.20,Dissolve);
float coverage=pow(saturate(art.a),.70)*smoothstep(.005,.035,art.a);
float edge=smoothstep(0,.025,u)*(1-smoothstep(.985,1,u));
float nearFade=smoothstep(40,105,Depth);
// The translucent body retains gold contrast against bright sky; only carving
// highlights bloom. Fade is driven by real flight stop, never a fixed .57s age.
float alpha=coverage*Opacity*dissolve*edge*nearFade*lerp(.82,.96,saturate((Charge-1)/2));
return float4(color*brightness,saturate(alpha));
