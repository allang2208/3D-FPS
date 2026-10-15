// Shaft component-local centimetres. Its mount is weapon Z = 82 cm.
// Keep both axes at the same centimetres-per-artwork-pixel scale.
// The complete motif stays upright along the bare shaft, between the end fittings.
uint texWidth, texHeight;
RuneTexture.GetDimensions(texWidth, texHeight);
float artHeight = 37.5;
float shaftStart = -39.5;
float along = P.z - shaftStart;
float2 radial = P.xy - float2(-.088, -.094);
float radius = max(length(radial), .001);
float angle = atan2(radial.x, -radial.y);
// Resonance's wide rings occupy one full wrap. The narrow complete motifs
// use opposite faces, with enough arc length for each at its natural aspect.
float copies = RuneMode < .5 ? 1.0 : 2.0;
float sector = 6.28318530718 / copies;
angle -= sector * floor((angle + .5 * sector) / sector);
float arcCM = angle * radius;
float artWidth = artHeight * float(texWidth) / max(float(texHeight), 1.0);
float2 artworkUV = float2(.5 + arcCM / artWidth, 1.0 - along / artHeight);
float inside = smoothstep(0, .6, along) * (1 - smoothstep(artHeight - .6, artHeight, along));
inside *= smoothstep(0, .07, .5 * sector - abs(angle));
inside *= 1 - smoothstep(.2, .55, abs(normalize(N.xyz).z));
inside *= step(-.5, RuneMode);
artworkUV = saturate(artworkUV);
