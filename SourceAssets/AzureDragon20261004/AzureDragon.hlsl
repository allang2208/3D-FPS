// Original energy surface. The Fab model's shape and surface normals are retained.
float edge = pow(1.0 - saturate(abs(dot(normalize(Normal), normalize(View)))), 3.0);
float wrist = smoothstep(0.0, 0.18, saturate(LocalX));
float band = sin(LocalX * 20.0 - Age * 9.0) * 0.5 + 0.5;
float brightness = 0.55 + edge * 1.4 + band * 0.08;
float3 color = lerp(Body.rgb, Rim.rgb, edge) * brightness;
float alpha = saturate((Opacity + edge * 0.10) * Reveal * wrist);
return float4(color, alpha);
