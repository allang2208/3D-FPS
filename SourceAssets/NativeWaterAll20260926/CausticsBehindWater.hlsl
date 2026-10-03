// SingleLayerWater's behind-water depth, in linear camera depth (cm).
// Project the existing Clearwater atlas onto the opaque receiver reconstructed along
// the camera ray. This leaves the receiver's own material, lighting and shadows intact.
float3 toSurface = Position - Camera;
float3 receiver = Camera + toSurface * clamp(BehindDepth / max(PixelDepth, .01), 1, 500);
float depth = max(Position.z - receiver.z, 0);
float3 sun = normalize(SunDirection + float3(0,0,1e-5));
float3 ray = refract(-sun, float3(0,0,1), 1.0/1.3335);
float2 uv = frac((receiver.xy - ray.xy*depth/max(-ray.z,.1))/PatchCm);
float f = frac(Clock/60.0)*32;
float a=floor(f), b=fmod(a+1,32);
float2 inner=(4.5+uv*503.0)/512.0;
float2 ua=(float2(fmod(a,8),floor(a/8))+inner)/float2(8,4);
float2 ub=(float2(fmod(b,8),floor(b/8))+inner)/float2(8,4);
float3 web=lerp(Texture2DSampleLevel(Atlas,AtlasSampler,ua,0).rgb,
                Texture2DSampleLevel(Atlas,AtlasSampler,ub,0).rgb,frac(f));
float rangeFade=1-smoothstep(2500,9000,length(toSurface));
float weight=Strength*Daylight*Coverage*smoothstep(0,8,depth)*exp(-depth*.0015)*rangeFade;
return 1 + web*weight*3.0;
