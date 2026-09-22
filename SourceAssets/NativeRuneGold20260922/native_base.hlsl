// The original ink's UV0 coverage, not a new projected glyph pattern.
float amount = saturate(Mask.r * GoldAmount);
float detail = .60 + .40 * saturate(dot(SourceBase, float3(.2126, .7152, .0722)) / .75);
return lerp(SourceBase, GoldColor * detail, amount);
