float2 p=(UV-.5)*2;
float border=smoothstep(0,.13,min(min(UV.x,1-UV.x),min(UV.y,1-UV.y)));
if(Mode>.5){
    float radius=length(p);
    float band=exp(-pow((radius-.70)*24,2));
    float gap=.35+.65*smoothstep(-.85,.25,p.x);
    return band*gap*Alpha*border;
}
float bend=.10*sin(UV.x*5+Clock*9);
float trailMask=exp(-pow((p.y-bend)*9,2));
return trailMask*pow(saturate(UV.x),.7)*Alpha*border;
