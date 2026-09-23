// Preserve paint identity, markings, original texture and all separate optics.
float marks = 1-smoothstep(.42,.72,dot(Base,float3(.2126,.7152,.0722)));
float wear = Detail.r*Strength*marks;
float3 coating = Base*(.975+.025*Detail.g)*(1-.025*Detail.b);
float3 scuffed = coating + wear*float3(.030,.033,.035);
return lerp(Base, scuffed, Region);
