float index = min(5.0,floor(Variation*6.0));
float2 cell = float2(fmod(index,3.0),floor(index/3.0));
float2 coord = (cell+clamp(UV,.015,.985))/float2(3.0,2.0);
float mask = Texture2DSample(Drops,DropsSampler,coord).b;
float2 edge = smoothstep(0.0,.075,UV)*smoothstep(0.0,.075,1.0-UV);
return smoothstep(.035,.70,mask)*edge.x*edge.y;
