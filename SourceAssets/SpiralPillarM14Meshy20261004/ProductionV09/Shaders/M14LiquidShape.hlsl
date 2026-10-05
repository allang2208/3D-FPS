// Local X follows the shot. Attached lobes and trailing neck; detached droplets
// are emitted by the shared bounded cosmetic pool.
float x=clamp(P.x/50,-1,1);
float front=smoothstep(-.86,.10,x),tail=1-front;
float t=Clock*7.3+Seed*6.283185;
float lobe=.075*sin(P.x*.085+P.y*.042-t)+.045*cos(P.z*.063-P.x*.041+t*.71);
float radial=lerp(.16,1.02,front)*(1+lobe);
float release=1-smoothstep(0,.14,Age);
float3 q=P;
q.x-=tail*tail*(64+release*15);
q.x+=front*2.2*sin(P.y*.055+P.z*.047-t*.8);
q.yz*=radial;
q.y+=tail*(4.1*sin(t-x*2.9)+1.6*sin(t*1.6-x*4.2));
q.z+=tail*(3.0*cos(t*.83-x*3.2)-1.5*tail);
return q;
