// Centimetres. A contained basin reuses Clearwater optics, with capillary-scale waves.
float2 p=(UV-.5)*42;
float edge=1-smoothstep(17.5,21,length(p));
float h=0;float2 slope=0;
for(int i=0;i<6;i++)
{
    float angle=.73+i*2.39996;
    float2 dir=float2(cos(angle),sin(angle));
    float k=.24+i*.17, a=.032/(1+i*.45);
    float phase=dot(p,dir)*k-Clock*sqrt(981*k)+i*1.87;
    h+=sin(phase)*a;slope+=cos(phase)*a*k*dir;
}
float age=Clock-QuenchTime;
float2 delta=p-Hit.xy;
float r=length(delta);float2 dir=delta/max(r,.05);
float active=step(0,age)*step(age,7);
float envelope=active*exp(-max(age,0)*.70)*exp(-pow((r-max(age,0)*13)/5.5,2));
float phase=r*1.45-age*19;
h+=sin(phase)*.42*envelope;
slope+=dir*cos(phase)*.42*1.45*envelope;
float boil=Immersion*exp(-r*r/45)*exp(-max(age,0)*.6);
h+=sin(r*2.1-Clock*24)*.075*boil;
slope+=dir*cos(r*2.1-Clock*24)*.16*boil;
return float3(h*edge,slope*edge);
