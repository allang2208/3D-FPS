float2 p=(UV-.5)*2;
p.x+=sin(p.y*6+Variation*18)*.035*(1-Age);
float width=lerp(.38,.24,saturate(Age));
float body=1-smoothstep(.67,1,length(float2(p.x/width,(p.y+.06)/.86)));
float pinch=exp(-pow((p.y-.12)/.11,2))*smoothstep(.24,.68,Age)*.8;
body*=1-pinch;
float bead=1-smoothstep(.64,1,length((p-float2(.04*sin(Variation*21),.57))/float2(.32,.26)));
float2 edge=smoothstep(0,.065,UV)*smoothstep(0,.065,1-UV);
return saturate(max(body,bead)*edge.x*edge.y*Alpha);
