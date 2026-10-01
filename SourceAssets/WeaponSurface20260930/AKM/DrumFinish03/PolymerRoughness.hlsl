float luma=dot(Colour,float3(.2126,.7152,.0722));
float chroma=(max(Colour.r,max(Colour.g,Colour.b))-min(Colour.r,min(Colour.g,Colour.b)))/max(luma,.015);
float shell=(1-smoothstep(.10,.60,Metal))*smoothstep(.006,.010,luma);
shell*=1-smoothstep(.06,.16,luma);
shell*=1-smoothstep(.45,.95,chroma);
float finish=clamp(Center+(Base-.56)*SourceWeight,.32,.55);
return lerp(Base,finish,shell*saturate(Strength));
