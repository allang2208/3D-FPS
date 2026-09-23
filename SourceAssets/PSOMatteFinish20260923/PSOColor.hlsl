// Keep host-specific pigment, source lettering and the complete structural map.
float3 original = Base;
float marks = 1-smoothstep(.42,.72,dot(Base,float3(.2126,.7152,.0722)));
float3 pigment = lerp(Base, __TINT__, __TINT_WEIGHT__);
float wear = Detail.r*Strength*marks;
float3 coating = pigment*(.982+.018*Detail.g)*(1-.018*Detail.b);
float3 scuffed = coating + wear*float3(.024,.026,.028);
return lerp(original, scuffed, Region);
