// Coordinate dark polymer on the drum, grips and stock, separately from steel.
// Retain dark recesses, saturated decoration and bright authored markings.
float luma=dot(Base,float3(.2126,.7152,.0722));
float chroma=(max(Base.r,max(Base.g,Base.b))-min(Base.r,min(Base.g,Base.b)))/max(luma,.015);
float shell=(1-smoothstep(.10,.60,Metal))*smoothstep(.006,.010,luma);
shell*=1-smoothstep(.06,.16,luma);
shell*=1-smoothstep(.45,.95,chroma);
float3 finish=Tint*pow(max(Base/.014,float3(.0001,.0001,.0001)),.35);
return lerp(Base,finish,shell*saturate(Strength));
