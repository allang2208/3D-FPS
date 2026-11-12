// Two staggered, jittered drop fields. Rings end inside their cells, so the
// cheap two-sample field has no clipped rings at a cell seam. World cm/seconds.
float fade=1-smoothstep(2600,6500,distance(P,Camera));
if(Rain<=.005 || fade<=0) return float3(0,0,0);
float2 gradient=0;
[unroll] for(int i=0;i<2;i++)
{
    float size=clamp(Spacing,20.,120.)*(i==0?1.:.68);
    float2 uv=P.xy/size+float2(i*13.27,i*7.83);
    float2 id=floor(uv);
    float3 h=frac(sin(float3(dot(id,float2(127.1,311.7)),dot(id,float2(269.5,183.3)),dot(id,float2(419.2,371.9))))*43758.5453);
    float age=frac(Clock*(1.05+i*.18)+h.z);
    float2 delta=frac(uv)-(.38+.24*h.xy);
    float dist=length(delta);float radius=.015+age*.24;
    float width=max(.018,length(fwidth(uv))*.6);
    float band=(dist-radius)/width;
    float envelope=smoothstep(0,.06,age)*(1-smoothstep(.48,.82,age));
    float active=step(h.x,saturate(Rain)*.85+.08);
    float ring=sin(band*2.3)*exp(-band*band)*envelope*active;
    gradient+=delta/max(dist,.001)*ring;
}
return float3(gradient*(.10+.12*saturate(Rain))*fade,0);
