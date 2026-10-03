// Original bounded smoke integration. No third-party shader code or assets.
// Post-process WorldPosition is reconstructed from opaque scene depth.
float3 pixelDelta = PixelPos - CameraOrigin;
float rayDistance = length(pixelDelta);
float3 direction = pixelDelta / max(.001, rayDistance);
float4 spheres[4] = {MistSphere0, MistSphere1, MistSphere2, MistSphere3};
float opticalDepth = 0;
[unroll] for (int i = 0; i < 4; ++i)
{
    float radius = spheres[i].w;
    if (radius <= 1) continue;
    float3 offset = CameraOrigin - spheres[i].xyz;
    float b = dot(offset, direction);
    float discriminant = b * b - dot(offset, offset) + radius * radius;
    if (discriminant <= 0) continue;
    float root = sqrt(discriminant);
    float enter = max(0, -b - root);
    float leave = min(rayDistance, -b + root);
    if (leave <= enter) continue;
    float densitySum = 0;
    [unroll] for (int j = 0; j < 3; ++j)
    {
        float travel = lerp(enter, leave, (j + .5) / 3.);
        float3 point = CameraOrigin + direction * travel;
        float3 local = (point - spheres[i].xyz) / radius;
        float radial = saturate(1 - dot(local, local));
        float n0 = Texture2DSampleLevel(NoiseTex, NoiseTexSampler,
            point.xy * .0045 + float2(Time * .022, -Time * .015), 1).r;
        float n1 = Texture2DSampleLevel(NoiseTex, NoiseTexSampler,
            point.yz * .0037 + float2(-Time * .011, Time * .018), 1).r;
        densitySum += radial * (.55 + .6 * n0 + .4 * n1);
    }
    opticalDepth += (leave - enter) * densitySum / 3. * .045;
}
float transmittance = exp(-min(20, opticalDepth));
float3 soot = float3(.0015, .0013, .0018);
float3 fogged = lerp(soot, SceneColor.rgb, transmittance);
float shortSight = smoothstep(80, 250, rayDistance) * saturate(BlindStrength);
return lerp(fogged, soot, shortSight);
