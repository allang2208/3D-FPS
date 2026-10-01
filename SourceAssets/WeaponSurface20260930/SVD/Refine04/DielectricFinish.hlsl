// Continue the R03 material identity mask. Fine grain is evaluated in the same
// pre-skinned centimetres as the metal finish, before the one wetness layer.
float marks = smoothstep(.25,.55,max(Base.r,max(Base.g,Base.b)));
float warm = smoothstep(1.20,1.65,Base.r/max(Base.g,.001));
float rubber = smoothstep(.70,.79,Rough);
float area = saturate(Dielectric)*(1-saturate(Region))*(1-marks)*(1-warm)*(1-rubber)*saturate(Exterior);

// Keep most source colour variation and its hue; compress only the dark
// furniture's residual cloudy contrast. The original atlas is never rewritten.
float lum = dot(Base,float3(.2126,.7152,.0722));
float cleanLum = clamp(.021+(lum-.021)*.5,.014,.040);
float3 cleanBase = Base * cleanLum/max(lum,.001);
float3 dryBase = lerp(Base,cleanBase,area*saturate(ColorCleanup));
float fineRough = clamp(PolymerRough+(Rough-.55)*.22+(Grain.a-.375)*2.*PolymerGrain,.46,.64);
float dryRough = lerp(Rough,fineRough,area);
return float4(lerp(dryBase,Finish.rgb,Region),lerp(dryRough,Finish.a,Region));
