// Central seat front/back faces, in the unchanged weapon-origin static mesh.
// Keep the source rune mask, palette and fade envelope; only placement differs.
float3 offset = P.xyz - float3(0, 0, 92.9);
float along = offset.z + 4.3;
float2 uv = float2(.5 + offset.x / 7.5, .5 - offset.z / 8.6);
float inside = smoothstep(0, .035, uv.x) * (1 - smoothstep(.965, 1, uv.x));
inside *= smoothstep(0, .035, uv.y) * (1 - smoothstep(.965, 1, uv.y));
// Exclude the head-contact cheeks, top cap, bottom collar and recessed core.
inside *= smoothstep(.65, .90, abs(normalize(N.xyz).y));
inside *= smoothstep(2.8, 3.3, abs(P.y));
inside *= step(-.5, RuneMode);
float2 artworkUV = float2(lerp(.30, .70, saturate(uv.x)), saturate(uv.y));
