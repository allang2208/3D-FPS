float3 axis = normalize(Axis);
float3 delta = P - Origin;
float along = dot(delta, axis);
float q = along / max(Length, 1.0);
float3 radial = delta - axis * along;
float3 reference = abs(axis.z) < .95 ? float3(0,0,1) : float3(0,1,0);
float3 side = normalize(cross(reference, axis));
float3 up = cross(axis, side);
float angle = atan2(dot(radial, up), dot(radial, side)) / 6.2831853 + .5;
float coordinate = along / 260.0;
float tick = floor(Age * 22.0);
float lineWidth = clamp(fwidth(angle) * 1.2, .0025, .025);
float strokes = 0;
// Uneven snapped paths and short side branches; no repeated helical rings.
[unroll] for (int i = 0; i < 4; ++i)
{
    float phase = Seed + i * .271;
    float bend = .075 * sin(coordinate * 4.7 + tick * 1.17 + i * 2.1);
    float jagged = .032 * sin(floor(coordinate * 13.0) * 2.73 + tick * .91 + i * 4.13);
    float target = phase + bend + jagged;
    float distanceToStroke = abs(frac(angle - target + .5) - .5);
    float stroke = 1.0 - smoothstep(.004, .004 + lineWidth, distanceToStroke);
    float branchTarget = target + .038 * sin(coordinate * 19.0 + i * 1.7);
    float branchDistance = abs(frac(angle - branchTarget + .5) - .5);
    float branch = (1.0 - smoothstep(.002, .002 + lineWidth, branchDistance))
                 * smoothstep(.5,.8,sin(coordinate * 11.0 + tick * 1.7 + i));
    float sparks = .35 + .65 * smoothstep(-.1,.65,sin(coordinate * 8.0 - Age * 95.0 + i));
    strokes += (stroke + branch * .55) * sparks;
}
float facing = .20 + .80 * saturate(abs(dot(normalize(N), normalize(V))));
float caps = 1.0 - smoothstep(.65,.90,abs(dot(normalize(N),axis)));
float tips = smoothstep(0,.025,q) * (1.0 - smoothstep(.96,1.0,q));
float front = 1.0 - smoothstep(Age/.045,Age/.045+.025,q);
return saturate(strokes) * facing * caps * tips * front;
