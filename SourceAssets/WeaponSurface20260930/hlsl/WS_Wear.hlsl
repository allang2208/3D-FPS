// Mask: baked per gun (R convex edge, G cavity, B AO, A handling contact).
// Returns (edge wear, edge proximity, cavity, hairline scratch), all 0..1.
float edge=saturate(Mask.r);
float noise=saturate(Grain.r*.55+Grain.g*.45);
float value=edge*lerp(1.,.25+1.5*noise,saturate(EdgeBreakup));
float wear=saturate((value-(1.-saturate(EdgeWear)))*EdgeContrast)*step(.001,EdgeWear);
float scratch=saturate(Grain.b*ScratchAmount*(1.-Mask.g));
return float4(wear,edge,saturate(Mask.g),scratch);
