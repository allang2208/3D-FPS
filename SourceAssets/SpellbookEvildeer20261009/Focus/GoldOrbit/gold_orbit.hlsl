// UV rows 0..1: two travelling ribbons. Rows 2..3: sixteen small spark quads.
float band = floor((UV.x + 0.001) * 0.5);
float u = UV.x - band * 2.0;
float energy;
if (UV.y > 1.5)
{
    float2 p = float2(u, UV.y - 2.0) * 2.0 - 1.0;
    float core = exp(-dot(p,p)*14.0);
    float star = exp(-abs(p.x*p.y)*75.0) * pow(saturate(1.0-length(p)),3.0);
    float blink = pow(saturate(0.5+0.5*sin(GoldAge*(2.2+frac(band*.31))+band*2.39996)),5.0);
    energy = (core+star*.7)*blink*2.0;
}
else
{
    float direction = band < 0.5 ? 1.0 : -1.0;
    float travel = frac(u-GoldAge*.17*direction+band*.37);
    float head = min(travel,1.0-travel);
    float flow = exp(-head*head*1400.0)*1.5 + exp(-travel*11.0)*.55;
    float edge = pow(saturate(1.0-abs(UV.y*2.0-1.0)),2.0);
    energy = edge*(.025+flow);
}
return float3(1.0,.56,.09)*energy*Fade*(3.5+2.0*PageActivity);
