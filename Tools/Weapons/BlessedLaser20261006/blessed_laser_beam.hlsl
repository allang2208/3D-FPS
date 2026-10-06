// Stable continuous gold beam with restrained travelling silk highlights.
// Physical distance keeps the flow speed constant as an occluder shortens it.
float DistanceCM = (LocalPosition.z * 0.01 + 0.5) * max(BeamLengthCM, 0.1);
float Angle = atan2(LocalPosition.y, LocalPosition.x);
float Filament = pow(saturate(0.5 + 0.5 * cos(Angle * 3.0 + DistanceCM * 0.012 - FlowTime * 0.65)), 18.0);
float FlowPhase = frac(DistanceCM / 130.0 - FlowTime * 0.9);
float FlowDistance = min(FlowPhase, 1.0 - FlowPhase);
float Flow = exp2(-FlowDistance * FlowDistance * 70.0);
float Silk = Filament * (0.35 + 0.65 * Flow);
float Scope = saturate(ScopeAlpha);
// Authored in exposure-compensated signal units. Keep blue near zero so
// highlights remain amber/gold rather than turning pale white in the tonemapper.
float3 Gold = float3(1.0, 0.32, 0.004);
float3 WarmSilk = float3(1.0, 0.42, 0.009);
float3 Emission = (Gold * 3.0 + WarmSilk * (2.0 * Silk + 0.4 * Flow)) * lerp(1.0, 0.12, Scope);
float Opacity = (0.80 + 0.16 * Silk + 0.025 * Flow) * (1.0 - Scope);
return float4(Emission, Opacity);
