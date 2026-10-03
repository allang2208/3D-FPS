float2 p=UV;
float ends=smoothstep(0,.10,p.x)*(1-smoothstep(.90,1,p.x));
float height=sin(saturate(p.y)*3.14159265);
float waves=sin(p.x*47+p.y*13-Time*4.1)*.5+.5;
float eddies=sin(p.x*83-p.y*19+Time*2.6)*.5+.5;
// Exact zero at the perimeter, no opaque rectangle or bright outline.
return ends*pow(saturate(height),1.7)*lerp(.42,1,waves*.65+eddies*.35)*saturate(Heat/1.2);
