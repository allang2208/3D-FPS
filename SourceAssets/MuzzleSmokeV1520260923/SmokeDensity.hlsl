// Use the most readable rolling part of the original 64-frame simulation.
float frame = lerp(2.0, 56.0, pow(saturate(ParticleAge), 0.88));
float first = floor(frame);
float second = min(first + 1.0, 63.0);
float2 uv = clamp(SpriteUV, 0.5/256.0, 255.5/256.0);
float2 a = float2(fmod(first,8.0),floor(first/8.0));
float2 b = float2(fmod(second,8.0),floor(second/8.0));
float da = Texture2DSampleLevel(SmokeAtlas,SmokeAtlasSampler,(a+uv)/8.0,0).r;
float db = Texture2DSampleLevel(SmokeAtlas,SmokeAtlasSampler,(b+uv)/8.0,0).r;
// Lift thin tendrils while keeping transparent atlas gutters exactly zero.
return pow(saturate(lerp(da,db,frac(frame))),0.78) * 1.15;
