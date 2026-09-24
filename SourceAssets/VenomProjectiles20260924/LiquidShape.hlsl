// Local X follows flight. A rounded leading lobe sheds a narrower oscillating tail.
float x=clamp(P.x/50,-1,1);
float front=smoothstep(-.95,.28,x);
float tail=1-front;
float t=Clock*8+Seed*6.283185;
float radial=lerp(.40,1.04,front)*(1+.027*sin(P.x*.10-t));
float3 q=P;
q.x-=tail*tail*18;
q.yz*=radial;
q.y+=sin(t-P.x*.075)*tail*2.1;
q.z+=cos(t*.81-P.x*.09)*tail*1.5;
return q;
