// Local engine cylinder: radius 50 cm, Z endpoints -50/+50 before instance scale.
// V13 = the V12 visibility rules (axial end glow plus side falloff, both caps lit)
// with a head-to-tail taper for the persistent streak. Same parameter names as V12
// (Tint / Emission / Opacity / Exposure), so no parameter rewiring is required.
// local +Z points from the tail towards the round (see ApplyTracerTransform).
float along = saturate(LocalPosition.z * 0.01 + 0.5);        // 0 = tail, 1 = round end
float facing = saturate(abs(dot(normalize(NormalWS), normalize(ViewVector))));
float radial = saturate(length(LocalPosition.xy) * 0.02);
float cap = smoothstep(0.46, 0.495, abs(LocalPosition.z) * 0.01);
float taper = smoothstep(0.03, 0.62, along);                 // fade the tail away
float head = smoothstep(0.55, 1.0, along);                   // keep the head bright
float body = taper * lerp(0.74, 1.0, head);
float sideAlpha = body * lerp(0.22, 1.0, pow(facing, 0.65)) * (1.0 - cap);
float disc = exp2(-3.0 * radial * radial) * (1.0 - smoothstep(0.70, 1.0, radial));
float endAlpha = cap * disc * lerp(0.55, 1.0, along);
float core = max(pow(facing, 3.0) * body, cap * exp2(-8.0 * radial * radial) * lerp(0.60, 1.0, along));
float alpha = saturate(sideAlpha + endAlpha) * Opacity;
float3 warm = lerp(Tint.rgb * 0.85, Tint.rgb, along);         // tail reads slightly cooler/darker
float3 color = lerp(warm, float3(1.0, 0.95, 0.80), saturate(core));
color *= Emission * lerp(0.66, 1.0, saturate(core)) / max(Exposure, 0.001);
return float4(color, alpha);