// An irregular pressure front, with a soft edge and interrupted sectors.
float2 p=(UV-.5)*2;
float r=length(p);
float angle=atan2(p.y,p.x);
float edge=.78+sin(angle*7+Seed*9+Age*2)*.018+sin(angle*13-Seed*6)*.012;
float width=max(.018,fwidth(r)*1.3);
float band=1-smoothstep(width,width+.036,abs(r-edge));
float sectors=smoothstep(-.72,-.12,sin(angle*5+Seed*7));
float border=1-smoothstep(.91,.98,r);
return saturate(band*sectors*border*Alpha);
