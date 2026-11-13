// U wraps once around the impact. V is the distance from centre / wave radius.
const float angle = UV.x * 6.2831853;
const float radius = UV.y;
const float life = saturate(Fade);
const float age = 1.0 - life;
const float lobes = sin(7.0 * angle + 0.65 * sin(3.0 * angle));
const float folds = sin(16.0 * angle - 1.7 * age + 1.4 * lobes);
const float leadingEdge = 0.966 + 0.008 * lobes + 0.006 * folds;
const float behind = leadingEdge - radius;
const float aa = clamp(fwidth(radius), 0.001, 0.014);

// A narrow pale crest shows the leading edge even when the dust breaks apart.
const float crest = smoothstep(-0.013-aa, -0.002, behind)
                  * (1.0 - smoothstep(0.002, 0.032+aa, behind));
const float lee = smoothstep(0.008, 0.040, behind)
                * (1.0 - smoothstep(0.047, 0.106, behind));
const float billow = sin(23.0 * angle + 16.0 * behind - 3.0 * age + 1.6 * folds);
const float grains = sin(53.0 * angle - 48.0 * behind + 2.1 * billow);
const float wakeWidth = 0.19 + 0.040 * lobes + 0.032 * billow;
const float dust = smoothstep(0.036, 0.088, behind)
                 * (1.0 - smoothstep(wakeWidth-0.05, wakeWidth+0.04, behind))
                 * smoothstep(-0.65 + 0.55 * age, 0.58, 0.60 * folds + 0.45 * billow + 0.18 * grains);
const float crestWeight = crest * (0.83 + 0.11 * folds);
const float leeWeight = lee * 0.49;
const float dustWeight = dust * 0.47;
const float fadeOut = smoothstep(0.0, 0.32, life);
const float3 light = float3(0.74,0.67,0.53) * crestWeight
                   + float3(0.095,0.079,0.061) * leeWeight
                   + float3(0.40,0.32,0.23) * dustWeight;
return float4(light * fadeOut, saturate(crestWeight + leeWeight + dustWeight) * fadeOut);
