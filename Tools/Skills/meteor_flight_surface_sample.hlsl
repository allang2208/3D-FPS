// Flight-only loop; the impact materials keep their own clamped playback.
float2 p=UV;
p.x=Dynamic.y>.5?1-p.x:p.x;
float frame=frac(Dynamic.x)*64;
float f0=floor(frame);
float f1=fmod(f0+1,64);
float2 inset=(4.5+saturate(p)*247)/256;
float2 cell0=float2(fmod(f0,8),floor(f0/8));
float2 cell1=float2(fmod(f1,8),floor(f1/8));
float4 a=Texture2DSampleLevel(Atlas,AtlasSampler,(cell0+inset)/8,0);
float4 b=Texture2DSampleLevel(Atlas,AtlasSampler,(cell1+inset)/8,0);
return lerp(a,b,frac(frame));
