float age=saturate(Meta.x),seed=frac(Meta.y);
float2 p=UV*2-1;
float life=smoothstep(0,.12,age)*(1-smoothstep(.42,1,age));
if(Meta.y>1.5)
{
    // Low, soft copper dust. The two intersecting cards have feathered borders.
    float radius=length(p);
    float swirl=sin(p.x*7+sin(p.y*6+seed*9)+age*4)*.5+.5;
    float cloud=exp(-radius*radius*4)*(1-smoothstep(.5,1,radius));
    return float4(float3(.28,.14,.048),cloud*(.4+.6*swirl)*life*.16);
}
float diamond=1-smoothstep(.14,.72,abs(p.x)+abs(p.y)*.72);
float core=exp(-dot(p,p)*19);
float flicker=.78+.22*sin(age*14+seed*18);
float3 color=lerp(float3(.9,.33,.045),float3(1,.83,.36),core);
return float4(color*(2.2+Charge*.35),max(diamond*.65,core)*life*flicker*.62);
