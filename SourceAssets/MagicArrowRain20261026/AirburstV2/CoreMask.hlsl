// Local burst silhouette. Particle age, not world time, drives the breakup.
float2 p=(UV-.5)*2;
float r=length(p);
float angle=atan2(p.y,p.x);
float ripple=sin(angle*7+Seed*11)*.025+sin(angle*13-Seed*7+Age*4)*.018;
float body=1-smoothstep(.12,.78,r+ripple);
float rays=pow(saturate(cos(angle*6+Seed*5)),14)*(1-smoothstep(.28,.96,r));
float border=1-smoothstep(.90,.98,r);
return saturate((body*body+rays*.25)*border*Alpha);
