float3 axis = normalize(Axis);
float3 delta = P - Origin;
float along = dot(delta, axis);
float q = saturate(along / max(Length, 1.0));
float3 radial = delta - axis * along;
float3 radialDirection = radial / max(length(radial), .01);
float2 uv = flux.FlowUV(P, Origin, Axis, Age, Seed);
float3 field = Texture2DSampleLevel(NoiseTex, NoiseTexSampler, uv, 0).rgb;
float envelope = smoothstep(0, .04, q) * (1.0 - smoothstep(.93, 1.0, q));
float strength = Role < .5 ? .045 : (Role < 1.5 ? .16 : .34);
float fold = (field.r - .5) * 2.0 + .22 * sin(along / 38.0 - Age * 42.0 + field.g * 6.2831853);
// Lance silhouette: narrow tail, slight head mass, pointed tip.
float profile = flux.SpearProfile(q);
// Filament arcs intermittently lift off the host surface.
if (Role > 2.5) profile += .25 * max(0.0, sin(floor(uv.y * 3.0) * 7.7 + Age * 22.0));
// Lateral snake sells the electric jag instead of a straight pipe.
float3 refv = abs(axis.z) < .95 ? float3(0,0,1) : float3(0,1,0);
float3 side = normalize(cross(refv, axis));
float3 upv = cross(axis, side);
float snakeAmp = Role < .5 ? .02 : (Role < 1.5 ? .09 : .20);
float snakeA = smoothstep(.02, .30, q) * Radius * snakeAmp;
float3 lateral = (side * (sin(q * 9.0 + Age * 14.0 + field.b * 6.2831853 + Seed)
    + .4 * sin(q * 29.0 - Age * 31.0 + Seed * 2.3))
    + upv * sin(q * 7.0 - Age * 11.0 + field.g * 6.2831853 + Seed * 1.7)) * snakeA;
return radialDirection * Radius * (strength * fold * envelope + profile - 1.0) + lateral;
