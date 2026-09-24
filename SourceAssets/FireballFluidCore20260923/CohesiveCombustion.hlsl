// The existing persistent core owns the silhouette. Combustion fields supply
// rolling heat and soft soot pockets without dissolving the center of the orb.
float2 p = (UV - 0.5) * 2.0;
float r = length(p);
float flame = saturate(Combustion.r);
float temperature = saturate(Combustion.g);
float soot = saturate(Combustion.b);
float turbulence = saturate(flame * 0.62 + N1 * 0.23 + N2 * 0.15);
float edgeRadius = r + 0.070 * (N1 - 0.5) + 0.030 * (N2 - 0.5)
                    + 0.025 * (0.5 - flame);
float edge = 1.0 - smoothstep(0.64, 0.97, edgeRadius);
float thickness = sqrt(saturate(1.0 - r * r));
float heat = saturate(0.13 + 0.28 * thickness + 0.40 * flame
                      + 0.19 * temperature + 0.10 * N2);
float3 ember = float3(1.0, 0.060, 0.002);
float3 orange = float3(1.0, 0.250, 0.012);
float3 hot = float3(1.0, 0.640, 0.100);
float3 rgb = lerp(ember, orange, smoothstep(0.20, 0.62, heat));
rgb = lerp(rgb, hot, smoothstep(0.66, 0.99, heat));
float warmPocket = 1.0 - 0.23 * soot * (1.0 - flame);
return float4(rgb * (0.74 + 0.26 * thickness) * warmPocket,
              edge * (0.82 + 0.12 * turbulence));
