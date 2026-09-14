float frame = 2.0 + saturate(Age) * 25.0 + Variation * 3.0;
float i0 = floor(frame), i1 = i0 + 1.0;
float2 inset = clamp(UV, 0.016, 0.984);
float2 a = (float2(fmod(i0,8.0),floor(i0/8.0)) + inset) / 8.0;
float2 b = (float2(fmod(i1,8.0),floor(i1/8.0)) + inset) / 8.0;
float density = lerp(Texture2DSample(Wisp,WispSampler,a).a,
                     Texture2DSample(Wisp,WispSampler,b).a,frac(frame));
float2 p = (UV-.5)*2;
float edge = 1.0-smoothstep(.60,1.0,length(p));
return saturate(density*3.4)*edge;
