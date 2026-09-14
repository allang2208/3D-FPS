float2 p=(UV-.5)*2; float a=atan2(p.y,p.x); float r=length(p)/(1+.08*sin(a*7)+.045*cos(a*11)); float edge=1-smoothstep(.60,.94,r); return edge*(.70+.30*(1-smoothstep(.15,.6,r)));
