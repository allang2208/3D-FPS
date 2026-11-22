// UV spans the rear glass. The material supplies the EPhysicalScopeStyle family.
float2 p = 2.0 * (UV - 0.5);
float2 side = float2(p.x < 0.0 ? -1.0 : 1.0, p.y < 0.0 ? -1.0 : 1.0);
float2 dx = ddx(p);
float2 dy = ddy(p);

// Measure strokes in raster pixels, keeping the same fine edge on tilted glass.
struct GlassStrokes
{
    float2 position;
    float2 pixelX;
    float2 pixelY;
    float2 facetShift;

    float2 ToPixels(float2 delta)
    {
        return float2(dot(delta, pixelX), dot(delta, pixelY));
    }

    float2 Segment(float2 a, float2 b)
    {
        float2 v = ToPixels(b - a);
        float2 w = ToPixels(position - a);
        float t = saturate(dot(w, v) / max(dot(v, v), 1.e-8));
        float2 shaded = w - facetShift;
        float ts = saturate(dot(shaded,v) / max(dot(v,v),1.e-8));
        return float2(length(w-t*v),length(shaded-ts*v));
    }
};
float det = dx.x * dy.y - dy.x * dx.y;
float invDet = (det < 0.0 ? -1.0 : 1.0) / max(abs(det), 1.e-12);
GlassStrokes ink;
ink.position = p;
ink.pixelX = float2(dy.y, -dy.x) * invDet;
ink.pixelY = float2(-dx.y, dx.x) * invDet;
// Both flanks belong to the pane. The dark edge turns with the engraving.
float2 faceDiagonal=ink.ToPixels(float2(.70,1.));
ink.facetShift=faceDiagonal/max(length(faceDiagonal),1.e-5)*1.00;

// Radius is measured on the pane. Only line width and the centre mark use pixels.
float r = length(p);
float2 d;
float halfWidth = .52;
float edgeWidth = .64;
float dotRadius = 1.43;
float guideOpacity = 1.;
[branch] if (family == 10 || family == 11) // Clearfield and Farwatch: historic green glass.
{
    float gap = max(.036, 4.3 * max(length(dx), length(dy)));
    float reach = .96;
    d = min(ink.Segment(float2(side.x*gap,0),float2(side.x*reach,0)),
            ink.Segment(float2(0,side.y*gap),float2(0,side.y*reach)));
    if (family == 11)
    {
        float tick = max(.032, 2.0 / max(length(ink.ToPixels(float2(1,0))),1.e-5));
        d = min(d,ink.Segment(float2(-tick,.12),float2(tick,.12)));
        d = min(d,ink.Segment(float2(-tick,.24),float2(tick,.24)));
    }
    halfWidth = .575;
    edgeWidth = .46;
    dotRadius = 1.8;
    guideOpacity = lerp(.95,.48,smoothstep(.22,.78,r));
}
else if (family == 7) // Peakwatch: two shallow mountain shoulders with a green peak point.
{
    d = ink.Segment(float2(side.x*.054,.039),float2(side.x*.20,.14));
    d = min(d,ink.Segment(float2(side.x*.20,.14),float2(side.x*.295,.14)));
    // A single fine witness below the peak echoes the original bow engraving.
    d = min(d,ink.Segment(float2(-.034,.24),float2(.034,.24)));
    halfWidth = lerp(.57,.39,smoothstep(.08,.30,r));
    dotRadius = 1.65;
    guideOpacity = lerp(.92,.52,smoothstep(.09,.34,r));
}
else if (family == 1 || family == 2) // Both original meshes carry four red stadia and a dot.
{
    // The two build_model.py files place the same .30 cm arms at .24 cm.
    // Express those lengths in the runtime rear-plane basis for each fitting.
    float planeRadius = family == 1 ? 1.79 : 1.585;
    float inner = (.24 - .15) / planeRadius;
    float outer = (.24 + .15) / planeRadius;
    d = min(ink.Segment(float2(side.x*inner,0),float2(side.x*outer,0)),
            ink.Segment(float2(0,side.y*inner),float2(0,side.y*outer)));
    halfWidth = .56;
    edgeWidth = .48;
    dotRadius = 1.60;
}
else if (family == 3) // KV design sheet: a clean illuminated crossing.
{
    d = min(ink.Segment(float2(-.43,0),float2(.43,0)),
            ink.Segment(float2(0,-.25),float2(0,.32)));
    d = min(d,ink.Segment(float2(side.x*.26,0),float2(side.x*.26,.039)));
    halfWidth = lerp(.43,.74,smoothstep(.12,.43,r));
}
else if (family == 8) // SVCh fitting: a low T with a clear upper field.
{
    d = ink.Segment(float2(side.x*.107,.058),float2(side.x*.245,.058));
    d = min(d,ink.Segment(float2(0,.085),float2(0,.225)));
    halfWidth = .47;
    edgeWidth = .97;
}
else if (family == 4) // The main PSO tip, one lower reference and the detached side wires.
{
    d = ink.Segment(float2(0,0),float2(side.x*.156,.141));
    d = min(d,ink.Segment(float2(0,.23),float2(side.x*.050,.275)));
    d = min(d,ink.Segment(float2(side.x*.25,0),float2(side.x*.50,0)));
    halfWidth = lerp(.40,.76,smoothstep(.10,.28,r));
    edgeWidth = 1.03;
    guideOpacity = lerp(.97,.64,smoothstep(.14,.28,r));
}
else if (family == 9) // SVD integral glass: a suspended point over a fine side-wire.
{
    d = ink.Segment(float2(side.x*.09,0),float2(side.x*.45,0));
    d = min(d,ink.Segment(float2(0,.092),float2(side.x*.067,.158)));
    halfWidth = lerp(.45,.66,smoothstep(.10,.45,r));
}
else if (family == 5) // DW715 duplex: intersecting fine wires with heavier outer posts.
{
    d = min(ink.Segment(float2(-.74,0),float2(.74,0)),
            ink.Segment(float2(0,-.66),float2(0,.66)));
    halfWidth = lerp(.49,.95,smoothstep(.26,.34,r));
    edgeWidth = .65;
}
else if (family == 6) // Thermal emitter and four short red display corners.
{
    float2 corner = side*float2(.162,.124);
    d = min(ink.Segment(corner,side*float2(.098,.124)),
            ink.Segment(corner,side*float2(.162,.081)));
    halfWidth = .53;
    edgeWidth = 1.33;
    guideOpacity = .92;
}
else // M24 fine wire cross, brightest at the central intersection.
{
    d = min(ink.Segment(float2(-.64,0),float2(.64,0)),ink.Segment(float2(0,-.60),float2(0,.60)));
    d = min(d,ink.Segment(side*float2(.29,0),side*float2(.29,.022)));
    d = min(d,ink.Segment(side*float2(0,.29),side*float2(.022,.29)));
    halfWidth = lerp(.51,.83,smoothstep(.36,.43,r));
    edgeWidth = lerp(.78,.54,smoothstep(.025,.20,r));
    guideOpacity = lerp(1.,.66,smoothstep(.12,.65,r));
}
float2 widths = float2(halfWidth,halfWidth+edgeWidth);
float useFacet = family == 6 ? 0. : smoothstep(.035,.12,r);
d.y = lerp(d.x,d.y,useFacet);
float2 lines = saturate(.5+widths-d)-saturate(.5-widths-d);
lines.x *= guideOpacity;
// The shaded bevel absorbs light. Endpoints transmit more of the view.
float groove = 1.-(1.-lines.y)*(1.-lines.y);
lines.y = max(lines.x,groove*lerp(1.,.84,smoothstep(.39,.76,r)));
if (family == 0 || family == 5) return float4(lines,0.,saturate(r));
float2 dotRadii = float2(dotRadius,dotRadius+(family == 1 || family == 2 ? .65 : 1.48));
float2 centre = saturate(.5+dotRadii-length(ink.ToPixels(p)));
return float4(max(lines,centre),centre.x,saturate(r));
