float3 axis = normalize(Axis);
float3 delta = P - Origin;
float along = dot(delta, axis);
float q = along / max(Length, 1.0);
float2 uv = flux.FlowUV(P, Origin, Axis, Age, Seed);
float3 coarse = Texture2DSampleLevel(NoiseTex, NoiseTexSampler, uv, 0).rgb;
float2 detailUV = uv * 2.0 + (coarse.gb - .5) * .24;
float3 detail = Texture2DSampleLevel(NoiseTex, NoiseTexSampler, detailUV, 0).rgb;
float density = coarse.r * .66 + detail.g * .34;
float facing = saturate(abs(dot(normalize(N), normalize(V))));
float angularCoverage = .40 + .60 * pow(facing, .70);
float caps = smoothstep(.65, .90, abs(dot(normalize(N), axis)));
float bodyStart = smoothstep(0, min(.035, 18.0 / max(Length,1)), q);
float bodyEnd = 1.0 - smoothstep(.97, 1.002, q);
// The front sweeps the beam into place in 90 ms, with a bright launch spike.
float front = 1.0 - smoothstep(Age / .09, Age / .09 + .03, q);
// The spear tip dims into its collapsed point instead of ending in a blunt disc.
float tipTaper = 1.0 - .65 * smoothstep(.955, 1.0, q);
float core = (.88 + .12 * coarse.b) * lerp(angularCoverage, 1.0, caps);
float inner = (.32 + .68 * smoothstep(.22, .70, density)) * angularCoverage;
float outer = (.08 + .92 * smoothstep(.30, .72, density)) * angularCoverage;
float mask = Role < .5 ? core : (Role < 1.5 ? inner : outer);
float tips = Role < .5 ? lerp(bodyStart * bodyEnd, .80, caps) : bodyStart * bodyEnd * (1.0 - caps);
return mask * tips * tipTaper * front;
