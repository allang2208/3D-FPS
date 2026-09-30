// Same wet film response as the HK416 materials: slight darkening, smoother film, beads.
float r=lerp(lerp(CR.a,max(.085,CR.a*.70),Data.a),.065,Data.b*.8);
return float4(CR.rgb*(1.-Data.a*.07),r);
