// Preserve the author's texture. Change the base-steel tone with a continuous
// transfer; never replace it with a flat colour or synthesize new scratches.
float metal=smoothstep(.45,.85,Metal)*saturate(Region);
float luminance=dot(Base,float3(.2126,.7152,.0722));
float chroma=(max(Base.r,max(Base.g,Base.b))-min(Base.r,min(Base.g,Base.b)))/max(luminance,.015);
float colourProtection=smoothstep(.22,.55,chroma);
float cavityProtection=1-smoothstep(.004,.018,luminance);
// Original bright wear is retained. This is a tonal transfer, not a claim to
// recover a semantic paint/decal mask from brightness alone.
float highlightProtection=smoothstep(.085,.22,luminance);
float weight=metal*(1-colourProtection)*(1-cavityProtection)*(1-highlightProtection)*Strength;
return lerp(Base,Base*ToneScale,weight);
