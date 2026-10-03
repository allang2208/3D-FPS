struct ThunderFluxCoordinates
{
    float2 FlowUV(float3 positionWS, float3 originWS, float3 axisWS, float age, float seed)
    {
        float3 axis = normalize(axisWS);
        float3 delta = positionWS - originWS;
        float along = dot(delta, axis);
        float3 radial = delta - axis * along;
        float3 reference = abs(axis.z) < .95 ? float3(0,0,1) : float3(0,1,0);
        float3 side = normalize(cross(reference, axis));
        float3 up = cross(axis, side);
        float angle = atan2(dot(radial, up), dot(radial, side)) / 6.2831853 + .5;
        // Positive axial motion goes from staff to impact. Angular drift rolls
        // the folds, while integer angular tiling retains a seamless circumference.
        return float2(along / 320.0 - age * 12.0 + seed,
                      angle * 2.0 + age * .45 + .10 * sin(along / 170.0 - age * 7.0) + seed * .37);
    }
    // Lance silhouette along the beam: narrow tail, slight head mass, pointed tip.
    float SpearProfile(float q)
    {
        float p = lerp(.55, 1.0, smoothstep(0.0, .16, q));
        p *= 1.0 + .30 * exp(-pow((q - .88) / .055, 2.0));
        p *= 1.0 - .90 * smoothstep(.95, 1.0, q);
        return p;
    }
};
ThunderFluxCoordinates flux;
