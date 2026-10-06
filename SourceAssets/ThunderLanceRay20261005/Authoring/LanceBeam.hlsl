// Thunder Lance beam — derived from M09's crossed soft ribbons, recolored to
// electric blue with a white-hot spine. No solid cylinder, no hard edges.
float across=UV.x*2-1;
float wobble=.10*sin(UV.y*28-Clock*4.5)+.045*sin(UV.y*63+Clock*2.5);
float soft=exp(-5.5*pow(across-wobble,2))*(1-smoothstep(.70,1.,abs(across)));
// Slow internal strands plus a hot spine — luminous plasma, not drawn lines.
float strands=.66+.17*sin(UV.y*46-Clock*9+across*5)+.09*sin(UV.y*91-Clock*12-across*9);
float core=exp(-14.*pow(across-wobble*.6,2));
float tips=smoothstep(0.,.016,UV.y)*(1-smoothstep(.985,1.,UV.y));
float3 tint=lerp(float3(.07,.22,.62),float3(.38,.72,1.0),saturate(.5+.5*sin(UV.y*13-Clock*1.6+across)));
float3 coreTint=float3(.82,.95,1.0);
float glow=1.8+FirePower*1.6;
// Warning profile kept for the discharge decay phase: as FirePower eases to
// zero the beam widens and pales while it dies — energy dispersing, not
// geometry blinking out.
float warning=1-smoothstep(.02,.18,FirePower);
float warningSoft=exp(-3.2*pow(across-wobble*.55,2))*(1-smoothstep(.82,1.,abs(across)));
float warningCore=exp(-28*across*across);
float warningFlow=.94+.06*sin(UV.y*18-Clock*5);
float profile=lerp(soft*strands+core*.55,(warningSoft*.88+warningCore*.12)*warningFlow,warning);
tint=lerp(lerp(tint,coreTint,core*.8),float3(.45,.62,1.0),warning*.8);
glow+=warning*.7;
return float4(tint*glow/max(Exposure,.25),saturate(Strength*.58*profile*tips*lerp(1.,3.2,warning)));
