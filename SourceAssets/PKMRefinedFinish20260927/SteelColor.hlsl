// Neutral dark gun steel. Preserve markings and source part-level contrast.
float luminance=dot(Base,float3(.2126,.7152,.0722));
float markings=smoothstep(.32,.66,max(Base.r,max(Base.g,Base.b)));
float region=saturate(Region)*smoothstep(.20,.60,Metal)*(1-markings);
float shading=clamp(luminance/.034,.72,1.30);
float3 coating=lerp(Base,Tint*shading,ColorWeight)*(1+(Detail.g-.5)*.018);
float wear=Detail.r*Strength;
return lerp(Base,coating+wear*float3(.020,.022,.024),region);
