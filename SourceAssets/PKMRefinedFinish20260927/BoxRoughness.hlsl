// Olive enamel stays dielectric, with a restrained satin reflection.
float structure=clamp((Base-.40)*.13,-.025,.025);
float enamel=clamp(Center+structure+(Detail.g-.5)*.018
                   -Detail.r*Strength*.060,.36,.49);
return lerp(Base,enamel,saturate(Region));
