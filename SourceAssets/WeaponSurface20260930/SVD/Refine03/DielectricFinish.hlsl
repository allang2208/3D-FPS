// Preserve original colour and metal mask. Only external, dark, non-rubber
// dielectric areas of the main handguard/stock receive the finer satin range.
float marks = smoothstep(.25,.55,max(Base.r,max(Base.g,Base.b)));
float warm = smoothstep(1.20,1.65,Base.r/max(Base.g,.001));
float rubber = smoothstep(.70,.79,Rough);
float area = saturate(Dielectric)*(1-saturate(Region))*(1-marks)*(1-warm)*(1-rubber)*saturate(Exterior);
float fineRough = clamp(.56+(Rough-.55)*.30,.48,.64);
float dryRough = lerp(Rough,fineRough,area);
return float4(lerp(Base,Finish.rgb,Region),lerp(dryRough,Finish.a,Region));
