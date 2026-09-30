// Coatings stay dielectric; only exposed substrate (edge wear, scratches) turns metallic.
float metal=lerp(Metal,EdgeMetal,saturate(max(Wear.x,Wear.w*.6)));
float ao=lerp(1.,saturate(Mask.b),saturate(AOStrength));
return float4(metal,ao,0,0);
