float2 p=(UV-.5)*2; float n=sin(p.x*7+sin(p.y*5))*cos(p.y*6); float r=length(p)+n*.055; return pow(saturate(1-r),1.4)*(.85+.15*n);
