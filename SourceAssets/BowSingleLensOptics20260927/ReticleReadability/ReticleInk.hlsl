// Pane-relative engraving with a stable centre light and subdued, transmissive guides.
struct GlassInk
{
    float3 Shade(float4 etch, float style, float4 draw, float release)
    {
        int family = (int)round(style);
        float3 centreLight, guide;
        float3 rim = float3(.012,.014,.014);
        if (family == 7 || family == 10 || family == 11)
        {
            // Original fixed-bow illuminant and its independent 2.4x centre gain.
            float3 green = float3(.035,.36,.055);
            centreLight = green * (family == 7 ? 2.32 : 2.4);
            guide = green * lerp(1.,.16,smoothstep(.22,.78,etch.w));
            rim = float3(.006,.016,.008);
            if (family == 7)
            {
                float tension = saturate(dot(draw,float4(.14,.23,.63,.65))+.30*release);
                guide = lerp(guide,float3(.18,.52,.20),tension);
            }
        }
        else if (family == 6)
        {
            centreLight = float3(1.38,.028,.018);
            guide = float3(.67,.024,.017);
            rim = float3(.017,.006,.006);
        }
        else if (family == 0)
        {
            centreLight = float3(1.30,1.37,1.40);
            guide = lerp(centreLight,float3(.23,.25,.255),smoothstep(.038,.48,etch.w));
        }
        else if (family == 1 || family == 2)
        {
            centreLight = float3(1.55,.020,.012);
            guide = float3(1.22,.014,.009) * lerp(1.,.77,smoothstep(.12,.218,etch.w));
            rim = float3(.041,.006,.005);
        }
        else if (family == 3)
        {
            centreLight = float3(.82,1.07,1.17);
            guide = float3(.32,.43,.46);
        }
        else if (family == 8)
        {
            centreLight = float3(.66,1.0,.84);
            guide = float3(.27,.40,.33);
        }
        else if (family == 4)
        {
            centreLight = float3(1.00,.105,.046);
            guide = float3(.49,.122,.068);
        }
        else if (family == 9)
        {
            centreLight = float3(.98,.51,.18);
            guide = float3(.37,.26,.15);
        }
        else // DW715
        {
            centreLight = float3(1.02,1.00,.94);
            guide = lerp(centreLight,float3(.27,.26,.24),smoothstep(.04,.34,etch.w));
        }
        return centreLight*etch.z + guide*(etch.x-etch.z) + rim*(etch.y-etch.x);
    }
};
GlassInk glassInk;
