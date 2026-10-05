// Broad advected folds, a wet inner density and a few small bubbles.
float t=Clock*.85+Seed*6.283185;
float3 q=P*3.1;
q+=float3(sin(q.y+t*.7),sin(q.z*.9-t*.5),cos(q.x+t*.4))*.42;
float a=sin(q.x*1.55+q.z*.72-t);
float b=sin(q.y*1.9-q.x*.62+t*.63);
float c=cos(q.z*2.1+q.y*.7-t*.86);
float density=saturate(.48+a*b*.30+c*.18);
float bubble=smoothstep(.88,.98,a*b*c);
return float4(cos(q.x*1.55+q.z*.72-t)*b*.16,
              a*cos(q.y*1.9-q.x*.62+t*.63)*.16,density,bubble);
