// V4: slit-like OUTLINE, luminous sword-energy surface. No void or torn lips.
// UV.x runs between the pointed tips, UV.y across the thick energy body.
float along = saturate(UV.x);
float across = UV.y * 2.0 - 1.0;
float flow = Age * 2.8;
float drift = .035 * sin(along * 17.0 - flow * 2.4)
            + .014 * sin(along * 41.0 + flow * 1.6);
float lateral = abs(across - drift);
float tips = smoothstep(0.0, .075, along) * (1.0 - smoothstep(.925, 1.0, along));
// Broad feathering on both sides: brightness and density dissolve toward air.
float feather = 1.0 - smoothstep(.26, .98, lateral);
float fill = exp(-pow(lateral * 2.1, 2.0));
float stream = .5 + .5 * sin((across - drift) * 34.0 + along * 5.0 - flow * 4.0);
float ribbons = pow(stream, 7.0);
float fine = pow(.5 + .5 * sin((across - drift) * 83.0 + along * 9.0 - flow * 7.0), 11.0);
float swell = .5 + .5 * sin(along * 15.0 - flow * 2.6);
float spine = exp(-pow(lateral * 11.0, 2.0));
float erosion = smoothstep(Dissolve - .14, Dissolve + .18, .66 + .20 * swell + .12 * stream);

// Filled blue energy, brightest through the middle. Fine lengthwise currents
// read as a cutting wave instead of tracing the two edges of an empty portal.
float3 body = lerp(float3(.018, .15, .78), float3(.28, .62, 1.0), fill * .86);
float3 light = body * (1.25 + fill * .78 + swell * .18 + HitGlow * .24);
light += float3(.16, .43, .85) * (ribbons * .36 + fine * .12) * feather;
light += float3(.35, .62, .85) * spine * .27;
float alpha = feather * (.83 + .10 * fill + .06 * swell);

// Existing rear layer is diffuse energy haze, with no bright closed outline.
float haze = pow(saturate(1.0 - lateral), .8);
float hazeAlpha = feather * haze * (.23 + .08 * swell);
float3 hazeColor = float3(.035, .24, .85) * (.8 + .25 * stream);
float3 color = lerp(light, hazeColor, Layer);
return float4(color / max(Exposure, .035), tips * erosion * lerp(alpha, hazeAlpha, Layer) * Opacity);
