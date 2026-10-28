float2 p=(UV-.5)*2;
float a=Variation*6.283185;
float2 q=float2(p.x*cos(a)-p.y*sin(a),p.x*sin(a)+p.y*cos(a));
float lump=.55+.20*sin(q.x*8+sin(q.y*6+a))+.14*sin(q.y*13-q.x*7+a);
float rim=1-smoothstep(.30,.95,length(p));
float pores=.68+.32*sin(q.x*28+sin(q.y*24))*sin(q.y*31+a);
float2 edge=smoothstep(0,.07,UV)*smoothstep(0,.07,1-UV);
return saturate(rim*lump*pores*edge.x*edge.y*Alpha);
