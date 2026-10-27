// A thicker, mostly connected front; keep the V2 ground-impact ring separate.
float2 p=(UV-.5)*2;
float r=length(p);
float angle=atan2(p.y,p.x);
float edge=.83+sin(angle*7+Seed*9+Age*2)*.019+sin(angle*13-Seed*6)*.012;
float width=max(.032,fwidth(r)*1.4);
float band=1-smoothstep(width,width+.046,abs(r-edge));
float halo=(1-smoothstep(.05,.15,abs(r-edge)))*.18;
float sectors=.55+.45*smoothstep(-.72,.05,sin(angle*5+Seed*7));
float border=1-smoothstep(.94,.99,r);
return saturate((band+halo)*sectors*border*Alpha);
