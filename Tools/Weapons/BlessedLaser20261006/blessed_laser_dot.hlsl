// The inherited opacity graph retains post-temporal coverage and depth occlusion.
float Glow = 1.0 + 0.035 * sin(FlowTime * 2.4);
return float3(5.2, 1.664, 0.0208) * Glow * lerp(1.0, 0.10, saturate(ScopeAlpha));
