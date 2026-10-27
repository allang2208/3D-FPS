// A compact hot center breaking into a ragged emerald blast edge.
float2 p=(UV-.5)*2;
float r=length(p);
float angle=atan2(p.y,p.x);
float ripple=sin(angle*7+Seed*11)*.045+sin(angle*13-Seed*7+Age*5)*.025;
float body=1-smoothstep(.18,.81,r+ripple);
float rays=pow(saturate(cos(angle*7+Seed*5)),10)*(1-smoothstep(.34,.96,r));
float border=1-smoothstep(.90,.98,r);
return saturate((body*body+rays*.40)*border*Alpha);
