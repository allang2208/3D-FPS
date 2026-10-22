// R: sparse hot fractures, G: soft soot coverage, BA: shallow relief normal XY.
float2 p=(UV-.5)*2;
float r=length(p);
float angle=atan2(p.y,p.x);
float edge=1-smoothstep(.72,.98,r+.055*sin(angle*7+Seed*13)+.025*sin(angle*13-Seed*8));
float2 q=p*4.3+float2(Seed*17.1,Seed*9.7);
float2 cell=floor(q), f=frac(q);
float nearest=20,second=20;
for(int y=-1;y<=1;y++) for(int x=-1;x<=1;x++)
{
    float2 id=cell+float2(x,y);
    float2 random=frac(sin(float2(dot(id,float2(127.1,311.7)),dot(id,float2(269.5,183.3))))*43758.5453);
    float2 delta=float2(x,y)+.18+.64*random-f;
    float d=dot(delta,delta);
    if(d<nearest){second=nearest;nearest=d;}else second=min(second,d);
}
float noise=frac(sin(dot(cell,float2(17.13,91.77)))*43758.5453);
float gap=sqrt(second)-sqrt(nearest);
float crack=(1-smoothstep(.012,.050,gap))*smoothstep(.12,.35,r)*(1-smoothstep(.62,.9,r));
crack*=smoothstep(.38,.70,noise)*edge;
float soot=edge*(.48+.25*(1-smoothstep(.15,.85,r))+.10*noise);
// Subtle bowl/rim shading, without moving the gameplay surface.
float bowl=-.22*exp(-r*r*4);
float rim=.10*exp(-pow((r-.62)*8,2))*(.65+.35*sin(angle*5+Seed*9));
float2 grad=p*(bowl+rim)+float2(sin(q.x*8),sin(q.y*7))*.012*edge;
return float4(crack,soot,grad);
