// Keep the established military olive pigment and the box's own atlas shading.
float luminance=dot(Base,float3(.2126,.7152,.0722));
float variation=clamp(luminance/.028,.90,1.10);
float3 paint=float3(.047,.065,.025)*variation*(1+(Detail.g-.5)*.015);
float exposed=saturate(Detail.r*Strength*.55);
float3 finish=lerp(paint,float3(.14,.155,.165),exposed);
return lerp(Base,finish,saturate(Region));
