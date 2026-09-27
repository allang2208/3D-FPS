// The same coverage drives scratch color and exposed-metal response.
float exposed=saturate(Detail.r*Strength*.55);
return lerp(Base,.94*exposed,saturate(Region));
