// Original analytic gold halo. Phase is game time / 1.4 seconds, supplied by the held gun.
float2 p = (UV - 0.5) * 2.0;
float r = length(p);
float pulse = 0.5 - 0.5 * cos(Phase * 6.2831853);
float halo = exp(-r * r * 13.0) * (0.18 + 0.40 * pulse);
float core = exp(-r * r * 100.0) * (0.10 + 0.18 * pulse);
float ringRadius = 0.12 + 0.58 * Phase;
float ring = exp(-pow((r - ringRadius) / 0.045, 2.0)) * pow(1.0 - Phase, 2.0) * 0.20;
float edge = 1.0 - smoothstep(0.65, 0.94, r);
float alpha = saturate((halo + core + ring) * edge * Strength);
// Exposure compensation keeps the pulse golden instead of clipping to white in dark rooms.
float3 gold = float3(1.0, 0.50, 0.035);
return float4(gold * 1.8 / max(Exposure, 0.05), alpha);
