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
// Strokes thin toward the spear tip.
float lineWidth = clamp(fwidth(angle) * 1.2, .0025, .025) * lerp(1.3, .55, saturate(q));
float strokes = 0;
// Seven uneven snapped paths with second-tier forks; no repeated helical rings.
[unroll] for (int i = 0; i < 7; ++i)
{
    float phase = Seed + i * .143;
    float bend = .075 * sin(coordinate * 4.7 + tick * 1.17 + i * 2.1);
    float jagged = .032 * sin(floor(coordinate * 13.0) * 2.73 + tick * .91 + i * 4.13);
    float target = phase + bend + jagged;
    float distanceToStroke = abs(frac(angle - target + .5) - .5);
    float stroke = 1.0 - smoothstep(.004, .004 + lineWidth, distanceToStroke);
    float branchTarget = target + .038 * sin(coordinate * 19.0 + i * 1.7);
    float branchDistance = abs(frac(angle - branchTarget + .5) - .5);
    float branch = (1.0 - smoothstep(.002, .002 + lineWidth, branchDistance))
                 * smoothstep(.5,.8,sin(coordinate * 11.0 + tick * 1.7 + i));
    float forkTarget = target + .06 * sin(coordinate * 29.0 - tick * 1.3 + i * 2.9);
    float forkDistance = abs(frac(angle - forkTarget + .5) - .5);
    float fork = (1.0 - smoothstep(.0015, .0015 + lineWidth, forkDistance))
               * smoothstep(.6,.85,sin(coordinate * 17.0 + tick * 2.3 + i * 1.3));
    float sparks = .35 + .65 * smoothstep(-.1,.65,sin(coordinate * 8.0 - Age * 140.0 + i));
    float flicker = .55 + .45 * sin(tick * 9.43 + i * 5.1);
    strokes += (stroke + branch * .55 + fork * .38) * sparks * flicker;
}
float facing = .20 + .80 * saturate(abs(dot(normalize(N), normalize(V))));
float caps = 1.0 - smoothstep(.65,.90,abs(dot(normalize(N),axis)));
float tips = smoothstep(0,.025,q) * (1.0 - smoothstep(.96,1.0,q));
float front = 1.0 - smoothstep(Age/.09,Age/.09+.03,q);
return saturate(strokes) * facing * caps * tips * front;
