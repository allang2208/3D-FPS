// Seam-free advected density; coordinates are relative to the liquid mesh.
float t=Clock*.72+Seed*6.283185;
float3 q=P*3.5;
q+=float3(sin(q.y*1.1+t*.53),sin(q.z*.9-t*.41),cos(q.x+t*.37))*.28;
float a=sin(q.x*1.7+q.z*.8-t);
float b=sin(q.y*2.1-q.x*.6+t*.67);
float c=cos(q.z*2.3+q.y*.7-t*.83);
float density=saturate(.50+a*b*.26+c*.17);
float bubble=smoothstep(.86,.98,a*b*c);
return float4(cos(q.x*1.7+q.z*.8-t)*b*.12,
              a*cos(q.y*2.1-q.x*.6+t*.67)*.12,density,bubble);
