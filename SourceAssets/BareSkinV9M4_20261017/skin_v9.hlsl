// M4 bare skin V9: everything is baked into the V9 UV0 (colour zones, veins, creases, furrows, pores);
// no triplanar, no packed-coordinate UVs, no wrist switch, so nothing can seam on the old split.
float3 n = NormalSample;
n.xy *= NormalStrength;
n = normalize(float3(n.xy, max(n.z, .05)));
OutColour = saturate(Colour * Tint);
OutRoughness = clamp(Masks.g * RoughnessScale + RoughnessOffset, .2, .85);
OutSpecular = SkinSpecular * lerp(1, Masks.b, CavitySpecular);
OutAO = lerp(1, Masks.r * lerp(1, Masks.b, .5), AOStrength);
OutScatter = saturate(Masks.a * ScatterStrength);
return n;
