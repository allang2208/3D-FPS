// Original Mantaflow density bake: 8x8 tiles, 64 frames, 256px per tile.
// Each particle advances independently. Adjacent frames interpolate without
// wrapping to frame zero. The existing particle alpha controls birth/death.
float animationFrame = saturate(ParticleAge) * 63.0;
float first = floor(animationFrame);
float second = min(first + 1.0, 63.0);
float2 localUV = clamp(SpriteUV, 0.5 / 256.0, 255.5 / 256.0);
float2 tileA = float2(fmod(first, 8.0), floor(first / 8.0));
float2 tileB = float2(fmod(second, 8.0), floor(second / 8.0));
// Mips are disabled for this small sprite atlas: neighboring animation tiles
// must never enter a filtered sample. Four transparent texels guard each tile.
float densityA = Texture2DSampleLevel(SmokeAtlas, SmokeAtlasSampler, (tileA + localUV) / 8.0, 0).r;
float densityB = Texture2DSampleLevel(SmokeAtlas, SmokeAtlasSampler, (tileB + localUV) / 8.0, 0).r;
// Make fresh muzzle smoke more readable, easing back as it spreads. Apply the
// gain after coverage clamping so dense curls retain the same relative boost;
// the downstream particle alpha and aged sightline mask still control opacity.
float visibilityGain = lerp(1.35, 1.15, smoothstep(0.15, 0.70, saturate(ParticleAge)));
return saturate(lerp(densityA, densityB, frac(animationFrame)) * 0.9) * visibilityGain;
