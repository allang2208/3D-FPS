// Finish layer from the surface card, then cavity, handling, scratches and edge wear.
// Returns (base colour linear, roughness).
float3 base=lerp(Finish,Src,saturate(SrcW));
base*=1.+(Grain.g-.5)*2.*MottleC;
base*=1.-Wear.z*CavDark;
float r=Rough+(SrcR-Pivot)*SrcRW;
r+=(Grain.r-.5)*2.*GrainR+(Grain.g-.5)*2.*MottleR;
r+=(Grain.a-.375)*Stipple;
r+=Wear.z*CavRough;
r-=Wear.y*EdgeHL;
r-=Mask.a*Handling*(.75+.5*(Grain.g-.5));
base=lerp(base,lerp(base,EdgeColor,.35),Wear.w);
r-=Wear.w*.16;
base=lerp(base,EdgeColor,Wear.x);
r=lerp(r,EdgeRough,Wear.x);
return float4(max(base,0.),clamp(r,.05,1.));
