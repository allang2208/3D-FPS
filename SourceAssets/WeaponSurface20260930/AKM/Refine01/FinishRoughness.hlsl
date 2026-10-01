float metal=smoothstep(.45,.85,Metal)*saturate(Region);
float luminance=dot(Colour,float3(.2126,.7152,.0722));
float chroma=(max(Colour.r,max(Colour.g,Colour.b))-min(Colour.r,min(Colour.g,Colour.b)))/max(luminance,.015);
float protection=max(smoothstep(.22,.55,chroma),max(1-smoothstep(.004,.018,luminance),smoothstep(.085,.22,luminance)));
float fine=(Detail.r-.5)*2.*Grain+(Detail.g-.5)*2.*Variation;
// Keep original roughness variation and localized polished/scratched regions.
float finish=Center+(Base-Pivot)*SourceWeight+fine;
return lerp(Base,clamp(finish,.20,.85),metal*(1-protection)*Strength);
