float2 p=(UV-.5)*2;
// A tapered droplet with a denser curved edge and one small glint.
p.x*=1+.18*p.y;
float r=length(p);
float aa=max(fwidth(r),.025);
float body=1-smoothstep(.65-aa,.96+aa,r);
float rim=exp(-pow((r-.67)/.17,2));
float glint=exp(-dot(p-float2(-.25,.23),p-float2(-.25,.23))*24);
return saturate(body*(.74+.18*rim+.08*glint)*Alpha);
