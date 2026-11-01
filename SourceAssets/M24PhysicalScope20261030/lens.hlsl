// Screen projection is shared with the firing camera. Geometry alone clips
// this image: no screen-space circular mask or replacement scope housing.
float2 uv = .5 + (ScreenUV - .5) * ScreenToLens.xy;
float3 scene = Texture2DSample(Scene, SceneSampler, saturate(uv)).rgb;
float2 angle = atan((uv - .5) * (2 * CaptureTanHalfFOV)) * 1000;
float pixel = max(max(fwidth(angle.x), fwidth(angle.y)), .001);
float halfWidth = pixel * .425;
float2 a = abs(angle);
float crossDistance = min(a.x, a.y) - halfWidth;
// Slightly heavier posts beyond 22 mrad, retaining a fine centre crosshair.
if (max(a.x, a.y) > 22) crossDistance = min(a.x, a.y) - pixel * 1.125;
float ink = 1 - smoothstep(-pixel * .4, pixel * .4, crossDistance);
float halo = 1 - smoothstep(0, pixel, crossDistance - pixel * .5);
float halfOpacity = smoothstep(4.5, 7, 1 / pixel) * .65;
[unroll] for (int axis = 0; axis < 2; ++axis)
{
    float2 p = axis == 0 ? a : a.yx;
    float tick = floor(p.x * 2 + .5);
    float whole = 1 - step(.5, fmod(tick, 2));
    float major = 1 - step(.5, fmod(tick, 10));
    float length = pixel * (major > .5 ? 4.5 : whole > .5 ? 2.5 : 1.45);
    float distance = max(abs(p.x - tick * .5) - halfWidth, p.y - length);
    float visible = step(1, tick) * step(tick, 40) * (whole > .5 ? 1 : halfOpacity);
    ink = max(ink, (1 - smoothstep(-pixel * .4, pixel * .4, distance)) * visible);
    halo = max(halo, (1 - smoothstep(0, pixel, distance - pixel * .5)) * visible);
}
float2 labelUV = angle / 48 + .5;
float inLabels = step(0, labelUV.x) * step(labelUV.x, 1) * step(0, labelUV.y) * step(labelUV.y, 1);
float2 labels = Texture2DSample(Labels, LabelsSampler, saturate(labelUV)).rg * inLabels;
float labelVisibility = smoothstep(3.5, 5, 1 / pixel);
ink = max(ink, labels.r * labelVisibility);
halo = max(halo, labels.g * labelVisibility);
// Etching, not luminous HUD graphics; a faint bright edge helps on dark targets.
scene *= float3(.975, .99, 1);
scene = lerp(scene, max(scene, float3(.18, .19, .18)), halo * .22);
return lerp(scene, float3(.002, .0025, .0022), ink * .97);
