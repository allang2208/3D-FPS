float along=P.z+35.5;
float2 radial=P.xy-float2(-.0445214100,.1056659501);
float radius=max(length(radial),.001);
float angle=atan2(radial.x,-radial.y);
angle-=3.14159265359*floor((angle+1.57079632679)/3.14159265359);
float2 uv=saturate(float2(.5+angle*radius/(33.5*.25),1-along/33.5));
float3 ink=Texture2DSample(RuneTexture,RuneTextureSampler,uv).rgb;
float inside=smoothstep(0,.6,along)*(1-smoothstep(32.9,33.5,along));
inside*=smoothstep(0,.07,1.57079632679-abs(angle));
inside*=1-smoothstep(.2,.55,abs(normalize(N).z));
inside*=step(-.5,RuneMode);
float time=PreviewTime>=0?PreviewTime:T;
float breath=smoothstep(.22,.92,.5+.5*sin(along*.48-time*1.6));
float pulse=.46+1.18*breath;
float3 bluewhite=lerp(ConductionGlowColor,float3(.86,.94,1),.32);
float3 emission=bluewhite*ink.g*pulse*GlowStrength*2.1;
// Coverage is permanent silver. Only the narrow recessed channels carry current.
return float4(emission,ink.r*inside);