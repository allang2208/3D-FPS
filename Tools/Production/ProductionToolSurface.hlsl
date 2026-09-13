// Local centimetres keep the grain attached while the tool swings or tumbles.
float3 P = Position;
float3 N = normalize(LocalNormal);
float3 S = step(0.0, N) * 2.0 - 1.0;
float3 W = pow(abs(N), 4.0);
W /= max(dot(W, 1.0), 0.0001);

// The original EBS UV islands identify parts; they are not suitable detail UVs.
float steel = step(0.8, UV.x);
float edge = steel * step(0.91, UV.x);
float grip = (1.0 - steel) * step(0.2, UV.y);
float2 wx = float2(P.y * S.x / 22.0, P.z / WoodLength);
float2 wy = float2(-P.x * S.y / 22.0, P.z / WoodLength);
float2 wz = float2(P.x * S.z, P.y) / 22.0;
float2 mx = float2(P.y * S.x, P.z) / MetalSize;
float2 my = float2(-P.x * S.y, P.z) / MetalSize;
float2 mz = float2(P.x * S.z, P.y) / MetalSize;

float3 wood = Texture2DSample(WoodColor, WoodColorSampler, wx).rgb * W.x
            + Texture2DSample(WoodColor, WoodColorSampler, wy).rgb * W.y
            + Texture2DSample(WoodColor, WoodColorSampler, wz).rgb * W.z;
float3 metal = Texture2DSample(MetalColor, MetalColorSampler, mx).rgb * W.x
             + Texture2DSample(MetalColor, MetalColorSampler, my).rgb * W.y
             + Texture2DSample(MetalColor, MetalColorSampler, mz).rgb * W.z;
float woodLuma = dot(wood, float3(0.2126, 0.7152, 0.0722));
float metalLuma = dot(metal, float3(0.2126, 0.7152, 0.0722));
float rust = smoothstep(0.08, 0.28, metal.r - metal.b) * RustAmount * (1.0 - edge * 0.8);
float3 timber = lerp(woodLuma.xxx, wood, 0.78) * WoodTint;
float3 forged = SteelTint * lerp(0.84, 1.16, saturate(metalLuma * 2.5));
forged = lerp(forged, float3(0.23, 0.24, 0.245), edge * 0.8);
forged = lerp(forged, float3(0.125, 0.066, 0.028), rust);
float3 leather = float3(0.041, 0.032, 0.024) * lerp(0.85, 1.2, saturate(metalLuma * 3.0));
Roughness = lerp(clamp(WoodRoughness + (woodLuma - 0.12) * 0.18, 0.58, 0.86),
                 clamp(lerp(0.49, 0.31, edge) + rust * 0.25 + (metalLuma - 0.15) * 0.1, 0.29, 0.76), steel);
Roughness = lerp(Roughness, 0.77, grip);
Metallic = steel * (0.92 - rust * 0.65);

// BC5 textures sampled through texture objects need explicit XY normal decode.
float2 nx = lerp(Texture2DSample(WoodNormal, WoodNormalSampler, wx).rg * 2.0 - 1.0,
                 Texture2DSample(MetalNormal, MetalNormalSampler, mx).rg * 2.0 - 1.0, steel);
float2 ny = lerp(Texture2DSample(WoodNormal, WoodNormalSampler, wy).rg * 2.0 - 1.0,
                 Texture2DSample(MetalNormal, MetalNormalSampler, my).rg * 2.0 - 1.0, steel);
float2 nz = lerp(Texture2DSample(WoodNormal, WoodNormalSampler, wz).rg * 2.0 - 1.0,
                 Texture2DSample(MetalNormal, MetalNormalSampler, mz).rg * 2.0 - 1.0, steel);
float strength = lerp(WoodNormalStrength, MetalNormalStrength, steel) * lerp(1.0, 0.28, grip);
nx *= strength; ny *= strength; nz *= strength;
float3 bx = float3(N.x * sqrt(saturate(1.0 - dot(nx, nx))), N.y + S.x * nx.x, N.z + nx.y);
float3 by = float3(N.x - S.y * ny.x, N.y * sqrt(saturate(1.0 - dot(ny, ny))), N.z + ny.y);
float3 bz = float3(N.x + S.z * nz.x, N.y + nz.y, N.z * sqrt(saturate(1.0 - dot(nz, nz))));
SurfaceNormal = normalize(bx * W.x + by * W.y + bz * W.z);
return lerp(lerp(timber, leather, grip), forged, steel);
