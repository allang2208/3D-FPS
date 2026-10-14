// Card-local centimetres on a 7.5 x 10.4 cm pooled YZ quad.
// Match SM_DealerCard's 6.3 x 8.8 cm outline and 0.30 cm corner radius.
// UV top-left follows the existing FBX import convention; positive Y rises on screen.
struct DealerRoundedCard
{
    float Distance(float2 p)
    {
        float2 q = abs(p) - float2(2.85, 4.10);
        return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - 0.30;
    }
};
DealerRoundedCard card;
float2 p = float2((UV.x - 0.5) * 7.5, (0.5 - UV.y) * 10.4);
float t = Age;
float sd = card.Distance(p);
float edge = exp(-pow(sd / 0.045, 2.0));
float glow = exp(-abs(sd) * 12.0);
// Each selected card has an independent flame phase. Upward advection makes tongues,
// while the stable hot edge keeps all four rounded corners readable throughout settlement.
float noise = saturate(0.50 + 0.27 * sin(p.x * 19.0 + p.y * 3.5 - t * 8.0 + Seed)
                           + 0.23 * sin(p.x * 33.0 - p.y * 8.0 + t * 13.0 + Seed * 1.73));
float lift = 0.12 + 0.48 * noise * noise;
float drift = 0.035 * sin(p.y * 9.0 - t * 6.0 + Seed);
float plume = exp(-pow(card.Distance(p - float2(drift, lift)) / (0.055 + noise * 0.075), 2.0));
plume *= smoothstep(0.01, 0.06, sd) * (0.18 + 0.82 * noise);
float edgePulse = 0.86 + 0.14 * sin(t * 7.0 + Seed);
float attack = smoothstep(0.0, 0.16, t);
// No panel or rectangular frame: alpha vanishes away from the card contour and tongues.
float margin = (1.0 - smoothstep(3.50, 3.75, abs(p.x)))
             * (1.0 - smoothstep(5.00, 5.20, abs(p.y)));
float coverage = saturate(edge * 0.87 * edgePulse + glow * 0.13 + plume * 0.68)
               * margin * attack * Reveal;
float heat = saturate(edge * 0.92 + plume * noise * 0.25);
float3 color = lerp(float3(2.10, 0.15, 0.012), float3(3.20, 1.25, 0.14), heat);
return float4(color, coverage);
