// Local engine cylinder: radius 50 cm, Z endpoints -50/+50 before instance scale.
// The end discs must glow too: the shooter mostly sees the tracer along its axis.
float along = saturate(LocalPosition.z * 0.01 + 0.5);
float facing = saturate(abs(dot(normalize(NormalWS), normalize(ViewVector))));
float radial = saturate(length(LocalPosition.xy) * 0.02);
float cap = smoothstep(0.46, 0.495, abs(LocalPosition.z) * 0.01);
float body = smoothstep(0.0, 0.58, along) * (1.0 - smoothstep(0.88, 1.0, along));
float sideAlpha = body * lerp(0.25, 1.0, pow(facing, 0.65)) * (1.0 - cap);
float disc = exp2(-3.0 * radial * radial) * (1.0 - smoothstep(0.70, 1.0, radial));
float endAlpha = cap * disc * lerp(0.75, 1.0, along);
float core = max(pow(facing, 3.0) * body, cap * exp2(-8.0 * radial * radial));
float alpha = saturate(sideAlpha + endAlpha) * Opacity;
float3 color = lerp(Tint.rgb, float3(1.0, 0.94, 0.78), saturate(core));
color *= Emission * lerp(0.70, 1.0, saturate(core)) / max(Exposure, 0.001);
return float4(color, alpha);
