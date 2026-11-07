// Gold oath in blade-local centimetres. Preserve the portrait crest's native
// 2:3 aspect; only the connecting filigree spans the selected blade's length.
float3 axis = normalize(BladeAxis.xyz);
float3 side = normalize(cross(float3(0,1,0), axis));
float3 depth = cross(axis, side);
float3 local = P.xyz - BladeOrigin.xyz;
float x = dot(local, side);
float z = dot(local, axis) - Dimensions.y;
float span = max(Dimensions.z, 1.0);
float t = z / span;
float coverage = smoothstep(0.0, .016, t) * (1.0-smoothstep(.978, 1.0, t));
coverage *= smoothstep(.07, .38, abs(dot(normalize(N.xyz), depth))) * step(10.5, RuneMode);
float width = max(Dimensions.x, 1.0);
float aa = clamp(.55 * max(fwidth(x), fwidth(z)), .028, .24);

// The central crest and the circular seals all have the same physical scale
// in X and Z. Reserve the intervals between them for the tapering gold wires.
float crestWidth = width * .78;
float2 crestUV = float2(.5 + x/crestWidth, .5 - (z - span*.19)/(1.5*crestWidth));
float crest = Texture2DSample(RuneTexture, RuneTextureSampler, saturate(crestUV)).r;
crest = smoothstep(.055, .56, crest);
float halfRail = width * lerp(.18, .028, saturate(t));
halfRail *= smoothstep(0., .075, t) * (1.-smoothstep(.88, 1., t));
float interlace = abs(cos(3.14159265 * (t-.19)/.275));
float railD = abs(abs(x) - halfRail * interlace);
float stroke = width * lerp(.028, .016, saturate(t));
float rail = 1.-smoothstep(max(0.,stroke-aa), stroke+aa, railD);
float ink = crest;
float bridge = 1.;
float lit = 0.;
[unroll] for (int i=0; i<3; ++i)
{
    float center = .19 + i*.275;
    float2 q = float2(x, z - center*span);
    float radius = width*(.45 - .055*i);
    float ringD = abs(length(q) - radius);
    float ring = 1.-smoothstep(max(0.,stroke-aa), stroke+aa, ringD);
    // An open notch closes as its own seal charges. The idle strokes stay gold.
    float sealCharge = smoothstep(i/3., (i+1.)/3., OathCharge);
    float notch = smoothstep(.78,.94,q.x/max(.01,length(q)));
    ring *= 1.-notch*(1.-max(sealCharge,OathRelease));
    float diamondD = abs(abs(q.x)+abs(q.y)*.68-radius*.77)*.827;
    float diamond = (1.-smoothstep(max(0.,stroke-aa),stroke+aa,diamondD))*step(1.,float(i));
    ink = max(ink,max(ring,diamond));
    bridge *= smoothstep(radius*.93,radius+stroke+aa,length(q));
    lit = max(lit, (1.-smoothstep(radius, radius*1.65, length(q))) * sealCharge);
}
ink = max(ink,rail*bridge);
float opacity = saturate(ink*coverage);
float flash = saturate(max(OathReady,OathRelease));
float3 amber = float3(.86,.32,.035);
float3 gold = float3(1.65,.86,.20);
float3 color = lerp(amber,gold,.45+.52*ink) * (1.+lit*.52+flash*.88);
return float4(color, opacity*.96);
