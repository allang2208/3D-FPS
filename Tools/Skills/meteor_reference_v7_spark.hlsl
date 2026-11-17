float2 p=abs(UV-.5)*2;
float tip=pow(saturate(1-p.y),.52);
float width=lerp(.08,.70,tip);
float streak=(1-smoothstep(width*.16,width,p.x))*tip;
float core=exp(-dot((UV-.5)*float2(8,5),(UV-.5)*float2(8,5)))*.24;
float needle=saturate(streak+core)*(1-smoothstep(.87,1,p.y));
float chip=1-smoothstep(.12,.68,length((UV-.5)*float2(2,2.2)));
return lerp(needle,chip,saturate(Dynamic.w));
