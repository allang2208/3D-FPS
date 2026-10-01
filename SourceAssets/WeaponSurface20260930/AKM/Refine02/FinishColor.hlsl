// Preserve authored marks and wear while bringing the broad steel finish to
// the project satin family. Compress source tonal variation around its original
// steel reference; do not darken the reference repeatedly between revisions.
float metal=smoothstep(.45,.85,Metal)*saturate(Region);
float luminance=dot(Base,float3(.2126,.7152,.0722));
float chroma=(max(Base.r,max(Base.g,Base.b))-min(Base.r,min(Base.g,Base.b)))/max(luminance,.015);
float colourProtection=smoothstep(.45,.95,chroma);
float cavityProtection=1-smoothstep(.002,.010,luminance);
float wearProtection=smoothstep(.12,.32,luminance);
float weight=metal*(1-colourProtection)*(1-cavityProtection)*(1-wearProtection)*saturate(Strength);
float3 finish=.058*ToneScale*pow(max(Base,float3(.0001,.0001,.0001))/.058,SourceContrast);
return lerp(Base,finish,weight);
