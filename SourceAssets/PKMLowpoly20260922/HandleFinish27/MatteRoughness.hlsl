// Keep existing source roughness and the protected optical/device region.
// A dry satin coating with subdued handling wear, not polished chrome.
float matte = clamp(max(Base, .50) + .095 + (Detail.g-.5)*.055
                    + Detail.b*.025 + (Detail.a-.5)*.026, .56, .80);
matte -= Detail.r * Strength * .060;
return lerp(Base, matte, Region);
