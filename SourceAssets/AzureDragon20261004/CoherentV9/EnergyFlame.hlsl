float f=saturate(Fill);
float t=saturate(Attr.g);
float seed=Attr.b*6.2831853;
float rootZ=Attr.r*60.-24.;
float front=saturate(abs(dot(normalize(Normal),normalize(View))));
// Front-facing flame shells are soft; their genuinely curved sides reveal depth.
float shell=pow(front,1.2);
float hot=.5+.5*sin(Age*(4.8+f*3.)-t*12.+seed);
float filaments=pow(saturate(.5+.5*sin(Age*3.7-t*19.+seed*1.7)),3.);
float rootGate=1.-smoothstep(-20.+f*40.,-18.+f*40.,rootZ);
float crown=smoothstep(23.,25.,rootZ);
rootGate=lerp(rootGate,smoothstep(.86,1.,f),crown);
float alpha=shell*(.10+.20*hot+.08*filaments)*(1.-smoothstep(.73,1.,t));
alpha*=rootGate*smoothstep(.005,.025,f)*(.25+.75*f)*Reveal;
float3 color=lerp(float3(.007,.27,.31),float3(.17,.80,.87),hot*.63+filaments*.22);
color*=.72+.45*f+Pulse*.14+Burst*.42;
return float4(color,saturate(alpha));
