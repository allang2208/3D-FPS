// Restore the original PKM box's linear olive pigment. The existing atlas still
// supplies subtle surface variation; structural normal and AO stay untouched.
float luminance = dot(Base, float3(.2126, .7152, .0722));
float variation = clamp(luminance / .028, .85, 1.12);
float3 paint = float3(.047, .065, .025) * variation;
float3 coating = paint * (.975 + .025 * Detail.g) * (1 - .025 * Detail.b);
float wear = saturate(Detail.r * Strength);
return lerp(Base, coating + wear * float3(.030, .033, .035), Region);
