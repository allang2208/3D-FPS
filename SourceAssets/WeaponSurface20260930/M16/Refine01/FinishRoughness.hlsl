float metal=smoothstep(.45,.85,Metal)*saturate(Region);
float luminance=dot(Colour,float3(.2126,.7152,.0722));
float chroma=(max(Colour.r,max(Colour.g,Colour.b))-min(Colour.r,min(Colour.g,Colour.b)))/max(luminance,.015);
float protection=max(smoothstep(.45,.95,chroma),1-smoothstep(.002,.010,luminance));
float fine=(Detail.r-.5)*2.*Grain+(Detail.g-.5)*2.*Variation;
float finish=Center+(Base-Pivot)*SourceWeight+fine;
// Bright source wear retains its authored shape and a slightly smoother
// exposed-metal response, rather than excluding broad steel from the finish.
float wear=smoothstep(.12,.32,luminance);
finish=lerp(finish,min(Base,Center-.035),wear*.70);
return lerp(Base,clamp(finish,.20,.85),metal*(1-protection)*saturate(Strength));
