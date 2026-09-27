// Replace the old .56-.80 matte clamp; original source map remains an input.
float region=saturate(Region)*smoothstep(.20,.60,Metal);
float structure=clamp((Base-.40)*.16,-.035,.035);
float satin=clamp(Center+structure+(Detail.g-.5)*.024
                  -Detail.r*Strength*.055,.28,.50);
return lerp(Base,satin,region);
