// Intact paint is dielectric; only the existing fine scratch mask exposes steel.
float exposed = saturate(Detail.r * Strength * .50);
return lerp(Base, .94 * exposed, Region);
