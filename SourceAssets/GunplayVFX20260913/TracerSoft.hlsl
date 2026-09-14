// Project-authored soft current-flight segment. Local cylinder Z runs tail to head.
float along = saturate(LocalPosition.z * 0.01 + 0.5);
float facing = saturate(abs(dot(normalize(NormalWS), normalize(ViewVector))));
float tail = pow(smoothstep(0.0, 0.72, along), 1.25);
float tip = 1.0 - smoothstep(0.86, 1.0, along);
float core = pow(facing, 6.0) * smoothstep(0.25, 0.80, along);
float alpha = tail * tip * pow(facing, 0.85) * Opacity;
float3 color = lerp(Tint.rgb, float3(1.0, 0.92, 0.72), core);
color *= Emission * lerp(0.45, 1.0, core) / max(Exposure, 0.001);
return float4(color, alpha);
